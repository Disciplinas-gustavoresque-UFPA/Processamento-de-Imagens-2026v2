"""
plugins/filtros/filtro_espectro_tdf.py
-----------------------------------------
Plugin para geração e visualização do espectro de magnitude
utilizando a Transformada Discreta de Fourier (TDF).

Gera o resultado final em uma nova aba com o nome
provisório herdado da imagem original de origem.
"""

import cv2
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)

from core.plugin_base import PluginBase


class FiltroEspectroTDF(PluginBase):
    """Plugin para visualização do Espectro de Frequência da imagem."""
    
    display_name = "Espectro de Fourier (TDF)"

    # ------------------------------------------------------------------
    # Interface (setup_ui)
    # ------------------------------------------------------------------

    def setup_ui(self) -> None:
        """Cria os controles para selecionar o canal de análise e os botões de ação."""
        layout_principal = QVBoxLayout(self)

        # --- Seleção da Origem da Imagem ---
        rotulo_metodo = QLabel("Canal para análise espectral:", self)
        layout_principal.addWidget(rotulo_metodo)

        self._grupo_metodos = QButtonGroup(self)
        self._radios_metodo: dict[str, QRadioButton] = {}

        opcoes = [
            ("Média em Tons de Cinza", "media"),
            ("Canal Vermelho (R)", "r"),
            ("Canal Verde (G)", "g"),
            ("Canal Azul (B)", "b"),
        ]

        for texto, valor in opcoes:
            radio = QRadioButton(texto, self)
            self._grupo_metodos.addButton(radio)
            self._radios_metodo[valor] = radio
            layout_principal.addWidget(radio)

        # Define a Média como padrão
        self._radios_metodo["media"].setChecked(True)

        layout_principal.addSpacing(15)

        # --- Botões de Ação ---
        layout_botoes = QHBoxLayout()
        self._btn_aplicar = QPushButton("Aplicar", self)
        self._btn_cancelar = QPushButton("Cancelar", self)
        layout_botoes.addWidget(self._btn_aplicar)
        layout_botoes.addWidget(self._btn_cancelar)
        layout_principal.addLayout(layout_botoes)

        # --- Conexões de Sinais (Eventos) ---
        for radio in self._radios_metodo.values():
            radio.toggled.connect(self._ao_alterar_parametros)

        self._btn_aplicar.clicked.connect(self._ao_aplicar)
        self._btn_cancelar.clicked.connect(self.reject)

        self.setLayout(layout_principal)
        self.setMinimumWidth(320)

        # Força o primeiro preview ao carregar a interface
        self._ao_alterar_parametros(True)

    def _obter_metodo(self) -> str:
        """Verifica qual rádio button está marcado e retorna a sua chave."""
        for valor, radio in self._radios_metodo.items():
            if radio.isChecked():
                return valor
        return "media"

    # ------------------------------------------------------------------
    # Lógica de processamento
    # ------------------------------------------------------------------

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        """Calcula o espectro de magnitude via TDF e formata para exibição."""
        metodo = self._obter_metodo()

        # 1) Extração do canal escolhido via slicing:
        if metodo == "r":
            canal_base = imagem[..., 0]
        elif metodo == "g":
            canal_base = imagem[..., 1]
        elif metodo == "b":
            canal_base = imagem[..., 2]
        else:
            canal_base = np.mean(imagem, axis=2).astype(np.uint8)

        # 2) Aplicação da Transformada Discreta de Fourier (2D)
        f = np.fft.fft2(canal_base)

        # 3) Deslocamento: Traz as baixas frequências para o centro geométrico
        fshift = np.fft.fftshift(f)

        # 4) Espectro de Magnitude
        magnitude = np.abs(fshift)

        # 5) Escala Logarítmica
        espectro_log = 20 * np.log(magnitude + 1e-8)

        # 6) Normalização e Casting
        espectro_normalizado = cv2.normalize(
            espectro_log, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U
        )

        # 7) Retorno: Matriz 3D (RGB)
        return np.stack((espectro_normalizado, espectro_normalizado, espectro_normalizado), axis=-1)

    # ------------------------------------------------------------------
    # Slots privados e manipulação de Abas
    # ------------------------------------------------------------------

    def _ao_alterar_parametros(self, marcado: bool) -> None:
        """Regera o processamento para mostrar o preview ao vivo no canvas."""
        if not marcado:
            return
        imagem_processada = self.processar(self.imagem_original)
        self.preview_requested.emit(imagem_processada)

    def _ao_aplicar(self) -> None:
        """Gera a imagem espectral final e a insere usando o motor nativo do app."""
        imagem_processada = self.processar(self.imagem_original)
        
        # Captura a instância da JanelaPrincipal
        janela_principal = self.parent()
        
        if janela_principal and hasattr(janela_principal, "_adicionar_documento_imagem"):
            
            # Captura o nome do arquivo da imagem original
            indice_atual = janela_principal.tabs.currentIndex()
            nome_original = janela_principal.tabs.tabText(indice_atual).replace("*", "").strip()
            
            # Remove a extensão para evitar "espectro_fourier_imagem.png.png"
            if "." in nome_original:
                nome_original = nome_original.rsplit(".", 1)[0]
                
            nome_aba = f"espectro_fourier_{nome_original}.png"
            caminho_virtual = f"/{nome_aba}" 
            
            # Cria a imagem do espectro em uma nova aba
            janela_principal._adicionar_documento_imagem(
                caminho=caminho_virtual,
                imagem_bgr=imagem_processada,
                nome_aba=nome_aba,
                tooltip="Arquivo não salvo gerado por Análise Espectral",
                modificado=True, # Força o asterisco e o pedido para salvar ao fechar
                mensagem_status=f"Espectro funcional gerado: {nome_aba}"
            )

        # Fecha o diálogo do filtro limpando o preview da aba de origem
        self.reject()
