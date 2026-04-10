import numpy as np
from PySide6.QtWidgets import QVBoxLayout, QSlider, QPushButton, QLabel
from PySide6.QtCore import Qt
from core.plugin_base import PluginBase


class SaltPepperNoise(PluginBase):
    display_name = "Ruído Salt and Pepper"

    def setup_ui(self):
        layout = QVBoxLayout(self)

        
        self.label_amount = QLabel("Intensidade: 5%")
        self.slider_amount = QSlider(Qt.Horizontal)
        self.slider_amount.setMinimum(1)
        self.slider_amount.setMaximum(100)
        self.slider_amount.setValue(5)

        
        self.btn_apply = QPushButton("Aplicar")

        layout.addWidget(self.label_amount)
        layout.addWidget(self.slider_amount)
        layout.addWidget(self.btn_apply)

        self.setLayout(layout)

        # Eventos
        self.slider_amount.valueChanged.connect(self._on_change)
        self.btn_apply.clicked.connect(self._on_apply)

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        noisy = imagem.copy()

        amount = self.slider_amount.value() / 100.0

        h, w = noisy.shape[:2]
        total_pixels = h * w
        num_noise = int(total_pixels * amount)

        
        ys = np.random.randint(0, h, num_noise)
        xs = np.random.randint(0, w, num_noise)

        
        for i in range(num_noise):
            if np.random.rand() < 0.5:
                value = 255  
            else:
                value = 0    

            if noisy.ndim == 2:
                noisy[ys[i], xs[i]] = value
            else:
                noisy[ys[i], xs[i], :] = value

        return noisy

    def _on_change(self):
        valor = self.slider_amount.value()
        self.label_amount.setText(f"Intensidade: {valor}%")

        img = self.processar(self.imagem_original)
        self.preview_requested.emit(img)

    def _on_apply(self):
        img = self.processar(self.imagem_original)
        self.apply_requested.emit(img)
        self.accept()