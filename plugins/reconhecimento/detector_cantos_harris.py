import cv2
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
)

from core.plugin_base import PluginBase


class DetectorCantosHarris(PluginBase):
    display_name = "Detector de Cantos de Harris"

    def setup_ui(self):
        self.setWindowTitle("Detector de Cantos de Harris")
        self.resize(520, 340)

        layout = QVBoxLayout(self)

        instrucao = QLabel(
            "Detecta cantos usando a técnica de Harris. "
            "Ajuste o threshold: menor detecta mais cantos; maior mantém apenas os cantos mais fortes."
        )
        instrucao.setWordWrap(True)
        layout.addWidget(instrucao)

        # Threshold
        linha_threshold = QHBoxLayout()

        self.label_threshold = QLabel("Threshold: 1%")
        linha_threshold.addWidget(self.label_threshold)

        self.slider_threshold = QSlider(Qt.Orientation.Horizontal)
        self.slider_threshold.setRange(1, 20)
        self.slider_threshold.setValue(1)
        self.slider_threshold.valueChanged.connect(self._ao_alterar_threshold)
        linha_threshold.addWidget(self.slider_threshold)

        layout.addLayout(linha_threshold)

        # Block size
        linha_block = QHBoxLayout()
        linha_block.addWidget(QLabel("Vizinhança:"))

        self.spin_block = QSpinBox()
        self.spin_block.setRange(2, 15)
        self.spin_block.setValue(2)
        self.spin_block.valueChanged.connect(self._atualizar_preview)
        linha_block.addWidget(self.spin_block)

        layout.addLayout(linha_block)

        # Ksize
        linha_ksize = QHBoxLayout()
        linha_ksize.addWidget(QLabel("Abertura Sobel:"))

        self.spin_ksize = QSpinBox()
        self.spin_ksize.setRange(3, 7)
        self.spin_ksize.setSingleStep(2)
        self.spin_ksize.setValue(3)
        self.spin_ksize.valueChanged.connect(self._garantir_ksize_impar)
        linha_ksize.addWidget(self.spin_ksize)

        layout.addLayout(linha_ksize)

        # K
        linha_k = QHBoxLayout()
        linha_k.addWidget(QLabel("Parâmetro k:"))

        self.spin_k = QDoubleSpinBox()
        self.spin_k.setRange(0.01, 0.20)
        self.spin_k.setSingleStep(0.01)
        self.spin_k.setValue(0.04)
        self.spin_k.valueChanged.connect(self._atualizar_preview)
        linha_k.addWidget(self.spin_k)

        layout.addLayout(linha_k)

        self.check_supressao = QCheckBox("Reduzir pontos muito próximos")
        self.check_supressao.setChecked(True)
        self.check_supressao.stateChanged.connect(self._atualizar_preview)
        layout.addWidget(self.check_supressao)

        self.check_mapa_resposta = QCheckBox("Mostrar mapa de resposta de Harris")
        self.check_mapa_resposta.setChecked(False)
        self.check_mapa_resposta.stateChanged.connect(self._atualizar_preview)
        layout.addWidget(self.check_mapa_resposta)

        self.label_resultado = QLabel("Cantos detectados: 0")
        self.label_resultado.setWordWrap(True)
        layout.addWidget(self.label_resultado)

        linha_botoes = QHBoxLayout()

        self.btn_preview = QPushButton("Pré-visualizar")
        self.btn_preview.clicked.connect(self._atualizar_preview)
        linha_botoes.addWidget(self.btn_preview)

        self.btn_aplicar = QPushButton("Aplicar")
        self.btn_aplicar.clicked.connect(self._aplicar)
        linha_botoes.addWidget(self.btn_aplicar)

        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.clicked.connect(self.reject)
        linha_botoes.addWidget(self.btn_cancelar)

        layout.addLayout(linha_botoes)
        self.setLayout(layout)

    def _ao_alterar_threshold(self, *_):
        valor = self.slider_threshold.value()
        self.label_threshold.setText(f"Threshold: {valor}%")
        self._atualizar_preview()

    def _garantir_ksize_impar(self, valor):
        if valor % 2 == 0:
            self.spin_ksize.setValue(valor + 1)
            return

        self._atualizar_preview()

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        saida = imagem.copy()

        cinza = cv2.cvtColor(imagem, cv2.COLOR_RGB2GRAY)
        cinza = np.float32(cinza)

        block_size = self.spin_block.value()
        ksize = self.spin_ksize.value()
        k = self.spin_k.value()

        resposta = cv2.cornerHarris(
            cinza,
            blockSize=block_size,
            ksize=ksize,
            k=k,
        )

        resposta = cv2.dilate(resposta, None)

        resposta_maxima = resposta.max()

        if resposta_maxima <= 0:
            self.label_resultado.setText("Cantos detectados: 0")
            return saida

        threshold = (self.slider_threshold.value() / 100.0) * resposta_maxima

        mapa_binario = resposta > threshold

        if self.check_supressao.isChecked():
            pontos = self._extrair_pontos_com_supressao(resposta, mapa_binario)
        else:
            ys, xs = np.where(mapa_binario)
            pontos = list(zip(xs, ys))

        if self.check_mapa_resposta.isChecked():
            saida = self._aplicar_mapa_resposta(imagem, resposta)

        for x, y in pontos:
            cv2.circle(
                saida,
                (int(x), int(y)),
                3,
                (255, 0, 0),
                -1,
                cv2.LINE_AA,
            )

        self.label_resultado.setText(
            f"Cantos detectados: {len(pontos)}"
        )

        return saida

    def _extrair_pontos_com_supressao(self, resposta, mapa_binario):
        resposta_normalizada = cv2.normalize(
            resposta,
            None,
            0,
            255,
            cv2.NORM_MINMAX,
        ).astype(np.uint8)

        componentes, labels, stats, centroids = cv2.connectedComponentsWithStats(
            mapa_binario.astype(np.uint8),
            connectivity=8,
        )

        pontos = []

        for rotulo in range(1, componentes):
            mascara = labels == rotulo

            if not np.any(mascara):
                continue

            ys, xs = np.where(mascara)
            valores = resposta_normalizada[ys, xs]

            indice_melhor = np.argmax(valores)

            x = xs[indice_melhor]
            y = ys[indice_melhor]

            area = stats[rotulo, cv2.CC_STAT_AREA]

            # Evita ruídos muito grandes ou componentes estranhos.
            if area <= 0:
                continue

            pontos.append((x, y))

        return pontos

    def _aplicar_mapa_resposta(self, imagem_rgb, resposta):
        resposta_norm = cv2.normalize(
            resposta,
            None,
            0,
            255,
            cv2.NORM_MINMAX,
        ).astype(np.uint8)

        mapa_bgr = cv2.applyColorMap(
            resposta_norm,
            cv2.COLORMAP_JET,
        )

        mapa_rgb = cv2.cvtColor(
            mapa_bgr,
            cv2.COLOR_BGR2RGB,
        )

        imagem_com_mapa = cv2.addWeighted(
            imagem_rgb,
            0.65,
            mapa_rgb,
            0.35,
            0,
        )

        return imagem_com_mapa

    def _atualizar_preview(self, *_):
        imagem_processada = self.processar(self.imagem_original)
        self.preview_requested.emit(imagem_processada)

    def _aplicar(self):
        imagem_processada = self.processar(self.imagem_original)
        self.apply_requested.emit(imagem_processada)
        self.accept()