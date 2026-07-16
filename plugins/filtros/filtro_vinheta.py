"""
Plugin para aplicação do efeito de vinheta. A vinheta mantém a região central da imagem mais clara e escurece
 as bordas. O usuário pode controlar a intensidade do escureciment e o raio.
"""
import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
)

from core.plugin_base import PluginBase

class FiltroVinheta(PluginBase):
    display_name = "Vinheta"

    _INTERVALO_PREVIEW_MS = 60

    def setup_ui(self) -> None:
        layout_principal = QVBoxLayout(self)

        self._rotulo_intensidade = QLabel(
            "Intensidade: 50%",
            self,
        )
        self._rotulo_intensidade.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        layout_principal.addWidget(self._rotulo_intensidade)

        self._slider_intensidade = QSlider(
            Qt.Orientation.Horizontal,
            self,
        )
        self._slider_intensidade.setRange(0, 100)
        self._slider_intensidade.setValue(50)
        self._slider_intensidade.setTickInterval(10)
        self._slider_intensidade.setTickPosition(
            QSlider.TickPosition.TicksBelow
        )
        layout_principal.addWidget(self._slider_intensidade)

        self._rotulo_raio = QLabel(
            "Raio central preservado: 55%",
            self,
        )
        self._rotulo_raio.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        layout_principal.addWidget(self._rotulo_raio)

        self._slider_raio = QSlider(
            Qt.Orientation.Horizontal,
            self,
        )
        self._slider_raio.setRange(0, 90)
        self._slider_raio.setValue(55)
        self._slider_raio.setTickInterval(10)
        self._slider_raio.setTickPosition(
            QSlider.TickPosition.TicksBelow
        )
        layout_principal.addWidget(self._slider_raio)

        explicacao = QLabel(
            "A intensidade controla o escurecimento das bordas. "
            "O raio define o tamanho da região central preservada.",
            self,
        )
        explicacao.setWordWrap(True)
        explicacao.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_principal.addWidget(explicacao)

        layout_botoes = QHBoxLayout()

        self._botao_aplicar = QPushButton("Aplicar", self)
        self._botao_cancelar = QPushButton("Cancelar", self)

        layout_botoes.addWidget(self._botao_aplicar)
        layout_botoes.addWidget(self._botao_cancelar)

        layout_principal.addLayout(layout_botoes)

        self._temporizador_preview = QTimer(self)
        self._temporizador_preview.setSingleShot(True)
        self._temporizador_preview.setInterval(
            self._INTERVALO_PREVIEW_MS
        )
        self._temporizador_preview.timeout.connect(
            self._emitir_preview
        )

        self._slider_intensidade.valueChanged.connect(
            self._ao_alterar_parametros
        )
        self._slider_raio.valueChanged.connect(
            self._ao_alterar_parametros
        )

        self._botao_aplicar.clicked.connect(self._ao_aplicar)
        self._botao_cancelar.clicked.connect(self.reject)

        self.setMinimumWidth(380)

    def _obter_parametros(self) -> tuple[float, float]:
    
        intensidade = self._slider_intensidade.value() / 100.0
        raio = self._slider_raio.value() / 100.0

        return intensidade, raio

    @staticmethod
    def _aplicar_smoothstep(valores: np.ndarray) -> np.ndarray:

        valores = np.clip(valores, 0.0, 1.0)

        return valores**2 * (3.0 - 2.0 * valores)

    @classmethod
    def _criar_mascara(
        cls,
        altura: int,
        largura: int,
        intensidade: float,
        raio: float,
    ) -> np.ndarray:

        centro_x = (largura - 1) / 2.0
        centro_y = (altura - 1) / 2.0

        semieixo_x = max(largura / 2.0, 1.0)
        semieixo_y = max(altura / 2.0, 1.0)

        coordenadas_y, coordenadas_x = np.ogrid[
            :altura,
            :largura,
        ]

        distancia_x = (
            coordenadas_x - centro_x
        ) / semieixo_x

        distancia_y = (
            coordenadas_y - centro_y
        ) / semieixo_y

        distancia_radial = np.sqrt(
            distancia_x**2 + distancia_y**2
        ).astype(np.float32)

        largura_transicao = max(1.0 - raio, 1e-6)

        transicao = (
            distancia_radial - raio
        ) / largura_transicao

        transicao_suave = cls._aplicar_smoothstep(
            transicao
        )

        mascara = 1.0 - intensidade * transicao_suave

        return np.clip(
            mascara,
            0.0,
            1.0,
        ).astype(np.float32)

    def processar(self, imagem: np.ndarray) -> np.ndarray:

        if imagem is None or imagem.size == 0:
            return imagem.copy()

        intensidade, raio = self._obter_parametros()

        if intensidade == 0.0:
            return imagem.copy()

        altura, largura = imagem.shape[:2]

        mascara = self._criar_mascara(
            altura=altura,
            largura=largura,
            intensidade=intensidade,
            raio=raio,
        )

        imagem_float = imagem.astype(np.float32)

        if imagem.ndim == 3:
            mascara = mascara[..., np.newaxis]

        resultado = imagem_float * mascara

        return np.rint(
            np.clip(resultado, 0.0, 255.0)
        ).astype(np.uint8)

    def _ao_alterar_parametros(self, _valor: int) -> None:
  
        intensidade = self._slider_intensidade.value()
        raio = self._slider_raio.value()

        self._rotulo_intensidade.setText(
            f"Intensidade: {intensidade}%"
        )

        self._rotulo_raio.setText(
            f"Raio central preservado: {raio}%"
        )

        self._temporizador_preview.start()

    def _emitir_preview(self) -> None:
        imagem_processada = self.processar(
            self.imagem_original
        )

        self.preview_requested.emit(
            imagem_processada
        )

    def _ao_aplicar(self) -> None:
        self._temporizador_preview.stop()

        imagem_processada = self.processar(
            self.imagem_original
        )

        self.apply_requested.emit(
            imagem_processada
        )

        self.accept()