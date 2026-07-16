'''
Plugin para quantização uniforme de cores por canal. O filtro reduz cada canal da imagem para uma quantidade definida de níveis: 
2, 4, 8, 16 ou 32 níveis por canal. Cada intensidade é mapeada para o nível uniforme mais próximo e depois reconstruída no intervalo [0, 255]
'''

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from core.plugin_base import PluginBase
class FiltroQuantizacaoCores(PluginBase):

    display_name = "Quantização de Cores"

    _NIVEIS_DISPONIVEIS = (2, 4, 8, 16, 32)

    def setup_ui(self) -> None:
        layout_principal = QVBoxLayout(self)

        titulo = QLabel("Quantidade de níveis por canal", self)
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_principal.addWidget(titulo)

        self._combo_niveis = QComboBox(self)

        for niveis in self._NIVEIS_DISPONIVEIS:
            self._combo_niveis.addItem(
                f"{niveis} níveis por canal",
                niveis,
            )

        indice_padrao = self._combo_niveis.findData(8)
        self._combo_niveis.setCurrentIndex(indice_padrao)

        layout_principal.addWidget(self._combo_niveis)

        self._rotulo_cores = QLabel(self)
        self._rotulo_cores.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_principal.addWidget(self._rotulo_cores)

        self._rotulo_explicacao = QLabel(
            "A quantização é aplicada independentemente em cada canal.",
            self,
        )
        self._rotulo_explicacao.setWordWrap(True)
        self._rotulo_explicacao.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_principal.addWidget(self._rotulo_explicacao)

        layout_botoes = QHBoxLayout()

        self._btn_aplicar = QPushButton("Aplicar", self)
        self._btn_cancelar = QPushButton("Cancelar", self)

        layout_botoes.addWidget(self._btn_aplicar)
        layout_botoes.addWidget(self._btn_cancelar)

        layout_principal.addLayout(layout_botoes)

        self._combo_niveis.currentIndexChanged.connect(
            self._ao_mudar_niveis
        )
        self._btn_aplicar.clicked.connect(self._ao_aplicar)
        self._btn_cancelar.clicked.connect(self.reject)

        self.setMinimumWidth(360)

        self._atualizar_rotulos()

    def _obter_niveis(self) -> int:
        niveis = self._combo_niveis.currentData()

        if niveis not in self._NIVEIS_DISPONIVEIS:
            return 8

        return int(niveis)

    def _atualizar_rotulos(self) -> None:
        niveis = self._obter_niveis()
        total_cores = niveis ** 3

        self._rotulo_cores.setText(
            f"Máximo teórico de cores RGB: {total_cores:,}".replace(",", ".")
        )

    def processar(self, imagem: np.ndarray) -> np.ndarray:

        if imagem is None or imagem.size == 0:
            return imagem.copy()

        niveis = self._obter_niveis()

        imagem_float = imagem.astype(np.float32)

        indices_quantizados = np.rint(
            imagem_float * (niveis - 1) / 255.0
        )

        resultado = np.rint(
            indices_quantizados * 255.0 / (niveis - 1)
        )

        return np.clip(resultado, 0, 255).astype(np.uint8)

    def _ao_mudar_niveis(self, _indice: int) -> None:
        self._atualizar_rotulos()

        imagem_processada = self.processar(self.imagem_original)
        self.preview_requested.emit(imagem_processada)

    def _ao_aplicar(self) -> None:
        imagem_processada = self.processar(self.imagem_original)
        self.apply_requested.emit(imagem_processada)
        self.accept()
