"""Decodificador de QR Code: formato, máscara, codewords e texto."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from plugins.reconhecimento._qrcode.geometria import versao_da_dimensao
from plugins.reconhecimento._qrcode.reed_solomon import ReedSolomonError, corrigir_msg
from plugins.reconhecimento._qrcode.tabelas import (
    ALIGNMENT_POSITIONS,
    ALPHANUMERIC,
    EC_BLOCKS,
    ERROR_LEVEL_NAMES,
)


class QRDecodeError(Exception):
    """Falha de decodificação do QR Code."""


@dataclass
class DecodedQR:
    text: str
    version: int
    error_level: str
    mask: int
    corrected_errors: int


def _bch_remainder(valor: int, gerador: int, grau: int) -> int:
    valor <<= grau
    while valor.bit_length() - 1 >= grau:
        shift = (valor.bit_length() - 1) - grau
        valor ^= gerador << shift
    return valor


def _format_codewords_validos() -> list[tuple[int, str, int]]:
    validos: list[tuple[int, str, int]] = []
    for ec_bits, nome in ERROR_LEVEL_NAMES.items():
        for mascara in range(8):
            dados = (ec_bits << 3) | mascara
            bch = _bch_remainder(dados, 0x537, 10)
            codigo = ((dados << 10) | bch) ^ 0x5412
            validos.append((codigo, nome, mascara))
    return validos


FORMAT_VALIDOS = _format_codewords_validos()


def _hamming(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def _ler_bits_posicoes(grade: np.ndarray, posicoes: list[tuple[int, int]]) -> int:
    valor = 0
    for y, x in posicoes:
        valor = (valor << 1) | int(bool(grade[y, x]))
    return valor


def _ler_formato(grade: np.ndarray) -> tuple[str, int]:
    dim = grade.shape[0]
    pos1 = (
        [(8, i) for i in range(6)]
        + [(8, 7), (8, 8), (7, 8)]
        + [(i, 8) for i in range(5, -1, -1)]
    )
    pos2 = (
        [(8, i) for i in range(dim - 1, dim - 8, -1)]
        + [(i, 8) for i in range(dim - 8, dim)]
    )
    lidos = [_ler_bits_posicoes(grade, pos1), _ler_bits_posicoes(grade, pos2)]

    melhor: tuple[int, str, int] | None = None
    melhor_dist = 16
    for lido in lidos:
        for codigo, nivel, mascara in FORMAT_VALIDOS:
            dist = _hamming(lido, codigo)
            if dist < melhor_dist:
                melhor_dist = dist
                melhor = (codigo, nivel, mascara)

    if melhor is None or melhor_dist > 3:
        raise QRDecodeError("informação de formato inválida")
    return melhor[1], melhor[2]


def _mascara_reservados(versao: int, dim: int) -> np.ndarray:
    reservado = np.zeros((dim, dim), dtype=bool)

    def marcar_ret(y0: int, x0: int, y1: int, x1: int) -> None:
        reservado[max(0, y0):min(dim, y1), max(0, x0):min(dim, x1)] = True

    marcar_ret(0, 0, 9, 9)
    marcar_ret(0, dim - 8, 9, dim)
    marcar_ret(dim - 8, 0, dim, 9)

    reservado[6, :] = True
    reservado[:, 6] = True

    reservado[8, 0:9] = True
    reservado[0:9, 8] = True
    reservado[8, dim - 8:dim] = True
    reservado[dim - 8:dim, 8] = True

    if 0 <= 4 * versao + 9 < dim:
        reservado[4 * versao + 9, 8] = True

    for y in ALIGNMENT_POSITIONS.get(versao, []):
        for x in ALIGNMENT_POSITIONS.get(versao, []):
            perto_finder = (
                (x <= 8 and y <= 8)
                or (x >= dim - 9 and y <= 8)
                or (x <= 8 and y >= dim - 9)
            )
            if not perto_finder:
                marcar_ret(y - 2, x - 2, y + 3, x + 3)

    if versao >= 7:
        marcar_ret(0, dim - 11, 6, dim - 8)
        marcar_ret(dim - 11, 0, dim - 8, 6)

    return reservado


def _mask_bit(mask: int, row: int, col: int) -> bool:
    if mask == 0:
        return (row + col) % 2 == 0
    if mask == 1:
        return row % 2 == 0
    if mask == 2:
        return col % 3 == 0
    if mask == 3:
        return (row + col) % 3 == 0
    if mask == 4:
        return ((row // 2) + (col // 3)) % 2 == 0
    if mask == 5:
        return ((row * col) % 2 + (row * col) % 3) == 0
    if mask == 6:
        return (((row * col) % 2 + (row * col) % 3) % 2) == 0
    if mask == 7:
        return (((row + col) % 2 + (row * col) % 3) % 2) == 0
    raise QRDecodeError("máscara inválida")


def _extrair_codewords(grade: np.ndarray, versao: int, mascara: int) -> list[int]:
    dim = grade.shape[0]
    reservado = _mascara_reservados(versao, dim)
    bits: list[int] = []

    subindo = True
    col = dim - 1
    while col > 0:
        if col == 6:
            col -= 1
        linhas = range(dim - 1, -1, -1) if subindo else range(dim)
        for row in linhas:
            for c in (col, col - 1):
                if reservado[row, c]:
                    continue
                bit = bool(grade[row, c])
                if _mask_bit(mascara, row, c):
                    bit = not bit
                bits.append(int(bit))
        subindo = not subindo
        col -= 2

    codewords: list[int] = []
    for i in range(0, len(bits) - 7, 8):
        valor = 0
        for bit in bits[i:i + 8]:
            valor = (valor << 1) | bit
        codewords.append(valor)
    return codewords


def _blocos_estrutura(versao: int, nivel: str) -> tuple[int, list[int]]:
    if versao not in EC_BLOCKS or nivel not in EC_BLOCKS[versao]:
        raise QRDecodeError("versão acima do suporte atual do decodificador")
    ec_por_bloco, grupos = EC_BLOCKS[versao][nivel]
    tamanhos: list[int] = []
    for quantidade, dados in grupos:
        tamanhos.extend([dados] * quantidade)
    return ec_por_bloco, tamanhos


def _deintercalar_corrigir(
    codewords: list[int], versao: int, nivel: str
) -> tuple[list[int], int]:
    ec_por_bloco, tamanhos_dados = _blocos_estrutura(versao, nivel)
    total_esperado = sum(tamanhos_dados) + ec_por_bloco * len(tamanhos_dados)
    if len(codewords) < total_esperado:
        raise QRDecodeError("palavras de código insuficientes")
    codewords = codewords[:total_esperado]

    blocos = [[] for _ in tamanhos_dados]
    indice = 0
    for pos in range(max(tamanhos_dados)):
        for i, tamanho in enumerate(tamanhos_dados):
            if pos < tamanho:
                blocos[i].append(codewords[indice])
                indice += 1

    ecs = [[] for _ in tamanhos_dados]
    for pos in range(ec_por_bloco):
        for i in range(len(tamanhos_dados)):
            ecs[i].append(codewords[indice])
            indice += 1

    dados_corrigidos: list[int] = []
    total_corrigidos = 0
    for dados, ec in zip(blocos, ecs):
        try:
            corrigido, qtd = corrigir_msg(dados + ec, ec_por_bloco)
        except ReedSolomonError as erro:
            raise QRDecodeError(str(erro)) from erro
        dados_corrigidos.extend(corrigido[:len(dados)])
        total_corrigidos += qtd

    return dados_corrigidos, total_corrigidos


class BitStream:
    def __init__(self, dados: list[int]):
        self.bits: list[int] = []
        for byte in dados:
            for shift in range(7, -1, -1):
                self.bits.append((byte >> shift) & 1)
        self.pos = 0

    def restante(self) -> int:
        return len(self.bits) - self.pos

    def ler(self, n: int) -> int:
        if self.pos + n > len(self.bits):
            raise QRDecodeError("fim inesperado do fluxo de bits")
        valor = 0
        for _ in range(n):
            valor = (valor << 1) | self.bits[self.pos]
            self.pos += 1
        return valor


def _bits_contador(modo: int, versao: int) -> int:
    grupo = 0 if versao <= 9 else 1 if versao <= 26 else 2
    tabela = {
        0b0001: (10, 12, 14),
        0b0010: (9, 11, 13),
        0b0100: (8, 16, 16),
        0b1000: (8, 10, 12),
    }
    if modo not in tabela:
        raise QRDecodeError(f"modo QR não suportado: {modo:04b}")
    return tabela[modo][grupo]


def _ler_eci(stream: BitStream) -> int:
    primeiro = stream.ler(8)
    if (primeiro & 0x80) == 0:
        return primeiro
    if (primeiro & 0xC0) == 0x80:
        return ((primeiro & 0x3F) << 8) | stream.ler(8)
    if (primeiro & 0xE0) == 0xC0:
        return ((primeiro & 0x1F) << 16) | stream.ler(16)
    raise QRDecodeError("ECI inválido")


def _decodificar_kanji(stream: BitStream, quantidade: int) -> str:
    """Decodifica caracteres do modo Kanji compacto do padrão QR."""
    bytes_kanji = bytearray()
    for _ in range(quantidade):
        valor_13_bits = stream.ler(13)
        deslocamento = ((valor_13_bits // 0xC0) << 8) | (valor_13_bits % 0xC0)

        if deslocamento < 0x1F00:
            codigo_shift_jis = deslocamento + 0x8140
        else:
            codigo_shift_jis = deslocamento + 0xC140

        bytes_kanji.extend(codigo_shift_jis.to_bytes(2, "big"))

    try:
        return bytes(bytes_kanji).decode("shift_jis")
    except UnicodeDecodeError as erro:
        raise QRDecodeError("conteúdo Kanji inválido") from erro


def _decodificar_dados(dados: list[int], versao: int) -> str:
    stream = BitStream(dados)
    partes: list[str] = []
    encoding = "utf-8"

    while stream.restante() >= 4:
        modo = stream.ler(4)
        if modo == 0:
            break
        if modo == 0b0111:
            eci = _ler_eci(stream)
            if eci == 3:
                encoding = "iso-8859-1"
            elif eci == 20:
                encoding = "shift_jis"
            elif eci == 26:
                encoding = "utf-8"
            continue

        contador = stream.ler(_bits_contador(modo, versao))
        if modo == 0b0001:
            restante = contador
            while restante >= 3:
                partes.append(f"{stream.ler(10):03d}")
                restante -= 3
            if restante == 2:
                partes.append(f"{stream.ler(7):02d}")
            elif restante == 1:
                partes.append(str(stream.ler(4)))
        elif modo == 0b0010:
            restante = contador
            while restante >= 2:
                valor = stream.ler(11)
                if valor >= 45 * 45:
                    raise QRDecodeError("valor alfanumérico inválido")
                partes.append(ALPHANUMERIC[valor // 45])
                partes.append(ALPHANUMERIC[valor % 45])
                restante -= 2
            if restante == 1:
                valor = stream.ler(6)
                if valor >= len(ALPHANUMERIC):
                    raise QRDecodeError("valor alfanumérico inválido")
                partes.append(ALPHANUMERIC[valor])
        elif modo == 0b0100:
            bytes_lidos = bytes(stream.ler(8) for _ in range(contador))
            try:
                partes.append(bytes_lidos.decode(encoding))
            except UnicodeDecodeError:
                partes.append(bytes_lidos.decode("latin-1", errors="replace"))
        elif modo == 0b1000:
            partes.append(_decodificar_kanji(stream, contador))
        else:
            raise QRDecodeError(f"modo QR não suportado: {modo:04b}")

    return "".join(partes)


def decodificar_grade(grade: np.ndarray) -> DecodedQR:
    dim = grade.shape[0]
    versao = versao_da_dimensao(dim)
    if versao is None:
        raise QRDecodeError("dimensão de grade inválida")

    nivel, mascara = _ler_formato(grade)
    codewords = _extrair_codewords(grade, versao, mascara)
    dados, corrigidos = _deintercalar_corrigir(codewords, versao, nivel)
    texto = _decodificar_dados(dados, versao)
    if texto == "":
        raise QRDecodeError("QR decodificado sem texto")
    return DecodedQR(texto, versao, nivel, mascara, corrigidos)
