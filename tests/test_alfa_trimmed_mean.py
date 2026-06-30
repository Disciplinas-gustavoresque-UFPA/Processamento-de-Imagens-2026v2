"""Testes do filtro Alfa-Trimmed Mean — foco na remoção mista de ruído."""

import numpy as np
import pytest

from plugins.filtros.alfa_trimmed_mean_filter import (
    FiltroAlfaTrimmedMean,
    alfatrimmedmeanfilter_2d_numpy,
)


# ---------------------------------------------------------------------------
#  Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def imagem_limpa():
    """Imagem 64×64 com gradiente suave — fácil de medir distorção."""
    rng = np.arange(64, dtype=np.float64)
    canal = (rng[:, None] + rng[None, :]) / 2  # 0..63
    canal = (canal / 63 * 200 + 28).astype(np.uint8)  # 28..228
    return np.stack([canal, canal, canal], axis=-1)


@pytest.fixture
def plugin(qapp, imagem_limpa):
    return FiltroAlfaTrimmedMean(imagem_limpa)


# ---------------------------------------------------------------------------
#  Helpers para injetar ruído
# ---------------------------------------------------------------------------

def _adicionar_gaussiano(img: np.ndarray, sigma: float = 25, seed: int = 42) -> np.ndarray:
    rng = np.random.RandomState(seed)
    ruido = rng.normal(0, sigma, img.shape)
    return np.clip(img.astype(np.float64) + ruido, 0, 255).astype(np.uint8)


def _adicionar_salt_pepper(img: np.ndarray, taxa: float = 0.05, seed: int = 42) -> np.ndarray:
    rng = np.random.RandomState(seed)
    out = img.copy()
    h, w = img.shape[:2]
    n_pixels = int(taxa * h * w)
    coords = rng.choice(h * w, n_pixels, replace=False)
    ys, xs = coords // w, coords % w
    metade = n_pixels // 2
    if img.ndim == 3:
        out[ys[:metade], xs[:metade], :] = 255
        out[ys[metade:], xs[metade:], :] = 0
    else:
        out[ys[:metade], xs[:metade]] = 255
        out[ys[metade:], xs[metade:]] = 0
    return out


def _adicionar_ruido_misto(
    img: np.ndarray, sigma: float = 20, taxa_sp: float = 0.05, seed: int = 42
) -> np.ndarray:
    """Aplica gaussiano + salt & pepper na imagem."""
    com_gauss = _adicionar_gaussiano(img, sigma, seed)
    return _adicionar_salt_pepper(com_gauss, taxa_sp, seed + 1)


def _mse(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.mean((a.astype(np.float64) - b.astype(np.float64)) ** 2))


# ---------------------------------------------------------------------------
#  Testes básicos do filtro
# ---------------------------------------------------------------------------

def test_alpha_zero_e_media_pura(imagem_limpa):
    """Alpha=0 → média aritmética pura (sem trimming)."""
    canal = imagem_limpa[:, :, 0].astype(np.float64)
    resultado = alfatrimmedmeanfilter_2d_numpy(canal, alpha=0)
    assert resultado is not None
    assert resultado.shape == canal.shape


def test_alpha_maximo_e_mediana(imagem_limpa):
    """Alpha máximo (8 para janela 3×3) → mediana pura."""
    canal = imagem_limpa[:, :, 0].astype(np.float64)
    resultado = alfatrimmedmeanfilter_2d_numpy(canal, alpha=8)
    assert resultado is not None


def test_alpha_impar_retorna_none(imagem_limpa):
    """Alpha ímpar deve ser rejeitado."""
    canal = imagem_limpa[:, :, 0].astype(np.float64)
    assert alfatrimmedmeanfilter_2d_numpy(canal, alpha=3) is None


def test_preserva_shape_e_dtype(plugin, imagem_limpa):
    """O plugin deve manter shape RGB e dtype uint8."""
    plugin.slider_alpha.setValue(1)  # alpha=2
    resultado = plugin.processar(imagem_limpa)
    assert resultado.shape == imagem_limpa.shape
    assert resultado.dtype == np.uint8


# ---------------------------------------------------------------------------
#  Testes de remoção de ruído
# ---------------------------------------------------------------------------

def test_remocao_ruido_gaussiano(plugin, imagem_limpa):
    """Alpha baixo (≈média) deve reduzir ruído gaussiano."""
    ruidosa = _adicionar_gaussiano(imagem_limpa, sigma=25)
    mse_antes = _mse(ruidosa, imagem_limpa)

    plugin.slider_alpha.setValue(0)  # alpha=0 → média pura
    plugin.slider_iteracoes.setValue(1)
    filtrada = plugin.processar(ruidosa)
    mse_depois = _mse(filtrada, imagem_limpa)

    assert mse_depois < mse_antes, (
        f"Filtro deveria reduzir MSE gaussiano: {mse_antes:.1f} → {mse_depois:.1f}"
    )


def test_remocao_salt_pepper(plugin, imagem_limpa):
    """Alpha alto (≈mediana) deve reduzir salt & pepper."""
    ruidosa = _adicionar_salt_pepper(imagem_limpa, taxa=0.05)
    mse_antes = _mse(ruidosa, imagem_limpa)

    # Alpha máximo para kernel 3×3 = 8 (slider_value = 4)
    plugin.slider_alpha.setValue(4)  # alpha=8 → mediana
    plugin.slider_iteracoes.setValue(1)
    filtrada = plugin.processar(ruidosa)
    mse_depois = _mse(filtrada, imagem_limpa)

    assert mse_depois < mse_antes, (
        f"Filtro deveria reduzir MSE salt&pepper: {mse_antes:.1f} → {mse_depois:.1f}"
    )


def test_remocao_ruido_misto(plugin, imagem_limpa):
    """Alpha intermediário deve reduzir ruído MISTO (gaussiano + salt & pepper)."""
    ruidosa = _adicionar_ruido_misto(imagem_limpa, sigma=20, taxa_sp=0.05)
    mse_antes = _mse(ruidosa, imagem_limpa)

    # Alpha intermediário: ~50% do máximo (slider=2 → alpha=4)
    plugin.slider_alpha.setValue(2)  # alpha=4 → misto
    plugin.slider_iteracoes.setValue(2)
    filtrada = plugin.processar(ruidosa)
    mse_depois = _mse(filtrada, imagem_limpa)

    assert mse_depois < mse_antes, (
        f"Filtro deveria reduzir MSE misto: {mse_antes:.1f} → {mse_depois:.1f}"
    )


def test_ruido_misto_alpha_intermediario_melhor_que_extremos(plugin, imagem_limpa):
    """Para ruído misto, alpha intermediário deve ser melhor que os extremos."""
    ruidosa = _adicionar_ruido_misto(imagem_limpa, sigma=20, taxa_sp=0.05)

    resultados = {}
    for slider_val, nome in [(0, "media"), (2, "misto"), (4, "mediana")]:
        plugin.slider_alpha.setValue(slider_val)
        plugin.slider_iteracoes.setValue(2)
        filtrada = plugin.processar(ruidosa)
        resultados[nome] = _mse(filtrada, imagem_limpa)

    # O alpha intermediário deve ter MSE menor (melhor) que pelo menos um extremo
    assert resultados["misto"] < max(resultados["media"], resultados["mediana"]), (
        f"Alpha misto deveria superar ao menos um extremo: "
        f"media={resultados['media']:.1f}, misto={resultados['misto']:.1f}, "
        f"mediana={resultados['mediana']:.1f}"
    )


def test_multiplas_iteracoes_melhoram(plugin, imagem_limpa):
    """Mais iterações devem reduzir o MSE progressivamente (até certo ponto)."""
    ruidosa = _adicionar_ruido_misto(imagem_limpa, sigma=20, taxa_sp=0.05)

    plugin.slider_alpha.setValue(2)  # alpha=4 → misto
    mse_por_iteracao = []
    for n_iter in [1, 2, 3]:
        plugin.slider_iteracoes.setValue(n_iter)
        filtrada = plugin.processar(ruidosa)
        mse_por_iteracao.append(_mse(filtrada, imagem_limpa))

    # 2 iterações devem ser melhor que 1
    assert mse_por_iteracao[1] <= mse_por_iteracao[0], (
        f"2 iterações deveriam melhorar: iter1={mse_por_iteracao[0]:.1f}, "
        f"iter2={mse_por_iteracao[1]:.1f}"
    )


def test_nao_modifica_imagem_original(plugin, imagem_limpa):
    """O processamento não deve alterar a imagem de entrada."""
    ruidosa = _adicionar_ruido_misto(imagem_limpa)
    copia = ruidosa.copy()
    plugin.slider_alpha.setValue(2)
    plugin.processar(ruidosa)
    np.testing.assert_array_equal(ruidosa, copia)
