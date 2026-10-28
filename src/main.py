# -*- coding: utf-8 -*-
"""
Orquesta todo el pipeline diario:

  1. Trae titulares de las 6 fuentes (sources.py).
  2. Traduce los titulares no-coreanos al español para poder
     compararlos y agruparlos junto con los coreanos (translate.py).
  3. Agrupa noticias equivalentes y elige las más relevantes, exigiendo
     que tengan un original en coreano (dedup.py).
  4. Para cada noticia elegida, arma el bloque bilingüe: coreano
     (título + resumen tal cual viene de la fuente) + su traducción al
     español (DeepL).
  5. Obtiene el hanja del día con su significado, definición y origen
     completos desde el Diccionario de Hanja de Naver, traducidos al
     español (hanja_page.py + naver_hanja.py); si Naver no responde,
     cae automáticamente al banco local de respaldo (hanja_db.py).
  6. Genera el PDF de máximo 2 páginas de noticias + 1 página de hanja
     (pdf_builder.py).

Uso:
    python main.py --out /ruta/boletin.pdf --max-historias 6

Variables de entorno requeridas:
    DEEPL_API_KEY   clave de la API de DeepL (gratuita o de pago)
"""

from __future__ import annotations

import argparse
import logging
from datetime import date

from dedup import seleccionar_top_historias
from hanja_page import obtener_hanja_del_dia
from models import Item
from pdf_builder import Story, construir_pdf
from sources import SOURCES, fetch_source
from translate import traducir, traducir_lote

log = logging.getLogger("corea_news.main")


def recolectar_items(limite_por_fuente: int, dias: int) -> list[Item]:
    todos: list[Item] = []
    for source in SOURCES:
        todos.extend(fetch_source(source, limite=limite_por_fuente, dias=dias))
    log.info("Total de titulares recolectados: %d", len(todos))
    return todos


def normalizar_titulos_a_espanol(items: list[Item]) -> dict[int, str]:
    """Traduce al español los títulos que no vienen ya en español, para
    poder compararlos/agruparlos con un criterio de similitud común."""
    no_espanol = [it for it in items if it.idioma != "es"]
    if no_espanol:
        traducciones = traducir_lote([it.titulo for it in no_espanol])
        mapa_traducido = {id(it): t for it, t in zip(no_espanol, traducciones)}
    else:
        mapa_traducido = {}

    resultado: dict[int, str] = {}
    for it in items:
        resultado[id(it)] = it.titulo if it.idioma == "es" else mapa_traducido.get(id(it), it.titulo)
    return resultado


def construir_story_desde_cluster(cluster) -> Story:
    principal = cluster.item_coreano_principal()
    texto_ko = principal.resumen or principal.titulo
    titulo_es = traducir(principal.titulo, origen="KO")
    resumen_es = traducir(texto_ko, origen="KO") if texto_ko != principal.titulo else titulo_es
    return Story(
        titulo_ko=principal.titulo,
        resumen_ko=principal.resumen or "",
        titulo_es=titulo_es,
        resumen_es=resumen_es,
        fuente=principal.fuente,
        enlace=principal.enlace,
        num_fuentes=cluster.relevancia,
    )


def generar_boletin(output_path: str, max_historias: int = 6, limite_por_fuente: int = 12, dias: int = 2) -> int:
    items = recolectar_items(limite_por_fuente, dias)
    if not items:
        raise RuntimeError(
            "No se pudo recolectar ninguna noticia de ninguna fuente. "
            "Revisa la conexión a internet y los selectores de sources.py."
        )

    titulos_es = normalizar_titulos_a_espanol(items)
    top_clusters = seleccionar_top_historias(items, titulos_es, max_historias=max_historias)
    if not top_clusters:
        raise RuntimeError(
            "Ninguna noticia recolectada tenía una fuente en coreano original "
            "(Dong-a/Chosun/JoongAng). Revisa esas tres fuentes primero."
        )

    stories = [construir_story_desde_cluster(c) for c in top_clusters]
    hanja = obtener_hanja_del_dia(date.today())
    if hanja.es_respaldo_local:
        log.warning(
            "El hanja del día (%s) se tomó del banco local de respaldo "
            "porque no se pudo consultar Naver hoy.", hanja.hanja,
        )
    paginas = construir_pdf(stories, hanja, output_path, max_paginas_noticias=2)
    log.info("Boletín generado en %s (%d páginas, %d historias)", output_path, paginas, len(stories))
    return paginas


def main():
    parser = argparse.ArgumentParser(description="Genera el boletín diario de noticias de Corea del Sur en PDF.")
    parser.add_argument("--out", default=f"boletin_corea_{date.today().isoformat()}.pdf")
    parser.add_argument("--max-historias", type=int, default=6)
    parser.add_argument("--limite-por-fuente", type=int, default=12)
    parser.add_argument("--dias", type=int, default=2, help="Ventana de días hacia atrás a considerar.")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    generar_boletin(args.out, args.max_historias, args.limite_por_fuente, args.dias)


if __name__ == "__main__":
    main()
