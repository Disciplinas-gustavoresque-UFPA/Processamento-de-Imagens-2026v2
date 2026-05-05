"""
app.py
------
Janela Principal do Studio de Processamento de Imagens.

Funcionalidades
---------------
* Abrir e fechar imagens (PNG, JPG, BMP, TIFF).
* Suporte a abertura a múltiplas imagens via abas
* Barra superior com abas exibindo miniaturas das imagens.
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
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QImage, QKeySequence, QPixmap, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QTabWidget,
    QWidget,
    QVBoxLayout,
)

# Garante que o diretório raiz do projeto esteja no sys.path para que os
# plugins possam importar ``core.plugin_base`` sem ajustes manuais.
_DIRETORIO_RAIZ = os.path.dirname(os.path.abspath(__file__))
if _DIRETORIO_RAIZ not in sys.path:
    sys.path.insert(0, _DIRETORIO_RAIZ)

from core.plugin_base import PluginBase  # noqa: E402  (importação após sys.path)
from components.zoom import VisualizadorImagem  # noqa: E402


# ---------------------------------------------------------------------------
# Widget de arrastar e soltar (drag-and-drop)
# ---------------------------------------------------------------------------

_EXTENSOES_IMAGEM = (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif")


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
    return nome_pasta


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
            menu_pai.addMenu(submenu)
            carregar_plugins_dinamicamente(submenu, caminho, janela_principal)

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
    def __init__(self, caminho_arquivo: str, imagem_bgr: np.ndarray, parent=None):
        super().__init__(parent)
        self.caminho = caminho_arquivo
        self.imagem_atual = imagem_bgr
        self.imagem_backup = None
        self.foi_modificado = False

        # Configura o layout específico desta aba
        self.layout_interno = QVBoxLayout(self)
        self.layout_interno.setContentsMargins(0, 0, 0, 0)

        # Label onde a imagem será exibida
        self.label_imagem = QLabel()
        self.label_imagem.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_imagem.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.label_imagem.setScaledContents(False)

        # ScrollArea para permitir rolar imagens muito grandes
        self.area_rolagem = QScrollArea()
        self.area_rolagem.setWidget(self.label_imagem)
        self.area_rolagem.setWidgetResizable(True)
        self.area_rolagem.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.layout_interno.addWidget(self.area_rolagem)
        
        self.atualizar_visualizacao(self.imagem_atual)

    def atualizar_visualizacao(self, imagem_bgr: np.ndarray) -> None:
        """Converte a matriz OpenCV e desenha no QLabel do documento."""
        imagem_rgb = cv2.cvtColor(imagem_bgr, cv2.COLOR_BGR2RGB)
        altura, largura, canais = imagem_rgb.shape
        bytes_por_linha = canais * largura
        qimage = QImage(imagem_rgb.data, largura, altura, bytes_por_linha, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qimage)

        # Ajusta ao tamanho do viewport da ScrollArea
        tamanho_disponivel = self.area_rolagem.viewport().size()
        pixmap_escalado = pixmap.scaled(
            tamanho_disponivel,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.label_imagem.setPixmap(pixmap_escalado)
        
    def resizeEvent(self, event):
        """Garante que a imagem seja redimensionada se a janela mudar de tamanho."""
        super().resizeEvent(event)
        self.atualizar_visualizacao(self.imagem_atual)

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


# ---------------------------------------------------------------------------
# Janela Principal
# ---------------------------------------------------------------------------
class JanelaPrincipal(QMainWindow):
    """Janela principal do Studio de Processamento de Imagens."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Studio de Processamento de Imagens")
        self.resize(900, 650)

        self._construir_interface()
        self._construir_menus()

    # ------------------------------------------------------------------
    # Construção da interface
    # ------------------------------------------------------------------

    def _construir_interface(self) -> None:
        """Cria o widget central (área de visualização da imagem)."""
        self._stacked = QStackedWidget(self)
      
        # Página 0: placeholder com botões para quando não há imagem
        self._placeholder = QWidget(self)
        layout_placeholder = QVBoxLayout(self._placeholder)
        layout_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Título
        titulo = QLabel("Studio de Processamento de Imagens")
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        titulo.setStyleSheet("font-size: 22px; font-weight: bold; color: #333;")
        
        subtitulo = QLabel("Comece abrindo ou arrastando uma imagem")
        subtitulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitulo.setStyleSheet("font-size: 13px; color: #888;")
        
        # Botões em linha
        btn_nova = QPushButton("Nova Imagem")
        btn_nova.setFixedSize(130, 40)
        
        btn_abrir = QPushButton("Abrir imagem…")
        btn_abrir.setFixedSize(130, 40)
        btn_abrir.clicked.connect(self.abrir_imagem)
        
        btn_colar = QPushButton("Colar do clipboard")
        btn_colar.setFixedSize(150, 40)
        btn_colar.clicked.connect(self.colar_imagem_clipboard)
        
        layout_botoes = QHBoxLayout()
        layout_botoes.setSpacing(10)
        layout_botoes.addStretch()
        layout_botoes.addWidget(btn_nova)
        layout_botoes.addWidget(btn_abrir)
        layout_botoes.addWidget(btn_colar)
        layout_botoes.addStretch()
        
        # Separador "ou"
        separador = QLabel("— ou —")
        separador.setAlignment(Qt.AlignmentFlag.AlignCenter)
        separador.setStyleSheet("font-size: 12px; color: #aaa;")
        
        # Área de arrastar
        area_arrastar = AreaArrastarImagem()
        area_arrastar.arquivo_solto.connect(self._carregar_imagem_do_caminho)
        
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
        
        # Página 1: abas para múltiplas imagens
        self.tabs = QTabWidget(self)
        self.tabs.setTabsClosable(True) # Habilita o botão (X) em cada aba
        self.tabs.setElideMode(Qt.TextElideMode.ElideRight)
        
        # Estilo para deixar as abas maiores (para caber a miniatura)
        self.tabs.setIconSize(QSize(30, 30))
        self.tabs.setStyleSheet("""
            QTabBar { alignment: left; }
            QTabBar::tab { height: 40px; max-width: 120px; padding: 5px 10px; }
            QTabWidget::pane { border-top: 2px solid #C2C7CB; }
            QTabBar::close-button { subcontrol-position: right; subcontrol-origin: padding; margin-top: 2px; margin-right: 2px; }
        """)
        
        # Conecta o sinal de clique no botão de fechar da aba à função de validação
        self.tabs.tabCloseRequested.connect(self._solicitar_fechamento_aba)
        
        # Montagem final
        self._stacked.addWidget(self._placeholder)
        self._stacked.addWidget(self.tabs)
        
        # Inicia o app mostrando a página 0
        self._stacked.setCurrentIndex(0)
        self.setCentralWidget(self._stacked)
        
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
        acao_abrir = menu_arquivo.addAction("Abrir imagem…")
        acao_abrir.triggered.connect(self.abrir_imagem)

        acao_colar = menu_arquivo.addAction("Colar do clipboard")
        acao_colar.triggered.connect(self.colar_imagem_clipboard)

        acao_salvar = menu_arquivo.addAction("Salvar imagem…")
        acao_salvar.triggered.connect(self.salvar_imagem)
        menu_arquivo.addSeparator()
        acao_sair = menu_arquivo.addAction("Sair")
        acao_sair.triggered.connect(self.close)

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

    # ------------------------------------------------------------------
    # Slots públicos
    # ------------------------------------------------------------------

    def abrir_imagem(self) -> None:
        """Abre a imagem, cria um novo DocumentoImagem e adiciona como aba com miniatura."""
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

    def _carregar_imagem_do_caminho(self, caminho: str) -> None:
        """Carrega uma imagem a partir do caminho informado e adiciona como uma nova aba."""
        imagem_bgr = cv2.imread(caminho)
        if imagem_bgr is None:
            QMessageBox.critical(self, "Erro", f"Não foi possível abrir:\n{caminho}")
            return

        # Instancia o documento com a imagem carregada
        novo_documento = DocumentoImagem(caminho, imagem_bgr)
        
        # Gera a miniatura (Icon) para a aba
        miniatura_icon = self._gerar_icone_miniatura(imagem_bgr)
        
        # Extrai apenas o nome do arquivo para exibir na aba
        nome_arquivo = os.path.basename(caminho)
        
        # Adiciona a aba com a miniatura e o nome
        indice = self.tabs.addTab(novo_documento, miniatura_icon, nome_arquivo)
        self.tabs.setTabToolTip(indice, nome_arquivo)
        self.tabs.setCurrentIndex(indice)

        # Alterna o QStackedWidget para mostrar a página de abas (Página 1)
        self._stacked.setCurrentIndex(1)

        self.statusBar().showMessage(f"Imagem carregada: {nome_arquivo}")

    def _gerar_icone_miniatura(self, imagem_bgr: np.ndarray) -> QIcon:
        """Converte uma imagem OpenCV para QIcon para usar na aba."""
        imagem_rgb = cv2.cvtColor(imagem_bgr, cv2.COLOR_BGR2RGB)
        altura, largura, canais = imagem_rgb.shape
        qimage = QImage(imagem_rgb.data, largura, altura, canais * largura, QImage.Format.Format_RGB888)
        
        # Cria um pixmap quadrado e escala a imagem para caber
        pixmap = QPixmap(30, 30)
        pixmap.fill(Qt.GlobalColor.transparent)
        pixmap_imagem = QPixmap.fromImage(qimage).scaled(
            30, 30, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        
        # Desenha a miniatura centralizada no ícone
        import PySide6.QtGui as QtGui
        painter = QtGui.QPainter(pixmap)
        x = (30 - pixmap_imagem.width()) // 2
        y = (30 - pixmap_imagem.height()) // 2
        painter.drawPixmap(x, y, pixmap_imagem)
        painter.end()
        
        return QIcon(pixmap)

    def _solicitar_fechamento_aba(self, indice: int) -> None:
        """Dispara o alerta de fechamento. Se o usuário confirmar, fecha a aba."""
        if indice < 0:
            return
            
        aba = self.tabs.widget(indice)
        nome_arquivo = os.path.basename(aba.caminho)

        # Cria a instância do QMessageBox
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Aviso de Fechamento")
        msg_box.setText(f"Deseja realmente fechar o arquivo '{nome_arquivo}'?\n\nQualquer modificação não salva será perdida.")
        msg_box.setIcon(QMessageBox.Icon.Warning)

        # Adiciona botões com textos personalizados
        btn_fechar = msg_box.addButton("Sim, fechar arquivo", QMessageBox.ButtonRole.AcceptRole)
        btn_cancelar = msg_box.addButton("Não, manter aberto", QMessageBox.ButtonRole.RejectRole)
        msg_box.setDefaultButton(btn_cancelar)

        # Exibe a janela de validação
        msg_box.exec()

        # Verifica a resposta do usuário
        if msg_box.clickedButton() == btn_fechar:
            self.tabs.removeTab(indice)
            aba.deleteLater() # Libera memória da imagem
            self.statusBar().showMessage(f"Arquivo '{nome_arquivo}' fechado.")
            
            # Se não houver mais abas abertas, volta para a tela inicial (Página 0)
            if self.tabs.count() == 0:
                self._stacked.setCurrentIndex(0)
                self._atualizar_status_vazio()

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
    
    def salvar_imagem(self) -> None:
        """Salva a imagem da aba atual em arquivo."""
        aba_atual = self.tabs.currentWidget()
        if not aba_atual:
            QMessageBox.information(self, "Aviso", "Nenhuma imagem para salvar.")
            return

        caminho, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar imagem",
            aba_atual.caminho,
            "PNG (*.png);;JPG (*.jpg);;BMP (*.bmp)"
        )

        if not caminho:
            return

        sucesso = cv2.imwrite(caminho, aba_atual.imagem_atual)

        if sucesso:
            aba_atual.caminho = caminho
            self.statusBar().showMessage(f"Imagem salva em: {caminho}")
            # Atualiza a miniatura caso o usuário tenha salvo após aplicar um filtro
            self.tabs.setTabIcon(self.tabs.currentIndex(), self._gerar_icone_miniatura(aba_atual.imagem_atual))
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

        # Gera um nome genérico para a nova aba
        contador = self.tabs.count() + 1
        nome_arquivo = f"Clipboard_{contador}"
        caminho_ficticio = f"/{nome_arquivo}" # Caminho fictício, pois ainda não existe no disco
        
        # Instancia o documento de imagem
        novo_documento = DocumentoImagem(caminho_ficticio, imagem_bgr)
        miniatura_icon = self._gerar_icone_miniatura(imagem_bgr)
        
        # Adiciona a aba com o ícone (miniatura)
        indice = self.tabs.addTab(novo_documento, miniatura_icon, nome_arquivo)
        self.tabs.setTabToolTip(indice, "Imagem colada (Não salva)")
        self.tabs.setCurrentIndex(indice)

        # Alterna o QStackedWidget para mostrar a página de abas (Página 1)
        self._stacked.setCurrentIndex(1)
        
        # Marca como modificado para forçar o asterisco e indicar que o arquivo precisa ser salvo
        self._marcar_como_modificado(novo_documento, True)

        self.statusBar().showMessage("Imagem colada do clipboard.")

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
        if not aba_atual:
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
        """Substitui a imagem de trabalho pela imagem processada e atualiza a miniatura da aba."""
        imagem_bgr = cv2.cvtColor(imagem_rgb, cv2.COLOR_RGB2BGR)
        aba.imagem_atual = imagem_bgr
        aba.imagem_backup = None
        
        # Atualiza a aba com a nova miniatura
        indice_aba = self.tabs.indexOf(aba)
        if indice_aba != -1:
            self.tabs.setTabIcon(indice_aba, self._gerar_icone_miniatura(imagem_bgr))
            
        self._marcar_como_modificado(aba, True)
        self.statusBar().showMessage("Filtro aplicado com sucesso.")

    def _restaurar_backup(self) -> None:
        """Restaura a imagem da aba atual ao estado anterior."""
        aba_atual = self.tabs.currentWidget()
        if aba_atual and aba_atual.imagem_backup is not None:
            aba_atual.imagem_atual = aba_atual.imagem_backup
            aba_atual.atualizar_visualizacao(aba_atual.imagem_atual)
            aba_atual.imagem_backup = None

    def _ao_zoom_alterado(self, zoom: float) -> None:
        """Atualiza o indicador permanente com o nível de zoom atual."""
        nivel_zoom = round(zoom * 100)
        self._label_zoom_status.setText(f"Zoom: {nivel_zoom:.0f}%")

    def keyPressEvent(self, evento) -> None:
        """Inicia o modo de arrasto (Barra de Espaço) delegando para a aba atual."""
        if evento.key() == Qt.Key.Key_Space and not evento.isAutoRepeat():
            aba_atual = self.tabs.currentWidget()
            
            # Repassa ao DocumentoImagem (assumindo que ele herdará/instanciará o VisualizadorImagem)
            if aba_atual and hasattr(aba_atual, 'definir_modo_arrasto'):
                aba_atual.definir_modo_arrasto(True)
                
            evento.accept()
            return
        super().keyPressEvent(evento)

    def keyReleaseEvent(self, evento) -> None:
        """Encerra o modo de arrasto (Barra de Espaço) delegando para a aba atual."""
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

    def _exibir_imagem(self, imagem_bgr: np.ndarray, ajustar_a_janela: bool = False) -> None:
        """
        Delega a exibição da imagem à aba atual.
        Mantido para retrocompatibilidade com funções da branch main.
        """
        aba_atual = self.tabs.currentWidget()
        if aba_atual:
            # Se você integrar a lógica de 'ajustar_a_janela' no DocumentoImagem depois, 
            # você pode passar essa variável como parâmetro aqui também.
            aba_atual.atualizar_visualizacao(imagem_bgr)
            
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
    app = QApplication(sys.argv)
    app.setApplicationName("Studio de Processamento de Imagens")
    janela = JanelaPrincipal()
    janela.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
