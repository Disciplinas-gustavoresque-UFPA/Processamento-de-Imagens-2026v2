"""Plugin para detecção de cantos com o algoritmo FAST."""

import cv2
import numpy as np
from PySide6.QtCore import QTimer, Qt
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
    """Detecta e marca pontos de interesse FAST na imagem."""

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

        self._checkbox_nms = QCheckBox("Supressão de não-máximos", self)
        self._checkbox_nms.setChecked(True)
        self._checkbox_nms.setToolTip(
            "Mantém os pontos mais fortes quando há várias detecções próximas."
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

        QTimer.singleShot(0, self._atualizar_preview)

    def _detectar(self, imagem: np.ndarray) -> tuple[np.ndarray, int]:
        """Retorna uma cópia RGB anotada e a quantidade de cantos detectados."""
        if imagem.ndim == 3:
            cinza = cv2.cvtColor(imagem, cv2.COLOR_RGB2GRAY)
            resultado = imagem.copy()
        elif imagem.ndim == 2:
            cinza = imagem
            resultado = cv2.cvtColor(imagem, cv2.COLOR_GRAY2RGB)
        else:
            raise ValueError("A imagem deve possuir um canal ou três canais RGB.")

        detector = cv2.FastFeatureDetector_create(
            threshold=self._slider_limiar.value(),
            nonmaxSuppression=self._checkbox_nms.isChecked(),
            type=cv2.FAST_FEATURE_DETECTOR_TYPE_9_16,
        )

        pontos = detector.detect(cinza, None)

        imagem_anotada = cv2.drawKeypoints(
            resultado,
            pontos,
            None,
            color=(255, 0, 0),
            flags=cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS,
        )

        return imagem_anotada, len(pontos)

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        """Aplica o FAST e devolve a imagem RGB com os cantos marcados."""
        resultado, _ = self._detectar(imagem)
        return resultado

    def _atualizar_quantidade(self) -> np.ndarray:
        resultado, quantidade = self._detectar(self.imagem_original)
        self._rotulo_quantidade.setText(f"Cantos detectados: {quantidade}")
        return resultado

    def _ao_alterar_limiar(self, valor: int) -> None:
        self._rotulo_limiar.setText(f"Limiar de intensidade: {valor}")
        self._atualizar_preview()

    def _atualizar_preview(self, _marcado: bool | None = None) -> None:
        if not hasattr(self, "imagem_original") or self.imagem_original is None:
            return

        imagem_processada = self._atualizar_quantidade()
        self.preview_requested.emit(imagem_processada)

    def _ao_aplicar(self) -> None:
        if not hasattr(self, "imagem_original") or self.imagem_original is None:
            return

        imagem_processada = self._atualizar_quantidade()
        self.apply_requested.emit(imagem_processada)
        self.accept()