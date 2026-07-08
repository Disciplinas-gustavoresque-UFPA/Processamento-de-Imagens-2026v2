import cv2
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


class FiltroBilateral(PluginBase):
    """Filtro bilateral de preservação de bordas com parâmetros interativos."""

    display_name = "Filtro Bilateral"

    def setup_ui(self) -> None:
        layout_principal = QVBoxLayout(self)

        self._rotulo_diametro = QLabel("Diâmetro do kernel: 5", self)
        self._rotulo_diametro.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_principal.addWidget(self._rotulo_diametro)

        self._slider_diametro = QSlider(Qt.Orientation.Horizontal, self)
        self._slider_diametro.setRange(1, 13)
        self._slider_diametro.setValue(3)
        self._slider_diametro.setTickInterval(1)
        self._slider_diametro.setTickPosition(QSlider.TickPosition.TicksBelow)
        layout_principal.addWidget(self._slider_diametro)

        self._rotulo_sigma_cor = QLabel("Sigma de cor: 75", self)
        self._rotulo_sigma_cor.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_principal.addWidget(self._rotulo_sigma_cor)

        self._slider_sigma_cor = QSlider(Qt.Orientation.Horizontal, self)
        self._slider_sigma_cor.setRange(1, 200)
        self._slider_sigma_cor.setValue(75)
        self._slider_sigma_cor.setTickInterval(25)
        self._slider_sigma_cor.setTickPosition(QSlider.TickPosition.TicksBelow)
        layout_principal.addWidget(self._slider_sigma_cor)

        self._rotulo_sigma_espaco = QLabel("Sigma de espaço: 75", self)
        self._rotulo_sigma_espaco.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_principal.addWidget(self._rotulo_sigma_espaco)

        self._slider_sigma_espaco = QSlider(Qt.Orientation.Horizontal, self)
        self._slider_sigma_espaco.setRange(1, 200)
        self._slider_sigma_espaco.setValue(75)
        self._slider_sigma_espaco.setTickInterval(25)
        self._slider_sigma_espaco.setTickPosition(QSlider.TickPosition.TicksBelow)
        layout_principal.addWidget(self._slider_sigma_espaco)

        layout_botoes = QHBoxLayout()
        self._btn_aplicar = QPushButton("Aplicar", self)
        self._btn_cancelar = QPushButton("Cancelar", self)
        layout_botoes.addWidget(self._btn_aplicar)
        layout_botoes.addWidget(self._btn_cancelar)
        layout_principal.addLayout(layout_botoes)

        self._slider_diametro.valueChanged.connect(self._ao_mudar_parametros)
        self._slider_sigma_cor.valueChanged.connect(self._ao_mudar_parametros)
        self._slider_sigma_espaco.valueChanged.connect(self._ao_mudar_parametros)
        self._btn_aplicar.clicked.connect(self._ao_aplicar)
        self._btn_cancelar.clicked.connect(self.reject)

        self.setLayout(layout_principal)
        self.setMinimumWidth(360)

        QTimer.singleShot(100, self._emitir_preview)

    def _diametro(self) -> int:
        return 2 * self._slider_diametro.value() - 1

    def _sigma_cor(self) -> float:
        return float(self._slider_sigma_cor.value())

    def _sigma_espaco(self) -> float:
        return float(self._slider_sigma_espaco.value())

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        diametro = self._diametro()
        sigma_cor = self._sigma_cor()
        sigma_espaco = self._sigma_espaco()

        imagem_saida = np.empty_like(imagem)
        for canal in range(imagem.shape[-1]):
            imagem_saida[..., canal] = cv2.bilateralFilter(
                imagem[..., canal], diametro, sigma_cor, sigma_espaco
            )

        return imagem_saida

    def _emitir_preview(self) -> None:
        self._atualizar_rotulos()
        imagem_processada = self.processar(self.imagem_original)
        self.preview_requested.emit(imagem_processada)

    def _ao_mudar_parametros(self, _valor: int) -> None:
        self._atualizar_rotulos()
        imagem_processada = self.processar(self.imagem_original)
        self.preview_requested.emit(imagem_processada)

    def _atualizar_rotulos(self) -> None:
        self._rotulo_diametro.setText(f"Diâmetro do kernel: {self._diametro()}")
        self._rotulo_sigma_cor.setText(f"Sigma de cor: {self._sigma_cor():.0f}")
        self._rotulo_sigma_espaco.setText(f"Sigma de espaço: {self._sigma_espaco():.0f}")

    def _ao_aplicar(self) -> None:
        imagem_processada = self.processar(self.imagem_original)
        self.apply_requested.emit(imagem_processada)
        self.accept()

 