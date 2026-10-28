# -*- coding: utf-8 -*-
"""
Catálogo de hanja (한자) para la sección "Hanja del día".

Este archivo cumple dos roles:

  1. `hanja_of_the_day(fecha)` elige, de forma determinista según el
     día del año, QUÉ carácter le toca al boletín de hoy. Ese carácter
     es el que se le pide al diccionario de Naver (ver `naver_hanja.py`)
     para traer el significado, la definición y el origen/etimología
     completos tal como los da Naver.

  2. Sirve como **respaldo local** si Naver no responde ese día (sitio
     caído, cambio de estructura, sin internet, etc.): en ese caso se
     usa el `significado` corto de aquí en vez de dejar la página de
     hanja vacía. main.py marca claramente en el PDF cuándo el dato
     viene de este respaldo y no de Naver, para no hacerlo pasar por
     la definición/origen reales del diccionario.

Cada entrada:
  hanja        : el carácter chino usado en coreano
  hun_eum      : lectura coreana tradicional "significado + sonido" (훈음)
  romanizacion : romanización revisada del sonido coreano
  significado  : traducción/explicación breve en español (solo para el
                 modo de respaldo; la versión completa del día a día
                 sale de Naver, no de aquí)
  ejemplo      : (palabra_hangul, romanizacion, significado_es) o None

La lista cubre los hanja básicos de nivel educativo (8~6급 del examen
de aptitud de hanja), por lo que son los más usados como raíz de
palabras que aparecen a diario en la prensa coreana (국가, 경제, 정치,
사회, 문화, 교육, 시간, 사람, etc.).
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import Optional, Tuple


@dataclass(frozen=True)
class Hanja:
    hanja: str
    hun_eum: str
    romanizacion: str
    significado: str
    ejemplo: Optional[Tuple[str, str, str]] = None


HANJA_DB = [
    Hanja("一", "한 일", "il", "Uno, el número 1.", ("一生", "ilsaeng", "toda la vida")),
    Hanja("二", "두 이", "i", "Dos, el número 2.", ("二月", "iwol", "febrero (2º mes)")),
    Hanja("三", "석 삼", "sam", "Tres, el número 3.", ("三國", "samguk", "los Tres Reinos")),
    Hanja("四", "넉 사", "sa", "Cuatro, el número 4.", ("四季", "sagye", "las cuatro estaciones")),
    Hanja("五", "다섯 오", "o", "Cinco, el número 5.", ("五感", "ogam", "los cinco sentidos")),
    Hanja("六", "여섯 육", "yuk", "Seis, el número 6.", ("六月", "yuwol", "junio (6º mes)")),
    Hanja("七", "일곱 칠", "chil", "Siete, el número 7.", ("七夕", "chilseok", "festival de Chilseok")),
    Hanja("八", "여덟 팔", "pal", "Ocho, el número 8.", ("八道", "paldo", "las ocho provincias tradicionales")),
    Hanja("九", "아홉 구", "gu", "Nueve, el número 9.", ("九日", "guil", "día nueve")),
    Hanja("十", "열 십", "sip", "Diez, el número 10.", ("十年", "sipnyeon", "diez años")),
    Hanja("人", "사람 인", "in", "Persona, ser humano.", ("人生", "insaeng", "la vida (humana)")),
    Hanja("山", "메 산", "san", "Montaña.", ("山水", "sansu", "paisaje de montañas y aguas")),
    Hanja("水", "물 수", "su", "Agua.", ("水道", "sudo", "sistema de agua potable")),
    Hanja("火", "불 화", "hwa", "Fuego.", ("火山", "hwasan", "volcán")),
    Hanja("木", "나무 목", "mok", "Árbol, madera.", ("木曜日", "mogyoil", "jueves")),
    Hanja("金", "쇠 금 / 성 김", "geum / gim", "Metal, oro; también el apellido Kim.", ("黃金", "hwanggeum", "oro (metal precioso)")),
    Hanja("土", "흙 토", "to", "Tierra, suelo.", ("土地", "toji", "terreno")),
    Hanja("日", "날 일", "il", "Día, sol; también 'Japón' en compuestos.", ("日記", "ilgi", "diario personal")),
    Hanja("月", "달 월", "wol", "Luna; también 'mes'.", ("月給", "wolgeup", "salario mensual")),
    Hanja("年", "해 년", "nyeon", "Año.", ("年金", "nyeongeum", "pensión")),
    Hanja("大", "큰 대", "dae", "Grande.", ("大統領", "daetongnyeong", "presidente (de un país)")),
    Hanja("小", "작을 소", "so", "Pequeño.", ("小說", "soseol", "novela")),
    Hanja("中", "가운데 중", "jung", "Medio, centro.", ("中心", "jungsim", "centro")),
    Hanja("國", "나라 국", "guk", "País, nación.", ("國家", "gukga", "nación, Estado")),
    Hanja("王", "임금 왕", "wang", "Rey.", ("王國", "wangguk", "reino")),
    Hanja("女", "계집 녀", "nyeo", "Mujer.", ("女子", "yeoja", "mujer")),
    Hanja("男", "사내 남", "nam", "Hombre.", ("男子", "namja", "hombre")),
    Hanja("子", "아들 자", "ja", "Hijo; también sufijo de 'persona/cosa'.", ("子女", "janyeo", "hijos (hijo e hija)")),
    Hanja("父", "아비 부", "bu", "Padre.", ("父母", "bumo", "padres")),
    Hanja("母", "어미 모", "mo", "Madre.", ("母國", "moguk", "patria, país natal")),
    Hanja("學", "배울 학", "hak", "Aprender, estudiar.", ("學校", "hakgyo", "escuela")),
    Hanja("校", "학교 교", "gyo", "Escuela.", ("校長", "gyojang", "director de escuela")),
    Hanja("先", "먼저 선", "seon", "Primero, antes.", ("先生", "seonsaeng", "maestro/a, señor/a")),
    Hanja("生", "날 생", "saeng", "Nacer, vida.", ("生産", "saengsan", "producción")),
    Hanja("門", "문 문", "mun", "Puerta.", ("大門", "daemun", "puerta principal")),
    Hanja("車", "수레 거 / 차", "geo / cha", "Vehículo, carro.", ("自動車", "jadongcha", "automóvil")),
    Hanja("電", "번개 전", "jeon", "Electricidad, relámpago.", ("電話", "jeonhwa", "teléfono")),
    Hanja("話", "말씀 화", "hwa", "Habla, palabra.", ("對話", "daehwa", "diálogo")),
    Hanja("春", "봄 춘", "chun", "Primavera.", ("春風", "chunpung", "brisa de primavera")),
    Hanja("夏", "여름 하", "ha", "Verano.", ("夏期", "hagi", "temporada de verano")),
    Hanja("秋", "가을 추", "chu", "Otoño.", ("秋夕", "chuseok", "Chuseok, fiesta de la cosecha")),
    Hanja("冬", "겨울 동", "dong", "Invierno.", ("冬眠", "dongmyeon", "hibernación")),
    Hanja("東", "동녘 동", "dong", "Este.", ("東海", "donghae", "Mar del Este")),
    Hanja("西", "서녘 서", "seo", "Oeste.", ("西洋", "seoyang", "Occidente")),
    Hanja("南", "남녘 남", "nam", "Sur.", ("南北", "nambuk", "sur y norte")),
    Hanja("北", "북녘 북", "buk", "Norte.", ("北韓", "bukhan", "Corea del Norte")),
    Hanja("心", "마음 심", "sim", "Corazón, mente.", ("中心", "jungsim", "centro")),
    Hanja("愛", "사랑 애", "ae", "Amor.", ("愛情", "aejeong", "cariño, afecto")),
    Hanja("平", "평평할 평", "pyeong", "Plano, igualdad, paz.", ("平和", "pyeonghwa", "paz")),
    Hanja("和", "화할 화", "hwa", "Armonía, paz.", ("平和", "pyeonghwa", "paz")),
    Hanja("時", "때 시", "si", "Tiempo, hora.", ("時間", "sigan", "tiempo, hora")),
    Hanja("間", "사이 간", "gan", "Entre, espacio, intervalo.", ("時間", "sigan", "tiempo, hora")),
    Hanja("命", "목숨 명", "myeong", "Vida, destino.", ("生命", "saengmyeong", "vida (biológica)")),
    Hanja("新", "새 신", "sin", "Nuevo.", ("新聞", "sinmun", "periódico (noticias nuevas)")),
    Hanja("古", "예 고", "go", "Antiguo.", ("古代", "godae", "la antigüedad")),
    Hanja("民", "백성 민", "min", "Pueblo, gente.", ("國民", "gungmin", "ciudadanía, pueblo de una nación")),
    Hanja("政", "정사 정", "jeong", "Gobierno, política.", ("政治", "jeongchi", "política")),
    Hanja("治", "다스릴 치", "chi", "Gobernar, administrar.", ("政治", "jeongchi", "política")),
    Hanja("經", "지날 경", "gyeong", "Pasar, transcurrir; 'clásico'.", ("經濟", "gyeongje", "economía")),
    Hanja("濟", "건널 제", "je", "Cruzar, ayudar, socorrer.", ("經濟", "gyeongje", "economía")),
    Hanja("文", "글월 문", "mun", "Escritura, letras, cultura.", ("文化", "munhwa", "cultura")),
    Hanja("化", "될 화", "hwa", "Transformarse, convertirse.", ("文化", "munhwa", "cultura")),
    Hanja("社", "모일 사", "sa", "Reunirse, sociedad.", ("社會", "sahoe", "sociedad")),
    Hanja("會", "모일 회", "hoe", "Reunirse, encuentro.", ("社會", "sahoe", "sociedad")),
    Hanja("世", "인간 세", "se", "Mundo, generación.", ("世界", "segye", "el mundo")),
    Hanja("界", "지경 계", "gye", "Límite, frontera, ámbito.", ("世界", "segye", "el mundo")),
]


def hanja_of_the_day(fecha: date) -> Hanja:
    """Devuelve el hanja del día de forma determinista según el día del año."""
    idx = (fecha.timetuple().tm_yday - 1) % len(HANJA_DB)
    return HANJA_DB[idx]


if __name__ == "__main__":
    from datetime import date as _date
    h = hanja_of_the_day(_date.today())
    print(f"{h.hanja}  ({h.hun_eum} / {h.romanizacion})")
    print(h.significado)
    if h.ejemplo:
        palabra, rom, es = h.ejemplo
        print(f"Ejemplo: {palabra} ({rom}) — {es}")
