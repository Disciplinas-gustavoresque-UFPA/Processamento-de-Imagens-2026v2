import numpy as np

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QLabel,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)

from core.plugin_base import PluginBase


class FiltroCanaisRGB(PluginBase):
    display_name = "Extração de Canais RGB"

    multiple_images_requested = Signal(list)

    def __init__(self, imagem_rgb: np.ndarray, parent=None):
        super().__init__(imagem_rgb, parent)

        self.imagem_rgb = imagem_rgb.copy()

        self.setWindowTitle("Extração de Canais RGB")

        layout = QVBoxLayout(self)

        descricao = QLabel(
            "Gera três imagens separadas a partir dos canais RGB:\n"
            "Canal vermelho, canal verde e canal azul."
        )
        layout.addWidget(descricao)

        self.radio_colorido = QRadioButton("Manter canal colorido e zerar os outros")
        self.radio_cinza = QRadioButton("Gerar canais em escala de cinza")

        self.radio_colorido.setChecked(True)

        grupo = QButtonGroup(self)
        grupo.addButton(self.radio_colorido)
        grupo.addButton(self.radio_cinza)

        layout.addWidget(self.radio_colorido)
        layout.addWidget(self.radio_cinza)

        botao_gerar = QPushButton("Gerar 3 imagens")
        botao_gerar.clicked.connect(self._gerar_canais)
        layout.addWidget(botao_gerar)

    def _gerar_canais(self) -> None:
        imagem = self.imagem_rgb[:, :, :3]

        if self.radio_cinza.isChecked():
            canais = self._gerar_canais_em_cinza(imagem)
        else:
            canais = self._gerar_canais_coloridos(imagem)

        self.multiple_images_requested.emit(canais)
        self.accept()

    def _gerar_canais_coloridos(
        self,
        imagem: np.ndarray,
    ) -> list[tuple[str, np.ndarray]]:
        canal_r = np.zeros_like(imagem)
        canal_g = np.zeros_like(imagem)
        canal_b = np.zeros_like(imagem)

        canal_r[:, :, 0] = imagem[:, :, 0]
        canal_g[:, :, 1] = imagem[:, :, 1]
        canal_b[:, :, 2] = imagem[:, :, 2]

        return [
            ("Canal R", canal_r),
            ("Canal G", canal_g),
            ("Canal B", canal_b),
        ]

    def _gerar_canais_em_cinza(
        self,
        imagem: np.ndarray,
    ) -> list[tuple[str, np.ndarray]]:
        canal_r = np.repeat(imagem[:, :, 0:1], 3, axis=2)
        canal_g = np.repeat(imagem[:, :, 1:2], 3, axis=2)
        canal_b = np.repeat(imagem[:, :, 2:3], 3, axis=2)

        return [
            ("Canal R Cinza", canal_r),
            ("Canal G Cinza", canal_g),
            ("Canal B Cinza", canal_b),
        ]