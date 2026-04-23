import numpy as np
import cv2
from PySide6.QtWidgets import QVBoxLayout, QSlider, QPushButton, QLabel
from core.plugin_base import PluginBase

class FiltroBordas(PluginBase):
    display_name = "Detector de Bordas"

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Label
        self.label = QLabel("Intensidade da Borda")
        layout.addWidget(self.label)

        # Slider
        self.slider = QSlider()
        self.slider.setMinimum(50)
        self.slider.setMaximum(200)
        self.slider.setValue(100)
        self.slider.valueChanged.connect(self._ao_alterar_slider)
        layout.addWidget(self.slider)

        # Botão aplicar
        self.btn_aplicar = QPushButton("Aplicar")
        self.btn_aplicar.clicked.connect(self._ao_aplicar)
        layout.addWidget(self.btn_aplicar)

        self.setLayout(layout)

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        # Converter para cinza
        gray = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)

        # Pegar valor do slider
        valor = self.slider.value()

        # Aplicar Canny
        edges = cv2.Canny(gray, valor, valor * 2)

        # Converter de volta para 3 canais
        edges_rgb = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)

        return edges_rgb

    def _ao_alterar_slider(self):
        img_processada = self.processar(self.imagem_original)
        self.preview_requested.emit(img_processada)

    def _ao_aplicar(self):
        img_processada = self.processar(self.imagem_original)
        self.apply_requested.emit(img_processada)
        self.accept()