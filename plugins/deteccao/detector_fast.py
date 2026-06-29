"""Plugin para deteccao de cantos com o algoritmo FAST."""

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
)

from core.plugin_base import PluginBase


class DetectorFAST(PluginBase):
    """Interface do detector de pontos de interesse FAST."""

    display_name = "Detector de Cantos (FAST)"

    def setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        descricao = QLabel(
            "Detecta cantos comparando cada pixel com os pixels de uma "
            "circunferência ao seu redor.",
            self,
        )
        descricao.setWordWrap(True)
        layout.addWidget(descricao)

        self._rotulo_limiar = QLabel("Limiar de intensidade: 20", self)
        layout.addWidget(self._rotulo_limiar)

        self._slider_limiar = QSlider(Qt.Orientation.Horizontal, self)
        self._slider_limiar.setRange(1, 255)
        self._slider_limiar.setValue(20)
        self._slider_limiar.setToolTip(
            "Valores menores detectam mais pontos; valores maiores exigem "
            "cantos com maior contraste."
        )
        layout.addWidget(self._slider_limiar)

        self._checkbox_nms = QCheckBox("Supressão de não-maximos", self)
        self._checkbox_nms.setChecked(True)
        self._checkbox_nms.setToolTip(
            "Mantem os pontos mais fortes quando ha varias deteccões próximas."
        )
        layout.addWidget(self._checkbox_nms)

        self._rotulo_quantidade = QLabel("Cantos detectados: 0", self)
        self._rotulo_quantidade.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._rotulo_quantidade)

        layout_botoes = QHBoxLayout()

        self._btn_aplicar = QPushButton("Aplicar", self)
        self._btn_cancelar = QPushButton("Cancelar", self)

        layout_botoes.addWidget(self._btn_aplicar)
        layout_botoes.addWidget(self._btn_cancelar)

        layout.addLayout(layout_botoes)

        self._slider_limiar.valueChanged.connect(self._ao_alterar_limiar)
        self._checkbox_nms.toggled.connect(self._atualizar_preview)
        self._btn_aplicar.clicked.connect(self._ao_aplicar)
        self._btn_cancelar.clicked.connect(self.reject)

        self.setMinimumWidth(360)

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        """Retorna uma copia da imagem original.
        """
        return imagem.copy()

    def _ao_alterar_limiar(self, valor: int) -> None:
        self._rotulo_limiar.setText(f"Limiar de intensidade: {valor}")
        self._atualizar_preview()

    def _atualizar_preview(self, _marcado: bool | None = None) -> None:
        if not hasattr(self, "imagem_original") or self.imagem_original is None:
            return

        imagem_processada = self.processar(self.imagem_original)
        self.preview_requested.emit(imagem_processada)

    def _ao_aplicar(self) -> None:
        if not hasattr(self, "imagem_original") or self.imagem_original is None:
            return

        imagem_processada = self.processar(self.imagem_original)
        self.apply_requested.emit(imagem_processada)
        self.accept()