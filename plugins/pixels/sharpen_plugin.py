import numpy as np
import cv2

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QVBoxLayout,
    QLabel,
    QSlider,
    QPushButton,
    QHBoxLayout,
    QComboBox
)

from core.plugin_base import PluginBase


class SharpenPlugin(PluginBase):
    display_name = "Nitidez (Sharpen)"

    def setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        self.label_filtro = QLabel("Filtro de Borramento:")
        self.combo_filtro = QComboBox()
        self.combo_filtro.addItems(["Gaussiano", "Média", "Mediano"])
        self.combo_filtro.currentIndexChanged.connect(self._on_change)

        # Slider de Intensidade (Alpha)
        self.label_intensidade = QLabel("Intensidade (Alpha): 1.00")
        self.slider_intensidade = QSlider(Qt.Horizontal)
        self.slider_intensidade.setMinimum(0)
        self.slider_intensidade.setMaximum(300)
        self.slider_intensidade.setValue(100) # Inicializa em 1.0
        self.slider_intensidade.valueChanged.connect(self._on_change)

        # Slider de Fator do Residual (Raio)
        self.label_raio = QLabel("Raio (Fator do Residual): 4.0")
        self.slider_raio = QSlider(Qt.Horizontal)
        self.slider_raio.setMinimum(1)
        self.slider_raio.setMaximum(500)
        self.slider_raio.setValue(40)
        self.slider_raio.valueChanged.connect(self._on_change)

        btn_layout = QHBoxLayout()

        self.btn_apply = QPushButton("Aplicar")
        self.btn_cancel = QPushButton("Cancelar")

        self.btn_apply.clicked.connect(self._apply)
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_apply)
        btn_layout.addWidget(self.btn_cancel)

        layout.addWidget(self.label_filtro)
        layout.addWidget(self.combo_filtro)
        layout.addSpacing(10)
        layout.addWidget(self.label_intensidade)
        layout.addWidget(self.slider_intensidade)
        layout.addSpacing(10)
        layout.addWidget(self.label_raio)
        layout.addWidget(self.slider_raio)
        layout.addSpacing(10)
        layout.addLayout(btn_layout)

    def _intensity(self) -> float:
        return self.slider_intensidade.value() / 100.0

    def _radius(self) -> float:
        return self.slider_raio.value() / 10.0

    def _on_change(self, *args):
        val_intensidade = self._intensity()
        val_raio = self._radius()

        self.label_intensidade.setText(f"Intensidade (Alpha): {val_intensidade:.2f}")
        self.label_raio.setText(f"Raio (Fator do Residual): {val_raio:.1f}")

        preview = self.processar(self.imagem_original)
        self.preview_requested.emit(preview)

    def _apply(self):
        result = self.processar(self.imagem_original)
        self.apply_requested.emit(result)
        self.accept()

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        alpha = self._intensity()
        raio = self._radius()
        tipo_filtro = self.combo_filtro.currentText()

        if tipo_filtro == "Gaussiano":
            blurred = cv2.GaussianBlur(imagem, (0, 0), sigmaX=raio)

        elif tipo_filtro == "Média":
            k_size = int(raio) * 2 + 1
            blurred = cv2.blur(imagem, (k_size, k_size))

        elif tipo_filtro == "Mediano":
            k_size = int(raio) * 2 + 1
            blurred = cv2.medianBlur(imagem, k_size)

        sharpened = cv2.addWeighted(
            imagem, 1 + alpha,
            blurred, -alpha,
            0
        )

        return np.clip(sharpened, 0, 255).astype(np.uint8)
