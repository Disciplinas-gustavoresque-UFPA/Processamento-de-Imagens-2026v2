"""
detector_fogo.py
----------------
Plugin para detecção de fogo e fumaça em imagens utilizando a API do Roboflow.

Funcionalidades
---------------
* Detecta fogo e fumaça em imagens usando modelo pré-treinado (Roboflow Universe).
* Desenha caixas delimitadoras e exibe contagem de detecções e confiança média.
* Permite mostrar ou ocultar caixas delimitadoras.
* Integração com a interface do Studio de Processamento de Imagens.
"""

import cv2
import numpy as np
import logging
import os
from PySide6.QtCore import QObject, QThread, Qt, Signal, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QSlider,
)

# Configuração de logger dedicada ao plugin (sem alterar logger global da aplicação)
# O arquivo é gravado em diretório de dados do usuário para evitar problemas de permissão.

# Inicialização robusta do logger: fallback para StreamHandler se houver erro de permissão/IO
_BASE_DADOS_USUARIO = os.getenv('APPDATA') or os.path.join(os.path.expanduser('~'), '.local', 'share')
_DIR_LOG = os.path.join(_BASE_DADOS_USUARIO, 'Processamento-de-Imagens-2026v2', 'logs')
_LOG_PATH = os.path.join(_DIR_LOG, 'detector_fogo.log')
_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.WARNING)
if not _LOGGER.handlers:
    try:
        os.makedirs(_DIR_LOG, exist_ok=True)
        _handler = logging.FileHandler(_LOG_PATH, encoding='utf-8')
    except Exception as e:
        _handler = logging.StreamHandler()
        _LOGGER.warning(f"Falha ao criar FileHandler para log do plugin: {e}. Usando StreamHandler.")
    _handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    _LOGGER.addHandler(_handler)
_LOGGER.propagate = False

from core.plugin_base import PluginBase


class _DetectorFogoWorker(QObject):
    """Worker para executar inferência sem bloquear a interface gráfica."""

    concluido = Signal(object, int, float)
    falha = Signal(str)

    def __init__(
        self,
        plugin: "DetectorFogo",
        imagem: np.ndarray,
        confianca: int,
        mostrar_boxes: bool,
    ) -> None:
        super().__init__()
        self._plugin = plugin
        self._imagem = imagem
        self._confianca = confianca
        self._mostrar_boxes = mostrar_boxes

    @Slot()
    def run(self) -> None:
        try:
            imagem_resultado, contagem, confianca_media = self._plugin._processar_deteccao(
                self._imagem,
                self._confianca,
                self._mostrar_boxes,
            )
            self.concluido.emit(imagem_resultado, contagem, confianca_media)
        except Exception as e:
            _LOGGER.error(f"Erro na execução assíncrona da detecção: {e}")
            self.falha.emit(str(e))



class DetectorFogo(PluginBase):
    """
    Plugin para detecção de fogo em imagens usando a API do Roboflow.

    Esta classe implementa um plugin que detecta fogo e fumaça em imagens,
    utilizando um modelo YOLOv8 hospedado no Roboflow Universe. O plugin
    permite visualizar as detecções, exibir caixas delimitadoras e aplicar o filtro
    à imagem principal do Studio.
    """

    def closeEvent(self, event):
        """Marca flag de cancelamento ao fechar o diálogo."""
        self._fechado = True
        super().closeEvent(event)

    def showEvent(self, event):
        """Reseta flag de cancelamento ao abrir o diálogo."""
        self._fechado = False
        super().showEvent(event)

    def _resetar_estado_cancelamento(self):
        """Garante que a flag _fechado está False ao iniciar nova detecção."""
        self._fechado = False

    def reject(self) -> None:
        """Impede fechar o diálogo se a detecção estiver em andamento."""
        if hasattr(self, "_thread_deteccao") and self._thread_deteccao is not None and self._thread_deteccao.isRunning():
            QMessageBox.information(self, "Aguarde", "A detecção ainda está em andamento. Aguarde a conclusão para cancelar.")
            return
        super().reject()

    display_name = "Detector de Fogo e Fumaça"

    # Cache do modelo Roboflow (singleton para evitar recarregamento)
    _modelo = None
    _api_key_cache = None

    # Configurações do modelo no Roboflow
    _WORKSPACE = "gadjiiavov-n4n8k"
    _PROJECT = "fire-fhsxx"
    _VERSION = 2
    _API_KEY = "NZYJNuZfV3bJDCpXyYMH"

    # Mapeamento de classes para rótulo em pt-BR
    _CLASSE_LABEL_PTBR = {
        "fire": "Fogo",
        "smoke": "Fumaça"
    }

    # ------------------------------------------------------------------
    # Interface (setup_ui)
    # ------------------------------------------------------------------

    def setup_ui(self) -> None:
        """
        Cria os controles da interface do plugin.

        Controles:
        - Slider para confiança mínima
        - Checkbox para mostrar caixas delimitadoras
        - Rótulo de estatísticas
        - Botões Detectar, Aplicar e Cancelar
        """
        layout_principal = QVBoxLayout(self)

        # --- Slider de confiança mínima ---
        layout_confianca = QHBoxLayout()
        self._rotulo_confianca = QLabel("Confiança mínima:", self)
        self._slider_confianca = QSlider(Qt.Orientation.Horizontal, self)
        self._slider_confianca.setMinimum(0)
        self._slider_confianca.setMaximum(100)
        self._slider_confianca.setValue(20)
        self._slider_confianca.setTickInterval(5)
        self._slider_confianca.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._valor_confianca = QLabel("20%", self)
        layout_confianca.addWidget(self._rotulo_confianca)
        layout_confianca.addWidget(self._slider_confianca)
        layout_confianca.addWidget(self._valor_confianca)
        layout_principal.addLayout(layout_confianca)

        self._slider_confianca.valueChanged.connect(self._atualizar_valor_confianca)

        # --- Checkbox para mostrar caixas delimitadoras ---
        self._checkbox_boxes = QCheckBox("Mostrar caixas delimitadoras", self)
        self._checkbox_boxes.setChecked(True)
        layout_principal.addWidget(self._checkbox_boxes)

        # --- Rótulo para estatísticas de detecção ---
        self._rotulo_estatisticas = QLabel("Detecções: 0 | Confiança média: --", self)
        self._rotulo_estatisticas.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._rotulo_estatisticas.setStyleSheet("font-weight: bold; padding: 10px;")
        layout_principal.addWidget(self._rotulo_estatisticas)

        # --- Botões ---
        layout_botoes = QHBoxLayout()
        self._btn_detectar = QPushButton("Detectar", self)
        self._btn_aplicar = QPushButton("Aplicar", self)
        self._btn_cancelar = QPushButton("Cancelar", self)
        layout_botoes.addWidget(self._btn_detectar)
        layout_botoes.addWidget(self._btn_aplicar)
        layout_botoes.addWidget(self._btn_cancelar)
        layout_principal.addLayout(layout_botoes)

        # --- Conexões ---
        self._checkbox_boxes.stateChanged.connect(self._ao_alterar_checkbox)
        self._btn_detectar.clicked.connect(self._ao_detectar)
        self._btn_aplicar.clicked.connect(self._ao_aplicar)
        self._btn_cancelar.clicked.connect(self.reject)

        self.setLayout(layout_principal)
        self.setMinimumWidth(450)

        # Armazena última imagem processada e estatísticas
        self._ultima_imagem_processada: np.ndarray | None = None
        self._ultima_contagem = 0
        self._ultima_confianca_media = 0.0

    def _atualizar_valor_confianca(self, valor: int) -> None:
        self._valor_confianca.setText(f"{valor}%")

    # ------------------------------------------------------------------
    # Carregamento do modelo
    # ------------------------------------------------------------------

    @classmethod
    def _carregar_modelo(cls, api_key: str):
        """
        Carrega o modelo Roboflow em cache (singleton).

        Parâmetros
        ----------
        api_key : str
            Chave de API do Roboflow.

        Retorna
        -------
        model : objeto do modelo carregado
        """
        if cls._modelo is None or cls._api_key_cache != api_key:
            from roboflow import Roboflow

            rf = Roboflow(api_key=api_key)
            project = rf.workspace(cls._WORKSPACE).project(cls._PROJECT)
            cls._modelo = project.version(cls._VERSION).model
            cls._api_key_cache = api_key
        return cls._modelo

    # ------------------------------------------------------------------
    # Lógica de processamento
    # ------------------------------------------------------------------

    def _processar_deteccao(
        self,
        imagem: np.ndarray,
        confianca: int,
        mostrar_boxes: bool,
    ) -> tuple[np.ndarray, int, float]:
        """Executa a detecção e retorna imagem processada e métricas."""

        if not isinstance(imagem, np.ndarray) or imagem.ndim != 3 or imagem.shape[2] != 3:
            raise ValueError("Imagem de entrada inválida para detecção de fogo.")

        temp_path = None
        try:
            try:
                modelo = self._carregar_modelo(self._API_KEY)
            except ModuleNotFoundError as e:
                if e.name == "roboflow":
                    raise RuntimeError(
                        "A biblioteca 'roboflow' não está instalada. "
                        "Instale com: pip install -r requirements.txt"
                    ) from e
                raise
            except Exception as e:
                raise RuntimeError(f"Erro ao carregar modelo Roboflow: {e}") from e

            import tempfile

            try:
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                    temp_path = tmp.name
                    imagem_bgr = cv2.cvtColor(imagem, cv2.COLOR_RGB2BGR)
                    if not cv2.imwrite(temp_path, imagem_bgr):
                        raise RuntimeError("Falha ao gravar imagem temporária para detecção de fogo.")
            except Exception as e:
                raise RuntimeError(f"Erro ao salvar imagem temporária: {e}") from e

            try:
                resultado = modelo.predict(temp_path, confidence=confianca).json()
            except Exception as e:
                raise RuntimeError(f"Erro ao conectar com a API do Roboflow: {e}") from e

            import json

            _LOGGER.warning(f"Resultado bruto da API Roboflow: {json.dumps(resultado, indent=2, ensure_ascii=False)}")
            if not isinstance(resultado, dict) or 'predictions' not in resultado or not isinstance(resultado['predictions'], list):
                raise RuntimeError("Resposta inesperada da API do Roboflow.")

        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception as e:
                    _LOGGER.error(f"Erro ao remover arquivo temporário: {e}")

        imagem_resultado = imagem.copy()
        predicoes = resultado.get('predictions', [])
        contagem = len(predicoes)
        confidencias = []

        for pred in predicoes:
            try:
                x_center = pred['x']
                y_center = pred['y']
                width = pred['width']
                height = pred['height']
                x1 = int(x_center - width / 2)
                y1 = int(y_center - height / 2)
                x2 = int(x_center + width / 2)
                y2 = int(y_center + height / 2)
                conf = pred['confidence']
                confidencias.append(conf)
                classe_original = pred.get('class', 'fire')
                # Traduzir rótulo para pt-BR se possível
                nome_classe = self._CLASSE_LABEL_PTBR.get(classe_original.lower(), classe_original.capitalize())
                if mostrar_boxes:
                    if classe_original.lower() == 'smoke':
                        cor = (128, 128, 128)
                    else:
                        cor = (255, 100, 0)
                    cv2.rectangle(imagem_resultado, (x1, y1), (x2, y2), cor, 3)
                    label = f"{nome_classe}: {conf:.1%}"
                    tamanho_fonte = 0.55
                    espessura = 1
                    (largura_texto, altura_texto), baseline = cv2.getTextSize(
                        label, cv2.FONT_HERSHEY_SIMPLEX, tamanho_fonte, espessura
                    )
                    padding = 4
                    altura_label = altura_texto + baseline + padding * 2
                    if y1 - altura_label >= 0:
                        label_y1 = y1 - altura_label
                        label_y2 = y1
                        texto_y = y1 - padding - baseline
                    else:
                        label_y1 = y1
                        label_y2 = y1 + altura_label
                        texto_y = y1 + altura_texto + padding
                    cv2.rectangle(
                        imagem_resultado,
                        (x1, label_y1),
                        (x1 + largura_texto + padding * 2, label_y2),
                        cor,
                        -1,
                    )
                    cv2.putText(
                        imagem_resultado,
                        label,
                        (x1 + padding, texto_y),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        tamanho_fonte,
                        (255, 255, 255),
                        espessura,
                        cv2.LINE_AA,
                    )
            except Exception as e:
                _LOGGER.error(f"Erro ao processar caixa delimitadora: {e} | pred: {pred}")

        confianca_media = sum(confidencias) / len(confidencias) if confidencias else 0.0
        return imagem_resultado, contagem, confianca_media

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        """
        Executa a detecção de fogo e fumaça na imagem via API Roboflow.

        Parâmetros
        ----------
        imagem : np.ndarray
            Imagem RGB de entrada.

        Retorna
        -------
        np.ndarray
            Imagem com caixas delimitadoras desenhadas (se habilitado).
        """

        try:
            confianca = self._slider_confianca.value()
            mostrar_boxes = self._checkbox_boxes.isChecked()
            imagem_resultado, contagem, confianca_media = self._processar_deteccao(
                imagem,
                confianca,
                mostrar_boxes,
            )
            self._ultima_contagem = contagem
            self._ultima_confianca_media = confianca_media
            self._atualizar_estatisticas()
            return imagem_resultado
        except Exception as e:
            _LOGGER.error(f"Erro ao processar detecção: {e}")
            QMessageBox.critical(self, "Erro na detecção", str(e))
            if isinstance(imagem, np.ndarray):
                return imagem.copy()
            return np.zeros((100, 100, 3), dtype=np.uint8)

    def _atualizar_estatisticas(self) -> None:
        """Atualiza o rótulo de estatísticas com contagem e confiança média."""
        if self._ultima_contagem > 0:
            texto = (
                f"🔥 Detecções: {self._ultima_contagem} | "
                f"Confiança média: {self._ultima_confianca_media:.1%}"
            )
            self._rotulo_estatisticas.setStyleSheet(
                "font-weight: bold; padding: 10px; color: #ff4500;"
            )
        else:
            texto = "Detecções: 0 | Confiança média: --"
            self._rotulo_estatisticas.setStyleSheet(
                "font-weight: bold; padding: 10px; color: #228b22;"
            )
        self._rotulo_estatisticas.setText(texto)

    # ------------------------------------------------------------------
    # Slots privados
    # ------------------------------------------------------------------

    def _ao_alterar_checkbox(self, _estado: int | None = None) -> None:
        """Reprocessa a imagem quando checkbox é alterado."""
        if self._ultima_imagem_processada is not None:
            self._ao_detectar()


    def _ao_detectar(self) -> None:
        """Executa a detecção e emite o sinal de pré-visualização."""
        self._resetar_estado_cancelamento()
        # Mostrar mensagem de processamento com cursor de espera
        self._rotulo_estatisticas.setText("⏳ Analisando a imagem... Aguarde")
        self._rotulo_estatisticas.setStyleSheet(
            "font-weight: bold; padding: 10px; color: #1e90ff;"
        )
        self._btn_detectar.setEnabled(False)
        self._btn_aplicar.setEnabled(False)
        self.setCursor(Qt.CursorShape.WaitCursor)

        # Forçar atualização da interface antes do processamento
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()

        if hasattr(self, "_thread_deteccao") and self._thread_deteccao is not None and self._thread_deteccao.isRunning():
            return

        confianca = self._slider_confianca.value()
        mostrar_boxes = self._checkbox_boxes.isChecked()

        self._thread_deteccao = QThread(self)
        self._worker_deteccao = _DetectorFogoWorker(
            self,
            self.imagem_original.copy(),
            confianca,
            mostrar_boxes,
        )
        self._worker_deteccao.moveToThread(self._thread_deteccao)

        self._thread_deteccao.started.connect(self._worker_deteccao.run)
        self._worker_deteccao.concluido.connect(self._ao_deteccao_concluida)
        self._worker_deteccao.falha.connect(self._ao_deteccao_falhou)
        self._worker_deteccao.concluido.connect(self._finalizar_deteccao)
        self._worker_deteccao.falha.connect(self._finalizar_deteccao)
        self._worker_deteccao.concluido.connect(self._thread_deteccao.quit)
        self._worker_deteccao.falha.connect(self._thread_deteccao.quit)
        self._thread_deteccao.finished.connect(self._limpar_thread_deteccao)

        self._thread_deteccao.start()

    def _ao_deteccao_concluida(self, imagem_processada: np.ndarray, contagem: int, confianca_media: float) -> None:
        """Atualiza interface quando a detecção assíncrona conclui com sucesso."""
        if hasattr(self, '_fechado') and self._fechado:
            _LOGGER.info("Resultado da thread ignorado: diálogo já foi fechado.")
            return
        self._ultima_imagem_processada = imagem_processada
        self._ultima_contagem = contagem
        self._ultima_confianca_media = confianca_media
        self._atualizar_estatisticas()
        self.preview_requested.emit(imagem_processada)

    def _ao_deteccao_falhou(self, mensagem: str) -> None:
        """Exibe erro de detecção assíncrona sem travar a interface."""
        self._ultima_contagem = 0
        self._ultima_confianca_media = 0.0
        self._atualizar_estatisticas()
        QMessageBox.critical(self, "Erro na detecção", mensagem)

    def _finalizar_deteccao(self, *args) -> None:
        """Restaura o estado da interface ao final da detecção."""
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self._btn_detectar.setEnabled(True)
        self._btn_aplicar.setEnabled(True)

        if "Analisando" in self._rotulo_estatisticas.text():
            self._atualizar_estatisticas()

    def _limpar_thread_deteccao(self) -> None:
        """Libera referências de thread/worker após conclusão."""
        if hasattr(self, "_worker_deteccao") and self._worker_deteccao is not None:
            self._worker_deteccao.deleteLater()
        if hasattr(self, "_thread_deteccao") and self._thread_deteccao is not None:
            self._thread_deteccao.deleteLater()
        self._worker_deteccao = None
        self._thread_deteccao = None

    def _ao_aplicar(self) -> None:
        """Emite o sinal de confirmação e fecha o diálogo."""
        if hasattr(self, "_thread_deteccao") and self._thread_deteccao is not None and self._thread_deteccao.isRunning():
            QMessageBox.information(self, "Aguarde", "A detecção ainda está em andamento.")
            return
        if self._ultima_imagem_processada is None:
            QMessageBox.information(self, "Detecção necessária", "Execute a detecção e aguarde a conclusão antes de aplicar.")
            return
        self.apply_requested.emit(self._ultima_imagem_processada)
        self.accept()
