"""Plugin de Reconhecimento Óptico de Caracteres (OCR)."""

from __future__ import annotations

import os
import cv2
import numpy as np
from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from core.plugin_base import PluginBase


def obter_caminho_tesseract() -> str | None:
    """Tenta localizar o executável do Tesseract OCR no Windows."""
    if os.name == "nt":
        caminhos_comuns = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]
        for caminho in caminhos_comuns:
            if os.path.exists(caminho):
                return caminho
    return None


class LeitorOCRWorker(QObject):
    """Worker que executa o OCR em background para evitar travamento da interface."""

    concluido = Signal(str)
    falhou = Signal(str)
    finalizado = Signal()

    def __init__(self, imagem: np.ndarray, tesseract_cmd: str | None = None):
        super().__init__()
        self._imagem = imagem.copy()
        self._tesseract_cmd = tesseract_cmd

    @Slot()
    def executar(self) -> None:
        try:
            import pytesseract

            if self._tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = self._tesseract_cmd

            # --- PRE-PROCESSAMENTO DO RECORTE ---
            # 1. Conversão para escala de cinza
            cinza = cv2.cvtColor(self._imagem, cv2.COLOR_RGB2GRAY)

            # 2. Redimensionamento se a imagem for muito pequena (melhora precisão)
            h, w = cinza.shape[:2]
            if h < 50 or w < 50:
                fator = max(2.0, 100.0 / min(h, w))
                cinza = cv2.resize(
                    cinza, (0, 0), fx=fator, fy=fator, interpolation=cv2.INTER_CUBIC
                )

            # 3. Limiarização de Otsu para binarização
            _, binarizada = cv2.threshold(
                cinza, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU
            )

            # --- OCR ---
            # Executa a leitura no recorte limiarizado
            texto = pytesseract.image_to_string(binarizada, lang="por+eng")
            self.concluido.emit(texto.strip())

        except ImportError:
            self.falhou.emit(
                "A biblioteca 'pytesseract' não está instalada no ambiente Python.\n\n"
                "Instale-a executando: pip install pytesseract"
            )
        except Exception as erro:
            self.falhou.emit(
                f"Erro ao executar o OCR: {erro}\n\n"
                "Certifique-se de que o Tesseract OCR está instalado no seu sistema "
                "e configurado corretamente no PATH."
            )
        finally:
            self.finalizado.emit()


class LeitorOCR(PluginBase):
    """Plugin de Reconhecimento Óptico de Caracteres usando ROI."""

    display_name = "Reconhecedor de Texto OCR"

    def setup_ui(self) -> None:
        self._parent_window = self.parent()
        self._recorte: np.ndarray | None = None
        self._thread_ocr: QThread | None = None
        self._worker_ocr: LeitorOCRWorker | None = None

        # 1. Validação do ROI (Região de Interesse)
        aba_atual = None
        if self._parent_window and hasattr(self._parent_window, "tabs"):
            aba_atual = self._parent_window.tabs.currentWidget()

        mascara = None
        if aba_atual and hasattr(aba_atual, "visualizador"):
            mascara = aba_atual.visualizador.mascara_atual

        if mascara is None:
            QMessageBox.warning(
                self,
                "OCR — Região não selecionada",
                "Nenhuma Região de Interesse (ROI) foi selecionada.\n\n"
                "Por favor, ative a ferramenta de seleção geométrica na barra lateral "
                "esquerda (ícone de retângulo), marque a área com texto na imagem "
                "e tente abrir este plugin novamente.",
            )
            from PySide6.QtCore import QTimer

            QTimer.singleShot(0, self.reject)

            # Layout minimalista temporário
            layout = QVBoxLayout(self)
            self.setLayout(layout)
            return

        # 2. Obtenção do recorte focado
        y_indices, x_indices = np.where(mascara == 255)
        if len(x_indices) > 0 and len(y_indices) > 0:
            x1, y1 = x_indices.min(), y_indices.min()
            x2, y2 = x_indices.max(), y_indices.max()
            w = x2 - x1 + 1
            h = y2 - y1 + 1
            self._recorte = self.imagem_original[y1 : y2 + 1, x1 : x2 + 1]
            self._roi_info = f"Região selecionada: {w}x{h} px (x: {x1}, y: {y1})"
        else:
            QMessageBox.warning(
                self,
                "OCR — Seleção inválida",
                "A seleção de região de interesse é inválida ou está vazia.",
            )
            from PySide6.QtCore import QTimer

            QTimer.singleShot(0, self.reject)

            layout = QVBoxLayout(self)
            self.setLayout(layout)
            return

        # 3. Configuração dos elementos da UI
        layout = QVBoxLayout(self)

        self._lbl_info = QLabel(self._roi_info, self)
        self._lbl_info.setStyleSheet("font-weight: bold; color: #4CAF50;")
        layout.addWidget(self._lbl_info)

        self._status = QLabel(
            'Clique em "Executar OCR" para reconhecer o texto da seleção.', self
        )
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._status)

        self._texto = QPlainTextEdit(self)
        self._texto.setReadOnly(True)
        self._texto.setPlaceholderText("O texto reconhecido aparecerá aqui.")
        self._texto.setMinimumHeight(120)
        layout.addWidget(self._texto)

        botoes = QHBoxLayout()
        self._btn_executar = QPushButton("Executar OCR", self)
        self._btn_copiar = QPushButton("Copiar Texto", self)
        self._btn_fechar = QPushButton("Fechar", self)

        self._btn_copiar.setEnabled(False)

        botoes.addWidget(self._btn_executar)
        botoes.addWidget(self._btn_copiar)
        botoes.addWidget(self._btn_fechar)
        layout.addLayout(botoes)

        self._btn_executar.clicked.connect(self._ao_executar_ocr)
        self._btn_copiar.clicked.connect(self._ao_copiar)
        self._btn_fechar.clicked.connect(self.reject)

        self.setLayout(layout)
        self.setMinimumWidth(450)

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        # O OCR lê o texto mas não altera os pixels da imagem no canvas
        return imagem.copy()

    def closeEvent(self, evento) -> None:
        if (
            self._thread_ocr is not None
            and self._thread_ocr.isRunning()
        ):
            self._status.setText("Aguarde a finalização do OCR.")
            evento.ignore()
            return
        super().closeEvent(evento)

    def _ao_executar_ocr(self) -> None:
        if self._recorte is None:
            return

        self._status.setText("Processando imagem e extraindo texto...")
        self._btn_executar.setEnabled(False)
        self._btn_copiar.setEnabled(False)
        self._texto.setPlainText("")

        self._thread_ocr = QThread(self)
        tesseract_cmd = obter_caminho_tesseract()

        self._worker_ocr = LeitorOCRWorker(self._recorte, tesseract_cmd)
        self._worker_ocr.moveToThread(self._thread_ocr)

        self._thread_ocr.started.connect(self._worker_ocr.executar)
        self._worker_ocr.concluido.connect(self._ao_ocr_concluido)
        self._worker_ocr.falhou.connect(self._ao_ocr_falhou)
        self._worker_ocr.finalizado.connect(self._thread_ocr.quit)
        self._worker_ocr.finalizado.connect(self._worker_ocr.deleteLater)

        self._thread_ocr.finished.connect(self._ao_thread_finalizada)
        self._thread_ocr.finished.connect(self._thread_ocr.deleteLater)

        self._thread_ocr.start()

    @Slot(str)
    def _ao_ocr_concluido(self, texto: str) -> None:
        if not texto:
            self._status.setText("OCR concluído: nenhum texto detectado.")
            self._texto.setPlainText("")
            QMessageBox.information(
                self, "OCR", "Nenhum texto foi reconhecido na região selecionada."
            )
            return

        self._status.setText("OCR concluído com sucesso.")
        self._texto.setPlainText(texto)
        self._btn_copiar.setEnabled(True)

        # Exibe caixa de mensagem com o texto e botão para copiar
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Texto Reconhecido (OCR)")
        msg.setText("O texto a seguir foi extraído:")
        msg.setDetailedText(texto)

        # Para facilitar a leitura direta, também configuramos a mensagem principal
        if len(texto) < 100:
            msg.setInformativeText(texto)

        btn_copiar = msg.addButton("Copiar", QMessageBox.ButtonRole.ActionRole)
        msg.addButton(QMessageBox.StandardButton.Ok)

        msg.exec()

        if msg.clickedButton() == btn_copiar:
            QApplication.clipboard().setText(texto)
            self._status.setText("Texto copiado para a área de transferência.")

    @Slot(str)
    def _ao_ocr_falhou(self, mensagem: str) -> None:
        self._status.setText("Ocorreu um erro no OCR.")
        QMessageBox.critical(self, "Falha no OCR", mensagem)

    @Slot()
    def _ao_thread_finalizada(self) -> None:
        self._thread_ocr = None
        self._worker_ocr = None
        self._btn_executar.setEnabled(True)

    def _ao_copiar(self) -> None:
        texto = self._texto.toPlainText()
        if texto:
            QApplication.clipboard().setText(texto)
            self._status.setText("Texto copiado para a área de transferência.")
