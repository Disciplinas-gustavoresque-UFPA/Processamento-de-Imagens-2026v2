import cv2
import numpy as np

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QHBoxLayout,
)

from core.plugin_base import PluginBase


class FiltroCanny(PluginBase):
    display_name = "Detecção de Bordas (Canny)"

    def setup_ui(self) -> None:

        layout = QVBoxLayout(self)

        self.info = QLabel(
            "Detecta bordas utilizando o algoritmo de Canny."
        )
        layout.addWidget(self.info)

        self.rotulo_intensidade = QLabel(
            "Sensibilidade: 50%",
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
        self.slider_intensidade.setValue(50)

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

        self.btn_aplicar.clicked.connect(
            self._ao_aplicar
        )

        self.btn_cancelar.clicked.connect(
            self.reject
        )

        self.setLayout(layout)
        self.setMinimumWidth(320)

        self._ao_mudar_intensidade(
            self.slider_intensidade.value()
        )

    def _obter_limiares(self):

        intensidade = self.slider_intensidade.value()

        threshold1 = max(
            10,
            int(100 - intensidade)
        )

        threshold2 = max(
            30,
            int(200 - intensidade * 1.5)
        )

        return threshold1, threshold2

    def processar(
        self,
        imagem: np.ndarray
    ) -> np.ndarray:

        if len(imagem.shape) == 3:

            gray = cv2.cvtColor(
                imagem,
                cv2.COLOR_RGB2GRAY
            )

        else:

            gray = imagem.copy()

        gray = cv2.GaussianBlur(
            gray,
            (5, 5),
            1.4
        )

        threshold1, threshold2 = (
            self._obter_limiares()
        )

        bordas = cv2.Canny(
            gray,
            threshold1,
            threshold2
        )

        return cv2.cvtColor(
            bordas,
            cv2.COLOR_GRAY2RGB
        )

    def _ao_mudar_intensidade(
        self,
        valor: int
    ) -> None:

        self.rotulo_intensidade.setText(
            f"Sensibilidade: {valor}%"
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