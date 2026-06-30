"""
plugins/bordas/filtro_sobel.py
-----------------------------------------
Plugin: Detecção de bordas via Operador Sobel.
 
Etapas:
1) Conversão da imagem RGB para escala de cinzentos.
2) Convolução com kernels 3x3 para derivadas espaciais (X e Y).
3) Cálculo da magnitude do gradiente com ajuste de escala e normalização.
 
Detalhes:
* Kernel X: Destaca linhas verticais.
* Kernel Y: Destaca linhas horizontais.
* Reduz ruídos devido à suavização integrada (peso 2 no centro).
* Usa float64 (cv2.CV_64F) e normaliza para uint8 com np.clip().

"""
import cv2
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout

from core.plugin_base import PluginBase


class FiltroSobel(PluginBase):
    display_name = "Operador Sobel"

    def setup_ui(self) -> None:
        """
        O método setup_ui cria a interface do plugin com layout vertical. 
        
        Define um rótulo informativo, botões de ação e um slider horizontal (escala de 0.1x a 4.0x) interligados a eventos. 
        
        Não tem argumentos nem retorno.
        """
        layout = QVBoxLayout(self)

        self.info = QLabel("Aplica o operador Sobel para destacar bordas na imagem.")
        layout.addWidget(self.info)

        self.rotulo_escala = QLabel("Escala da magnitude: 1.0x", self)
        self.rotulo_escala.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.rotulo_escala)

        self.slider_escala = QSlider(Qt.Orientation.Horizontal, self)
        self.slider_escala.setMinimum(1)
        self.slider_escala.setMaximum(40)
        self.slider_escala.setValue(10)
        self.slider_escala.valueChanged.connect(self._ao_mudar_escala)
        layout.addWidget(self.slider_escala)

        layout_botoes = QHBoxLayout()
        self.btn_aplicar = QPushButton("Aplicar", self)
        self.btn_cancelar = QPushButton("Cancelar", self)
        layout_botoes.addWidget(self.btn_aplicar)
        layout_botoes.addWidget(self.btn_cancelar)
        layout.addLayout(layout_botoes)

        self.btn_aplicar.clicked.connect(self._ao_aplicar)
        self.btn_cancelar.clicked.connect(self.reject)

        self.setLayout(layout)
        self.setMinimumWidth(420)
        self._ao_mudar_escala(self.slider_escala.value())

    def _obter_escala(self) -> float:
        """
        O método _obter_escala converte o valor inteiro do slider (1 a 40) para um fator de ponto flutuante (0.1 a 4.0), dividindo-o por 10. 
        
        Não possui parâmetros externos além de self. 
        
        Retorna um valor float.
        
        """
        return self.slider_escala.value() / 10.0 
    
    def processar(self, imagem: np.ndarray) -> np.ndarray:
        """
        O método processar converte uma imagem RGB para cinza e usa convolução com kernels 3x3 do Operador Sobel para extrair as derivadas X e Y. 
        
        Calcula a magnitude do gradiente, aplica escala e normaliza em uint8 [0-255]. 
        
        Retorna em RGB.
        """

        # 1º Converte a imagem RGB para escala de cinza
        if len(imagem.shape) == 3:
            gray = cv2.cvtColor(imagem, cv2.COLOR_RGB2GRAY)
        else:
            gray = imagem.copy()

        # definição dos kernels Sobel (dando maior peso ao elemento central)
        kernel_x = np.array(
            [
                [-1, 0, 1],
                [-2, 0, 2],
                [-1, 0, 1],
            ],
            dtype=np.float32,
        )
        kernel_y = np.array(
            [
                [-1, -2, -1],
                [0, 0, 0],
                [1, 2, 1],
            ],
            dtype=np.float32,
        )

        # para evitar gradientes negativos sejam cortados em zero, mantendo as bordas de transição claro-para-escuro e escuro-para-claro.
        # convolução usando os kernels Sobel com tipo de dado de precisão maior (float64)
        img_sobel_x = cv2.filter2D(gray, cv2.CV_64F, kernel_x)
        img_sobel_y = cv2.filter2D(gray, cv2.CV_64F, kernel_y)

        # calcula a magnitude do vetor gradiente (raiz quadrada da soma dos quadrados)
        magnitude = cv2.magnitude(img_sobel_x, img_sobel_y)
        magnitude *= self._obter_escala()

        # tratamento de saturação: garante que os valores estejam entre 0 e 255 e converte de volta para 8 bits
        resultado = np.clip(magnitude, 0, 255).astype(np.uint8)
        return cv2.cvtColor(resultado, cv2.COLOR_GRAY2RGB)
    
    def _ao_mudar_escala(self, valor: int) -> None:
        """
        O método _ao_mudar_escala atualiza o rótulo de texto e gera a pré-visualização em tempo real ao processar a imagem com a nova escala. 
        
        Recebe o valor inteiro do slider e emite um sinal. 
        
        Não possui retorno.
            
        """
        escala = valor / 10.0
        self.rotulo_escala.setText(f"Escala da magnitude: {escala:.1f}x")
        imagem_processada = self.processar(self.imagem_original)
        self.preview_requested.emit(imagem_processada)

    def _ao_aplicar(self) -> None:
        """
        O método _ao_aplicar confirma as alterações ao processar a imagem uma última vez. 

        Emite o sinal apply_requested com o resultado final e fecha a janela (accept). 

        Recebe apenas self e não possui retorno.
        """
        img_processada = self.processar(self.imagem_original)
        self.apply_requested.emit(img_processada)
        self.accept()