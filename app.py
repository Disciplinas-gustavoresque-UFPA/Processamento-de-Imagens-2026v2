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
* Carregar plugins dinamicamente em dois grupos de menu:
    - ``Pixels`` para operações pontuais (ex.: brilho/contraste).
    - ``Filtros`` para operações regionais.
* Pré-visualizar e aplicar filtros via os sinais ``preview_requested`` e
    ``apply_requested`` definidos em ``PluginBase``.
"""

import importlib.util
import inspect
import os
import sys

import cv2
import numpy as np
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QImage, QPixmap, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QScrollArea,
    QSizePolicy,
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
            submenu = QMenu(entrada, menu_pai)
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
        """Configura a interface baseada em um QTabWidget central."""
        self.tabs = QTabWidget(self)
        self.tabs.setTabsClosable(True) # Habilita o botão (X) em cada aba
        
        # Estilo para deixar as abas maiores (para caber a miniatura)
        self.tabs.setIconSize(QSize(40, 40))
        self.tabs.setStyleSheet("""
            QTabBar { alignment: left; }
            QTabBar::tab { height: 80px; width: 140px; padding: 5px; font-weight: bold; text-align: left; }
            QTabWidget::pane { border-top: 2px solid #C2C7CB; }
        """)

        # Conecta o sinal de clique no botão de fechar da aba à função de validação
        self.tabs.tabCloseRequested.connect(self._solicitar_fechamento_aba)
        
        self.setCentralWidget(self.tabs)
        self.setStatusBar(QStatusBar(self))
        self._atualizar_status_vazio()

    def _construir_menus(self) -> None:
        """Cria a barra de menus com Arquivo, Pixels e Filtros."""
        barra = self.menuBar()

        # --- Menu Arquivo ---
        menu_arquivo = barra.addMenu("Arquivo")
        acao_abrir = menu_arquivo.addAction("Abrir imagem…")
        acao_abrir.triggered.connect(self.abrir_imagem)
        
        acao_salvar = menu_arquivo.addAction("Salvar imagem…")
        acao_salvar.triggered.connect(self.salvar_imagem)
        menu_arquivo.addSeparator()
        acao_sair = menu_arquivo.addAction("Sair")
        acao_sair.triggered.connect(self.close)

        # --- Menu Pixels (operações pontuais) ---
        menu_pixels = barra.addMenu("Pixels")
        diretorio_pixels = os.path.join(_DIRETORIO_RAIZ, "plugins", "pixels")
        carregar_plugins_dinamicamente(menu_pixels, diretorio_pixels, self)

        if not menu_pixels.actions():
            aviso = menu_pixels.addAction("(nenhum plugin encontrado)")
            aviso.setEnabled(False)

        # --- Menu Filtros (operações regionais) ---
        menu_filtros = barra.addMenu("Filtros")
        diretorio_filtros = os.path.join(_DIRETORIO_RAIZ, "plugins", "filtros")
        carregar_plugins_dinamicamente(menu_filtros, diretorio_filtros, self)

        if not menu_filtros.actions():
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

        for caminho in caminhos:
            imagem_bgr = cv2.imread(caminho)
            if imagem_bgr is None:
                QMessageBox.critical(self, "Erro", f"Não foi possível abrir:\n{caminho}")
                continue

             # Instancia o documento e adiciona à UI
            novo_documento = DocumentoImagem(caminho, imagem_bgr)
            
            # Gera a miniatura (Icon) para a aba
            miniatura_icon = self._gerar_icone_miniatura(imagem_bgr)
            
            # Pega só o nome do arquivo para colocar na aba (Ex: foto.jpg)
            nome_arquivo = os.path.basename(caminho)
            
            # Adiciona a aba com o ícone (miniatura) e o título
            indice = self.tabs.addTab(novo_documento, miniatura_icon, nome_arquivo)
            self.tabs.setCurrentIndex(indice)

            self.statusBar().showMessage(f"Imagem carregada: {nome_arquivo}")
    
    def _gerar_icone_miniatura(self, imagem_bgr: np.ndarray) -> QIcon:
        """Converte uma imagem OpenCV para QIcon para usar na aba."""
        imagem_rgb = cv2.cvtColor(imagem_bgr, cv2.COLOR_BGR2RGB)
        altura, largura, canais = imagem_rgb.shape
        qimage = QImage(imagem_rgb.data, largura, altura, canais * largura, QImage.Format.Format_RGB888)
        
        # Cria um pixmap quadrado e escala a imagem para caber
        pixmap = QPixmap(60, 60)
        pixmap.fill(Qt.GlobalColor.transparent)
        pixmap_imagem = QPixmap.fromImage(qimage).scaled(
            60, 60, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        
        # Desenha a miniatura centralizada no ícone
        import PySide6.QtGui as QtGui
        painter = QtGui.QPainter(pixmap)
        x = (60 - pixmap_imagem.width()) // 2
        y = (60 - pixmap_imagem.height()) // 2
        painter.drawPixmap(x, y, pixmap_imagem)
        painter.end()
        
        return QIcon(pixmap)

    def _solicitar_fechamento_aba(self, indice: int) -> None:
        """Dispara o alerta de fechamento. Se o usuário confirmar, fecha a aba."""
        if indice < 0:
            return
            
        aba = self.tabs.widget(indice)
        nome_arquivo = os.path.basename(aba.caminho)

        resposta = QMessageBox.warning(
            self,
            "Aviso de Fechamento",
            f"Deseja realmente fechar o arquivo '{nome_arquivo}'?\n\nQualquer modificação não salva será perdida.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel
        )

        if resposta == QMessageBox.StandardButton.Yes:
            self.tabs.removeTab(indice)
            aba.deleteLater() # Libera memória
            self.statusBar().showMessage(f"Arquivo '{nome_arquivo}' fechado.")
            if self.tabs.count() == 0:
                self._atualizar_status_vazio()

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
            self.statusBar().showMessage(f"Imagem salva em: {caminho}")
            # Atualiza a miniatura caso o usuário tenha salvo após aplicar um filtro
            self.tabs.setTabIcon(self.tabs.currentIndex(), self._gerar_icone_miniatura(aba_atual.imagem_atual))
        else:
            QMessageBox.critical(self, "Erro", "Falha ao salvar a imagem.")

    def _atualizar_status_vazio(self):
        self.statusBar().showMessage("Pronto. Abra uma imagem no menu Arquivo.")

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
            
        self.statusBar().showMessage("Filtro aplicado com sucesso.")

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
