# -*- coding: utf-8 -*-
"""
Recolección de titulares desde las fuentes de noticias de Corea del Sur.

Estrategia por fuente (en este orden, hasta que una funcione):
  1. Feed RSS directo conocido (el más estable y rápido).
  2. Descubrimiento automático de RSS: busca <link rel="alternate"
     type="application/rss+xml"> en el <head> de la página principal.
  3. Google News RSS filtrado por sitio (site:dominio), como última
     red de seguridad para fuentes sin RSS propio o cuyo feed cambió.

NOTA IMPORTANTE: este módulo necesita internet real (se ejecuta en
Google Colab o en el runner de GitHub Actions). No se puede probar
dentro de un entorno sandbox sin salida a internet; si una fuente
cambia su estructura, el error quedará registrado en el log con el
nombre de la fuente para poder ajustarla.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from urllib.parse import quote

import feedparser
import requests
from bs4 import BeautifulSoup

from models import Item, Source

log = logging.getLogger("corea_news.sources")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 BoletinCoreaBot/1.0"
    )
}
TIMEOUT = 15


# --------------------------------------------------------------------------
# Catálogo de fuentes pedidas por el usuario.
#
# Para el texto "original coreano" usamos los diarios coreanos
# (Dong-a Ilbo, Chosun Ilbo, JoongAng Ilbo). KBS World en español y
# Korea.net se usan como señal de relevancia/contexto (si una noticia
# también aparece ahí, confirma que es importante), y Korea Herald
# aporta el ángulo en inglés. Ver dedup.py para cómo se combinan.
# --------------------------------------------------------------------------
SOURCES: List[Source] = [
    Source(
        nombre="Dong-a Ilbo",
        idioma="ko",
        rss_candidatos=["https://rss.donga.com/total.xml"],
        homepage="https://www.donga.com/",
        google_news_dominio="donga.com",
    ),
    Source(
        nombre="Chosun Ilbo",
        idioma="ko",
        rss_candidatos=[
            "https://www.chosun.com/arc/outboundfeeds/rss/",
            "https://www.chosun.com/rss.xml",
        ],
        homepage="https://www.chosun.com/",
        google_news_dominio="chosun.com",
    ),
    Source(
        nombre="JoongAng Ilbo",
        idioma="ko",
        rss_candidatos=["https://rss.joins.com/joins_news_list.xml"],
        homepage="https://www.joongang.co.kr/",
        google_news_dominio="joongang.co.kr",
    ),
    Source(
        nombre="Korea Herald",
        idioma="en",
        rss_candidatos=["https://www.koreaherald.com/rss/newsAll"],
        homepage="https://www.koreaherald.com/",
        google_news_dominio="koreaherald.com",
    ),
    Source(
        nombre="KBS World (español)",
        idioma="es",
        rss_candidatos=[],
        homepage="https://world.kbs.co.kr/service/news_list.htm?lang=s",
        google_news_dominio="world.kbs.co.kr",
    ),
    Source(
        nombre="Korea.net (español)",
        idioma="es",
        rss_candidatos=[],
        homepage="https://spanish.korea.net/",
        google_news_dominio="spanish.korea.net",
    ),
]


def _parse_feed(url: str, fuente: str, idioma: str, limite: int) -> List[Item]:
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    parsed = feedparser.parse(resp.content)
    if parsed.bozo and not parsed.entries:
        raise ValueError(f"RSS inválido en {url}: {parsed.bozo_exception}")

    items = []
    for e in parsed.entries[:limite]:
        pub = None
        if getattr(e, "published_parsed", None):
            pub = datetime(*e.published_parsed[:6], tzinfo=timezone.utc)
        items.append(
            Item(
                titulo=e.get("title", "").strip(),
                enlace=e.get("link", "").strip(),
                fuente=fuente,
                idioma=idioma,
                publicado=pub,
                resumen=BeautifulSoup(e.get("summary", ""), "html.parser").get_text(" ", strip=True),
            )
        )
    return items


def _discover_rss(homepage: str) -> Optional[str]:
    """Busca un <link rel="alternate" type="application/rss+xml"> en la portada."""
    try:
        resp = requests.get(homepage, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        link = soup.find("link", attrs={"type": "application/rss+xml"})
        if link and link.get("href"):
            href = link["href"]
            if href.startswith("//"):
                href = "https:" + href
            elif href.startswith("/"):
                from urllib.parse import urljoin
                href = urljoin(homepage, href)
            return href
    except Exception as exc:  # noqa: BLE001
        log.info("No se pudo auto-descubrir RSS en %s: %s", homepage, exc)
    return None


def _google_news_fallback(dominio: str, fuente: str, idioma: str, limite: int, dias: int) -> List[Item]:
    """
    Último recurso: Google News RSS filtrado por sitio. No es una API
    oficial de Google (puede cambiar sin aviso), pero es ampliamente
    usado como red de seguridad cuando un medio no ofrece RSS propio
    o lo cambió de dirección.
    """
    hl_gl = {
        "ko": ("hl=ko&gl=KR&ceid=KR:ko"),
        "en": ("hl=en-US&gl=US&ceid=US:en"),
        "es": ("hl=es-419&gl=MX&ceid=MX:es-419"),
    }[idioma]
    q = quote(f"site:{dominio} when:{dias}d")
    url = f"https://news.google.com/rss/search?q={q}&{hl_gl}"
    items = _parse_feed(url, fuente, idioma, limite)
    # Google News antepone a veces " - NombreMedio" al título; se deja
    # tal cual porque sigue siendo el titular real del artículo.
    return items


def fetch_source(source: Source, limite: int = 12, dias: int = 2) -> List[Item]:
    """Intenta cada estrategia en orden y devuelve la primera que funcione."""
    intentos = []

    for url in source.rss_candidatos:
        intentos.append(("rss directo", url))
    if source.homepage:
        descubierto = _discover_rss(source.homepage)
        if descubierto:
            intentos.append(("rss auto-descubierto", descubierto))

    for metodo, url in intentos:
        try:
            items = _parse_feed(url, source.nombre, source.idioma, limite)
            if items:
                log.info("[%s] OK via %s (%s) — %d items", source.nombre, metodo, url, len(items))
                return items
        except Exception as exc:  # noqa: BLE001
            log.info("[%s] falló %s (%s): %s", source.nombre, metodo, url, exc)

    if source.google_news_dominio:
        try:
            items = _google_news_fallback(
                source.google_news_dominio, source.nombre, source.idioma, limite, dias
            )
            if items:
                log.info("[%s] OK via Google News fallback — %d items", source.nombre, len(items))
                return items
        except Exception as exc:  # noqa: BLE001
            log.warning("[%s] también falló el fallback de Google News: %s", source.nombre, exc)

    log.error("[%s] no se pudieron obtener titulares por ningún método", source.nombre)
    return []


def fetch_all(limite_por_fuente: int = 12, dias: int = 2) -> List[Item]:
    todos: List[Item] = []
    for source in SOURCES:
        todos.extend(fetch_source(source, limite=limite_por_fuente, dias=dias))
    return todos


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    for it in fetch_all():
        print(f"[{it.fuente}] {it.titulo}  -> {it.enlace}")
