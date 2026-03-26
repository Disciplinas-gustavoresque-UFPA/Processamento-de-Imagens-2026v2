"""
plugins/filtro_brilho.py
------------------------
Plugin de exemplo: ajuste de brilho via slider.

O brilho é ajustado somando ou subtraindo um valor escalar a todos os pixels
da imagem usando NumPy, com saturação em [0, 255].
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


class FiltroBrilho(PluginBase):
    """Plugin para ajuste interativo de brilho da imagem."""

    display_name = "Ajuste de Brilho"

    # ------------------------------------------------------------------
    # Interface (setup_ui)
    # ------------------------------------------------------------------

    def setup_ui(self) -> None:
        """Cria o slider de brilho e os botões Aplicar / Cancelar."""
        layout_principal = QVBoxLayout(self)

        # --- Rótulo informativo ---
        self._rotulo_valor = QLabel("Brilho: 0", self)
        self._rotulo_valor.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_principal.addWidget(self._rotulo_valor)

        # --- Slider de brilho (-255 a +255) ---
        self._slider = QSlider(Qt.Orientation.Horizontal, self)
        self._slider.setMinimum(-255)
        self._slider.setMaximum(255)
        self._slider.setValue(0)
        self._slider.setTickInterval(10)
        self._slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        layout_principal.addWidget(self._slider)

        # --- Botões ---
        layout_botoes = QHBoxLayout()
        self._btn_aplicar = QPushButton("Aplicar", self)
        self._btn_cancelar = QPushButton("Cancelar", self)
        layout_botoes.addWidget(self._btn_aplicar)
        layout_botoes.addWidget(self._btn_cancelar)
        layout_principal.addLayout(layout_botoes)

        # --- Conexões ---
        self._slider.valueChanged.connect(self._ao_mover_slider)
        self._btn_aplicar.clicked.connect(self._ao_aplicar)
        self._btn_cancelar.clicked.connect(self.reject)

        self.setLayout(layout_principal)
        self.setMinimumWidth(320)

    # ------------------------------------------------------------------
    # Lógica de processamento
    # ------------------------------------------------------------------

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        """
        Aplica o ajuste de brilho à imagem.

        Parâmetros
        ----------
        imagem : np.ndarray
            Imagem RGB de entrada.

        Retorna
        -------
        np.ndarray
            Imagem com o brilho ajustado, valores saturados em [0, 255].
        """
        valor = self._slider.value()

        # Converte para int16 para evitar overflow antes de saturar
        resultado = imagem.astype(np.int16) + valor
        resultado = np.clip(resultado, 0, 255).astype(np.uint8)
        return resultado

    # ------------------------------------------------------------------
    # Slots privados
    # ------------------------------------------------------------------

    def _ao_mover_slider(self, valor: int) -> None:
        """Atualiza o rótulo e emite o sinal de pré-visualização."""
        self._rotulo_valor.setText(f"Brilho: {valor:+d}")
        imagem_processada = self.processar(self.imagem_original)
        self.preview_requested.emit(imagem_processada)

    def _ao_aplicar(self) -> None:
        """Emite o sinal de confirmação e fecha o diálogo."""
        imagem_processada = self.processar(self.imagem_original)
        self.apply_requested.emit(imagem_processada)
        self.accept()
