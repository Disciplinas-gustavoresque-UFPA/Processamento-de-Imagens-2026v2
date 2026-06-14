"""
plugins/pixels/visualizacao_planos_bits.py
-------------------------------------------
Plugin de visualização de planos de bits (*bit-plane slicing*).

Permite selecionar um ou mais planos de bit (do bit 7, mais significativo, ao
bit 0, menos significativo) e visualizá-los como uma imagem binária: cada pixel
fica branco (255) quando *algum* dos bits selecionados está ligado e preto (0)
caso contrário.  Útil para inspecionar a contribuição de cada plano.

A operação é feita sobre a intensidade em tons de cinza (clássico de Gonzalez).
"""

import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from core.plugin_base import PluginBase


class VisualizacaoPlanosBits(PluginBase):
    display_name = "Planos de Bits"

    def setup_ui(self) -> None:
        layout_principal = QVBoxLayout(self)

        # --- Seleção de planos de bit (do MSB ao LSB) ---
        layout_principal.addWidget(QLabel("Planos de bit:", self))

        self._checks_bit: dict[int, QCheckBox] = {}
        grade_bits = QGridLayout()
        for posicao, bit in enumerate(range(7, -1, -1)):
            if bit == 7:
                rotulo = f"Bit {bit} (MSB)"
            elif bit == 0:
                rotulo = f"Bit {bit} (LSB)"
            else:
                rotulo = f"Bit {bit}"
            check = QCheckBox(rotulo, self)
            self._checks_bit[bit] = check
            grade_bits.addWidget(check, posicao // 2, posicao % 2)
        layout_principal.addLayout(grade_bits)

        # Começa com o bit mais significativo marcado para um preview imediato.
        self._checks_bit[7].setChecked(True)

        self._rotulo_status = QLabel(self)
        self._rotulo_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_principal.addWidget(self._rotulo_status)

        # --- Botões ---
        layout_botoes = QHBoxLayout()
        self._btn_aplicar = QPushButton("Aplicar", self)
        self._btn_cancelar = QPushButton("Cancelar", self)
        layout_botoes.addWidget(self._btn_aplicar)
        layout_botoes.addWidget(self._btn_cancelar)
        layout_principal.addLayout(layout_botoes)

        self._btn_aplicar.clicked.connect(self._ao_aplicar)
        self._btn_cancelar.clicked.connect(self.reject)

        for check in self._checks_bit.values():
            check.toggled.connect(self._ao_mudar_controle)

        self.setLayout(layout_principal)
        self.setMinimumWidth(320)

        # Força o preview após o render da janela.
        QTimer.singleShot(100, self._emitir_preview)

    def _bits_selecionados(self) -> list[int]:
        return [bit for bit, check in self._checks_bit.items() if check.isChecked()]

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        bits = self._bits_selecionados()
        mascara = 0
        for bit in bits:
            mascara |= 1 << bit

        # Nenhum plano selecionado: imagem totalmente preta (contribuição nula).
        if mascara == 0:
            return np.zeros_like(imagem)

        rgb = imagem[..., :3].astype(np.uint16)
        cinza = np.rint((rgb[..., 0] + rgb[..., 1] + rgb[..., 2]) / 3.0).astype(np.uint8)
        resultado = np.where((cinza & mascara) > 0, 255, 0).astype(np.uint8)
        return np.stack((resultado, resultado, resultado), axis=-1)

    def _texto_status(self) -> str:
        bits = self._bits_selecionados()
        if not bits:
            return "Nenhum plano selecionado"
        lista = ", ".join(str(bit) for bit in sorted(bits, reverse=True))
        return f"Planos: {lista}"

    def _emitir_preview(self) -> None:
        self._rotulo_status.setText(self._texto_status())
        self.preview_requested.emit(self.processar(self.imagem_original))

    def _ao_mudar_controle(self, _marcado: bool = False) -> None:
        self._emitir_preview()

    def _ao_aplicar(self) -> None:
        imagem_processada = self.processar(self.imagem_original)
        self.preview_requested.emit(imagem_processada)
        self.apply_requested.emit(imagem_processada)
        self.accept()
