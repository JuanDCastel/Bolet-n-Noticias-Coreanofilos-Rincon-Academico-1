# -*- coding: utf-8 -*-
"""
Genera el PDF final del boletín a partir de una plantilla HTML/CSS,
renderizada con wkhtmltopdf (motor WebKit).

¿Por qué HTML + wkhtmltopdf y no reportlab puro?
reportlab solo puede incrustar fuentes TrueType con contorno "glyf".
Las fuentes coreanas más comunes (Noto Sans CJK, Noto Sans KR) usan
contornos "CFF/PostScript" dentro de un contenedor .ttf/.otf, algo
que reportlab rechaza ("postscript outlines are not supported").
wkhtmltopdf renderiza con el motor de fuentes del sistema (vía
fontconfig), así que cualquier fuente coreana instalada con
`apt-get install fonts-noto-cjk` se ve perfecto sin conversiones.

Requisitos del sistema (una sola vez, en Colab o en el workflow de
GitHub Actions):
    apt-get install -y wkhtmltopdf fonts-noto-cjk

Páginas:
  - 1-2: noticias más relevantes, en coreano y en español.
  - 3 (aparte, con salto de página forzado): hanja del día.
"""

from __future__ import annotations

import html
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import List, Optional

from hanja_page import HanjaPagina

MESES_ES = [
    "", "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]

KOREAN_FONT_STACK = (
    "'Noto Sans CJK KR', 'Noto Sans KR', 'Malgun Gothic', "
    "'Apple SD Gothic Neo', sans-serif"
)


@dataclass
class Story:
    titulo_ko: str
    resumen_ko: str
    titulo_es: str
    resumen_es: str
    fuente: str
    enlace: str
    num_fuentes: int = 1


def _fecha_es(d: date) -> str:
    return f"{d.day} de {MESES_ES[d.month]} de {d.year}"


def _e(texto: str) -> str:
    return html.escape(texto or "", quote=False)


CSS = f"""
@page {{ size: Letter; margin: 18mm 20mm; }}
* {{ box-sizing: border-box; }}
body {{
    font-family: {KOREAN_FONT_STACK};
    color: #222;
    font-size: 10.3pt;
    line-height: 1.45;
}}
h1.boletin-titulo {{
    font-size: 20pt;
    margin: 0 0 2pt 0;
    color: #1a1a2e;
}}
p.fecha {{
    font-size: 10pt;
    color: #555566;
    margin: 0 0 14pt 0;
}}
div.historia {{
    margin-bottom: 11pt;
    padding-bottom: 9pt;
    border-bottom: 0.5pt solid #dddddd;
}}
div.historia:last-child {{ border-bottom: none; }}
p.titulo-es {{
    font-weight: 700;
    font-size: 12.2pt;
    color: #1a1a2e;
    margin: 0 0 3pt 0;
}}
p.resumen-es {{
    margin: 0 0 6pt 0;
    font-size: 9.6pt;
}}
p.titulo-ko {{
    font-weight: 700;
    font-size: 11.3pt;
    color: #003f88;
    margin: 0 0 3pt 0;
}}
p.resumen-ko {{
    margin: 0 0 5pt 0;
    font-size: 9.6pt;
    color: #333;
}}
p.meta {{
    font-size: 7.6pt;
    color: #8888a0;
    margin: 0;
}}
.salto-pagina {{ page-break-before: always; }}
.hanja-seccion {{
    text-align: center;
    padding-top: 14mm;
}}
.hanja-titulo {{
    font-size: 15pt;
    font-weight: 700;
    color: #1a1a2e;
    margin-bottom: 9mm;
}}
.hanja-caracter {{
    font-size: 72pt;
    line-height: 1;
    margin-bottom: 5mm;
}}
.hanja-lectura {{
    font-size: 13.5pt;
    font-weight: 700;
    color: #003f88;
    margin-bottom: 1.5mm;
}}
.hanja-meta {{
    font-size: 8.5pt;
    color: #8888a0;
    margin-bottom: 6mm;
}}
.hanja-bloque {{
    text-align: left;
    max-width: 140mm;
    margin: 0 auto 6mm auto;
}}
.hanja-subtitulo {{
    font-size: 10pt;
    font-weight: 700;
    color: #003f88;
    text-transform: uppercase;
    letter-spacing: 0.4pt;
    margin: 0 0 2mm 0;
}}
.hanja-cuerpo {{
    font-size: 10.3pt;
    line-height: 1.5;
    margin: 0 0 2mm 0;
}}
.hanja-definicion-item {{
    font-size: 10.3pt;
    line-height: 1.5;
    margin: 0 0 1.5mm 0;
}}
.hanja-respaldo-aviso {{
    font-size: 8pt;
    color: #a05a2c;
    max-width: 140mm;
    margin: 4mm auto 0 auto;
    text-align: left;
    font-style: italic;
}}
"""


def _render_historias_html(stories: List[Story]) -> str:
    bloques = []
    for s in stories:
        cobertura = f" · cubierto por {s.num_fuentes} medios" if s.num_fuentes > 1 else ""
        bloques.append(f"""
        <div class="historia">
            <p class="titulo-es">{_e(s.titulo_es)}</p>
            <p class="resumen-es">{_e(s.resumen_es)}</p>
            <p class="titulo-ko">{_e(s.titulo_ko)}</p>
            <p class="resumen-ko">{_e(s.resumen_ko)}</p>
            <p class="meta">Fuente: {_e(s.fuente)}{cobertura}</p>
        </div>""")
    return "\n".join(bloques)


def _render_hanja_html(hanja: HanjaPagina) -> str:
    meta_partes = []
    if hanja.radical:
        meta_partes.append(f"Radical (부수): {_e(hanja.radical)}")
    if hanja.trazos:
        meta_partes.append(f"Trazos: {_e(hanja.trazos)}")
    meta_html = (
        f'<p class="hanja-meta">{" · ".join(meta_partes)}</p>' if meta_partes else ""
    )

    definicion_html = ""
    if hanja.definicion_es:
        items = "".join(
            f'<p class="hanja-definicion-item">{i + 1}. {_e(d)}</p>'
            for i, d in enumerate(hanja.definicion_es)
        )
        definicion_html = f"""
        <div class="hanja-bloque">
            <p class="hanja-subtitulo">Definición</p>
            {items}
        </div>"""

    origen_html = ""
    if hanja.origen_es:
        origen_html = f"""
        <div class="hanja-bloque">
            <p class="hanja-subtitulo">Origen del carácter (자원풀이)</p>
            <p class="hanja-cuerpo">{_e(hanja.origen_es)}</p>
        </div>"""

    aviso_html = ""
    if hanja.es_respaldo_local:
        aviso_html = (
            '<p class="hanja-respaldo-aviso">'
            "Nota: hoy no se pudo consultar el diccionario de Naver (hanja.dict.naver.com); "
            "se muestra el significado del banco de respaldo local."
            "</p>"
        )

    return f"""
    <div class="hanja-seccion">
        <div class="hanja-titulo">Hanja del día (한자)</div>
        <div class="hanja-caracter">{_e(hanja.hanja)}</div>
        <div class="hanja-lectura">{_e(hanja.hun_eum_ko)} ({_e(hanja.romanizacion)})</div>
        {meta_html}
        {definicion_html}
        {origen_html}
        {aviso_html}
    </div>"""


def construir_html(stories: List[Story], hanja: HanjaPagina, fecha: Optional[date] = None) -> str:
    fecha = fecha or date.today()
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<style>{CSS}</style>
</head>
<body>
    <h1 class="boletin-titulo">Boletín de Corea del Sur</h1>
    <p class="fecha">{_e(_fecha_es(fecha))}</p>
    {_render_historias_html(stories)}
    <div class="salto-pagina">
        {_render_hanja_html(hanja)}
    </div>
</body>
</html>"""


def _contar_paginas_pdf(pdf_path: str) -> int:
    data = Path(pdf_path).read_bytes()
    return len(re.findall(rb"/Type\s*/Page(?!s)", data))


def _wkhtmltopdf_bin() -> str:
    exe = shutil.which("wkhtmltopdf")
    if not exe:
        raise RuntimeError(
            "No se encontró 'wkhtmltopdf' en el sistema. Instálalo con:\n"
            "    apt-get install -y wkhtmltopdf fonts-noto-cjk"
        )
    return exe


def _render_pdf(html_str: str, output_path: str) -> None:
    exe = _wkhtmltopdf_bin()
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(html_str)
        tmp_html = f.name
    try:
        subprocess.run(
            [
                exe,
                "--quiet",
                "--enable-local-file-access",
                "--encoding", "utf-8",
                tmp_html,
                output_path,
            ],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"wkhtmltopdf falló: {exc.stderr.decode('utf-8', 'ignore')}"
        ) from exc
    finally:
        Path(tmp_html).unlink(missing_ok=True)


def construir_pdf(
    stories: List[Story],
    hanja: HanjaPagina,
    output_path: str,
    fecha: Optional[date] = None,
    max_paginas_noticias: int = 2,
) -> int:
    """
    Construye el PDF y devuelve el número total de páginas.
    Si las noticias no caben en `max_paginas_noticias`, recorta la
    historia menos relevante (se asume que `stories` ya viene
    ordenada de más a menos relevante) y reintenta.
    """
    historias = list(stories)
    while True:
        html_str = construir_html(historias, hanja, fecha)
        _render_pdf(html_str, output_path)
        paginas_totales = _contar_paginas_pdf(output_path)
        paginas_noticias = paginas_totales - 1  # la última página es la de hanja
        if paginas_noticias <= max_paginas_noticias or len(historias) <= 1:
            break
        historias = historias[:-1]
    return paginas_totales


if __name__ == "__main__":
    from hanja_db import hanja_of_the_day

    mock_stories = [
        Story(
            titulo_ko="정부, 내년도 예산안 발표",
            resumen_ko="정부가 29일 내년도 예산안을 발표했다. 복지와 국방 분야 지출이 늘어난 것이 특징이다.",
            titulo_es="El gobierno presenta el presupuesto para el próximo año",
            resumen_es="El gobierno surcoreano presentó el 29 su propuesta de presupuesto, con mayor gasto en bienestar social y defensa.",
            fuente="Dong-a Ilbo",
            enlace="https://example.com/1",
            num_fuentes=3,
        ),
        Story(
            titulo_ko="한국 축구, 아시안컵 우승",
            resumen_ko="한국 축구 국가대표팀이 아시안컵 결승에서 승리하며 우승을 차지했다.",
            titulo_es="La selección de fútbol de Corea gana la Copa Asiática",
            resumen_es="La selección nacional de Corea del Sur venció en la final de la Copa Asiática y se consagró campeona.",
            fuente="Chosun Ilbo",
            enlace="https://example.com/2",
            num_fuentes=1,
        ),
        Story(
            titulo_ko="수도권 아파트 가격 상승세 지속",
            resumen_ko="서울을 포함한 수도권 아파트 가격이 세 달 연속 상승세를 보이고 있다.",
            titulo_es="Los precios de apartamentos en el área metropolitana siguen subiendo",
            resumen_es="Los precios de los apartamentos en Seúl y alrededores subieron por tercer mes consecutivo.",
            fuente="JoongAng Ilbo",
            enlace="https://example.com/3",
            num_fuentes=1,
        ),
        Story(
            titulo_ko="한국은행, 기준금리 동결",
            resumen_ko="한국은행이 기준금리를 현 수준에서 동결하기로 결정했다. 물가 안정을 고려한 조치로 풀이된다.",
            titulo_es="El Banco de Corea mantiene sin cambios la tasa de interés",
            resumen_es="El Banco de Corea decidió mantener la tasa de interés de referencia, en una medida vinculada a la estabilidad de precios.",
            fuente="Korea Herald",
            enlace="https://example.com/4",
            num_fuentes=2,
        ),
        Story(
            titulo_ko="케이팝 그룹, 월드투어 발표",
            resumen_ko="인기 케이팝 그룹이 내년 상반기 월드투어 일정을 공개했다.",
            titulo_es="Grupo de K-pop anuncia gira mundial",
            resumen_es="Un popular grupo de K-pop reveló las fechas de su gira mundial para el primer semestre del próximo año.",
            fuente="Korea.net (español)",
            enlace="https://example.com/5",
            num_fuentes=1,
        ),
    ]

    # Simulación de una respuesta "rica" de Naver (significado + varias
    # acepciones de la definición + origen/etimología), ya que este
    # entorno de desarrollo no tiene salida a internet hacia Naver.
    hanja_naver_mock = HanjaPagina(
        hanja="水",
        hun_eum_ko="물 수",
        romanizacion="su",
        definicion_es=[
            "Agua, líquido en general.",
            "Uno de los cinco elementos (오행) de la cosmología tradicional de Asia oriental.",
            "Por extensión: ríos, mares o cuerpos de agua.",
        ],
        origen_es=(
            "Carácter pictográfico (상형자): representa el trazo sinuoso de una "
            "corriente de agua fluyendo entre dos orillas. Es uno de los 214 "
            "radicales tradicionales del chino y aparece como componente en "
            "muchísimos caracteres relacionados con líquidos (예: 江, 河, 海)."
        ),
        radical="水 (물수) · 0 trazos adicionales",
        trazos="총 4획",
        es_respaldo_local=False,
    )
    paginas = construir_pdf(
        mock_stories,
        hanja_naver_mock,
        output_path="/tmp/corea_news/output/boletin_prueba.pdf",
    )
    print(f"PDF generado con {paginas} páginas (hanja vía Naver).")

    # Simulación del modo de respaldo (cuando Naver no responde ese día).
    hanja_respaldo_mock = HanjaPagina(
        hanja="月",
        hun_eum_ko="달 월",
        romanizacion="wol",
        definicion_es=["Luna; también 'mes'."],
        origen_es="",
        es_respaldo_local=True,
    )
    paginas2 = construir_pdf(
        mock_stories[:2],
        hanja_respaldo_mock,
        output_path="/tmp/corea_news/output/boletin_prueba_respaldo.pdf",
    )
    print(f"PDF generado con {paginas2} páginas (hanja de respaldo local).")
