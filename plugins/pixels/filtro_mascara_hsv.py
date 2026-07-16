"""
plugins/pixels/filtro_mascara_hsv.py
-------------------------------------
Plugin de máscara interativa por faixa de cor (HSV range selection).
"""

import cv2
import numpy as np
from PySide6.QtCore import Qt, QTimer
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


class FiltroMascaraHSV(PluginBase):
    """Mascara interativa por faixa de cor no espaco HSV."""

    display_name = "Mascara HSV (Faixa de Cor)"

    def setup_ui(self) -> None:
        layout_principal = QVBoxLayout(self)

        rotulo_titulo = QLabel("Selecione a faixa de cor HSV:", self)
        rotulo_titulo.setStyleSheet("font-weight: bold;")
        layout_principal.addWidget(rotulo_titulo)

        # --- Faixa de Matiz (H): 0-179 no OpenCV ---
        self._rotulo_h_min = QLabel("Matiz minima (H): 0", self)
        layout_principal.addWidget(self._rotulo_h_min)
        self._slider_h_min = QSlider(Qt.Orientation.Horizontal, self)
        self._slider_h_min.setRange(0, 179)
        self._slider_h_min.setValue(0)
        layout_principal.addWidget(self._slider_h_min)

        self._rotulo_h_max = QLabel("Matiz maxima (H): 179", self)
        layout_principal.addWidget(self._rotulo_h_max)
        self._slider_h_max = QSlider(Qt.Orientation.Horizontal, self)
        self._slider_h_max.setRange(0, 179)
        self._slider_h_max.setValue(179)
        layout_principal.addWidget(self._slider_h_max)

        layout_principal.addSpacing(5)

        # --- Faixa de Saturacao (S): 0-255 ---
        self._rotulo_s_min = QLabel("Saturacao minima (S): 0", self)
        layout_principal.addWidget(self._rotulo_s_min)
        self._slider_s_min = QSlider(Qt.Orientation.Horizontal, self)
        self._slider_s_min.setRange(0, 255)
        self._slider_s_min.setValue(0)
        layout_principal.addWidget(self._slider_s_min)

        self._rotulo_s_max = QLabel("Saturacao maxima (S): 255", self)
        layout_principal.addWidget(self._rotulo_s_max)
        self._slider_s_max = QSlider(Qt.Orientation.Horizontal, self)
        self._slider_s_max.setRange(0, 255)
        self._slider_s_max.setValue(255)
        layout_principal.addWidget(self._slider_s_max)

        layout_principal.addSpacing(5)

        # --- Faixa de Valor (V): 0-255 ---
        self._rotulo_v_min = QLabel("Valor minimo (V): 0", self)
        layout_principal.addWidget(self._rotulo_v_min)
        self._slider_v_min = QSlider(Qt.Orientation.Horizontal, self)
        self._slider_v_min.setRange(0, 255)
        self._slider_v_min.setValue(0)
        layout_principal.addWidget(self._slider_v_min)

        self._rotulo_v_max = QLabel("Valor maximo (V): 255", self)
        layout_principal.addWidget(self._rotulo_v_max)
        self._slider_v_max = QSlider(Qt.Orientation.Horizontal, self)
        self._slider_v_max.setRange(0, 255)
        self._slider_v_max.setValue(255)
        layout_principal.addWidget(self._slider_v_max)

        layout_principal.addSpacing(10)

        # --- Modo de saida ---
        rotulo_modo = QLabel("Modo de saida:", self)
        layout_principal.addWidget(rotulo_modo)

        self._grupo_modo = QButtonGroup(self)
        self._radios_modo: dict[str, QRadioButton] = {}

        opcoes_modo = [
            ("Mascara binaria (preto/branco)", "binaria"),
            ("Imagem mascarada (fundo preto)", "mascarada"),
            ("Destaque da selecao (vermelho)", "destaque"),
        ]

        for texto, valor in opcoes_modo:
            radio = QRadioButton(texto, self)
            self._grupo_modo.addButton(radio)
            self._radios_modo[valor] = radio
            layout_principal.addWidget(radio)

        self._radios_modo["binaria"].setChecked(True)

        layout_principal.addSpacing(10)

        # --- Botoes ---
        layout_botoes = QHBoxLayout()
        self._btn_aplicar = QPushButton("Aplicar", self)
        self._btn_cancelar = QPushButton("Cancelar", self)
        layout_botoes.addWidget(self._btn_aplicar)
        layout_botoes.addWidget(self._btn_cancelar)
        layout_principal.addLayout(layout_botoes)

        # --- Conexoes de sinais ---
        for slider in [
            self._slider_h_min, self._slider_h_max,
            self._slider_s_min, self._slider_s_max,
            self._slider_v_min, self._slider_v_max,
        ]:
            slider.valueChanged.connect(self._ao_mudar_parametros)

        for radio in self._radios_modo.values():
            radio.toggled.connect(self._ao_mudar_parametros)

        self._btn_aplicar.clicked.connect(self._ao_aplicar)
        self._btn_cancelar.clicked.connect(self.reject)

        self.setLayout(layout_principal)
        self.setMinimumWidth(380)

        QTimer.singleShot(100, self._emitir_preview)

    # ------------------------------------------------------------------
    # Metodos auxiliares
    # ------------------------------------------------------------------

    def _obter_modo(self) -> str:
        """Retorna a chave do modo de saida selecionado."""
        for valor, radio in self._radios_modo.items():
            if radio.isChecked():
                return valor
        return "binaria"

    def _obter_faixa_hsv(self) -> tuple[int, int, int, int, int, int]:
        """Retorna (h_min, h_max, s_min, s_max, v_min, v_max)."""
        return (
            self._slider_h_min.value(),
            self._slider_h_max.value(),
            self._slider_s_min.value(),
            self._slider_s_max.value(),
            self._slider_v_min.value(),
            self._slider_v_max.value(),
        )

    def _atualizar_rotulos(self) -> None:
        """Atualiza os textos dos labels com os valores atuais dos sliders."""
        h_min, h_max, s_min, s_max, v_min, v_max = self._obter_faixa_hsv()
        self._rotulo_h_min.setText(f"Matiz minima (H): {h_min}")
        self._rotulo_h_max.setText(f"Matiz maxima (H): {h_max}")
        self._rotulo_s_min.setText(f"Saturacao minima (S): {s_min}")
        self._rotulo_s_max.setText(f"Saturacao maxima (S): {s_max}")
        self._rotulo_v_min.setText(f"Valor minimo (V): {v_min}")
        self._rotulo_v_max.setText(f"Valor maximo (V): {v_max}")

    def _gerar_mascara(self, imagem: np.ndarray) -> np.ndarray:
        """Gera a mascara binaria a partir da faixa HSV selecionada."""
        h_min, h_max, s_min, s_max, v_min, v_max = self._obter_faixa_hsv()

        # Garante que min <= max para cada canal
        lower = np.array([min(h_min, h_max), min(s_min, s_max), min(v_min, v_max)], dtype=np.uint8)
        upper = np.array([max(h_min, h_max), max(s_min, s_max), max(v_min, v_max)], dtype=np.uint8)

        imagem_hsv = cv2.cvtColor(imagem, cv2.COLOR_RGB2HSV)
        mascara = cv2.inRange(imagem_hsv, lower, upper)
        return mascara

    # ------------------------------------------------------------------
    # Processamento
    # ------------------------------------------------------------------

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        """Aplica a mascara HSV de acordo com o modo de saida selecionado."""
        mascara = self._gerar_mascara(imagem)
        modo = self._obter_modo()

        if modo == "binaria":
            # Mascara binaria: branco (255) onde corresponde, preto (0) onde nao
            return cv2.cvtColor(mascara, cv2.COLOR_GRAY2RGB)

        elif modo == "mascarada":
            # Aplica a mascara sobre a imagem original (fundo vira preto)
            resultado = np.zeros_like(imagem)
            mascara_3ch = cv2.cvtColor(mascara, cv2.COLOR_GRAY2RGB)
            resultado[mascara_3ch > 0] = imagem[mascara_3ch > 0]
            return resultado

        elif modo == "destaque":
            # Destaca os pixels selecionados em vermelho sobre a imagem
            resultado = imagem.copy()
            vermelho = np.array([255, 0, 0], dtype=np.uint8)
            mascara_3ch = cv2.cvtColor(mascara, cv2.COLOR_GRAY2RGB)
            resultado[mascara_3ch > 0] = vermelho
            return resultado

        return imagem.copy()

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def _emitir_preview(self) -> None:
        """Emite o sinal de preview com a imagem processada."""
        self._atualizar_rotulos()
        imagem_processada = self.processar(self.imagem_original)
        self.preview_requested.emit(imagem_processada)

    def _ao_mudar_parametros(self, _valor: int | bool) -> None:
        """Chamado quando qualquer slider ou radio eh alterado."""
        self._atualizar_rotulos()
        imagem_processada = self.processar(self.imagem_original)
        self.preview_requested.emit(imagem_processada)

    def _ao_aplicar(self) -> None:
        """Aplica a mascara e fecha o dialogo."""
        imagem_processada = self.processar(self.imagem_original)
        self.apply_requested.emit(imagem_processada)
        self.accept()
