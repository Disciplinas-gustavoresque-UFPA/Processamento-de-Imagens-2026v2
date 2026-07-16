"""
Plugin para Operações Aritméticas entre duas imagens.

Objetivo:
    Permitir combinar a imagem atualmente carregada com uma segunda
    imagem utilizando a função cv2.addWeighted().

Especificidades:
    - O usuário seleciona uma segunda imagem.
    - Define os parâmetros alpha, beta e gamma.
    - A segunda imagem é redimensionada automaticamente para possuir
      as mesmas dimensões da imagem original, quando necessário.
    - A operação realizada é:

        dst = saturate(src1 * alpha + src2 * beta + gamma)

    onde:
        src1 = imagem atualmente carregada;
        src2 = segunda imagem selecionada;
        alpha = peso aplicado à imagem original;
        beta = peso aplicado à segunda imagem;
        gamma = deslocamento adicionado ao resultado.

    A função limita automaticamente os valores ao intervalo permitido
    para imagens de 8 bits (0–255).

Retorno:
    Imagem resultante da combinação das duas imagens.
"""

from pathlib import Path

import cv2
import numpy as np

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
)

from core.plugin_base import PluginBase


class OperacoesAritmeticas(PluginBase):
    """Plugin para combinação ponderada entre duas imagens."""

    display_name = "Operações Aritméticas"

    def setup_ui(self) -> None:
        """
        Objetivo:
            Configurar a interface gráfica do plugin.

        Especificidades:
            Cria os componentes necessários para a operação
            aritmética, incluindo:

            - botão para selecionar a segunda imagem;
            - sliders para ajuste de alpha, beta e gamma;
            - botões Aplicar e Cancelar.

            Também realiza a conexão entre os componentes da
            interface e seus respectivos métodos.

        Parâmetros:
            Nenhum.

        Retorno:
            None.
        """

        layout_principal = QVBoxLayout(self)

        layout_principal.addWidget(
            QLabel(
                "Selecione uma segunda imagem para combinar "
                "com a imagem atual."
            )
        )

        # Botão para selecionar a segunda imagem
        self._botao_imagem = QPushButton("Selecionar imagem")
        self._botao_imagem.clicked.connect(self._selecionar_imagem)

        layout_principal.addWidget(self._botao_imagem)

        self._label_imagem = QLabel("Nenhuma imagem selecionada.")
        layout_principal.addWidget(self._label_imagem)

        # ---------------- Alpha ----------------

        layout_principal.addWidget(
            QLabel("Alpha (Imagem Atual):")
        )

        self._slider_alpha = QSlider(Qt.Horizontal)
        self._slider_alpha.setRange(0, 200)
        self._slider_alpha.setValue(100)

        self._valor_alpha = QLabel("1.00")

        layout_principal.addWidget(self._slider_alpha)
        layout_principal.addWidget(self._valor_alpha)

        # ---------------- Beta ----------------

        layout_principal.addWidget(
            QLabel("Beta (Segunda Imagem):")
        )

        self._slider_beta = QSlider(Qt.Horizontal)
        self._slider_beta.setRange(0, 200)
        self._slider_beta.setValue(100)

        self._valor_beta = QLabel("1.00")

        layout_principal.addWidget(self._slider_beta)
        layout_principal.addWidget(self._valor_beta)

        # ---------------- Gamma ----------------

        layout_principal.addWidget(
            QLabel("Gamma:")
        )

        self._slider_gamma = QSlider(Qt.Horizontal)
        self._slider_gamma.setRange(-255, 255)
        self._slider_gamma.setValue(0)

        self._valor_gamma = QLabel("0")

        layout_principal.addWidget(self._slider_gamma)
        layout_principal.addWidget(self._valor_gamma)

        # ---------------- Botões ----------------

        layout_botoes = QHBoxLayout()

        self._botao_aplicar = QPushButton("Aplicar")
        self._botao_cancelar = QPushButton("Cancelar")

        layout_botoes.addWidget(self._botao_aplicar)
        layout_botoes.addWidget(self._botao_cancelar)

        layout_principal.addLayout(layout_botoes)

        # Conexões

        self._slider_alpha.valueChanged.connect(
            self._ao_mudar_parametros
        )

        self._slider_beta.valueChanged.connect(
            self._ao_mudar_parametros
        )

        self._slider_gamma.valueChanged.connect(
            self._ao_mudar_parametros
        )

        self._botao_aplicar.clicked.connect(self._ao_aplicar)
        self._botao_cancelar.clicked.connect(self.reject)

        self._segunda_imagem = None

        self.setLayout(layout_principal)
        self.setMinimumWidth(380)
