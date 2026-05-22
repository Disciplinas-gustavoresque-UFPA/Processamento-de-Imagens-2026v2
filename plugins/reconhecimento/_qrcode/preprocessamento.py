"""Pré-processamento de baixo nível para detectar QR Codes."""

from __future__ import annotations

import cv2
import numpy as np


def para_cinza(imagem_rgb: np.ndarray) -> np.ndarray:
    """Converte RGB para escala de cinza."""
    return cv2.cvtColor(imagem_rgb, cv2.COLOR_RGB2GRAY)


def normalizar_contraste(cinza: np.ndarray) -> np.ndarray:
    """Aumenta contraste local sem destruir bordas fortes."""
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(cinza)


def gerar_binarizacoes(imagem_rgb: np.ndarray) -> list[tuple[str, np.ndarray]]:
    """
    Gera várias hipóteses binárias.

    O decodificador tenta todas. Isso deixa a leitura mais tolerante a sombras,
    fundo irregular e QR invertido.
    """
    cinza = para_cinza(imagem_rgb)
    contraste = normalizar_contraste(cinza)
    blur = cv2.GaussianBlur(contraste, (3, 3), 0)

    variantes: list[tuple[str, np.ndarray]] = []

    _, otsu = cv2.threshold(
        blur, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU
    )
    variantes.append(("otsu", otsu))
    variantes.append(("otsu_invertido", cv2.bitwise_not(otsu)))

    for bloco in (21, 31, 41):
        adapt = cv2.adaptiveThreshold(
            blur,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            bloco,
            5,
        )
        variantes.append((f"adaptativo_{bloco}", adapt))
        variantes.append((f"adaptativo_{bloco}_invertido", cv2.bitwise_not(adapt)))

    kernel = np.ones((3, 3), np.uint8)
    refinadas: list[tuple[str, np.ndarray]] = []
    for nome, binaria in variantes:
        refinadas.append((nome, binaria))
        refinadas.append((f"{nome}_open", cv2.morphologyEx(binaria, cv2.MORPH_OPEN, kernel)))
        refinadas.append((f"{nome}_close", cv2.morphologyEx(binaria, cv2.MORPH_CLOSE, kernel)))

    return refinadas
