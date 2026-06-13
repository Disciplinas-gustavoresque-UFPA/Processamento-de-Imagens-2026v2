"""Pipeline para ler QR Code a partir de uma imagem RGB."""

from __future__ import annotations

from collections.abc import Callable
from hashlib import blake2b

import cv2
import numpy as np

from plugins.reconhecimento._qrcode.decoder import QRDecodeError, decodificar_grade
from plugins.reconhecimento._qrcode.detector import detectar_candidatos
from plugins.reconhecimento._qrcode.geometria import amostrar_grade, warp_para_grade
from plugins.reconhecimento._qrcode.modelos import QRCandidate, QRReadResult
from plugins.reconhecimento._qrcode.preprocessamento import gerar_binarizacoes


class QRProcessingCache:
    """Cache pequeno para dados caros reaproveitáveis na mesma imagem."""

    def __init__(self, max_entradas: int = 4):
        self.max_entradas = max(1, max_entradas)
        self._binarizacoes: dict[str, list[tuple[str, np.ndarray]]] = {}
        self._candidatos: dict[tuple[str, int], list[QRCandidate]] = {}
        self._resultados: dict[tuple[str, int], list[QRReadResult]] = {}
        self._ordem_binarizacoes: list[str] = []
        self._ordem_candidatos: list[tuple[str, int]] = []
        self._ordem_resultados: list[tuple[str, int]] = []

    def obter_binarizacoes(
        self,
        chave_imagem: str,
        imagem_rgb: np.ndarray,
    ) -> list[tuple[str, np.ndarray]]:
        if chave_imagem not in self._binarizacoes:
            self._binarizacoes[chave_imagem] = gerar_binarizacoes(imagem_rgb)

        self._registrar_uso(
            chave_imagem,
            self._ordem_binarizacoes,
            self._binarizacoes,
        )
        return self._binarizacoes[chave_imagem]

    def obter_candidatos(
        self,
        chave_imagem: str,
        max_versao: int,
        construir: Callable[[], list[QRCandidate]],
    ) -> list[QRCandidate]:
        chave = (chave_imagem, max_versao)
        if chave not in self._candidatos:
            self._candidatos[chave] = construir()

        self._registrar_uso(chave, self._ordem_candidatos, self._candidatos)
        return self._candidatos[chave]

    def obter_resultados(
        self,
        chave_imagem: str,
        max_versao: int,
    ) -> list[QRReadResult] | None:
        chave = (chave_imagem, max_versao)
        if chave not in self._resultados:
            return None

        self._registrar_uso(chave, self._ordem_resultados, self._resultados)
        return _copiar_resultados(self._resultados[chave])

    def guardar_resultados(
        self,
        chave_imagem: str,
        max_versao: int,
        resultados: list[QRReadResult],
    ) -> None:
        chave = (chave_imagem, max_versao)
        self._resultados[chave] = _copiar_resultados(resultados)
        self._registrar_uso(chave, self._ordem_resultados, self._resultados)

    def _registrar_uso(self, chave, ordem: list, mapa: dict) -> None:
        if chave in ordem:
            ordem.remove(chave)
        ordem.append(chave)

        while len(ordem) > self.max_entradas:
            antiga = ordem.pop(0)
            mapa.pop(antiga, None)


class QRReader:
    """Leitor QR com múltiplas hipóteses e decodificador próprio."""

    def __init__(
        self,
        max_versao: int = 40,
        cache: QRProcessingCache | None = None,
    ):
        self.max_versao = max_versao
        self.cache = cache or QRProcessingCache(max_entradas=1)

    def ler(self, imagem_rgb: np.ndarray) -> QRReadResult:
        return self.ler_todos(imagem_rgb)[0]

    def ler_todos(self, imagem_rgb: np.ndarray) -> list[QRReadResult]:
        chave_imagem = _assinatura_imagem(imagem_rgb)
        resultado_cacheado = self.cache.obter_resultados(chave_imagem, self.max_versao)
        if resultado_cacheado is not None:
            return resultado_cacheado

        candidatos = self._coletar_candidatos(imagem_rgb, chave_imagem)
        erros: list[str] = []
        tentativas = 0
        resultados: list[QRReadResult] = []

        for candidato in candidatos:
            if _candidato_ja_lido(candidato.corners, resultados):
                continue

            versoes = self._versoes_para_tentar(candidato)
            candidato_decodificado = False
            for versao in versoes:
                dimensao = 21 + 4 * (versao - 1)
                for fator in (1.0, 0.985, 1.015):
                    cantos = _escalar_cantos(candidato.corners, fator)
                    try:
                        warp = warp_para_grade(imagem_rgb, cantos, dimensao)
                        grade = amostrar_grade(warp, dimensao)
                    except Exception as erro:
                        erros.append(str(erro))
                        continue

                    for rotacao in range(4):
                        tentativas += 1
                        grade_rot = np.rot90(grade, rotacao)
                        try:
                            decodificado = decodificar_grade(grade_rot)
                        except (QRDecodeError, ValueError) as erro:
                            erros.append(str(erro))
                            continue

                        if _resultado_duplicado(cantos, decodificado.text, resultados):
                            candidato_decodificado = True
                            break

                        resultados.append(
                            QRReadResult(
                                text=decodificado.text,
                                version=decodificado.version,
                                error_level=decodificado.error_level,
                                mask=decodificado.mask,
                                corrected_errors=decodificado.corrected_errors,
                                candidate_name=candidato.source_name,
                                annotated_image=imagem_rgb.copy(),
                                grid=grade_rot,
                                attempts=tentativas,
                                corners=np.asarray(cantos, dtype=np.float32),
                            )
                        )
                        candidato_decodificado = True
                        break
                    if candidato_decodificado:
                        break
                if candidato_decodificado:
                    break

        if resultados:
            resultados.sort(key=lambda resultado: _chave_posicao(resultado.corners))
            anotada = self._anotar_multiplos(imagem_rgb, [r.corners for r in resultados])
            for resultado in resultados:
                resultado.annotated_image = anotada
            self.cache.guardar_resultados(chave_imagem, self.max_versao, resultados)
            return resultados

        detalhe = erros[-1] if erros else "nenhum candidato encontrado"
        raise QRDecodeError(f"Não foi possível ler o QR Code: {detalhe}")

    def _coletar_candidatos(
        self,
        imagem_rgb: np.ndarray,
        chave_imagem: str,
    ) -> list[QRCandidate]:
        def construir() -> list[QRCandidate]:
            todos: list[QRCandidate] = []
            binarizacoes = self.cache.obter_binarizacoes(chave_imagem, imagem_rgb)
            for nome, binaria in binarizacoes:
                todos.extend(
                    detectar_candidatos(binaria, nome, max_versao=self.max_versao)
                )
            todos.sort(key=lambda item: item.score, reverse=True)
            return _deduplicar(todos)[:240]

        return self.cache.obter_candidatos(
            chave_imagem,
            self.max_versao,
            construir,
        )

    def _versoes_para_tentar(self, candidato: QRCandidate) -> list[int]:
        if candidato.version_hint is None:
            return list(range(1, self.max_versao + 1))
        inicio = max(1, candidato.version_hint - 1)
        fim = min(self.max_versao, candidato.version_hint + 1)
        versoes = list(range(inicio, fim + 1))
        if candidato.version_hint in versoes:
            versoes.remove(candidato.version_hint)
            versoes.insert(0, candidato.version_hint)
        return versoes

    def _anotar_multiplos(
        self, imagem_rgb: np.ndarray, lista_cantos: list[np.ndarray]
    ) -> np.ndarray:
        anotada = imagem_rgb.copy()
        cores = ((0, 220, 80), (255, 120, 0), (80, 160, 255), (220, 80, 220))

        for indice, cantos in enumerate(lista_cantos):
            cor = cores[indice % len(cores)]
            pts = np.asarray(cantos, dtype=np.int32).reshape((-1, 1, 2))
            cv2.polylines(anotada, [pts], True, cor, 3, cv2.LINE_AA)
            for ponto in pts.reshape(-1, 2):
                cv2.circle(anotada, tuple(int(v) for v in ponto), 5, cor, -1)

        return anotada


def _escalar_cantos(cantos: np.ndarray, fator: float) -> np.ndarray:
    if abs(fator - 1.0) < 1e-9:
        return np.asarray(cantos, dtype=np.float32)
    pts = np.asarray(cantos, dtype=np.float32)
    centro = pts.mean(axis=0)
    return centro + (pts - centro) * fator


def _assinatura_imagem(imagem_rgb: np.ndarray) -> str:
    imagem_contigua = np.ascontiguousarray(imagem_rgb)
    digest = blake2b(imagem_contigua.tobytes(), digest_size=16).hexdigest()
    return f"{imagem_contigua.shape}|{imagem_contigua.dtype}|{digest}"


def _copiar_resultados(resultados: list[QRReadResult]) -> list[QRReadResult]:
    return [_copiar_resultado(resultado) for resultado in resultados]


def _copiar_resultado(resultado: QRReadResult) -> QRReadResult:
    return QRReadResult(
        text=resultado.text,
        version=resultado.version,
        error_level=resultado.error_level,
        mask=resultado.mask,
        corrected_errors=resultado.corrected_errors,
        candidate_name=resultado.candidate_name,
        annotated_image=resultado.annotated_image.copy(),
        grid=resultado.grid.copy(),
        attempts=resultado.attempts,
        corners=resultado.corners.copy(),
    )


def _deduplicar(candidatos: list[QRCandidate]) -> list[QRCandidate]:
    filtrados: list[QRCandidate] = []
    for cand in candidatos:
        centro = cand.corners.mean(axis=0)
        area = float(cv2.contourArea(cand.corners.astype(np.float32)))
        duplicado = False
        for existente in filtrados:
            if cand.version_hint != existente.version_hint:
                continue
            centro_ex = existente.corners.mean(axis=0)
            area_ex = float(cv2.contourArea(existente.corners.astype(np.float32)))
            distancia = float(np.linalg.norm(centro - centro_ex))
            escala = max(area, area_ex, 1.0) ** 0.5
            razao_area = abs(area - area_ex) / max(area, area_ex, 1.0)
            if (
                distancia < max(8.0, escala * 0.04)
                and razao_area < 0.08
                and _cantos_muito_proximos(cand.corners, existente.corners, escala)
            ):
                duplicado = True
                break
        if not duplicado:
            filtrados.append(cand)
    return filtrados


def _cantos_muito_proximos(
    cantos_a: np.ndarray,
    cantos_b: np.ndarray,
    escala: float,
) -> bool:
    pontos_a = np.asarray(cantos_a, dtype=np.float32)
    pontos_b = np.asarray(cantos_b, dtype=np.float32)
    distancia_media = float(np.linalg.norm(pontos_a - pontos_b, axis=1).mean())
    return distancia_media < max(2.0, escala * 0.01)


def _resultado_duplicado(
    cantos: np.ndarray, texto: str, resultados: list[QRReadResult]
) -> bool:
    for resultado in resultados:
        if resultado.text == texto and _mesma_regiao(cantos, resultado.corners):
            return True
        if _mesma_regiao(cantos, resultado.corners, tolerancia=0.35):
            return True
    return False


def _candidato_ja_lido(cantos: np.ndarray, resultados: list[QRReadResult]) -> bool:
    return any(_mesma_regiao(cantos, resultado.corners, tolerancia=0.25) for resultado in resultados)


def _chave_posicao(cantos: np.ndarray) -> tuple[float, float]:
    centro = np.asarray(cantos, dtype=np.float32).mean(axis=0)
    return float(centro[1]), float(centro[0])


def _mesma_regiao(
    cantos_a: np.ndarray,
    cantos_b: np.ndarray,
    tolerancia: float = 0.22,
) -> bool:
    pontos_a = np.asarray(cantos_a, dtype=np.float32)
    pontos_b = np.asarray(cantos_b, dtype=np.float32)
    centro_a = pontos_a.mean(axis=0)
    centro_b = pontos_b.mean(axis=0)
    area_a = max(1.0, float(cv2.contourArea(pontos_a)))
    area_b = max(1.0, float(cv2.contourArea(pontos_b)))

    distancia = float(np.linalg.norm(centro_a - centro_b))
    escala = max(area_a, area_b) ** 0.5
    razao_area = min(area_a, area_b) / max(area_a, area_b)
    return distancia <= max(12.0, escala * tolerancia) and razao_area >= 0.45
