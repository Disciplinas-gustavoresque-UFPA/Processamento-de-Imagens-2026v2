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

        self.label_ratio = QLabel("Sal: 50% | Pimenta: 50%")
        self.slider_ratio = QSlider(Qt.Horizontal)
        self.slider_ratio.setMinimum(0)
        self.slider_ratio.setMaximum(100)
        self.slider_ratio.setValue(50)

        self.label_kernel = QLabel("Tamanho: 1")
        self.slider_kernel = QSlider(Qt.Horizontal)
        self.slider_kernel.setMinimum(1)
        self.slider_kernel.setMaximum(7)
        self.slider_kernel.setValue(1)

        self.btn_apply = QPushButton("Aplicar")

        layout.addWidget(self.label_amount)
        layout.addWidget(self.slider_amount)
        layout.addWidget(self.label_ratio)
        layout.addWidget(self.slider_ratio)
        layout.addWidget(self.label_kernel)
        layout.addWidget(self.slider_kernel)
        layout.addWidget(self.btn_apply)

        self.setLayout(layout)

        self.slider_amount.valueChanged.connect(self._on_change)
        self.slider_ratio.valueChanged.connect(self._on_change)
        self.slider_kernel.valueChanged.connect(self._on_change)
        self.btn_apply.clicked.connect(self._on_apply)

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        noisy = imagem.copy()

        amount = self.slider_amount.value() / 100.0
        salt_ratio = self.slider_ratio.value() / 100.0
        kernel_size = self.slider_kernel.value()

        h, w = noisy.shape[:2]
        total_pixels = h * w
        num_noise = int((total_pixels * amount) / (kernel_size ** 2))

        ys = np.random.randint(0, h, num_noise)
        xs = np.random.randint(0, w, num_noise)

        for i in range(num_noise):
            if np.random.rand() < salt_ratio:
                value = 255
            else:
                value = 0

            self._apply_noise(noisy, ys[i], xs[i], value, kernel_size)

        return noisy

    def _apply_noise(self, img, y, x, value, kernel_size):
        k = kernel_size // 2

        y_min = max(0, y - k)
        y_max = min(img.shape[0], y + k + 1)
        x_min = max(0, x - k)
        x_max = min(img.shape[1], x + k + 1)

        if img.ndim == 2:
            img[y_min:y_max, x_min:x_max] = value
        else:
            img[y_min:y_max, x_min:x_max, :] = value

    def _on_change(self):
        self.label_amount.setText(f"Intensidade: {self.slider_amount.value()}%")
        sal = self.slider_ratio.value()
        pimenta = 100 - sal
        self.label_ratio.setText(f"Sal: {sal}% | Pimenta: {pimenta}%")
        self.label_kernel.setText(f"Tamanho: {self.slider_kernel.value()}")

        img = self.processar(self.imagem_original)
        self.preview_requested.emit(img)

    def _on_apply(self):
        img = self.processar(self.imagem_original)
        self.apply_requested.emit(img)
        self.accept()