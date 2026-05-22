import numpy as np
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from core.plugin_base import PluginBase


class FiltroNegativo(PluginBase):
    display_name = "Negativo"

    def setup_ui(self) -> None:
        layout_principal = QVBoxLayout(self)

        rotulo = QLabel(
            "Este filtro aplica o efeito negativo na imagem.",
            self,
        )

        layout_principal.addWidget(rotulo)

        layout_botoes = QHBoxLayout()

        self._btn_aplicar = QPushButton("Aplicar", self)
        self._btn_cancelar = QPushButton("Cancelar", self)

        layout_botoes.addWidget(self._btn_aplicar)
        layout_botoes.addWidget(self._btn_cancelar)

        layout_principal.addLayout(layout_botoes)

        self._btn_aplicar.clicked.connect(self._ao_aplicar)
        self._btn_cancelar.clicked.connect(self.reject)

        self.setLayout(layout_principal)
        self.setMinimumWidth(320)

        # PREVIEW IMEDIATO
        imagem_processada = self.processar(self.imagem_original)
        self.preview_requested.emit(imagem_processada)

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        print("Aplicando negativo...")

        imagem_saida = imagem.copy()

        imagem_saida[..., :3] = 255 - imagem_saida[..., :3]

        return imagem_saida

    def _ao_aplicar(self) -> None:
        imagem_processada = self.processar(self.imagem_original)
        print("Enviando preview...")
        self.preview_requested.emit(imagem_processada)
        print("Enviando apply...")
        self.apply_requested.emit(imagem_processada)
        self.accept()