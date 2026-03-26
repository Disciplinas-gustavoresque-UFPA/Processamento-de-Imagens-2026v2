"""
core/plugin_base.py
-------------------
Classe base abstrata para todos os plugins do Studio de Processamento de Imagens.

Cada plugin deve herdar de ``PluginBase`` e implementar os métodos abstratos
``setup_ui`` e ``processar``.
"""

from abc import abstractmethod

import numpy as np
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog


class PluginBase(QDialog):
    """
    Base abstrata para plugins de processamento de imagem.

    Sinais
    ------
    preview_requested : Signal(np.ndarray)
        Emitido enquanto o usuário ajusta os controles, enviando a imagem
        processada para a janela principal exibir em tempo real.
    apply_requested : Signal(np.ndarray)
        Emitido quando o usuário confirma a operação, substituindo a imagem
        de trabalho pela imagem processada.
    """

    preview_requested = Signal(np.ndarray)
    apply_requested = Signal(np.ndarray)

    # Subclasses devem definir este atributo para nomear o plugin nos menus.
    display_name: str = "Plugin sem nome"

    def __init__(self, imagem: np.ndarray, parent=None):
        """
        Parâmetros
        ----------
        imagem : np.ndarray
            Imagem original em formato RGB (H × W × 3, dtype uint8).
        parent : QWidget, opcional
            Widget pai do diálogo.
        """
        super().__init__(parent)
        self.imagem_original: np.ndarray = imagem.copy()
        self.setWindowTitle(self.display_name)
        self.setup_ui()

    @abstractmethod
    def setup_ui(self) -> None:
        """
        Constrói os controles visuais do plugin (sliders, checkboxes, etc.).

        Este método é chamado automaticamente pelo ``__init__`` após a
        inicialização do diálogo.  O aluno deve criar os widgets necessários
        e conectá-los ao método ``processar``.
        """

    @abstractmethod
    def processar(self, imagem: np.ndarray) -> np.ndarray:
        """
        Aplica o algoritmo de processamento à imagem fornecida.

        Parâmetros
        ----------
        imagem : np.ndarray
            Imagem de entrada em formato RGB.

        Retorna
        -------
        np.ndarray
            Imagem resultante após o processamento.
        """
