# Manual de Uso e Configuração — Reconhecedor de Texto OCR

Este manual descreve como configurar e utilizar o novo plugin de **Reconhecimento Óptico de Caracteres (OCR)** no Studio de Processamento de Imagens.

---

## 🚀 Como Funciona o Plugin

O plugin de OCR está integrado à barra de menus em **Reconhecimento ➔ Reconhecedor de Texto OCR**. 

Diferente de leitores de texto comuns que processam a imagem inteira (o que aumenta o consumo de memória e a taxa de erro com fundos complexos), este plugin **trabalha focado em uma Região de Interesse (ROI)**. 

### Fluxo de processamento interno:
1. O usuário seleciona uma região da imagem usando a ferramenta geométrica (Bounding Box).
2. A imagem é recortada focando apenas na área selecionada.
3. No background (para não travar a interface gráfica), o recorte sofre **pré-processamento**:
   - Conversão para escala de cinza.
   - Redimensionamento inteligente (se o texto for muito pequeno).
   - Limiarização de Otsu (binarização preto e branco) para otimizar a leitura.
4. O recorte tratado é enviado ao motor do **Tesseract OCR**.
5. O texto resultante é exibido em tela com opção de cópia imediata.

---

## 🛠️ Requisitos de Instalação

Para que o plugin funcione, são necessários dois componentes: a biblioteca Python (`pytesseract`) e o motor local do Tesseract OCR.

### 1. Dependência Python
Instale as dependências do projeto atualizadas (que agora incluem o `pytesseract`):
```bash
pip install -r requirements.txt
```

### 2. Motor Tesseract OCR (Dependência do Sistema Operacional)

Você precisa ter o executável do Tesseract instalado no seu computador. Siga as instruções abaixo de acordo com seu sistema:

#### **Windows**
O plugin está configurado para localizar o Tesseract automaticamente nas pastas padrões do Windows. Instale usando uma das opções:
* **Via Terminal (PowerShell/CMD):**
  ```powershell
  winget search tesseract
  # Instale com o ID correspondente retornado, ex:
  winget install UB.TesseractOCR
  ```
* **Via Instalador Manual:**
  1. Acesse a página de instaladores do **[UB Mannheim Tesseract Wiki](https://github.com/UB-Mannheim/tesseract/wiki)**.
  2. Baixe o instalador mais recente para 64-bit (ex: `tesseract-ocr-w64-setup-...exe`).
  3. Prossiga com a instalação padrão (que instala em `C:\Program Files\Tesseract-OCR`).

#### **Linux (Ubuntu/Debian)**
Instale via gerenciador de pacotes `apt`:
```bash
sudo apt update
sudo apt install tesseract-ocr tesseract-ocr-por
```

#### **macOS**
Instale via `Homebrew`:
```bash
brew install tesseract tesseract-lang
```

---

## 📖 Passo a Passo de Uso no Studio

1. **Abra uma imagem** contendo textos no Studio (ex: uma placa de sinalização, documento ou lateral de veículo).
2. Ative a **Ferramenta de Seleção Geométrica (ROI)** na barra de ferramentas lateral esquerda (ícone de retângulo tracejado).
3. **Desenhe um retângulo** ao redor do texto que deseja ler.
4. No menu superior, clique em **Reconhecimento ➔ Reconhecedor de Texto OCR**.
5. Na janela do plugin, verifique se a resolução da região de interesse está correta e clique em **Executar OCR**.
6. Uma caixa de diálogo se abrirá mostrando o texto extraído, contendo um botão **Copiar** para enviar o resultado diretamente para a sua área de transferência.
