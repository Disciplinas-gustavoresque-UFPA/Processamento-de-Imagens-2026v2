import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from core.plugin_base import PluginBase


class FiltroEscalaDeCinza(PluginBase):
    display_name = "Escala de Cinza"

    def setup_ui(self) -> None:
        layout_principal = QVBoxLayout(self)

        rotulo_metodo = QLabel("Metodo de conversao:", self)
        layout_principal.addWidget(rotulo_metodo)

        self._combo_metodo = QComboBox(self)
        self._combo_metodo.addItem("Canal R", "r")
        self._combo_metodo.addItem("Canal G", "g")
        self._combo_metodo.addItem("Canal B", "b")
        self._combo_metodo.addItem("Media RGB", "media")
        layout_principal.addWidget(self._combo_metodo)

        self._rotulo_metodo_atual = QLabel("Conversao atual: Canal R", self)
        self._rotulo_metodo_atual.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_principal.addWidget(self._rotulo_metodo_atual)

        layout_botoes = QHBoxLayout()
        self._btn_aplicar = QPushButton("Aplicar", self)
        self._btn_cancelar = QPushButton("Cancelar", self)
        layout_botoes.addWidget(self._btn_aplicar)
        layout_botoes.addWidget(self._btn_cancelar)
        layout_principal.addLayout(layout_botoes)

        self._combo_metodo.currentIndexChanged.connect(self._ao_mudar_metodo)
        self._btn_aplicar.clicked.connect(self._ao_aplicar)
        self._btn_cancelar.clicked.connect(self.reject)

        self.setLayout(layout_principal)
        self.setMinimumWidth(320)

    def _obter_metodo(self) -> str:
        return str(self._combo_metodo.currentData())

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        imagem_float = imagem.astype(np.float32)
        metodo = self._obter_metodo()

        r = imagem_float[..., 0]
        g = imagem_float[..., 1]
        b = imagem_float[..., 2]

        if metodo == "r":
            cinza = r
        elif metodo == "g":
            cinza = g
        elif metodo == "b":
            cinza = b
        else:
            cinza = (r + g + b) / 3.0

        canal = np.rint(cinza).astype(np.uint8)
        return np.stack((canal, canal, canal), axis=-1)

    def _ao_mudar_metodo(self, _indice: int) -> None:
        self._rotulo_metodo_atual.setText(
            f"Conversao atual: {self._combo_metodo.currentText()}"
        )
        imagem_processada = self.processar(self.imagem_original)
        self.preview_requested.emit(imagem_processada)

    def _ao_aplicar(self) -> None:
        imagem_processada = self.processar(self.imagem_original)
        self.apply_requested.emit(imagem_processada)
        self.accept()