"""
plugins/pixels/filtro_transformacao_por_partes.py
-----------------------------------------
Plugin para Transformação Linear por Partes (Piecewise Linear Transformation).

Implementa um gráfico interativo onde o usuário pode adicionar, mover e 
remover pontos de controle. Inclui seleção de canal (RGB, R, G, B) com
feedback visual de cores.

A adição de pontos é feita pelo clique do botão esquerdo do mouse.
A remoção de pontos é feita pelo clique do botão direito do mouse.
A movimentação de pontos é feita pelo clique e arraste do mouse sobre o ponto.
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

        # --- Estrutura de Memória dos Canais ---
        self.memorias_curvas = {
            "rgb": [QPointF(0.0, 0.0), QPointF(1.0, 1.0)],
            "r":   [QPointF(0.0, 0.0), QPointF(1.0, 1.0)],
            "g":   [QPointF(0.0, 0.0), QPointF(1.0, 1.0)],
            "b":   [QPointF(0.0, 0.0), QPointF(1.0, 1.0)]
        }
        self.canal_anterior = "rgb"

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
        dica = QLabel("<b>Clique</b> para adicionar pontos. <b>Arraste</b> para ajustar.<br><b>Botão Direito</b> no ponto para remover.", self)
        dica.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_principal.addWidget(dica)

        layout_curva = QHBoxLayout()
        layout_curva.addStretch()
        self.widget_curva = WidgetCurvaInterativa(self)
        layout_curva.addWidget(self.widget_curva)
        layout_curva.addStretch()
        layout_principal.addLayout(layout_curva)

        layout_principal.addSpacing(10)

        # Botão Reset
        layout_resets = QHBoxLayout()
        self._btn_reset_atual = QPushButton("Resetar Curva Atual", self)
        self._btn_reset_tudo = QPushButton("Resetar Tudo", self)
        layout_resets.addWidget(self._btn_reset_atual)
        layout_resets.addWidget(self._btn_reset_tudo)
        layout_principal.addLayout(layout_resets)
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
        self._btn_reset_atual.clicked.connect(self._resetar_canal_atual)
        self._btn_reset_tudo.clicked.connect(self._resetar_tudo)

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

    def _gerar_lut(self, pontos: list[QPointF]) -> np.ndarray:
        """Função utilitária para converter uma lista de QPointF em uma LUT de 256 posições."""
        x = [p.x() * 255.0 for p in pontos]
        y = [p.y() * 255.0 for p in pontos]
        x_valores = np.arange(256)
        lut = np.interp(x_valores, x, y)
        return np.clip(lut, 0, 255).astype(np.uint8)

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        """Aplica cumulativamente as curvas de todos os canais na imagem final."""
        
        # Sincroniza a memória com o que está desenhado na tela atualmente
        canal_atual = self._obter_canal()
        self.memorias_curvas[canal_atual] = self.widget_curva.pontos.copy()

        imagem_saida = imagem.copy()

        # Aplica primeiro a curva global (RGB) em todos os canais
        lut_rgb = self._gerar_lut(self.memorias_curvas["rgb"])
        imagem_saida = cv2.LUT(imagem_saida, lut_rgb)

        # Aplica as curvas específicas
        canais_individuais = [("r", 0), ("g", 1), ("b", 2)]
        
        for canal_nome, idx in canais_individuais:
            pontos_canal = self.memorias_curvas[canal_nome]
            lut_canal = self._gerar_lut(pontos_canal)
            imagem_saida[..., idx] = cv2.LUT(imagem_saida[..., idx], lut_canal)

        return imagem_saida

    def _ao_alterar_canal(self, checado: bool) -> None:
        """Salva a curva atual e carrega a nova curva ao trocar de aba de cor."""
        if not checado:
            return 

        canal_atual = self._obter_canal()

        # Salva o estado físico da curva no canal que estava sendo editando antes da troca
        self.memorias_curvas[self.canal_anterior] = self.widget_curva.pontos.copy()

        # Injeta no gráfico interativo os pontos da memória do novo canal selecionado
        self.widget_curva.pontos = self.memorias_curvas[canal_atual].copy()
        
        # Atualiza a interface visualmente
        self.widget_curva.definir_cor_canal(canal_atual)
        self.widget_curva.ponto_selecionado = -1
        self.canal_anterior = canal_atual
        self.widget_curva.update()

        # Chama o processamento para garantir a atualização da imagem
        self._ao_alterar_parametros()
        
    def _resetar_canal_atual(self) -> None:
        """Limpa apenas a curva do canal que está visível no momento."""
        canal_atual = self._obter_canal()
        pontos_padrao = [QPointF(0.0, 0.0), QPointF(1.0, 1.0)]
        
        # Reseta a memória e o widget
        self.memorias_curvas[canal_atual] = pontos_padrao.copy()
        self.widget_curva.pontos = pontos_padrao.copy()
        self.widget_curva.ponto_selecionado = -1
        self.widget_curva.update()
        
        self._ao_alterar_parametros()

    def _resetar_tudo(self) -> None:
        """Limpa as curvas de TODOS os canais e restaura a imagem original."""
        pontos_padrao = [QPointF(0.0, 0.0), QPointF(1.0, 1.0)]
        
        # Percorre o dicionário e reseta a memória de todos os canais simultaneamente
        for canal in self.memorias_curvas.keys():
            self.memorias_curvas[canal] = pontos_padrao.copy()
        
        # Reseta o widget visualmente para a aba atual
        self.widget_curva.pontos = pontos_padrao.copy()
        self.widget_curva.ponto_selecionado = -1
        self.widget_curva.update()
        
        # Reaplica o processamento (que agora usará apenas retas [0,1] neutras)
        self._ao_alterar_parametros()

    def _ao_alterar_parametros(self) -> None:
        imagem_processada = self.processar(self.imagem_original)
        self.preview_requested.emit(imagem_processada)

    def _ao_aplicar(self) -> None:
        imagem_processada = self.processar(self.imagem_original)
        self.apply_requested.emit(imagem_processada)
        self.accept()
