"""Ajuste de temperatura de cor compatível com ``gegl:color-temperature``."""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
)

from core.plugin_base import PluginBase


_TEMPERATURA_MINIMA = 1000
_TEMPERATURA_MAXIMA = 12000
_TEMPERATURA_PADRAO = 6500

# Coeficientes atuais do GEGL para aproximar o locus planckiano em RGB linear
# com primárias BT.709/sRGB.
_COEFICIENTES_RGB_R55 = np.array(
    [
        [
            6.9389923563552169e-01,
            2.7719388100974670e03,
            2.0999316761104289e07,
            -4.8889434162208414e09,
            -1.1899785506796783e07,
            -4.7418427686099203e04,
            1.0,
            3.5434394338546258e03,
            -5.6159353379127791e05,
            2.7369467137870544e08,
            1.6295814912940913e08,
            4.3975072422421846e05,
        ],
        [
            9.5417426141210926e-01,
            2.2041043287098860e03,
            -3.0142332673634286e06,
            -3.5111986367681120e03,
            -5.7030969525354260e00,
            6.1810926909962016e-01,
            1.0,
            1.3728609973644000e03,
            1.3099184987576159e06,
            -2.1757404458816318e03,
            -2.3892456292510311e00,
            8.1079012401293249e-01,
        ],
        [
            -7.1151622540856201e10,
            3.3728185802339764e16,
            -7.9396187338868539e19,
            2.9699115135330123e22,
            -9.7520399221734228e22,
            -2.9250107732225114e20,
            1.0,
            1.3888666482167408e16,
            2.3899765140914549e19,
            1.4583606312383295e23,
            1.9766018324502894e22,
            2.9395068478016189e18,
        ],
    ],
    dtype=np.float64,
)


def _temperatura_para_rgb_linear(temperatura: float) -> np.ndarray:
    """Avalia a aproximação racional de grau 5 utilizada pelo GEGL."""
    temperatura = float(
        np.clip(temperatura, _TEMPERATURA_MINIMA, _TEMPERATURA_MAXIMA)
    )
    rgb = np.empty(3, dtype=np.float64)

    for canal, coeficientes in enumerate(_COEFICIENTES_RGB_R55):
        numerador = coeficientes[0]
        for coeficiente in coeficientes[1:6]:
            numerador = numerador * temperatura + coeficiente

        denominador = coeficientes[6]
        for coeficiente in coeficientes[7:12]:
            denominador = denominador * temperatura + coeficiente

        rgb[canal] = numerador / denominador

    return rgb


def _fatores_temperatura(
    temperatura_original: float,
    temperatura_pretendida: float,
) -> np.ndarray:
    original_rgb = _temperatura_para_rgb_linear(temperatura_original)
    pretendida_rgb = _temperatura_para_rgb_linear(temperatura_pretendida)
    return original_rgb / pretendida_rgb


def _construir_lut_srgb_para_linear() -> np.ndarray:
    valores = np.arange(256, dtype=np.float64) / 255.0
    return np.where(
        valores <= 0.04045,
        valores / 12.92,
        ((valores + 0.055) / 1.055) ** 2.4,
    )


_LUT_SRGB_PARA_LINEAR = _construir_lut_srgb_para_linear()


def _linear_para_srgb(valores: np.ndarray) -> np.ndarray:
    valores = np.clip(valores, 0.0, 1.0)
    return np.where(
        valores <= 0.0031308,
        valores * 12.92,
        1.055 * np.power(valores, 1.0 / 2.4) - 0.055,
    )


class FiltroTemperaturaCor(PluginBase):
    """Altera a temperatura de cor seguindo a operação atual do GEGL/GIMP."""

    display_name = "Temperatura de Cores"
    _INTERVALO_PREVIEW_MS = 50

    def setup_ui(self) -> None:
        layout_principal = QVBoxLayout(self)

        (
            self._temperatura_original,
            self._slider_temperatura_original,
        ) = self._adicionar_controle_temperatura(
            layout_principal,
            "Temperatura original:",
        )
        (
            self._temperatura_pretendida,
            self._slider_temperatura_pretendida,
        ) = self._adicionar_controle_temperatura(
            layout_principal,
            "Temperatura pretendida:",
        )

        layout_botoes = QHBoxLayout()
        self._btn_aplicar = QPushButton("Aplicar", self)
        self._btn_cancelar = QPushButton("Cancelar", self)
        layout_botoes.addWidget(self._btn_aplicar)
        layout_botoes.addWidget(self._btn_cancelar)
        layout_principal.addLayout(layout_botoes)

        self._timer_preview = QTimer(self)
        self._timer_preview.setSingleShot(True)
        self._timer_preview.setInterval(self._INTERVALO_PREVIEW_MS)
        self._timer_preview.timeout.connect(self._emitir_preview)

        self._slider_temperatura_original.valueChanged.connect(
            self._temperatura_original.setValue
        )
        self._slider_temperatura_pretendida.valueChanged.connect(
            self._temperatura_pretendida.setValue
        )
        self._temperatura_original.valueChanged.connect(
            self._slider_temperatura_original.setValue
        )
        self._temperatura_pretendida.valueChanged.connect(
            self._slider_temperatura_pretendida.setValue
        )
        self._temperatura_original.valueChanged.connect(self._agendar_preview)
        self._temperatura_pretendida.valueChanged.connect(self._agendar_preview)
        self._btn_aplicar.clicked.connect(self._ao_aplicar)
        self._btn_cancelar.clicked.connect(self.reject)

        self.setMinimumWidth(380)

    def _adicionar_controle_temperatura(
        self,
        layout: QVBoxLayout,
        texto: str,
    ) -> tuple[QSpinBox, QSlider]:
        layout.addWidget(QLabel(texto, self))
        campo = self._criar_campo_temperatura()
        slider = self._criar_slider_temperatura()
        layout.addWidget(campo)
        layout.addWidget(slider)
        return campo, slider

    def _criar_campo_temperatura(self) -> QSpinBox:
        controle = QSpinBox(self)
        controle.setRange(_TEMPERATURA_MINIMA, _TEMPERATURA_MAXIMA)
        controle.setSingleStep(100)
        controle.setValue(_TEMPERATURA_PADRAO)
        controle.setSuffix(" K")
        controle.setKeyboardTracking(False)
        return controle

    def _criar_slider_temperatura(self) -> QSlider:
        slider = QSlider(Qt.Orientation.Horizontal, self)
        slider.setRange(_TEMPERATURA_MINIMA, _TEMPERATURA_MAXIMA)
        slider.setSingleStep(100)
        slider.setPageStep(500)
        slider.setValue(_TEMPERATURA_PADRAO)
        return slider

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        if imagem.ndim != 3 or imagem.shape[2] < 3:
            raise ValueError("A temperatura de cor requer uma imagem RGB.")

        temperatura_original = self._temperatura_original.value()
        temperatura_pretendida = self._temperatura_pretendida.value()
        if temperatura_original == temperatura_pretendida:
            return imagem.copy()

        fatores = _fatores_temperatura(
            temperatura_original,
            temperatura_pretendida,
        )
        rgb_linear = _LUT_SRGB_PARA_LINEAR[imagem[..., :3]]
        rgb_ajustado = rgb_linear * fatores.reshape(1, 1, 3)
        rgb_srgb = _linear_para_srgb(rgb_ajustado)

        resultado = imagem.copy()
        resultado[..., :3] = np.rint(rgb_srgb * 255.0).astype(np.uint8)
        return resultado

    def _agendar_preview(self, _valor: int) -> None:
        if not self._timer_preview.isActive():
            self._timer_preview.start()

    def _emitir_preview(self) -> None:
        self.preview_requested.emit(self.processar(self.imagem_original))

    def _ao_aplicar(self) -> None:
        self._timer_preview.stop()
        resultado = self.processar(self.imagem_original)
        self.apply_requested.emit(resultado)
        self.accept()
