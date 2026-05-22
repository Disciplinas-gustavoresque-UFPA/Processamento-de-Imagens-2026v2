"""Decodificador Reed-Solomon em GF(256) usado por QR Codes."""

from __future__ import annotations


class ReedSolomonError(Exception):
    """Erro irrecuperavel de Reed-Solomon."""


GF_EXP = [0] * 512
GF_LOG = [0] * 256


def _init_tables() -> None:
    x = 1
    for i in range(255):
        GF_EXP[i] = x
        GF_LOG[x] = i
        x <<= 1
        if x & 0x100:
            x ^= 0x11D
    for i in range(255, 512):
        GF_EXP[i] = GF_EXP[i - 255]


_init_tables()


def gf_add(x: int, y: int) -> int:
    return x ^ y


def gf_mul(x: int, y: int) -> int:
    if x == 0 or y == 0:
        return 0
    return GF_EXP[GF_LOG[x] + GF_LOG[y]]


def gf_div(x: int, y: int) -> int:
    if y == 0:
        raise ZeroDivisionError("divisão por zero em GF(256)")
    if x == 0:
        return 0
    return GF_EXP[(GF_LOG[x] + 255 - GF_LOG[y]) % 255]


def gf_pow(x: int, power: int) -> int:
    if power == 0:
        return 1
    if x == 0:
        return 0
    return GF_EXP[(GF_LOG[x] * power) % 255]


def gf_inverse(x: int) -> int:
    if x == 0:
        raise ZeroDivisionError("zero não tem inverso em GF(256)")
    return GF_EXP[255 - GF_LOG[x]]


def poly_scale(poly: list[int], escalar: int) -> list[int]:
    return [gf_mul(coef, escalar) for coef in poly]


def poly_add(p: list[int], q: list[int]) -> list[int]:
    resultado = [0] * max(len(p), len(q))
    for i, coef in enumerate(p):
        resultado[i + len(resultado) - len(p)] ^= coef
    for i, coef in enumerate(q):
        resultado[i + len(resultado) - len(q)] ^= coef
    return resultado


def poly_eval(poly: list[int], x: int) -> int:
    y = poly[0]
    for coef in poly[1:]:
        y = gf_mul(y, x) ^ coef
    return y


def calcular_sindromes(mensagem: list[int], nsym: int) -> list[int]:
    """Calcula síndromes S_0..S_(nsym-1) com primeiro gerador em alpha^0."""
    return [poly_eval(mensagem, gf_pow(2, i)) for i in range(nsym)]


def tem_erro(sindromes: list[int]) -> bool:
    return any(valor != 0 for valor in sindromes)


def encontrar_localizador_erros(sindromes: list[int], nsym: int) -> list[int]:
    """Berlekamp-Massey para encontrar o polinomio localizador de erros."""
    synd = [0] + sindromes
    err_loc = [1]
    old_loc = [1]

    for i in range(nsym):
        delta = synd[i + 1]
        for j in range(1, len(err_loc)):
            delta ^= gf_mul(err_loc[-(j + 1)], synd[i + 1 - j])

        old_loc.append(0)
        if delta != 0:
            if len(old_loc) > len(err_loc):
                novo_loc = poly_scale(old_loc, delta)
                old_loc = poly_scale(err_loc, gf_inverse(delta))
                err_loc = novo_loc
            err_loc = poly_add(err_loc, poly_scale(old_loc, delta))

    while len(err_loc) > 1 and err_loc[0] == 0:
        err_loc.pop(0)

    erros = len(err_loc) - 1
    if erros * 2 > nsym:
        raise ReedSolomonError("erros demais para a capacidade do bloco")
    return err_loc


def encontrar_posicoes_erros(err_loc: list[int], tamanho_msg: int) -> list[int]:
    """Chien search."""
    erros = len(err_loc) - 1
    posicoes: list[int] = []
    for i in range(tamanho_msg):
        # A raiz do localizador e alpha^(-i), onde i e a distancia a partir
        # do fim da palavra RS.
        if poly_eval(err_loc, gf_pow(2, 255 - i)) == 0:
            posicoes.append(tamanho_msg - 1 - i)
    if len(posicoes) != erros:
        raise ReedSolomonError("não foi possível localizar todos os erros")
    return posicoes


def _resolver_sistema_gf(matriz: list[list[int]], vetor: list[int]) -> list[int]:
    n = len(vetor)
    aug = [linha[:] + [vetor[i]] for i, linha in enumerate(matriz)]

    for col in range(n):
        pivot = None
        for row in range(col, n):
            if aug[row][col] != 0:
                pivot = row
                break
        if pivot is None:
            raise ReedSolomonError("sistema singular ao calcular magnitudes")

        if pivot != col:
            aug[col], aug[pivot] = aug[pivot], aug[col]

        inv = gf_inverse(aug[col][col])
        for k in range(col, n + 1):
            aug[col][k] = gf_mul(aug[col][k], inv)

        for row in range(n):
            if row == col or aug[row][col] == 0:
                continue
            fator = aug[row][col]
            for k in range(col, n + 1):
                aug[row][k] ^= gf_mul(fator, aug[col][k])

    return [aug[i][n] for i in range(n)]


def corrigir_msg(mensagem: list[int], nsym: int) -> tuple[list[int], int]:
    """
    Corrige uma mensagem RS e devolve apenas os bytes corrigidos.

    A mensagem recebida deve conter dados + bytes de correção do bloco.
    """
    corrigida = mensagem[:]
    sindromes = calcular_sindromes(corrigida, nsym)
    if not tem_erro(sindromes):
        return corrigida, 0

    err_loc = encontrar_localizador_erros(sindromes, nsym)
    posicoes = encontrar_posicoes_erros(err_loc, len(corrigida))
    qtd_erros = len(posicoes)
    if qtd_erros == 0:
        raise ReedSolomonError("síndrome inválida sem posições de erro")

    matriz: list[list[int]] = []
    for i in range(qtd_erros):
        linha = []
        for pos in posicoes:
            expoente = i * (len(corrigida) - 1 - pos)
            linha.append(gf_pow(2, expoente))
        matriz.append(linha)

    magnitudes = _resolver_sistema_gf(matriz, sindromes[:qtd_erros])
    for pos, mag in zip(posicoes, magnitudes):
        corrigida[pos] ^= mag

    if tem_erro(calcular_sindromes(corrigida, nsym)):
        raise ReedSolomonError("correção Reed-Solomon falhou")

    return corrigida, qtd_erros
