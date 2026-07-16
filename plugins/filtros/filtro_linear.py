"""
plugins/filtros/filtro_linear.py
-----------------------------------------
Plugin para aplicação de filtros lineares generalizados.

Permite ao usuário definir dimensões personalizadas do kernel, 
inserir coeficientes manualmente ou carregá-los de um arquivo CSV.

Escolha entre Correlação ou Convolução, e aplique em todos os canais 
ou em um canal de cor específico (R, G, B).
"""

import cv2
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.plugin_base import PluginBase


class FiltroLinear(PluginBase):
    """Plugin de Filtro Linear (Correlação, Convolução, CSV e Canais)."""
    
    display_name = "Filtro Linear (Conv/Corr)"

    # ------------------------------------------------------------------
    # Interface (setup_ui)
    # ------------------------------------------------------------------

    def setup_ui(self) -> None:
        layout_principal = QVBoxLayout(self)

        # --- Seleção do Canal Afetado ---
        rotulo_canal = QLabel("Canal afetado pelo filtro:", self)
        layout_principal.addWidget(rotulo_canal)

        self._grupo_canais = QButtonGroup(self)
        self._radios_canal: dict[str, QRadioButton] = {}

        opcoes_canal = [
            ("Todos os Canais (RGB)", "rgb"),
            ("Canal Vermelho (R)", "r"),
            ("Canal Verde (G)", "g"),
            ("Canal Azul (B)", "b"),
        ]

        # Layout horizontal para os botões de canal para economizar espaço vertical
        layout_canais = QHBoxLayout()
        for texto, valor in opcoes_canal:
            radio = QRadioButton(texto, self)
            self._grupo_canais.addButton(radio)
            self._radios_canal[valor] = radio
            # Quebra o nome para caber melhor se a janela for estreita
            radio.setText(texto.replace(" (", "\n(")) 
            layout_canais.addWidget(radio)

        self._radios_canal["rgb"].setChecked(True)
        layout_principal.addLayout(layout_canais)
        layout_principal.addSpacing(10)

        # --- Seleção da Operação Matemática ---
        rotulo_operacao = QLabel("Operação Espacial:", self)
        layout_principal.addWidget(rotulo_operacao)

        self._grupo_operacao = QButtonGroup(self)
        self._radios_operacao: dict[str, QRadioButton] = {}

        opcoes_operacao = [
            ("Correlação (Matriz Original)", "correlacao"),
            ("Convolução (Matriz Invertida 180°)", "convolucao"),
        ]

        layout_op = QHBoxLayout()
        for texto, valor in opcoes_operacao:
            radio = QRadioButton(texto, self)
            self._grupo_operacao.addButton(radio)
            self._radios_operacao[valor] = radio
            layout_op.addWidget(radio)

        self._radios_operacao["correlacao"].setChecked(True)
        layout_principal.addLayout(layout_op)
        layout_principal.addSpacing(10)

        # --- Controles de Dimensão do Kernel ---
        layout_dimensao = QHBoxLayout()
        
        rotulo_linhas = QLabel("Linhas:", self)
        self._spin_linhas = QSpinBox(self)
        self._spin_linhas.setRange(1, 21)
        self._spin_linhas.setValue(3)

        rotulo_colunas = QLabel("Colunas:", self)
        self._spin_colunas = QSpinBox(self)
        self._spin_colunas.setRange(1, 21)
        self._spin_colunas.setValue(3)

        self._btn_csv = QPushButton("Carregar de CSV", self)
        self._btn_csv.clicked.connect(self._carregar_csv)

        layout_dimensao.addWidget(rotulo_linhas)
        layout_dimensao.addWidget(self._spin_linhas)
        layout_dimensao.addSpacing(15)
        layout_dimensao.addWidget(rotulo_colunas)
        layout_dimensao.addWidget(self._spin_colunas)
        layout_dimensao.addStretch()
        layout_dimensao.addWidget(self._btn_csv)

        layout_principal.addLayout(layout_dimensao)
        layout_principal.addSpacing(10)

        # --- Grade Dinâmica de Coeficientes ---
        rotulo_matriz = QLabel("Coeficientes da Matriz:", self)
        layout_principal.addWidget(rotulo_matriz)

        self._container_grade = QWidget(self)
        self._layout_grade = QGridLayout(self._container_grade)
        self._layout_grade.setSpacing(5)
        layout_principal.addWidget(self._container_grade)

        dica = QLabel("<i>Dica: O arquivo CSV deve conter números separados por vírgula.</i>", self)
        dica.setStyleSheet("color: #777; font-size: 11px;")
        dica.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_principal.addWidget(dica)

        layout_principal.addSpacing(15)

        # --- Botões de Ação ---
        layout_botoes = QHBoxLayout()
        self._btn_aplicar = QPushButton("Aplicar", self)
        self._btn_cancelar = QPushButton("Cancelar", self)
        layout_botoes.addWidget(self._btn_aplicar)
        layout_botoes.addWidget(self._btn_cancelar)
        layout_principal.addLayout(layout_botoes)

        # --- Conexões de Ação ---
        for radio in self._radios_canal.values():
            radio.toggled.connect(self._ao_alterar_parametros)

        for radio in self._radios_operacao.values():
            radio.toggled.connect(self._ao_alterar_parametros)

        self._spin_linhas.valueChanged.connect(self._ao_mudar_dimensao)
        self._spin_colunas.valueChanged.connect(self._ao_mudar_dimensao)

        self._btn_aplicar.clicked.connect(self._ao_aplicar)
        self._btn_cancelar.clicked.connect(self.reject)

        self.setLayout(layout_principal)
        self.layout().setSizeConstraint(QVBoxLayout.SizeConstraint.SetFixedSize)

        self._desenhar_grade(3, 3)

    # ------------------------------------------------------------------
    # Leitura e Gerenciamento da Grade e Controles
    # ------------------------------------------------------------------

    def _obter_canal(self) -> str:
        for valor, radio in self._radios_canal.items():
            if radio.isChecked():
                return valor
        return "rgb"

    def _obter_operacao(self) -> str:
        for valor, radio in self._radios_operacao.items():
            if radio.isChecked():
                return valor
        return "correlacao"

    def _ao_mudar_dimensao(self) -> None:
        linhas = self._spin_linhas.value()
        colunas = self._spin_colunas.value()
        self._desenhar_grade(linhas, colunas)

    def _desenhar_grade(self, linhas: int, colunas: int) -> None:
        while self._layout_grade.count():
            item = self._layout_grade.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self._caixas_valores = []

        for linha in range(linhas):
            linha_caixas = []
            for coluna in range(colunas):
                caixa = QDoubleSpinBox(self)
                caixa.setRange(-9999.0, 9999.0)
                caixa.setSingleStep(1.0)
                caixa.setDecimals(2)
                caixa.setFixedWidth(75)
                caixa.setAlignment(Qt.AlignmentFlag.AlignCenter)

                # Inicia todos os coeficientes em 1.0 (Lembre-se de ajustar para evitar saturação)
                caixa.setValue(1.0)

                caixa.valueChanged.connect(lambda _, : self._ao_alterar_parametros())
                
                self._layout_grade.addWidget(caixa, linha, coluna)
                linha_caixas.append(caixa)
                
            self._caixas_valores.append(linha_caixas)

        self._ao_alterar_parametros()

    def _carregar_csv(self) -> None:
        caminho, _ = QFileDialog.getOpenFileName(
            self, "Abrir Arquivo de Kernel", "", "CSV Files (*.csv)"
        )

        if not caminho:
            return

        try:
            matriz_lida = np.loadtxt(caminho, delimiter=",", dtype=np.float32)

            if matriz_lida.ndim == 1:
                matriz_lida = matriz_lida.reshape(1, -1)

            linhas, colunas = matriz_lida.shape

            if linhas > 21 or colunas > 21:
                QMessageBox.warning(self, "Aviso", "O kernel no CSV é muito grande para edição visual (máx 21x21).")
                return

            self._spin_linhas.blockSignals(True)
            self._spin_colunas.blockSignals(True)

            self._spin_linhas.setValue(linhas)
            self._spin_colunas.setValue(colunas)

            self._spin_linhas.blockSignals(False)
            self._spin_colunas.blockSignals(False)

            self._desenhar_grade(linhas, colunas)

            for linha in range(linhas):
                for coluna in range(colunas):
                    caixa = self._caixas_valores[linha][coluna]
                    caixa.blockSignals(True)
                    caixa.setValue(float(matriz_lida[linha, coluna]))
                    caixa.blockSignals(False)

            self._ao_alterar_parametros()

        except Exception as erro:
            QMessageBox.critical(self, "Erro ao carregar CSV", f"Formato inválido ou leitura falhou.\n\nDetalhes:\n{erro}")

    def _obter_matriz_kernel(self) -> np.ndarray:
        linhas = len(self._caixas_valores)
        colunas = len(self._caixas_valores[0]) if linhas > 0 else 0
        kernel = np.zeros((linhas, colunas), dtype=np.float32)

        for linha in range(linhas):
            for coluna in range(colunas):
                valor = self._caixas_valores[linha][coluna].value()
                kernel[linha, coluna] = valor

        return kernel

    # ------------------------------------------------------------------
    # Lógica de processamento
    # ------------------------------------------------------------------

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        if imagem is None or imagem.size == 0:
            return imagem.copy() if imagem is not None else np.array([])

        kernel = self._obter_matriz_kernel()
        operacao = self._obter_operacao()
        canal_alvo = self._obter_canal()

        if operacao == "convolucao":
            kernel = cv2.flip(kernel, -1)

        imagem_saida = imagem.copy()

        # Isola o canal Alpha se a imagem for BGRA (4 canais)
        possui_alpha = imagem.ndim == 3 and imagem.shape[2] == 4
        if possui_alpha:
            cor_trabalho = imagem[..., :3]
            alpha = imagem[..., 3:]
        else:
            cor_trabalho = imagem
            alpha = None

        if canal_alvo == "rgb":
            # Aplica nos 3 canais simultaneamente
            imagem_filtrada = cv2.filter2D(cor_trabalho, -1, kernel)
            imagem_saida = np.clip(imagem_filtrada, 0, 255).astype(np.uint8)
        else:
            # Aplica apenas no canal selecionado
            idx_canal = {"r": 2, "g": 1, "b": 0}[canal_alvo]
            
            # Isola o canal e aplica o filtro 2D
            canal_isolado = cor_trabalho[..., idx_canal]
            canal_filtrado = cv2.filter2D(canal_isolado, -1, kernel)
            
            # Substitui o canal na imagem de trabalho aplicando saturação segura (clip)
            imagem_saida = cor_trabalho.copy()
            imagem_saida[..., idx_canal] = np.clip(canal_filtrado, 0, 255).astype(np.uint8)

        # Reconcatena o canal de opacidade (Alpha), se ele existir
        if possui_alpha:
            return np.concatenate((imagem_saida, alpha), axis=2)

        return imagem_saida

    # ------------------------------------------------------------------
    # Slots privados
    # ------------------------------------------------------------------

    def _ao_alterar_parametros(self, estado=None) -> None:
        if hasattr(self, "imagem_original"):
            imagem_processada = self.processar(self.imagem_original)
            self.preview_requested.emit(imagem_processada)

    def _ao_aplicar(self) -> None:
        if hasattr(self, "imagem_original"):
            imagem_processada = self.processar(self.imagem_original)
            self.apply_requested.emit(imagem_processada)
            self.accept()
