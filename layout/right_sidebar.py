"""Barra lateral direita com painel de ajustes."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class RightSidebar(QFrame):
    """Widget da barra lateral direita com painel de ajustes."""

    ajuste_solicitado = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("rightSidebar")
        self.setFixedWidth(280)

        self._aplicar_estilo()
        self._construir_ui()

    def _aplicar_estilo(self) -> None:
        caminho_qss = Path(__file__).parent / "styles" / "right_sidebar.qss"
        if caminho_qss.exists():
            self.setStyleSheet(caminho_qss.read_text(encoding="utf-8"))

    def _construir_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._criar_painel_ajustes())

    def _criar_painel_ajustes(self) -> QWidget:
        container = QFrame(self)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(12, 10, 12, 10)
        container_layout.setSpacing(8)

        titulo = QLabel("Ajustes", container)
        titulo.setObjectName("rightSectionTitle")
        container_layout.addWidget(titulo)

        subtitulo = QLabel("Adicionar um ajuste", container)
        subtitulo.setObjectName("rightSubtleText")
        container_layout.addWidget(subtitulo)

        grade = QGridLayout()
        grade.setHorizontalSpacing(4)
        grade.setVerticalSpacing(4)

        ajustes = [
            ("brilho_contraste", "Brilho/Contraste", self._icone_svg_arquivo("brilho_contraste.svg")),
            ("preto_branco", "Preto e branco", self._icone_svg_arquivo("preto_branco.svg")),
            ("saturacao", "Saturação", self._icone_svg_arquivo("saturacao.svg")),
            ("ruido_salt_pepper", "Ruído Salt and Pepper", self._icone_png("saltandpepper.png")),
        ]

        for indice, (chave_ajuste, titulo_ajuste, icone) in enumerate(ajustes):
            botao = QToolButton(container)
            botao.setObjectName("adjustmentIconButton")
            botao.setToolTip(titulo_ajuste)
            botao.setIcon(icone)
            botao.setIconSize(QSize(18, 18))
            botao.setAutoRaise(True)
            botao.clicked.connect(
                lambda _checked=False, chave=chave_ajuste: self.ajuste_solicitado.emit(chave)
            )
            grade.addWidget(botao, indice // 5, indice % 5)

        container_layout.addLayout(grade)
        container_layout.addStretch()

        return container

    def _icone_svg_arquivo(self, nome_arquivo: str) -> QIcon:
        caminho_icone = Path(__file__).parent / "ui" / "icons" / nome_arquivo
        if caminho_icone.exists():
            return QIcon(str(caminho_icone))
        return QIcon()

    def _icone_png(self, nome_arquivo: str) -> QIcon:
        caminho_icone = Path(__file__).parent / "ui" / "icons" / nome_arquivo
        if caminho_icone.exists():
            return QIcon(str(caminho_icone))
        return QIcon()
