# Importa a biblioteca OpenCV, usada para o processamento matemático das matrizes da imagem
import cv2

# Importa a biblioteca NumPy, padronizada no Python para manipulação eficiente de arrays
import numpy as np

# Importa os componentes visuais do PySide6 (Qt) para construir a interface do plugin
from PySide6.QtWidgets import (
    QVBoxLayout,    # Gerenciador de layout que empilha elementos verticalmente
    QHBoxLayout,    # Gerenciador de layout que enfileira elementos horizontalmente
    QPushButton,    # Componente de botão clicável
    QLabel,         # Componente de rótulo para exibir textos
    QSizePolicy,    # Classe de política de tamanho (para consertar o corte do texto)
    QRadioButton,   # Componente de seleção exclusiva (radio button) — apenas um pode ser marcado
    QButtonGroup,   # Agrupador lógico que garante a exclusão mútua entre radio buttons
    QGroupBox,      # Componente de caixa agrupadora com título e borda visual
)

# Importa a classe base de plugins que o professor construiu no motor do projeto
from core.plugin_base import PluginBase


# Declara a classe do plugin, herdando toda a lógica (como a janela e os sinais) do PluginBase
class OtsuThresholding(PluginBase):

    # Propriedade lida pelo `app.py` para definir o nome que aparece na barra de menus
    display_name = "Otsu Thresholding"

    # Método obrigatório executado para desenhar os botões e textos na janela do plugin
    def setup_ui(self) -> None:

        # Cria o organizador vertical principal; tudo será empilhado de cima para baixo
        layout_principal = QVBoxLayout(self)

        # Cria o rótulo de texto explicando o que a ferramenta faz
        descricao = QLabel(
            "Binariza a imagem calculando o limiar ideal automaticamente pelo método de Otsu.\n"
            "Selecione em qual canal o filtro será aplicado.",
            self
        )

        # Habilita a quebra de linha automática (Word Wrap) para textos longos
        descricao.setWordWrap(True)

        # Define que a caixa de texto pode expandir na horizontal e deve respeitar a altura mínima para não cortar
        descricao.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        # Insere a descrição no topo do layout vertical
        layout_principal.addWidget(descricao)

        # Adiciona um espaçamento visual (margem) de 10 pixels no layout
        layout_principal.addSpacing(10)

        # ────────────────────────────────────────────────────────────
        # Grupo lógico exclusivo — garante que apenas um radio button
        # esteja marcado em toda a janela (entre RGB, HSV e Cinza)
        # ────────────────────────────────────────────────────────────

        # Cria o agrupador lógico que impõe exclusão mútua entre todos os radio buttons
        self._grupo_canais = QButtonGroup(self)

        # Dicionário que mapeia cada chave de canal ao seu radio button correspondente
        # Usado em _obter_canal() para descobrir qual opção está marcada
        self._radios_canal: dict[str, QRadioButton] = {}

        # ────────────────────────────────────────────────────────────
        # Opção padrão: Escala de Cinza
        # ────────────────────────────────────────────────────────────

        # Cria o radio button "Escala de Cinza" — comportamento original do Otsu
        radio_cinza = QRadioButton("Escala de Cinza (padrão)", self)

        # Registra no agrupador lógico e no dicionário de mapeamento
        self._grupo_canais.addButton(radio_cinza)
        self._radios_canal["cinza"] = radio_cinza

        # Marca como selecionado ao abrir o plugin (opção padrão)
        radio_cinza.setChecked(True)

        # Adiciona o radio button ao layout principal (fora de qualquer QGroupBox)
        layout_principal.addWidget(radio_cinza)

        # Adiciona um espaçamento antes dos grupos de canais
        layout_principal.addSpacing(5)

        # ────────────────────────────────────────────────────────────
        # Grupo visual (QGroupBox) para os canais do modelo RGB
        # ────────────────────────────────────────────────────────────

        # Cria uma caixa agrupadora rotulada "Canais RGB" para organizar as opções visualmente
        grupo_rgb = QGroupBox("Canais RGB", self)

        # Cria um layout vertical interno para empilhar os radio buttons dentro do grupo
        layout_rgb = QVBoxLayout()

        # Lista de opções RGB: tupla (texto visível, chave interna)
        opcoes_rgb = [
            ("Canal Vermelho (R)", "r"),
            ("Canal Verde (G)",    "g"),
            ("Canal Azul (B)",     "b"),
        ]

        # Cria um radio button para cada canal RGB e registra no agrupador e no dicionário
        for texto, chave in opcoes_rgb:
            radio = QRadioButton(texto, self)
            self._grupo_canais.addButton(radio)
            self._radios_canal[chave] = radio
            layout_rgb.addWidget(radio)

        # Define o layout interno do grupo RGB
        grupo_rgb.setLayout(layout_rgb)

        # Insere o grupo RGB no layout vertical principal
        layout_principal.addWidget(grupo_rgb)

        # Adiciona espaçamento entre os dois grupos de canais
        layout_principal.addSpacing(5)

        # ────────────────────────────────────────────────────────────
        # Grupo visual (QGroupBox) para os canais do modelo HSV
        # ────────────────────────────────────────────────────────────

        # Cria uma caixa agrupadora rotulada "Canais HSV" para organizar as opções visualmente
        grupo_hsv = QGroupBox("Canais HSV", self)

        # Cria um layout vertical interno para empilhar os radio buttons dentro do grupo
        layout_hsv = QVBoxLayout()

        # Lista de opções HSV: tupla (texto visível, chave interna)
        opcoes_hsv = [
            ("Matiz (H)",             "h"),
            ("Saturação (S)",         "s"),
            ("Valor / Brilho (V)",    "v"),
        ]

        # Cria um radio button para cada canal HSV e registra no agrupador e no dicionário
        for texto, chave in opcoes_hsv:
            radio = QRadioButton(texto, self)
            self._grupo_canais.addButton(radio)
            self._radios_canal[chave] = radio
            layout_hsv.addWidget(radio)

        # Define o layout interno do grupo HSV
        grupo_hsv.setLayout(layout_hsv)

        # Insere o grupo HSV no layout vertical principal
        layout_principal.addWidget(grupo_hsv)

        # ────────────────────────────────────────────────────────────
        # Rótulo informativo que mostra o limiar encontrado pelo Otsu
        # ────────────────────────────────────────────────────────────
        layout_principal.addSpacing(5)

        self._rotulo_limiar = QLabel("", self)
        self._rotulo_limiar.setWordWrap(True)
        self._rotulo_limiar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        layout_principal.addWidget(self._rotulo_limiar)

        # ────────────────────────────────────────────────────────────
        # Espaço elástico e botões de ação
        # ────────────────────────────────────────────────────────────

        # Cria um "espaço elástico" que empurra os textos para cima e os botões para baixo
        layout_principal.addStretch()

        # Cria um organizador horizontal para alocar os botões um ao lado do outro
        layout_botoes = QHBoxLayout()

        # Cria o botão "Aplicar" para rodar o filtro e salvar na tela
        self._btn_aplicar = QPushButton("Aplicar", self)

        # Cria o botão "Cancelar" para fechar o diálogo e reverter alterações
        self._btn_cancelar = QPushButton("Cancelar", self)

        # Adiciona o botão Aplicar no layout horizontal (fica na esquerda)
        layout_botoes.addWidget(self._btn_aplicar)

        # Adiciona o botão Cancelar no layout horizontal (fica na direita)
        layout_botoes.addWidget(self._btn_cancelar)

        # Insere a "linha" de botões no fundo do layout vertical principal
        layout_principal.addLayout(layout_botoes)

        # ────────────────────────────────────────────────────────────
        # Conexões de sinais (eventos)
        # ────────────────────────────────────────────────────────────

        # Conecta a mudança de seleção do radio button ao método de preview
        # O sinal toggled(bool) é emitido tanto ao marcar quanto ao desmarcar;
        # filtramos dentro do slot para processar apenas quando 'marcado' é True
        for radio in self._radios_canal.values():
            radio.toggled.connect(self._ao_alterar_selecao)

        # Conecta o sinal de clique do botão "Aplicar" à nossa função interna _ao_aplicar
        self._btn_aplicar.clicked.connect(self._ao_aplicar)

        # Conecta o sinal de clique do botão "Cancelar" à função reject() do Qt
        self._btn_cancelar.clicked.connect(self.reject)

        # Aplica o layout que construímos como a interface oficial deste plugin
        self.setLayout(layout_principal)

        # Força o painel a ter pelo menos 360 pixels de largura para garantir boa leitura dos textos
        self.setMinimumWidth(360)

    # ────────────────────────────────────────────────────────────────
    # Método auxiliar interno
    # ────────────────────────────────────────────────────────────────

    def _obter_canal(self) -> str:
        """
        Verifica qual radio button está marcado e retorna a sua chave.
        Possíveis valores: "cinza", "r", "g", "b", "h", "s", "v".
        """
        for chave, radio in self._radios_canal.items():
            if radio.isChecked():
                return chave
        # Caso de segurança — nunca deveria acontecer porque sempre há um marcado
        return "cinza"

    # ────────────────────────────────────────────────────────────────
    # Método central de processamento
    # ────────────────────────────────────────────────────────────────

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        """
        Aplica o limiar de Otsu no canal selecionado pelo usuário.

        Lógica:
        1. Identifica qual canal está marcado (cinza, R, G, B, H, S ou V).
        2. Extrai o canal correspondente da imagem:
           - "cinza": converte RGB → tons de cinza.
           - "r", "g", "b": extrai o canal diretamente da matriz RGB.
           - "h", "s", "v": converte RGB → HSV e extrai o canal desejado.
        3. Aplica cv2.threshold com a flag THRESH_OTSU no canal extraído.
        4. Converte o resultado de volta para RGB (3 canais) para exibição.
        """
        canal_selecionado = self._obter_canal()

        # Nomes legíveis para o rótulo informativo
        nomes = {
            "cinza": "Escala de Cinza",
            "r": "Vermelho (R)", "g": "Verde (G)", "b": "Azul (B)",
            "h": "Matiz (H)", "s": "Saturação (S)", "v": "Valor/Brilho (V)",
        }

        # ── Extração do canal base para aplicar o Otsu ──

        if canal_selecionado == "cinza":
            # Converte a imagem RGB para tons de cinza (1 canal)
            if len(imagem.shape) == 3:
                canal_base = cv2.cvtColor(imagem, cv2.COLOR_RGB2GRAY)
            else:
                canal_base = imagem

        elif canal_selecionado in {"r", "g", "b"}:
            # Mapeia a chave para o índice do canal na matriz RGB (R=0, G=1, B=2)
            indice = {"r": 0, "g": 1, "b": 2}[canal_selecionado]
            canal_base = imagem[:, :, indice]

        else:
            # Canais HSV: converte de RGB para HSV e extrai o canal desejado
            imagem_hsv = cv2.cvtColor(imagem, cv2.COLOR_RGB2HSV)
            indice = {"h": 0, "s": 1, "v": 2}[canal_selecionado]
            canal_base = imagem_hsv[:, :, indice]

        # ── Aplicação do limiar de Otsu ──
        # Parâmetros:
        # - canal_base: o canal extraído (matriz 2D, 1 canal).
        # - 0: valor ignorado pelo OpenCV quando usamos a flag THRESH_OTSU.
        # - 255: valor máximo (branco absoluto) atribuído aos pixels acima do limiar.
        # - THRESH_BINARY + THRESH_OTSU: binariza e calcula o limiar ideal automaticamente.
        # Retorna o limiar encontrado (t_ideal) e a imagem binarizada (imagem_binaria).
        t_ideal, imagem_binaria = cv2.threshold(
            canal_base, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )

        # Atualiza o rótulo informativo na interface com o limiar encontrado
        nome_canal = nomes.get(canal_selecionado, canal_selecionado)
        self._rotulo_limiar.setText(
            f"Limiar encontrado ({nome_canal}): {int(t_ideal)}"
        )

        # O motor visual da aplicação (PySide6) espera uma matriz de 3 dimensões (RGB).
        # Converte a imagem binária (1 canal) de volta para RGB (3 canais) repetindo os valores.
        return cv2.cvtColor(imagem_binaria, cv2.COLOR_GRAY2RGB)

    # ────────────────────────────────────────────────────────────────
    # Slots de eventos (sinais)
    # ────────────────────────────────────────────────────────────────

    def _ao_alterar_selecao(self, marcado: bool) -> None:
        """Regera o processamento para mostrar o preview ao vivo no canvas."""
        # O sinal toggled é emitido duas vezes: uma para o botão desmarcado (False)
        # e outra para o botão marcado (True). Filtramos para processar apenas uma vez.
        if not marcado:
            return
        imagem_processada = self.processar(self.imagem_original)
        self.preview_requested.emit(imagem_processada)

    def _ao_aplicar(self) -> None:
        """Aplica o filtro na matriz oficial e fecha a janela."""
        # Chama a função 'processar' passando a imagem de backup intacta da aplicação
        imagem_processada = self.processar(self.imagem_original)

        # Emite (dispara) um sinal interno do Qt com a matriz da imagem resultante
        self.apply_requested.emit(imagem_processada)

        # Fecha a janela do plugin informando ao Qt que a operação foi um sucesso (Aceita)
        self.accept()