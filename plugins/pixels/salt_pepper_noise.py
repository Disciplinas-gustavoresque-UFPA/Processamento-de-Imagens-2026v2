import numpy as np
import cv2

from PySide6.QtWidgets import QVBoxLayout, QSlider, QPushButton, QLabel
from PySide6.QtCore import Qt, QTimer
from core.plugin_base import PluginBase


class SaltPepperNoise(PluginBase):
    display_name = "Ruído Salt and Pepper"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._update_preview)

    def setup_ui(self):
        layout = QVBoxLayout(self)

        self.label_amount = QLabel("Intensidade: 5%")
        self.slider_amount = QSlider(Qt.Horizontal)
        self.slider_amount.setMinimum(0)
        self.slider_amount.setMaximum(100)
        self.slider_amount.setValue(5)

        self.label_ratio = QLabel("Sal: 50% | Pimenta: 50%")
        self.slider_ratio = QSlider(Qt.Horizontal)
        self.slider_ratio.setMinimum(0)
        self.slider_ratio.setMaximum(100)
        self.slider_ratio.setValue(50)

        self.label_kernel = QLabel("Tamanho do grão: 1")
        self.slider_kernel = QSlider(Qt.Horizontal)
        self.slider_kernel.setMinimum(1)
        self.slider_kernel.setMaximum(7)
        self.slider_kernel.setValue(1)

        self.label_alpha = QLabel("Opacidade: 100%")
        self.slider_alpha = QSlider(Qt.Horizontal)
        self.slider_alpha.setMinimum(0)
        self.slider_alpha.setMaximum(100)
        self.slider_alpha.setValue(100)

        self.btn_apply = QPushButton("Aplicar")

        layout.addWidget(self.label_amount)
        layout.addWidget(self.slider_amount)
        layout.addWidget(self.label_ratio)
        layout.addWidget(self.slider_ratio)
        layout.addWidget(self.label_kernel)
        layout.addWidget(self.slider_kernel)
        layout.addWidget(self.label_alpha)
        layout.addWidget(self.slider_alpha)
        layout.addWidget(self.btn_apply)

        self.setLayout(layout)

        self.slider_amount.valueChanged.connect(self._on_change)
        self.slider_ratio.valueChanged.connect(self._on_change)
        self.slider_kernel.valueChanged.connect(self._on_change)
        self.slider_alpha.valueChanged.connect(self._on_change)

        self.btn_apply.clicked.connect(self._on_apply)

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        img = imagem.copy().astype(np.uint8)

        # Intensidade suavizada, evita saturação agressiva
        amount = (self.slider_amount.value() / 100.0) * 0.25

        salt_ratio = self.slider_ratio.value() / 100.0
        kernel_size = self.slider_kernel.value()
        alpha = self.slider_alpha.value() / 100.0

        h, w = img.shape[:2]
        num_pixels = int(amount * h * w)

        if num_pixels == 0:
            return img

        coords = np.random.choice(h * w, num_pixels, replace=False)
        ys = coords // w
        xs = coords % w

        num_salt = int(num_pixels * salt_ratio)

        salt_mask = np.zeros((h, w), dtype=np.uint8)
        pepper_mask = np.zeros((h, w), dtype=np.uint8)

        salt_mask[ys[:num_salt], xs[:num_salt]] = 1
        pepper_mask[ys[num_salt:], xs[num_salt:]] = 1


        if kernel_size > 1:
            kernel = np.ones((kernel_size, kernel_size), np.uint8)

            salt_mask = cv2.dilate(salt_mask, kernel, iterations=1)
            pepper_mask = cv2.dilate(pepper_mask, kernel, iterations=1)


        overlap = (salt_mask == 1) & (pepper_mask == 1)
        salt_mask[overlap] = 0
        pepper_mask[overlap] = 0

        noisy = img.copy()

        noisy[salt_mask == 1] = 255
        noisy[pepper_mask == 1] = 0

        out = ((1 - alpha) * img + alpha * noisy).astype(np.uint8)

        return out

    def _on_change(self):
        self.label_amount.setText(f"Intensidade: {self.slider_amount.value()}%")

        sal = self.slider_ratio.value()
        pimenta = 100 - sal
        self.label_ratio.setText(f"Sal: {sal}% | Pimenta: {pimenta}%")

        self.label_kernel.setText(f"Tamanho do grão: {self.slider_kernel.value()}")
        self.label_alpha.setText(f"Opacidade: {self.slider_alpha.value()}%")

        self._timer.start(150)

    def _update_preview(self):
        img = self.processar(self.imagem_original)
        self.preview_requested.emit(img)

    def _on_apply(self):
        img = self.processar(self.imagem_original)
        self.apply_requested.emit(img)
        self.accept()