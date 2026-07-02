from typing import Optional

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout

from core.plugin_base import PluginBase


# ---------------------------------------------------------------------------
#   1D ALFA-TRIMMED MEAN FILTER — implementação interna (janela fixa = 5)
# ---------------------------------------------------------------------------
def _alfatrimmedmeanfilter_1d(signal: list[float], N: int, alpha: int) -> list[float]:
    start = alpha >> 1
    end = 5 - (alpha >> 1)
    result = [0.0] * (N - 4)

    for i in range(2, N - 2):
        window = [signal[i - 2 + j] for j in range(5)]

        # Selection sort parcial (apenas até 'end')
        for j in range(end):
            min_idx = j
            for k in range(j + 1, 5):
                if window[k] < window[min_idx]:
                    min_idx = k
            window[j], window[min_idx] = window[min_idx], window[j]

        # Divisor = (5 - alpha), nº de elementos mantidos após o corte
        result[i - 2] = sum(window[start:end]) / (5 - alpha)
    return result


# ---------------------------------------------------------------------------
#   1D ALFA-TRIMMED MEAN FILTER — wrapper público
# ---------------------------------------------------------------------------
def alfatrimmedmeanfilter_1d(
    signal: list[float],
    alpha: int,
    result: Optional[list[float]] = None,
) -> Optional[list[float]]:
    N = len(signal)
    if N < 1 or alpha < 0 or alpha > 4 or (alpha & 1):
        return None

    if N == 1:
        if result is not None:
            result[0] = signal[0]
            return result
        return [signal[0]]

    # Extensão do sinal com espelhamento nas bordas
    extension = [0.0] * (N + 4)
    extension[2 : 2 + N] = signal[:]
    for i in range(2):
        extension[i] = signal[1 - i]
        extension[N + 2 + i] = signal[N - 1 - i]

    filtered = _alfatrimmedmeanfilter_1d(extension, N + 4, alpha)

    if result is not None:
        for i in range(len(filtered)):
            result[i] = filtered[i]
        return result
    return filtered


# ---------------------------------------------------------------------------
#   2D ALFA-TRIMMED MEAN FILTER — implementação interna (janela 3×3)
# ---------------------------------------------------------------------------
def _alfatrimmedmeanfilter_2d(
    image: list[float], N: int, M: int, alpha: int
) -> list[float]:
    start = alpha >> 1
    end = 9 - (alpha >> 1)
    result = [0.0] * ((N - 2) * (M - 2))

    for m in range(1, M - 1):
        for n in range(1, N - 1):
            window = []
            for j in range(m - 1, m + 2):
                for i in range(n - 1, n + 2):
                    window.append(image[j * N + i])

            # Selection sort parcial
            for j in range(end):
                min_idx = j
                for l in range(j + 1, 9):
                    if window[l] < window[min_idx]:
                        min_idx = l
                window[j], window[min_idx] = window[min_idx], window[j]

            target = (m - 1) * (N - 2) + n - 1
            result[target] = sum(window[start:end]) / (9 - alpha)
    return result


# ---------------------------------------------------------------------------
#   2D ALFA-TRIMMED MEAN FILTER — wrapper público
# ---------------------------------------------------------------------------
def alfatrimmedmeanfilter_2d(
    image: list[float],
    N: int,
    M: int,
    alpha: int,
    result: Optional[list[float]] = None,
) -> Optional[list[float]]:
    if N < 1 or M < 1 or alpha < 0 or alpha > 8 or (alpha & 1):
        return None

    # Extensão da imagem com espelhamento nas bordas
    extension = [0.0] * ((N + 2) * (M + 2))
    for i in range(M):
        for j in range(N):
            extension[(N + 2) * (i + 1) + 1 + j] = image[N * i + j]
        extension[(N + 2) * (i + 1)] = image[N * i]
        extension[(N + 2) * (i + 2) - 1] = image[N * (i + 1) - 1]
    extension[0 : N + 2] = extension[N + 2 : 2 * (N + 2)]
    extension[(N + 2) * (M + 1) : (N + 2) * (M + 2)] = extension[
        (N + 2) * M : (N + 2) * (M + 1)
    ]

    filtered = _alfatrimmedmeanfilter_2d(extension, N + 2, M + 2, alpha)

    if result is not None:
        for i in range(len(filtered)):
            result[i] = filtered[i]
        return result
    return filtered


# ---------------------------------------------------------------------------
#   Wrapper NumPy para o filtro 2D
# ---------------------------------------------------------------------------
def alfatrimmedmeanfilter_2d_numpy(
    image: np.ndarray, alpha: int
) -> Optional[np.ndarray]:
    """Aplica o filtro alfa-trimmed mean 2D em uma imagem numpy 2D.

    Args:
        image: Imagem de entrada como numpy array 2D (altura x largura).
        alpha: Parâmetro alfa do filtro (0, 2, 4, 6 ou 8; deve ser par).

    Returns:
        Imagem filtrada como numpy array 2D, ou None se argumentos inválidos.
    """
    if image.ndim != 2:
        return None
    M, N = image.shape
    flat = image.flatten().tolist()
    filtered = alfatrimmedmeanfilter_2d(flat, N, M, alpha)
    if filtered is None:
        return None
    return np.array(filtered).reshape(M, N)


# ---------------------------------------------------------------------------
#   Plugin para a interface do Studio de Processamento de Imagens
# ---------------------------------------------------------------------------
class FiltroAlfaTrimmedMean(PluginBase):
    """Plugin que aplica o filtro Alfa-Trimmed Mean em imagens RGB.

    O filtro é inerentemente misto — o parâmetro alpha controla o
    equilíbrio entre média (bom para Gaussiano) e mediana (bom para
    salt & pepper). Valores intermediários de alpha tratam ambos
    os tipos de ruído simultaneamente.
    """

    display_name = "Alfa-Trimmed Mean"

    _TAMANHOS_KERNEL = [3, 5, 7]

    def setup_ui(self) -> None:
        """Constrói os controles da janela flutuante do plugin."""
        layout = QVBoxLayout(self)

        self.info = QLabel(
            "Filtro Alfa-Trimmed Mean — filtro misto por natureza.\n"
            "O alpha controla o equilíbrio:\n"
            "  ← alpha=0: média pura (ruído Gaussiano)\n"
            "  → alpha=máx: mediana pura (salt & pepper)\n"
            "  meio: trata ambos os ruídos simultaneamente",
            self,
        )
        self.info.setWordWrap(True)
        layout.addWidget(self.info)

        # --- Kernel ---
        layout_kernel = QHBoxLayout()
        layout_kernel.addWidget(QLabel("Kernel:", self))
        self.combo_kernel = QComboBox(self)
        for k in self._TAMANHOS_KERNEL:
            self.combo_kernel.addItem(f"{k}×{k}", k)
        self.combo_kernel.setCurrentIndex(0)
        self.combo_kernel.currentIndexChanged.connect(self._ao_mudar_kernel)
        layout_kernel.addWidget(self.combo_kernel)
        layout.addLayout(layout_kernel)

        # --- Alpha ---
        self.rotulo_alpha = QLabel("", self)
        self.rotulo_alpha.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.rotulo_alpha)

        self.slider_alpha = QSlider(Qt.Orientation.Horizontal, self)
        self.slider_alpha.setMinimum(0)
        self.slider_alpha.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider_alpha.setTickInterval(1)
        self.slider_alpha.valueChanged.connect(self._ao_mudar_alpha)
        layout.addWidget(self.slider_alpha)

        # --- Iterações ---
        self.rotulo_iteracoes = QLabel("Iterações: 1", self)
        self.rotulo_iteracoes.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.rotulo_iteracoes)

        self.slider_iteracoes = QSlider(Qt.Orientation.Horizontal, self)
        self.slider_iteracoes.setMinimum(1)
        self.slider_iteracoes.setMaximum(5)
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

        self._ao_mudar_kernel(0)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _tamanho_kernel(self) -> int:
        return self.combo_kernel.currentData()

    def _max_alpha(self) -> int:
        k = self._tamanho_kernel()
        max_a = k * k - 1
        if max_a % 2 != 0:
            max_a -= 1
        return max_a

    def _obter_alpha(self) -> int:
        return self.slider_alpha.value() * 2

    # ------------------------------------------------------------------
    # Callbacks de UI
    # ------------------------------------------------------------------

    def _ao_mudar_kernel(self, _index: int) -> None:
        max_alpha = self._max_alpha()
        self.slider_alpha.setMaximum(max_alpha // 2)
        self.slider_alpha.setValue(max_alpha // 4)
        self._ao_mudar_alpha(self.slider_alpha.value())

    def _ao_mudar_alpha(self, _valor: int) -> None:
        alpha = self._obter_alpha()
        kernel = self._tamanho_kernel()
        janela_total = kernel * kernel
        self.rotulo_alpha.setText(
            f"Alpha: {alpha}  (usa {janela_total - alpha} de {janela_total} vizinhos)"
        )
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
        """Aplica o filtro alfa-trimmed mean em cada canal RGB da imagem."""
        if imagem.ndim == 2:
            imagem = np.stack([imagem] * 3, axis=-1)

        alpha = self._obter_alpha()
        kernel = self._tamanho_kernel()
        iteracoes = self.slider_iteracoes.value()

        resultado = imagem
        for _ in range(iteracoes):
            resultado = self._aplicar_filtro(resultado, alpha, kernel)
        return resultado

    def _aplicar_filtro(self, imagem: np.ndarray, alpha: int, kernel: int) -> np.ndarray:
        """Aplica uma passada do filtro em todos os canais."""
        resultado = np.empty(imagem.shape, dtype=np.uint8)
        for c in range(imagem.shape[2]):
            canal = imagem[:, :, c].astype(np.float64)
            resultado[:, :, c] = self._filtrar_canal_rapido(canal, alpha, kernel)
        return np.ascontiguousarray(resultado)

    @staticmethod
    def _filtrar_canal_rapido(canal: np.ndarray, alpha: int, kernel: int) -> np.ndarray:
        """Aplica o filtro alfa-trimmed mean 2D vetorizado em um canal.

        Coleta todos os kernel² vizinhos de uma vez via slicing do NumPy,
        ordena e calcula a média da faixa trimada — tudo em C.
        """
        M, N = canal.shape
        raio = kernel // 2
        janela_total = kernel * kernel

        padded = np.pad(canal, raio, mode="edge")

        vizinhos = np.empty((M, N, janela_total), dtype=np.float64)
        idx = 0
        for di in range(kernel):
            for dj in range(kernel):
                vizinhos[:, :, idx] = padded[di : di + M, dj : dj + N]
                idx += 1

        vizinhos.sort(axis=2)

        start = alpha >> 1
        end = janela_total - (alpha >> 1)
        media = vizinhos[:, :, start:end].mean(axis=2)

        return np.clip(media, 0, 255).astype(np.uint8)

    # ------------------------------------------------------------------
    # Ações
    # ------------------------------------------------------------------

    def _ao_aplicar(self) -> None:
        img_processada = self.processar(self.imagem_original)
        self.apply_requested.emit(img_processada)
        self.accept()
