"""Plugin de leitura de QR Code."""

from __future__ import annotations

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
from plugins.reconhecimento._qrcode.decoder import QRDecodeError
from plugins.reconhecimento._qrcode.modelos import QRReadResult
from plugins.reconhecimento._qrcode.reader import QRProcessingCache, QRReader


class LeitorQRWorker(QObject):
    """Worker que executa a leitura de QR Code fora da thread da interface."""

    concluido = Signal(list)
    falhou = Signal(str)
    finalizado = Signal()

    def __init__(
        self,
        imagem: np.ndarray,
        max_versao: int = 40,
        cache: QRProcessingCache | None = None,
    ):
        super().__init__()
        self._imagem = imagem.copy()
        self._max_versao = max_versao
        self._cache = cache

    @Slot()
    def executar(self) -> None:
        try:
            resultados = QRReader(
                max_versao=self._max_versao,
                cache=self._cache,
            ).ler_todos(self._imagem)
            self.concluido.emit(resultados)
        except QRDecodeError as erro:
            self.falhou.emit(str(erro))
        except Exception as erro:
            self.falhou.emit(f"Erro inesperado ao ler o QR Code: {erro}")
        finally:
            self.finalizado.emit()


class LeitorQRCode(PluginBase):
    """Leitor de QR Code com detecção e decodificação."""

    display_name = "Leitor de QR Code"

    def setup_ui(self) -> None:
        self._resultado_imagem: np.ndarray | None = None
        self._texto_lido = ""
        self._thread_leitura: QThread | None = None
        self._worker_leitura: LeitorQRWorker | None = None
        self._cache_leitura = QRProcessingCache(max_entradas=4)

        layout = QVBoxLayout(self)

        self._status = QLabel('Clique em "Ler QR Code" para iniciar.', self)
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._status)

        self._texto = QPlainTextEdit(self)
        self._texto.setReadOnly(True)
        self._texto.setPlaceholderText("O texto decodificado aparecerá aqui.")
        self._texto.setMinimumHeight(100)
        layout.addWidget(self._texto)

        botoes = QHBoxLayout()
        self._btn_ler = QPushButton("Ler QR Code", self)
        self._btn_copiar = QPushButton("Copiar texto", self)

        self._btn_copiar.setEnabled(False)

        botoes.addWidget(self._btn_ler)
        botoes.addWidget(self._btn_copiar)
        layout.addLayout(botoes)

        self._btn_ler.clicked.connect(self._ao_ler)
        self._btn_copiar.clicked.connect(self._ao_copiar)

        self.setLayout(layout)
        self.setMinimumWidth(520)

    def closeEvent(self, evento) -> None:
        if self._thread_leitura is not None and self._thread_leitura.isRunning():
            self._status.setText("Aguarde a leitura do QR Code terminar.")
            evento.ignore()
            return

        super().closeEvent(evento)

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        """Retorna a imagem anotada quando houver leitura bem-sucedida."""
        if self._resultado_imagem is not None:
            return self._resultado_imagem
        return imagem.copy()

    def _ao_ler(self) -> None:
        self._status.setText("Processando hipóteses de QR Code...")
        self._btn_ler.setEnabled(False)
        self._btn_copiar.setEnabled(False)
        self._texto.setPlainText("")
        self._resultado_imagem = None
        self._texto_lido = ""

        self._thread_leitura = QThread(self)
        self._worker_leitura = LeitorQRWorker(
            self.imagem_original,
            cache=self._cache_leitura,
        )
        self._worker_leitura.moveToThread(self._thread_leitura)

        self._thread_leitura.started.connect(self._worker_leitura.executar)
        self._worker_leitura.concluido.connect(self._ao_leitura_concluida)
        self._worker_leitura.falhou.connect(self._ao_leitura_falhou)
        self._worker_leitura.finalizado.connect(self._thread_leitura.quit)
        self._worker_leitura.finalizado.connect(self._worker_leitura.deleteLater)
        self._thread_leitura.finished.connect(self._ao_thread_finalizada)
        self._thread_leitura.finished.connect(self._thread_leitura.deleteLater)
        self._thread_leitura.start()

    @Slot(list)
    def _ao_leitura_concluida(self, resultados: list[QRReadResult]) -> None:
        textos = [resultado.text for resultado in resultados]
        self._resultado_imagem = resultados[0].annotated_image
        self._texto_lido = _formatar_textos_lidos(textos)
        self._texto.setPlainText(self._texto_lido)

        if len(resultados) == 1:
            self._status.setText("QR Code lido com sucesso.")
        else:
            self._status.setText(f"{len(resultados)} QR Codes lidos com sucesso.")

        self.preview_requested.emit(resultados[0].annotated_image)
        self._btn_copiar.setEnabled(True)

    @Slot(str)
    def _ao_leitura_falhou(self, mensagem: str) -> None:
        self._status.setText("QR Code não lido.")
        self._texto.setPlainText("")
        self._resultado_imagem = None
        self._texto_lido = ""
        self._btn_copiar.setEnabled(False)
        QMessageBox.warning(self, "Leitor de QR Code", mensagem)

    @Slot()
    def _ao_thread_finalizada(self) -> None:
        self._thread_leitura = None
        self._worker_leitura = None
        self._btn_ler.setEnabled(True)

    def _ao_copiar(self) -> None:
        if self._texto_lido:
            QApplication.clipboard().setText(self._texto_lido)
            self._status.setText("Texto copiado para a área de transferência.")


def _formatar_textos_lidos(textos: list[str]) -> str:
    if len(textos) == 1:
        return textos[0]
    return "\n".join(f"{indice}. {texto}" for indice, texto in enumerate(textos, 1))
