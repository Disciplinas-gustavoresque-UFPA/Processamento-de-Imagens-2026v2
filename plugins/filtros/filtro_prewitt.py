import cv2
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout

from core.plugin_base import PluginBase


class FiltroPrewitt(PluginBase):
    display_name = "Detecção de Borda (Prewitt)"

    def setup_ui(self) -> None:
        """Constroi os botoes e controles da janela flutuante."""
        layout = QVBoxLayout(self)

        self.info = QLabel("Aplica o operador Prewitt para destacar bordas na imagem.")
        layout.addWidget(self.info)

        self.rotulo_escala = QLabel("Escala da magnitude: 1.0x", self)
        self.rotulo_escala.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.rotulo_escala)

        self.slider_escala = QSlider(Qt.Orientation.Horizontal, self)
        self.slider_escala.setMinimum(1)
        self.slider_escala.setMaximum(40)
        self.slider_escala.setValue(10)
        self.slider_escala.valueChanged.connect(self._ao_mudar_escala)
        layout.addWidget(self.slider_escala)

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
        self._ao_mudar_escala(self.slider_escala.value())

    def _obter_escala(self) -> float:
        return self.slider_escala.value() / 10.0

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        """Processa a imagem aplicando o filtro Prewitt."""
        if len(imagem.shape) == 3:
            gray = cv2.cvtColor(imagem, cv2.COLOR_RGB2GRAY)
        else:
            gray = imagem.copy()

        kernel_x = np.array(
            [
                [-1, 0, 1],
                [-1, 0, 1],
                [-1, 0, 1],
            ],
            dtype=np.float32,
        )
        kernel_y = np.array(
            [
                [-1, -1, -1],
                [0, 0, 0],
                [1, 1, 1],
            ],
            dtype=np.float32,
        )

        img_prewitt_x = cv2.filter2D(gray, cv2.CV_64F, kernel_x)
        img_prewitt_y = cv2.filter2D(gray, cv2.CV_64F, kernel_y)

        magnitude = cv2.magnitude(img_prewitt_x, img_prewitt_y)
        magnitude *= self._obter_escala()

        resultado = np.clip(magnitude, 0, 255).astype(np.uint8)
        return cv2.cvtColor(resultado, cv2.COLOR_GRAY2RGB)

    def _ao_mudar_escala(self, valor: int) -> None:
        escala = valor / 10.0
        self.rotulo_escala.setText(f"Escala da magnitude: {escala:.1f}x")
        imagem_processada = self.processar(self.imagem_original)
        self.preview_requested.emit(imagem_processada)

    def _ao_aplicar(self) -> None:
        """Confirma a alteracao e fecha a janela do plugin."""
        img_processada = self.processar(self.imagem_original)
        self.apply_requested.emit(img_processada)
        self.accept()