"""
plugins/pixels/filtro_transformacao_por_partes.py
-----------------------------------------
Plugin para Transformação Linear por Partes (Piecewise Linear Transformation).

Implementa um gráfico interativo onde o usuário pode adicionar, mover e 
remover pontos de controle. Inclui seleção de canal (RGB, R, G, B) com
feedback visual de cores.
"""

import cv2
import numpy as np
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)

from core.plugin_base import PluginBase

class FiltroPiecewise(PluginBase):
    """Plugin para transformação por partes através de curvas interativas com seleção de canais."""
    
    display_name = "Transformação por partes (Piecewise)"

    # ------------------------------------------------------------------
    # Interface (setup_ui)
    # ------------------------------------------------------------------

    def setup_ui(self) -> None:
        layout_principal = QVBoxLayout(self)

        # --- Seleção do Canal ---
        rotulo_canal = QLabel("Canal a ser editado:", self)
        layout_principal.addWidget(rotulo_canal)

        self._grupo_canais = QButtonGroup(self)
        self._radios_canal: dict[str, QRadioButton] = {}

        opcoes_canal = [
            ("RGB", "rgb"),
            ("Vermelho", "r"),
            ("Verde", "g"),
            ("Azul", "b"),
        ]

        layout_canais = QHBoxLayout()
        for texto, valor in opcoes_canal:
            radio = QRadioButton(texto, self)
            self._grupo_canais.addButton(radio)
            self._radios_canal[valor] = radio
            layout_canais.addWidget(radio)

        self._radios_canal["rgb"].setChecked(True)
        layout_principal.addLayout(layout_canais)
        layout_principal.addSpacing(10)

        # --- Botões de Ação ---
        layout_botoes = QHBoxLayout()
        self._btn_aplicar = QPushButton("Aplicar", self)
        self._btn_cancelar = QPushButton("Cancelar", self)
        layout_botoes.addWidget(self._btn_aplicar)
        layout_botoes.addWidget(self._btn_cancelar)
        layout_principal.addLayout(layout_botoes)

        # --- Conexões ---
        for radio in self._radios_canal.values():
            radio.toggled.connect(self._ao_alterar_canal)

        self._btn_aplicar.clicked.connect(self._ao_aplicar)
        self._btn_cancelar.clicked.connect(self.reject)

        self.setLayout(layout_principal)
        self.setMinimumWidth(340)


    def _obter_canal(self) -> str:
        for valor, radio in self._radios_canal.items():
            if radio.isChecked():
                return valor
        return "rgb"

    # ------------------------------------------------------------------
    # Lógica de processamento
    # ------------------------------------------------------------------

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        """Aplica a curva (LUT) ao canal selecionado."""
        
        canal_alvo = self._obter_canal()
        imagem_saida = imagem.copy()

        return imagem_saida

    def _ao_alterar_canal(self, checado: bool) -> None:
        """Atualiza a cor do gráfico e refaz o processamento ao trocar de aba de cor."""
        if not checado:
            return
        
        canal_atual = self._obter_canal()
        self._ao_alterar_parametros()

    def _ao_alterar_parametros(self) -> None:
        imagem_processada = self.processar(self.imagem_original)
        self.preview_requested.emit(imagem_processada)

    def _ao_aplicar(self) -> None:
        imagem_processada = self.processar(self.imagem_original)
        self.apply_requested.emit(imagem_processada)
        self.accept()
