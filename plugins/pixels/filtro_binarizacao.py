import cv2
import numpy as np
from PySide6.QtCore import Qt
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

class FiltroBinarizacao(PluginBase):
    """Plugin para binarização da imagem"""
    display_name = "Binarização"

    # ------------------------------------------------------------------
    # Interface (setup_ui)
    # ------------------------------------------------------------------

    def setup_ui(self) -> None:
        layout_principal = QVBoxLayout(self)
        
        # --- Seleção da Origem da Imagem ---
        rotulo_metodo = QLabel("Canal base para binarização:", self)
        layout_principal.addWidget(rotulo_metodo)
        
        self._grupo_metodos = QButtonGroup(self)
        self._radios_metodo: dict[str, QRadioButton] = {}
        
        opcoes = [
            ("Média RGB", "media"),
            ("Canal Vermelho (R)", "r"),
            ("Canal Verde (G)", "g"),
            ("Canal Azul (B)", "b"),
            ]
        
        for texto, valor in opcoes:
            radio = QRadioButton(texto, self)
            self._grupo_metodos.addButton(radio)
            self._radios_metodo[valor] = radio
            layout_principal.addWidget(radio)

        # Define a Média RGB como padrão
        self._radios_metodo["media"].setChecked(True)

        layout_principal.addSpacing(10)

        # --- Controle do Limiar (Slider) ---
        self._rotulo_limiar = QLabel("Limiar (Threshold): 127", self)
        layout_principal.addWidget(self._rotulo_limiar)

        self._slider_limiar = QSlider(Qt.Orientation.Horizontal, self)
        self._slider_limiar.setRange(0, 255)
        self._slider_limiar.setValue(127)  # Inicia no meio da escala
        layout_principal.addWidget(self._slider_limiar)

        layout_principal.addSpacing(10)

        # --- Botões de Ação ---
        layout_botoes = QHBoxLayout()
        self._btn_aplicar = QPushButton("Aplicar", self)
        self._btn_cancelar = QPushButton("Cancelar", self)
        layout_botoes.addWidget(self._btn_aplicar)
        layout_botoes.addWidget(self._btn_cancelar)
        layout_principal.addLayout(layout_botoes)

        # --- Conexões de Sinais (Eventos) ---
        for radio in self._radios_metodo.values():
            radio.toggled.connect(self._ao_alterar_parametros)

        self._slider_limiar.valueChanged.connect(self._ao_mover_slider)
        
        self._btn_aplicar.clicked.connect(self._ao_aplicar)
        self._btn_cancelar.clicked.connect(self.reject)

        self.setLayout(layout_principal)
        self.setMinimumWidth(320)


    def _ao_mover_slider(self, valor: int) -> None:
        """Atualiza o texto da interface quando o slider é movimentado."""
        self._rotulo_limiar.setText(f"Limiar (Threshold): {valor}")
        self._ao_alterar_parametros(True)

    def _ao_alterar_parametros(self, marcado: bool) -> None:
        """Regera o processamento para mostrar o preview ao vivo no canvas."""
        if not marcado:
            return
        # Utiliza a cópia da imagem enviada pelo construtor da PluginBase
        imagem_processada = self.processar(self.imagem_original)
        self.preview_requested.emit(imagem_processada)

    def _ao_aplicar(self) -> None:
        """Aplica o filtro na matriz oficial e adiciona ao histórico."""
        imagem_processada = self.processar(self.imagem_original)
        self.apply_requested.emit(imagem_processada)
        self.accept()
