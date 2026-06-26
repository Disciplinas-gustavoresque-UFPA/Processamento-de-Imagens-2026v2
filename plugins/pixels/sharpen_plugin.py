import numpy as np
import cv2

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QVBoxLayout,
    QLabel,
    QSlider,
    QPushButton,
    QHBoxLayout,
)

from core.plugin_base import PluginBase


class SharpenPlugin(PluginBase):
    display_name = "Nitidez (Sharpen)"

    def setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Label
        self.label = QLabel("Intensidade: 1.0")

        # Slider
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(300) 
        self.slider.setValue(0)

        self.slider.valueChanged.connect(self._on_change)

        # Botões
        btn_layout = QHBoxLayout()

        self.btn_apply = QPushButton("Aplicar")
        self.btn_cancel = QPushButton("Cancelar")

        self.btn_apply.clicked.connect(self._apply)
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_apply)
        btn_layout.addWidget(self.btn_cancel)

        # Layout final
        layout.addWidget(self.label)
        layout.addWidget(self.slider)
        layout.addLayout(btn_layout)

    def _intensity(self) -> float:
        return self.slider.value() / 100.0

    def _on_change(self):
        value = self._intensity()
        self.label.setText(f"Intensidade: {value:.2f}")

        preview = self.processar(self.imagem_original)
        self.preview_requested.emit(preview)

    def _apply(self):
        result = self.processar(self.imagem_original)
        self.apply_requested.emit(result)
        self.accept()

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        alpha = self._intensity()

        # blur leve
        blurred = cv2.GaussianBlur(imagem, (0, 0), sigmaX=4)

        # unsharp mask
        sharpened = cv2.addWeighted(
            imagem, 1 + alpha,
            blurred, -alpha,
            0
        )

        return np.clip(sharpened, 0, 255).astype(np.uint8)