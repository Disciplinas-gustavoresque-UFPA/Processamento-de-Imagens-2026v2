import cv2
import numpy as np

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)

from core.plugin_base import PluginBase


class FiltroBinario(PluginBase):
    display_name = "Binário"

    def setup_ui(self) -> None:
        layout_principal = QVBoxLayout(self)

        rotulo_modo = QLabel("Modo do filtro:", self)
        layout_principal.addWidget(rotulo_modo)

        self._grupo_opcoes = QButtonGroup(self)
        self._radios: dict[str, QRadioButton] = {}

        opcoes = [
            ("Sem Filtro", "sem_filtro"),
            ("Binário", "binario"),
            ("Binário Otsu", "otsu"),
        ]

        for texto, valor in opcoes:
            radio = QRadioButton(texto, self)

            self._grupo_opcoes.addButton(radio)
            self._radios[valor] = radio

            layout_principal.addWidget(radio)

        self._radios["sem_filtro"].setChecked(True)

        self._rotulo_status = QLabel(
            "Filtro atual: Sem Filtro",
            self,
        )

        layout_principal.addWidget(self._rotulo_status)

        layout_botoes = QHBoxLayout()

        self._btn_aplicar = QPushButton("Aplicar", self)
        self._btn_cancelar = QPushButton("Cancelar", self)

        layout_botoes.addWidget(self._btn_aplicar)
        layout_botoes.addWidget(self._btn_cancelar)

        layout_principal.addLayout(layout_botoes)

        self._btn_aplicar.clicked.connect(self._ao_aplicar)
        self._btn_cancelar.clicked.connect(self.reject)

        for radio in self._radios.values():
            radio.toggled.connect(self._ao_mudar_opcao)

        self.setLayout(layout_principal)
        self.setMinimumWidth(320)

        # força preview após renderização da janela
        QTimer.singleShot(100, self._emitir_preview)

    def _obter_opcao(self) -> str:
        for valor, radio in self._radios.items():
            if radio.isChecked():
                return valor

        return "sem_filtro"

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        opcao = self._obter_opcao()

        if opcao == "sem_filtro":
            return imagem.copy()

        possui_alpha = (
            len(imagem.shape) == 3
            and imagem.shape[2] == 4
        )

        if possui_alpha:
            rgb = imagem[..., :3]
            alpha = imagem[..., 3]
        else:
            rgb = imagem

        # Converte para escala de cinza
        cinza = cv2.cvtColor(
            rgb,
            cv2.COLOR_RGB2GRAY
        )

        if opcao == "binario":
            _, resultado_binario = cv2.threshold(
                cinza,
                127,
                255,
                cv2.THRESH_BINARY
            )

        elif opcao == "otsu":
            _, resultado_binario = cv2.threshold(
                cinza,
                0,
                255,
                cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )

        else:
            return imagem.copy()

        # Converte de volta para RGB
        resultado = cv2.cvtColor(
            resultado_binario,
            cv2.COLOR_GRAY2RGB
        )

        # Reanexa alpha se existir
        if possui_alpha:
            resultado = np.dstack(
                (resultado, alpha)
            )

        return resultado

    def _emitir_preview(self) -> None:
        imagem_processada = self.processar(
            self.imagem_original
        )

        self.preview_requested.emit(
            imagem_processada
        )

    def _ao_mudar_opcao(self, marcado: bool) -> None:
        if not marcado:
            return

        opcao = self._obter_opcao()

        self._rotulo_status.setText(
            f"Filtro atual: {self._radios[opcao].text()}"
        )

        self._emitir_preview()

    def _ao_aplicar(self) -> None:
        imagem_processada = self.processar(
            self.imagem_original
        )

        self.preview_requested.emit(
            imagem_processada
        )

        self.apply_requested.emit(
            imagem_processada
        )

        self.accept()