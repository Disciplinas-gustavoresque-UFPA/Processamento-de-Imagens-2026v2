import cv2
import numpy as np

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QSlider,
    QVBoxLayout,
)

from core.plugin_base import PluginBase


class FiltroLaplace(PluginBase):
    display_name = "Laplace"

    def setup_ui(self) -> None:
        layout_principal = QVBoxLayout(self)

        rotulo_modo = QLabel(
            "Modo do filtro:",
            self,
        )

        layout_principal.addWidget(
            rotulo_modo
        )

        self._grupo_opcoes = QButtonGroup(
            self
        )

        self._radios: dict[str, QRadioButton] = {}

        opcoes = [
            ("Sem Filtro", "sem_filtro"),
            ("Laplace", "laplace"),
        ]

        for texto, valor in opcoes:
            radio = QRadioButton(
                texto,
                self,
            )

            self._grupo_opcoes.addButton(
                radio
            )

            self._radios[valor] = radio

            layout_principal.addWidget(
                radio
            )

        self._radios[
            "sem_filtro"
        ].setChecked(True)

        self._rotulo_status = QLabel(
            "Filtro atual: Sem Filtro",
            self,
        )

        layout_principal.addWidget(
            self._rotulo_status
        )

        # Kernel
        rotulo_kernel = QLabel(
            "Tamanho do Kernel:",
            self,
        )

        layout_principal.addWidget(
            rotulo_kernel
        )

        self._grupo_kernel = QButtonGroup(
            self
        )

        self._radios_kernel: dict[
            int,
            QRadioButton
        ] = {}

        for ksize in (1, 3, 5, 7):
            radio = QRadioButton(
                f"{ksize}x{ksize}",
                self,
            )

            self._grupo_kernel.addButton(
                radio
            )

            self._radios_kernel[
                ksize
            ] = radio

            layout_principal.addWidget(
                radio
            )

        self._radios_kernel[
            3
        ].setChecked(True)

        # Intensidade
        rotulo_intensidade_titulo = QLabel(
            "Intensidade:",
            self,
        )

        layout_principal.addWidget(
            rotulo_intensidade_titulo
        )

        self._slider_intensidade = QSlider(
            Qt.Horizontal,
            self,
        )

        self._slider_intensidade.setMinimum(
            0
        )

        self._slider_intensidade.setMaximum(
            300
        )

        self._slider_intensidade.setValue(
            100
        )

        layout_principal.addWidget(
            self._slider_intensidade
        )

        self._rotulo_intensidade = QLabel(
            "100%",
            self,
        )

        layout_principal.addWidget(
            self._rotulo_intensidade
        )

        layout_botoes = QHBoxLayout()

        self._btn_aplicar = QPushButton(
            "Aplicar",
            self,
        )

        self._btn_cancelar = QPushButton(
            "Cancelar",
            self,
        )

        layout_botoes.addWidget(
            self._btn_aplicar
        )

        layout_botoes.addWidget(
            self._btn_cancelar
        )

        layout_principal.addLayout(
            layout_botoes
        )

        self._btn_aplicar.clicked.connect(
            self._ao_aplicar
        )

        self._btn_cancelar.clicked.connect(
            self.reject
        )

        for radio in self._radios.values():
            radio.toggled.connect(
                self._ao_mudar_opcao
            )

        for radio in self._radios_kernel.values():
            radio.toggled.connect(
                self._ao_mudar_kernel
            )

        self._slider_intensidade.valueChanged.connect(
            self._ao_mudar_intensidade
        )

        self.setLayout(
            layout_principal
        )

        self.setMinimumWidth(
            320
        )

        QTimer.singleShot(
            100,
            self._emitir_preview
        )

    def _obter_opcao(self) -> str:
        for valor, radio in (
            self._radios.items()
        ):
            if radio.isChecked():
                return valor

        return "sem_filtro"

    def _obter_intensidade(self) -> float:
        return (
            self._slider_intensidade.value()
            / 100.0
        )

    def _obter_kernel_size(self) -> int:
        for ksize, radio in (
            self._radios_kernel.items()
        ):
            if radio.isChecked():
                return ksize

        return 3

    def processar(
        self,
        imagem: np.ndarray
    ) -> np.ndarray:

        opcao = self._obter_opcao()

        if opcao == "sem_filtro":
            return imagem.copy()

        possui_alpha = (
            imagem.shape[2] == 4
            if len(imagem.shape) == 3
            else False
        )

        if possui_alpha:
            rgb = imagem[..., :3]
            alpha = imagem[..., 3]
        else:
            rgb = imagem

        cinza = cv2.cvtColor(
            rgb,
            cv2.COLOR_RGB2GRAY
        )

        laplace = cv2.Laplacian(
            cinza,
            cv2.CV_64F,
            ksize=self._obter_kernel_size()
        )

        laplace = cv2.convertScaleAbs(
            laplace,
            alpha=self._obter_intensidade()
        )

        resultado = cv2.cvtColor(
            laplace,
            cv2.COLOR_GRAY2RGB
        )

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

    def _ao_mudar_opcao(
        self,
        marcado: bool
    ) -> None:

        if not marcado:
            return

        opcao = self._obter_opcao()

        self._rotulo_status.setText(
            f"Filtro atual: {self._radios[opcao].text()}"
        )

        self._emitir_preview()

    def _ao_mudar_kernel(
        self,
        marcado: bool
    ) -> None:

        if not marcado:
            return

        self._emitir_preview()

    def _ao_mudar_intensidade(
        self,
        valor: int
    ) -> None:

        self._rotulo_intensidade.setText(
            f"{valor}%"
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