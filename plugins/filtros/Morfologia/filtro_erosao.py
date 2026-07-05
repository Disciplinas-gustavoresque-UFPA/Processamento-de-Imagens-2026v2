import cv2
import numpy as np

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
)

from core.plugin_base import PluginBase


class FiltroErosao(PluginBase):
    """Plugin que aplica o filtro morfológico de Erosão em imagens RGB.

    A erosão reduz as regiões claras (ou objetos brancos em imagens
    binárias), removendo pequenas saliências e separando componentes
    conectados por pontes estreitas. O efeito é controlado pela forma
    e tamanho do elemento estruturante e pelo número de iterações.
    """

    display_name = "Erosão"

    _FORMAS_KERNEL = [
        ("Retângulo", cv2.MORPH_RECT),
        ("Cruz", cv2.MORPH_CROSS),
        ("Elipse", cv2.MORPH_ELLIPSE),
    ]

    def setup_ui(self) -> None:
        """Constrói os controles da janela flutuante do plugin."""
        layout = QVBoxLayout(self)

        # --- Informativo ---
        self.info = QLabel(
            "Reduz regiões claras da imagem, removendo\n"
            "pequenas saliências e separando componentes\n"
            "conectados por pontes estreitas.",
            self,
        )
        self.info.setWordWrap(True)
        layout.addWidget(self.info)

        # --- Forma do Elemento Estruturante ---
        layout_forma = QHBoxLayout()
        layout_forma.addWidget(QLabel("Elemento Estruturante:", self))
        self.combo_forma = QComboBox(self)
        for nome, valor in self._FORMAS_KERNEL:
            self.combo_forma.addItem(nome, valor)
        self.combo_forma.setCurrentIndex(0)
        self.combo_forma.currentIndexChanged.connect(self._ao_mudar_forma)
        layout_forma.addWidget(self.combo_forma)
        layout.addLayout(layout_forma)

        # --- Tamanho do Kernel ---
        self.rotulo_kernel = QLabel("Tamanho do Kernel: 3×3", self)
        self.rotulo_kernel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.rotulo_kernel)

        self.slider_kernel = QSlider(Qt.Orientation.Horizontal, self)
        self.slider_kernel.setMinimum(1)   # representa kernel 3 (2*1+1)
        self.slider_kernel.setMaximum(10)  # representa kernel 21 (2*10+1)
        self.slider_kernel.setValue(1)
        self.slider_kernel.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider_kernel.setTickInterval(1)
        self.slider_kernel.valueChanged.connect(self._ao_mudar_kernel)
        layout.addWidget(self.slider_kernel)

        # --- Iterações ---
        self.rotulo_iteracoes = QLabel("Iterações: 1", self)
        self.rotulo_iteracoes.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.rotulo_iteracoes)

        self.slider_iteracoes = QSlider(Qt.Orientation.Horizontal, self)
        self.slider_iteracoes.setMinimum(1)
        self.slider_iteracoes.setMaximum(10)
        self.slider_iteracoes.setValue(1)
        self.slider_iteracoes.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider_iteracoes.setTickInterval(1)
        self.slider_iteracoes.valueChanged.connect(self._ao_mudar_iteracoes)
        layout.addWidget(self.slider_iteracoes)

        # --- Botões ---
        layout_botoes = QHBoxLayout()
        self.btn_aplicar = QPushButton("Aplicar", self)
        self.btn_cancelar = QPushButton("Cancelar", self)
        layout_botoes.addWidget(self.btn_aplicar)
        layout_botoes.addWidget(self.btn_cancelar)
        layout.addLayout(layout_botoes)

        self.btn_aplicar.clicked.connect(self._ao_aplicar)
        self.btn_cancelar.clicked.connect(self.reject)

        self.setLayout(layout)
        self.setMinimumWidth(400)

        # Preview inicial
        self._disparar_preview()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _obter_forma(self) -> int:
        """Retorna a constante OpenCV da forma do elemento estruturante."""
        return self.combo_forma.currentData()

    def _obter_tamanho_kernel(self) -> int:
        """Retorna o tamanho do kernel (sempre ímpar: 3, 5, 7, ..., 21)."""
        return 2 * self.slider_kernel.value() + 1

    def _obter_iteracoes(self) -> int:
        """Retorna o número de iterações."""
        return self.slider_iteracoes.value()

    # ------------------------------------------------------------------
    # Callbacks de UI
    # ------------------------------------------------------------------

    def _ao_mudar_forma(self, _index: int) -> None:
        self._disparar_preview()

    def _ao_mudar_kernel(self, _valor: int) -> None:
        tamanho = self._obter_tamanho_kernel()
        self.rotulo_kernel.setText(f"Tamanho do Kernel: {tamanho}×{tamanho}")
        self._disparar_preview()

    def _ao_mudar_iteracoes(self, valor: int) -> None:
        self.rotulo_iteracoes.setText(f"Iterações: {valor}")
        self._disparar_preview()

    def _disparar_preview(self) -> None:
        imagem_processada = self.processar(self.imagem_original)
        self.preview_requested.emit(imagem_processada)

    # ------------------------------------------------------------------
    # Processamento
    # ------------------------------------------------------------------

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        """Aplica a erosão morfológica na imagem.

        Parâmetros
        ----------
        imagem : np.ndarray
            Imagem de entrada em formato RGB (ou RGBA).

        Retorna
        -------
        np.ndarray
            Imagem erodida.
        """
        tamanho = self._obter_tamanho_kernel()
        forma = self._obter_forma()
        iteracoes = self._obter_iteracoes()

        # Cria o elemento estruturante
        kernel = cv2.getStructuringElement(forma, (tamanho, tamanho))

        # Trata imagens com canal alpha separadamente
        possui_alpha = len(imagem.shape) == 3 and imagem.shape[2] == 4

        if possui_alpha:
            rgb = imagem[..., :3]
            alpha = imagem[..., 3]
            resultado_rgb = cv2.erode(rgb, kernel, iterations=iteracoes)
            resultado = np.dstack((resultado_rgb, alpha))
        else:
            resultado = cv2.erode(imagem, kernel, iterations=iteracoes)

        return resultado

    # ------------------------------------------------------------------
    # Ações
    # ------------------------------------------------------------------

    def _ao_aplicar(self) -> None:
        img_processada = self.processar(self.imagem_original)
        self.apply_requested.emit(img_processada)
        self.accept()
