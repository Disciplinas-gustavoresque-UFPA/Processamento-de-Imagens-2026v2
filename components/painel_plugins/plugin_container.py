"""
components/painel_plugins/plugin_container.py
-------------------------------
Container que exibe o widget do plugin ativo na área de trabalho.
"""

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QScrollArea
)
from PySide6.QtGui import QFont

from core.plugin_base import PluginBase


class PluginContainer(QWidget):
    """Container que mostra os controles do plugin ativo."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._plugin_atual: PluginBase = None
        self._callback_preview = None
        self._callback_aplicar = None
        self._setup_ui()
        
    def _setup_ui(self):
        """Configura o layout do container."""
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.setSpacing(0)
        
        # Cabeçalho do plugin
        cabecalho = QWidget()
        cabecalho.setStyleSheet("""
            QWidget {
                background-color: #3d3d3d;
                border-bottom: 1px solid #5d5d5d;
            }
        """)
        layout_cabecalho = QHBoxLayout(cabecalho)
        
        self._label_titulo = QLabel("Nenhum filtro selecionado")
        self._label_titulo.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self._label_titulo.setStyleSheet("color: white; padding: 8px;")
        
        self._btn_fechar = QPushButton("✕")
        self._btn_fechar.setFixedSize(30, 30)
        self._btn_fechar.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: white;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #c44;
                border-radius: 4px;
            }
        """)
        self._btn_fechar.clicked.connect(self.limpar_plugin)
        self._btn_fechar.hide()
        
        layout_cabecalho.addWidget(self._label_titulo)
        layout_cabecalho.addStretch()
        layout_cabecalho.addWidget(self._btn_fechar)
        
        layout_principal.addWidget(cabecalho)
        
        # Área de conteúdo (onde o widget do plugin ficará)
        self._area_conteudo = QScrollArea()
        self._area_conteudo.setWidgetResizable(True)
        self._area_conteudo.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #2b2b2b;
            }
        """)
        
        self._conteudo_widget = QWidget()
        self._layout_conteudo = QVBoxLayout(self._conteudo_widget)
        self._layout_conteudo.setContentsMargins(10, 10, 10, 10)
        
        self._area_conteudo.setWidget(self._conteudo_widget)
        layout_principal.addWidget(self._area_conteudo)
        
        # Altura fixa para o container de plugin
        self.setMaximumHeight(400)
        self.setMinimumHeight(200)
        
    def definir_plugin(self, plugin: PluginBase, imagem_rgb: np.ndarray, 
                       callback_preview, callback_aplicar):
        """
        Define o plugin ativo e exibe seus controles.
        """
        # Limpa plugin anterior
        self.limpar_plugin()
        
        self._plugin_atual = plugin
        self._callback_preview = callback_preview
        self._callback_aplicar = callback_aplicar
        
        # Atualiza a imagem original do plugin
        self._plugin_atual.imagem_original = imagem_rgb.copy()
        
        # Conecta os sinais
        self._plugin_atual.preview_requested.connect(callback_preview)
        self._plugin_atual.apply_requested.connect(callback_aplicar)
        
        # Configura o widget do plugin
        widget_plugin = self._plugin_atual.get_widget()
        
        if isinstance(widget_plugin, QWidget):
            # Remove os botões Aplicar/Cancelar do plugin original
            self._remover_botoes_padrao(widget_plugin)
            
            # Adiciona botões customizados
            layout_botoes = QHBoxLayout()
            btn_aplicar = QPushButton("✓ Aplicar")
            btn_cancelar = QPushButton("✗ Cancelar")
            btn_aplicar.setStyleSheet(self._get_botao_style())
            btn_cancelar.setStyleSheet(self._get_botao_style())
            
            btn_aplicar.clicked.connect(self._aplicar_plugin)
            btn_cancelar.clicked.connect(self.limpar_plugin)
            
            layout_botoes.addWidget(btn_aplicar)
            layout_botoes.addWidget(btn_cancelar)
            
            # Adiciona ao layout
            self._layout_conteudo.addWidget(widget_plugin)
            self._layout_conteudo.addLayout(layout_botoes)
        
        self._label_titulo.setText(getattr(self._plugin_atual, 'display_name', 'Plugin'))
        self._btn_fechar.show()
        
    def _get_botao_style(self):
        """Retorna o estilo dos botões."""
        return """
            QPushButton {
                padding: 8px;
                background-color: #4CAF50;
                border: none;
                color: white;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """
        
    def _remover_botoes_padrao(self, widget):
        """Remove os botões Aplicar/Cancelar do layout do plugin."""
        for botao in widget.findChildren(QPushButton):
            if botao.text() in ["Aplicar", "Cancelar", "Apply", "Cancel"]:
                botao.hide()
                
    def _aplicar_plugin(self):
        """Aplica o plugin atual e fecha o container."""
        if self._plugin_atual:
            # Processa a imagem
            imagem_processada = self._plugin_atual.processar(self._plugin_atual.imagem_original)
            # Emite o sinal de apply
            self._plugin_atual.apply_requested.emit(imagem_processada)
            # Limpa o container
            self.limpar_plugin()
            
    def limpar_plugin(self):
        """Remove o plugin atual e limpa o container."""
        if self._plugin_atual:
            # Desconecta os sinais
            try:
                self._plugin_atual.preview_requested.disconnect()
            except:
                pass
            try:
                self._plugin_atual.apply_requested.disconnect()
            except:
                pass
            
            # Remove o widget do layout
            for i in reversed(range(self._layout_conteudo.count())):
                item = self._layout_conteudo.itemAt(i)
                if item.widget():
                    item.widget().deleteLater()
                elif item.layout():
                    # Limpa layouts aninhados
                    while item.layout().count():
                        subitem = item.layout().takeAt(0)
                        if subitem.widget():
                            subitem.widget().deleteLater()
                    
            self._plugin_atual = None
            self._callback_preview = None
            self._callback_aplicar = None
            
        self._label_titulo.setText("Nenhum filtro selecionado")
        self._btn_fechar.hide()