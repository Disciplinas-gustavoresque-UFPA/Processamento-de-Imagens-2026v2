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


    def _selecionar_imagem(self) -> None:
        """
        Objetivo:
            Permitir ao usuário selecionar uma segunda imagem para ser
            utilizada na operação aritmética.

        Especificidades:
            Abre um diálogo para seleção de arquivos de imagem.
            Caso uma imagem válida seja escolhida, ela é carregada
            utilizando o OpenCV, armazenada internamente e o nome do
            arquivo é exibido na interface.

            Após o carregamento, uma nova pré-visualização é gerada.

        Parâmetros:
            Nenhum.

        Retorno:
            None.
        """

        arquivo, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar imagem",
            "",
            "Imagens (*.png *.jpg *.jpeg *.bmp)",
        )

        if not arquivo:
            return

        imagem = cv2.imread(arquivo)

        if imagem is None:
            return

        # Converter para RGB caso o restante da aplicação utilize esse formato.
        imagem = cv2.cvtColor(imagem, cv2.COLOR_BGR2RGB)

        self._segunda_imagem = imagem

        self._label_imagem.setText(Path(arquivo).name)

        self._emitir_preview()

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        """
        Objetivo:
            Combinar a imagem atualmente carregada com uma segunda
            imagem utilizando a função cv2.addWeighted().

        Especificidades:
            Caso nenhuma segunda imagem tenha sido selecionada,
            retorna uma cópia da imagem original.

            A segunda imagem é redimensionada automaticamente para
            possuir as mesmas dimensões da imagem principal, caso
            necessário.

            A operação realizada é:

                dst = src1 * alpha + src2 * beta + gamma

            onde:

                src1  -> imagem original;
                src2  -> segunda imagem;
                alpha -> peso aplicado à imagem original;
                beta  -> peso aplicado à segunda imagem;
                gamma -> deslocamento aplicado ao resultado.

            O OpenCV realiza automaticamente a saturação dos valores,
            limitando-os ao intervalo permitido para imagens de
            8 bits (0 a 255).

        Parâmetros:
            imagem (np.ndarray):
                Imagem atualmente carregada na aplicação.

        Retorno:
            np.ndarray:
                Imagem resultante da combinação entre as duas imagens.
        """

        if self._segunda_imagem is None:
            return imagem.copy()

        imagem_segundaria = cv2.resize(
            self._segunda_imagem,
            (imagem.shape[1], imagem.shape[0]),
        )

        alpha = self._slider_alpha.value() / 100.0
        beta = self._slider_beta.value() / 100.0
        gamma = self._slider_gamma.value()

        resultado = cv2.addWeighted(
            imagem,
            alpha,
            imagem_segundaria,
            beta,
            gamma,
        )

        return resultado

    def _ao_mudar_parametros(self) -> None:
        """
        Objetivo:
            Atualizar os valores exibidos na interface e gerar uma nova
            pré-visualização da operação aritmética.

        Especificidades:
            Os sliders de alpha e beta armazenam valores inteiros entre
            0 e 200. Esses valores são convertidos para números reais
            dividindo-os por 100, permitindo representar valores entre
            0.00 e 2.00.

            O valor de gamma é exibido diretamente, pois representa um
            deslocamento inteiro.

            Após atualizar os rótulos, uma nova pré-visualização é
            solicitada.

        Parâmetros:
            Nenhum.

        Retorno:
            None.
        """

        self._valor_alpha.setText(
            f"{self._slider_alpha.value() / 100:.2f}"
        )

        self._valor_beta.setText(
            f"{self._slider_beta.value() / 100:.2f}"
        )

        self._valor_gamma.setText(
            str(self._slider_gamma.value())
        )

        self._emitir_preview()

    def _emitir_preview(self) -> None:
        """
        Objetivo:
            Gerar uma pré-visualização da imagem resultante da operação
            aritmética.

        Especificidades:
            A pré-visualização somente é emitida quando uma segunda
            imagem já foi carregada.

            A imagem processada é enviada para a janela principal por
            meio do sinal 'preview_requested', permitindo visualizar o
            resultado antes da aplicação definitiva.

        Parâmetros:
            Nenhum.

        Retorno:
            None.
        """

        if self._segunda_imagem is None:
            return

        imagem_processada = self.processar(
            self.imagem_original
        )

        self.preview_requested.emit(imagem_processada)

    def _ao_aplicar(self) -> None:
        """
        Objetivo:
            Confirmar e aplicar definitivamente a operação aritmética.

        Especificidades:
            Processa a imagem utilizando os parâmetros atualmente
            definidos pelo usuário, emite o resultado para a aplicação
            por meio do sinal 'apply_requested' e encerra a janela do
            plugin.

        Parâmetros:
            Nenhum.

        Retorno:
            None.
        """

        imagem_processada = self.processar(
            self.imagem_original
        )

        self.apply_requested.emit(imagem_processada)

        self.accept()