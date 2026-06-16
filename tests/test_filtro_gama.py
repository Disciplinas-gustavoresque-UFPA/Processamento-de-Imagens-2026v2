

import numpy as np
import pytest

from plugins.pixels.filtro_gama import FiltroGama


@pytest.fixture
def imagem():
    return np.array([[[10, 128, 240]]], dtype=np.uint8)


@pytest.fixture
def plugin(qapp, imagem):
    return FiltroGama(imagem)


def _processar_com_gama(plugin, imagem, valor_slider):
    plugin._slider.setValue(valor_slider)
    return plugin.processar(imagem)


def test_identidade_gama_1(plugin, imagem):
    resultado = _processar_com_gama(plugin, imagem, 100)
    np.testing.assert_array_equal(resultado, imagem)


def test_gama_maior_que_1_clareia(plugin, imagem):
    resultado = _processar_com_gama(plugin, imagem, 220)
    assert np.all(resultado[..., :3] >= imagem[..., :3])
    assert np.any(resultado[..., :3] > imagem[..., :3])


def test_gama_menor_que_1_escurece(plugin, imagem):
    resultado = _processar_com_gama(plugin, imagem, 45)
    assert np.all(resultado[..., :3] <= imagem[..., :3])
    assert np.any(resultado[..., :3] < imagem[..., :3])


def test_preserva_dtype_e_shape(plugin, imagem):
    resultado = _processar_com_gama(plugin, imagem, 180)
    assert resultado.dtype == np.uint8
    assert resultado.shape == imagem.shape


def test_extremos_permanecem_fixos(plugin):
    img = np.array([[[0, 255, 0]]], dtype=np.uint8)
    for valor in (45, 100, 220):
        resultado = _processar_com_gama(plugin, img, valor)
        assert resultado[0, 0, 0] == 0
        assert resultado[0, 0, 1] == 255


def test_nao_modifica_imagem_original(plugin, imagem):
    copia = imagem.copy()
    _processar_com_gama(plugin, imagem, 220)
    np.testing.assert_array_equal(imagem, copia)
