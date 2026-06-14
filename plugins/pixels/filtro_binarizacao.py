import cv2
import numpy as np
from PySide6.QtCore import Qt

from core.plugin_base import PluginBase

class FiltroBinarizacao(PluginBase):
    display_name = "Binarização"
