import numpy as np
import cv2

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QVBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
)

from core.plugin_base import PluginBase


class HistogramaPlugin(PluginBase):
    display_name = "Histograma da Imagem"

    def setup_ui(self):
        layout = QVBoxLayout(self)

        self._btn_atualizar = QPushButton("Atualizar Histograma")

        self._label_hist = QLabel("Histograma aqui")
        self._label_hist.setAlignment(Qt.AlignCenter)
        self._label_hist.setMinimumHeight(200)

        self._canal_ativo = "RGB"

        self._canal_combo = QComboBox()
        self._canal_combo.addItems([
            "RGB", "R (Vermelho)", "G (Verde)",
            "B (Azul)", "Cinza", "Alfa"
        ])
        self._canal_combo.currentTextChanged.connect(self._atualizar_canal)

        layout.addWidget(self._btn_atualizar)
        layout.addWidget(self._canal_combo)
        layout.addWidget(self._label_hist)

        self._btn_atualizar.clicked.connect(self._gerar_histograma)

        self.setLayout(layout)
        self.setMinimumWidth(400)

        # 🔷 Cache de histogramas
        self._hist_cache = {}

        self._gerar_histograma()

    # ==================================================
    # 🔥 API PÚBLICA (REUTILIZAÇÃO EM OUTROS PLUGINS)
    # ==================================================
    def get_histograma(self, canal=None):
        """
        Retorna histograma (ou lista de histogramas) já cacheado.
        Pode ser usado por outros plugins.
        """
        canal = canal or self._canal_ativo
        return self._obter_histograma(self.imagem_original, canal)

    # ==================================================
    # 🔥 CACHE
    # ==================================================
    def _obter_histograma(self, imagem, canal):
        chave = (id(imagem), canal)

        if chave in self._hist_cache:
            return self._hist_cache[chave]

        hists = self._calcular_histograma(imagem, canal)
        self._hist_cache[chave] = hists

        return hists

    def limpar_cache(self):
        """Use quando a imagem mudar"""
        self._hist_cache.clear()

    # ==================================================
    # 🔥 CÁLCULO PURO
    # ==================================================
    def _calcular_histograma(self, imagem, canal):
        if canal == "Cinza":
            img = cv2.cvtColor(imagem, cv2.COLOR_RGB2GRAY)
            hist = cv2.calcHist([img], [0], None, [256], [0, 256]).flatten()
            return [hist]

        canais = {
            "B (Azul)": (0, (255, 0, 0)),
            "G (Verde)": (1, (0, 255, 0)),
            "R (Vermelho)": (2, (0, 0, 255)),
        }

        if canal == "RGB":
            hists = []
            for idx, _ in canais.values():
                hist = cv2.calcHist([imagem], [idx], None, [256], [0, 256]).flatten()
                hists.append(hist)
            return hists

        elif canal in canais:
            idx, _ = canais[canal]
            hist = cv2.calcHist([imagem], [idx], None, [256], [0, 256]).flatten()
            return [hist]

        return []

    # ==================================================
    # 🔥 PIPELINE PRINCIPAL
    # ==================================================
    def _gerar_histograma(self):
        imagem = self.imagem_original

        hists = self._obter_histograma(imagem, self._canal_ativo)
        cores = self._obter_cores(self._canal_ativo)

        img_hist = self._renderizar_histograma(hists, cores)
        self._exibir_histograma(img_hist)

    # ==================================================
    # 🔥 CORES
    # ==================================================
    def _obter_cores(self, canal):
        mapa = {
            "RGB": [(255, 0, 0), (0, 255, 0), (0, 0, 255)],
            "R (Vermelho)": [(0, 0, 255)],
            "G (Verde)": [(0, 255, 0)],
            "B (Azul)": [(255, 0, 0)],
            "Cinza": [(255, 255, 255)],
        }
        return mapa.get(canal, [(255, 255, 255)])

    # ==================================================
    # 🔥 RENDERIZAÇÃO
    # ==================================================
    def _renderizar_histograma(self, hists, cores):
        altura = 300
        largura = 512

        base = np.zeros((altura, largura, 3), dtype=np.uint8)
        x = np.arange(256) * 2

        for hist, cor in zip(hists, cores):
            hist = hist.copy()
            cv2.normalize(hist, hist, 0, altura, cv2.NORM_MINMAX)
            hist = hist.flatten().astype(int)

            pts = np.column_stack((x, altura - hist))
            pts = np.vstack([
                pts,
                [x[-1], altura],
                [x[0], altura]
            ])

            pts = pts.astype(np.int32).reshape((-1, 1, 2))

            overlay = np.zeros_like(base)
            cv2.fillPoly(overlay, [pts], cor)

            base = cv2.addWeighted(base, 1.0, overlay, 0.4, 0)

        return base

    # ==================================================
    # 🔥 EXIBIÇÃO
    # ==================================================
    def _exibir_histograma(self, imagem_bgr):
        imagem_rgb = cv2.cvtColor(imagem_bgr, cv2.COLOR_BGR2RGB)

        h, w, ch = imagem_rgb.shape
        bytes_per_line = ch * w

        qimg = QImage(
            imagem_rgb.data,
            w,
            h,
            bytes_per_line,
            QImage.Format_RGB888
        )

        pixmap = QPixmap.fromImage(qimg)
        self._label_hist.setPixmap(pixmap)

    def _atualizar_canal(self, texto):
        self._canal_ativo = texto
        self._gerar_histograma()

    # ==================================================
    def processar(self, imagem: np.ndarray) -> np.ndarray:
        return imagem