# Boletín diario de Corea del Sur

Genera automáticamente un PDF de máximo 2 páginas con las noticias más
relevantes de Corea del Sur del día, en **coreano original** y su
**traducción al español latinoamericano** (DeepL), más una página
aparte con el **hanja del día**: significado, definición y
origen/etimología (자원풀이), tomados del **Diccionario de Hanja de
Naver** (hanja.dict.naver.com) y traducidos al español.

## Cómo se decide qué es "lo más relevante"

Se recolectan titulares de 6 fuentes:

- **Dong-a Ilbo, Chosun Ilbo, JoongAng Ilbo** → dan el texto **en coreano original**.
- **Korea Herald, KBS World (español), Korea.net (español)** → se usan como
  señal de relevancia: si una noticia también aparece ahí, confirma que
  es importante, aunque no den el texto coreano.

Se agrupan los titulares que hablan del mismo hecho (comparando los
títulos ya traducidos a un idioma común) y se ordenan por **cuántas
fuentes distintas cubren cada noticia**. Solo entran al boletín las
noticias que tengan al menos un artículo en coreano original.

## Cómo se arma la página de hanja (Naver)

`naver_hanja.py` consulta `hanja.dict.naver.com` para el carácter del
día (elegido de forma determinista por `hanja_db.py`, rotando sin
repetirse). Como Naver no publica una API oficial, el módulo prueba en
este orden:

1. La API JSON interna que usa el sitio (`api3`).
2. Si no trae nada útil, el HTML de la página de búsqueda (metadatos
   `og:description` y bloques de texto cercanos a "자원").
3. Si ninguna de las dos funciona ese día, cae al **banco local de
   respaldo** (`hanja_db.py`) — el PDF nunca se queda sin página de
   hanja, pero esa nota de respaldo queda indicada en el propio PDF,
   para no hacerla pasar por datos reales de Naver.

**Importante:** este scraper se escribió sin poder probarlo contra el
sitio real (el entorno de desarrollo no tenía salida a internet hacia
Naver), así que el *parser* del JSON es deliberadamente defensivo: no
asume una ruta fija dentro de la respuesta, sino que reconoce los
campos por el nombre de su llave (`hunum`, `jawon`, `mean`, etc.) y,
si no reconoce nada, por la forma del contenido (el texto más largo =
origen, un par de palabras en hangul = significado+lectura). Por eso
la **celda 3.1 del notebook de Colab es la primera que debes correr**:
`naver_hanja.diagnostico("水")` te muestra en crudo qué respondió
Naver hoy. Si el resultado no se ve bien, pégame esa salida (o el log
de una corrida real) y ajusto el parser al toque — el resto del
boletín sigue funcionando mientras tanto gracias al respaldo local.

## Archivos del proyecto

```
src/
  models.py         estructuras de datos compartidas (Item, Source)
  hanja_db.py        banco local de hanja: elige el carácter del día + respaldo si Naver falla
  naver_hanja.py       consulta hanja.dict.naver.com (significado, definición, origen)
  hanja_page.py          ensambla la página de hanja: Naver + traducción, o respaldo local
  sources.py                obtiene titulares (RSS directo → auto-descubrimiento → Google News por sitio)
  dedup.py                   agrupa noticias equivalentes y calcula relevancia
  translate.py                 traducción con DeepL (noticias y, con otro contexto, hanja)
  pdf_builder.py                  arma el PDF (HTML + wkhtmltopdf, fuente Noto Sans CJK)
  main.py                           orquesta todo el pipeline
requirements.txt
.github/workflows/boletin_diario.yml   automatización diaria sin intervención humana
boletin_corea.ipynb                     notebook de Google Colab, listo para abrir y correr
```

## Usar el notebook en Google Colab

1. Sube `boletin_corea.ipynb` a Google Colab (Archivo → Subir notebook).
2. Corre las celdas en orden. La primera instala `wkhtmltopdf` y la
   fuente coreana (`fonts-noto-cjk`) a nivel de sistema — son
   necesarias para que el PDF muestre bien el hangul (`reportlab` por
   sí solo no puede; ver la nota técnica en `pdf_builder.py`).
3. Te pedirá tu clave de DeepL (gratis en https://www.deepl.com/pro-api,
   500.000 caracteres/mes).
4. **Corre la celda 3.1 (diagnóstico de Naver) antes que nada más.**
5. Corre la sección 4 para generar el boletín completo del día.
6. Al final te muestra el PDF y te deja descargarlo.

Este notebook sirve para **desarrollar y revisar el resultado**, pero
Colab no tiene forma de ejecutarse solo todos los días. Para eso está
la automatización de GitHub Actions.

## Automatización diaria sin depender de un humano (GitHub Actions)

1. Crea un repositorio en GitHub (puede ser privado) y sube el
   contenido de este proyecto: `src/`, `requirements.txt`, `.github/`
   y `README.md`. No subas `boletin_corea.ipynb` si no quieres, es
   solo para Colab.
2. En el repo: **Settings → Secrets and variables → Actions → New
   repository secret** → nombre `DEEPL_API_KEY`, valor tu clave de
   DeepL. (Nunca pegues esta clave en un chat conmigo — se agrega
   directamente ahí.)
3. El workflow `.github/workflows/boletin_diario.yml` corre todos los
   días a las 07:00 hora de Bogotá (12:00 UTC — ajustable editando la
   línea `cron:` del archivo).
4. Cada corrida deja el PDF en dos lugares:
   - Como **artifact** de esa ejecución (pestaña Actions → la corrida → Artifacts).
   - Commiteado en `boletines/AAAA-MM-DD.pdf` del propio repositorio.

A partir de ahí, **nadie tiene que ejecutar nada a mano**: el único
paso humano queda en revisar el PDF.

## Prueba del workflow (hazlo tú y lo revisamos juntos)

Como mi sesión no tiene tu cuenta de GitHub conectada, no puedo crear
el repositorio ni disparar la corrida por ti. Estos son los pasos
exactos para que la pruebes tú mismo:

1. **Crea el repo** (en github.com → "New repository"; puede ser privado).
2. **Sube los archivos** de este proyecto (`src/`, `requirements.txt`,
   `.github/`, `README.md`) — arrastrándolos en la web de GitHub, o por
   git:
   ```bash
   git init
   git add src requirements.txt .github README.md
   git commit -m "Boletín diario de Corea del Sur"
   git branch -M main
   git remote add origin https://github.com/<tu-usuario>/<tu-repo>.git
   git push -u origin main
   ```
3. **Agrega el secreto** `DEEPL_API_KEY` (paso 2 de la sección anterior).
4. **Dispáralo manualmente** (sin esperar al cron, para probar ya):
   pestaña **Actions** del repo → selecciona "Boletín diario de Corea
   del Sur" en la lista de la izquierda → botón **Run workflow** → Run.
5. Espera 1-3 minutos y entra a esa corrida. Si el círculo queda
   **verde ✅**, ya tienes la prueba de que corre solo, sin intervención
   humana: baja el PDF desde **Artifacts**, al final de la página de
   esa corrida.
6. Si queda **rojo ❌**, abre el paso que falló (lo más probable es
   "Generar el boletín del día") y copia el mensaje de error — pégamelo
   aquí y lo diagnosticamos juntos. Los puntos más probables de fallo
   la primera vez:
   - Falta el secreto `DEEPL_API_KEY` o tiene un typo en el nombre.
   - Alguna fuente de noticias cambió su estructura (el log dice cuál).
   - La página de hanja de Naver no devolvió nada reconocible (no
     debería tumbar la corrida — cae al respaldo local — pero revisa
     el log para confirmarlo).

Cuando quieras, también puedo revisar el repo directamente si conectas
tu cuenta de GitHub a esta sesión (Settings → Connectors en claude.ai);
en ese momento puedo crear el repo, subir el código y disparar la
corrida yo mismo para darte el resultado sin que tengas que hacer estos
pasos. Mientras tanto, con que me compartas el link de la corrida (o el
error) alcanza para seguir ajustando el código.

## Conectarlo con N8N

Ya que lo quieres sincronizado con N8N, la forma más simple (sin
montar un servidor aparte) es dejar que **GitHub Actions sea quien
genera el PDF a diario** (como ya queda configurado arriba) y que
**N8N solo venga a buscarlo y repartirlo**:

1. Nodo **Schedule Trigger** en N8N, programado un rato después de la
   hora del cron de GitHub Actions (para darle tiempo a terminar).
2. Nodo **HTTP Request** que descargue el PDF del día desde la URL fija
   de `raw.githubusercontent.com` (si el repo es privado, agrega el
   header `Authorization: token <tu GitHub token>` con un *Personal
   Access Token* de solo lectura):
   `https://raw.githubusercontent.com/<usuario>/<repo>/main/boletines/2026-10-28.pdf`
3. De ahí, los nodos que prefieras para distribuirlo: **Email**,
   **Slack**, **Google Drive**, etc.

Si en algún momento prefieres que N8N dispare la generación en vez de
solo recogerla, se puede cambiar el trigger de GitHub Actions de
`schedule` a `repository_dispatch` y que un nodo HTTP Request de N8N
llame a la API de GitHub (`POST /repos/<usuario>/<repo>/dispatches`)
para arrancar el workflow bajo demanda. Dime si quieres que lo arme
así en vez del cron fijo.

## Cosas a tener en cuenta / próximos ajustes

- **No pude probar la recolección de noticias ni el scraping de Naver
  contra los sitios reales** desde el entorno donde escribí este
  código (solo tiene salida a GitHub y gestores de paquetes). La
  primera corrida real va a ser en tu Colab o en GitHub Actions — ver
  la celda de diagnóstico (sección 3.1 del notebook) para el caso de
  Naver, y el punto 6 de "Prueba del workflow" para las noticias.
- `Chosun Ilbo`, `JoongAng Ilbo`, `KBS World (español)` y `Korea.net
  (español)` no tienen un feed RSS oficial confirmado, así que
  `sources.py` cae automáticamente a una búsqueda en Google News
  filtrada por sitio cuando no encuentra un RSS propio.
- El PDF se genera con HTML + `wkhtmltopdf` (no con `reportlab` puro)
  porque las fuentes coreanas usan un tipo de contorno que `reportlab`
  no soporta — está explicado en el encabezado de `pdf_builder.py`.
