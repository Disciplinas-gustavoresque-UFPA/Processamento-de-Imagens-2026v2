"""
core/compressao_imagem.py
-------------------------
Módulo de análise de compressão de imagens.

Implementa a codificação de Huffman sobre a matriz de pixels e compara
o resultado com as compressões JPEG e PNG via OpenCV.

Funcionalidades
---------------
* Construção da árvore de Huffman a partir das frequências dos pixels.
* Cálculo de entropia e redundância dos dados.
* Compressão simulada via Huffman (tamanho do bitstream).
* Compressão real via JPEG (``cv2.imencode``) com qualidade configurável.
* Compressão real via PNG (``cv2.imencode``).
* Função unificada ``analisar_compressao`` que retorna todos os resultados.
"""

from __future__ import annotations

import heapq
import math
import struct
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

import cv2
import numpy as np


# ---------------------------------------------------------------------------
# Árvore de Huffman
# ---------------------------------------------------------------------------

@dataclass(order=True)
class NoHuffman:
    """Nó da árvore de Huffman, comparável por frequência."""

    frequencia: int
    simbolo: int | None = field(default=None, compare=False)
    esquerda: "NoHuffman | None" = field(default=None, compare=False)
    direita: "NoHuffman | None" = field(default=None, compare=False)


def construir_arvore_huffman(frequencias: dict[int, int]) -> NoHuffman:
    """
    Constrói a árvore de Huffman a partir de um dicionário de frequências.

    Parâmetros
    ----------
    frequencias : dict[int, int]
        Mapeamento símbolo → contagem de ocorrências.

    Retorna
    -------
    NoHuffman
        Raiz da árvore de Huffman.
    """
    if not frequencias:
        return NoHuffman(frequencia=0)

    heap: list[NoHuffman] = [
        NoHuffman(frequencia=freq, simbolo=simbolo)
        for simbolo, freq in frequencias.items()
    ]
    heapq.heapify(heap)

    # Caso especial: apenas um símbolo distinto.
    if len(heap) == 1:
        unico = heapq.heappop(heap)
        raiz = NoHuffman(
            frequencia=unico.frequencia,
            esquerda=unico,
        )
        return raiz

    while len(heap) > 1:
        esquerda = heapq.heappop(heap)
        direita = heapq.heappop(heap)
        pai = NoHuffman(
            frequencia=esquerda.frequencia + direita.frequencia,
            esquerda=esquerda,
            direita=direita,
        )
        heapq.heappush(heap, pai)

    return heap[0]


def gerar_codigos_huffman(raiz: NoHuffman) -> dict[int, str]:
    """
    Percorre a árvore e gera o dicionário símbolo → código binário.

    Parâmetros
    ----------
    raiz : NoHuffman
        Raiz da árvore de Huffman.

    Retorna
    -------
    dict[int, str]
        Mapeamento símbolo → string de bits (ex.: ``{0: '00', 128: '1', ...}``).
    """
    codigos: dict[int, str] = {}

    def _percorrer(no: NoHuffman | None, prefixo: str) -> None:
        if no is None:
            return
        if no.simbolo is not None:
            codigos[no.simbolo] = prefixo or "0"
            return
        _percorrer(no.esquerda, prefixo + "0")
        _percorrer(no.direita, prefixo + "1")

    _percorrer(raiz, "")
    return codigos


# ---------------------------------------------------------------------------
# Métricas de informação
# ---------------------------------------------------------------------------

def calcular_entropia(frequencias: dict[int, int], total: int) -> float:
    """
    Calcula a entropia de Shannon (bits por símbolo).

    H = -Σ p(x) · log₂(p(x))
    """
    if total == 0:
        return 0.0

    entropia = 0.0
    for freq in frequencias.values():
        if freq > 0:
            p = freq / total
            entropia -= p * math.log2(p)
    return entropia


def calcular_redundancia(entropia: float, bits_por_simbolo: int = 8) -> float:
    """
    Calcula a redundância dos dados.

    R = 1 − (H / L)

    Onde *H* é a entropia e *L* são os bits por símbolo no formato original.
    """
    if bits_por_simbolo == 0:
        return 0.0
    return 1.0 - (entropia / bits_por_simbolo)


# ---------------------------------------------------------------------------
# Compressão Huffman
# ---------------------------------------------------------------------------

def comprimir_huffman(imagem_bgr: np.ndarray) -> dict[str, Any]:
    """
    Aplica a codificação de Huffman sobre os valores de pixel da imagem.

    Parâmetros
    ----------
    imagem_bgr : np.ndarray
        Imagem em formato BGR (OpenCV).

    Retorna
    -------
    dict
        Dicionário com as chaves:
        - ``tamanho_original``  : int — tamanho bruto em bytes.
        - ``tamanho_comprimido``: int — tamanho estimado do bitstream em bytes.
        - ``total_bits``        : int — total de bits do bitstream.
        - ``entropia``          : float — entropia de Shannon (bits/símbolo).
        - ``redundancia``       : float — redundância (0–1).
        - ``taxa_compressao``   : float — razão original / comprimido.
        - ``economia_percentual``: float — percentual de redução.
        - ``tabela_codigos``    : dict — primeiros 20 códigos Huffman.
    """
    pixels = imagem_bgr.flatten().astype(np.uint8)
    total_pixels = len(pixels)

    tamanho_original = total_pixels  # cada pixel ocupa 1 byte

    # Contagem de frequências
    frequencias = dict(Counter(pixels.tolist()))

    # Entropia e redundância
    entropia = calcular_entropia(frequencias, total_pixels)
    redundancia = calcular_redundancia(entropia)

    # Árvore e códigos
    arvore = construir_arvore_huffman(frequencias)
    codigos = gerar_codigos_huffman(arvore)

    # Tamanho do bitstream comprimido
    total_bits = sum(
        frequencias[simbolo] * len(codigo)
        for simbolo, codigo in codigos.items()
    )
    tamanho_comprimido = math.ceil(total_bits / 8)

    # Taxa de compressão
    taxa = tamanho_original / tamanho_comprimido if tamanho_comprimido > 0 else 0
    economia = (1 - tamanho_comprimido / tamanho_original) * 100 if tamanho_original > 0 else 0

    # Amostra da tabela de códigos (os 20 mais frequentes)
    codigos_ordenados = sorted(codigos.items(), key=lambda x: frequencias.get(x[0], 0), reverse=True)
    tabela_amostra = dict(codigos_ordenados[:20])

    return {
        "tamanho_original": tamanho_original,
        "tamanho_comprimido": tamanho_comprimido,
        "total_bits": total_bits,
        "entropia": entropia,
        "redundancia": redundancia,
        "taxa_compressao": taxa,
        "economia_percentual": economia,
        "tabela_codigos": tabela_amostra,
    }


# ---------------------------------------------------------------------------
# Compressão JPEG / PNG (via OpenCV)
# ---------------------------------------------------------------------------

def comprimir_jpeg(imagem_bgr: np.ndarray, qualidade: int = 95) -> dict[str, Any]:
    """
    Codifica a imagem como JPEG e retorna o tamanho resultante.

    Parâmetros
    ----------
    imagem_bgr : np.ndarray
        Imagem em formato BGR.
    qualidade : int
        Qualidade JPEG (0–100). Padrão: 95.

    Retorna
    -------
    dict
        Dicionário com ``tamanho_comprimido``, ``economia_percentual`` e
        ``taxa_compressao``.
    """
    tamanho_original = imagem_bgr.nbytes

    parametros = [cv2.IMWRITE_JPEG_QUALITY, qualidade]
    sucesso, buffer = cv2.imencode(".jpg", imagem_bgr, parametros)

    if not sucesso:
        return {
            "tamanho_comprimido": 0,
            "economia_percentual": 0.0,
            "taxa_compressao": 0.0,
        }

    tamanho_comprimido = len(buffer)
    economia = (1 - tamanho_comprimido / tamanho_original) * 100 if tamanho_original > 0 else 0
    taxa = tamanho_original / tamanho_comprimido if tamanho_comprimido > 0 else 0

    return {
        "tamanho_comprimido": tamanho_comprimido,
        "economia_percentual": economia,
        "taxa_compressao": taxa,
    }


def comprimir_png(imagem_bgr: np.ndarray) -> dict[str, Any]:
    """
    Codifica a imagem como PNG e retorna o tamanho resultante.

    Parâmetros
    ----------
    imagem_bgr : np.ndarray
        Imagem em formato BGR.

    Retorna
    -------
    dict
        Dicionário com ``tamanho_comprimido``, ``economia_percentual`` e
        ``taxa_compressao``.
    """
    tamanho_original = imagem_bgr.nbytes

    sucesso, buffer = cv2.imencode(".png", imagem_bgr)

    if not sucesso:
        return {
            "tamanho_comprimido": 0,
            "economia_percentual": 0.0,
            "taxa_compressao": 0.0,
        }

    tamanho_comprimido = len(buffer)
    economia = (1 - tamanho_comprimido / tamanho_original) * 100 if tamanho_original > 0 else 0
    taxa = tamanho_original / tamanho_comprimido if tamanho_comprimido > 0 else 0

    return {
        "tamanho_comprimido": tamanho_comprimido,
        "economia_percentual": economia,
        "taxa_compressao": taxa,
    }


# ---------------------------------------------------------------------------
# Análise unificada
# ---------------------------------------------------------------------------

def analisar_compressao(imagem_bgr: np.ndarray) -> dict[str, Any]:
    """
    Executa todas as análises de compressão e retorna um dicionário consolidado.

    Parâmetros
    ----------
    imagem_bgr : np.ndarray
        Imagem em formato BGR (OpenCV).

    Retorna
    -------
    dict
        Chaves: ``dimensoes``, ``canais``, ``tamanho_original``,
        ``huffman``, ``jpeg``, ``png``.
    """
    altura, largura = imagem_bgr.shape[:2]
    canais = imagem_bgr.shape[2] if imagem_bgr.ndim == 3 else 1
    tamanho_original = imagem_bgr.nbytes

    return {
        "dimensoes": (largura, altura),
        "canais": canais,
        "tamanho_original": tamanho_original,
        "huffman": comprimir_huffman(imagem_bgr),
        "jpeg": comprimir_jpeg(imagem_bgr),
        "png": comprimir_png(imagem_bgr),
    }


def salvar_arquivo_huffman(imagem_bgr: np.ndarray, caminho_saida: str) -> None:
    """
    Gera e salva o arquivo compactado no formato proprietário .huff.
    """
    altura, largura = imagem_bgr.shape[:2]
    canais = imagem_bgr.shape[2] if imagem_bgr.ndim == 3 else 1
    
    pixels = imagem_bgr.flatten().astype(np.uint8)
    frequencias = dict(Counter(pixels.tolist()))
    
    arvore = construir_arvore_huffman(frequencias)
    codigos = gerar_codigos_huffman(arvore)
    
    # Construir bitstream
    lista_bits = []
    for p in pixels:
        lista_bits.append(codigos[p])
    bitstream_str = "".join(lista_bits)
    total_bits = len(bitstream_str)
    
    # Converter string de bits para bytes
    buffer_bytes = bytearray()
    for i in range(0, total_bits, 8):
        byte_str = bitstream_str[i:i+8]
        if len(byte_str) < 8:
            byte_str = byte_str.ljust(8, '0')  # Padding com zeros à direita
        buffer_bytes.append(int(byte_str, 2))
        
    # Salvar em formato binário estruturado
    with open(caminho_saida, "wb") as f:
        # Magic header
        f.write(b"HUFF")
        # Metadados: largura (I), altura (I), canais (B)
        f.write(struct.pack(">IIB", largura, altura, canais))
        # Tabela de frequências: tamanho da tabela (H)
        f.write(struct.pack(">H", len(frequencias)))
        for simbolo, freq in frequencias.items():
            f.write(struct.pack(">BI", simbolo, freq))
        # Total de bits úteis (Q)
        f.write(struct.pack(">Q", total_bits))
        # Dados comprimidos
        f.write(buffer_bytes)
