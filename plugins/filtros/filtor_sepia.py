import cv2
import numpy as np

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QVBoxLayout,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QSlider,
)

from core.plugin_base import PluginBase


class FiltroSepia(PluginBase):
    display_name = "Filtro Sépia"

    def setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        self.info = QLabel(
            "Aplica um efeito sépia com intensidade ajustável."
        )
        layout.addWidget(self.info)

        self.rotulo_intensidade = QLabel(
            "Intensidade: 100%",
            self
        )
        self.rotulo_intensidade.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        layout.addWidget(self.rotulo_intensidade)

        self.slider_intensidade = QSlider(
            Qt.Orientation.Horizontal,
            self
        )
        self.slider_intensidade.setMinimum(0)
        self.slider_intensidade.setMaximum(100)
        self.slider_intensidade.setValue(100)

        self.slider_intensidade.valueChanged.connect(
            self._ao_mudar_intensidade
        )

        layout.addWidget(self.slider_intensidade)

        layout_botoes = QHBoxLayout()

        self.btn_aplicar = QPushButton("Aplicar")
        self.btn_cancelar = QPushButton("Cancelar")

        layout_botoes.addWidget(self.btn_aplicar)
        layout_botoes.addWidget(self.btn_cancelar)

        layout.addLayout(layout_botoes)

        self.btn_aplicar.clicked.connect(self._ao_aplicar)
        self.btn_cancelar.clicked.connect(self.reject)

        self.setLayout(layout)
        self.setMinimumWidth(320)

        self._ao_mudar_intensidade(
            self.slider_intensidade.value()
        )

    def _obter_intensidade(self) -> float:
        return self.slider_intensidade.value() / 100.0

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        """
        Aplica o filtro sépia com intensidade variável.
        """

        img = imagem.astype(np.float32)

        matriz_sepia = np.array(
            [
                [0.393, 0.769, 0.189],
                [0.349, 0.686, 0.168],
                [0.272, 0.534, 0.131],
            ],
            dtype=np.float32,
        )

        img_sepia = cv2.transform(img, matriz_sepia)

        img_sepia = np.clip(
            img_sepia,
            0,
            255
        ).astype(np.uint8)

        intensidade = self._obter_intensidade()

        resultado = cv2.addWeighted(
            imagem,
            1.0 - intensidade,
            img_sepia,
            intensidade,
            0
        )

        return resultado

    def _ao_mudar_intensidade(
        self,
        valor: int
    ) -> None:

        self.rotulo_intensidade.setText(
            f"Intensidade: {valor}%"
        )

        imagem_processada = self.processar(
            self.imagem_original
        )

        self.preview_requested.emit(
            imagem_processada
        )

    def _ao_aplicar(self) -> None:

        img_processada = self.processar(
            self.imagem_original
        )

        self.apply_requested.emit(
            img_processada
        )

        self.accept()