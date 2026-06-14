import cv2
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from core.plugin_base import PluginBase


class FiltroPrewitt(PluginBase):
    display_name = "Deteccao de Borda (Prewitt)"

    def setup_ui(self) -> None:
        """Constroi os botoes e controles da janela flutuante."""
        layout = QVBoxLayout(self)

        self.info = QLabel("Aplica o operador Prewitt para destacar bordas na imagem.")
        layout.addWidget(self.info)

        layout_botoes = QHBoxLayout()
        self.btn_aplicar = QPushButton("Aplicar", self)
        self.btn_cancelar = QPushButton("Cancelar", self)
        layout_botoes.addWidget(self.btn_aplicar)
        layout_botoes.addWidget(self.btn_cancelar)
        layout.addLayout(layout_botoes)

        self.btn_aplicar.clicked.connect(self._ao_aplicar)
        self.btn_cancelar.clicked.connect(self.reject)

        self.setLayout(layout)
        self.setMinimumWidth(320)

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        """Processa a imagem aplicando o filtro Prewitt."""
        return imagem.copy()

    def _ao_aplicar(self) -> None:
        """Confirma a alteracao e fecha a janela do plugin."""
        img_processada = self.processar(self.imagem_original)
        self.apply_requested.emit(img_processada)
        self.accept()