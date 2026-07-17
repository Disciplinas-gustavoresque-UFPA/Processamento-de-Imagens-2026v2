import numpy as np
from PySide6.QtWidgets import QVBoxLayout, QSlider, QPushButton
from core.plugin_base import PluginBase

class FiltroTeste(PluginBase):

    display_name = "Teste"

    def setup_ui(self):
        pass

    def processar(self, imagem: np.ndarray):
        return imagem