"""
plugins/pixels/filtro_transformacao_por_partes.py
-----------------------------------------
Plugin para Transformação Linear por Partes (Piecewise Linear Transformation).

Implementa um gráfico interativo onde o usuário pode adicionar, mover e 
remover pontos de controle. Inclui seleção de canal (RGB, R, G, B) com
feedback visual de cores.
"""

import cv2
import numpy as np
from PySide6.QtCore import Qt, Signal, QPointF
from PySide6.QtGui import QPainter, QPen, QColor, QBrush, QMouseEvent
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from core.plugin_base import PluginBase

# ==============================================================================
# COMPONENTE CUSTOMIZADO: Gráfico Interativo
# ==============================================================================

class WidgetCurvaInterativa(QWidget):
    """
    Componente visual que desenha a grade e gerencia a interação do usuário
    com os pontos de controle da transformação por partes.
    """
    curva_alterada = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(280, 280)
        self.margem = 20
        self.area_plot = 240 # 280 - 2*20

        # Cor da linha do gráfico (muda conforme o canal selecionado)
        self.cor_curva = QColor("#00d7ff") # Ciano por padrão (RGB)

        # Pontos da curva normalizados entre [0.0, 1.0]
        self.pontos = [QPointF(0.0, 0.0), QPointF(1.0, 1.0)]
        self.ponto_selecionado = -1

    def definir_cor_canal(self, canal: str):
        """Altera a cor do gráfico para dar feedback visual de qual canal está sendo editado."""
        cores = {
            "rgb": "#00d7ff", # Ciano
            "r": "#ff4d4d",   # Vermelho
            "g": "#4dff4d",   # Verde
            "b": "#4d4dff"    # Azul
        }
        self.cor_curva = QColor(cores.get(canal, "#00d7ff"))
        self.update()

    def obter_pontos_lut(self) -> tuple[list[float], list[float]]:
        """Retorna os valores X e Y no range [0, 255] para a criação da LUT."""
        x = [p.x() * 255.0 for p in self.pontos]
        y = [p.y() * 255.0 for p in self.pontos]
        return x, y

    def resetar(self):
        self.pontos = [QPointF(0.0, 0.0), QPointF(1.0, 1.0)]
        self.curva_alterada.emit()
        self.update()

    # --- Conversão de Coordenadas ---
    def _valor_para_tela(self, p: QPointF) -> QPointF:
        x_tela = self.margem + (p.x() * self.area_plot)
        y_tela = self.margem + ((1.0 - p.y()) * self.area_plot)
        return QPointF(x_tela, y_tela)

    def _tela_para_valor(self, pos) -> QPointF:
        x_val = (pos.x() - self.margem) / self.area_plot
        y_val = 1.0 - ((pos.y() - self.margem) / self.area_plot)
        x_val = max(0.0, min(1.0, x_val))
        y_val = max(0.0, min(1.0, y_val))
        return QPointF(x_val, y_val)

    # --- Renderização ---
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Fundo e Grade
        painter.fillRect(self.rect(), QColor("#2b2b2b"))
        painter.setPen(QPen(QColor("#444"), 1, Qt.PenStyle.DashLine))
        
        passos = 4
        for i in range(passos + 1):
            coord = self.margem + i * (self.area_plot / passos)
            painter.drawLine(int(coord), self.margem, int(coord), self.margem + self.area_plot)
            painter.drawLine(self.margem, int(coord), self.margem + self.area_plot, int(coord))

        # Eixos e Histograma base (linha reta diagonal)
        painter.setPen(QPen(QColor("#555"), 1))
        painter.drawLine(self.margem, self.margem + self.area_plot, self.margem + self.area_plot, self.margem)

        # Desenha a Linha da Curva com a cor dinâmica
        painter.setPen(QPen(self.cor_curva, 2))
        for i in range(len(self.pontos) - 1):
            p1 = self._valor_para_tela(self.pontos[i])
            p2 = self._valor_para_tela(self.pontos[i+1])
            painter.drawLine(p1, p2)

        # Desenha os Pontos de Controle
        for i, p in enumerate(self.pontos):
            p_tela = self._valor_para_tela(p)
            if i == self.ponto_selecionado:
                painter.setBrush(QBrush(QColor("#fff")))
                painter.setPen(QPen(self.cor_curva, 2))
                raio = 5
            else:
                painter.setBrush(QBrush(self.cor_curva))
                painter.setPen(Qt.PenStyle.NoPen)
                raio = 4
            painter.drawEllipse(p_tela, raio, raio)

    # --- Eventos de Mouse ---
    def mousePressEvent(self, event: QMouseEvent):
        # Adição de ponto
        if event.button() == Qt.MouseButton.LeftButton:
            for i, p in enumerate(self.pontos):
                p_tela = self._valor_para_tela(p)
                dist = (p_tela.x() - event.position().x())**2 + (p_tela.y() - event.position().y())**2
                if dist < 64: 
                    self.ponto_selecionado = i
                    self.update()
                    return

            novo_p = self._tela_para_valor(event.position())
            self.pontos.append(novo_p)
            self.pontos.sort(key=lambda p: p.x())
            self.ponto_selecionado = self.pontos.index(novo_p)
            self.curva_alterada.emit()
            self.update()

        # Remoção de ponto
        elif event.button() == Qt.MouseButton.RightButton:
            for i, p in enumerate(self.pontos):
                if i == 0 or i == len(self.pontos) - 1:
                    continue 
                
                p_tela = self._valor_para_tela(p)
                dist = (p_tela.x() - event.position().x())**2 + (p_tela.y() - event.position().y())**2
                if dist < 64:
                    self.pontos.pop(i)
                    self.ponto_selecionado = -1
                    self.curva_alterada.emit()
                    self.update()
                    return
    # Movimentação de ponto
    def mouseMoveEvent(self, event: QMouseEvent):
        if self.ponto_selecionado != -1:
            novo_p = self._tela_para_valor(event.position())
            
            # Restrições para o ponto não cruzar os vizinhos no eixo X
            if self.ponto_selecionado == 0:
                novo_p.setX(0.0) 
            elif self.ponto_selecionado == len(self.pontos) - 1:
                novo_p.setX(1.0) 
            else:
                limite_esq = self.pontos[self.ponto_selecionado - 1].x() + 0.01
                limite_dir = self.pontos[self.ponto_selecionado + 1].x() - 0.01
                x_val = max(limite_esq, min(limite_dir, novo_p.x()))
                novo_p.setX(x_val)

            self.pontos[self.ponto_selecionado] = novo_p
            self.curva_alterada.emit()
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.ponto_selecionado = -1
        self.update()

# ==============================================================================
# PLUGIN OFICIAL
# ==============================================================================

class FiltroPiecewise(PluginBase):
    """Plugin para transformação por partes através de curvas interativas com seleção de canais."""
    
    display_name = "Transformação por partes (Piecewise)"

    # ------------------------------------------------------------------
    # Interface (setup_ui)
    # ------------------------------------------------------------------

    def setup_ui(self) -> None:
        layout_principal = QVBoxLayout(self)

        # --- Seleção do Canal ---
        rotulo_canal = QLabel("Canal a ser editado:", self)
        layout_principal.addWidget(rotulo_canal)

        self._grupo_canais = QButtonGroup(self)
        self._radios_canal: dict[str, QRadioButton] = {}

        opcoes_canal = [
            ("RGB", "rgb"),
            ("Vermelho", "r"),
            ("Verde", "g"),
            ("Azul", "b"),
        ]

        layout_canais = QHBoxLayout()
        for texto, valor in opcoes_canal:
            radio = QRadioButton(texto, self)
            self._grupo_canais.addButton(radio)
            self._radios_canal[valor] = radio
            layout_canais.addWidget(radio)

        self._radios_canal["rgb"].setChecked(True)
        layout_principal.addLayout(layout_canais)
        layout_principal.addSpacing(10)

        # --- Gráfico ---
        layout_curva = QHBoxLayout()
        layout_curva.addStretch()
        self.widget_curva = WidgetCurvaInterativa(self)
        layout_curva.addWidget(self.widget_curva)
        layout_curva.addStretch()
        layout_principal.addLayout(layout_curva)

        layout_principal.addSpacing(10)

        # Botão Reset
        self._btn_reset = QPushButton("Resetar Curva Atual", self)
        layout_principal.addWidget(self._btn_reset)
        layout_principal.addSpacing(15)

        # --- Botões de Ação ---
        layout_botoes = QHBoxLayout()
        self._btn_aplicar = QPushButton("Aplicar", self)
        self._btn_cancelar = QPushButton("Cancelar", self)
        layout_botoes.addWidget(self._btn_aplicar)
        layout_botoes.addWidget(self._btn_cancelar)
        layout_principal.addLayout(layout_botoes)

        # --- Conexões ---
        for radio in self._radios_canal.values():
            radio.toggled.connect(self._ao_alterar_canal)

        self.widget_curva.curva_alterada.connect(self._ao_alterar_parametros)
        self._btn_reset.clicked.connect(self.widget_curva.resetar)

        self._btn_aplicar.clicked.connect(self._ao_aplicar)
        self._btn_cancelar.clicked.connect(self.reject)

        self.setLayout(layout_principal)
        self.setMinimumWidth(340)

    def _obter_canal(self) -> str:
        for valor, radio in self._radios_canal.items():
            if radio.isChecked():
                return valor
        return "rgb"

    # ------------------------------------------------------------------
    # Lógica de processamento
    # ------------------------------------------------------------------

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        """Aplica a curva (LUT) ao canal selecionado."""
        xp, yp = self.widget_curva.obter_pontos_lut()
        x_valores = np.arange(256)
        
        # Cria a Look-Up Table resolvendo a equação para os 256 tons possíveis
        lut = np.interp(x_valores, xp, yp)
        lut = np.clip(lut, 0, 255).astype(np.uint8)
        
        canal_alvo = self._obter_canal()
        imagem_saida = imagem.copy()

        if canal_alvo == "rgb":
            # Aplica a mesma tabela nos três canais simultaneamente
            imagem_saida = cv2.LUT(imagem_saida, lut)
        else:
            # Pega apenas o índice do canal (0=R, 1=G, 2=B) e aplica a LUT só nele
            idx_canal = {"r": 0, "g": 1, "b": 2}[canal_alvo]
            imagem_saida[..., idx_canal] = cv2.LUT(imagem_saida[..., idx_canal], lut)

        return imagem_saida

    def _ao_alterar_canal(self, checado: bool) -> None:
        """Atualiza a cor do gráfico e refaz o processamento ao trocar de aba de cor."""
        if not checado:
            return
        
        canal_atual = self._obter_canal()
        self.widget_curva.definir_cor_canal(canal_atual)
        self._ao_alterar_parametros()

    def _ao_alterar_parametros(self) -> None:
        imagem_processada = self.processar(self.imagem_original)
        self.preview_requested.emit(imagem_processada)

    def _ao_aplicar(self) -> None:
        imagem_processada = self.processar(self.imagem_original)
        self.apply_requested.emit(imagem_processada)
        self.accept()
