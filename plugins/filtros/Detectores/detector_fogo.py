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
from PySide6.QtCore import Qt
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
_LOG_PATH = os.path.join(os.path.dirname(__file__), 'detector_fogo.log')
_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.WARNING)
if not _LOGGER.handlers:
    _handler = logging.FileHandler(_LOG_PATH, encoding='utf-8')
    _handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    _LOGGER.addHandler(_handler)
_LOGGER.propagate = False

from core.plugin_base import PluginBase


class DetectorFogo(PluginBase):
    """
    Plugin para detecção de fogo em imagens usando a API do Roboflow.

    Esta classe implementa um plugin que detecta fogo e fumaça em imagens,
    utilizando um modelo YOLOv8 hospedado no Roboflow Universe. O plugin
    permite visualizar as detecções, exibir caixas delimitadoras e aplicar o filtro
    à imagem principal do Studio.
    """

    display_name = "Detector de Fogo e Fumaça"

    # Cache do modelo Roboflow (singleton para evitar recarregamento)
    _modelo = None
    _api_key_cache = None

    # Configurações do modelo no Roboflow
    _WORKSPACE = "gadjiiavov-n4n8k"
    _PROJECT = "fire-fhsxx"
    _VERSION = 2
    _API_KEY = "NZYJNuZfV3bJDCpXyYMH"

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

        # Validação da imagem de entrada
        if not isinstance(imagem, np.ndarray) or imagem.ndim != 3 or imagem.shape[2] != 3:
            _LOGGER.error(f"Imagem de entrada inválida: type={type(imagem)}, shape={getattr(imagem, 'shape', None)}")
            QMessageBox.critical(self, "Erro", "Imagem de entrada inválida para detecção de fogo.")
            return np.zeros((100, 100, 3), dtype=np.uint8)


        temp_path = None
        try:
            # Carrega o modelo Roboflow em cache
            try:
                modelo = self._carregar_modelo(self._API_KEY)
            except ModuleNotFoundError as e:
                if e.name == "roboflow":
                    _LOGGER.error("Dependência 'roboflow' não encontrada no ambiente.")
                    QMessageBox.critical(
                        self,
                        "Dependência ausente",
                        "A biblioteca 'roboflow' não está instalada.\n\n"
                        "Instale com: pip install -r requirements.txt",
                    )
                    return imagem.copy()
                raise
            except Exception as e:
                _LOGGER.error(f"Erro ao carregar modelo Roboflow: {e}")
                QMessageBox.critical(self, "Erro na detecção", f"Erro ao carregar modelo Roboflow:\n\n{e}")
                return imagem.copy()

            confianca = self._slider_confianca.value()

            # Salva imagem temporária para enviar à API
            import tempfile
            import os
            try:
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                    temp_path = tmp.name
                    imagem_bgr = cv2.cvtColor(imagem, cv2.COLOR_RGB2BGR)
                    if not cv2.imwrite(temp_path, imagem_bgr):
                        _LOGGER.error(f"Falha ao gravar imagem temporária em disco: {temp_path}")
                        QMessageBox.critical(
                            self,
                            "Erro",
                            "Falha ao gravar imagem temporária para detecção de fogo.",
                        )
                        return imagem.copy()
            except Exception as e:
                _LOGGER.error(f"Erro ao salvar imagem temporária: {e}")
                QMessageBox.critical(self, "Erro", f"Erro ao salvar imagem temporária: {e}")
                return imagem.copy()

            # Executa inferência via API Roboflow
            try:
                resultado = modelo.predict(temp_path, confidence=confianca).json()
            except Exception as e:
                _LOGGER.error(f"Erro ao conectar com a API do Roboflow: {e}")
                QMessageBox.critical(self, "Erro na detecção", f"Erro ao conectar com a API do Roboflow:\n\n{str(e)}")
                return imagem.copy()

            # Valida resposta da API
            import json
            _LOGGER.warning(f"Resultado bruto da API Roboflow: {json.dumps(resultado, indent=2, ensure_ascii=False)}")
            if not isinstance(resultado, dict) or 'predictions' not in resultado or not isinstance(resultado['predictions'], list):
                _LOGGER.error(f"Resposta inesperada da API: {resultado}")
                QMessageBox.critical(self, "Erro na detecção", "Resposta inesperada da API do Roboflow.")
                return imagem.copy()

        finally:
            # Remove arquivo temporário, se existir
            import os
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception as e:
                    _LOGGER.error(f"Erro ao remover arquivo temporário: {e}")

        # Cria cópia da imagem para desenhar as detecções
        imagem_resultado = imagem.copy()
        predicoes = resultado.get('predictions', [])
        contagem = len(predicoes)
        confidencias = []
        mostrar_boxes = self._checkbox_boxes.isChecked()

        for pred in predicoes:
            try:
                # Processa e desenha cada caixa delimitadora
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
                nome_classe = classe_original.capitalize()
                if mostrar_boxes:
                    if classe_original.lower() == 'smoke':
                        cor = (128, 128, 128)  # Cinza para fumaça
                    else:
                        cor = (255, 100, 0)    # Laranja para fogo
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

        # Atualiza estatísticas de detecção
        self._ultima_contagem = contagem
        self._ultima_confianca_media = (
            sum(confidencias) / len(confidencias) if confidencias else 0.0
        )
        self._atualizar_estatisticas()

        return imagem_resultado

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
        # Mostrar mensagem de processamento com cursor de espera
        self._rotulo_estatisticas.setText("⏳ Analisando a imagem... Aguarde")
        self._rotulo_estatisticas.setStyleSheet(
            "font-weight: bold; padding: 10px; color: #1e90ff;"
        )
        self._btn_detectar.setEnabled(False)
        self.setCursor(Qt.CursorShape.WaitCursor)

        # Forçar atualização da interface antes do processamento
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()

        try:
            imagem_processada = self.processar(self.imagem_original)
            self._ultima_imagem_processada = imagem_processada
            self.preview_requested.emit(imagem_processada)
        except Exception as e:
            _LOGGER.error(f"Erro inesperado ao detectar fogo e fumaça: {e}")
            QMessageBox.critical(self, "Erro na detecção", f"Erro inesperado:\n\n{e}")
        finally:
            # Restaurar cursor e botão
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self._btn_detectar.setEnabled(True)

            # Garante que o rótulo não fique preso em "Analisando..."
            if "Analisando" in self._rotulo_estatisticas.text():
                self._atualizar_estatisticas()

    def _ao_aplicar(self) -> None:
        """Emite o sinal de confirmação e fecha o diálogo."""
        if self._ultima_imagem_processada is None:
            self._ao_detectar()
        if self._ultima_imagem_processada is not None:
            self.apply_requested.emit(self._ultima_imagem_processada)
            self.accept()
