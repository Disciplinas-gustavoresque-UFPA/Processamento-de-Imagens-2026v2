import cv2
import numpy as np
from PySide6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
)
from core.plugin_base import PluginBase 

class OtsuThresholding(PluginBase):
    display_name = "Otsu Thresholding"

    def setup_ui(self) -> None:
        layout_principal = QVBoxLayout(self)

        descricao = QLabel(
            "Binariza a imagem calculando o limiar ideal automaticamente pelo método de Otsu.",
            self
        )
        descricao.setWordWrap(True)
        layout_principal.addWidget(descricao)

        layout_botoes = QHBoxLayout()
        self._btn_aplicar = QPushButton("Aplicar", self)
        self._btn_cancelar = QPushButton("Cancelar", self)
        
        layout_botoes.addWidget(self._btn_aplicar)
        layout_botoes.addWidget(self._btn_cancelar)
        layout_principal.addLayout(layout_botoes)

        self._btn_aplicar.clicked.connect(self._ao_aplicar)
        self._btn_cancelar.clicked.connect(self.reject)

        self.setLayout(layout_principal)
        self.setMinimumWidth(320)

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        # 1. O Otsu exige que a imagem esteja em tons de cinza (1 canal)
        # Como o app envia RGB, convertemos RGB -> GRAY
        if len(imagem.shape) == 3:
            imagem_cinza = cv2.cvtColor(imagem, cv2.COLOR_RGB2GRAY)
        else:
            imagem_cinza = imagem
            
        # 2. Aplica o limiar de Otsu
        # O OpenCV retorna dois valores: o limiar calculado (t_ideal) e a imagem binarizada
        t_ideal, imagem_binaria = cv2.threshold(
            imagem_cinza, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
        
        # Opcional: imprimir o limiar no console para fins de debug
        print(f"Limiar ideal calculado por Otsu: {t_ideal}")

        # 3. Retorna a imagem final convertida para RGB (3 canais) para a interface
        return cv2.cvtColor(imagem_binaria, cv2.COLOR_GRAY2RGB)

    def _ao_aplicar(self) -> None:
        imagem_processada = self.processar(self.imagem_original)
        self.apply_requested.emit(imagem_processada)
        self.accept()
