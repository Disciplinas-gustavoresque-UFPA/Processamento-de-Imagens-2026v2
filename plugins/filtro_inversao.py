"""
plugins/filtro_inversao.py
-------------------------
Plugin de exemplo: inversão de cores.

Cada pixel da imagem é invertido usando a operação:
novo_valor = 255 - valor_original
"""

import numpy as np
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from core.plugin_base import PluginBase


class FiltroInversao(PluginBase):
    """Plugin para inversão de cores da imagem."""

    display_name = "Inversão de Cores"

    # ------------------------------------------------------------------
    # Interface (setup_ui)
    # ------------------------------------------------------------------

    def setup_ui(self) -> None:
        """Cria interface simples com botões Aplicar / Cancelar."""
        layout_principal = QVBoxLayout(self)

        # --- Rótulo informativo ---
        self._rotulo = QLabel("Filtro: Inversão de Cores", self)
        layout_principal.addWidget(self._rotulo)

        # --- Botões ---
        layout_botoes = QHBoxLayout()
        self._btn_aplicar = QPushButton("Aplicar", self)
        self._btn_cancelar = QPushButton("Cancelar", self)
        layout_botoes.addWidget(self._btn_aplicar)
        layout_botoes.addWidget(self._btn_cancelar)
        layout_principal.addLayout(layout_botoes)

        # --- Conexões ---
        self._btn_aplicar.clicked.connect(self._ao_aplicar)
        self._btn_cancelar.clicked.connect(self.reject)

        self.setLayout(layout_principal)
        self.setMinimumWidth(320)

        # Emite preview automaticamente ao abrir
        imagem_processada = self.processar(self.imagem_original)
        self.preview_requested.emit(imagem_processada)

    # ------------------------------------------------------------------
    # Lógica de processamento
    # ------------------------------------------------------------------

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        """
        Aplica inversão de cores à imagem.

        Parâmetros
        ----------
        imagem : np.ndarray
            Imagem RGB de entrada.

        Retorna
        -------
        np.ndarray
            Imagem com cores invertidas.
        """
        return 255 - imagem

    # ------------------------------------------------------------------
    # Slots privados
    # ------------------------------------------------------------------

    def _ao_aplicar(self) -> None:
        """Emite o sinal de confirmação e fecha o diálogo."""
        imagem_processada = self.processar(self.imagem_original)
        self.apply_requested.emit(imagem_processada)
        self.accept()