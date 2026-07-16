"""Barra lateral direita com painel de ajustes e estatísticas de compressão."""

from __future__ import annotations

from pathlib import Path
import numpy as np

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


def _formatar_tamanho(tamanho_bytes: int) -> str:
    """Converte bytes para uma string legível (B, KB, MB)."""
    if tamanho_bytes < 1024:
        return f"{tamanho_bytes} B"
    if tamanho_bytes < 1024 * 1024:
        return f"{tamanho_bytes / 1024:.2f} KB"
    return f"{tamanho_bytes / (1024 * 1024):.2f} MB"


class BarraLateralDireita(QFrame):
    """Widget da barra lateral direita com painel de ajustes e comparativo de compressão."""

    ajuste_solicitado = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("rightSidebar")

        self._largura_expandida = 280
        self._largura_encolhida = 28
        self._esta_encolhida = False
        self._imagem_atual: np.ndarray | None = None
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

        # Divisor
        divisor = QFrame(container)
        divisor.setFrameShape(QFrame.Shape.HLine)
        divisor.setObjectName("rightDivisor")
        container_layout.addWidget(divisor)

        # Seção de Compressão
        titulo_comp = QLabel("Comparativo de Compressão", container)
        titulo_comp.setObjectName("rightSectionTitle")
        container_layout.addWidget(titulo_comp)

        comp_frame = QFrame(container)
        comp_frame.setObjectName("compressionStatsFrame")
        comp_grid = QGridLayout(comp_frame)
        comp_grid.setContentsMargins(10, 10, 10, 10)
        comp_grid.setVerticalSpacing(8)
        comp_grid.setHorizontalSpacing(6)

        lbl_orig = QLabel("Original:", comp_frame)
        lbl_orig.setObjectName("compLabel")
        self.lbl_orig_val = QLabel("-", comp_frame)
        self.lbl_orig_val.setObjectName("compVal")
        self.lbl_orig_val.setAlignment(Qt.AlignmentFlag.AlignRight)

        lbl_huff = QLabel("Huffman:", comp_frame)
        lbl_huff.setObjectName("compLabel")
        self.lbl_huff_val = QLabel("-", comp_frame)
        self.lbl_huff_val.setObjectName("compVal")
        self.lbl_huff_val.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.lbl_huff_pct = QLabel("-", comp_frame)
        self.lbl_huff_pct.setObjectName("compPct")
        self.lbl_huff_pct.setAlignment(Qt.AlignmentFlag.AlignRight)

        lbl_jpeg = QLabel("JPEG:", comp_frame)
        lbl_jpeg.setObjectName("compLabel")
        self.lbl_jpeg_val = QLabel("-", comp_frame)
        self.lbl_jpeg_val.setObjectName("compVal")
        self.lbl_jpeg_val.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.lbl_jpeg_pct = QLabel("-", comp_frame)
        self.lbl_jpeg_pct.setObjectName("compPct")
        self.lbl_jpeg_pct.setAlignment(Qt.AlignmentFlag.AlignRight)

        lbl_png = QLabel("PNG:", comp_frame)
        lbl_png.setObjectName("compLabel")
        self.lbl_png_val = QLabel("-", comp_frame)
        self.lbl_png_val.setObjectName("compVal")
        self.lbl_png_val.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.lbl_png_pct = QLabel("-", comp_frame)
        self.lbl_png_pct.setObjectName("compPct")
        self.lbl_png_pct.setAlignment(Qt.AlignmentFlag.AlignRight)

        lbl_redundancy = QLabel("Redundância:", comp_frame)
        lbl_redundancy.setObjectName("compLabel")
        self.lbl_redundancy_val = QLabel("-", comp_frame)
        self.lbl_redundancy_val.setObjectName("compVal")
        self.lbl_redundancy_val.setAlignment(Qt.AlignmentFlag.AlignRight)

        comp_grid.addWidget(lbl_orig, 0, 0)
        comp_grid.addWidget(self.lbl_orig_val, 0, 1, 1, 2)

        comp_grid.addWidget(lbl_huff, 1, 0)
        comp_grid.addWidget(self.lbl_huff_val, 1, 1)
        comp_grid.addWidget(self.lbl_huff_pct, 1, 2)

        comp_grid.addWidget(lbl_jpeg, 2, 0)
        comp_grid.addWidget(self.lbl_jpeg_val, 2, 1)
        comp_grid.addWidget(self.lbl_jpeg_pct, 2, 2)

        comp_grid.addWidget(lbl_png, 3, 0)
        comp_grid.addWidget(self.lbl_png_val, 3, 1)
        comp_grid.addWidget(self.lbl_png_pct, 3, 2)

        comp_grid.addWidget(lbl_redundancy, 4, 0)
        comp_grid.addWidget(self.lbl_redundancy_val, 4, 1, 1, 2)

        container_layout.addWidget(comp_frame)

        self.btn_exportar = QPushButton("Exportar arquivo compactado (.huff)", container)
        self.btn_exportar.setObjectName("huffExportButton")
        self.btn_exportar.setEnabled(False)
        self.btn_exportar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_exportar.clicked.connect(self._exportar_huffman)
        container_layout.addWidget(self.btn_exportar)

        container_layout.addStretch()

        return container

    def atualizar_compressao(self, imagem_bgr: np.ndarray | None) -> None:
        """Calcula e atualiza as estatísticas de compressão da imagem atual."""
        self._imagem_atual = imagem_bgr
        if imagem_bgr is None:
            self.lbl_orig_val.setText("-")
            self.lbl_huff_val.setText("-")
            self.lbl_huff_pct.setText("-")
            self.lbl_jpeg_val.setText("-")
            self.lbl_jpeg_pct.setText("-")
            self.lbl_png_val.setText("-")
            self.lbl_png_pct.setText("-")
            self.lbl_redundancy_val.setText("-")
            self.btn_exportar.setEnabled(False)
            return

        try:
            from core.compressao_imagem import analisar_compressao

            res = analisar_compressao(imagem_bgr)
            tamanho_orig = res["tamanho_original"]

            self.lbl_orig_val.setText(_formatar_tamanho(tamanho_orig))

            # Huffman
            huff = res["huffman"]
            self.lbl_huff_val.setText(_formatar_tamanho(huff["tamanho_comprimido"]))
            self.lbl_huff_pct.setText(f"-{huff['economia_percentual']:.1f}%")
            self.lbl_redundancy_val.setText(f"{huff['redundancia'] * 100:.2f}%")

            # JPEG
            jpeg = res["jpeg"]
            self.lbl_jpeg_val.setText(_formatar_tamanho(jpeg["tamanho_comprimido"]))
            self.lbl_jpeg_pct.setText(f"-{jpeg['economia_percentual']:.1f}%")

            # PNG
            png = res["png"]
            self.lbl_png_val.setText(_formatar_tamanho(png["tamanho_comprimido"]))
            self.lbl_png_pct.setText(f"-{png['economia_percentual']:.1f}%")

            self.btn_exportar.setEnabled(True)
        except Exception as e:
            print(f"[Erro de análise de compressão] {e}")
            self.lbl_orig_val.setText("erro")

    def _exportar_huffman(self) -> None:
        if self._imagem_atual is None:
            return

        caminho, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar arquivo compactado",
            "",
            "Arquivo Huffman (*.huff)"
        )
        if not caminho:
            return

        try:
            from core.compressao_imagem import salvar_arquivo_huffman
            salvar_arquivo_huffman(self._imagem_atual, caminho)
            QMessageBox.information(
                self,
                "Sucesso",
                f"Arquivo compactado com sucesso!\nSalvo em: {caminho}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Erro",
                f"Erro ao salvar arquivo compactado:\n{e}"
            )

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
