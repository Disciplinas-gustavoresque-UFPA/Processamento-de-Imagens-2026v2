import numpy as np

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
)

from core.plugin_base import PluginBase


class FiltroGama(PluginBase):
    """Correção Gama: ajuste tonal não-linear ``saida = 255 * (entrada/255) ** (1/gama)``.

    gama > 1 clareia as sombras; gama < 1 escurece; gama = 1 não altera.
    """

    display_name = "Correção Gama"

    def setup_ui(self) -> None:
        layout_principal = QVBoxLayout(self)

        rotulo_titulo = QLabel("Gama:", self)
        layout_principal.addWidget(rotulo_titulo)

        self._slider = QSlider(Qt.Orientation.Horizontal, self)
        self._slider.setRange(10, 300)
        self._slider.setValue(100)
        layout_principal.addWidget(self._slider)

        self._rotulo_status = QLabel("Gama: 1.00 (sem alteração)", self)
        layout_principal.addWidget(self._rotulo_status)

        layout_botoes = QHBoxLayout()

        self._btn_aplicar = QPushButton("Aplicar", self)
        self._btn_cancelar = QPushButton("Cancelar", self)

        layout_botoes.addWidget(self._btn_aplicar)
        layout_botoes.addWidget(self._btn_cancelar)

        layout_principal.addLayout(layout_botoes)

        self._slider.valueChanged.connect(self._ao_mudar_gama)
        self._btn_aplicar.clicked.connect(self._ao_aplicar)
        self._btn_cancelar.clicked.connect(self.reject)

        self.setLayout(layout_principal)
        self.setMinimumWidth(320)

        QTimer.singleShot(100, self._emitir_preview)

    def _gama(self) -> float:
        return self._slider.value() / 100.0

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        gama = self._gama()

        indices = np.arange(256, dtype=np.float32) / 255.0
        lut = np.clip(np.power(indices, 1.0 / gama) * 255.0, 0, 255).astype(np.uint8)

        imagem_saida = imagem.copy()
        imagem_saida[..., :3] = lut[imagem_saida[..., :3]]

        return imagem_saida

    def _emitir_preview(self) -> None:
        imagem_processada = self.processar(self.imagem_original)

        self.preview_requested.emit(imagem_processada)

    def _ao_mudar_gama(self, valor: int) -> None:
        gama = valor / 100.0

        if valor == 100:
            self._rotulo_status.setText("Gama: 1.00 (sem alteração)")
        else:
            self._rotulo_status.setText(f"Gama: {gama:.2f}")

        self._emitir_preview()

    def _ao_aplicar(self) -> None:
        imagem_processada = self.processar(self.imagem_original)

        self.preview_requested.emit(imagem_processada)
        self.apply_requested.emit(imagem_processada)

        self.accept()
