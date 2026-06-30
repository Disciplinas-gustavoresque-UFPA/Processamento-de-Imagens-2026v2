"""
plugins/imagem/transformar/recortar_imagem.py

Plugin de recorte interativo de imagens.

A implementação segue cinco etapas:

1) Carregamento da imagem original no visualizador.
2) Seleção da área de interesse através do mouse.
3) Atualização automática das coordenadas e dimensões do recorte.
4) Validação dos limites da região selecionada.
5) Aplicação do recorte e envio da imagem resultante para a aplicação."""

import numpy as np
from PySide6.QtCore import Qt, QRect, QPoint
from PySide6.QtGui import QPixmap, QImage, QPainter, QPen, QColor
from PySide6.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QLabel, QLineEdit,
    QDialogButtonBox, QMessageBox
)

from core.plugin_base import PluginBase
from components.zoom import VisualizadorImagem


class RecortarImagem(PluginBase):
    """Plugin de Recorte - Seleção persistente e ajustável"""

    display_name = "Recortar Imagem"

    def setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        self.visualizador = VisualizadorImagem(self)
        self.visualizador.setMinimumSize(850, 620)
        layout.addWidget(self.visualizador)

        # Campos
        coords = QHBoxLayout()
        self._x = QLineEdit("0")
        self._y = QLineEdit("0")
        self._w = QLineEdit("300")
        self._h = QLineEdit("300")

        for txt, campo in [("X:", self._x), ("Y:", self._y),
                           ("Largura:", self._w), ("Altura:", self._h)]:
            coords.addWidget(QLabel(txt))
            coords.addWidget(campo)
            campo.textChanged.connect(self._campos_alterados)

        layout.addLayout(coords)

        # Botões
        btn_box = QDialogButtonBox()
        self.btn_aplicar = btn_box.addButton("Aplicar Recorte", QDialogButtonBox.ButtonRole.AcceptRole)
        self.btn_cancelar = btn_box.addButton("Cancelar", QDialogButtonBox.ButtonRole.RejectRole)
        self.btn_aplicar.clicked.connect(self._aplicar_recorte)
        self.btn_cancelar.clicked.connect(self.reject)
        layout.addWidget(btn_box)

        # Estado
        self._retangulo = QRect(0, 0, 0, 0)
        self._arrastando = False
        self._inicio = QPoint()

        self._carregar_imagem()
        self._instalar_mouse()

    def _carregar_imagem(self):
        rgb = self.imagem_original.copy()
        h, w = rgb.shape[:2]
        bytes_por_linha = w * 3

        qimage = QImage(rgb.data, w, h, bytes_por_linha, QImage.Format.Format_RGB888).copy()
        pixmap = QPixmap.fromImage(qimage)

        self.visualizador.definir_pixmap(pixmap, ajustar_a_janela=False)
        if hasattr(self.visualizador, '_definir_zoom_absoluto'):
            self.visualizador._definir_zoom_absoluto(1.0)

    def _instalar_mouse(self):
        label = self.visualizador._label_imagem
        self._original_paint = label.paintEvent
        label.mousePressEvent = self._mouse_press
        label.mouseMoveEvent = self._mouse_move
        label.mouseReleaseEvent = self._mouse_release
        label.paintEvent = self._paint_overlay

    def _mouse_press(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return

        self._arrastando = True
        self._inicio = event.pos()

        # Se clicar dentro do retângulo existente, permite mover
        if self._retangulo.contains(event.pos()):
            self._movendo = True
        else:
            self._movendo = False
            self._retangulo = QRect(event.pos().x(), event.pos().y(), 0, 0)

        self._atualizar_campos()
        self.visualizador._label_imagem.update()

    def _mouse_move(self, event):
        if not self._arrastando:
            return

        if hasattr(self, '_movendo') and self._movendo:
            # Movimento do inteiro
            delta = event.pos() - self._inicio
            self._retangulo.translate(delta.x(), delta.y())
            self._inicio = event.pos()
        else:
            self._retangulo = QRect(self._inicio, event.pos()).normalized()

        self._atualizar_campos()
        self.visualizador._label_imagem.update()

    def _mouse_release(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._arrastando = False
            self.visualizador._label_imagem.update()

    def _paint_overlay(self, event):
        self._original_paint(event)

        if self._retangulo.width() > 5 and self._retangulo.height() > 5:
            painter = QPainter(self.visualizador._label_imagem)
            pen = QPen(QColor(255, 255, 255), 2, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.drawRect(self._retangulo)
            painter.end()

    def _atualizar_campos(self):
        self._x.setText(str(max(0, self._retangulo.x())))
        self._y.setText(str(max(0, self._retangulo.y())))
        self._w.setText(str(max(1, self._retangulo.width())))
        self._h.setText(str(max(1, self._retangulo.height())))

    def _campos_alterados(self):
        try:
            x = int(self._x.text() or 0)
            y = int(self._y.text() or 0)
            w = int(self._w.text() or 1)
            h = int(self._h.text() or 1)
            self._retangulo = QRect(x, y, w, h)
            self.visualizador._label_imagem.update()
        except ValueError:
            pass

    def _aplicar_recorte(self):
        try:
            x = max(0, int(self._x.text() or 0))
            y = max(0, int(self._y.text() or 0))
            w = int(self._w.text() or 1)
            h = int(self._h.text() or 1)

            if w <= 0 or h <= 0:
                QMessageBox.warning(self, "Erro", "Largura e altura devem ser maiores que zero.")
                return

            img_h, img_w = self.imagem_original.shape[:2]
            w = min(w, img_w - x)
            h = min(h, img_h - y)

            if w <= 0 or h <= 0:
                QMessageBox.warning(self, "Erro", "Seleção fora dos limites.")
                return

            crop = self.imagem_original[y:y+h, x:x+w].copy()
            self.apply_requested.emit(crop)
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao recortar: {e}")