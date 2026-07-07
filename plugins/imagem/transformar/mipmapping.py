import cv2
import numpy as np
from PySide6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QComboBox,
    QPushButton,
)
from core.plugin_base import PluginBase


class PluginMipmapping(PluginBase):
    display_name = "Mipmapping"

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Configuração da grade M x N
        grade_layout = QHBoxLayout()

        grade_layout.addWidget(QLabel("Linhas (M):"))
        self.spin_m = QSpinBox()
        self.spin_m.setRange(1, 8)
        self.spin_m.setValue(2)
        self.spin_m.valueChanged.connect(self._ao_alterar_config)
        grade_layout.addWidget(self.spin_m)

        grade_layout.addWidget(QLabel("Colunas (N):"))
        self.spin_n = QSpinBox()
        self.spin_n.setRange(1, 8)
        self.spin_n.setValue(2)
        self.spin_n.valueChanged.connect(self._ao_alterar_config)
        grade_layout.addWidget(self.spin_n)

        layout.addLayout(grade_layout)

        # Seleção da abordagem de mipmapping
        layout.addWidget(QLabel("Método de Mipmapping:"))

        self.combo_metodo = QComboBox()
        self.combo_metodo.addItems([
            "Sem mipmapping (Subamostragem Direta)",
            "Mipmapping - Implementação Manual",
            "Mipmapping - OpenCV (pyrDown)"
        ])
        self.combo_metodo.currentIndexChanged.connect(self._ao_alterar_config)
        layout.addWidget(self.combo_metodo)

        self.btn_aplicar = QPushButton("Aplicar no Editor")
        self.btn_aplicar.clicked.connect(self._ao_aplicar)
        layout.addWidget(self.btn_aplicar)

        self.setLayout(layout)
    def _gerar_piramide_manual(self, imagem: np.ndarray) -> list[np.ndarray]:
        """
        Gera todos os níveis da pirâmide gaussiana usando
        filtro binomial seguido de subamostragem.
        """

        kernel = np.array(
            [
                [1, 4, 6, 4, 1],
                [4,16,24,16,4],
                [6,24,36,24,6],
                [4,16,24,16,4],
                [1,4,6,4,1]
            ],
            dtype=np.float32
        ) / 256.0

        mipmaps = [imagem]

        atual = imagem.astype(np.float32)

        while atual.shape[0] > 1 and atual.shape[1] > 1:

            if len(atual.shape) == 3:

                filtrada = np.empty_like(atual)

                for canal in range(atual.shape[2]):
                    filtrada[:, :, canal] = cv2.filter2D(
                        atual[:, :, canal],
                        -1,
                        kernel
                    )

            else:

                filtrada = cv2.filter2D(
                    atual,
                    -1,
                    kernel
                )

            atual = filtrada[::2, ::2]

            mipmaps.append(
                atual.astype(np.uint8)
            )

        return mipmaps
    def _gerar_piramide_cv2(self, imagem: np.ndarray) -> list[np.ndarray]:
        """
        Gera a pirâmide gaussiana utilizando a implementação
        nativa do OpenCV (cv2.pyrDown).
        """

        mipmaps = [imagem]

        atual = imagem.copy()

        while atual.shape[0] > 1 and atual.shape[1] > 1:
            atual = cv2.pyrDown(atual)
            mipmaps.append(atual)

        return mipmaps
    
    def _selecionar_nivel_mipmap(
        self,
        piramide: list[np.ndarray],
        largura_destino: int,
        altura_destino: int,
    ) -> np.ndarray:
        """
        Seleciona o nível da pirâmide cuja resolução é mais adequada
        para a imagem de destino. Caso necessário, realiza um pequeno
        ajuste de tamanho utilizando INTER_AREA.
        """

        melhor = piramide[0]

        for nivel in piramide:

            if (
                nivel.shape[0] >= altura_destino
                and
                nivel.shape[1] >= largura_destino
            ):
                melhor = nivel
            else:
                break

        if (
            melhor.shape[0] != altura_destino
            or
            melhor.shape[1] != largura_destino
        ):
            melhor = cv2.resize(
                melhor,
                (largura_destino, altura_destino),
                interpolation=cv2.INTER_AREA,
            )

        return melhor
    
    def processar(self, imagem: np.ndarray) -> np.ndarray:
        m = self.spin_m.value()
        n = self.spin_n.value()
        metodo = self.combo_metodo.currentIndex()

        alt_orig, larg_orig = imagem.shape[:2]

        nova_alt = max(1, alt_orig // m)
        nova_larg = max(1, larg_orig // n)

        # ==========================================================
        # Método 0 - Subamostragem direta (sem mipmapping)
        # ==========================================================
        if metodo == 0:

            sub_img = cv2.resize(
                imagem,
                (nova_larg, nova_alt),
                interpolation=cv2.INTER_NEAREST,
            )

        # ==========================================================
        # Método 1 - Pirâmide Gaussiana manual
        # ==========================================================
        elif metodo == 1:

            piramide = self._gerar_piramide_manual(imagem)

            sub_img = self._selecionar_nivel_mipmap(
                piramide,
                nova_larg,
                nova_alt,
            )
        # ==========================================================
        # Método 2 - Mipmapping usando OpenCV (cv2.pyrDown)
        # ==========================================================
        else:

            piramide = self._gerar_piramide_cv2(imagem)

            sub_img = self._selecionar_nivel_mipmap(
                piramide,
                nova_larg,
                nova_alt,
            )       
        # ==========================================================
        # Montagem da grade M × N utilizando a imagem reduzida
        # ==========================================================
        if imagem.ndim == 3:
            grade = np.tile(sub_img, (m, n, 1))
        else:
            grade = np.tile(sub_img, (m, n))

        return cv2.resize(
            grade,
            (larg_orig, alt_orig),
            interpolation=cv2.INTER_LINEAR,
        )

    def _ao_alterar_config(self):
        if hasattr(self, "imagem_original"):
            self.preview_requested.emit(
                self.processar(self.imagem_original)
            )

    def _ao_aplicar(self):
        if hasattr(self, "imagem_original"):
            self.apply_requested.emit(
                self.processar(self.imagem_original)
            )
            self.accept()