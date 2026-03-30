"""
app.py
------
Janela Principal do Studio de Processamento de Imagens.

Funcionalidades
---------------
* Abrir imagens (PNG, JPG, BMP, TIFF).
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
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QKeySequence, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QMenu,
    QMessageBox,
    QStatusBar,
)

# Garante que o diretório raiz do projeto esteja no sys.path para que os
# plugins possam importar ``core.plugin_base`` sem ajustes manuais.
_DIRETORIO_RAIZ = os.path.dirname(os.path.abspath(__file__))
if _DIRETORIO_RAIZ not in sys.path:
    sys.path.insert(0, _DIRETORIO_RAIZ)

from core.plugin_base import PluginBase  # noqa: E402  (importação após sys.path)
from components.zoom.zoom import VisualizadorImagem  # noqa: E402


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
# Janela Principal
# ---------------------------------------------------------------------------
class JanelaPrincipal(QMainWindow):
    """Janela principal do Studio de Processamento de Imagens."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Studio de Processamento de Imagens")
        self.resize(900, 650)

        # Estado interno
        self._imagem_atual: np.ndarray | None = None   # BGR (OpenCV)
        self._imagem_backup: np.ndarray | None = None  # cópia antes do plugin

        self._construir_interface()
        self._construir_menus()

    # ------------------------------------------------------------------
    # Construção da interface
    # ------------------------------------------------------------------

    def _construir_interface(self) -> None:
        """Cria o widget central (área de visualização da imagem)."""
        self._visualizador = VisualizadorImagem(self)
        self._visualizador.zoom_alterado.connect(self._ao_zoom_alterado)
        self.setCentralWidget(self._visualizador)

        self.setStatusBar(QStatusBar(self))

    def _construir_menus(self) -> None:
        """Cria a barra de menus com Arquivo, Visualizar e Filtros (plugins)."""
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

        # --- Menu Visualizar ---
        menu_visualizar = barra.addMenu("Visualizar")

        acao_zoom_mais = menu_visualizar.addAction("Aumentar zoom")
        acao_zoom_mais.setShortcut(QKeySequence.StandardKey.ZoomIn)
        acao_zoom_mais.triggered.connect(self._visualizador.aumentar_zoom)

        acao_zoom_menos = menu_visualizar.addAction("Diminuir zoom")
        acao_zoom_menos.setShortcut(QKeySequence.StandardKey.ZoomOut)
        acao_zoom_menos.triggered.connect(self._visualizador.diminuir_zoom)

        acao_ajustar = menu_visualizar.addAction("Ajustar à janela")
        acao_ajustar.setShortcut("Ctrl+9")
        acao_ajustar.triggered.connect(self._visualizador.ajustar_imagem_a_janela)

        acao_zoom_100 = menu_visualizar.addAction("Zoom 100%")
        acao_zoom_100.setShortcut("Ctrl+0")
        acao_zoom_100.triggered.connect(self._visualizador.resetar_zoom)

        # --- Menu Filtros (populado dinamicamente) ---
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
        """Abre um diálogo de arquivo e carrega a imagem selecionada."""
        caminho, _ = QFileDialog.getOpenFileName(
            self,
            "Abrir Imagem",
            "",
            "Imagens (*.png *.jpg *.jpeg *.bmp *.tiff *.tif)",
        )
        if not caminho:
            return

        imagem_bgr = cv2.imread(caminho)
        if imagem_bgr is None:
            QMessageBox.critical(self, "Erro", f"Não foi possível abrir:\n{caminho}")
            return

        self._imagem_atual = imagem_bgr
        self._exibir_imagem(imagem_bgr, resetar_zoom=True)
        self.statusBar().showMessage(f"Imagem carregada: {caminho}")
        
    def salvar_imagem(self) -> None:
        """Salva a imagem atual em arquivo."""
        if self._imagem_atual is None:
            QMessageBox.information(self, "Aviso", "Nenhuma imagem para salvar.")
            return

        caminho, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar imagem",
            "",
            "PNG (*.png);;JPG (*.jpg);;BMP (*.bmp)"
        )

        if not caminho:
            return

        sucesso = cv2.imwrite(caminho, self._imagem_atual)

        if sucesso:
            self.statusBar().showMessage(f"Imagem salva em: {caminho}")
        else:
            QMessageBox.critical(self, "Erro", "Falha ao salvar a imagem.")

    def abrir_plugin(self, classe_plugin: type) -> None:
        """
        Instancia e exibe o diálogo do plugin, conectando seus sinais.

        Parâmetros
        ----------
        classe_plugin : type
            Classe do plugin a ser instanciado (subclasse de ``PluginBase``).
        """
        if self._imagem_atual is None:
            QMessageBox.information(
                self, "Aviso", "Abra uma imagem antes de aplicar um filtro."
            )
            return

        # Converte BGR → RGB antes de enviar ao plugin
        imagem_rgb = cv2.cvtColor(self._imagem_atual, cv2.COLOR_BGR2RGB)
        self._imagem_backup = self._imagem_atual.copy()

        dialogo = classe_plugin(imagem_rgb, self)
        dialogo.preview_requested.connect(self._ao_receber_preview)
        dialogo.apply_requested.connect(self._ao_aplicar_plugin)

        # Se o usuário fechar sem aplicar, restaura a imagem original
        dialogo.finished.connect(self._ao_fechar_plugin)

        dialogo.exec()

    # ------------------------------------------------------------------
    # Slots privados
    # ------------------------------------------------------------------

    def _ao_fechar_plugin(self, codigo: int) -> None:
        """Restaura o backup se o diálogo foi fechado sem confirmar."""
        from PySide6.QtWidgets import QDialog
        if codigo != QDialog.DialogCode.Accepted:
            self._restaurar_backup()

    def _ao_receber_preview(self, imagem_rgb: np.ndarray) -> None:
        """Exibe a pré-visualização sem alterar a imagem de trabalho."""
        imagem_bgr = cv2.cvtColor(imagem_rgb, cv2.COLOR_RGB2BGR)
        self._exibir_imagem(imagem_bgr)

    def _ao_aplicar_plugin(self, imagem_rgb: np.ndarray) -> None:
        """Substitui a imagem de trabalho pela imagem processada."""
        self._imagem_atual = cv2.cvtColor(imagem_rgb, cv2.COLOR_RGB2BGR)
        self._imagem_backup = None
        self.statusBar().showMessage("Filtro aplicado com sucesso.")

    def _restaurar_backup(self) -> None:
        """Restaura a imagem ao estado anterior à abertura do plugin."""
        if self._imagem_backup is not None:
            self._imagem_atual = self._imagem_backup
            self._exibir_imagem(self._imagem_atual)
            self._imagem_backup = None

    def _ao_zoom_alterado(self, zoom: float) -> None:
        """Atualiza a barra de status com o nível de zoom atual."""
        self.statusBar().showMessage(f"Zoom: {int(zoom * 100)}%")

    def keyPressEvent(self, evento) -> None:
        if evento.key() == Qt.Key.Key_Space and not evento.isAutoRepeat():
            self._visualizador.definir_modo_arrasto(True)
            evento.accept()
            return
        super().keyPressEvent(evento)

    def keyReleaseEvent(self, evento) -> None:
        if evento.key() == Qt.Key.Key_Space and not evento.isAutoRepeat():
            self._visualizador.definir_modo_arrasto(False)
            evento.accept()
            return
        super().keyReleaseEvent(evento)

    # ------------------------------------------------------------------
    # Utilitários de exibição
    # ------------------------------------------------------------------

    def _exibir_imagem(self, imagem_bgr: np.ndarray, resetar_zoom: bool = False) -> None:
        """
        Converte um array BGR para QPixmap e delega a exibição ao
        componente de visualização, preservando o zoom atual por padrão.
        """
        imagem_rgb = cv2.cvtColor(imagem_bgr, cv2.COLOR_BGR2RGB)
        altura, largura, canais = imagem_rgb.shape
        bytes_por_linha = canais * largura
        qimage = QImage(
            imagem_rgb.data,
            largura,
            altura,
            bytes_por_linha,
            QImage.Format.Format_RGB888,
        )
        pixmap = QPixmap.fromImage(qimage)
        self._visualizador.definir_pixmap(pixmap, resetar_zoom=resetar_zoom)


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
