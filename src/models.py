# -*- coding: utf-8 -*-
"""Estructuras de datos compartidas entre los módulos del pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class Item:
    titulo: str
    enlace: str
    fuente: str          # nombre legible de la fuente, p.ej. "Dong-a Ilbo"
    idioma: str           # "ko", "en" o "es"
    publicado: Optional[datetime] = None
    resumen: str = ""


@dataclass
class Source:
    nombre: str
    idioma: str                                # idioma principal del texto que entrega
    rss_candidatos: List[str] = field(default_factory=list)
    homepage: Optional[str] = None             # para auto-descubrimiento de RSS
    google_news_dominio: Optional[str] = None  # fallback site:dominio
