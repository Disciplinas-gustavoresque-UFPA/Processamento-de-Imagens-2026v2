"""
plugins/pixels/filtro_ruido_gaussiano.py
-----------------------------------------
Implementa o Ruído Gaussiano, considerando os modos de adição e substituição.
Modo de substituição inspirado no filtro Hurl do GIMP.

Substitui ou adiciona valores aleatórios baseados em uma distribuição 
Gaussiana a uma porcentagem específica de pixels da imagem.

Permite selecionar
canais específicos e fixar a semente (seed) de aleatoriedade para
garantir reprodutibilidade.
"""

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
)

from core.plugin_base import PluginBase


class FiltroRuidoGaussiano(PluginBase):
    """Plugin para aplicação de Ruído Gaussiano (Aditivo ou Substitutivo) com Seed."""
    
    display_name = "Ruído Gaussiano"

    # ------------------------------------------------------------------
    # Interface (setup_ui)
    # ------------------------------------------------------------------

    def setup_ui(self) -> None:
        """Constrói as opções de canais, modo de operação, sliders numéricos e controle de semente."""
        layout_principal = QVBoxLayout(self)

        # --- Modo de Operação (Adição vs Substituição) ---
        rotulo_modo = QLabel("Modo de Operação do Ruído:", self)
        layout_principal.addWidget(rotulo_modo)

        self._grupo_modos = QButtonGroup(self)
        self._radios_modo: dict[str, QRadioButton] = {}

        opcoes_modo = [
            ("Adição (Tradicional)", "aditivo"),
            ("Substituição (Estilo Hurl)", "substitutivo"),
        ]

        for texto, valor in opcoes_modo:
            radio = QRadioButton(texto, self)
            self._grupo_modos.addButton(radio)
            self._radios_modo[valor] = radio
            layout_principal.addWidget(radio)

        self._radios_modo["aditivo"].setChecked(True)  # Aditivo como padrão comercial
        layout_principal.addSpacing(10)

        # --- Seleção do Canal Afetado ---
        rotulo_canal = QLabel("Canal afetado pelo ruído:", self)
        layout_principal.addWidget(rotulo_canal)

        self._grupo_canais = QButtonGroup(self)
        self._radios_canal: dict[str, QRadioButton] = {}

        opcoes_canal = [
            ("Todos os Canais (RGB)", "rgb"),
            ("Canal Vermelho (R)", "r"),
            ("Canal Verde (G)", "g"),
            ("Canal Azul (B)", "b"),
        ]

        for texto, valor in opcoes_canal:
            radio = QRadioButton(texto, self)
            self._grupo_canais.addButton(radio)
            self._radios_canal[valor] = radio
            layout_principal.addWidget(radio)

        self._radios_canal["rgb"].setChecked(True)
        layout_principal.addSpacing(10)

        # --- Slider de Porcentagem (0 a 100%) ---
        self._rotulo_porcentagem = QLabel("Porcentagem de Pixels Afetados: 20%", self)
        layout_principal.addWidget(self._rotulo_porcentagem)

        self._slider_porcentagem = QSlider(Qt.Orientation.Horizontal, self)
        self._slider_porcentagem.setRange(0, 100)
        self._slider_porcentagem.setValue(20)
        layout_principal.addWidget(self._slider_porcentagem)

        layout_principal.addSpacing(10)

        # --- Slider de Desvio Padrão (Gaussiano) ---
        self._rotulo_desvio = QLabel("Desvio Padrão do Ruído: 50", self)
        layout_principal.addWidget(self._rotulo_desvio)

        self._slider_desvio = QSlider(Qt.Orientation.Horizontal, self)
        self._slider_desvio.setRange(1, 127)
        self._slider_desvio.setValue(50)
        layout_principal.addWidget(self._slider_desvio)

        layout_principal.addSpacing(10)

        # --- Controle de Semente (Seed) ---
        layout_seed = QHBoxLayout()
        self._check_seed = QCheckBox("Fixar Semente (Seed):", self)
        
        self._spin_seed = QSpinBox(self)
        self._spin_seed.setRange(0, 9999999) # Range genérico para sementes
        self._spin_seed.setValue(42)
        self._spin_seed.setEnabled(False) # Inicia desabilitado até o checkbox ser marcado

        layout_seed.addWidget(self._check_seed)
        layout_seed.addWidget(self._spin_seed)
        layout_principal.addLayout(layout_seed)

        layout_principal.addSpacing(15)

        # --- Botões de Ação ---
        layout_botoes = QHBoxLayout()
        self._btn_aplicar = QPushButton("Aplicar", self)
        self._btn_cancelar = QPushButton("Cancelar", self)
        layout_botoes.addWidget(self._btn_aplicar)
        layout_botoes.addWidget(self._btn_cancelar)
        layout_principal.addLayout(layout_botoes)

        # --- Conexões de Sinais (Eventos) ---
        for radio in self._radios_modo.values():
            radio.toggled.connect(self._ao_alterar_parametros)
    
        for radio in self._radios_canal.values():
            radio.toggled.connect(self._ao_alterar_parametros)

        self._slider_porcentagem.valueChanged.connect(self._ao_mover_sliders)
        self._slider_desvio.valueChanged.connect(self._ao_mover_sliders)
        
        # Habilita/desabilita o SpinBox dependendo do Checkbox
        self._check_seed.toggled.connect(self._spin_seed.setEnabled)
        self._check_seed.toggled.connect(self._ao_alterar_parametros)
        self._spin_seed.valueChanged.connect(self._ao_alterar_parametros)
        
        self._btn_aplicar.clicked.connect(self._ao_aplicar)
        self._btn_cancelar.clicked.connect(self.reject)

        self.setLayout(layout_principal)
        self.setMinimumWidth(340)

        # Dispara o preview inicial
        self._ao_alterar_parametros(True)

    def _obter_canal(self) -> str:
        """Verifica qual rádio button está marcado para a escolha do canal."""
        for valor, radio in self._radios_canal.items():
            if radio.isChecked():
                return valor
        return "rgb"

    def _obter_modo(self) -> str:
        """Verifica se o modo selecionado é aditivo ou substitutivo."""
        for valor, radio in self._radios_modo.items():
            if radio.isChecked():
                return valor
        return "aditivo"

    # ------------------------------------------------------------------
    # Lógica de processamento
    # ------------------------------------------------------------------

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        """Aplica o ruído gaussiano (aditivo ou substitutivo) conforme parâmetros."""
        
        porcentagem = self._slider_porcentagem.value() / 100.0
        desvio = self._slider_desvio.value()
        canal_alvo = self._obter_canal()
        modo = self._obter_modo()
        
        if porcentagem == 0.0:
            return imagem.copy()

        # Configuração da semente aleatória
        if self._check_seed.isChecked():
            semente = self._spin_seed.value()
            rng = np.random.default_rng(semente)
        else:
            # Se não fixar, cria um gerador totalmente livre a cada chamada
            rng = np.random.default_rng()

        altura, largura, canais = imagem.shape

        # Para o modo aditivo, precisa do cálculo em float para evitar overflow/underflow
        imagem_trabalho = imagem.astype(np.float32) if modo == "aditivo" else imagem.copy()

        # Criação da máscara de pixels afetados
        mascara_2d = rng.random((altura, largura)) < porcentagem

        # Seleção de canal e substituição de pixels pelo ruído
        if canal_alvo == "rgb":
            if modo == "substitutivo":
                # Lógica Original: Substitui o valor do pixel focado em torno do cinza médio (128)
                ruido = rng.normal(loc=128.0, scale=desvio, size=imagem.shape)
                ruido = np.clip(ruido, 0, 255).astype(np.uint8)
                mascara_3d = np.expand_dims(mascara_2d, axis=-1)
                imagem_saida = np.where(mascara_3d, ruido, imagem_trabalho)
            else:
                # Lógica Aditiva: Soma/subtrai o ruído centrado em 0 da imagem original
                ruido = rng.normal(loc=0.0, scale=desvio, size=imagem.shape)
                mascara_3d = np.expand_dims(mascara_2d, axis=-1)
                ruido_filtrado = np.where(mascara_3d, ruido, 0.0)
                imagem_saida = np.clip(imagem_trabalho + ruido_filtrado, 0, 255).astype(np.uint8)
            
        else:
            idx_canal = {"r": 0, "g": 1, "b": 2}[canal_alvo]
            
            if modo == "substitutivo":
                ruido_canal = rng.normal(loc=128.0, scale=desvio, size=(altura, largura))
                ruido_canal = np.clip(ruido_canal, 0, 255).astype(np.uint8)
                
                imagem_saida = imagem_trabalho
                imagem_saida[..., idx_canal] = np.where(
                    mascara_2d, 
                    ruido_canal, 
                    imagem_trabalho[..., idx_canal]
                )
            else:
                ruido_canal = rng.normal(loc=0.0, scale=desvio, size=(altura, largura))
                ruido_filtrado = np.where(mascara_2d, ruido_canal, 0.0)
                
                imagem_saida = imagem_trabalho.copy()
                imagem_saida[..., idx_canal] = np.clip(
                    imagem_trabalho[..., idx_canal] + ruido_filtrado, 0, 255
                )
                imagem_saida = imagem_saida.astype(np.uint8)

        return imagem_saida

    # ------------------------------------------------------------------
    # Slots privados
    # ------------------------------------------------------------------

    def _ao_mover_sliders(self) -> None:
        """Atualiza os textos numéricos da interface quando os sliders são movimentados."""
        self._rotulo_porcentagem.setText(f"Porcentagem de Pixels Afetados: {self._slider_porcentagem.value()}%")
        self._rotulo_desvio.setText(f"Desvio Padrão do Ruído: {self._slider_desvio.value()}")
        self._ao_alterar_parametros(True)

    def _ao_alterar_parametros(self, estado_qualquer=None) -> None:
        """Regera o processamento para mostrar o preview ao vivo no canvas."""
        imagem_processada = self.processar(self.imagem_original)
        self.preview_requested.emit(imagem_processada)

    def _ao_aplicar(self) -> None:
        """Aplica o filtro na matriz oficial e fecha a janela."""
        imagem_processada = self.processar(self.imagem_original)
        self.apply_requested.emit(imagem_processada)
        self.accept()
