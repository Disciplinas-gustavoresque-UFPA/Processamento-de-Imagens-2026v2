"""
plugins/imagem/transformar/seam_carving.py
-----------------------------------------
Plugin: Redimensionamento sensível ao conteúdo (Seam Carving).

Esta ferramenta permite reduzir as dimensões da imagem (largura e/ou altura)
preservando os objetos e estruturas de maior interesse visual. Diferente 
de um corte (crop) geométrico, o algoritmo identifica e remove iterativamente 
"costuras" (seams) contínuas de pixels que possuem a menor energia visual.

Arquitetura e Implementação:
* Matemática: Utiliza o filtro nativo de Sobel (cv2) para o mapa de energia e 
  Programação Dinâmica vetorizada (NumPy) para encontrar o caminho de menor custo.
* Concorrência: O processamento é delegado a uma Worker Thread (SeamCarvingWorker), 
  garantindo que a interface principal do editor não congele durante o cálculo.
* Interação: Controles deslizantes baseados em porcentagem (limite de 50%) 
  para reduzir a carga cognitiva, traduzindo automaticamente para pixels finais.

Nota sobre a Estratégia de Redução:
Quando ambas as dimensões são reduzidas, o algoritmo executa primeiro todas as 
remoções verticais e depois as horizontais. Essa estratégia simplifica a 
implementação e reutiliza o mesmo núcleo algorítmico através da transposição da 
matriz, em detrimento de possíveis ganhos de qualidade obtidos por estratégias 
adaptativas.
"""
import cv2
import numpy as np
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QGroupBox,
    QMessageBox,
    QSlider
)
from core.plugin_base import PluginBase


class SeamCarvingWorker(QThread):
    """
    Worker Thread: Executa a matemática do Seam Carving em segundo plano.
    """
    progresso = Signal(int)       
    concluido = Signal(np.ndarray) 

    def __init__(self, imagem: np.ndarray, largura_alvo: int, altura_alvo: int, parent=None):
        super().__init__(parent)
        self.imagem = imagem
        self.largura_alvo = largura_alvo
        self.altura_alvo = altura_alvo

    def _calcular_energia(self, imagem: np.ndarray) -> np.ndarray:
        if len(imagem.shape) == 3:
            cinza = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)
        else:
            cinza = imagem.copy()
            
        sobel_x = cv2.Sobel(cinza, cv2.CV_64F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(cinza, cv2.CV_64F, 0, 1, ksize=3)
        return np.abs(sobel_x) + np.abs(sobel_y)

    def _encontrar_seam_vertical(self, energia: np.ndarray) -> np.ndarray:
        linhas, colunas = energia.shape
        matriz_custo = energia.copy()
        backtrack = np.zeros_like(energia, dtype=int)

        for i in range(1, linhas):
            linha_ant = matriz_custo[i - 1]
            
            esq = np.roll(linha_ant, 1)
            esq[0] = np.inf
            dir = np.roll(linha_ant, -1)
            dir[-1] = np.inf
            cen = linha_ant

            empilhado = np.vstack([esq, cen, dir])
            matriz_custo[i] += np.min(empilhado, axis=0)
            escolhas = np.argmin(empilhado, axis=0)
            
            indices_origem = np.arange(colunas) + (escolhas - 1)
            backtrack[i] = np.clip(indices_origem, 0, colunas - 1)

        seam = np.zeros(linhas, dtype=int)
        seam[-1] = np.argmin(matriz_custo[-1])
        
        for i in range(linhas - 2, -1, -1):
            seam[i] = backtrack[i + 1, seam[i + 1]]
            
        return seam

    def _remover_seam_vertical(self, imagem: np.ndarray, seam: np.ndarray) -> np.ndarray:
        linhas, colunas = imagem.shape[:2]
        canais = imagem.shape[2] if len(imagem.shape) == 3 else 1
        
        mascara = np.ones((linhas, colunas), dtype=bool)
        mascara[np.arange(linhas), seam] = False
        
        if canais == 3:
            mascara_3d = np.stack([mascara]*3, axis=2)
            return imagem[mascara_3d].reshape(linhas, colunas - 1, 3)
        else:
            return imagem[mascara].reshape(linhas, colunas - 1)

    def run(self):
        img_atual = self.imagem.copy()
        linhas_orig, colunas_orig = img_atual.shape[:2]
        
        passos_largura = max(0, colunas_orig - self.largura_alvo)
        passos_altura = max(0, linhas_orig - self.altura_alvo)
        passos_totais = passos_largura + passos_altura

        if passos_totais == 0:
            self.concluido.emit(img_atual)
            return

        passo_atual = 0

        # 1. Redução de Largura (Costuras Verticais)
        for _ in range(passos_largura):
            energia = self._calcular_energia(img_atual)
            seam = self._encontrar_seam_vertical(energia)
            img_atual = self._remover_seam_vertical(img_atual, seam)
            
            passo_atual += 1
            self.progresso.emit(int((passo_atual / passos_totais) * 100))

        # 2. Redução de Altura (Costuras Horizontais via Transposição)
        if passos_altura > 0:
            img_atual = np.swapaxes(img_atual, 0, 1)
            
            for _ in range(passos_altura):
                energia = self._calcular_energia(img_atual)
                seam = self._encontrar_seam_vertical(energia)
                img_atual = self._remover_seam_vertical(img_atual, seam)
                
                passo_atual += 1
                self.progresso.emit(int((passo_atual / passos_totais) * 100))
                
            img_atual = np.swapaxes(img_atual, 0, 1)

        self.concluido.emit(img_atual)


class PluginSeamCarving(PluginBase):
    """Gerencia a interface gráfica e os eventos do plugin de Seam Carving."""
    display_name = "Seam Carving"

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # 1. Painel de Informações do Sistema
        grupo_info = QGroupBox("Status da Imagem")
        info_layout = QVBoxLayout()
        self.lbl_info = QLabel("Carregando informações da imagem...")
        self.lbl_info.setWordWrap(True)
        info_layout.addWidget(self.lbl_info)
        grupo_info.setLayout(info_layout)
        layout.addWidget(grupo_info)

        # 2. Painel de Configurações Interativas (Sliders)
        grupo_config = QGroupBox("Redimensionamento Sensível ao Conteúdo")
        config_layout = QVBoxLayout()
        
        lbl_explicacao = QLabel(
            "<i>Deslize para definir a porcentagem de redução desejada. "
            "O Seam Carving encolherá a imagem removendo as áreas com menos detalhes.</i>"
        )
        lbl_explicacao.setWordWrap(True)
        config_layout.addWidget(lbl_explicacao)

        # --- Controles de Largura ---
        lay_largura_textos = QHBoxLayout()
        lay_largura_textos.addWidget(QLabel("<b>Reduzir Largura:</b>"))
        self.lbl_largura_val = QLabel("0% (-- px)") 
        self.lbl_largura_val.setAlignment(Qt.AlignmentFlag.AlignRight)
        lay_largura_textos.addWidget(self.lbl_largura_val)
        
        self.slider_largura = QSlider(Qt.Orientation.Horizontal)
        self.slider_largura.setRange(0, 50) 
        self.slider_largura.setValue(0)
        self.slider_largura.valueChanged.connect(self._atualizar_textos_dinamicos)

        config_layout.addLayout(lay_largura_textos)
        config_layout.addWidget(self.slider_largura)

        # --- Controles de Altura ---
        lay_altura_textos = QHBoxLayout()
        lay_altura_textos.addWidget(QLabel("<b>Reduzir Altura:</b>"))
        self.lbl_altura_val = QLabel("0% (-- px)") 
        self.lbl_altura_val.setAlignment(Qt.AlignmentFlag.AlignRight)
        lay_altura_textos.addWidget(self.lbl_altura_val)
        
        self.slider_altura = QSlider(Qt.Orientation.Horizontal)
        self.slider_altura.setRange(0, 50) 
        self.slider_altura.setValue(0)
        self.slider_altura.valueChanged.connect(self._atualizar_textos_dinamicos)

        config_layout.addLayout(lay_altura_textos)
        config_layout.addWidget(self.slider_altura)

        grupo_config.setLayout(config_layout)
        layout.addWidget(grupo_config)

        # 3. Botão de Ação
        self.btn_aplicar = QPushButton("Aplicar no Editor")
        self.btn_aplicar.clicked.connect(self._ao_aplicar)
        layout.addWidget(self.btn_aplicar)

        self.setLayout(layout)
        self.worker = None 
        
        self.largura_base = 0
        self.altura_base = 0

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, "imagem_original"):
            self.altura_base, self.largura_base = self.imagem_original.shape[:2]
            self.lbl_info.setText(
                f"<b>Resolução Original:</b> {self.largura_base} px (L) x {self.altura_base} px (A)"
            )
            self.slider_largura.setValue(0)
            self.slider_altura.setValue(0)
            self._atualizar_textos_dinamicos()

    def _calcular_alvos(self):
        pct_largura = self.slider_largura.value()
        pct_altura = self.slider_altura.value()
        
        largura_alvo = int(self.largura_base * (1 - (pct_largura / 100.0)))
        altura_alvo = int(self.altura_base * (1 - (pct_altura / 100.0)))
        
        return largura_alvo, altura_alvo

    def _atualizar_textos_dinamicos(self):
        if self.largura_base == 0:
            return

        largura_alvo, altura_alvo = self._calcular_alvos()
        pct_largura = self.slider_largura.value()
        pct_altura = self.slider_altura.value()

        self.lbl_largura_val.setText(f"-{pct_largura}% (Restará {largura_alvo} px)")
        self.lbl_altura_val.setText(f"-{pct_altura}% (Restará {altura_alvo} px)")

    def _atualizar_progresso(self, porcentagem: int):
        self.btn_aplicar.setText(f"Processando matriz... {porcentagem}%")

    def _ao_concluir(self, img_processada: np.ndarray):
        self.apply_requested.emit(img_processada)
        self.accept()

    def _ao_aplicar(self):
        if hasattr(self, "imagem_original"):
            pct_largura = self.slider_largura.value()
            pct_altura = self.slider_altura.value()
            
            if pct_largura == 0 and pct_altura == 0:
                self.reject()
                return

            largura_alvo, altura_alvo = self._calcular_alvos()

            self.btn_aplicar.setEnabled(False)
            self.slider_largura.setEnabled(False)
            self.slider_altura.setEnabled(False)

            self.worker = SeamCarvingWorker(self.imagem_original, largura_alvo, altura_alvo)
            self.worker.progresso.connect(self._atualizar_progresso)
            self.worker.concluido.connect(self._ao_concluir)
            
            self.worker.start()