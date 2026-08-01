import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from core.plugin_base import PluginBase


class RotacaoAngulo(PluginBase):
    """Plugin para rotacionar a imagem em um ângulo definido pelo usuário."""

    display_name = "Rotação em Ângulo"

    def setup_ui(self) -> None:
        layout_principal = QVBoxLayout(self)

        rotulo = QLabel("Informe o ângulo de rotação:", self)
        rotulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_principal.addWidget(rotulo)

        self._campo_angulo = QDoubleSpinBox(self)
        self._campo_angulo.setMinimum(-360.0)
        self._campo_angulo.setMaximum(360.0)
        self._campo_angulo.setValue(0.0)
        self._campo_angulo.setSingleStep(1.0)
        self._campo_angulo.setSuffix("°")
        layout_principal.addWidget(self._campo_angulo)

        layout_botoes = QHBoxLayout()
        self._btn_aplicar = QPushButton("Aplicar", self)
        self._btn_cancelar = QPushButton("Cancelar", self)

        layout_botoes.addWidget(self._btn_aplicar)
        layout_botoes.addWidget(self._btn_cancelar)
        layout_principal.addLayout(layout_botoes)

        self._campo_angulo.valueChanged.connect(self._ao_mudar_angulo)
        self._btn_aplicar.clicked.connect(self._ao_aplicar)
        self._btn_cancelar.clicked.connect(self.reject)

        self.setLayout(layout_principal)
        self.setMinimumWidth(320)

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        angulo = np.deg2rad(self._campo_angulo.value())

        altura, largura = imagem.shape[:2]
        centro_x = largura / 2
        centro_y = altura / 2

        resultado = np.zeros_like(imagem)

        cos_a = np.cos(angulo)
        sin_a = np.sin(angulo)

        for y in range(altura):
            for x in range(largura):
                x_c = x - centro_x
                y_c = y - centro_y

                origem_x = cos_a * x_c + sin_a * y_c + centro_x
                origem_y = -sin_a * x_c + cos_a * y_c + centro_y

                origem_x = int(round(origem_x))
                origem_y = int(round(origem_y))

                if 0 <= origem_x < largura and 0 <= origem_y < altura:
                    resultado[y, x] = imagem[origem_y, origem_x]

        return resultado

    def _ao_mudar_angulo(self, _valor: float) -> None:
        imagem_processada = self.processar(self.imagem_original)
        self.preview_requested.emit(imagem_processada)

    def _ao_aplicar(self) -> None:
        imagem_processada = self.processar(self.imagem_original)
        self.apply_requested.emit(imagem_processada)
        self.accept()