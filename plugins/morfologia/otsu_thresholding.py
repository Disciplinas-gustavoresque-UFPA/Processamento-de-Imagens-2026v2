import cv2
import numpy as np
from core.plugin_base import PluginBase 

class OtsuThresholding(PluginBase):
    def __init__(self):
        super().__init__()
        self.name = "Limiarização de Otsu"
        self.description = "Binariza a imagem calculando o limiar ideal automaticamente pelo método de Otsu."

    def setup_ui(self):
        # Se quiser caprichar (e buscar a badge UI/UX Master), você pode adicionar 
        # um CheckBox aqui perguntando se o usuário quer "Inverter Cores" (fundo preto/objeto branco).
        pass

    def processar(self, imagem_np, parametros):
        # 1. O Otsu exige que a imagem esteja em tons de cinza (1 canal)
        if len(imagem_np.shape) == 3:
            imagem_cinza = cv2.cvtColor(imagem_np, cv2.COLOR_BGR2GRAY)
        else:
            imagem_cinza = imagem_np
            
        # 2. Aplica o limiar de Otsu
        # O OpenCV retorna dois valores: o limiar calculado (t_ideal) e a imagem binarizada
        t_ideal, imagem_binaria = cv2.threshold(imagem_cinza, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Opcional: imprimir o limiar no console para fins de debug
        print(f"Limiar ideal calculado por Otsu: {t_ideal}")

        # 3. Retorna a imagem final para a interface (e converte de volta para BGR se a interface exigir)
        return cv2.cvtColor(imagem_binaria, cv2.COLOR_GRAY2BGR)