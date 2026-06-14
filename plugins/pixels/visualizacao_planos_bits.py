"""
plugins/pixels/visualizacao_planos_bits.py
-------------------------------------------
Plugin de visualização de planos de bits (*bit-plane slicing*).

Permite selecionar um ou mais planos de bit (do bit 7, mais significativo, ao
bit 0, menos significativo) e visualizá-los de duas formas:

* **Plano binário** — cada pixel fica branco (255) quando *algum* dos bits
  selecionados está ligado e preto (0) caso contrário.  Útil para inspecionar
  um plano isolado.
* **Reconstrução** — mantém apenas os bits selecionados no seu peso original e
  zera os demais, evidenciando a contribuição daqueles planos para a imagem.

A operação pode ser feita sobre a intensidade em tons de cinza (clássico de
Gonzalez) ou canal a canal sobre o RGB, preservando a cor.
"""

import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
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

        # --- Domínio: tons de cinza ou por canal RGB ---
        layout_principal.addWidget(QLabel("Domínio:", self))
        self._grupo_dominio = QButtonGroup(self)
        self._radios_dominio: dict[str, QRadioButton] = {}
        for texto, valor in [("Tons de cinza", "cinza"), ("Por canal RGB", "rgb")]:
            radio = QRadioButton(texto, self)
            self._grupo_dominio.addButton(radio)
            self._radios_dominio[valor] = radio
            layout_principal.addWidget(radio)
        self._radios_dominio["cinza"].setChecked(True)

        # --- Modo de exibição ---
        layout_principal.addWidget(QLabel("Modo de exibição:", self))
        self._grupo_modo = QButtonGroup(self)
        self._radios_modo: dict[str, QRadioButton] = {}
        for texto, valor in [("Plano binário", "binario"), ("Reconstrução", "reconstrucao")]:
            radio = QRadioButton(texto, self)
            self._grupo_modo.addButton(radio)
            self._radios_modo[valor] = radio
            layout_principal.addWidget(radio)
        self._radios_modo["binario"].setChecked(True)

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
        for radio in (*self._radios_dominio.values(), *self._radios_modo.values()):
            radio.toggled.connect(self._ao_mudar_controle)

        self.setLayout(layout_principal)
        self.setMinimumWidth(320)

        # Força o preview após o render da janela.
        QTimer.singleShot(100, self._emitir_preview)

    def _bits_selecionados(self) -> list[int]:
        return [bit for bit, check in self._checks_bit.items() if check.isChecked()]

    def _dominio(self) -> str:
        return "rgb" if self._radios_dominio["rgb"].isChecked() else "cinza"

    def _modo(self) -> str:
        return "reconstrucao" if self._radios_modo["reconstrucao"].isChecked() else "binario"

    def _fatiar(self, canais: np.ndarray, mascara: int, modo: str) -> np.ndarray:
        """Aplica o fatiamento de bits a um array uint8 (qualquer formato)."""
        if modo == "binario":
            return np.where((canais & mascara) > 0, 255, 0).astype(np.uint8)
        return (canais & mascara).astype(np.uint8)

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        bits = self._bits_selecionados()
        mascara = 0
        for bit in bits:
            mascara |= 1 << bit

        # Nenhum plano selecionado: imagem totalmente preta (contribuição nula).
        if mascara == 0:
            return np.zeros_like(imagem)

        modo = self._modo()

        if self._dominio() == "cinza":
            rgb = imagem[..., :3].astype(np.uint16)
            cinza = np.rint((rgb[..., 0] + rgb[..., 1] + rgb[..., 2]) / 3.0).astype(np.uint8)
            resultado = self._fatiar(cinza, mascara, modo)
            return np.stack((resultado, resultado, resultado), axis=-1)

        saida = imagem.copy()
        saida[..., :3] = self._fatiar(imagem[..., :3], mascara, modo)
        return saida

    def _texto_status(self) -> str:
        bits = self._bits_selecionados()
        if not bits:
            return "Nenhum plano selecionado"
        lista = ", ".join(str(bit) for bit in sorted(bits, reverse=True))
        return f"Planos: {lista}  |  {self._radios_modo[self._modo()].text()}"

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
