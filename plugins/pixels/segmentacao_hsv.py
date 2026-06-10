import cv2
import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSlider,
    QPushButton
)

from core.plugin_base import PluginBase 

class SegmentacaoHSVPlugin(PluginBase):
    # Nome que será exibido automaticamente no Menu do sistema
    display_name = "Segmentação HSV"

    def __init__(self, imagem_rgb: np.ndarray, parent=None):
        super().__init__(imagem_rgb, parent)
        self.setWindowTitle("Segmentação por Cores HSV")
        self.resize(400, 350)
        
        # Armazena a imagem original convertida em HSV para processamento
        self.imagem_rgb_original = imagem_rgb.copy()
        self.imagem_hsv = cv2.cvtColor(self.imagem_rgb_original, cv2.COLOR_RGB2HSV)
        
        self._construir_ui()
        self._atualizar_segmentacao()

    def _construir_ui(self):
        layout_principal = QVBoxLayout(self)
        
        # Definição dos Sliders: (Nome, valor_min, valor_max, valor_inicial)
        # H (Matiz) vai de 0 a 179 no OpenCV. S e V vão de 0 a 255.
        self.sliders = {}
        config_sliders = [
            ("H Mínimo", 0, 179, 0),
            ("H Máximo", 0, 179, 179),
            ("S Mínimo", 0, 255, 0),
            ("S Máximo", 0, 255, 255),
            ("V Mínimo", 0, 255, 0),
            ("V Máximo", 0, 255, 255),
        ]
        
        for nome, v_min, v_max, v_ini in config_sliders:
            layout_slider = QHBoxLayout()
            label_nome = QLabel(f"{nome}:")
            label_nome.setMinimumWidth(80)
            
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(v_min, v_max)
            slider.setValue(v_ini)
            
            label_valor = QLabel(str(v_ini))
            label_valor.setMinimumWidth(30)
            
            # Atualiza o label numérico e gera o preview ao arrastar o slider
            slider.valueChanged.connect(lambda v, lbl=label_valor: lbl.setText(str(v)))
            slider.valueChanged.connect(self._atualizar_segmentacao)
            
            layout_slider.addWidget(label_nome)
            layout_slider.addWidget(slider)
            layout_slider.addWidget(label_valor)
            layout_principal.addLayout(layout_slider)
            
            # Guarda a referência para ler os valores depois
            self.sliders[nome] = slider

        # Botões de confirmação do QDialog
        layout_botoes = QHBoxLayout()
        btn_cancelar = QPushButton("Cancelar")
        btn_aplicar = QPushButton("Aplicar")
        
        btn_cancelar.clicked.connect(self.reject)
        btn_aplicar.clicked.connect(self.accept)
        
        layout_botoes.addWidget(btn_cancelar)
        layout_botoes.addWidget(btn_aplicar)
        layout_principal.addLayout(layout_botoes)

    def _atualizar_segmentacao(self):
        """Calcula a máscara HSV e envia o sinal de preview para a tela principal."""
        # Recupera os valores atuais dos controles deslizantes
        h_min = self.sliders["H Mínimo"].value()
        h_max = self.sliders["H Máximo"].value()
        s_min = self.sliders["S Mínimo"].value()
        s_max = self.sliders["S Máximo"].value()
        v_min = self.sliders["V Mínimo"].value()
        v_max = self.sliders["V Máximo"].value()
        
        limite_inferior = np.array([h_min, s_min, v_min])
        limite_superior = np.array([h_max, s_max, v_max])
        
        # Cria a máscara binária baseada nos intervalos selecionados
        mascara = cv2.inRange(self.imagem_hsv, limite_inferior, limite_superior)
        
        # Aplica a máscara na imagem original para isolar os pixels selecionados
        imagem_segmentada = cv2.bitwise_and(self.imagem_rgb_original, self.imagem_rgb_original, mask=mascara)
        
        # Emite o sinal de preview_requested exigido pela arquitetura do sistema
        self.preview_requested.emit(imagem_segmentada)

    def accept(self):
        """Disparado ao clicar em Aplicar, consolidando a alteração no histórico."""
        h_min = self.sliders["H Mínimo"].value()
        h_max = self.sliders["H Máximo"].value()
        s_min = self.sliders["S Mínimo"].value()
        s_max = self.sliders["S Máximo"].value()
        v_min = self.sliders["V Mínimo"].value()
        v_max = self.sliders["V Máximo"].value()
        
        limite_inferior = np.array([h_min, s_min, v_min])
        limite_superior = np.array([h_max, s_max, v_max])
        
        mascara = cv2.inRange(self.imagem_hsv, limite_inferior, limite_superior)
        imagem_final = cv2.bitwise_and(self.imagem_rgb_original, self.imagem_rgb_original, mask=mascara)
        
        # Emite o sinal de aplicação definitiva e encerra a janela de diálogo
        self.apply_requested.emit(imagem_final)
        super().accept()