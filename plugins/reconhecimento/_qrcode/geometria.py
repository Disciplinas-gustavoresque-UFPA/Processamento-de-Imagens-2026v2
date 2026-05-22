"""Geometria, homografia e amostragem da grade do QR Code."""

from __future__ import annotations

import cv2
import numpy as np


def dimensao_da_versao(versao: int) -> int:
    return 21 + 4 * (versao - 1)


def versao_da_dimensao(dim: int) -> int | None:
    if dim < 21 or (dim - 21) % 4 != 0:
        return None
    versao = ((dim - 21) // 4) + 1
    if 1 <= versao <= 40:
        return versao
    return None


def versao_mais_proxima(dim_estimada: float) -> int:
    versao = int(round((dim_estimada - 21) / 4 + 1))
    return max(1, min(40, versao))


def ordenar_cantos(cantos: np.ndarray) -> np.ndarray:
    """Ordena cantos como TL, TR, BR, BL."""
    pontos = np.asarray(cantos, dtype=np.float32)
    soma = pontos.sum(axis=1)
    diff = np.diff(pontos, axis=1).reshape(-1)

    tl = pontos[np.argmin(soma)]
    br = pontos[np.argmax(soma)]
    tr = pontos[np.argmin(diff)]
    bl = pontos[np.argmax(diff)]
    return np.array([tl, tr, br, bl], dtype=np.float32)


def warp_para_grade(
    imagem_rgb: np.ndarray,
    cantos: np.ndarray,
    dimensao: int,
    escala_modulo: int = 8,
) -> np.ndarray:
    """Achata a região candidata para uma imagem quadrada normalizada."""
    tamanho = dimensao * escala_modulo
    destino = np.array(
        [[0, 0], [tamanho - 1, 0], [tamanho - 1, tamanho - 1], [0, tamanho - 1]],
        dtype=np.float32,
    )
    matriz = cv2.getPerspectiveTransform(ordenar_cantos(cantos), destino)
    return cv2.warpPerspective(imagem_rgb, matriz, (tamanho, tamanho))


def amostrar_grade(imagem_warp_rgb: np.ndarray, dimensao: int) -> np.ndarray:
    """
    Amostra o centro de cada modulo e devolve matriz booleana.

    True significa modulo escuro.
    """
    cinza = cv2.cvtColor(imagem_warp_rgb, cv2.COLOR_RGB2GRAY)
    escala = cinza.shape[0] / dimensao
    grade = np.zeros((dimensao, dimensao), dtype=bool)

    for y in range(dimensao):
        for x in range(dimensao):
            cx = int((x + 0.5) * escala)
            cy = int((y + 0.5) * escala)
            raio = max(1, int(escala * 0.22))
            y0 = max(0, cy - raio)
            y1 = min(cinza.shape[0], cy + raio + 1)
            x0 = max(0, cx - raio)
            x1 = min(cinza.shape[1], cx + raio + 1)
            grade[y, x] = np.median(cinza[y0:y1, x0:x1]) < 128

    return grade


def desenhar_grade(grade: np.ndarray, escala: int = 8) -> np.ndarray:
    """Cria imagem RGB visualizando a grade binaria."""
    img = np.where(grade, 0, 255).astype(np.uint8)
    img = cv2.resize(img, (grade.shape[1] * escala, grade.shape[0] * escala), interpolation=cv2.INTER_NEAREST)
    return cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
