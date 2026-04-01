"""Componente de visualização com zoom no cursor e arrasto da imagem."""

from __future__ import annotations

from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QScrollArea, QSizePolicy


class VisualizadorImagem(QScrollArea):
    """Widget responsável por exibir imagem com zoom e arrasto."""

    zoom_alterado = Signal(float)

    _ZOOM_MINIMO = 0.10
    _ZOOM_MAXIMO = 8.00
    _FATOR_RODAS = 1.15
    _MAX_PIXELS_RENDER = 40_000_000

    def __init__(self, parent=None):
        super().__init__(parent)

        self._label_imagem = QLabel("Abra uma imagem para começar.", self)
        self._label_imagem.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label_imagem.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored
        )
        self._label_imagem.setScaledContents(True)

        self.setWidget(self._label_imagem)
        self.setWidgetResizable(False)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._pixmap_original: QPixmap | None = None
        self._zoom = 1.0
        self._espaco_pressionado = False
        self._arrastando = False
        self._ultima_posicao_mouse = None

    def possui_imagem(self) -> bool:
        return self._pixmap_original is not None

    def definir_pixmap(self, pixmap: QPixmap, resetar_zoom: bool = False) -> None:
        if pixmap.isNull():
            self._pixmap_original = None
            self._label_imagem.clear()
            self._label_imagem.setText("Imagem inválida.")
            self._label_imagem.adjustSize()
            self.horizontalScrollBar().setValue(0)
            self.verticalScrollBar().setValue(0)
            self._zoom = 1.0
            self.zoom_alterado.emit(self._zoom)
            return

        self._pixmap_original = pixmap
        self._label_imagem.setPixmap(self._pixmap_original)
        self._label_imagem.adjustSize()

        if resetar_zoom:
            self.ajustar_imagem_a_janela()
            return

        limite_superior = self._limite_zoom_superior()
        if self._zoom > limite_superior:
            self._definir_zoom_absoluto(limite_superior)
        else:
            self._atualizar_pixmap()

    def ajustar_imagem_a_janela(self) -> None:
        if self._pixmap_original is None:
            return

        largura_imagem = self._pixmap_original.width()
        altura_imagem = self._pixmap_original.height()
        if largura_imagem <= 0 or altura_imagem <= 0:
            self._definir_zoom_absoluto(1.0)
            return

        largura_viewport = max(1, self.viewport().width())
        altura_viewport = max(1, self.viewport().height())

        fator_largura = largura_viewport / largura_imagem
        fator_altura = altura_viewport / altura_imagem
        zoom_ajustado = min(fator_largura, fator_altura, 1.0)

        self._definir_zoom_absoluto(zoom_ajustado)

    def resetar_zoom(self) -> None:
        if self._pixmap_original is None:
            return
        self._definir_zoom_absoluto(1.0)

    def aumentar_zoom(self) -> None:
        centro = self.viewport().rect().center()
        self._aplicar_fator_zoom(self._FATOR_RODAS, centro)

    def diminuir_zoom(self) -> None:
        centro = self.viewport().rect().center()
        self._aplicar_fator_zoom(1 / self._FATOR_RODAS, centro)

    def definir_modo_arrasto(self, ativo: bool) -> None:
        self._espaco_pressionado = ativo
        if not ativo:
            self._arrastando = False
            self._ultima_posicao_mouse = None
            self.viewport().setCursor(Qt.CursorShape.ArrowCursor)
        elif self.possui_imagem():
            self.viewport().setCursor(Qt.CursorShape.OpenHandCursor)

    def wheelEvent(self, evento) -> None:
        if (
            evento.modifiers() & Qt.KeyboardModifier.ControlModifier
            and self._pixmap_original is not None
            and evento.angleDelta().y() != 0
        ):
            fator = self._FATOR_RODAS if evento.angleDelta().y() > 0 else 1 / self._FATOR_RODAS
            self._aplicar_fator_zoom(fator, evento.position())
            evento.accept()
            return

        super().wheelEvent(evento)

    def mousePressEvent(self, evento) -> None:
        if (
            self._espaco_pressionado
            and self._pixmap_original is not None
            and evento.button() == Qt.MouseButton.LeftButton
        ):
            self._arrastando = True
            self._ultima_posicao_mouse = evento.position()
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
            evento.accept()
            return

        super().mousePressEvent(evento)

    def mouseMoveEvent(self, evento) -> None:
        if self._arrastando and self._ultima_posicao_mouse is not None:
            delta = evento.position() - self._ultima_posicao_mouse
            self._ultima_posicao_mouse = evento.position()

            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - int(delta.x())
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - int(delta.y())
            )
            evento.accept()
            return

        super().mouseMoveEvent(evento)

    def mouseReleaseEvent(self, evento) -> None:
        if self._arrastando and evento.button() == Qt.MouseButton.LeftButton:
            self._arrastando = False
            self._ultima_posicao_mouse = None
            if self._espaco_pressionado and self.possui_imagem():
                self.viewport().setCursor(Qt.CursorShape.OpenHandCursor)
            else:
                self.viewport().setCursor(Qt.CursorShape.ArrowCursor)
            evento.accept()
            return

        super().mouseReleaseEvent(evento)

    def _definir_zoom_absoluto(self, zoom: float) -> None:
        novo_zoom = max(self._ZOOM_MINIMO, min(self._limite_zoom_superior(), zoom))
        if abs(novo_zoom - self._zoom) < 1e-6:
            return

        self._zoom = novo_zoom
        self._atualizar_pixmap()
        self.zoom_alterado.emit(self._zoom)

    def _aplicar_fator_zoom(self, fator: float, ancora_viewport) -> None:
        if self._pixmap_original is None:
            return

        zoom_antigo = self._zoom
        zoom_novo = max(
            self._ZOOM_MINIMO,
            min(self._limite_zoom_superior(), zoom_antigo * fator),
        )

        if abs(zoom_novo - zoom_antigo) < 1e-6:
            return

        barra_h = self.horizontalScrollBar()
        barra_v = self.verticalScrollBar()

        x_imagem = (barra_h.value() + ancora_viewport.x()) / zoom_antigo
        y_imagem = (barra_v.value() + ancora_viewport.y()) / zoom_antigo

        self._zoom = zoom_novo
        self._atualizar_pixmap()

        barra_h.setValue(int(x_imagem * zoom_novo - ancora_viewport.x()))
        barra_v.setValue(int(y_imagem * zoom_novo - ancora_viewport.y()))

        self.zoom_alterado.emit(self._zoom)

    def _atualizar_pixmap(self) -> None:
        if self._pixmap_original is None:
            return

        largura = max(1, int(self._pixmap_original.width() * self._zoom))
        altura = max(1, int(self._pixmap_original.height() * self._zoom))
        self._label_imagem.resize(largura, altura)

    def _limite_zoom_superior(self) -> float:
        if self._pixmap_original is None:
            return self._ZOOM_MAXIMO

        pixels_base = self._pixmap_original.width() * self._pixmap_original.height()
        if pixels_base <= 0:
            return self._ZOOM_MAXIMO

        # Mantém o consumo de memória sob controle em imagens grandes.
        limite_por_area = (self._MAX_PIXELS_RENDER / pixels_base) ** 0.5
        # Para imagens que já cabem no teto, mantém 100% sempre possível.
        if pixels_base <= self._MAX_PIXELS_RENDER:
            limite_por_area = max(1.0, limite_por_area)
        return max(self._ZOOM_MINIMO, min(self._ZOOM_MAXIMO, limite_por_area))
