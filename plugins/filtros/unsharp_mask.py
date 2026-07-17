"""
Plugin: Unsharp Mask
--------------------
Realça detalhes da imagem utilizando o algoritmo Unsharp Mask.

Autor: Adan Alexey Mafra de Meneses
Disciplina: Processamento de Imagens - UFPA 2026

Descrição
---------
O algoritmo funciona em três etapas:

1. Aplica um desfoque Gaussiano na imagem.
2. Calcula a diferença entre a imagem original e a desfocada.
3. Soma essa diferença à imagem original, aumentando a nitidez.

Fórmula:

    Resultado = Original + α * (Original - Blur)

onde:
    α = intensidade do efeito.

"""

import cv2
import numpy as np

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
)

from core.plugin_base import PluginBase


class UnsharpMaskPlugin(PluginBase):

    display_name = "Unsharp Mask"

    def setup_ui(self):

        layout = QVBoxLayout(self)

        titulo = QLabel("Intensidade da Nitidez")
        layout.addWidget(titulo)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(300)
        self.slider.setValue(150)
        self.slider.valueChanged.connect(self._atualizar_preview)

        layout.addWidget(self.slider)

        self.btn_aplicar = QPushButton("Aplicar")
        self.btn_aplicar.clicked.connect(self._aplicar)

        layout.addWidget(self.btn_aplicar)

        self.setLayout(layout)

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        """
        Executa o algoritmo Unsharp Mask.

        Parameters
        ----------
        imagem : np.ndarray
            Imagem original.

        Returns
        -------
        np.ndarray
            Imagem com nitidez aumentada.
        """

        intensidade = self.slider.value() / 100.0

        # Desfoque Gaussiano
        blur = cv2.GaussianBlur(imagem, (9, 9), sigmaX=10)

        # Unsharp Mask
        resultado = cv2.addWeighted(
            imagem,
            1.0 + intensidade,
            blur,
            -intensidade,
            0
        )

        return np.clip(resultado, 0, 255).astype(np.uint8)

    def _atualizar_preview(self):
        """
        Atualiza a visualização em tempo real.
        """
        imagem = self.processar(self.imagem_original)
        self.preview_requested.emit(imagem)

    def _aplicar(self):
        """
        Aplica definitivamente o filtro.
        """
        imagem = self.processar(self.imagem_original)
        self.apply_requested.emit(imagem)
        self.accept()