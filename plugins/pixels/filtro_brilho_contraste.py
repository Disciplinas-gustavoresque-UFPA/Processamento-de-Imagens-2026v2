"""
plugins/pixels/filtro_brilho_contraste.py
-----------------------------------------
Plugin de exemplo: ajuste de brilho e contraste via sliders.

A implementação segue cinco etapas:

1) Normalização para [0, 1]
2) Ajuste de brilho com regra condicional
3) Ajuste de contraste com tangente e pivô em 0.5
4) Clipping para [0, 1]
5) Retorno para 8 bits (0 a 255)

Onde:
* B (brilho) está em (-1.0, 1.0)
* C (contraste) está em (-1.0, 1.0)
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


class FiltroBrilhoContraste(PluginBase):
    """Plugin para ajuste interativo de brilho e contraste da imagem."""

    display_name = "Brilho e Contraste"

    # ------------------------------------------------------------------
    # Interface (setup_ui)
    # ------------------------------------------------------------------

    def setup_ui(self) -> None:
        """Cria os sliders de brilho/contraste e os botões Aplicar/Cancelar."""
        layout_principal = QVBoxLayout(self)

        # --- Rótulos informativos ---
        self._rotulo_brilho = QLabel("Brilho (B): +0.00", self)
        self._rotulo_brilho.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_principal.addWidget(self._rotulo_brilho)

        self._rotulo_contraste = QLabel("Contraste (C): +0.00", self)
        self._rotulo_contraste.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_principal.addWidget(self._rotulo_contraste)

        # --- Slider de brilho (B em -0.99 a +0.99) ---
        self._slider_brilho = QSlider(Qt.Orientation.Horizontal, self)
        self._slider_brilho.setMinimum(-99)
        self._slider_brilho.setMaximum(99)
        self._slider_brilho.setValue(0)
        self._slider_brilho.setTickInterval(5)
        self._slider_brilho.setTickPosition(QSlider.TickPosition.TicksBelow)
        layout_principal.addWidget(self._slider_brilho)

        # --- Slider de contraste (C em -0.99 a +0.99) ---
        self._slider_contraste = QSlider(Qt.Orientation.Horizontal, self)
        self._slider_contraste.setMinimum(-99)
        self._slider_contraste.setMaximum(99)
        self._slider_contraste.setValue(0)
        self._slider_contraste.setTickInterval(5)
        self._slider_contraste.setTickPosition(QSlider.TickPosition.TicksBelow)
        layout_principal.addWidget(self._slider_contraste)

        # --- Botões ---
        layout_botoes = QHBoxLayout()
        self._btn_aplicar = QPushButton("Aplicar", self)
        self._btn_cancelar = QPushButton("Cancelar", self)
        layout_botoes.addWidget(self._btn_aplicar)
        layout_botoes.addWidget(self._btn_cancelar)
        layout_principal.addLayout(layout_botoes)

        # --- Conexões ---
        self._slider_brilho.valueChanged.connect(self._ao_mudar_parametro)
        self._slider_contraste.valueChanged.connect(self._ao_mudar_parametro)
        self._btn_aplicar.clicked.connect(self._ao_aplicar)
        self._btn_cancelar.clicked.connect(self.reject)

        self.setLayout(layout_principal)
        self.setMinimumWidth(340)

    # ------------------------------------------------------------------
    # Lógica de processamento
    # ------------------------------------------------------------------

    def _obter_parametros_normalizados(self) -> tuple[float, float]:
        """Lê os sliders e converte para o intervalo contínuo (-1, 1)."""
        brilho = self._slider_brilho.value() / 100.0
        contraste = self._slider_contraste.value() / 100.0
        return brilho, contraste

    def _calcular_slant(self, contraste: float) -> float:
        """Calcula o fator angular do contraste com base na tangente."""
        return float(np.tan((contraste + 1.0) * np.pi / 4.0))

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        """
        Aplica os ajustes de brilho e contraste conforme especificação.

        Parâmetros
        ----------
        imagem : np.ndarray
            Imagem RGB de entrada.

        Retorna
        -------
        np.ndarray
            Imagem final em 8 bits após normalização, ajuste e clipping.
        """
        brilho, contraste = self._obter_parametros_normalizados()

        # 1) Normaliza os pixels de [0, 255] para [0.0, 1.0].
        v = imagem.astype(np.float32) / 255.0

        # 2) Ajuste de brilho com regra condicional.
        b_calc = brilho / 2.0
        if b_calc < 0.0:
            v_luz = v * (1.0 + b_calc)
        else:
            v_luz = v + ((1.0 - v) * b_calc)

        # 3) Ajuste de contraste ao redor do pivô central (0.5).
        slant = self._calcular_slant(contraste)
        v_contraste = (v_luz - 0.5) * slant + 0.5

        # 4) Restringe os valores para o intervalo válido [0.0, 1.0].
        v_final = np.clip(v_contraste, 0.0, 1.0)

        # 5) Retorna para 8 bits com arredondamento para inteiro mais próximo.
        resultado = np.rint(v_final * 255.0).astype(np.uint8)
        return resultado

    # ------------------------------------------------------------------
    # Slots privados
    # ------------------------------------------------------------------

    def _ao_mudar_parametro(self, _valor: int) -> None:
        """Atualiza os rótulos e emite o sinal de pré-visualização."""
        brilho, contraste = self._obter_parametros_normalizados()

        self._rotulo_brilho.setText(f"Brilho (B): {brilho:+.2f}")
        self._rotulo_contraste.setText(f"Contraste (C): {contraste:+.2f}")

        imagem_processada = self.processar(self.imagem_original)
        self.preview_requested.emit(imagem_processada)

    def _ao_aplicar(self) -> None:
        """Emite o sinal de confirmação e fecha o diálogo."""
        imagem_processada = self.processar(self.imagem_original)
        self.apply_requested.emit(imagem_processada)
        self.accept()
