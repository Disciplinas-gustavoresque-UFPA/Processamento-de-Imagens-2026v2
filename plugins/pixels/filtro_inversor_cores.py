"""
plugins/pixels/filtro_blur.py
----------------------------
Plugin de exemplo: aplica diferentes tipos de borramento.
"""

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
)

from core.plugin_base import PluginBase


class FiltroBlur(PluginBase):
    """Plugin para aplicar borramento na imagem."""
    
    display_name = "Borramento (Blur)"
    
    def setup_ui(self) -> None:
        """Cria a interface do plugin."""
        layout_principal = QVBoxLayout(self)
        
        # --- Tipo de borramento ---
        rotulo_tipo = QLabel("Tipo de borramento:", self)
        layout_principal.addWidget(rotulo_tipo)
        
        self._combo_tipo = QComboBox(self)
        self._combo_tipo.addItems([
            "Média (Blur)",
            "Gaussiano",
            "Mediana"
        ])
        layout_principal.addWidget(self._combo_tipo)
        
        # --- Intensidade do borramento ---
        self._rotulo_intensidade = QLabel("Intensidade (tamanho do kernel): 3", self)
        self._rotulo_intensidade.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_principal.addWidget(self._rotulo_intensidade)
        
        self._slider_intensidade = QSlider(Qt.Orientation.Horizontal, self)
        self._slider_intensidade.setMinimum(1)
        self._slider_intensidade.setMaximum(15)
        self._slider_intensidade.setValue(3)
        self._slider_intensidade.setTickInterval(2)
        self._slider_intensidade.setTickPosition(QSlider.TickPosition.TicksBelow)
        layout_principal.addWidget(self._slider_intensidade)
        
        # --- Botões ---
        layout_botoes = QHBoxLayout()
        self._btn_aplicar = QPushButton("Aplicar", self)
        self._btn_cancelar = QPushButton("Cancelar", self)
        layout_botoes.addWidget(self._btn_aplicar)
        layout_botoes.addWidget(self._btn_cancelar)
        layout_principal.addLayout(layout_botoes)
        
        # --- Conexões ---
        self._slider_intensidade.valueChanged.connect(self._ao_mudar_parametro)
        self._combo_tipo.currentIndexChanged.connect(self._ao_mudar_parametro)
        self._btn_aplicar.clicked.connect(self._ao_aplicar)
        self._btn_cancelar.clicked.connect(self.reject)
        
        self.setLayout(layout_principal)
        self.setMinimumWidth(350)
    
    def _obter_parametros(self) -> tuple[str, int]:
        """Retorna o tipo e intensidade do borramento."""
        tipo = self._combo_tipo.currentText()
        intensidade = self._slider_intensidade.value()
        
        # Garantir que o kernel seja ímpar (requerido pelo OpenCV)
        if intensidade % 2 == 0:
            intensidade += 1
        
        return tipo, intensidade 
    
    def processar(self, imagem: np.ndarray) -> np.ndarray:
        """
        Aplica o borramento conforme o tipo selecionado.
        
        Parâmetros
        ----------
        imagem : np.ndarray
            Imagem RGB de entrada (H x W x 3, uint8).
        
        Retorna
        -------
        np.ndarray
            Imagem com borramento aplicado.
        """
        import cv2
        
        tipo, intensidade = self._obter_parametros()
        
        # Converter para BGR (OpenCV usa BGR)
        imagem_bgr = cv2.cvtColor(imagem, cv2.COLOR_RGB2BGR)
        
        # Aplicar o tipo de borramento
        if tipo == "Média (Blur)":
            kernel = (intensidade, intensidade)
            resultado_bgr = cv2.blur(imagem_bgr, kernel)
        elif tipo == "Gaussiano":
            kernel = (intensidade, intensidade)
            resultado_bgr = cv2.GaussianBlur(imagem_bgr, kernel, 0)
        else:  # Mediana
            # Mediana requer kernel ímpar, já garantido pelo _obter_parametros
            resultado_bgr = cv2.medianBlur(imagem_bgr, intensidade)
        
        # Converter de volta para RGB
        resultado_rgb = cv2.cvtColor(resultado_bgr, cv2.COLOR_BGR2RGB)
        
        return resultado_rgb
    
    def _ao_mudar_parametro(self, _valor=None) -> None:
        """Atualiza rótulos e emite preview."""
        tipo, intensidade = self._obter_parametros()
        
        self._rotulo_intensidade.setText(
            f"Intensidade (tamanho do kernel): {intensidade}"
        )
        
        # Emitir preview
        imagem_processada = self.processar(self.imagem_original)
        self.preview_requested.emit(imagem_processada)
    
    def _ao_aplicar(self) -> None:
        """Aplica o filtro permanentemente."""
        imagem_processada = self.processar(self.imagem_original)
        self.apply_requested.emit(imagem_processada)
        self.accept()