"""Plugin de localização de imagens por Template Matching.

O plugin permite selecionar uma imagem de referência e procurar ocorrências
semelhantes dentro da imagem aberta. A busca é realizada em múltiplas escalas,
permitindo localizar o objeto mesmo quando ele aparece em tamanhos diferentes.

As regiões encontradas são destacadas com retângulos e seus respectivos índices
de similaridade. O usuário pode ajustar o threshold de detecção e visualizar um
mapa de calor com as regiões de maior correspondência.
"""

import os

import cv2
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
)

from core.plugin_base import PluginBase


class LocalizarTemplate(PluginBase):
    """Localiza ocorrências de uma imagem de referência em múltiplas escalas."""

    display_name = "Localizar imagem de referência"

    def setup_ui(self):
        self.setWindowTitle("Localizar imagem de referência")
        self.resize(520, 300)

        self.template_rgb = None
        self.template_mask = None
        self.caminho_template = None
        self.max_deteccoes = 12
        self.tamanho_minimo_alvo = 32
        self.candidatos_por_escala = 40
        self.quantidade_escalas = 12

        layout = QVBoxLayout(self)

        self.label_instrucao = QLabel(
            "Localiza, na imagem aberta, regiões semelhantes à imagem de referência "
            "selecionada. A busca é feita automaticamente em vários tamanhos. "
            "O threshold controla a similaridade mínima: valores menores encontram "
            "mais regiões, enquanto valores maiores mantêm apenas as correspondências "
            "mais fortes. O mapa de calor destaca as áreas com maior semelhança."
        )
        self.label_instrucao.setWordWrap(True)
        layout.addWidget(self.label_instrucao)

        self.label_template = QLabel("Template: nenhum selecionado")
        layout.addWidget(self.label_template)

        self.btn_selecionar = QPushButton("Selecionar imagem de referência")
        self.btn_selecionar.clicked.connect(self._selecionar_template)
        layout.addWidget(self.btn_selecionar)

        self.check_mapa_calor = QCheckBox("Mostrar mapa de calor de similaridade")
        self.check_mapa_calor.setChecked(True)
        self.check_mapa_calor.stateChanged.connect(self._atualizar_preview)
        layout.addWidget(self.check_mapa_calor)

        linha_threshold = QHBoxLayout()

        self.label_threshold = QLabel("Threshold: 55%")
        linha_threshold.addWidget(self.label_threshold)

        self.slider_threshold = QSlider(Qt.Orientation.Horizontal)
        self.slider_threshold.setRange(1, 100)
        self.slider_threshold.setValue(55)
        self.slider_threshold.valueChanged.connect(self._ao_mudar_threshold)
        linha_threshold.addWidget(self.slider_threshold)

        layout.addLayout(linha_threshold)

        self.label_resultado = QLabel("Regiões encontradas: 0")
        self.label_resultado.setWordWrap(True)
        layout.addWidget(self.label_resultado)

        linha_botoes = QHBoxLayout()

        self.btn_aplicar = QPushButton("Aplicar")
        self.btn_aplicar.clicked.connect(self._aplicar)
        linha_botoes.addWidget(self.btn_aplicar)

        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.clicked.connect(self.reject)
        linha_botoes.addWidget(self.btn_cancelar)

        layout.addLayout(linha_botoes)
        self.setLayout(layout)

    def _selecionar_template(self):
        caminho, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar imagem de referência",
            "",
            "Imagens (*.png *.jpg *.jpeg *.bmp *.tiff *.tif)",
        )

        if not caminho:
            return

        resultado = self._carregar_template(caminho)

        if resultado is None:
            QMessageBox.critical(
                self,
                "Erro",
                "Não foi possível abrir a imagem de referência.",
            )
            return

        self.template_rgb, self.template_mask = resultado
        self.caminho_template = caminho
        self.label_template.setText(f"Template: {os.path.basename(caminho)}")

        self._atualizar_preview()

    def _carregar_template(self, caminho):
        imagem = cv2.imread(caminho, cv2.IMREAD_UNCHANGED)

        if imagem is None:
            return None

        if imagem.ndim == 2:
            rgb = cv2.cvtColor(imagem, cv2.COLOR_GRAY2RGB)
            mask = np.full(imagem.shape, 255, dtype=np.uint8)

        elif imagem.shape[2] == 4:
            bgr = imagem[:, :, :3]
            alpha = imagem[:, :, 3]
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            mask = np.where(alpha > 20, 255, 0).astype(np.uint8)

        else:
            rgb = cv2.cvtColor(imagem, cv2.COLOR_BGR2RGB)
            mask = self._criar_mascara_automatica(rgb)

        mask = self._limpar_mascara(mask)

        ys, xs = np.where(mask > 0)

        if len(xs) == 0 or len(ys) == 0:
            mask = np.full(rgb.shape[:2], 255, dtype=np.uint8)
            return rgb, mask

        x, y, w, h = cv2.boundingRect(mask)

        margem = 4
        x1 = max(0, x - margem)
        y1 = max(0, y - margem)
        x2 = min(rgb.shape[1], x + w + margem)
        y2 = min(rgb.shape[0], y + h + margem)

        rgb_crop = rgb[y1:y2, x1:x2]
        mask_crop = mask[y1:y2, x1:x2]

        return rgb_crop, mask_crop

    def _criar_mascara_automatica(self, rgb):
        hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)

        saturacao = hsv[:, :, 1]
        valor = hsv[:, :, 2]

        # Remove fundo branco/cinza quadriculado, mantendo objetos coloridos.
        mask = np.where((saturacao > 35) & (valor > 60), 255, 0).astype(np.uint8)

        proporcao = np.count_nonzero(mask) / mask.size

        # Se a máscara ficou ruim, usa o template inteiro.
        if proporcao < 0.02 or proporcao > 0.95:
            mask = np.full(rgb.shape[:2], 255, dtype=np.uint8)

        return mask

    def _limpar_mascara(self, mask):
        kernel = np.ones((3, 3), np.uint8)

        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.dilate(mask, kernel, iterations=1)

        return mask

    def _ao_mudar_threshold(self, *_):
        valor = self.slider_threshold.value()
        self.label_threshold.setText(f"Threshold: {valor}%")
        self._atualizar_preview()

    def _threshold(self) -> float:
        return self.slider_threshold.value() / 100.0

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        if self.template_rgb is None:
            return imagem.copy()

        imagem_saida = imagem.copy()

        altura_img, largura_img = imagem.shape[:2]
        altura_tpl, largura_tpl = self.template_rgb.shape[:2]

        if altura_tpl > altura_img or largura_tpl > largura_img:
            self.label_resultado.setText(
                "Template maior que a imagem aberta. O sistema tentará reduzir automaticamente."
            )

        imagem_edges = self._extrair_bordas(imagem)

        ocorrencias, mapa_calor = self._buscar_ocorrencias_multiescala(
            imagem_edges,
            largura_img,
            altura_img,
        )

        if self.check_mapa_calor.isChecked() and mapa_calor is not None:
            imagem_saida = self._aplicar_mapa_calor(imagem_saida, mapa_calor)

        for x, y, w, h, score in ocorrencias:
            cv2.rectangle(
                imagem_saida,
                (x, y),
                (x + w, y + h),
                (0, 255, 0),
                2,
            )

            texto = f"{score * 100:.1f}%"
            cv2.putText(
                imagem_saida,
                texto,
                (x, max(18, y - 6)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.50,
                (0, 255, 0),
                2,
                cv2.LINE_AA,
            )

        if ocorrencias:
            melhor = ocorrencias[0][4] * 100
            self.label_resultado.setText(
                f"Regiões encontradas: {len(ocorrencias)} | "
                f"Melhor similaridade: {melhor:.1f}%"
            )
        else:
            self.label_resultado.setText(
                "Nenhuma região encontrada. Tente diminuir o threshold."
            )

        return imagem_saida

    def _extrair_bordas(self, imagem_rgb):
        gray = cv2.cvtColor(imagem_rgb, cv2.COLOR_RGB2GRAY)
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        edges = cv2.Canny(gray, 60, 160)
        return edges

    def _buscar_ocorrencias_multiescala(self, imagem_edges, largura_img, altura_img):
        template_edges_original = self._extrair_bordas(self.template_rgb)

        altura_tpl, largura_tpl = template_edges_original.shape[:2]

        menor_escala = max(
            0.04,
            min(10 / max(largura_tpl, 1), 10 / max(altura_tpl, 1)),
        )

        maior_escala = min(
            1.0,
            largura_img / max(largura_tpl, 1),
            altura_img / max(altura_tpl, 1),
        )

        if maior_escala < menor_escala:
            maior_escala = menor_escala

        escalas = np.geomspace(menor_escala, maior_escala, self.quantidade_escalas)

        caixas = []
        mapa_calor_final = np.zeros((altura_img, largura_img), dtype=np.float32)

        threshold = self._threshold()

        for escala in escalas:
            largura_red = int(largura_tpl * escala)
            altura_red = int(altura_tpl * escala)

            if largura_red < self.tamanho_minimo_alvo or altura_red < self.tamanho_minimo_alvo:
                continue

            if largura_red > largura_img or altura_red > altura_img:
                continue

            template_edges = cv2.resize(
                template_edges_original,
                (largura_red, altura_red),
                interpolation=cv2.INTER_AREA,
            )

            template_mask = cv2.resize(
                self.template_mask,
                (largura_red, altura_red),
                interpolation=cv2.INTER_NEAREST,
            )

            try:
                mapa = cv2.matchTemplate(
                    imagem_edges,
                    template_edges,
                    cv2.TM_CCORR_NORMED,
                    mask=template_mask,
                )
            except cv2.error:
                mapa = cv2.matchTemplate(
                    imagem_edges,
                    template_edges,
                    cv2.TM_CCORR_NORMED,
                )

            mapa = np.nan_to_num(
                mapa,
                nan=0.0,
                posinf=0.0,
                neginf=0.0,
            )

            mapa_expandido = cv2.resize(
                mapa,
                (largura_img, altura_img),
                interpolation=cv2.INTER_CUBIC,
            )

            mapa_calor_final = np.maximum(mapa_calor_final, mapa_expandido)

            ys, xs = np.where(mapa >= threshold)

            if len(xs) == 0:
                continue

            scores = mapa[ys, xs]
            ordem = np.argsort(scores)[::-1][:self.candidatos_por_escala]

            for indice in ordem:
                x = int(xs[indice])
                y = int(ys[indice])
                score = float(scores[indice])

                caixas.append(
                    (
                        x,
                        y,
                        largura_red,
                        altura_red,
                        score,
                    )
                )

        caixas = sorted(caixas, key=lambda item: item[4], reverse=True)
        caixas = self._suprimir_sobreposicoes(caixas)

        return caixas, mapa_calor_final

    def _aplicar_mapa_calor(self, imagem_rgb, mapa_calor):
        mapa_normalizado = cv2.normalize(
            mapa_calor,
            None,
            0,
            255,
            cv2.NORM_MINMAX,
        ).astype(np.uint8)

        mapa_colorido_bgr = cv2.applyColorMap(
            mapa_normalizado,
            cv2.COLORMAP_JET,
        )

        mapa_colorido_rgb = cv2.cvtColor(
            mapa_colorido_bgr,
            cv2.COLOR_BGR2RGB,
        )

        imagem_com_mapa = cv2.addWeighted(
            imagem_rgb,
            0.65,
            mapa_colorido_rgb,
            0.35,
            0,
        )

        return imagem_com_mapa

    def _suprimir_sobreposicoes(self, caixas, limite_iou=0.15):
        if not caixas:
            return []

        caixas = sorted(caixas, key=lambda item: item[4], reverse=True)
        selecionadas = []

        for caixa in caixas:
            x, y, w, h, score = caixa

            centro_x = x + w / 2
            centro_y = y + h / 2

            muito_perto = False

            for sx, sy, sw, sh, _sscore in selecionadas:
                centro_sx = sx + sw / 2
                centro_sy = sy + sh / 2

                distancia = np.sqrt(
                    (centro_x - centro_sx) ** 2 +
                    (centro_y - centro_sy) ** 2
                )

                distancia_minima = max(w, h, sw, sh) * 0.65

                if distancia < distancia_minima:
                    muito_perto = True
                    break

                x1 = max(x, sx)
                y1 = max(y, sy)
                x2 = min(x + w, sx + sw)
                y2 = min(y + h, sy + sh)

                inter_w = max(0, x2 - x1)
                inter_h = max(0, y2 - y1)
                inter = inter_w * inter_h

                area_a = w * h
                area_b = sw * sh
                uniao = area_a + area_b - inter

                iou = inter / max(uniao, 1e-6)

                if iou > limite_iou:
                    muito_perto = True
                    break

            if not muito_perto:
                selecionadas.append(caixa)

            if len(selecionadas) >= self.max_deteccoes:
                break

        resultado = []

        for x, y, w, h, score in selecionadas:
            resultado.append(
                (
                    int(x),
                    int(y),
                    int(w),
                    int(h),
                    float(score),
                )
            )

        return resultado

    def _atualizar_preview(self, *_):
        if self.template_rgb is None:
            return

        imagem_processada = self.processar(self.imagem_original)
        self.preview_requested.emit(imagem_processada)

    def _aplicar(self):
        if self.template_rgb is None:
            QMessageBox.information(
                self,
                "Aviso",
                "Selecione uma imagem de referência primeiro.",
            )
            return

        imagem_processada = self.processar(self.imagem_original)
        self.apply_requested.emit(imagem_processada)
        self.accept()