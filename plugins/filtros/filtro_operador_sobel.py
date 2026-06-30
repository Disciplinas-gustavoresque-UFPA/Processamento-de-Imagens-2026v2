"""
# plugins/bordas/filtro_sobel.py
# -----------------------------------------
# Plugin: Detecção de bordas via Operador Sobel.
# 
# Etapas:
# 1) Conversão da imagem RGB para escala de cinzentos.
# 2) Convolução com kernels 3x3 para derivadas espaciais (X e Y).
# 3) Cálculo da magnitude do gradiente com ajuste de escala e normalização.
# 
# Detalhes:
# * Kernel X: Destaca linhas verticais.
# * Kernel Y: Destaca linhas horizontais.
# * Reduz ruídos devido à suavização integrada (peso 2 no centro).
# * Usa float64 (cv2.CV_64F) e normaliza para uint8 com np.clip().

"""
import cv2
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout

from core.plugin_base import PluginBase


class FiltroSobel(PluginBase):
    display_name = "Operador Sobel"

    def setup_ui(self) -> None:
        """
        Função que cria a interface do plugin com slider de ajuste do limiar e botões Aplicar/Cancelar.
        """
        layout = QVBoxLayout(self)

        self.info = QLabel("Aplica o operador Sobel para destacar bordas na imagem.")
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

