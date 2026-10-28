# -*- coding: utf-8 -*-
"""
Traducción al español latinoamericano con DeepL.

Requiere la variable de entorno DEEPL_API_KEY (clave gratuita o de
pago de https://www.deepl.com/pro-api). En Colab se setea con:

    import os
    os.environ["DEEPL_API_KEY"] = "tu-clave-aqui"

o mejor, usando `google.colab.userdata` (ver celda de configuración
del notebook) para no dejar la clave escrita en el código.

DeepL no tiene una variante específica "español latinoamericano"
como target_lang (solo differentia target_lang="ES" vs variantes de
EN/PT); por eso se traduce a "ES" y se le pide explícitamente, vía
`context`, que use español neutro/latinoamericano, y se evita
vocabulario marcadamente de España cuando el propio texto lo permite.
Para la mayoría de noticias esto no cambia el resultado de forma
perceptible, pero queda documentado por si se nota algún
"vosotros"/"vale" que convenga revisar a mano.
"""

from __future__ import annotations

import functools
import logging
import os
from typing import Optional

log = logging.getLogger("corea_news.translate")

_CLIENT = None


def _get_client():
    global _CLIENT
    if _CLIENT is None:
        import deepl  # import diferido: no todos los usos de este módulo necesitan red

        api_key = os.environ.get("DEEPL_API_KEY")
        if not api_key:
            raise RuntimeError(
                "Falta la variable de entorno DEEPL_API_KEY. "
                "Consigue una clave gratuita en https://www.deepl.com/pro-api "
                "y asígnala antes de ejecutar el pipeline."
            )
        _CLIENT = deepl.Translator(api_key)
    return _CLIENT


CONTEXTO_NOTICIAS = (
    "Noticias de Corea del Sur para un boletín en español "
    "latinoamericano neutro (evitar 'vosotros', 'vale', "
    "modismos de España)."
)

CONTEXTO_HANJA = (
    "Entrada de un diccionario de caracteres chinos (hanja) usados en "
    "coreano: significado, definición o explicación etimológica/origen "
    "del carácter. Traducir a un español latinoamericano neutro, claro "
    "y educativo (evitar 'vosotros', 'vale', modismos de España), "
    "preservando el sentido técnico/etimológico del texto."
)


@functools.lru_cache(maxsize=512)
def traducir(
    texto: str,
    origen: Optional[str] = None,
    destino: str = "ES",
    contexto: str = CONTEXTO_NOTICIAS,
) -> str:
    """
    Traduce `texto` al español (DeepL target_lang="ES").
    `origen` es opcional ("KO", "EN"); si se omite, DeepL autodetecta.
    `contexto` ajusta el tono/dominio de la traducción (noticias vs.
    entradas de diccionario de hanja, por ejemplo).
    El resultado se cachea en memoria del proceso para no re-traducir
    el mismo texto dos veces durante una misma corrida.
    """
    texto = (texto or "").strip()
    if not texto:
        return ""
    client = _get_client()
    resultado = client.translate_text(
        texto,
        source_lang=origen,
        target_lang=destino,
        context=contexto,
    )
    return resultado.text


def traducir_hanja(texto: str, origen: Optional[str] = "KO") -> str:
    """Atajo para traducir contenido del diccionario de hanja (definición,
    origen/etimología) con el contexto adecuado en vez del de noticias."""
    return traducir(texto, origen=origen, contexto=CONTEXTO_HANJA)


def traducir_lote(textos, origen: Optional[str] = None) -> list:
    """Traduce varios textos preservando el orden. Usa una sola llamada
    a la API cuando es posible, para ahorrar cuota y tiempo."""
    textos = list(textos)
    no_vacios = [(i, t) for i, t in enumerate(textos) if (t or "").strip()]
    if not no_vacios:
        return ["" for _ in textos]

    client = _get_client()
    resultados = client.translate_text(
        [t for _, t in no_vacios],
        source_lang=origen,
        target_lang="ES",
        context=(
            "Noticias de Corea del Sur para un boletín en español "
            "latinoamericano neutro (evitar 'vosotros', 'vale', "
            "modismos de España)."
        ),
    )
    salida = ["" for _ in textos]
    for (i, _), r in zip(no_vacios, resultados):
        salida[i] = r.text
    return salida


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(traducir("정부가 내년도 예산안을 발표했다.", origen="KO"))
