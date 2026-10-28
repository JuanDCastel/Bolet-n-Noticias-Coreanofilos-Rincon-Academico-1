# -*- coding: utf-8 -*-
"""
Agrupa titulares equivalentes venidos de varias fuentes y calcula qué
historias son "las más relevantes del día".

Lógica (deliberadamente simple, sin depender de modelos pesados ni de
un analizador morfológico coreano, para que corra rápido y gratis en
Colab/GitHub Actions):

  1. Cada titular se normaliza a una forma comparable en español
     (si no está ya en español, se traduce con DeepL — textos cortos,
     consume muy poca cuota).
  2. Se agrupan los titulares cuyo texto normalizado es muy similar
     (difflib.SequenceMatcher) en "clusters" = la misma noticia vista
     por varias fuentes.
  3. La relevancia de un cluster = cuántas fuentes DISTINTAS lo cubren
     (más fuentes cubriéndolo = más importante), con la fecha más
     reciente como desempate.
  4. Solo se seleccionan como noticia principal los clusters que
     tienen al menos un artículo en coreano original (Dong-a, Chosun
     o JoongAng), porque son los que nos dan el "texto original
     coreano" que pide la publicación. KBS/Korea.net/Korea Herald
     sirven como refuerzo de relevancia aunque no aporten el texto
     coreano.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Dict, List, Optional

from models import Item

SIMILARITY_THRESHOLD = 0.62


@dataclass
class Cluster:
    items: List[Item] = field(default_factory=list)

    @property
    def fuentes(self) -> List[str]:
        return sorted({it.fuente for it in self.items})

    @property
    def tiene_coreano(self) -> bool:
        return any(it.idioma == "ko" for it in self.items)

    def item_coreano_principal(self) -> Optional[Item]:
        """El ítem coreano con más texto (resumen más largo), para usarlo
        como base del texto original de la publicación."""
        candidatos = [it for it in self.items if it.idioma == "ko"]
        if not candidatos:
            return None
        return max(candidatos, key=lambda it: len(it.resumen or it.titulo))

    @property
    def relevancia(self) -> int:
        return len(self.fuentes)


def _similar(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def clusterizar(
    items: List[Item],
    titulo_normalizado: Dict[int, str],
) -> List[Cluster]:
    """
    titulo_normalizado: mapa id(item) -> título ya normalizado a un
    idioma común (típicamente español), calculado afuera para poder
    cachear/traducir en lote antes de llamar a esta función.
    """
    clusters: List[Cluster] = []
    for it in items:
        texto = titulo_normalizado[id(it)]
        destino = None
        for c in clusters:
            rep = titulo_normalizado[id(c.items[0])]
            if _similar(texto, rep) >= SIMILARITY_THRESHOLD:
                destino = c
                break
        if destino is None:
            destino = Cluster()
            clusters.append(destino)
        destino.items.append(it)
    return clusters


def seleccionar_top_historias(
    items: List[Item],
    titulo_normalizado: Dict[int, str],
    max_historias: int = 6,
) -> List[Cluster]:
    clusters = clusterizar(items, titulo_normalizado)
    elegibles = [c for c in clusters if c.tiene_coreano]
    elegibles.sort(key=lambda c: c.relevancia, reverse=True)
    return elegibles[:max_historias]


if __name__ == "__main__":
    # Prueba rápida con datos simulados (sin red), para validar la
    # lógica de clusterización y selección.
    from models import Item as _Item

    mock = [
        _Item("정부, 내년도 예산안 발표", "http://a", "Dong-a Ilbo", "ko", resumen="정부가 내년도 예산안을 발표했다."),
        _Item("Gobierno surcoreano anuncia presupuesto para el próximo año", "http://b", "KBS World (español)", "es"),
        _Item("Government unveils budget plan for next year", "http://c", "Korea Herald", "en"),
        _Item("한국 축구, 아시안컵 우승", "http://d", "Chosun Ilbo", "ko", resumen="한국 축구 대표팀이 아시안컵에서 우승을 차지했다."),
        _Item("수도권 아파트 가격 상승세", "http://e", "JoongAng Ilbo", "ko", resumen="서울 등 수도권 아파트 가격이 상승세를 이어가고 있다."),
    ]
    # Simulación de "normalización": en producción esto viene de DeepL.
    mock_normalizado = {
        id(mock[0]): "Gobierno anuncia presupuesto para el próximo año",
        id(mock[1]): "Gobierno surcoreano anuncia presupuesto para el próximo año",
        id(mock[2]): "Gobierno anuncia plan de presupuesto para el próximo año",
        id(mock[3]): "Selección de fútbol de Corea gana la Copa Asiática",
        id(mock[4]): "Precios de apartamentos en el área metropolitana suben",
    }
    top = seleccionar_top_historias(mock, mock_normalizado, max_historias=5)
    for c in top:
        print(f"Relevancia={c.relevancia}  Fuentes={c.fuentes}")
        principal = c.item_coreano_principal()
        print(f"   Coreano: {principal.titulo}")
