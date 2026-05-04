"""Barra lateral esquerda (estilo Photoshop) com botões de ferramenta."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QByteArray, QPoint, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap, QPolygon
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QFrame, QMenu, QToolButton, QVBoxLayout, QWidget


class ZoomToolButton(QToolButton):
    """Botão de zoom com submenu no duplo clique e indicador triangular."""

    modo_zoom_alterado = Signal(str)

    def __init__(
        self,
        pasta_icones: Path,
        carregar_icone_branco: Callable[[Path], QIcon | None],
        carregar_icone_preto: Callable[[Path], QIcon | None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._pasta_icones = pasta_icones
        self._carregar_icone_branco = carregar_icone_branco
        self._carregar_icone_preto = carregar_icone_preto
        self._modo_zoom = "zoom"

        self._menu_zoom = QMenu(self)
        self._rotulos_modo = {
            "zoom": "Zoom",
            "zoom-in": "Aumentar zoom",
            "zoom-out": "Diminuir zoom",
        }
        self._ordem_modos = ["zoom", "zoom-in", "zoom-out"]
        self._definir_modo_zoom("zoom")

    def _definir_modo_zoom(self, modo: str) -> None:
        if modo not in self._rotulos_modo:
            return

        self._modo_zoom = modo
        caminho_icone = self._pasta_icones / f"{modo}.svg"
        icone = self._carregar_icone_branco(caminho_icone)
        if icone is not None:
            self.setIcon(icone)
            self.setIconSize(QSize(20, 20))
        self._atualizar_menu_zoom()
        self.modo_zoom_alterado.emit(self._modo_zoom)

    def _atualizar_menu_zoom(self) -> None:
        self._menu_zoom.clear()

        for modo in self._ordem_modos:
            if modo == self._modo_zoom:
                continue

            acao = self._menu_zoom.addAction(self._rotulos_modo[modo])
            icone = self._carregar_icone_preto(self._pasta_icones / f"{modo}.svg")
            if icone is not None:
                acao.setIcon(icone)
            acao.triggered.connect(lambda _checked=False, m=modo: self._definir_modo_zoom(m))

    def obter_modo_zoom(self) -> str:
        return self._modo_zoom

    def mouseDoubleClickEvent(self, evento) -> None:
        if evento.button() == Qt.MouseButton.LeftButton:
            ponto_menu = self.mapToGlobal(QPoint(self.width() - 2, self.height() - 2))
            self._menu_zoom.exec(ponto_menu)
            evento.accept()
            return
        super().mouseDoubleClickEvent(evento)

    def paintEvent(self, evento) -> None:
        super().paintEvent(evento)

        # Indicador de submenu no canto inferior direito do botao.
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#d9d9d9"))

        triangulo = QPolygon(
            [
                QPoint(self.width() - 9, self.height() - 4),
                QPoint(self.width() - 4, self.height() - 9),
                QPoint(self.width() - 3, self.height() - 3),
            ]
        )
        painter.drawPolygon(triangulo)
        painter.end()


class LeftToolbar(QFrame):
    """Widget reutilizavel para a barra lateral esquerda com icones."""

    ferramenta_alterada = Signal(str)
    modo_zoom_alterado = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("leftToolbar")
        self.setFixedWidth(52)

        self._aplicar_estilo()
        self._construir_ui()

    def _aplicar_estilo(self) -> None:
        caminho_qss = Path(__file__).parent / "styles" / "left_toolbar.qss"
        if caminho_qss.exists():
            self.setStyleSheet(caminho_qss.read_text(encoding="utf-8"))

    def _construir_ui(self) -> None:
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(6, 8, 6, 8)
        layout_principal.setSpacing(4)

        pasta_icones = Path(__file__).parent / "ui" / "icons"
        self._botoes_ferramenta: list[QToolButton] = []
        self._nomes_ferramenta: list[str] = []
        definicoes = [
            ("Mover", pasta_icones / "hand.svg", "H"),
            ("Zoom", pasta_icones / "zoom.svg", "Z"),
            ("Rotação", None, "R"),
        ]

        for indice, (nome, caminho_icone, fallback) in enumerate(definicoes):
            if nome == "Zoom":
                botao = self._criar_botao_zoom(pasta_icones, nome)
            else:
                botao = self._criar_botao(nome, caminho_icone, fallback)
            botao.setCheckable(True)
            botao.setChecked(indice == 0)
            botao.clicked.connect(lambda _checked, i=indice: self._ativar_somente(i))
            layout_principal.addWidget(botao, alignment=Qt.AlignmentFlag.AlignHCenter)
            self._botoes_ferramenta.append(botao)
            self._nomes_ferramenta.append(nome)

        layout_principal.addSpacing(12)
        layout_principal.addStretch(1)

    def _criar_botao(self, nome: str, caminho_icone: Path | None, fallback: str) -> QToolButton:
        botao = QToolButton(self)
        botao.setObjectName("toolButton")
        botao.setProperty("class", "toolButton")
        botao.setToolTip(nome)

        # Caso especial para rotação: gera SVG inline
        if nome == "Rotação":
            icone = self._icone_rotacao_espelhamento()
            if icone is not None:
                botao.setIcon(icone)
                botao.setIconSize(QSize(20, 20))
                return botao

        if caminho_icone is not None and caminho_icone.exists():
            icone = self._carregar_icone_branco(caminho_icone)
            if icone is not None:
                botao.setIcon(icone)
                botao.setIconSize(QSize(20, 20))
                return botao

        # Fallback visual quando a biblioteca de icones nao estiver disponivel.
        botao.setText(fallback)
        botao.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        return botao

    def _criar_botao_zoom(self, pasta_icones: Path, nome: str) -> QToolButton:
        botao = ZoomToolButton(
            pasta_icones,
            self._carregar_icone_branco,
            self._carregar_icone_preto,
            self,
        )
        botao.setObjectName("toolButton")
        botao.setProperty("class", "toolButton")
        botao.setToolTip(nome)
        botao.modo_zoom_alterado.connect(self._ao_modo_zoom_alterado)
        return botao

    def _ao_modo_zoom_alterado(self, modo: str) -> None:
        self.modo_zoom_alterado.emit(modo)

    def _carregar_icone_branco(self, caminho_icone: Path) -> QIcon | None:
        """Carrega um SVG local e força cor branca para combinar com o tema escuro."""
        try:
            conteudo_svg = caminho_icone.read_text(encoding="utf-8")
        except Exception:
            return None

        conteudo_svg = conteudo_svg.replace("currentColor", "#FFFFFF")
        renderer = QSvgRenderer(QByteArray(conteudo_svg.encode("utf-8")))
        if not renderer.isValid():
            return None

        pixmap = QPixmap(20, 20)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()

        return QIcon(pixmap)

    def _carregar_icone_preto(self, caminho_icone: Path) -> QIcon | None:
        """Carrega um SVG local e força cor preta para menus claros."""
        try:
            conteudo_svg = caminho_icone.read_text(encoding="utf-8")
        except Exception:
            return None

        conteudo_svg = conteudo_svg.replace("currentColor", "#000000")
        renderer = QSvgRenderer(QByteArray(conteudo_svg.encode("utf-8")))
        if not renderer.isValid():
            return None

        pixmap = QPixmap(20, 20)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()

        return QIcon(pixmap)

    def _icone_rotacao_espelhamento(self) -> QIcon | None:
        """Cria um ícone SVG para rotação/espelhamento."""
        svg = '<svg viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg"><path d="M4 10a6 6 0 1 0 12 0" fill="none" stroke="#FFFFFF" stroke-width="1.5"/><path d="M14 6 L16 10 L12 10" fill="#FFFFFF"/></svg>'
        renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
        if not renderer.isValid():
            return None

        pixmap = QPixmap(20, 20)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()

        return QIcon(pixmap)

    def _ativar_somente(self, indice_ativo: int) -> None:
        for indice, botao in enumerate(self._botoes_ferramenta):
            botao.setChecked(indice == indice_ativo)

        nome_ferramenta = self._nomes_ferramenta[indice_ativo].lower()
        self.ferramenta_alterada.emit(nome_ferramenta)

    def _criar_swatches(self) -> QWidget:
        container = QWidget(self)
        container.setFixedSize(28, 28)

        primaria = QFrame(container)
        primaria.setObjectName("swatchPrimary")
        primaria.setGeometry(0, 0, 20, 20)

        secundaria = QFrame(container)
        secundaria.setObjectName("swatchSecondary")
        secundaria.setGeometry(8, 8, 20, 20)

        return container
