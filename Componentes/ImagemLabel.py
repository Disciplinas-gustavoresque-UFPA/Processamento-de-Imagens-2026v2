from PySide6.QtCore import (Signal)
from PySide6.QtWidgets import (QLabel)

class ImageLabel(QLabel):
    mouse_moved = Signal(object)  # envia o evento

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)

    def mouseMoveEvent(self, event):
        self.mouse_moved.emit(event)
        super().mouseMoveEvent(event)