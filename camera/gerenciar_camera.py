"""
gerenciar_camera.py
------
Implementa a classe DialogoCamera, que gerencia a abertura da câmera e a atualização dos frames.

"""

import cv2
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QKeySequence, QPixmap
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QDialog
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QStatusBar,
    QVBoxLayout,
    QPushButton
)

from core.plugin_base import PluginBase  # noqa: E402  (importação após sys.path)
from components.zoom import VisualizadorImagem  # noqa: E402

class DialogoCamera(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Capturar Imagem")
        self.setMinimumSize(640, 520)

        self.layout = QVBoxLayout(self)
        
        # Label para exibir o feed de vídeo
        self.label_video = QLabel("Iniciando câmera...", self)
        self.label_video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.label_video)

        # Botão de captura
        self.btn_capturar = QPushButton("Tirar Foto", self)
        self.btn_capturar.clicked.connect(self.accept) # Fecha o diálogo com sucesso
        self.layout.addWidget(self.btn_capturar)

        # Configuração da Câmera
        self.cap = cv2.VideoCapture(0)
        self.frame_final = None

        # Timer para atualizar o preview (30 FPS aproximadamente)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._atualizar_frame)
        self.timer.start(30)

    def _atualizar_frame(self):
        ret, frame = self.cap.read()
        if ret:
            self.frame_final = frame # Guarda o último frame lido
            
            # Converte BGR para RGB para exibição no Qt
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame_rgb.shape
            bytes_per_line = ch * w
            
            imagem_qt = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            # Redimensiona para caber no label mantendo o aspecto
            self.label_video.setPixmap(QPixmap.fromImage(imagem_qt).scaled(
                self.label_video.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            ))

    def closeEvent(self, event):
        """Libera a câmera ao fechar a janela."""
        self.timer.stop()
        self.cap.release()
        super().closeEvent(event)

    def get_frame(self):
        """Retorna o frame capturado."""
        return self.frame_final