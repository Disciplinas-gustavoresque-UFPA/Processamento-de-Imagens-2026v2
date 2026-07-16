"""
Implementação do Filtro Fade que combina redução de saturação, suavização do contraste,
levantamento dos tons escuros e leve aumento de brilho.
"""

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

class FiltroFade(PluginBase):

    display_name = "Fade"

    _INTERVALO_PREVIEW_MS = 60

    _REDUCAO_MAXIMA_SATURACAO = 0.35
    _REDUCAO_MAXIMA_CONTRASTE = 0.25
    _LEVANTAMENTO_MAXIMO_PRETOS = 0.08
    _AUMENTO_MAXIMO_BRILHO = 0.05

    def setup_ui(self) -> None:
        layout_principal = QVBoxLayout(self)

        self._rotulo_intensidade = QLabel(
            "Intensidade do Fade: 50%",
            self,
        )
        self._rotulo_intensidade.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        layout_principal.addWidget(self._rotulo_intensidade)

        self._slider_intensidade = QSlider(
            Qt.Orientation.Horizontal,
            self,
        )
        self._slider_intensidade.setRange(0, 100)
        self._slider_intensidade.setValue(50)
        self._slider_intensidade.setTickInterval(10)
        self._slider_intensidade.setTickPosition(
            QSlider.TickPosition.TicksBelow
        )
        layout_principal.addWidget(self._slider_intensidade)

        descricao = QLabel(
            "Reduz suavemente a saturação e o contraste, "
            "eleva os tons escuros e aumenta levemente o brilho.",
            self,
        )
        descricao.setWordWrap(True)
        descricao.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_principal.addWidget(descricao)

        layout_botoes = QHBoxLayout()

        self._botao_aplicar = QPushButton("Aplicar", self)
        self._botao_cancelar = QPushButton("Cancelar", self)

        layout_botoes.addWidget(self._botao_aplicar)
        layout_botoes.addWidget(self._botao_cancelar)

        layout_principal.addLayout(layout_botoes)

        self._temporizador_preview = QTimer(self)
        self._temporizador_preview.setSingleShot(True)
        self._temporizador_preview.setInterval(
            self._INTERVALO_PREVIEW_MS
        )
        self._temporizador_preview.timeout.connect(
            self._emitir_preview
        )

        self._slider_intensidade.valueChanged.connect(
            self._ao_alterar_intensidade
        )
        self._botao_aplicar.clicked.connect(self._ao_aplicar)
        self._botao_cancelar.clicked.connect(self.reject)

        self.adjustSize(390)

    def _obter_intensidade(self) -> float:
        return self._slider_intensidade.value() / 100.0

    @staticmethod
    def _calcular_referencia_acromatica(
        imagem_normalizada: np.ndarray,
    ) -> np.ndarray:
        if imagem_normalizada.ndim != 3:
            return imagem_normalizada

        return np.mean(
            imagem_normalizada,
            axis=2,
            keepdims=True,
            dtype=np.float32,
        )

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        if imagem is None or imagem.size == 0:
            return imagem.copy()

        intensidade = self._obter_intensidade()

        if intensidade <= 0.0:
            return imagem.copy()

        imagem_normalizada = imagem.astype(np.float32) / 255.0

        referencia_acromatica = self._calcular_referencia_acromatica(
            imagem_normalizada
        )

        reducao_saturacao = (
            self._REDUCAO_MAXIMA_SATURACAO * intensidade
        )

        imagem_dessaturada = (
            imagem_normalizada * (1.0 - reducao_saturacao)
            + referencia_acromatica * reducao_saturacao
        )

        fator_contraste = (
            1.0
            - self._REDUCAO_MAXIMA_CONTRASTE * intensidade
        )

        imagem_contraste = (
            imagem_dessaturada - 0.5
        ) * fator_contraste + 0.5

        levantamento_pretos = (
            self._LEVANTAMENTO_MAXIMO_PRETOS * intensidade
        )

        imagem_com_pretos_elevados = (
            levantamento_pretos
            + imagem_contraste * (1.0 - levantamento_pretos)
        )

        aumento_brilho = (
            self._AUMENTO_MAXIMO_BRILHO * intensidade
        )

        imagem_final = (
            imagem_com_pretos_elevados
            + (1.0 - imagem_com_pretos_elevados)
            * aumento_brilho
        )

        imagem_final = np.clip(imagem_final, 0.0, 1.0)

        return np.rint(
            imagem_final * 255.0
        ).astype(np.uint8)

    def _ao_alterar_intensidade(self, valor: int) -> None:
        self._rotulo_intensidade.setText(
            f"Intensidade do Fade: {valor}%"
        )

        self._temporizador_preview.start()

    def _emitir_preview(self) -> None:
        imagem_processada = self.processar(
            self.imagem_original
        )

        self.preview_requested.emit(
            imagem_processada
        )

    def _ao_aplicar(self) -> None:
        self._temporizador_preview.stop()

        imagem_processada = self.processar(
            self.imagem_original
        )

        self.apply_requested.emit(
            imagem_processada
        )

        self.accept()
