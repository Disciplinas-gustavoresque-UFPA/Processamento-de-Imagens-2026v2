"""
app.py
------
Janela Principal do Studio de Processamento de Imagens.

Funcionalidades
---------------
* Abrir e fechar imagens (PNG, JPG, BMP, TIFF).
* Suporte a abertura a múltiplas imagens via abas
* Barra superior com abas exibindo o nome das imagens.
* Exibir a imagem em um QLabel centralizado com redimensionamento automático.
* Carregar plugins dinamicamente em três grupos de menu:
    - ``Pixels`` para operações pontuais (ex.: brilho/contraste).
    - ``Imagem`` para transformações geométricas e ajustes globais.
    - ``Filtros`` para operações regionais.
* Pré-visualizar e aplicar plugins via os sinais ``preview_requested`` e
    ``apply_requested`` definidos em ``PluginBase``.
"""

import importlib.util
import inspect
import os
import sys

import cv2
import numpy as np
from PySide6.QtCore import Qt, QSettings, Signal, QSize, QTimer, qInstallMessageHandler
from PySide6.QtGui import QColor, QIcon, QImage, QKeySequence, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QSizePolicy,
    QTabBar,
    QTabWidget,
    QDialog,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from core.memento import Historico

# Garante que o diretório raiz do projeto esteja no sys.path para que os
# plugins possam importar ``core.plugin_base`` sem ajustes manuais.
_DIRETORIO_RAIZ = os.path.dirname(os.path.abspath(__file__))
if _DIRETORIO_RAIZ not in sys.path:
    sys.path.insert(0, _DIRETORIO_RAIZ)

from core.plugin_base import PluginBase  # noqa: E402  (importação após sys.path)
from components.zoom import VisualizadorImagem  # noqa: E402
from layout import BarraFerramentasEsquerda, BarraLateralDireita  # noqa: E402


_HANDLER_MENSAGENS_QT = None
_HANDLER_MENSAGENS_QT_ANTERIOR = None


def _instalar_filtro_mensagens_qt() -> None:
    """Suprime warnings do Qt conhecidos por serem ruído no console.

    No Windows, alguns caminhos internos podem chamar `QFont::setPointSize(-1)`
    (ponto indefinido), gerando um aviso que não afeta a execução do app.
    Filtramos apenas essa mensagem específica para não esconder outros warnings.
    """

    global _HANDLER_MENSAGENS_QT
    global _HANDLER_MENSAGENS_QT_ANTERIOR
    if _HANDLER_MENSAGENS_QT is not None:
        return

    def handler(tipo, contexto, mensagem: str) -> None:
        if mensagem.startswith(
            "QFont::setPointSize: Point size <= 0 (-1), must be greater than 0"
        ):
            return

        handler_anterior = _HANDLER_MENSAGENS_QT_ANTERIOR
        if callable(handler_anterior):
            handler_anterior(tipo, contexto, mensagem)
            return

        # Fallback: mantém ao menos a mensagem visível caso não exista handler anterior.
        sys.stderr.write(mensagem + "\n")

    _HANDLER_MENSAGENS_QT = handler
    _HANDLER_MENSAGENS_QT_ANTERIOR = qInstallMessageHandler(_HANDLER_MENSAGENS_QT)
from camera.gerenciar_camera import DialogoCamera


# ---------------------------------------------------------------------------
# Widget de arrastar e soltar (drag-and-drop)
# ---------------------------------------------------------------------------

_EXTENSOES_IMAGEM = (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif")
_EXTENSOES_SALVAMENTO = {".png", ".jpg", ".jpeg", ".bmp"}
_EXTENSAO_PADRAO_SALVAMENTO = ".png"


class AreaArrastarImagem(QLabel):
    """Área visual onde o usuário pode arrastar e soltar um arquivo de imagem."""

    arquivo_solto = Signal(str)

    _ESTILO_NORMAL = """
        QLabel {
            border: 2px dashed #aaa;
            border-radius: 8px;
            color: #888;
            font-size: 14px;
            background-color: #f9f9f9;
        }
    """
    _ESTILO_HOVER = """
        QLabel {
            border: 2px dashed #4a90d9;
            border-radius: 8px;
            color: #4a90d9;
            font-size: 14px;
            background-color: #e8f0fe;
        }
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setText("Arraste uma imagem aqui")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedSize(420, 120)
        self.setStyleSheet(self._ESTILO_NORMAL)

    def dragEnterEvent(self, evento):
        if evento.mimeData().hasUrls():
            for url in evento.mimeData().urls():
                if url.toLocalFile().lower().endswith(_EXTENSOES_IMAGEM):
                    self.setStyleSheet(self._ESTILO_HOVER)
                    evento.acceptProposedAction()
                    return
        evento.ignore()

    def dragLeaveEvent(self, evento):
        self.setStyleSheet(self._ESTILO_NORMAL)
        super().dragLeaveEvent(evento)

    def dropEvent(self, evento):
        self.setStyleSheet(self._ESTILO_NORMAL)
        for url in evento.mimeData().urls():
            caminho = url.toLocalFile()
            if caminho.lower().endswith(_EXTENSOES_IMAGEM):
                self.arquivo_solto.emit(caminho)
                return



# ---------------------------------------------------------------------------
# Carregamento dinâmico de plugins
# ---------------------------------------------------------------------------

def _carregar_classes_do_arquivo(caminho_arquivo: str) -> list[type]:
    """
    Importa um arquivo ``.py`` e retorna todas as classes que herdam de
    ``PluginBase`` (excluindo a própria ``PluginBase``).

    Parâmetros
    ----------
    caminho_arquivo : str
        Caminho absoluto para o arquivo Python.

    Retorna
    -------
    list[type]
        Lista de classes de plugin encontradas no arquivo.
    """
    nome_modulo = os.path.splitext(os.path.basename(caminho_arquivo))[0]
    spec = importlib.util.spec_from_file_location(nome_modulo, caminho_arquivo)
    if spec is None or spec.loader is None:
        return []

    modulo = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(modulo)  # type: ignore[union-attr]
    except Exception as erro:
        print(f"[plugins] Erro ao carregar '{caminho_arquivo}': {erro}")
        return []

    classes = []
    for _nome, obj in inspect.getmembers(modulo, inspect.isclass):
        if issubclass(obj, PluginBase) and obj is not PluginBase:
            classes.append(obj)
    return classes


def _formatar_nome_menu(nome_pasta: str) -> str:
    """Retorna o nome da pasta sem alterações para uso no submenu."""
    return nome_pasta.capitalize()


def carregar_plugins_dinamicamente(
    menu_pai: QMenu,
    diretorio: str,
    janela_principal: "JanelaPrincipal",
) -> None:
    """
    Percorre *recursivamente* ``diretorio`` e popula ``menu_pai`` com:

    * **Submenus** para cada subpasta encontrada.
    * **QActions** para cada classe de plugin encontrada nos arquivos ``.py``.

    Parâmetros
    ----------
    menu_pai : QMenu
        Menu (ou submenu) ao qual as entradas serão adicionadas.
    diretorio : str
        Caminho absoluto da pasta a ser varrida.
    janela_principal : JanelaPrincipal
        Referência à janela principal; usada nas QActions para instanciar
        e conectar os plugins.
    """
    if not os.path.isdir(diretorio):
        return

    entradas = sorted(os.listdir(diretorio))

    # --- Primeiro passamos pelas subpastas (criam submenus) ---
    for entrada in entradas:
        caminho = os.path.join(diretorio, entrada)
        if os.path.isdir(caminho) and not entrada.startswith("_"):
            submenu = QMenu(_formatar_nome_menu(entrada), menu_pai)
            
            # Executa a recursão primeiro para tentar popular o submenu
            carregar_plugins_dinamicamente(submenu, caminho, janela_principal)
            
            # Adiciona ao menu pai APENAS se alguma ação (ou submenu com ações) foi inserida
            if not submenu.isEmpty():
                menu_pai.addMenu(submenu)

    # --- Depois pelos arquivos .py (criam QActions) ---
    for entrada in entradas:
        caminho = os.path.join(diretorio, entrada)
        if (
            os.path.isfile(caminho)
            and entrada.endswith(".py")
            and not entrada.startswith("_")
        ):
            classes = _carregar_classes_do_arquivo(caminho)
            for classe_plugin in classes:
                nome_exibicao = getattr(
                    classe_plugin, "display_name", classe_plugin.__name__
                )
                acao = menu_pai.addAction(nome_exibicao)
                # Captura ``classe_plugin`` por valor via argumento padrão
                acao.triggered.connect(
                    lambda _checked=False, cls=classe_plugin: janela_principal.abrir_plugin(cls)
                )

# ---------------------------------------------------------------------------
# Classes de Estado
# ---------------------------------------------------------------------------

class DocumentoImagem(QWidget):
    """
    Representa o estado de uma única imagem aberta no programa.
    Encapsula o canvas, a matriz original e os backups para os plugins.
    """
    # Cria um sinal para repassar a alteração de zoom para a janela principal
    zoom_alterado = Signal(float)

    def __init__(self, caminho_arquivo: str, imagem_bgr: np.ndarray, parent=None):
        super().__init__(parent)
        self.caminho = caminho_arquivo
        self.imagem_atual = imagem_bgr
        self.imagem_backup = None
        self.foi_modificado = False
        self.historico = Historico(limite=10)

        # Configura o layout específico desta aba
        self.layout_interno = QVBoxLayout(self)
        self.layout_interno.setContentsMargins(0, 0, 0, 0)

        self.visualizador = VisualizadorImagem(self)
        self.layout_interno.addWidget(self.visualizador)
        
        # Conecta o sinal interno do visualizador ao sinal da aba
        self.visualizador.zoom_alterado.connect(self.zoom_alterado.emit)

        # Exibe a imagem logo na criação (ajustando à janela por padrão)
        self.atualizar_visualizacao(self.imagem_atual, ajustar_a_janela=True)

    def atualizar_visualizacao(self, imagem_bgr: np.ndarray, ajustar_a_janela: bool = False) -> None:
        """Converte a matriz OpenCV para QPixmap e delega ao componente de visualização."""
        imagem_rgb = cv2.cvtColor(imagem_bgr, cv2.COLOR_BGR2RGB)
        altura, largura, canais = imagem_rgb.shape
        bytes_por_linha = canais * largura
        
        qimage = QImage(
            imagem_rgb.data, 
            largura, 
            altura, 
            bytes_por_linha, 
            QImage.Format.Format_RGB888
        )
        pixmap = QPixmap.fromImage(qimage)

        # O visualizador customizado agora cuida do redimensionamento e da exibição
        self.visualizador.definir_pixmap(pixmap, ajustar_a_janela=ajustar_a_janela)
        if ajustar_a_janela:
            QTimer.singleShot(0, self.ajustar_imagem_a_janela)

    # ------------------------------------------------------------------
    # Delegação de métodos para o VisualizadorImagem
    # ------------------------------------------------------------------
    
    def aumentar_zoom(self):
        self.visualizador.aumentar_zoom()

    def diminuir_zoom(self):
        self.visualizador.diminuir_zoom()
        
    def ajustar_imagem_a_janela(self):
        self.visualizador.ajustar_imagem_a_janela()
        
    def resetar_zoom(self):
        self.visualizador.resetar_zoom()

    def definir_modo_arrasto(self, ativo: bool):
        self.visualizador.definir_modo_arrasto(ativo)

def _menu_tem_acao_folha(menu: QMenu) -> bool:
    """
    Retorna ``True`` quando há ao menos uma ação de plugin no menu.

    Ações que abrem submenus não contam; apenas ações "folha".
    """
    for acao in menu.actions():
        submenu = acao.menu()
        if submenu is None:
            return True
        if _menu_tem_acao_folha(submenu):
            return True
    return False

class TelaBoasVindas(QWidget):
    """Widget que exibe as opções iniciais (abrir, colar, arrastar)."""
    def __init__(self, janela_principal: "JanelaPrincipal", parent=None):
        super().__init__(parent)
        self.janela = janela_principal

        layout_placeholder = QVBoxLayout(self)
        layout_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)

        titulo = QLabel("Studio de Processamento de Imagens")
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        titulo.setStyleSheet("font-size: 22px; font-weight: bold; color: #333;")

        subtitulo = QLabel("Comece abrindo ou arrastando uma imagem")
        subtitulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitulo.setStyleSheet("font-size: 13px; color: #888;")

        btn_nova = QPushButton("Nova Imagem")
        btn_nova.setFixedSize(130, 40)

        btn_abrir = QPushButton("Abrir imagem")
        btn_abrir.setFixedSize(130, 40)
        btn_abrir.clicked.connect(self.janela.abrir_imagem)

        btn_colar = QPushButton("Colar do clipboard")
        btn_colar.setFixedSize(150, 40)
        btn_colar.clicked.connect(self.janela.colar_imagem_clipboard)

        layout_botoes = QHBoxLayout()
        layout_botoes.setSpacing(10)
        layout_botoes.addStretch()
        layout_botoes.addWidget(btn_nova)
        layout_botoes.addWidget(btn_abrir)
        layout_botoes.addWidget(btn_colar)
        layout_botoes.addStretch()

        separador = QLabel("— ou —")
        separador.setAlignment(Qt.AlignmentFlag.AlignCenter)
        separador.setStyleSheet("font-size: 12px; color: #aaa;")

        area_arrastar = AreaArrastarImagem()
        area_arrastar.arquivo_solto.connect(self.janela._carregar_imagem_do_caminho)

        layout_placeholder.addStretch()
        layout_placeholder.addWidget(titulo)
        layout_placeholder.addWidget(subtitulo)
        layout_placeholder.addSpacing(24)
        layout_placeholder.addLayout(layout_botoes)
        layout_placeholder.addSpacing(12)
        layout_placeholder.addWidget(separador)
        layout_placeholder.addSpacing(12)
        layout_placeholder.addWidget(area_arrastar, alignment=Qt.AlignmentFlag.AlignCenter)
        layout_placeholder.addStretch()


class BarraAbas(QTabBar):
    """Barra de abas que condensa largura sem estourar o espaco disponível."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDrawBase(False)
        self._largura_minima = 36
        self._largura_maxima = 320
        self._margem_condensar = 24
        self._cor_fundo = QColor("#1e1e1e")

    def tabSizeHint(self, index):
        barra_base = super(BarraAbas, self)
        tamanho = barra_base.tabSizeHint(index)
        total = self.count()
        if total <= 0 or index < 0 or index >= total:
            return tamanho

        largura_disponivel = self._largura_disponivel()
        if largura_disponivel <= 0:
            largura_disponivel = sum(
                max(self._largura_minima, barra_base.tabSizeHint(i).width())
                for i in range(total)
            )

        larguras_base = [
            min(
                self._largura_maxima,
                max(self._largura_minima, barra_base.tabSizeHint(i).width()),
            )
            for i in range(total)
        ]
        largura_total_base = sum(larguras_base)
        limite = max(0, largura_disponivel - self._margem_condensar)

        if largura_total_base <= limite:
            tamanho.setWidth(larguras_base[index])
            return tamanho

        largura_calculada = limite // total
        largura_final = max(
            self._largura_minima,
            min(larguras_base[index], self._largura_maxima, largura_calculada),
        )
        tamanho.setWidth(largura_final)
        return tamanho

    def minimumTabSizeHint(self, index):
        tamanho = super().minimumTabSizeHint(index)
        tamanho.setWidth(self._largura_minima)
        return tamanho

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.updateGeometry()
        self.update()

    def paintEvent(self, event):
        pintor = QPainter(self)
        pintor.fillRect(self.rect(), self._cor_fundo)
        pintor.end()

        super().paintEvent(event)

        if self.count() <= 0:
            return

        direita_abas = max(self.tabRect(i).right() for i in range(self.count()))
        if direita_abas + 1 >= self.width():
            return

        pintor = QPainter(self)
        area_vazia = self.rect().adjusted(direita_abas + 1, 0, 0, 0)
        pintor.fillRect(area_vazia, self._cor_fundo)
        pintor.end()

    def tabInserted(self, index):
        super().tabInserted(index)
        self.updateGeometry()

    def tabRemoved(self, index):
        super().tabRemoved(index)
        self.updateGeometry()

    def _largura_disponivel(self) -> int:
        widget_pai = self.parentWidget()
        if widget_pai is not None and widget_pai.contentsRect().width() > 0:
            return widget_pai.contentsRect().width()
        return self.width()


class AbasImagem(QTabWidget):
    """QTabWidget que mantém a faixa do cabeçalho com o fundo escuro."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cor_fundo = QColor("#1e1e1e")

    def paintEvent(self, event):
        pintor = QPainter(self)
        pintor.fillRect(self.rect(), self._cor_fundo)
        pintor.end()

        super().paintEvent(event)

        barra = self.tabBar()
        if barra is None:
            return

        geometria_barra = barra.geometry()
        esquerda = geometria_barra.right() + 1
        altura = geometria_barra.height()
        if esquerda >= self.width() or altura <= 0:
            return

        area_vazia = self.rect()
        area_vazia.setLeft(esquerda)
        area_vazia.setHeight(altura)

        pintor = QPainter(self)
        pintor.fillRect(area_vazia, self._cor_fundo)
        pintor.end()

# ---------------------------------------------------------------------------
# Janela Principal
# ---------------------------------------------------------------------------
class JanelaPrincipal(QMainWindow):
    """Janela principal do Studio de Processamento de Imagens."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Studio de Processamento de Imagens")
        self.resize(900, 650)

        self._modo_zoom_toolbar = "zoom"
        self._ferramenta_ativa_toolbar = "mover"
        self._imagem_atual: np.ndarray | None = None
        self._configuracoes = QSettings(
            "ProcessamentoDeImagens", "StudioDeProcessamentoDeImagens"
        )
        self._mostrar_aviso_fechamento = self._configuracoes.value(
            "avisos/confirmar_fechamento_arquivo", True, type=bool
        )

        self._construir_interface()
        self._construir_menus()

    # ------------------------------------------------------------------
    # Construção da interface
    # ------------------------------------------------------------------

    def _construir_interface(self) -> None:
        """Cria o layout central com toolbar lateral e área de visualização."""
        container_central = QWidget(self)
        layout_central = QHBoxLayout(container_central)
        layout_central.setContentsMargins(0, 0, 0, 0)
        layout_central.setSpacing(0)

        self._toolbar_esquerda = BarraFerramentasEsquerda(container_central)
        self._toolbar_esquerda.ferramenta_alterada.connect(self._ao_ferramenta_alterada)
        self._toolbar_esquerda.modo_zoom_alterado.connect(self._ao_modo_zoom_toolbar_alterado)
        layout_central.addWidget(self._toolbar_esquerda)

        self._stacked = QStackedWidget(container_central)
        layout_central.addWidget(self._stacked, 1)

        self._sidebar_direita = BarraLateralDireita(container_central)
        self._sidebar_direita.ajuste_solicitado.connect(self._ao_ajuste_solicitado)
        layout_central.addWidget(self._sidebar_direita)
      
        # Página 0: placeholder com botões para quando não há imagem
        self._placeholder = TelaBoasVindas(self)
        
        # Página 1: abas para múltiplas imagens
        self.tabs = AbasImagem(self)
        self.tabs.setTabBar(BarraAbas(self.tabs))
        self.tabs.setTabsClosable(False)
        self.tabs.setElideMode(Qt.TextElideMode.ElideRight)
        self.tabs.setIconSize(QSize(0, 0))
        self.tabs.setUsesScrollButtons(False)
        self.tabs.tabBar().setExpanding(False)
        self.tabs.tabBar().setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.tabs.setAutoFillBackground(False)
        self.tabs.tabBar().setAutoFillBackground(False)
        self.tabs.setStyleSheet("""
            QTabWidget { background: #1e1e1e; }
            QTabWidget::pane { border: none; background: #1e1e1e; }
            QTabWidget::tab-bar { left: 0px; background: #1e1e1e; }
            QTabWidget::left-corner, QTabWidget::right-corner { background: #1e1e1e; }
            QTabBar { alignment: left; background: #1e1e1e; }
            QTabBar::base { background: #1e1e1e; border: none; }
            QTabBar::scroller { background: #1e1e1e; }
            QTabBar::tab {
                background: #1e1e1e;
                color: #f3f4f6;
                padding: 2px 18px 2px 6px;
                height: 22px;
                min-height: 22px;
                min-width: 36px;
                border: none;
                border-radius: 0px;
                margin: 0px;
            }
            QTabBar::tab:selected {
                background: #1e1e1e;
            }
            QTabBar::tab:!selected {
                background: #1e1e1e;
                color: #d1d5db;
            }
            QToolButton#tabCloseButton {
                color: #f3f4f6;
                background: transparent;
                border: none;
                min-width: 12px;
                min-height: 12px;
                font-size: 11px;
                padding: 0px 2px;
            }
            QToolButton#tabCloseButton:hover {
                background: #2c2c2c;
            }
        """)
        
        self.tabs.currentChanged.connect(self._atualizar_zoom_ao_trocar_aba)
        # Conecta o sinal de clique no botão de fechar da aba à função de validação
        self.tabs.tabCloseRequested.connect(self._solicitar_fechamento_aba)

        # Montagem final
        self._stacked.addWidget(self._placeholder)
        self._stacked.addWidget(self.tabs)
        
        # Inicia o app mostrando a página 0
        self._stacked.setCurrentIndex(0)
        self.setCentralWidget(container_central)

        self._atualizar_visibilidade_laterais(False)
        
        # Configurações da barra de status
        self.setStatusBar(QStatusBar(self))
        self._label_zoom_status = QLabel("Zoom: 100%", self)
        self.statusBar().addPermanentWidget(self._label_zoom_status)
        self._atualizar_status_vazio()

    def _construir_menus(self) -> None:
        """Cria a barra de menus com Arquivo, Visualizar, Pixels, Imagem e Filtros (plugins)."""
        barra = self.menuBar()

        # --- Menu Arquivo ---
        menu_arquivo = barra.addMenu("Arquivo")

        acao_nova_aba = menu_arquivo.addAction("Nova aba em branco")
        acao_nova_aba.setShortcut("Ctrl+T")
        acao_nova_aba.triggered.connect(self.abrir_nova_aba)
        menu_arquivo.addSeparator()
        
        acao_abrir = menu_arquivo.addAction("Abrir imagem")
        acao_abrir.setShortcut("Ctrl+O")
        acao_abrir.triggered.connect(self.abrir_imagem)

        acao_camera = menu_arquivo.addAction("Capturar da Câmera")
        acao_camera.setShortcut("Ctrl+K")
        acao_camera.triggered.connect(self.capturar_da_camera)
        
        acao_colar = menu_arquivo.addAction("Colar do clipboard")
        acao_colar.setShortcut("Ctrl+V")
        acao_colar.triggered.connect(self.colar_imagem_clipboard)

        acao_salvar = menu_arquivo.addAction("Salvar imagem")
        acao_salvar.setShortcut("Ctrl+S")
        acao_salvar.triggered.connect(self.salvar_imagem)
        menu_arquivo.addSeparator()

        acao_sair = menu_arquivo.addAction("Sair")
        acao_sair.triggered.connect(self.close)
        
        # --- Menu Editar ---
        menu_editar = barra.addMenu("Editar")

        acao_desfazer = menu_editar.addAction("Desfazer")
        acao_desfazer.setShortcut(QKeySequence.StandardKey.Undo)
        acao_desfazer.triggered.connect(self.desfazer)
        
        # --- Menu Visualizar ---
        menu_visualizar = barra.addMenu("Visualizar")

        acao_zoom_mais = menu_visualizar.addAction("Aumentar zoom")
        acao_zoom_mais.setShortcut(QKeySequence.StandardKey.ZoomIn)
        acao_zoom_mais.triggered.connect(self._delegar_aumentar_zoom)

        acao_zoom_menos = menu_visualizar.addAction("Diminuir zoom")
        acao_zoom_menos.setShortcut(QKeySequence.StandardKey.ZoomOut)
        acao_zoom_menos.triggered.connect(self._delegar_diminuir_zoom)

        acao_ajustar = menu_visualizar.addAction("Ajustar à janela")
        acao_ajustar.setShortcut("Ctrl+9")
        acao_ajustar.triggered.connect(self._delegar_ajustar_janela)

        acao_zoom_100 = menu_visualizar.addAction("Zoom 100%")
        acao_zoom_100.setShortcut("Ctrl+0")
        acao_zoom_100.triggered.connect(self._delegar_resetar_zoom)

        # --- Menus de plugins (populados dinamicamente) ---
        # --- Menu Imagem (transformações e ajustes globais) ---
        menu_imagem = barra.addMenu("Imagem")
        diretorio_imagem = os.path.join(_DIRETORIO_RAIZ, "plugins", "imagem")
        carregar_plugins_dinamicamente(menu_imagem, diretorio_imagem, self)

        if not _menu_tem_acao_folha(menu_imagem):
            aviso = menu_imagem.addAction("(nenhum plugin encontrado)")
            aviso.setEnabled(False)

        # --- Menu Pixels (operações pontuais) ---
        menu_pixels = barra.addMenu("Pixels")
        diretorio_pixels = os.path.join(_DIRETORIO_RAIZ, "plugins", "pixels")
        carregar_plugins_dinamicamente(menu_pixels, diretorio_pixels, self)

        if not _menu_tem_acao_folha(menu_pixels):
            aviso = menu_pixels.addAction("(nenhum plugin encontrado)")
            aviso.setEnabled(False)

        # --- Menu Filtros (operações regionais) ---
        menu_filtros = barra.addMenu("Filtros")
        diretorio_filtros = os.path.join(_DIRETORIO_RAIZ, "plugins", "filtros")
        carregar_plugins_dinamicamente(menu_filtros, diretorio_filtros, self)

        if not _menu_tem_acao_folha(menu_filtros):
            aviso = menu_filtros.addAction("(nenhum plugin encontrado)")
            aviso.setEnabled(False)

        # --- Menu Detecção (pontos e características da imagem) ---
        menu_deteccao = barra.addMenu("Detecção")
        diretorio_deteccao = os.path.join(
            _DIRETORIO_RAIZ, "plugins", "deteccao"
        )
        carregar_plugins_dinamicamente(menu_deteccao, diretorio_deteccao, self)

        if not _menu_tem_acao_folha(menu_deteccao):
            aviso = menu_deteccao.addAction("(nenhum plugin encontrado)")
            aviso.setEnabled(False)

        # --- Menu Reconhecimento (leitura e identificação de padrões) ---
        menu_reconhecimento = barra.addMenu("Reconhecimento")
        diretorio_reconhecimento = os.path.join(
            _DIRETORIO_RAIZ, "plugins", "reconhecimento"
        )
        carregar_plugins_dinamicamente(
            menu_reconhecimento, diretorio_reconhecimento, self
        )

        if not _menu_tem_acao_folha(menu_reconhecimento):
            aviso = menu_reconhecimento.addAction("(nenhum plugin encontrado)")
            aviso.setEnabled(False)

    # ------------------------------------------------------------------
    # Slots públicos
    # ------------------------------------------------------------------

    def abrir_imagem(self) -> None:
        """Abre a imagem, cria um novo DocumentoImagem e adiciona como aba."""
        caminhos, _ = QFileDialog.getOpenFileNames(
            self,
            "Abrir Imagem",
            "",
            "Imagens (*.png *.jpg *.jpeg *.bmp *.tiff *.tif)",
        )

        if not caminhos:
            return

        # Para cada caminho selecionado, usamos a função unificada de carregamento
        for caminho in caminhos:
            self._carregar_imagem_do_caminho(caminho)

    def _normalizar_caminho_imagem(self, caminho: str) -> str:
        return os.path.normcase(os.path.abspath(caminho))

    def _indice_aba_por_caminho(self, caminho: str) -> int:
        caminho_normalizado = self._normalizar_caminho_imagem(caminho)
        for indice in range(self.tabs.count()):
            aba = self.tabs.widget(indice)
            if not isinstance(aba, DocumentoImagem):
                continue
            if self._normalizar_caminho_imagem(aba.caminho) == caminho_normalizado:
                return indice
        return -1

    def _adicionar_documento_imagem(
        self,
        caminho: str,
        imagem_bgr: np.ndarray,
        nome_aba: str | None = None,
        tooltip: str | None = None,
        modificado: bool = False,
        mensagem_status: str | None = None,
    ) -> DocumentoImagem:
        """Cria uma aba editável para uma imagem já carregada em memória."""
        self._imagem_atual = imagem_bgr
        novo_documento = DocumentoImagem(caminho, imagem_bgr)
        novo_documento.zoom_alterado.connect(self._ao_zoom_alterado)

        titulo_aba = nome_aba or os.path.basename(caminho) or "Imagem"
        aba_atual = self.tabs.currentWidget()
        if isinstance(aba_atual, TelaBoasVindas):
            indice_insercao = self.tabs.currentIndex()
            self.tabs.removeTab(indice_insercao)
            aba_atual.deleteLater()
            self.tabs.insertTab(indice_insercao, novo_documento, titulo_aba)
        else:
            indice_insercao = self.tabs.addTab(novo_documento, titulo_aba)

        self.tabs.setTabToolTip(indice_insercao, tooltip or titulo_aba)
        self._adicionar_botao_fechar_aba(indice_insercao, novo_documento)
        self.tabs.setCurrentIndex(indice_insercao)

        self._ao_ferramenta_alterada(self._ferramenta_ativa_toolbar)
        self._stacked.setCurrentIndex(1)
        self._atualizar_visibilidade_laterais(True)

        if modificado:
            self._marcar_como_modificado(novo_documento, True)

        if mensagem_status:
            self.statusBar().showMessage(mensagem_status)

        return novo_documento

    def _carregar_imagem_do_caminho(self, caminho: str) -> None:
        """Carrega uma imagem a partir do caminho informado e adiciona como uma nova aba."""
        indice_existente = self._indice_aba_por_caminho(caminho)
        if indice_existente != -1:
            self.tabs.setCurrentIndex(indice_existente)
            self._stacked.setCurrentIndex(1)
            self._atualizar_visibilidade_laterais(True)

            aba_existente = self.tabs.widget(indice_existente)
            if isinstance(aba_existente, DocumentoImagem):
                self._imagem_atual = aba_existente.imagem_atual

            self._ao_ferramenta_alterada(self._ferramenta_ativa_toolbar)
            self.statusBar().showMessage(
                f"Imagem ja aberta: {os.path.basename(caminho)}"
            )
            return

        imagem_bgr = cv2.imread(caminho)
        if imagem_bgr is None:
            QMessageBox.critical(self, "Erro", f"Não foi possível abrir:\n{caminho}")
            return

        # Extrai apenas o nome do arquivo para exibir na aba
        nome_arquivo = os.path.basename(caminho)
        self._adicionar_documento_imagem(
            caminho,
            imagem_bgr,
            nome_aba=nome_arquivo,
            tooltip=nome_arquivo,
            mensagem_status=f"Imagem carregada: {nome_arquivo}",
        )

    def abrir_nova_aba(self) -> None:
        """Abre uma nova aba em branco contendo as opções iniciais."""
        nova_aba = TelaBoasVindas(self)
        indice = self.tabs.addTab(nova_aba, "Nova Aba")
        self._adicionar_botao_fechar_aba(indice, nova_aba)
        self.tabs.setCurrentIndex(indice)
        self._stacked.setCurrentIndex(1)
        self.statusBar().showMessage("Nova aba em branco aberta.")

    def _solicitar_fechamento_aba(self, indice: int) -> None:
        """Dispara o alerta de fechamento. Se o usuário confirmar, fecha a aba."""
        if indice < 0:
            return
            
        aba = self.tabs.widget(indice)

        # Se for uma aba em branco, fecha direto sem perguntar
        if isinstance(aba, TelaBoasVindas):
            self.tabs.removeTab(indice)
            aba.deleteLater()
            
            # Se não houver mais abas abertas, volta para a tela inicial (Página 0)
            if self.tabs.count() == 0:
                self._stacked.setCurrentIndex(0)
                self._atualizar_visibilidade_laterais(False)
                self._atualizar_status_vazio()
            return

        if not isinstance(aba, DocumentoImagem):
            return

        nome_arquivo = os.path.basename(aba.caminho)

        if not aba.foi_modificado:
            self._fechar_aba_confirmada(indice, aba, nome_arquivo)
            return

        if not self._mostrar_aviso_fechamento:
            self._fechar_aba_confirmada(indice, aba, nome_arquivo)
            return

        # Cria a instância do QMessageBox
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Aviso de Fechamento")
        msg_box.setText(
            f"Deseja realmente fechar o arquivo '{nome_arquivo}'?\n\n"
            "Qualquer modificação não salva será perdida."
        )
        msg_box.setIcon(QMessageBox.Icon.Warning)

        # Adiciona botões com textos personalizados
        btn_fechar = msg_box.addButton(
            "Sim, fechar arquivo", QMessageBox.ButtonRole.AcceptRole
        )
        btn_cancelar = msg_box.addButton(
            "Não, manter aberto", QMessageBox.ButtonRole.RejectRole
        )
        msg_box.setDefaultButton(btn_cancelar)
        checkbox_nao_mostrar = QCheckBox("Não mostrar este aviso novamente", msg_box)
        msg_box.setCheckBox(checkbox_nao_mostrar)

        # Exibe a janela de validação
        msg_box.exec()

        # Verifica a resposta do usuário
        if msg_box.clickedButton() == btn_fechar:
            if checkbox_nao_mostrar.isChecked():
                self._mostrar_aviso_fechamento = False
                self._configuracoes.setValue(
                    "avisos/confirmar_fechamento_arquivo", False
                )
            self._fechar_aba_confirmada(indice, aba, nome_arquivo)

    def _fechar_aba_confirmada(
        self, indice: int, aba: QWidget, nome_arquivo: str
    ) -> None:
        self.tabs.removeTab(indice)
        aba.deleteLater()  # Libera memória da imagem
        self.statusBar().showMessage(f"Arquivo '{nome_arquivo}' fechado.")

        # Se não houver mais abas abertas, volta para a tela inicial (Página 0)
        if self.tabs.count() == 0:
            self._stacked.setCurrentIndex(0)
            self._atualizar_visibilidade_laterais(False)
            self._atualizar_status_vazio()

    def _adicionar_botao_fechar_aba(self, indice: int, widget: QWidget) -> None:
        botao = QToolButton(self.tabs)
        botao.setObjectName("tabCloseButton")
        botao.setText("x")
        botao.setFixedSize(14, 14)
        botao.setCursor(Qt.CursorShape.PointingHandCursor)
        botao.setAutoRaise(True)
        botao.clicked.connect(
            lambda _checked=False, alvo=widget: self._fechar_aba_por_widget(alvo)
        )
        self.tabs.tabBar().setTabButton(indice, QTabBar.ButtonPosition.RightSide, botao)
        self.tabs.tabBar().updateGeometry()

    def _fechar_aba_por_widget(self, widget: QWidget) -> None:
        indice = self.tabs.indexOf(widget)
        if indice != -1:
            self._solicitar_fechamento_aba(indice)
            return

    def _marcar_como_modificado(self, aba: DocumentoImagem, modificado: bool) -> None:
        """Atualiza o estado de modificação da aba e a interface visual."""
        aba.foi_modificado = modificado
        indice = self.tabs.indexOf(aba)
        if indice == -1:
            return

        nome_arquivo = os.path.basename(aba.caminho)

        if modificado:
            # Adiciona o asterisco na aba e avisa no tooltip
            self.tabs.setTabText(indice, f"* {nome_arquivo}")
            self.tabs.setTabToolTip(indice, f"{nome_arquivo} (Não salvo)")
        else:
            # Remove o asterisco e volta o tooltip ao normal
            self.tabs.setTabText(indice, nome_arquivo)
            self.tabs.setTabToolTip(indice, nome_arquivo)
        self.tabs.tabBar().updateGeometry()

    def _extensao_por_filtro_salvamento(self, filtro: str) -> str:
        if "JPG" in filtro or "JPEG" in filtro:
            return ".jpg"
        if "BMP" in filtro:
            return ".bmp"
        return _EXTENSAO_PADRAO_SALVAMENTO

    def _normalizar_caminho_salvamento(
        self, caminho: str, filtro_selecionado: str
    ) -> str | None:
        _raiz, extensao = os.path.splitext(caminho)
        if not extensao:
            return caminho + self._extensao_por_filtro_salvamento(filtro_selecionado)

        if extensao.lower() not in _EXTENSOES_SALVAMENTO:
            formatos = ", ".join(sorted(_EXTENSOES_SALVAMENTO))
            QMessageBox.warning(
                self,
                "Formato não suportado",
                f"Use uma das extensões suportadas: {formatos}.",
            )
            return None

        return caminho
    
    def salvar_imagem(self) -> None:
        """Salva a imagem da aba atual em arquivo."""
        aba_atual = self.tabs.currentWidget()
        if not isinstance(aba_atual, DocumentoImagem):
            QMessageBox.information(self, "Aviso", "Nenhuma imagem para salvar.")
            return

        caminho, filtro_selecionado = QFileDialog.getSaveFileName(
            self,
            "Salvar imagem",
            aba_atual.caminho,
            "PNG (*.png);;JPG (*.jpg);;BMP (*.bmp)"
        )

        if not caminho:
            return

        caminho_normalizado = self._normalizar_caminho_salvamento(
            caminho, filtro_selecionado
        )
        if caminho_normalizado is None:
            return

        try:
            sucesso = cv2.imwrite(caminho_normalizado, aba_atual.imagem_atual)
        except cv2.error as erro:
            QMessageBox.critical(
                self,
                "Erro",
                "Não foi possível salvar a imagem.\n\n"
                f"Detalhes: {erro}",
            )
            return

        if sucesso:
            aba_atual.caminho = caminho_normalizado
            self.statusBar().showMessage(f"Imagem salva em: {caminho_normalizado}")
            self._marcar_como_modificado(aba_atual, False)
        else:
            QMessageBox.critical(self, "Erro", "Falha ao salvar a imagem.")
    
    def _atualizar_status_vazio(self):
        """Atualiza a barra de status quando não há imagens abertas."""
        self.statusBar().showMessage("Pronto. Abra uma imagem no menu Arquivo.")

    def colar_imagem_clipboard(self) -> None:
        """Carrega uma imagem a partir do clipboard do sistema e adiciona como nova aba."""
        clipboard = QApplication.clipboard()
        qimage = clipboard.image()

        if qimage.isNull():
            QMessageBox.information(
                self, "Aviso", "Não há imagem no clipboard."
            )
            return

        # Converte a imagem do clipboard para o formato do OpenCV (BGR)
        qimage = qimage.convertToFormat(QImage.Format.Format_RGB888)
        largura = qimage.width()
        altura = qimage.height()
        bytes_por_linha = qimage.bytesPerLine()
        ptr = qimage.bits()

        arr_rgb = np.array(ptr).reshape((altura, bytes_por_linha))[:, :largura * 3]
        arr_rgb = arr_rgb.reshape((altura, largura, 3))
        imagem_bgr = cv2.cvtColor(arr_rgb, cv2.COLOR_RGB2BGR)

        contador = self.tabs.count() + 1
        nome_arquivo = f"Clipboard_{contador}"
        caminho_ficticio = f"/{nome_arquivo}"
        self._adicionar_documento_imagem(
            caminho_ficticio,
            imagem_bgr,
            nome_aba=nome_arquivo,
            tooltip="Imagem colada (Não salva)",
            modificado=True,
            mensagem_status="Imagem colada do clipboard.",
        )

    # ------------------------------------------------------------------
    # Integração com Plugins
    # ------------------------------------------------------------------
    def abrir_plugin(self, classe_plugin: type) -> None:
        """
        Instancia e exibe o diálogo do plugin para a imagem atual, conectando seus sinais.

        Parâmetros
        ----------
        classe_plugin : type
            Classe do plugin a ser instanciado (subclasse de ``PluginBase``).
        """
        aba_atual = self.tabs.currentWidget()
        if not isinstance(aba_atual, DocumentoImagem):
            QMessageBox.information(
                self, "Aviso", "Abra uma imagem antes de aplicar um filtro."
            )
            return

        # Converte BGR → RGB antes de enviar ao plugin
        imagem_rgb = cv2.cvtColor(aba_atual.imagem_atual, cv2.COLOR_BGR2RGB)
        aba_atual.imagem_backup = aba_atual.imagem_atual.copy()

        dialogo = classe_plugin(imagem_rgb, self)
        dialogo.preview_requested.connect(lambda rgb: self._ao_receber_preview(rgb, aba_atual))
        dialogo.apply_requested.connect(lambda rgb: self._ao_aplicar_plugin(rgb, aba_atual))

        # Se o usuário fechar sem aplicar, restaura a imagem original
        dialogo.finished.connect(lambda codigo: self._ao_fechar_plugin(codigo, aba_atual))

        dialogo.exec()

    def capturar_da_camera(self) -> None:
        """Abre a janela de preview e captura a imagem ao confirmar."""
        dialogo = DialogoCamera(self)
        try:
            # Se o usuário clicar em "Tirar Foto" (accept)
            if dialogo.exec() == QDialog.DialogCode.Accepted:
                frame = dialogo.get_frame()
                if frame is None:
                    QMessageBox.warning(
                        self,
                        "Captura da câmera",
                        "Nenhum frame foi capturado pela câmera.",
                    )
                    return

                contador = self.tabs.count() + 1
                nome_arquivo = f"Captura_Camera_{contador}"
                caminho_ficticio = f"/{nome_arquivo}.png"
                self._adicionar_documento_imagem(
                    caminho_ficticio,
                    frame,
                    nome_aba=nome_arquivo,
                    tooltip="Imagem capturada da câmera (Não salva)",
                    modificado=True,
                    mensagem_status="Imagem capturada via Live Preview.",
                )
        finally:
            dialogo.liberar_camera()

    # ------------------------------------------------------------------
    # Slots privados
    # ------------------------------------------------------------------

    def _ao_fechar_plugin(self, codigo: int, aba: DocumentoImagem) -> None:
        """Restaura o backup se o diálogo foi fechado sem confirmar."""
        from PySide6.QtWidgets import QDialog
        if codigo != QDialog.DialogCode.Accepted and aba.imagem_backup is not None:
            aba.imagem_atual = aba.imagem_backup
            aba.atualizar_visualizacao(aba.imagem_atual)
            aba.imagem_backup = None

    def _ao_receber_preview(self, imagem_rgb: np.ndarray, aba: DocumentoImagem) -> None:
        """Exibe a pré-visualização sem alterar a imagem de trabalho."""
        imagem_bgr = cv2.cvtColor(imagem_rgb, cv2.COLOR_RGB2BGR)
        aba.atualizar_visualizacao(imagem_bgr)


    def _ao_aplicar_plugin(self, imagem_rgb: np.ndarray, aba: DocumentoImagem) -> None:
        """
        Substitui a imagem da aba pela imagem processada,
        salvando o estado anterior no histórico.
        """
        # Salva estado atual antes da alteração
        if aba.imagem_atual is not None:
            aba.historico.salvar(aba.imagem_atual.copy())

        imagem_bgr = cv2.cvtColor(imagem_rgb, cv2.COLOR_RGB2BGR)

        aba.imagem_atual = imagem_bgr
        aba.imagem_backup = None

        # Atualiza visualização
        aba.atualizar_visualizacao(imagem_bgr)

        # Atualiza miniatura da aba
        indice_aba = self.tabs.indexOf(aba)
        if indice_aba != -1:
            self.tabs.setTabIcon(
                indice_aba,
                self._gerar_icone_miniatura(imagem_bgr)
            )

        self._marcar_como_modificado(aba, True)

        self.statusBar().showMessage("Filtro aplicado com sucesso.")

    def desfazer(self) -> None:
        """Desfaz a última operação aplicada."""
        aba_atual = self.tabs.currentWidget()

        if not isinstance(aba_atual, DocumentoImagem):
            return

        estado = aba_atual.historico.desfazer()

        if estado is None:
            self.statusBar().showMessage("Nada para desfazer.")
            return

        aba_atual.imagem_atual = estado
        aba_atual.atualizar_visualizacao(estado)

        # Atualiza miniatura da aba
        indice_aba = self.tabs.indexOf(aba_atual)
        if indice_aba != -1:
            self.tabs.setTabIcon(
                indice_aba,
                self._gerar_icone_miniatura(estado)
            )

        self.statusBar().showMessage("Desfazer realizado.")

    def _restaurar_backup(self) -> None:
        """Restaura a imagem da aba atual ao estado anterior."""
        aba_atual = self.tabs.currentWidget()
        if isinstance(aba_atual, DocumentoImagem) and aba_atual.imagem_backup is not None:
            aba_atual.imagem_atual = aba_atual.imagem_backup
            aba_atual.atualizar_visualizacao(aba_atual.imagem_atual)
            aba_atual.imagem_backup = None

    def _ao_zoom_alterado(self, zoom: float) -> None:
        """Atualiza o indicador permanente com o nível de zoom atual."""
        nivel_zoom = round(zoom * 100)
        self._label_zoom_status.setText(f"Zoom: {nivel_zoom:.0f}%")

    def _ao_ferramenta_alterada(self, ferramenta: str) -> None:
        """Aplica o comportamento da ferramenta selecionada na toolbar."""
        self._ferramenta_ativa_toolbar = ferramenta

        aba_atual = self.tabs.currentWidget() if hasattr(self, "tabs") else None
        visualizador = getattr(aba_atual, "visualizador", None) if aba_atual else None

        if ferramenta == "mover":
            if visualizador is None:
                return
            visualizador.definir_ferramenta_mao(True)
            visualizador.definir_ferramenta_zoom(None)
            return

        if ferramenta == "zoom":
            if visualizador is None:
                return
            visualizador.definir_ferramenta_mao(False)
            visualizador.definir_ferramenta_zoom(self._modo_zoom_toolbar)
            return

        if ferramenta == "rotação":
            # Abre o diálogo de rotação e espelhamento
            if not isinstance(aba_atual, DocumentoImagem):
                return
            self._abrir_plugin_rotacao_espelhamento()
            # Volta para a ferramenta de mover após fechar o diálogo.
            # A sincronização ocorre por um único caminho (selecionar_ferramenta_por_nome)
            # para evitar que o slot de alteração da ferramenta execute em duplicidade.
            self._ferramenta_ativa_toolbar = "mover"
            self._toolbar_esquerda.selecionar_ferramenta_por_nome("mover")
            return

        if visualizador is None:
            return
        visualizador.definir_ferramenta_mao(False)
        visualizador.definir_ferramenta_zoom(None)

    def _ao_modo_zoom_toolbar_alterado(self, modo_zoom: str) -> None:
        """Atualiza o modo de zoom selecionado no submenu do botão de zoom."""
        self._modo_zoom_toolbar = modo_zoom
        if self._ferramenta_ativa_toolbar != "zoom":
            return

        aba_atual = self.tabs.currentWidget()
        visualizador = getattr(aba_atual, "visualizador", None) if aba_atual else None
        if visualizador is not None:
            visualizador.definir_ferramenta_zoom(modo_zoom)

    def _ao_ajuste_solicitado(self, ajuste: str) -> None:
        """Abre o plugin correspondente ao ajuste clicado na barra lateral direita."""
        try:
            if ajuste == "brilho_contraste":
                from plugins.pixels.filtro_brilho_contraste import FiltroBrilhoContraste

                classe_plugin: type[PluginBase] = FiltroBrilhoContraste
            elif ajuste == "preto_branco":
                from plugins.pixels.filtro_escala_de_cinza import FiltroEscalaDeCinza

                classe_plugin = FiltroEscalaDeCinza
            elif ajuste == "saturacao":
                from plugins.pixels.filtro_saturacao import FiltroSaturacao

                classe_plugin = FiltroSaturacao
            elif ajuste == "ruido_salt_pepper":
                from plugins.pixels.salt_pepper_noise import SaltPepperNoise

                classe_plugin = SaltPepperNoise
            else:
                return
        except Exception as erro:
            QMessageBox.critical(
                self,
                "Erro",
                "Falha ao carregar o ajuste selecionado.\n\n"
                f"Ajuste: {ajuste}\n"
                f"Detalhes: {erro}",
            )
            return

        self.abrir_plugin(classe_plugin)

    def _abrir_plugin_rotacao_espelhamento(self) -> None:
        """Abre o diálogo de rotação e espelhamento."""
        try:
            from plugins.imagem.transformar.transformacoes_geometricas import (
                TransformacoesGeometricas,
            )
        except Exception as erro:
            QMessageBox.critical(
                self,
                "Erro",
                "Falha ao carregar o plugin de rotação/espelhamento.\n\n"
                f"Detalhes: {erro}",
            )
            return

        self.abrir_plugin(TransformacoesGeometricas)

    def _atualizar_visibilidade_laterais(self, imagem_ativa: bool) -> None:
        """Mostra ou oculta as barras laterais conforme a tela ativa."""
        self._toolbar_esquerda.setVisible(imagem_ativa)
        self._sidebar_direita.setVisible(imagem_ativa)
    def _atualizar_zoom_ao_trocar_aba(self, indice: int):
        """Ao trocar de aba, busca o zoom da aba atual e atualiza a barra de status."""
        if indice == -1: # Nenhuma aba aberta (fechou tudo)
            self._imagem_atual = None
            self._ao_zoom_alterado(1.0)
            return

        aba_atual = self.tabs.widget(indice)
        if isinstance(aba_atual, DocumentoImagem):
            self._imagem_atual = aba_atual.imagem_atual
            self._atualizar_visibilidade_laterais(True)
            zoom_atual = aba_atual.visualizador._zoom
            self._ao_zoom_alterado(zoom_atual)
            if self._ferramenta_ativa_toolbar in {"mover", "zoom"}:
                self._ao_ferramenta_alterada(self._ferramenta_ativa_toolbar)
            return

        self._imagem_atual = None
        self._atualizar_visibilidade_laterais(False)
        self._ao_zoom_alterado(1.0)

    def keyPressEvent(self, evento) -> None:
        """Atalhos globais."""
    
        if evento.matches(QKeySequence.StandardKey.Undo):
            self.desfazer()
            return

        if evento.key() == Qt.Key.Key_Space and not evento.isAutoRepeat():
            aba_atual = self.tabs.currentWidget()

            if aba_atual and hasattr(aba_atual, 'definir_modo_arrasto'):
                aba_atual.definir_modo_arrasto(True)

            evento.accept()
            return

        super().keyPressEvent(evento)


    def keyReleaseEvent(self, evento) -> None:
        """Encerra o modo de arrasto."""
    
        if evento.key() == Qt.Key.Key_Space and not evento.isAutoRepeat():
            aba_atual = self.tabs.currentWidget()

            if aba_atual and hasattr(aba_atual, 'definir_modo_arrasto'):
                aba_atual.definir_modo_arrasto(False)

            evento.accept()
            return

        super().keyReleaseEvent(evento)

    # ------------------------------------------------------------------
    # Utilitários de exibição
    # ------------------------------------------------------------------

    def _gerar_icone_miniatura(self, imagem_bgr: np.ndarray) -> QIcon:
        if imagem_bgr is None or imagem_bgr.size == 0:
            return QIcon()

        try:
            imagem_rgb = cv2.cvtColor(imagem_bgr, cv2.COLOR_BGR2RGB)
            altura, largura, canais = imagem_rgb.shape
            bytes_por_linha = canais * largura
            qimage = QImage(
                imagem_rgb.data,
                largura,
                altura,
                bytes_por_linha,
                QImage.Format.Format_RGB888,
            ).copy()
            pixmap = QPixmap.fromImage(qimage).scaled(
                32,
                32,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            return QIcon(pixmap)
        except (cv2.error, ValueError):
            return QIcon()

    def _exibir_imagem(self, imagem_bgr: np.ndarray, ajustar_a_janela: bool = False) -> None:
        """
        Delega a exibição da imagem à aba atual.
        Mantido para retrocompatibilidade com funções da branch main.
        """
        aba_atual = self.tabs.currentWidget()
        if aba_atual and hasattr(aba_atual, "atualizar_visualizacao"):
            aba_atual.atualizar_visualizacao(imagem_bgr, ajustar_a_janela=ajustar_a_janela)
            
    # ------------------------------------------------------------------
    # Delegação de Zoom para as abas
    # ------------------------------------------------------------------

    def _delegar_aumentar_zoom(self):
        aba = self.tabs.currentWidget()
        if aba and hasattr(aba, 'aumentar_zoom'):
            aba.aumentar_zoom()

    def _delegar_diminuir_zoom(self):
        aba = self.tabs.currentWidget()
        if aba and hasattr(aba, 'diminuir_zoom'):
            aba.diminuir_zoom()

    def _delegar_ajustar_janela(self):
        aba = self.tabs.currentWidget()
        if aba and hasattr(aba, 'ajustar_imagem_a_janela'):
            aba.ajustar_imagem_a_janela()

    def _delegar_resetar_zoom(self):
        aba = self.tabs.currentWidget()
        if aba and hasattr(aba, 'resetar_zoom'):
            aba.resetar_zoom()

# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------

def main() -> None:
    """Inicializa e executa a aplicação."""
    _instalar_filtro_mensagens_qt()
    app = QApplication(sys.argv)
    app.setApplicationName("Studio de Processamento de Imagens")
    janela = JanelaPrincipal()
    janela.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
