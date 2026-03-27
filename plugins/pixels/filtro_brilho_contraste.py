"""
plugins/pixels/filtro_brilho_contraste.py
-----------------------------------------
Plugin de exemplo: ajuste de brilho e contraste via sliders.

A transformação é feita com a fórmula linear abaixo:

    saida = clip(alpha * imagem + beta, 0, 255)

Onde:
* alpha controla o contraste.
* beta controla o brilho.
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
        self._rotulo_brilho = QLabel("Brilho: +0", self)
        self._rotulo_brilho.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_principal.addWidget(self._rotulo_brilho)

        self._rotulo_contraste = QLabel("Contraste: 1.00x", self)
        self._rotulo_contraste.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_principal.addWidget(self._rotulo_contraste)

        # --- Slider de brilho (-255 a +255) ---
        self._slider_brilho = QSlider(Qt.Orientation.Horizontal, self)
        self._slider_brilho.setMinimum(-255)
        self._slider_brilho.setMaximum(255)
        self._slider_brilho.setValue(0)
        self._slider_brilho.setTickInterval(10)
        self._slider_brilho.setTickPosition(QSlider.TickPosition.TicksBelow)
        layout_principal.addWidget(self._slider_brilho)

        # --- Slider de contraste (0.20x a 3.00x) ---
        # Escala inteira para manter um slider estável:
        # valor_real = valor_slider / 100
        self._slider_contraste = QSlider(Qt.Orientation.Horizontal, self)
        self._slider_contraste.setMinimum(20)
        self._slider_contraste.setMaximum(300)
        self._slider_contraste.setValue(100)
        self._slider_contraste.setTickInterval(10)
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

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        """
        Aplica os ajustes de brilho e contraste à imagem.

        Parâmetros
        ----------
        imagem : np.ndarray
            Imagem RGB de entrada.

        Retorna
        -------
        np.ndarray
            Imagem com brilho/contraste ajustados, saturada em [0, 255].
        """
        beta = self._slider_brilho.value()
        alpha = self._slider_contraste.value() / 100.0

        # Converte para float32 para preservar precisão no ganho linear.
        resultado = alpha * imagem.astype(np.float32) + beta
        resultado = np.clip(resultado, 0, 255).astype(np.uint8)
        return resultado

    # ------------------------------------------------------------------
    # Slots privados
    # ------------------------------------------------------------------

    def _ao_mudar_parametro(self, _valor: int) -> None:
        """Atualiza os rótulos e emite o sinal de pré-visualização."""
        brilho = self._slider_brilho.value()
        contraste = self._slider_contraste.value() / 100.0

        self._rotulo_brilho.setText(f"Brilho: {brilho:+d}")
        self._rotulo_contraste.setText(f"Contraste: {contraste:.2f}x")

        imagem_processada = self.processar(self.imagem_original)
        self.preview_requested.emit(imagem_processada)

    def _ao_aplicar(self) -> None:
        """Emite o sinal de confirmação e fecha o diálogo."""
        imagem_processada = self.processar(self.imagem_original)
        self.apply_requested.emit(imagem_processada)
        self.accept()
