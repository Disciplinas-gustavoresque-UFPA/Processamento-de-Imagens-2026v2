"""
plugins/filtros/low_poly.py
-----------------------------------------
Plugin: Efeito Low Poly (Mosaico Geométrico).

O que este plugin faz:
Aplica a estética "Low Poly" à imagem (comum em jogos 3D clássicos), substituindo os pixels originais por 
uma malha conectada de triângulos coloridos de preenchimento sólido.

Impacto do Ajuste (Complexidade):
Controla a quantidade de pontos gerados na malha. Valores baixos produzem um 
resultado mais abstrato e geométrico, enquanto valores altos preservam os 
detalhes e a silhueta da imagem original.

Arquitetura e Implementação:
* Distribuição Adaptativa: Usa o filtro de Canny (cv2) para identificar bordas, 
  concentrando triângulos menores em áreas de maior detalhe e triângulos maiores 
  em áreas homogêneas.
* Triangulação: Utiliza a Triangulação de Delaunay (`cv2.Subdiv2D`) para conectar 
  os pontos e preencher a área sem sobreposições ou lacunas.
* Cor: Pinta cada polígono com a cor do seu centroide, mantendo a fidelidade 
  à paleta original.
* Concorrência: O processamento ocorre em uma Worker Thread (`QThread`) com 
  verificações de interrupção, mantendo a interface responsiva durante o uso 
  do controle deslizante.
"""
import cv2
import numpy as np
from typing import Optional
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QGroupBox,
    QSlider
)
from core.plugin_base import PluginBase

# ==============================================================================
# CONSTANTES DE CONFIGURAÇÃO
# ==============================================================================
CANNY_LIMIAR_MIN = 50
CANNY_LIMIAR_MAX = 150
GAUSSIAN_BLUR_KSIZE = (5, 5)
PROPORCAO_PONTOS_BORDAS = 0.75

PROGRESSO_INICIAL = 5
PROGRESSO_CANNY = 15
PROGRESSO_TRIANGULACAO = 35
PROGRESSO_MAX = 100

PONTOS_MIN = 1000
PONTOS_MAX = 15000
PONTOS_PADRAO = 5000
SLIDER_PASSO_UNICO = 100
SLIDER_PASSO_PAGINA = 500

class LowPolyWorker(QThread):
    progresso = Signal(int)       
    concluido = Signal(np.ndarray) 

    def __init__(self, imagem: np.ndarray, num_pontos: int, parent=None):
        super().__init__(parent)
        self.imagem: np.ndarray = imagem
        self.num_pontos: int = num_pontos
        self._abortado: bool = False

    def abortar(self):
        self._abortado = True

    def _detectar_bordas(self, img: np.ndarray) -> np.ndarray:
        """Converte para escala de cinza de forma segura e aplica Canny."""
        if len(img.shape) == 3:
            if img.shape[2] == 4:
                cinza = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
            elif img.shape[2] == 3:
                cinza = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            else:
                cinza = img[:, :, 0].copy()
        else:
            cinza = img.copy()

        cinza_blur = cv2.GaussianBlur(cinza, GAUSSIAN_BLUR_KSIZE, 0)
        return cv2.Canny(cinza_blur, CANNY_LIMIAR_MIN, CANNY_LIMIAR_MAX)

    def _distribuir_pontos(self, bordas: np.ndarray, altura: int, largura: int) -> np.ndarray:
        """Distribui pontos baseados nas bordas e espalha o resto aleatoriamente."""
        coords_bordas = np.argwhere(bordas > 0)
        qtd_bordas = min(len(coords_bordas), int(self.num_pontos * PROPORCAO_PONTOS_BORDAS))
        
        if qtd_bordas > 0:
            indices = np.random.choice(len(coords_bordas), qtd_bordas, replace=False)
            pontos_selecionados = coords_bordas[indices]
        else:
            pontos_selecionados = np.empty((0, 2), dtype=int)

        qtd_aleatorios = self.num_pontos - qtd_bordas
        if qtd_aleatorios > 0:
            y_rand = np.random.randint(0, altura, qtd_aleatorios)
            x_rand = np.random.randint(0, largura, qtd_aleatorios)
            pontos_aleatorios = np.column_stack((y_rand, x_rand))
            if len(pontos_selecionados) > 0:
                pontos_selecionados = np.vstack((pontos_selecionados, pontos_aleatorios))
            else:
                pontos_selecionados = pontos_aleatorios

        cantos = np.array([[0, 0], [0, largura - 1], [altura - 1, 0], [altura - 1, largura - 1]])
        pontos_selecionados = np.vstack((pontos_selecionados, cantos))

        return np.unique(pontos_selecionados, axis=0)

    def _triangular_e_renderizar(self, img_atual: np.ndarray, pontos: np.ndarray, altura: int, largura: int) -> np.ndarray:
        """Aplica Delaunay e renderiza os triângulos baseados na cor do centroide."""
        subdiv = cv2.Subdiv2D((0, 0, largura, altura))
        total_pontos = len(pontos)
        
        for i, p in enumerate(pontos):
            if self._abortado: 
                return None
            
            subdiv.insert((float(p[1]), float(p[0])))
            if i % max(1, total_pontos // 10) == 0:
                passo = PROGRESSO_CANNY + int((i / total_pontos) * (PROGRESSO_TRIANGULACAO - PROGRESSO_CANNY))
                self.progresso.emit(passo)

        if self._abortado:
            return None

        triangulos = subdiv.getTriangleList()
        total_triangulos = len(triangulos)
        
        saida = np.zeros_like(img_atual)

        for i, t in enumerate(triangulos):
            if self._abortado: 
                return None
            
            pt1 = (np.clip(int(t[0]), 0, largura - 1), np.clip(int(t[1]), 0, altura - 1))
            pt2 = (np.clip(int(t[2]), 0, largura - 1), np.clip(int(t[3]), 0, altura - 1))
            pt3 = (np.clip(int(t[4]), 0, largura - 1), np.clip(int(t[5]), 0, altura - 1))
            
            cx = (pt1[0] + pt2[0] + pt3[0]) // 3
            cy = (pt1[1] + pt2[1] + pt3[1]) // 3
            cor_centro = img_atual[cy, cx].tolist()
            
            cv2.fillConvexPoly(saida, np.array([pt1, pt2, pt3], dtype=np.int32), cor_centro, cv2.LINE_AA)

            if total_triangulos > 0 and i % max(1, total_triangulos // 20) == 0:
                passo = PROGRESSO_TRIANGULACAO + int((i / total_triangulos) * (PROGRESSO_MAX - PROGRESSO_TRIANGULACAO))
                self.progresso.emit(passo)

        return saida

    def run(self):
        img_atual = self.imagem.copy()
        altura, largura = img_atual.shape[:2]

        if self._abortado: return
        self.progresso.emit(PROGRESSO_INICIAL)

        bordas = self._detectar_bordas(img_atual)
        if self._abortado: return
        self.progresso.emit(PROGRESSO_CANNY)

        pontos_selecionados = self._distribuir_pontos(bordas, altura, largura)
        if self._abortado: return
        
        saida = self._triangular_e_renderizar(img_atual, pontos_selecionados, altura, largura)

        if not self._abortado and saida is not None:
            self.concluido.emit(saida)

class PluginLowPoly(PluginBase):
    display_name = "Efeito Low Poly"

    def setup_ui(self):
        layout = QVBoxLayout(self)

        grupo_config = QGroupBox("Ajuste da Malha")
        config_layout = QVBoxLayout()
        
        lbl_explicacao = QLabel(
            "<i>O Low Poly estiliza a foto convertendo-a em uma malha de triângulos "
            "coloridos (mosaico geométrico). Deslize e solte o controle para aplicar. "
            "Menos pontos geram um efeito mais abstrato, enquanto mais pontos "
            "preservam os detalhes originais.</i>"
        )
        lbl_explicacao.setWordWrap(True)
        config_layout.addWidget(lbl_explicacao)

        lay_pontos_textos = QHBoxLayout()
        lay_pontos_textos.addWidget(QLabel("<b>Complexidade:</b>"))
        self.lbl_pontos_val = QLabel(f"{PONTOS_PADRAO} pontos") 
        self.lbl_pontos_val.setAlignment(Qt.AlignmentFlag.AlignRight)
        lay_pontos_textos.addWidget(self.lbl_pontos_val)
        
        self.slider_pontos = QSlider(Qt.Orientation.Horizontal)
        self.slider_pontos.setRange(PONTOS_MIN, PONTOS_MAX) 
        self.slider_pontos.setValue(PONTOS_PADRAO)
        self.slider_pontos.setSingleStep(SLIDER_PASSO_UNICO) 
        self.slider_pontos.setPageStep(SLIDER_PASSO_PAGINA) 
        
        self.slider_pontos.valueChanged.connect(self._ao_mexer_slider)
        self.slider_pontos.sliderReleased.connect(self._iniciar_renderizacao)

        config_layout.addLayout(lay_pontos_textos)
        config_layout.addWidget(self.slider_pontos)
        grupo_config.setLayout(config_layout)
        layout.addWidget(grupo_config)

        self.btn_aplicar = QPushButton("Aplicar Filtro")
        self.btn_aplicar.clicked.connect(self.accept)
        layout.addWidget(self.btn_aplicar)

        self.setLayout(layout)
        
        self.worker: Optional[LowPolyWorker] = None 

        self.timer_debounce = QTimer(self)
        self.timer_debounce.setSingleShot(True)
        self.timer_debounce.setInterval(500) 
        self.timer_debounce.timeout.connect(self._iniciar_renderizacao)

    def showEvent(self, event):
        super().showEvent(event)
        self.lbl_pontos_val.setText(f"{self.slider_pontos.value()} pontos")
        self.btn_aplicar.setText("Aplicar Filtro")
        self.btn_aplicar.setEnabled(True)

    def _ao_mexer_slider(self):
        self.lbl_pontos_val.setText(f"{self.slider_pontos.value()} pontos")
        self.btn_aplicar.setEnabled(False)
        
        if self.slider_pontos.isSliderDown():
            self.btn_aplicar.setText("Solte para atualizar...")
        else:
            self.btn_aplicar.setText("Aguardando ajuste...")
            self.timer_debounce.start()

    def _limpar_worker(self):
        """Centraliza o encerramento e a liberação de memória da Thread."""
        if self.worker is not None:
            if self.worker.isRunning():
                self.worker.abortar()
                self.worker.wait()
            self.worker.deleteLater()
            self.worker = None

    def _iniciar_renderizacao(self):
        if not hasattr(self, "imagem_original"): 
            return

        self.timer_debounce.stop() 
        self._limpar_worker()

        self.btn_aplicar.setEnabled(False)
        self.btn_aplicar.setText("Calculando Malha... 0%")
        
        self.worker = LowPolyWorker(self.imagem_original, self.slider_pontos.value())
        self.worker.progresso.connect(self._atualizar_progresso)
        self.worker.concluido.connect(self._ao_concluir_worker)
        self.worker.start()

    def _atualizar_progresso(self, porcentagem: int):
        self.btn_aplicar.setText(f"Calculando Malha... {porcentagem}%")

    def _ao_concluir_worker(self, imagem_processada: np.ndarray):
        self.btn_aplicar.setText("Aplicar Filtro")
        self.btn_aplicar.setEnabled(True)
        self.apply_requested.emit(imagem_processada)
        self._limpar_worker()

    def reject(self):
        self._limpar_worker()
        if hasattr(self, "imagem_original"):
            self.apply_requested.emit(self.imagem_original)
        super().reject()

    def accept(self):
        self._limpar_worker()
        super().accept()