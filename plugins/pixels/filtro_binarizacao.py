"""
plugins/pixels/filtro_binarizacao.py
-----------------------------------------
Plugin de exemplo: binarização interativa de imagens via slider.

A implementação segue três etapas:

1) Seleção do canal base da imagem RGB de entrada (Canal R, Canal G, Canal B ou a Média dos 3).
2) Conversão do canal escolhido para tons de cinza.
3) Aplicação do threshold para separar os pixels em dois grupos: pretos (0) e brancos (255) baseado no valor de limiar.

Onde:
* O método de extração pode ser R, G, B ou Média RGB.
* Limiar (threshold) está no intervalo [0, 255].
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
    QSlider,
    QVBoxLayout,
)

from core.plugin_base import PluginBase

class FiltroBinarizacao(PluginBase):
    """Plugin para binarização da imagem"""
    display_name = "Binarização"

    # ------------------------------------------------------------------
    # Interface (setup_ui)
    # ------------------------------------------------------------------

    def setup_ui(self) -> None:
        """Cria o slider de seleção do limiar (threshold), opções de canalRGB e os botões Aplicar/Cancelar."""
        layout_principal = QVBoxLayout(self)
        
        # --- Seleção da Origem da Imagem ---
        rotulo_metodo = QLabel("Canal base para binarização:", self)
        layout_principal.addWidget(rotulo_metodo)
        
        self._grupo_metodos = QButtonGroup(self)
        self._radios_metodo: dict[str, QRadioButton] = {}
        
        opcoes = [
            ("Média RGB", "media"),
            ("Canal Vermelho (R)", "r"),
            ("Canal Verde (G)", "g"),
            ("Canal Azul (B)", "b"),
            ]
        
        for texto, valor in opcoes:
            radio = QRadioButton(texto, self)
            self._grupo_metodos.addButton(radio)
            self._radios_metodo[valor] = radio
            layout_principal.addWidget(radio)

        # Define a Média RGB como padrão
        self._radios_metodo["media"].setChecked(True)

        layout_principal.addSpacing(10)

        # --- Controle do Limiar (Slider) ---
        self._rotulo_limiar = QLabel("Limiar (Threshold): 127", self)
        layout_principal.addWidget(self._rotulo_limiar)

        self._slider_limiar = QSlider(Qt.Orientation.Horizontal, self)
        self._slider_limiar.setRange(0, 255)
        self._slider_limiar.setValue(127)  # Inicia no meio da escala
        layout_principal.addWidget(self._slider_limiar)

        layout_principal.addSpacing(10)

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

        self._slider_limiar.valueChanged.connect(self._ao_mover_slider)
        
        self._btn_aplicar.clicked.connect(self._ao_aplicar)
        self._btn_cancelar.clicked.connect(self.reject)

        self.setLayout(layout_principal)
        self.setMinimumWidth(320)

        # Dispara o preview logo ao abrir a janela
        self._ao_alterar_parametros(True)

    def _obter_metodo(self) -> str:
        """Verifica qual rádio button está marcado e retorna a sua chave."""
        for valor, radio in self._radios_metodo.items():
            if radio.isChecked():
                return valor
        return "media"

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        """Lógica matemática executada a cada alteração nos controles."""
        metodo = self._obter_metodo()
        limiar = self._slider_limiar.value()

        # O app.py envia a imagem no formato RGB.
        # Extraí o canal escolhido via slicing:
        if metodo == "r":
            canal_base = imagem[..., 0]
        elif metodo == "g":
            canal_base = imagem[..., 1]
        elif metodo == "b":
            canal_base = imagem[..., 2]
        else:
            # Média RGB: calcula a média através do eixo de cor (axis=2)
            # e converte de float de volta para inteiro (uint8)
            canal_base = np.mean(imagem, axis=2).astype(np.uint8)

        # Aplica a binarização utilizando a função nativa do OpenCV
        # cv2.threshold retorna a tupla (limiar_aplicado, imagem_binarizada)
        _, img_bin = cv2.threshold(canal_base, limiar, 255, cv2.THRESH_BINARY)

        # O motor de renderização principal (app.py) espera uma imagem com 3 dimensões (RGB).
        # Empilha o resultado binário (1 canal) nos três canais finais
        return np.stack((img_bin, img_bin, img_bin), axis=-1)

    def _ao_mover_slider(self, valor: int) -> None:
        """Atualiza o texto da interface quando o slider é movimentado."""
        self._rotulo_limiar.setText(f"Limiar (Threshold): {valor}")
        self._ao_alterar_parametros(True)

    def _ao_alterar_parametros(self, marcado: bool) -> None:
        """Regera o processamento para mostrar o preview ao vivo no canvas."""
        if not marcado:
            return
        # Utiliza a cópia da imagem enviada pelo construtor da PluginBase
        imagem_processada = self.processar(self.imagem_original)
        self.preview_requested.emit(imagem_processada)

    def _ao_aplicar(self) -> None:
        """Aplica o filtro na matriz oficial e adiciona ao histórico."""
        imagem_processada = self.processar(self.imagem_original)
        self.apply_requested.emit(imagem_processada)
        self.accept()
