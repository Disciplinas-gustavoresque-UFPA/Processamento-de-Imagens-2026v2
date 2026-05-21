"""Barra lateral direita com painel de ajustes."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class BarraLateralDireita(QFrame):
    """Widget da barra lateral direita com painel de ajustes."""

    ajuste_solicitado = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("rightSidebar")

        self._largura_expandida = 280
        self._largura_encolhida = 28
        self._esta_encolhida = False
        self.setFixedWidth(self._largura_expandida)

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

        # Botão de encolher/expandir no canto superior esquerdo.
        header = QWidget(self)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(0)

        self._botao_toggle = QToolButton(header)
        self._botao_toggle.setObjectName("sidebarToggleButton")
        self._botao_toggle.setAutoRaise(True)
        self._botao_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self._botao_toggle.clicked.connect(self._alternar_colapso)
        header_layout.addWidget(self._botao_toggle)
        header_layout.addStretch(1)

        layout.addWidget(header)

        self._painel_ajustes = self._criar_painel_ajustes()
        layout.addWidget(self._painel_ajustes, 1)
        self._atualizar_botao_toggle()

    def _alternar_colapso(self) -> None:
        self._esta_encolhida = not self._esta_encolhida
        self._painel_ajustes.setVisible(not self._esta_encolhida)
        self.setFixedWidth(self._largura_encolhida if self._esta_encolhida else self._largura_expandida)
        self._atualizar_botao_toggle()

    def _atualizar_botao_toggle(self) -> None:
        if self._esta_encolhida:
            self._botao_toggle.setText("<")
            self._botao_toggle.setToolTip("Expandir barra lateral")
        else:
            self._botao_toggle.setText(">")
            self._botao_toggle.setToolTip("Encolher barra lateral")

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
