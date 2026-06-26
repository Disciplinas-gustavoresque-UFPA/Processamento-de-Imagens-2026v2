# Importa a biblioteca OpenCV, usada para o processamento matemático das matrizes da imagem
import cv2

# Importa a biblioteca NumPy, padronizada no Python para manipulação eficiente de arrays
import numpy as np

# Importa os componentes visuais do PySide6 (Qt) para construir a interface do plugin
from PySide6.QtWidgets import (
    QVBoxLayout,  # Gerenciador de layout que empilha elementos verticalmente
    QHBoxLayout,  # Gerenciador de layout que enfileira elementos horizontalmente
    QPushButton,  # Componente de botão clicável
    QLabel,       # Componente de rótulo para exibir textos
    QSizePolicy   # Classe de política de tamanho (nova adição para consertar o corte do texto)
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
            "Binariza a imagem calculando o limiar ideal automaticamente pelo método de Otsu.",
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
        
        # Cria um novo rótulo usando formatação HTML básica para destacar a informação
        info_parametros = QLabel(
            "O método de Otsu analisa o histograma da imagem "
            "e encontra o ponto de corte perfeito de forma automática.",
            self
        )
        
        # Aplica a mesma política de quebra de linha e expansão de tamanho para não cortar
        info_parametros.setWordWrap(True)
        info_parametros.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        
        # Adiciona as informações de parâmetros abaixo da descrição principal
        layout_principal.addWidget(info_parametros)
        
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

        # Conecta o sinal de clique do botão "Aplicar" à nossa função interna _ao_aplicar
        self._btn_aplicar.clicked.connect(self._ao_aplicar)
        
        # Conecta o sinal de clique do botão "Cancelar" à função reject() do Qt (que fecha a janela recusando mudanças)
        self._btn_cancelar.clicked.connect(self.reject)

        # Aplica o layout que construímos como a interface oficial deste plugin
        self.setLayout(layout_principal)
        
        # Força o painel a ter pelo menos 320 pixels de largura para garantir boa leitura dos textos
        self.setMinimumWidth(320)

    # Método central onde a matemática matricial da imagem é manipulada
    def processar(self, imagem: np.ndarray) -> np.ndarray:
        
        # O Otsu exige que a imagem esteja em tons de cinza (matriz 2D, 1 canal de cor).
        # Avalia o "shape" (dimensões da matriz). Se tiver 3 dimensões (Alt, Larg, Cor), indica que é colorida (RGB)
        if len(imagem.shape) == 3:
            # Usa a função do OpenCV para converter a matriz RGB (3 canais) para Cinza (1 canal)
            imagem_cinza = cv2.cvtColor(imagem, cv2.COLOR_RGB2GRAY)
        else:
            # Se não possuir 3 dimensões, assume-se que já é uma imagem em tons de cinza
            imagem_cinza = imagem
            
        # Aplica o limiar matemático usando o algoritmo de Otsu.
        # Parâmetros:
        # - imagem_cinza: A imagem de entrada.
        # - 0: O valor do limiar t (O OpenCV ignora esse número quando usamos a flag THRESH_OTSU).
        # - 255: O valor máximo (Branco absoluto) que os pixels receberão se ultrapassarem o limiar.
        # - THRESH_BINARY + THRESH_OTSU: A soma dessas flags diz ao OpenCV para binarizar e calcular o 't' sozinho.
        # A função retorna duas coisas: O limiar matemático encontrado (t_ideal) e a nova imagem (imagem_binaria).
        t_ideal, imagem_binaria = cv2.threshold(
            imagem_cinza, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )

        # Preparação do retorno para o app.py
        # O motor visual da aplicação (PySide6) espera uma matriz de 3 dimensões (RGB) para renderizar o Canvas.
        # Convertemos a imagem preta e branca (1 canal) de volta para o formato RGB (3 canais) repetindo os valores binários.
        return cv2.cvtColor(imagem_binaria, cv2.COLOR_GRAY2RGB)

    # Método executado na exata fração de segundo em que o botão Aplicar é clicado
    def _ao_aplicar(self) -> None:
        
        # Chama a função 'processar' construída acima, passando a imagem de backup intacta da aplicação
        imagem_processada = self.processar(self.imagem_original)
        
        # Emite (dispara) um sinal interno do Qt com a matriz da imagem resultante, avisando ao app.py para sobrescrever a tela original
        self.apply_requested.emit(imagem_processada)
        
        # Fecha a janela do plugin informando ao Qt que a operação foi um sucesso (Aceita)
        self.accept()