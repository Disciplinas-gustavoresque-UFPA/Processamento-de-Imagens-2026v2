"""Detecção geométrica de candidatos a QR Code."""

from __future__ import annotations

from itertools import combinations
from math import acos, degrees

import cv2
import numpy as np

from plugins.reconhecimento._qrcode.geometria import ordenar_cantos, versao_mais_proxima
from plugins.reconhecimento._qrcode.modelos import FinderPattern, QRCandidate


def _contar_descendentes(hierarquia: np.ndarray, indice: int, limite: int = 3) -> int:
    total = 0
    atual = hierarquia[indice][2]
    while atual != -1 and total < limite:
        total += 1
        atual = hierarquia[atual][2]
    return total


def _quadrado_score(contorno: np.ndarray) -> tuple[bool, float, tuple[float, float], float]:
    area = cv2.contourArea(contorno)
    if area < 64:
        return False, 0.0, (0.0, 0.0), 0.0

    rect = cv2.minAreaRect(contorno)
    (cx, cy), (w, h), _ = rect
    if w <= 1 or h <= 1:
        return False, 0.0, (0.0, 0.0), 0.0

    razao = min(w, h) / max(w, h)
    area_rect = w * h
    preenchimento = area / area_rect if area_rect > 0 else 0
    score = razao * min(1.0, preenchimento)
    return razao > 0.55 and preenchimento > 0.45, score, (cx, cy), max(w, h)


def detectar_finder_patterns(binaria: np.ndarray) -> list[FinderPattern]:
    """
    Detecta padroes localizadores por hierarquia de contornos.

    A imagem binária deve ter fundo claro e módulos escuros. A função inverte
    internamente para encontrar regiões pretas como objetos.
    """
    objetos_escuros = cv2.bitwise_not(binaria)
    contornos, hier = cv2.findContours(
        objetos_escuros, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
    )
    if hier is None:
        return []
    hierarquia = hier[0]
    candidatos: list[FinderPattern] = []

    for i, contorno in enumerate(contornos):
        if _contar_descendentes(hierarquia, i) < 2:
            continue

        child = hierarquia[i][2]
        grandchild = hierarquia[child][2] if child != -1 else -1
        if child == -1 or grandchild == -1:
            continue

        ok, score_quadrado, centro, tamanho = _quadrado_score(contorno)
        if not ok:
            continue

        area0 = max(1.0, cv2.contourArea(contorno))
        area1 = cv2.contourArea(contornos[child])
        area2 = cv2.contourArea(contornos[grandchild])
        r1 = area1 / area0
        r2 = area2 / max(1.0, area1)
        score_razao = 1.0 - min(1.0, abs(r1 - 0.50) + abs(r2 - 0.36))
        score = max(0.0, score_quadrado * 0.55 + score_razao * 0.45)
        if score < 0.35:
            continue

        candidatos.append(FinderPattern(centro, tamanho, score, contorno))

    candidatos.sort(key=lambda item: item.score * item.size, reverse=True)
    return _remover_finders_duplicados(candidatos)


def _remover_finders_duplicados(candidatos: list[FinderPattern]) -> list[FinderPattern]:
    filtrados: list[FinderPattern] = []
    for cand in candidatos:
        cx, cy = cand.center
        duplicado = False
        for existente in filtrados:
            ex, ey = existente.center
            dist = ((cx - ex) ** 2 + (cy - ey) ** 2) ** 0.5
            if dist < max(6.0, min(cand.size, existente.size) * 0.45):
                duplicado = True
                break
        if not duplicado:
            filtrados.append(cand)
    return filtrados[:18]


def _angulo(v1: np.ndarray, v2: np.ndarray) -> float:
    n1 = np.linalg.norm(v1)
    n2 = np.linalg.norm(v2)
    if n1 == 0 or n2 == 0:
        return 0.0
    cosv = float(np.clip(np.dot(v1, v2) / (n1 * n2), -1.0, 1.0))
    return degrees(acos(cosv))


def _ordenar_trio(finders: tuple[FinderPattern, FinderPattern, FinderPattern]):
    pts = [np.array(f.center, dtype=np.float32) for f in finders]
    melhor_idx = 0
    melhor_delta = 999.0
    for i in range(3):
        outros = [pts[j] for j in range(3) if j != i]
        delta = abs(_angulo(outros[0] - pts[i], outros[1] - pts[i]) - 90.0)
        if delta < melhor_delta:
            melhor_delta = delta
            melhor_idx = i

    tl = pts[melhor_idx]
    outros = [pts[j] for j in range(3) if j != melhor_idx]
    a = outros[0] - tl
    b = outros[1] - tl
    cross = a[0] * b[1] - a[1] * b[0]
    if cross > 0:
        tr, bl = outros[0], outros[1]
    else:
        tr, bl = outros[1], outros[0]
    return tl, tr, bl, melhor_delta


def _cantos_por_finders(
    tl: np.ndarray,
    tr: np.ndarray,
    bl: np.ndarray,
    modulo: float,
    dimensao: int,
) -> np.ndarray:
    eixo_x = tr - tl
    eixo_y = bl - tl
    eixo_x = eixo_x / max(1e-6, np.linalg.norm(eixo_x))
    eixo_y = eixo_y / max(1e-6, np.linalg.norm(eixo_y))

    canto_tl = tl - 3.5 * modulo * eixo_x - 3.5 * modulo * eixo_y
    canto_tr = tl + (dimensao - 3.5) * modulo * eixo_x - 3.5 * modulo * eixo_y
    canto_bl = tl - 3.5 * modulo * eixo_x + (dimensao - 3.5) * modulo * eixo_y
    canto_br = tl + (dimensao - 3.5) * modulo * eixo_x + (dimensao - 3.5) * modulo * eixo_y
    return np.array([canto_tl, canto_tr, canto_br, canto_bl], dtype=np.float32)


def candidatos_por_finders(
    finders: list[FinderPattern],
    nome_fonte: str,
    max_versao: int = 40,
    cantos_casco: np.ndarray | None = None,
) -> list[QRCandidate]:
    candidatos: list[QRCandidate] = []
    for trio in combinations(finders, 3):
        tl, tr, bl, delta_angulo = _ordenar_trio(trio)
        if delta_angulo > 28:
            continue

        dist_x = float(np.linalg.norm(tr - tl))
        dist_y = float(np.linalg.norm(bl - tl))
        if dist_x < 12 or dist_y < 12:
            continue

        razao_dist = min(dist_x, dist_y) / max(dist_x, dist_y)
        if razao_dist < 0.45:
            continue

        modulo = float(np.mean([f.size for f in trio]) / 7.0)
        if modulo <= 0:
            continue
        dim_estimada = ((dist_x + dist_y) / 2.0) / modulo + 7.0
        versao_base = versao_mais_proxima(dim_estimada)
        if versao_base > max_versao:
            continue

        score_finders = sum(f.score for f in trio) / 3.0
        score_geom = max(0.0, 1.0 - delta_angulo / 28.0) * razao_dist
        score = score_finders * 0.65 + score_geom * 0.35

        for versao in range(max(1, versao_base - 1), min(max_versao, versao_base + 1) + 1):
            dimensao = 21 + 4 * (versao - 1)
            cantos = _cantos_por_finders(tl, tr, bl, modulo, dimensao)
            candidatos.append(QRCandidate(cantos, score, nome_fonte, versao))
            if cantos_casco is not None:
                candidatos.append(
                    QRCandidate(
                        _cantos_por_homografia(tl, tr, bl, cantos_casco[2], dimensao),
                        min(1.0, score + 0.08),
                        f"{nome_fonte}_homografia",
                        versao,
                    )
                )

    candidatos.sort(key=lambda item: item.score, reverse=True)
    return _remover_candidatos_duplicados(candidatos)


def _cantos_por_homografia(
    tl: np.ndarray,
    tr: np.ndarray,
    bl: np.ndarray,
    br_canto: np.ndarray,
    dimensao: int,
) -> np.ndarray:
    """Estima os cantos do QR com 3 centros de finder + canto BR do casco."""
    destino_modulos = np.array(
        [
            [3.5, 3.5],
            [dimensao - 3.5, 3.5],
            [3.5, dimensao - 3.5],
            [dimensao, dimensao],
        ],
        dtype=np.float32,
    )
    origem_imagem = np.array([tl, tr, bl, br_canto], dtype=np.float32)
    matriz = cv2.getPerspectiveTransform(destino_modulos, origem_imagem)
    cantos_modulos = np.array(
        [[[0, 0], [dimensao, 0], [dimensao, dimensao], [0, dimensao]]],
        dtype=np.float32,
    )
    return cv2.perspectiveTransform(cantos_modulos, matriz)[0]


def candidatos_por_bbox(binaria: np.ndarray, nome_fonte: str, max_versao: int = 40) -> list[QRCandidate]:
    """Fallback para QR ja recortado ou com poucos contornos detectaveis."""
    escuros = cv2.bitwise_not(binaria)
    pontos = cv2.findNonZero(escuros)
    if pontos is None:
        return []
    x, y, w, h = cv2.boundingRect(pontos)
    if w < 18 or h < 18:
        return []
    cobertura = (w * h) / float(binaria.shape[0] * binaria.shape[1])
    if cobertura > 0.98:
        return []

    margem = 0
    # O retângulo do OpenCV fica em coordenadas de pixels. Subtrair 0.5
    # coloca os cantos na borda externa dos módulos, não no centro do pixel
    # de borda. Isso faz muita diferença em QR pequeno ou já recortado.
    x0 = max(0.0, x - margem - 0.5)
    y0 = max(0.0, y - margem - 0.5)
    x1 = min(float(binaria.shape[1] - 1), x + w + margem - 0.5)
    y1 = min(float(binaria.shape[0] - 1), y + h + margem - 0.5)
    cantos = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], dtype=np.float32)
    return [QRCandidate(cantos, 0.62, f"{nome_fonte}_bbox", None)]


def _obter_cantos_casco(binaria: np.ndarray) -> np.ndarray | None:
    escuros = cv2.bitwise_not(binaria)
    pontos = cv2.findNonZero(escuros)
    if pontos is None or len(pontos) < 80:
        return None

    x, y, w, h = cv2.boundingRect(pontos)
    cobertura = (w * h) / float(binaria.shape[0] * binaria.shape[1])
    if cobertura > 0.94 or w < 18 or h < 18:
        return None

    hull = cv2.convexHull(pontos)
    perimetro = cv2.arcLength(hull, True)
    approx = None
    for eps in (0.02, 0.035, 0.05, 0.08):
        candidato = cv2.approxPolyDP(hull, eps * perimetro, True)
        if len(candidato) == 4:
            approx = candidato.reshape(4, 2).astype(np.float32)
            break

    if approx is None:
        rect = cv2.minAreaRect(pontos)
        approx = cv2.boxPoints(rect).astype(np.float32)

    cantos = ordenar_cantos(approx)
    centro = cantos.mean(axis=0)
    return centro + (cantos - centro) * 1.04


def candidatos_por_casco(binaria: np.ndarray, nome_fonte: str, max_versao: int = 40) -> list[QRCandidate]:
    """Hipótese pelo casco convexo dos módulos escuros."""
    cantos = _obter_cantos_casco(binaria)
    if cantos is None:
        return []
    return [QRCandidate(cantos, 0.32, f"{nome_fonte}_casco", None)]


def detectar_candidatos(
    binaria: np.ndarray,
    nome_fonte: str,
    max_versao: int = 40,
) -> list[QRCandidate]:
    finders = detectar_finder_patterns(binaria)
    cantos_casco = _obter_cantos_casco(binaria)
    candidatos = candidatos_por_finders(
        finders,
        nome_fonte,
        max_versao=max_versao,
        cantos_casco=cantos_casco,
    )
    candidatos.extend(candidatos_por_casco(binaria, nome_fonte, max_versao=max_versao))
    candidatos.extend(candidatos_por_bbox(binaria, nome_fonte, max_versao=max_versao))
    candidatos.sort(key=lambda item: item.score, reverse=True)
    return _remover_candidatos_duplicados(candidatos)[:40]


def _remover_candidatos_duplicados(candidatos: list[QRCandidate]) -> list[QRCandidate]:
    filtrados: list[QRCandidate] = []
    for cand in candidatos:
        centro = cand.corners.mean(axis=0)
        duplicado = False
        for existente in filtrados:
            centro_ex = existente.corners.mean(axis=0)
            if (
                cand.version_hint == existente.version_hint
                and cand.source_name == existente.source_name
                and np.linalg.norm(centro - centro_ex) < 8
            ):
                duplicado = True
                break
        if not duplicado:
            filtrados.append(cand)
    return filtrados
