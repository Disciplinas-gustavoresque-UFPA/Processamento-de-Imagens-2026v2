import cv2
import numpy as np
from PySide6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QComboBox,
    QPushButton,
)
from core.plugin_base import PluginBase


class PluginMipmapping(PluginBase):
    display_name = "Mipmapping"

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Configuração da grade M x N
        grade_layout = QHBoxLayout()

        grade_layout.addWidget(QLabel("Linhas (M):"))
        self.spin_m = QSpinBox()
        self.spin_m.setRange(1, 8)
        self.spin_m.setValue(2)
        self.spin_m.valueChanged.connect(self._ao_alterar_config)
        grade_layout.addWidget(self.spin_m)

        grade_layout.addWidget(QLabel("Colunas (N):"))
        self.spin_n = QSpinBox()
        self.spin_n.setRange(1, 8)
        self.spin_n.setValue(2)
        self.spin_n.valueChanged.connect(self._ao_alterar_config)
        grade_layout.addWidget(self.spin_n)

        layout.addLayout(grade_layout)

        # Seleção da abordagem de mipmapping
        layout.addWidget(QLabel("Método de Mipmapping:"))

        self.combo_metodo = QComboBox()
        self.combo_metodo.addItems([
            "Sem mipmapping (Subamostragem Direta)",
            "Mipmapping - Implementação Manual",
            "Mipmapping - OpenCV (pyrDown)"
        ])
        self.combo_metodo.currentIndexChanged.connect(self._ao_alterar_config)
        layout.addWidget(self.combo_metodo)

        self.btn_aplicar = QPushButton("Aplicar no Editor")
        self.btn_aplicar.clicked.connect(self._ao_aplicar)
        layout.addWidget(self.btn_aplicar)

        self.setLayout(layout)

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        return imagem.copy()

    def _ao_alterar_config(self):
        pass

    def _ao_aplicar(self):
        self.accept()