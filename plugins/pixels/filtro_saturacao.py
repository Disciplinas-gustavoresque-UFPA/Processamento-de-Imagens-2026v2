"""
plugins/pixels/filtro_saturacao.py
--------------------------------
Plugin didático: ajuste de saturação no modo nativo (RGB), seguindo
a lógica do comando Cores -> Saturação do GIMP/GEGL.

A implementação segue seis etapas:

1) Normalização para [0, 1]
2) Decodificação de sRGB para RGB Linear
3) Cálculo da luminância do pixel em RGB Linear
4) Mistura entre versão dessaturada e versão original com escala s
5) Codificação de RGB Linear para sRGB (com clipping interno)
6) Retorno para 8 bits (0 a 255)

Onde:
* Slider vai de -100 a +100
* Escala s é mapeada para [0.0, 2.0] por: s = (slider + 100) / 100
* s = 0.0  -> dessaturação total
* s = 1.0  -> imagem original
* s = 2.0  -> saturação reforçada
"""

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
)

from core.plugin_base import PluginBase


class FiltroSaturacao(PluginBase):
    """Plugin para ajuste interativo de saturação em RGB (modo nativo)."""

    display_name = "Saturação"

    # Coeficientes de luminância usados na mistura de dessaturação.
    _LUMINANCIA_R = 0.2126
    _LUMINANCIA_G = 0.7152
    _LUMINANCIA_B = 0.0722

    # ------------------------------------------------------------------
    # Interface (setup_ui)
    # ------------------------------------------------------------------

    def setup_ui(self) -> None:
        """Cria slider de saturação e botões Aplicar/Cancelar."""
        layout_principal = QVBoxLayout(self)

        self._rotulo_slider = QLabel("Saturação: +0", self)
        self._rotulo_slider.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_principal.addWidget(self._rotulo_slider)

        self._rotulo_escala = QLabel("Escala GIMP (s): 1.00", self)
        self._rotulo_escala.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_principal.addWidget(self._rotulo_escala)

        self._slider_saturacao = QSlider(Qt.Orientation.Horizontal, self)
        self._slider_saturacao.setMinimum(-100)
        self._slider_saturacao.setMaximum(100)
        self._slider_saturacao.setValue(0)
        self._slider_saturacao.setTickInterval(10)
        self._slider_saturacao.setTickPosition(QSlider.TickPosition.TicksBelow)
        layout_principal.addWidget(self._slider_saturacao)

        layout_botoes = QHBoxLayout()
        self._btn_aplicar = QPushButton("Aplicar", self)
        self._btn_cancelar = QPushButton("Cancelar", self)
        layout_botoes.addWidget(self._btn_aplicar)
        layout_botoes.addWidget(self._btn_cancelar)
        layout_principal.addLayout(layout_botoes)

        self._slider_saturacao.valueChanged.connect(self._ao_mudar_saturacao)
        self._btn_aplicar.clicked.connect(self._ao_aplicar)
        self._btn_cancelar.clicked.connect(self.reject)

        self.setLayout(layout_principal)
        self.setMinimumWidth(360)

    # ------------------------------------------------------------------
    # Lógica de processamento
    # ------------------------------------------------------------------

    def _srgb_para_linear(self, v_srgb: np.ndarray) -> np.ndarray:
        """Decodifica a curva gama sRGB para RGB Linear."""
        is_linear = v_srgb <= 0.04045
        v_linear = np.zeros_like(v_srgb)

        # Trecho linear
        v_linear[is_linear] = v_srgb[is_linear] / 12.92
        # Trecho exponencial
        v_linear[~is_linear] = ((v_srgb[~is_linear] + 0.055) / 1.055) ** 2.4

        return v_linear

    def _linear_para_srgb(self, v_linear: np.ndarray) -> np.ndarray:
        """Codifica de RGB Linear de volta para sRGB."""
        # Faz clipping antes da curva para manter o domínio válido.
        v_linear = np.clip(v_linear, 0.0, 1.0)

        is_linear = v_linear <= 0.0031308
        v_srgb = np.zeros_like(v_linear)

        # Trecho linear
        v_srgb[is_linear] = v_linear[is_linear] * 12.92
        # Trecho exponencial
        v_srgb[~is_linear] = 1.055 * (v_linear[~is_linear] ** (1.0 / 2.4)) - 0.055

        return v_srgb

    def _obter_escala_gimp(self) -> float:
        """
        Converte o slider [-100, +100] para a escala contínua [0.0, 2.0].

        Mapeamento:
        * -100 -> 0.0
        *    0 -> 1.0
        * +100 -> 2.0
        """
        valor_slider = self._slider_saturacao.value()
        return (valor_slider + 100.0) / 100.0

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        """
        Aplica saturação no modo nativo RGB usando pipeline com luz linear,
        no mesmo raciocínio do operador de saturação do GEGL/GIMP.

        Parâmetros
        ----------
        imagem : np.ndarray
            Imagem RGB de entrada.

        Retorna
        -------
        np.ndarray
            Imagem RGB em 8 bits após ajuste de saturação.
        """
        escala = self._obter_escala_gimp()

        # 1) Normaliza os pixels de [0, 255] para [0.0, 1.0] (sRGB).
        v_srgb = imagem.astype(np.float32) / 255.0

        # 2) Converte para RGB Linear para processar em luz linear.
        v_linear = self._srgb_para_linear(v_srgb)

        # 3) Cálculo da luminância (CIE Y aproximada) em RGB Linear.
        luminancia = (
            v_linear[..., 0] * self._LUMINANCIA_R
            + v_linear[..., 1] * self._LUMINANCIA_G
            + v_linear[..., 2] * self._LUMINANCIA_B
        )

        # 4) Mistura no formato do GIMP Native.
        rscale = 1.0 - escala
        desaturado = (luminancia * rscale)[..., np.newaxis]

        # Mantém valores fora de [0, 1] nesta etapa para preservar a conta.
        v_saturado_linear = desaturado + (v_linear * escala)

        # 5) Converte de volta para sRGB (com clipping interno).
        v_final_srgb = self._linear_para_srgb(v_saturado_linear)

        # 6) Retorna para 8 bits com arredondamento para inteiro mais próximo.
        resultado = np.rint(v_final_srgb * 255.0).astype(np.uint8)
        return resultado

    # ------------------------------------------------------------------
    # Slots privados
    # ------------------------------------------------------------------

    def _ao_mudar_saturacao(self, _valor: int) -> None:
        """Atualiza rótulos e emite o sinal de pré-visualização."""
        valor_slider = self._slider_saturacao.value()
        escala = self._obter_escala_gimp()

        self._rotulo_slider.setText(f"Saturação: {valor_slider:+d}")
        self._rotulo_escala.setText(f"Escala GIMP (s): {escala:.2f}")

        imagem_processada = self.processar(self.imagem_original)
        self.preview_requested.emit(imagem_processada)

    def _ao_aplicar(self) -> None:
        """Emite o sinal de confirmação e fecha o diálogo."""
        imagem_processada = self.processar(self.imagem_original)
        self.apply_requested.emit(imagem_processada)
        self.accept()
