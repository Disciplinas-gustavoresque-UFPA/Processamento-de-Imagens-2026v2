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
