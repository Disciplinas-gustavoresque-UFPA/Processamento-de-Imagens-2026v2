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
        self._canal_combo.addItems(["RGB", "R (Vermelho)", "G (Verde)", "B (Azul)", "Cinza", "Alfa"])
        self._canal_combo.currentTextChanged.connect(self._atualizar_canal)

        layout.addWidget(self._btn_atualizar)
        layout.addWidget(self._canal_combo)
        layout.addWidget(self._label_hist)

        self._btn_atualizar.clicked.connect(self._gerar_histograma)

        self.setLayout(layout)
        self.setMinimumWidth(400)

        # Gera automaticamente ao abrir
        self._gerar_histograma()

    # --------------------------------------------------
    # Núcleo do histograma
    # --------------------------------------------------

    def _gerar_histograma(self):
        imagem = self.imagem_original

        # --- Modo cinza tem prioridade ---
        if self._canal_ativo == "Cinza":
            imagem = cv2.cvtColor(imagem, cv2.COLOR_RGB2GRAY)
            hist = cv2.calcHist([imagem], [0], None, [256], [0, 256]).flatten()

            img_hist = self._desenhar_histograma(
                [hist],
                cores=[(255, 255, 255)]
            )

        else:
            canais = {
                "B (Azul)": (0, (255, 0, 0)),
                "G (Verde)": (1, (0, 255, 0)),
                "R (Vermelho)": (2, (0, 0, 255)),
            }

            if self._canal_ativo == "RGB":
                hists = []
                cores = []
                for nome, (idx, cor) in canais.items():
                    hist = cv2.calcHist([imagem], [idx], None, [256], [0, 256]).flatten()
                    hists.append(hist)
                    cores.append(cor)

            elif self._canal_ativo in canais:
                idx, cor = canais[self._canal_ativo]
                hist = cv2.calcHist([imagem], [idx], None, [256], [0, 256]).flatten()
                hists = [hist]
                cores = [cor]

            else:
                return  # fallback seguro

            img_hist = self._desenhar_histograma(hists, cores)

        self._exibir_histograma(img_hist)

    # --------------------------------------------------
    # Renderização manual
    # --------------------------------------------------

    def _desenhar_histograma(self, hists, cores):
        altura = 300
        largura = 512

        # Canvas base (preto)
        base = np.zeros((altura, largura, 3), dtype=np.uint8)

        x = np.arange(256) * 2  # escala horizontal

        for hist, cor in zip(hists, cores):
            hist = hist.copy()
            cv2.normalize(hist, hist, 0, altura, cv2.NORM_MINMAX)
            hist = hist.flatten().astype(int)

            # 🔷 Criar polígono fechado
            pts = np.column_stack((x, altura - hist))

            # adicionar base (fechamento do polígono)
            pts = np.vstack([
                pts,
                [x[-1], altura],
                [x[0], altura]
            ])

            pts = pts.astype(np.int32).reshape((-1, 1, 2))

            # 🔷 Camada temporária
            overlay = np.zeros_like(base)

            # Preencher área
            cv2.fillPoly(overlay, [pts], cor)

            # 🔷 Alpha blending (transparência)
            alpha = 0.4
            base = cv2.addWeighted(base, 1.0, overlay, alpha, 0)

        return base

    # --------------------------------------------------
    # Exibir no QLabel
    # --------------------------------------------------

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

    # --------------------------------------------------
    # Override (não altera imagem)
    # --------------------------------------------------

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        return imagem