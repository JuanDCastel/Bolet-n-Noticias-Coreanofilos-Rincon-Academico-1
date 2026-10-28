# -*- coding: utf-8 -*-
"""
Arma el contenido final de la página de "Hanja del día": intenta traer
todo (significado, definición y origen) desde el Diccionario de Hanja
de Naver y lo traduce al español; si Naver no responde ese día, cae al
banco local de `hanja_db.py` y lo marca explícitamente como respaldo.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import List

import naver_hanja
from hanja_db import hanja_of_the_day
from translate import traducir_hanja

log = logging.getLogger("corea_news.hanja_page")


@dataclass
class HanjaPagina:
    hanja: str
    hun_eum_ko: str
    romanizacion: str
    definicion_es: List[str] = field(default_factory=list)
    origen_es: str = ""
    radical: str = ""
    trazos: str = ""
    es_respaldo_local: bool = False  # True si Naver falló y se usó el banco local


def obtener_hanja_del_dia(fecha: date | None = None) -> HanjaPagina:
    fecha = fecha or date.today()
    entrada_local = hanja_of_the_day(fecha)

    info = None
    try:
        info = naver_hanja.obtener_info(entrada_local.hanja)
    except Exception as exc:  # noqa: BLE001
        log.warning("Fallo inesperado consultando Naver para %s: %s", entrada_local.hanja, exc)

    if info is not None and info.encontrado:
        definicion_es = [traducir_hanja(d) for d in info.definicion] if info.definicion else []
        origen_es = traducir_hanja(info.origen) if info.origen else ""
        return HanjaPagina(
            hanja=info.hanja,
            hun_eum_ko=info.hun_eum or entrada_local.hun_eum,
            romanizacion=info.romanizacion or entrada_local.romanizacion,
            definicion_es=definicion_es,
            origen_es=origen_es,
            radical=info.radical,
            trazos=info.trazos,
            es_respaldo_local=False,
        )

    log.warning(
        "No se pudo obtener %s desde Naver; usando banco local de respaldo.",
        entrada_local.hanja,
    )
    return HanjaPagina(
        hanja=entrada_local.hanja,
        hun_eum_ko=entrada_local.hun_eum,
        romanizacion=entrada_local.romanizacion,
        definicion_es=[entrada_local.significado],
        origen_es="",
        es_respaldo_local=True,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    pagina = obtener_hanja_del_dia()
    print(pagina)
