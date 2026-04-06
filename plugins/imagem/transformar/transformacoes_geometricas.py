"""
Plugin de transformações geométricas básicas para a imagem carregada.

Disponibiliza as operações:
* Rotação 90° à esquerda
* Rotação 90° à direita
* Rotação 180°
* Espelhamento horizontal
* Espelhamento vertical
"""

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


class TransformacoesGeometricas(PluginBase):
    """Plugin para rotação e espelhamento da imagem."""

    display_name = "Rotação e Espelhamento"

    _OP_SEM_TRANSFORMACAO = 0
    _OP_ROT_90_ESQ = 1
    _OP_ROT_90_DIR = 2
    _OP_ROT_180 = 3
    _OP_ESPELHO_HORIZONTAL = 4
    _OP_ESPELHO_VERTICAL = 5

    def setup_ui(self) -> None:
        """
        Configura os controles do plugin e suas conexões.
        O plugin apresenta um conjunto de opções de transformação, cada uma representada por um botão de rádio.  O usuário pode escolher uma opção e clicar em "Aplicar" para confirmar a operação ou "Cancelar" para fechar o diálogo sem alterações. Enquanto o usuário ajusta as opções, uma pré-visualização da transformação é emitida para a janela principal.
        """
        layout_principal = QVBoxLayout(self)
        layout_principal.addWidget(
            QLabel("Escolha uma transformação para aplicar na imagem:", self)
        )

        self._grupo_opcoes = QButtonGroup(self)

        # Define as opções de transformação disponíveis
        opcoes = [
            ("Sem transformação", self._OP_SEM_TRANSFORMACAO, True),
            ("Rotacionar 90° à esquerda", self._OP_ROT_90_ESQ, False),
            ("Rotacionar 90° à direita", self._OP_ROT_90_DIR, False),
            ("Rotacionar 180°", self._OP_ROT_180, False),
            ("Espelhar horizontalmente", self._OP_ESPELHO_HORIZONTAL, False),
            ("Espelhar verticalmente", self._OP_ESPELHO_VERTICAL, False),
        ]

        # Cria os botões de rádio para cada opção de transformação.
        for texto, identificador, marcado in opcoes:
            botao = QRadioButton(texto, self)
            botao.setChecked(marcado)
            self._grupo_opcoes.addButton(botao, identificador)
            layout_principal.addWidget(botao)

        # Botões de ação: Aplicar e Cancelar
        layout_botoes = QHBoxLayout()
        self._botao_aplicar = QPushButton("Aplicar", self)
        self._botao_cancelar = QPushButton("Cancelar", self)
        layout_botoes.addWidget(self._botao_aplicar)
        layout_botoes.addWidget(self._botao_cancelar)
        layout_principal.addLayout(layout_botoes)

        self._grupo_opcoes.idClicked.connect(self._ao_mudar_opcao)
        self._botao_aplicar.clicked.connect(self._ao_aplicar)
        self._botao_cancelar.clicked.connect(self.reject)

        self.setLayout(layout_principal)
        self.setMinimumWidth(360)

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        """
        Aplica a transformação selecionada à imagem original e retorna o resultado. Ela é chamada para gerar a pré-visualização e para aplicar a transformação final.
        """
        operacao = self._grupo_opcoes.checkedId()

        if operacao == self._OP_ROT_90_ESQ:
            resultado = np.rot90(imagem, 1)
        elif operacao == self._OP_ROT_90_DIR:
            resultado = np.rot90(imagem, -1)
        elif operacao == self._OP_ROT_180:
            resultado = np.rot90(imagem, 2)
        elif operacao == self._OP_ESPELHO_HORIZONTAL:
            resultado = np.fliplr(imagem)
        elif operacao == self._OP_ESPELHO_VERTICAL:
            resultado = np.flipud(imagem)
        else:
            resultado = imagem.copy()

        return np.ascontiguousarray(resultado)

    def _ao_mudar_opcao(self, _identificador: int) -> None:
        """Emite pré-visualização da transformação escolhida."""
        imagem_processada = self.processar(self.imagem_original)
        self.preview_requested.emit(imagem_processada)

    def _ao_aplicar(self) -> None:
        """Confirma a operação e fecha o diálogo."""
        imagem_processada = self.processar(self.imagem_original)
        self.apply_requested.emit(imagem_processada)
        self.accept()
