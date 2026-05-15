"""Modelos de dados usados pelo leitor de QR Code."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass(frozen=True)
class FinderPattern:
    """Candidato a padrão localizador do QR Code."""

    center: tuple[float, float]
    size: float
    score: float
    contour: np.ndarray | None = field(default=None, compare=False)


@dataclass(frozen=True)
class QRCandidate:
    """Hipótese geométrica para uma região de QR Code."""

    corners: np.ndarray
    score: float
    source_name: str
    version_hint: int | None = None


@dataclass
class QRReadResult:
    """Resultado final da leitura."""

    text: str
    version: int
    error_level: str
    mask: int
    corrected_errors: int
    candidate_name: str
    annotated_image: np.ndarray
    grid: np.ndarray
    attempts: int
    corners: np.ndarray
