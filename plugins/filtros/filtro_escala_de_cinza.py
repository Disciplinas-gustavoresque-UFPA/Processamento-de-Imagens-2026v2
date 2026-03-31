import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)

from core.plugin_base import PluginBase


class FiltroEscalaDeCinza(PluginBase):
    display_name = "Escala de Cinza"

    def setup_ui(self) -> None:
        layout_principal = QVBoxLayout(self)

        rotulo_metodo = QLabel("Método de conversao:", self)
        layout_principal.addWidget(rotulo_metodo)

        self._grupo_metodos = QButtonGroup(self)
        self._radios_metodo: dict[str, QRadioButton] = {}

        opcoes = [
            ("Média RGB", "media"),
            ("Canal R", "r"),
            ("Canal G", "g"),
            ("Canal B", "b"),
            ("Canal L (HSL)", "hsl_l"),
            ("Canal B (HSB)", "hsb_b"),
        ]

        for texto, valor in opcoes:
            radio = QRadioButton(texto, self)
            self._grupo_metodos.addButton(radio)
            self._radios_metodo[valor] = radio
            layout_principal.addWidget(radio)

        self._radios_metodo["media"].setChecked(True)

        self._rotulo_metodo_atual = QLabel("Conversão atual: Média RGB", self)
        self._rotulo_metodo_atual.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_principal.addWidget(self._rotulo_metodo_atual)

        layout_botoes = QHBoxLayout()
        self._btn_aplicar = QPushButton("Aplicar", self)
        self._btn_cancelar = QPushButton("Cancelar", self)
        self._btn_aplicar.setAutoDefault(False)
        self._btn_aplicar.setDefault(False)
        self._btn_cancelar.setAutoDefault(False)
        self._btn_cancelar.setDefault(False)
        layout_botoes.addWidget(self._btn_aplicar)
        layout_botoes.addWidget(self._btn_cancelar)
        layout_principal.addLayout(layout_botoes)

        for radio in self._radios_metodo.values():
            radio.toggled.connect(self._ao_mudar_metodo)

        self._btn_aplicar.clicked.connect(self._ao_aplicar)
        self._btn_cancelar.clicked.connect(self.reject)

        self.setLayout(layout_principal)
        self.setMinimumWidth(320)

        self._ao_mudar_metodo(True)

    def _obter_metodo(self) -> str:
        for valor, radio in self._radios_metodo.items():
            if radio.isChecked():
                return valor
        return "media"

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        imagem_float = imagem.astype(np.float32)
        metodo = self._obter_metodo()

        r = imagem_float[..., 0]
        g = imagem_float[..., 1]
        b = imagem_float[..., 2]

        if metodo == "r":
            cinza = r
        elif metodo == "g":
            cinza = g
        elif metodo == "b":
            cinza = b
        elif metodo == "media":
            cinza = (r + g + b) / 3.0
        elif metodo == "hsl_l":
            cinza = (np.maximum.reduce([r, g, b]) + np.minimum.reduce([r, g, b])) / 2.0
        elif metodo == "hsb_b":
            cinza = np.maximum.reduce([r, g, b])
        else:
            cinza = (r + g + b) / 3.0

        canal = np.rint(cinza).astype(np.uint8)
        return np.stack((canal, canal, canal), axis=-1)

    def _ao_mudar_metodo(self, marcado: bool) -> None:
        if not marcado:
            return

        metodo = self._obter_metodo()
        self._rotulo_metodo_atual.setText(
            f"Conversao atual: {self._radios_metodo[metodo].text()}"
        )
        imagem_processada = self.processar(self.imagem_original)
        self.preview_requested.emit(imagem_processada)

    def _ao_aplicar(self) -> None:
        imagem_processada = self.processar(self.imagem_original)
        self.apply_requested.emit(imagem_processada)
        self.accept()