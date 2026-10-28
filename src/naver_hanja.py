# -*- coding: utf-8 -*-
"""
Obtiene, para un hanja dado, los datos del Diccionario de Hanja de
Naver (hanja.dict.naver.com): 훈음 (significado + lectura), 뜻풀이/정의
(definición) y 자원풀이 (origen/etimología del carácter).

AVISO IMPORTANTE SOBRE ESTE MÓDULO
-----------------------------------
Naver no publica una API oficial/documentada para este diccionario, así
que este módulo funciona por "mejor esfuerzo": intenta primero la API
JSON interna que usa el sitio (api3), y si no obtiene lo que necesita,
cae a leer el HTML de la página de resultados. Como el entorno donde
se escribió este código no tiene salida a internet general (solo a
GitHub y gestores de paquetes), **no fue posible probar este scraper
contra el sitio real antes de entregarlo**. La primera vez que se
ejecutará contra hanja.dict.naver.com de verdad será en tu Google Colab
o en GitHub Actions, que sí tienen internet completo.

Por eso este archivo incluye `diagnostico()`: una función que, para un
solo carácter, imprime exactamente qué respondió Naver (JSON crudo o
HTML) y qué se logró extraer. **Corre esa función primero** (hay una
celda dedicada para esto en el notebook de Colab). Si algo no calza
con el sitio real, pégame esa salida y ajusto el parser al toque.

Pase lo que pase, si el scraping falla para el hanja del día, el
pipeline no se rompe: `main.py` cae automáticamente al banco local de
`hanja_db.py` (más breve, pero siempre disponible) y lo deja indicado
en el PDF como respaldo, nunca haciéndolo pasar por datos de Naver.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

log = logging.getLogger("corea_news.naver_hanja")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 BoletinCoreaBot/1.0"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,es;q=0.8",
}
TIMEOUT = 15

API_URL = "https://hanja.dict.naver.com/api3/ko/search"
PAGE_URL = "https://hanja.dict.naver.com/search"

# Palabras clave (en el NOMBRE de la llave del JSON o como prefijo de
# texto visible en el HTML) que nos ayudan a reconocer cada campo sin
# depender de conocer el esquema exacto de la respuesta.
CLAVES_ORIGEN = ("jawon", "origin", "자원", "유래")
CLAVES_HUNUM = ("hunum", "hunEum", "hun_um", "훈음")
CLAVES_DEFINICION = ("mean", "definition", "뜻풀이", "뜻", "정의")
CLAVES_RADICAL = ("radical", "bushu", "부수")
CLAVES_TRAZOS = ("stroke", "획수", "획")


@dataclass
class HanjaNaver:
    hanja: str
    hun_eum: str = ""              # significado + lectura, p.ej. "물 수"
    romanizacion: str = ""         # lectura romanizada derivada del hangul
    definicion: List[str] = field(default_factory=list)   # 뜻풀이 / acepciones
    origen: str = ""                # 자원풀이 — explicación de origen/etimología
    radical: str = ""               # 부수
    trazos: str = ""                # 총 획수
    fuente: str = "Naver 한자사전"
    encontrado: bool = False


# --------------------------------------------------------------------
# Romanización simplificada (Revised Romanization) para el bloque de
# lectura hangul del 훈음, por si Naver no trae una romanización lista.
# Cubre los bloques silábicos completos de hangul (가-힣).
# --------------------------------------------------------------------
_CHO = ["g", "kk", "n", "d", "tt", "r", "m", "b", "pp", "s", "ss", "",
        "j", "jj", "c", "k", "t", "p", "h"]
_JUNG = ["a", "ae", "ya", "yae", "eo", "e", "yeo", "ye", "o", "wa", "wae",
         "oe", "yo", "u", "wo", "we", "wi", "yu", "eu", "ui", "i"]
_JONG = ["", "g", "kk", "gs", "n", "nj", "nh", "d", "l", "lg", "lm", "lb",
         "ls", "lt", "lp", "lh", "m", "b", "bs", "s", "ss", "ng", "j",
         "c", "k", "t", "p", "h"]


def _romanizar_hangul(texto: str) -> str:
    salida = []
    for ch in texto:
        code = ord(ch)
        if 0xAC00 <= code <= 0xD7A3:
            idx = code - 0xAC00
            cho, resto = divmod(idx, 21 * 28)
            jung, jong = divmod(resto, 28)
            salida.append(_CHO[cho] + _JUNG[jung] + _JONG[jong])
        elif ch == " ":
            salida.append(" ")
        # se omiten caracteres no-hangul (puntuación, hanja, etc.)
    return "".join(salida).strip()


def _extraer_ultima_silaba_lectura(hun_eum: str) -> str:
    """De un 훈음 como '물 수' devuelve solo la lectura ('수') para romanizar
    de forma compacta, que es lo que normalmente se usa como romanización
    corta del carácter."""
    partes = hun_eum.strip().split()
    if not partes:
        return ""
    return partes[-1]


# --------------------------------------------------------------------
# Estrategia 1: API JSON interna del sitio (api3). El esquema exacto
# NO está confirmado (ver aviso arriba) — por eso se recorre el JSON
# completo buscando valores por el nombre de su llave en vez de asumir
# una ruta fija como json["a"]["b"]["c"].
# --------------------------------------------------------------------

def _walk(obj, ruta=""):
    """Generador que recorre un JSON anidado y produce (ruta, valor) para
    cada valor hoja de tipo string no vacío."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _walk(v, f"{ruta}.{k}" if ruta else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk(v, f"{ruta}[{i}]")
    elif isinstance(obj, str) and obj.strip():
        yield ruta, obj.strip()


def _clasificar_desde_json(data) -> HanjaNaver:
    info = HanjaNaver(hanja="")
    definiciones = []
    candidatos_origen = []

    for ruta, valor in _walk(data):
        ruta_lower = ruta.lower()
        if any(c.lower() in ruta_lower for c in CLAVES_RADICAL) and not info.radical:
            info.radical = valor
        elif any(c.lower() in ruta_lower for c in CLAVES_TRAZOS) and not info.trazos:
            if re.search(r"\d", valor):
                info.trazos = valor
        elif any(c.lower() in ruta_lower for c in CLAVES_HUNUM) and not info.hun_eum:
            info.hun_eum = valor
        elif any(c.lower() in ruta_lower for c in CLAVES_ORIGEN):
            candidatos_origen.append(valor)
        elif any(c.lower() in ruta_lower for c in CLAVES_DEFINICION):
            if valor not in definiciones:
                definiciones.append(valor)

    # Heurística de respaldo si las llaves no trajeron nada reconocible:
    # el 훈음 suele ser una cadena corta "<significado> <lectura>" de 2
    # palabras en hangul puro; el origen suele ser el texto más largo.
    if not info.hun_eum:
        for _, valor in _walk(data):
            palabras = valor.split()
            if len(palabras) == 2 and all(_es_hangul_puro(p) for p in palabras):
                info.hun_eum = valor
                break

    if candidatos_origen:
        info.origen = max(candidatos_origen, key=len)
    elif not definiciones:
        # último recurso: el string más largo de todo el documento
        todos = [v for _, v in _walk(data)]
        if todos:
            mas_largo = max(todos, key=len)
            if len(mas_largo) > 25:
                info.origen = mas_largo

    info.definicion = definiciones[:6]
    info.encontrado = bool(info.hun_eum or info.origen or info.definicion)
    return info


def _es_hangul_puro(s: str) -> bool:
    return bool(s) and all(0xAC00 <= ord(c) <= 0xD7A3 for c in s)


def _intentar_api(hanja: str) -> Optional[HanjaNaver]:
    params = {"query": hanja, "range": "all"}
    try:
        resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:  # noqa: BLE001
        log.info("[%s] API de Naver no disponible/esperada: %s", hanja, exc)
        return None

    info = _clasificar_desde_json(data)
    if info.encontrado:
        info.hanja = hanja
        return info
    return None


# --------------------------------------------------------------------
# Estrategia 2 (respaldo): leer el HTML de la página de búsqueda y
# tomar meta-etiquetas (og:description / description), que suelen
# traer un resumen del 훈음 y a veces una definición corta aunque la
# página esté armada con JavaScript.
# --------------------------------------------------------------------

def _intentar_html(hanja: str) -> Optional[HanjaNaver]:
    try:
        resp = requests.get(
            PAGE_URL, params={"query": hanja}, headers=HEADERS, timeout=TIMEOUT
        )
        resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        log.info("[%s] HTML de Naver no disponible: %s", hanja, exc)
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    info = HanjaNaver(hanja=hanja)

    meta = soup.find("meta", attrs={"property": "og:description"}) or soup.find(
        "meta", attrs={"name": "description"}
    )
    if meta and meta.get("content"):
        texto = meta["content"].strip()
        info.definicion = [texto]
        info.origen = ""  # las meta-etiquetas casi nunca traen el 자원풀이 completo
        # intenta reconocer un patrón "<significado> <lectura>" al inicio
        m = re.match(r"^([가-힣]+\s[가-힣]{1,2})", texto)
        if m:
            info.hun_eum = m.group(1)
        info.encontrado = True

    # También busca cualquier bloque de texto visible cuyo encabezado
    # contenga "자원" (origen), por si el HTML trae ese fragmento
    # pre-renderizado para SEO.
    for tag in soup.find_all(string=re.compile("자원")):
        contenedor = tag.find_parent()
        if contenedor:
            texto_bloque = contenedor.get_text(" ", strip=True)
            if len(texto_bloque) > len(info.origen):
                info.origen = texto_bloque
                info.encontrado = True

    return info if info.encontrado else None


def obtener_info(hanja: str) -> Optional[HanjaNaver]:
    """Intenta API y luego HTML; devuelve None si ninguna estrategia
    encontró datos (el llamador debe tener un respaldo local)."""
    info = _intentar_api(hanja)
    if info is None:
        info = _intentar_html(hanja)
    if info is not None:
        info.hanja = hanja
        if not info.romanizacion:
            info.romanizacion = _romanizar_hangul(_extraer_ultima_silaba_lectura(info.hun_eum))
    return info


def diagnostico(hanja: str = "水") -> None:
    """Imprime en crudo lo que devuelve cada estrategia, para depurar
    contra el sitio real desde Colab (donde sí hay internet)."""
    print(f"=== Diagnóstico Naver Hanja para: {hanja} ===\n")

    print("--- Intento 1: API JSON (api3) ---")
    try:
        resp = requests.get(API_URL, params={"query": hanja, "range": "all"}, headers=HEADERS, timeout=TIMEOUT)
        print(f"Status: {resp.status_code}")
        print(f"Content-Type: {resp.headers.get('content-type')}")
        print("Primeros 1500 caracteres de la respuesta:")
        print(resp.text[:1500])
    except Exception as exc:  # noqa: BLE001
        print(f"Falló: {exc}")

    print("\n--- Intento 2: HTML de la página de búsqueda ---")
    try:
        resp = requests.get(PAGE_URL, params={"query": hanja}, headers=HEADERS, timeout=TIMEOUT)
        print(f"Status: {resp.status_code}")
        print("Primeros 1500 caracteres del HTML:")
        print(resp.text[:1500])
    except Exception as exc:  # noqa: BLE001
        print(f"Falló: {exc}")

    print("\n--- Resultado combinado de obtener_info() ---")
    info = obtener_info(hanja)
    if info is None:
        print("No se pudo extraer nada. Revisa el crudo de arriba y pégamelo para ajustar el parser.")
    else:
        print(f"hun_eum: {info.hun_eum!r}")
        print(f"romanizacion: {info.romanizacion!r}")
        print(f"radical: {info.radical!r}")
        print(f"trazos: {info.trazos!r}")
        print(f"definicion: {info.definicion!r}")
        print(f"origen: {info.origen[:300]!r}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    diagnostico("水")
