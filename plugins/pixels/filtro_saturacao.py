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
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
)

from core.plugin_base import PluginBase


def _construir_lut_srgb_para_linear() -> np.ndarray:
    """Pré-computa a tabela sRGB (uint8) → linear (float32), 256 entradas."""
    indices = np.arange(256, dtype=np.float32) / 255.0
    trecho_linear = indices / 12.92
    trecho_curvo = ((indices + 0.055) / 1.055) ** 2.4
    return np.where(indices <= 0.04045, trecho_linear, trecho_curvo).astype(np.float32)


class FiltroSaturacao(PluginBase):
    """Plugin para ajuste interativo de saturação em RGB (modo nativo)."""

    display_name = "Saturação"

    # Coeficientes de luminância usados na mistura de dessaturação.
    _LUMINANCIA_R = 0.2126
    _LUMINANCIA_G = 0.7152
    _LUMINANCIA_B = 0.0722

    # LUT estática: evita exponenciação **2.4 em milhões de pixels no decode.
    _LUT_SRGB_PARA_LINEAR = _construir_lut_srgb_para_linear()

    # Atraso (ms) entre o último movimento do slider e o disparo do preview.
    _DEBOUNCE_PREVIEW_MS = 80

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

        # Debounce: arrastar o slider só dispara processar() depois que o
        # usuário para de movê-lo. Sem isso, o pipeline pesado de gama é
        # invocado a cada tick e a UI engasga em imagens grandes.
        self._timer_preview = QTimer(self)
        self._timer_preview.setSingleShot(True)
        self._timer_preview.setInterval(self._DEBOUNCE_PREVIEW_MS)
        self._timer_preview.timeout.connect(self._emitir_preview)

        self._slider_saturacao.valueChanged.connect(self._ao_mudar_saturacao)
        self._btn_aplicar.clicked.connect(self._ao_aplicar)
        self._btn_cancelar.clicked.connect(self.reject)

        self.setLayout(layout_principal)
        self.setMinimumWidth(360)

    # ------------------------------------------------------------------
    # Lógica de processamento
    # ------------------------------------------------------------------

    def _srgb_uint8_para_linear(self, imagem_uint8: np.ndarray) -> np.ndarray:
        """Decodifica sRGB → RGB Linear consultando a LUT pré-computada."""
        return self._LUT_SRGB_PARA_LINEAR[imagem_uint8]

    def _linear_para_srgb(self, v_linear: np.ndarray) -> np.ndarray:
        """Codifica de RGB Linear de volta para sRGB."""
        # Faz clipping antes da curva para manter o domínio válido.
        v_linear = np.clip(v_linear, 0.0, 1.0)
        return np.where(
            v_linear <= 0.0031308,
            v_linear * 12.92,
            1.055 * (v_linear ** (1.0 / 2.4)) - 0.055,
        )

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

        # 1+2) Decodifica sRGB (uint8) direto para RGB Linear via LUT.
        # A LUT funde a normalização [0,255]→[0,1] e a curva de gama
        # numa única indexação vetorizada.
        v_linear = self._srgb_uint8_para_linear(imagem)

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
        """Atualiza rótulos imediatamente e agenda o preview com debounce."""
        valor_slider = self._slider_saturacao.value()
        escala = self._obter_escala_gimp()

        self._rotulo_slider.setText(f"Saturação: {valor_slider:+d}")
        self._rotulo_escala.setText(f"Escala GIMP (s): {escala:.2f}")

        # start() reinicia o timer: enquanto o usuário move o slider, o
        # disparo é adiado. processar() só roda quando o movimento para.
        self._timer_preview.start()

    def _emitir_preview(self) -> None:
        """Processa a imagem com o valor atual do slider e emite o preview."""
        imagem_processada = self.processar(self.imagem_original)
        self.preview_requested.emit(imagem_processada)

    def _ao_aplicar(self) -> None:
        """Emite o sinal de confirmação e fecha o diálogo."""
        # Garante que nenhum preview pendente dispare depois do apply.
        self._timer_preview.stop()
        imagem_processada = self.processar(self.imagem_original)
        self.apply_requested.emit(imagem_processada)
        self.accept()
