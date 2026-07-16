import cv2
import numpy as np

def criar_mascara_retangular(shape_imagem, x, y, largura, altura):
    """
    Cria uma máscara binária do mesmo tamanho da imagem original.
    
    Parâmetros:
        shape_imagem (tuple): Formato da imagem original (altura, largura, canais).
        x, y (int): Coordenadas do ponto superior esquerdo da Bounding Box.
        largura, altura (int): Dimensões da Bounding Box.
        
    Retorna:
        np.ndarray: Máscara binária onde o fundo é 0 (preto) e a ROI é 255 (branco).
    """
    # 1. Cria uma matriz preta (zeros) com a exata resolução da imagem (apenas 1 canal/2D)
    altura_img, largura_img = shape_imagem[:2]
    mascara = np.zeros((altura_img, largura_img), dtype=np.uint8)
    
    # 2. Pinta a região selecionada (Bounding Box) com 255 (branco)
    mascara[y:y+altura, x:x+largura] = 255
    
    return mascara

def aplicar_filtro_com_mascara(imagem_original, imagem_filtrada, mascara_binaria):
    """
    Funde a imagem original e a imagem filtrada utilizando a máscara binária.
    
    Parâmetros:
        imagem_original (np.ndarray): A imagem base original (RGB).
        imagem_filtrada (np.ndarray): A imagem inteira com o filtro já aplicado (RGB).
        mascara_binaria (np.ndarray): A máscara gerada (0 para fundo, 255 para ROI).
        
    Retorna:
        np.ndarray: A imagem final composta.
    """
    # Como a imagem é RGB (3 canais) e a máscara tem 1 canal, precisamos expandir a 
    # máscara para 3 dimensões para que o NumPy consiga fazer o "Broadcasting" matemático.
    # Transformamos o 255 em 1 para usar como condição booleana.
    condicao_mascara = (mascara_binaria[:, :, np.newaxis] == 255)
    
    # A mágica do NumPy: Onde a condição for Verdadeira (dentro do ROI), usa o pixel
    # da 'imagem_filtrada'. Onde for Falsa (fundo), preserva o pixel da 'imagem_original'.
    imagem_composta = np.where(condicao_mascara, imagem_filtrada, imagem_original)
    
    return imagem_composta.astype(np.uint8)

# Exemplo de Uso Prático do Fluxo:
# 1. mascara = criar_mascara_retangular(imagem.shape, 100, 100, 200, 200)
# 2. imagem_borrada = cv2.GaussianBlur(imagem, (21, 21), 0)
# 3. imagem_final = aplicar_filtro_com_mascara(imagem, imagem_borrada, mascara)