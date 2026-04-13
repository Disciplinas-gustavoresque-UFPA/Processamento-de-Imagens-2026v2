# Studio de Processamento de Imagens 2026

Repositório colaborativo da disciplina de Processamento de Imagens — UFPA 2026.

## Visão Geral

Este projeto é um **Studio de Processamento de Imagens** interativo, com interface nativa construída em Python e PySide6 (Qt). A arquitetura é modular e baseada em **plugins dinâmicos**, permitindo que dezenas de alunos contribuam simultaneamente.

## 🎮 Gamificação e Recompensas

Para tornar o nosso desenvolvimento mais dinâmico e simular um ambiente de engenharia de software de alto nível, este repositório conta com um sistema de gamificação.

As suas contribuições e Pull Requests (PRs) não valem apenas nota, mas também **Badges (Medalhas)** de prestígio.

**Como funciona?**
1. Você realiza uma contribuição. Por exemplo, abre um Pull Request com o seu plugin, resolve um bug ou faz uma excelente revisão no código de um colega.
2. 📢 **Solicitação de Badge:** O professor **não** distribui badges automaticamente. Para concorrer a uma badge, **você deve solicitá-la explicitamente** em um comentário no seu PR ou na Issue, justificando brevemente o porquê.
   * *Exemplo:* "Acredito que mereço a badge 🐛 *Bug Catcher* pois identifiquei e resolvi o problema de vazamento de memória que travava a aplicação."
3. O professor fará a revisão e avaliará o seu pedido. Se o seu trabalho realmente atingir o nível esperado, o professor responderá concedendo a badge oficialmente.
4. Todo domingo à noite, nosso robô invisível (GitHub Actions) varre o repositório, contabiliza as badges concedidas e atualiza o **Hall da Fama** abaixo.

**As Badges que você pode conquistar:**

* 🤝 **O Salvador da Pátria:** Ajudou os colegas em discussões, revisões ou resolveu bloqueios da turma.
* 🐛 **Bug Catcher:** Encontrou e corrigiu um erro crítico no software.
* ⭐ **Código de Ouro:** Escreveu um código limpo, elegante, bem documentado e otimizado.
* 🧠 **Lógica Brilhante:** Implementou um algoritmo complexo de forma excepcional.
* 🎨 **UI/UX Master:** Criou uma interface de configuração (Dialog) no PySide6 absurdamente fácil e bonita de usar.
* 💻 **Enter the Matrix:** Dominou a manipulação de matrizes, tensores e álgebra linear usando NumPy/OpenCV.

**🏆 Badges Exclusivas de Code Review (Revisão de Código):**

* 🛡️ **Guardião do Merge:** Impediu que um código quebrado fosse para a branch principal sugerindo boas correções.
* 🔎 **Detetive do Código:** Encontrou aquele bug minúsculo e disfarçado na matemática do plugin de um colega.
* 🌉 **Guardião da Bifrost:** O aluno que está sempre atento e avaliando os Pull Requests da turma com agilidade.
* 📐 **Revisor Implacável:** Não deixa passar nada: cobra variáveis bem escritas, arquitetura limpa e padrão de projeto.

---

## 🏆 Hall da Fama - Placar Semanal da Turma

> 🤖 *Placar atualizado automaticamente em: 13/04/2026 00:05*

### ⌨️ Jack Bauer do Código
*Quem mais codificou na semana (Volume total de linhas mescladas)*

![Jack Bauer](/.github/images/memes/image_5.png)

🥇 **@sayydaviid** (314 linhas mescladas)

<details><summary>Ver Top 3 completo</summary>

🥇 @sayydaviid (314)
🥈 @ygarasab (116)

</details>

---

### 🤝 John Coffey do grupo
*Quem mais ganhou a badge 🤝 O Salvador da Pátria*

![John Coffey](/.github/images/memes/image_6.png)

🥇 **Ainda não há registros nesta semana.**

---

### 🐛 Pokemon Bug Catcher
*Quem mais ganhou a badge 🐛 Bug Catcher*

![Bug Catcher](/.github/images/memes/image_7.png)

🥇 **Ainda não há registros nesta semana.**

---

### ⭐ Patrick Bateman da turma
*Quem mais ganhou a badge ⭐ Código de Ouro*

![Patrick Bateman](/.github/images/memes/image_8.png)

🥇 **Ainda não há registros nesta semana.**

---

### 🧠 John Nash da turma
*Quem mais ganhou a badge 🧠 Lógica Brilhante*

![John Nash](/.github/images/memes/image_9.png)

🥇 **Ainda não há registros nesta semana.**

---

### 🎨 Da Vinci do Front-end
*Quem mais ganhou a badge 🎨 UI/UX Master*

![Da Vinci](/.github/images/memes/image_10.png)

🥇 **Ainda não há registros nesta semana.**

---

### 💻 Neo da turma
*Quem dominou o uso de matrizes e álgebra linear (Badge 💻 Enter the Matrix)*

![Neo](/.github/images/memes/image_11.png)

🥇 **Ainda não há registros nesta semana.**

---

### 🧙‍♂️ O Gandalf do Code Review
*Quem mais ganhou a badge 🛡️ Guardião do Merge*

![Gandalf](/.github/images/memes/image_12.png)

🥇 **Ainda não há registros nesta semana.**

---

### 🕵️ O Sherlock Holmes da Turma
*Quem mais ganhou a badge 🔎 Detetive do Código*

![Sherlock](/.github/images/memes/image_13.png)

🥇 **Ainda não há registros nesta semana.**

---

### 👁️ O Heimdall do Repositório
*Quem mais ganhou a badge 🌉 Guardião da Bifrost*

![Heimdall](/.github/images/memes/image_14.png)

🥇 **Ainda não há registros nesta semana.**

---

### 👓 A Edna Moda do Código
*Quem mais ganhou a badge 📐 Revisor Implacável*

![Edna](/.github/images/memes/image_15.png)

🥇 **Ainda não há registros nesta semana.**

---

## 📌 Fluxo de Trabalho (Issues e PRs)

Para manter o repositório organizado, evitar conflitos, temos duas formas de contribuir. Você é livre para propor melhorias em qualquer parte do código (interface, motor gráfico, estado, etc.), mas o fluxo abaixo deve ser sempre respeitado:

### Fluxo 1: Resolvendo uma Tarefa do Professor
1. **Escolha uma Issue e assuma a tarefa:** Vá na aba *Issues* do repositório, escolha uma tarefa e **deixe um comentário com o seu usuário (ex: "Vou desenvolver esta funcionalidade - @seu-nick")** para sinalizar que você é o responsável oficial por ela.
2. **Aguarde a Avaliação do Professor:** Ao fim da discussão, o professor vai aprovar sua Issue para desenvolvimento.
3. **Crie a Branch:** Crie uma branch associada a essa Issue (ex: `feature/tool-retangulo` ou `fix/bug-selecao`).
4. **Faça Commits Atômicos:** Recomendamos fortemente a prática de commits atômicos. Cada commit deve resolver um único problema ou adicionar uma única funcionalidade, sempre com uma mensagem clara e descritiva explicando a alteração.
5. **Abra um Draft PR:** Assim que fizer o seu primeiro commit, abra um Pull Request em modo **Draft** (Rascunho). Isso avisa à turma que você já está trabalhando ativamente nessa frente.
6. **Desenvolva:** Continue desenvolvendo a lógica e registrando seus avanços em novos commits atômicos.
7. **Revisão e Merge:** Quando finalizar, tire o PR do modo Draft e solicite a revisão (Review) do professor (`@gustavoresque`).

### Fluxo 2: Propondo Melhorias, UI/UX ou Correções
1. **Crie uma Issue:** Quer melhorar o CSS, otimizar o `StateManager.js` ou encontrou um bug de renderização no SVG? Abra uma nova Issue com a sua proposta e **insira o seu usuário (`@seu-nick`) na descrição.**
2. **Chame o Professor:** Mencione o professor (`@gustavoresque`) na Issue para avaliação.
3. **Aprovação:** O professor vai avaliar a viabilidade técnica e aprovar a Issue.
4. **Mão na Massa:** Com a ideia aprovada, siga os mesmos passos do Fluxo 1 (branch, commits atômicos, Draft PR, código e revisão).

---

## ⚖️ Políticas de Colaboração e Fluxo Ágil

Para garantir uma melhor organização no desenvolvimento, este repositório adota regras de colaboração baseadas em metodologias ágeis e práticas reais de projetos Open Source.

### 1. Ideação Livre (Criação de Issues)
O repositório é aberto para ideias. Qualquer aluno pode (e deve! Pois faz parte da avaliação também) abrir Issues sugerindo novos filtros, ferramentas, correções de bugs ou melhorias de interface a qualquer momento. No entanto, **abrir uma Issue não significa que você tem autorização imediata para codificá-la.**

### 2. O "Sinal Verde" (Lock e Autorização)
Você só pode criar uma branch e começar a escrever código para uma Issue após o professor aprovar e "travar" a tarefa para você.
* **Como solicitar:** Deixe um comentário na Issue dizendo *"Quero assumir esta tarefa - @seu-nick"* ou algo assim.
* **Aprovação:** O professor avaliará a solicitação e adicionará uma label (ex: `Aprovada`), atribuindo você oficialmente como o responsável (Assignee).

### 3. Propriedade e Trabalho em Equipe (Ownership)
O aluno que recebeu a autorização (Assignee) torna-se o **"Tech Lead"** daquela tarefa. 
* Outros colegas podem ajudar discutindo soluções na Issue ou até mesmo enviando commits secundários para a sua branch, mas o Assignee é o responsável final por organizar o código, fechar o escopo e solicitar a revisão do professor.

### 4. Limite Anti-Monopólio (WIP Limit = 1)
Para evitar o bloquei de threads (que um aluno pegue simultaneamente multiplas issues), adotamos um limite de Trabalho em Progresso (*Work In Progress*).
* **Regra de Ouro:** Cada aluno só pode ter **1 (uma)** branch ativa por vez.
* Você só poderá reivindicar uma nova tarefa após ter aberto o Pull Request da sua tarefa atual e solicitado a revisão (Review) do professor. Enquanto o seu código estiver em desenvolvimento, seu foco deve ser exclusivo nessa branch.

---

## Arquitetura e Estrutura de Pastas

```text
.
├── app.py                        # Motor principal e Janela da Aplicação
├── requirements.txt              # Dependências do projeto
├── core/
│   └── plugin_base.py            # Classe abstrata que todo plugin deve herdar
└── plugins/
    ├── __init__.py               
    └── Filtros_Basicos/          # Subpastas criam submenus automaticamente!
        └── filtro_brilho.py      # Código do aluno
```

---

## 🚀 Como Rodar

Recomendamos fortemente o uso de um **Ambiente Virtual (venv)**. Isso evita conflitos com outras bibliotecas do seu computador e previne erros de permissão.

### Passo 1 — Criar o ambiente virtual

Abra o terminal na pasta raiz do projeto e rode:

```bash
python -m venv venv
```

### Passo 2 — Ativar o ambiente virtual

**No Windows (Prompt ou PowerShell):**

```bash
.\venv\Scripts\activate
```

> ⚠️ **Aviso (Erro no PowerShell):** Se o Windows bloquear a execução, rode o comando abaixo uma única vez, confirme com `S` e tente ativar de novo:
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

**No Linux ou Mac:**

```bash
source venv/bin/activate
```

*(Você saberá que deu certo quando o nome `(venv)` aparecer no início da linha do seu terminal).*

### Passo 3 — Instalar as dependências

Com o ambiente ativado, instale as bibliotecas necessárias para a interface Qt e o OpenCV funcionarem:

```bash
pip install -r requirements.txt
```

### Passo 4 — Iniciar o Studio

Agora é só rodar o motor principal:

```bash
python app.py
```

---

## 🛠️ Como Criar um novo Plugin

A mágica deste projeto é que você não precisa mexer no motor principal para adicionar ferramentas. O software lê a pasta `plugins/` e monta os menus automaticamente!

### Passo 1 — Crie a estrutura na pasta `plugins/`

Navegue até a pasta `plugins/`. Se o seu filtro pertence a uma categoria que já existe (ex: `Filtros_Basicos`), crie seu arquivo dentro dela. Se for uma categoria nova (ex: `Morfologia`), basta criar a pasta e colocar seu arquivo lá dentro. A interface criará um submenu com o nome da sua pasta.

> ⚠️ **Atenção:** Use apenas letras minúsculas, números e underscores (`_`) nos nomes dos arquivos `.py`.

### Passo 2 — Escreva o código herdando de `PluginBase`

O seu arquivo deve importar a classe base abstrata e implementar dois métodos obrigatórios: `setup_ui()` (para desenhar os controles da janela flutuante) e `processar()` (onde a matemática matricial acontece).

Aqui está um esqueleto de exemplo:

```python
import numpy as np
from PySide6.QtWidgets import QVBoxLayout, QSlider, QPushButton
from core.plugin_base import PluginBase

class MeuFiltro(PluginBase):
    # O nome que aparecerá bonito no Menu superior do programa
    display_name = "Meu Filtro Incrível" 

    def setup_ui(self):
        """Construa os botões e controles da sua janela flutuante aqui."""
        layout = QVBoxLayout(self)
        
        # Cria um slider simples
        self.meu_slider = QSlider()
        self.meu_slider.valueChanged.connect(self._ao_alterar_slider)
        layout.addWidget(self.meu_slider)
        
        # Botão de aplicar
        self.btn_aplicar = QPushButton("Aplicar")
        self.btn_aplicar.clicked.connect(self._ao_aplicar)
        layout.addWidget(self.btn_aplicar)
        
        self.setLayout(layout)

    def processar(self, imagem: np.ndarray) -> np.ndarray:
        """A mágica matemática acontece aqui (use OpenCV ou NumPy pura)."""
        valor = self.meu_slider.value()
        # Exemplo simples: somar um valor aos pixels e saturar em 255
        resultado = np.clip(imagem.astype(np.int16) + valor, 0, 255)
        return resultado.astype(np.uint8)
        
    def _ao_alterar_slider(self):
        """Envia a imagem provisória para a tela principal em tempo real."""
        img_processada = self.processar(self.imagem_original)
        self.preview_requested.emit(img_processada)
        
    def _ao_aplicar(self):
        """Confirma a alteração e fecha a janelinha do plugin."""
        img_processada = self.processar(self.imagem_original)
        self.apply_requested.emit(img_processada)
        self.accept()
```

*💡 Dica: Dê uma olhada no arquivo `plugins/filtro_brilho.py` para ver um exemplo real completo e testado!*

> ⚠️ *Atenção*: Siga nosso fluxo de trabalho e se atente para as políticas de colaboração!

## 📄 Licença

Projeto educacional — Disciplina de Processamento de Imagens — UFPA 2026.