import numpy as np
import threading
import cv2
from PySide6.QtWidgets import QVBoxLayout, QSlider, QPushButton, QLabel
from PySide6.QtCore import Qt
from core.plugin_base import PluginBase


class SaltPepperNoise(PluginBase):
    display_name = "Ruído Salt and Pepper"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._kernel_cache = {}
        self._timer = None

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

   

    def _gaussian_kernel(self, size: int) -> np.ndarray:
        if size in self._kernel_cache:
            return self._kernel_cache[size]

        ax = np.arange(-size // 2 + 1., size // 2 + 1.)
        xx, yy = np.meshgrid(ax, ax)

        sigma = size / 2.0
        kernel = np.exp(-(xx**2 + yy**2) / (2. * sigma**2))
        kernel = kernel / np.sum(kernel)

        self._kernel_cache[size] = kernel
        return kernel

   

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        img = imagem.astype(np.float32)

        amount = self.slider_amount.value() / 100.0
        salt_ratio = self.slider_ratio.value() / 100.0
        kernel_size = self.slider_kernel.value()

        h, w = img.shape[:2]

        noise_map = np.random.rand(h, w).astype(np.float32)

        threshold = 1.0 - amount
        noise_mask = (noise_map > threshold).astype(np.float32)

        sigma = kernel_size

        blob_mask = cv2.GaussianBlur(
            noise_mask,
            (0, 0),
            sigmaX=sigma,
            sigmaY=sigma
        )

        blob_mask = np.clip(blob_mask, 0, 1)

        salt = (np.random.rand(h, w) < salt_ratio).astype(np.float32)
        pepper = 1.0 - salt

        noise_layer = (salt * 255.0) + (pepper * 0.0)

        if img.ndim == 2:
            out = img * (1 - blob_mask) + noise_layer * blob_mask
        else:
            out = img.copy()
            for c in range(3):
                out[:, :, c] = (
                    img[:, :, c] * (1 - blob_mask) +
                    noise_layer * blob_mask
                )

        return np.clip(out, 0, 255).astype(np.uint8)



    def _apply_noise(self, img, y, x, value, kernel_size):
        k = kernel_size // 2

        y_min = max(0, y - k)
        y_max = min(img.shape[0], y + k + 1)
        x_min = max(0, x - k)
        x_max = min(img.shape[1], x + k + 1)

        patch = img[y_min:y_max, x_min:x_max]
        patch_h, patch_w = patch.shape[:2]

        kernel = self._gaussian_kernel(kernel_size)

        kh, kw = kernel.shape
        ky = (kh - patch_h) // 2
        kx = (kw - patch_w) // 2

        kernel = kernel[ky:ky + patch_h, kx:kx + patch_w]

        if img.ndim == 2:
            img[y_min:y_max, x_min:x_max] = (
                patch * (1 - kernel) + value * kernel
            )
        else:
            for c in range(3):
                img[y_min:y_max, x_min:x_max, c] = (
                    patch[:, :, c] * (1 - kernel) + value * kernel
                )

    

    def _on_change(self):
        self.label_amount.setText(f"Intensidade: {self.slider_amount.value()}%")
        sal = self.slider_ratio.value()
        pimenta = 100 - sal
        self.label_ratio.setText(f"Sal: {sal}% | Pimenta: {pimenta}%")
        self.label_kernel.setText(f"Tamanho: {self.slider_kernel.value()}")

        if self._timer:
            self._timer.cancel()

        self._timer = threading.Timer(0.15, self._update_preview)
        self._timer.start()

    def _update_preview(self):
        img = self.processar(self.imagem_original)
        self.preview_requested.emit(img)

    def _on_apply(self):
        img = self.processar(self.imagem_original)
        self.apply_requested.emit(img)
        self.accept()