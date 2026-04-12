"""
components/painel_plugins/painel_plugins.py
----------------------------
Painel lateral com seções expansíveis para organizar os plugins.
"""

import os
import importlib.util
import inspect
from typing import Dict, List, Type

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QPushButton, 
    QLabel
)
from PySide6.QtGui import QFont

from core.plugin_base import PluginBase


class SecaoPlugins(QWidget):
    """Seção expansível que contém botões para um grupo de plugins."""
    
    # CORRIGIDO: Adicionar o tipo do argumento
    plugin_selecionado = Signal(object)  # Emite a classe do plugin
    
    def __init__(self, titulo: str, parent=None):
        super().__init__(parent)
        self.titulo = titulo
        self._expandido = True
        self._botoes = []
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Cria a UI da seção."""
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.setSpacing(2)
        
        # Botão do cabeçalho (expansível)
        self._btn_cabecalho = QPushButton(f"▶ {self.titulo}", self)
        self._btn_cabecalho.setFlat(True)
        self._btn_cabecalho.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 8px;
                font-weight: bold;
                background-color: #2d2d2d;
                border: none;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
        """)
        self._btn_cabecalho.clicked.connect(self._toggle_expandir)
        layout_principal.addWidget(self._btn_cabecalho)
        
        # Container dos botões (expansível)
        self._container = QWidget()
        self._layout_botoes = QVBoxLayout(self._container)
        self._layout_botoes.setContentsMargins(10, 5, 5, 5)
        self._layout_botoes.setSpacing(5)
        layout_principal.addWidget(self._container)
        
    def _toggle_expandir(self):
        """Expande ou recolhe a seção."""
        self._expandido = not self._expandido
        self._container.setVisible(self._expandido)
        self._btn_cabecalho.setText(f"{'▼' if self._expandido else '▶'} {self.titulo}")
        
    def adicionar_plugin(self, nome: str, classe_plugin: Type[PluginBase]):
        """Adiciona um botão para o plugin na seção."""
        botao = QPushButton(nome, self)
        botao.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 6px;
                background-color: #3d3d3d;
                border: none;
                color: #e0e0e0;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
            QPushButton:pressed {
                background-color: #5d5d5d;
            }
        """)
        # CORRIGIDO: Usar lambda com argumento correto
        botao.clicked.connect(lambda checked=False, cls=classe_plugin: self.plugin_selecionado.emit(cls))
        self._layout_botoes.addWidget(botao)
        self._botoes.append(botao)
        
    def expandir(self):
        """Expande a seção."""
        if not self._expandido:
            self._toggle_expandir()
            
    def recolher(self):
        """Recolhe a seção."""
        if self._expandido:
            self._toggle_expandir()


class PainelPlugins(QWidget):
    """Painel lateral completo com todas as seções de plugins."""
    
    # CORRIGIDO: Adicionar o tipo do argumento
    plugin_selecionado = Signal(object)  # Encaminha o sinal
    
    def __init__(self, diretorio_plugins: str, parent=None):
        super().__init__(parent)
        self.diretorio_plugins = diretorio_plugins
        self._secoes: Dict[str, SecaoPlugins] = {}
        
        self._setup_ui()
        self._carregar_plugins()
        
    def _setup_ui(self):
        """Configura o layout do painel."""
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.setSpacing(0)
        
        # Título do painel
        titulo = QLabel("Ferramentas")
        titulo.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        titulo.setStyleSheet("""
            QLabel {
                padding: 10px;
                background-color: #2d2d2d;
                color: white;
                border-bottom: 1px solid #4d4d4d;
            }
        """)
        layout_principal.addWidget(titulo)
        
        # Área rolável para as seções
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #2b2b2b;
            }
        """)
        
        self._container_widget = QWidget()
        self._layout_secoes = QVBoxLayout(self._container_widget)
        self._layout_secoes.setContentsMargins(5, 5, 5, 5)
        self._layout_secoes.setSpacing(10)
        self._layout_secoes.addStretch()
        
        scroll.setWidget(self._container_widget)
        layout_principal.addWidget(scroll)
        
        self.setMaximumWidth(280)
        self.setMinimumWidth(200)
        
    def _carregar_plugins(self):
        """Varre o diretório e carrega os plugins organizados por categoria."""
        if not os.path.isdir(self.diretorio_plugins):
            print(f"Diretório não encontrado: {self.diretorio_plugins}")
            return
            
        # Mapeamento de categorias para títulos
        titulos_categorias = {
            "pixels": "Ajustes de Pixel",
            "filtros": "Filtros",
        }
        
        # Varre cada subdiretório dentro de plugins/
        for categoria in os.listdir(self.diretorio_plugins):
            caminho_categoria = os.path.join(self.diretorio_plugins, categoria)
            if not os.path.isdir(caminho_categoria) or categoria.startswith("_"):
                continue
                
            print(f"Carregando categoria: {categoria}")
            
            # Cria seção para esta categoria
            titulo = titulos_categorias.get(categoria, f"📁 {categoria.capitalize()}")
            secao = SecaoPlugins(titulo, self)
            secao.plugin_selecionado.connect(self.plugin_selecionado.emit)
            
            # Carrega plugins desta categoria
            self._carregar_plugins_da_categoria(caminho_categoria, secao)
            
            # Adiciona a seção ao layout (antes do stretch)
            self._layout_secoes.insertWidget(self._layout_secoes.count() - 1, secao)
            self._secoes[categoria] = secao
            
    def _carregar_plugins_da_categoria(self, diretorio: str, secao: SecaoPlugins):
        """Carrega todos os plugins de uma categoria específica."""
        for arquivo in sorted(os.listdir(diretorio)):
            if not arquivo.endswith(".py") or arquivo.startswith("_"):
                continue
                
            caminho = os.path.join(diretorio, arquivo)
            print(f"  Carregando plugin: {arquivo}")
            classes = self._carregar_classes_do_arquivo(caminho)
            
            for classe_plugin in classes:
                nome_exibicao = getattr(
                    classe_plugin, "display_name", classe_plugin.__name__
                )
                print(f"    Adicionando: {nome_exibicao}")
                secao.adicionar_plugin(nome_exibicao, classe_plugin)
                
    def _carregar_classes_do_arquivo(self, caminho_arquivo: str) -> List[Type[PluginBase]]:
        """Importa um arquivo e retorna classes que herdam de PluginBase."""
        nome_modulo = os.path.splitext(os.path.basename(caminho_arquivo))[0]
        spec = importlib.util.spec_from_file_location(nome_modulo, caminho_arquivo)
        if spec is None or spec.loader is None:
            return []
            
        modulo = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(modulo)
        except Exception as erro:
            print(f"[plugins] Erro ao carregar '{caminho_arquivo}': {erro}")
            return []
            
        classes = []
        for _nome, obj in inspect.getmembers(modulo, inspect.isclass):
            if issubclass(obj, PluginBase) and obj is not PluginBase:
                classes.append(obj)
        return classes
        
    def expandir_todos(self):
        """Expande todas as seções."""
        for secao in self._secoes.values():
            secao.expandir()
            
    def recolher_todos(self):
        """Recolhe todas as seções."""
        for secao in self._secoes.values():
            secao.recolher()