# Research: Informe PPT de Postmortem por Release

## 1. Generación del fichero .pptx

**Decision**: `python-pptx` para construir el documento (slides, formas, texto, imágenes).

**Rationale**: Ya está disponible en el entorno de desarrollo (`python-pptx` instalado y verificado durante la sesión de especificación). Es la librería estándar de Python para generar `.pptx` mediante código, sin depender de PowerPoint/COM/Office instalado en el servidor. Genera OOXML válido, abrible en PowerPoint/LibreOffice/Google Slides (SC-003).

**Alternatives considered**:
- Generar el .pptx a partir de una plantilla `.potx` corporativa existente: descartado por ahora porque no existe ninguna plantilla de este tipo en el repositorio (se buscó explícitamente); el `.pptx` de referencia usado como inspiración de estilo no es una plantilla reutilizable de forma sencilla (contiene un objeto OLE incrustado en la portada de origen desconocido). Queda como mejora futura si se aporta una plantilla corporativa real.
- LibreOffice en modo headless (`soffice --convert-to pptx`) partiendo de HTML/Markdown: descartado, añade una dependencia de sistema pesada (instalación de LibreOffice) para un caso de uso que `python-pptx` cubre directamente.

## 2. Renderizado de las gráficas como imágenes

**Decision**: Reconstruir cada gráfica como una `plotly.graph_objects.Figure` en Python (con los mismos colores/trazas que su equivalente en JavaScript) y exportarla a PNG con **Kaleido** (motor oficial de exportación estática de Plotly), para incrustar la imagen en la diapositiva correspondiente.

**Rationale**: Kaleido es el motor recomendado por Plotly para exportar figuras a imagen sin depender de un navegador completo ni de un servidor corriendo; funciona directamente sobre datos en Python, alineado con el resto de `converters/` (scripts batch que operan sobre ficheros JSON, sin necesitar el dashboard "vivo"). Genera imágenes estáticas de alta fidelidad visual con el mismo motor de trazado (Plotly) que ya usan los dashboards, minimizando diferencias de estilo.

**Alternatives considered**:
- **Automatizar un navegador headless (Playwright/Selenium)** para abrir el dashboard real y capturar pantallazos de cada `<div>` de gráfica: daría fidelidad visual perfecta por construcción (mismo código JS, cero duplicación de lógica), pero exige que el dashboard esté desplegado/accesible en el momento de generar el informe, añade una dependencia pesada (binarios de navegador) a un proyecto que hoy no tiene ninguna dependencia de producción más allá de `python-dotenv`, y es sustancialmente más lento y frágil (timing, selectores, gestión del ciclo de vida del navegador) que invocar una función Python sobre datos ya en memoria. Se descarta para esta versión; ver riesgo de duplicación de lógica más abajo.
- **matplotlib**: no reproduce con precisión el estilo visual de Plotly (fuentes, interpolación, leyendas) usado en los dashboards; se descarta por fidelidad visual inferior a Kaleido+Plotly.

**Riesgo aceptado y cómo se mitiga**: reconstruir las gráficas en Python duplica lógica que hoy solo existe en JavaScript (agregación diaria, cálculo de backlog, ventana horaria del PaP, etc.). Este riesgo es inherente a la decisión de no depender de un navegador. Se mitiga con: (a) tests unitarios en Python con casos ya verificados manualmente en JavaScript durante el desarrollo de los dashboards (mismos datos de entrada, mismo resultado esperado), y (b) manteniendo la lógica de agregación en un módulo Python pequeño y aislado (una función por gráfica) para que un cambio futuro en el JS tenga un lugar evidente y acotado donde replicarse.

## 3. Cálculo de los KPIs del informe

**Decision**: Nueva función Python que replica exactamente las reglas actuales del dashboard de postmortem (`analyzeData()` en `dashboards/postmortem/index.html`): Total, Pendientes (global/PaP/Mesa = no Cerrado/Resuelto en cualquier momento), % Cerradas, % Resueltas PaP (solo resoluciones el mismo día calendario que el despliegue), % Resueltas Mesa, Tiempo Medio de Resolución (media de duración entre "Fecha de envío" y "Fecha de última resolución" en incidencias cerradas/resueltas con ambas fechas válidas).

**Rationale**: FR-004 exige que el informe nunca muestre cifras distintas a las del dashboard para los mismos datos. Los KPIs ya precalculados en `_metadata.kpis.dashboard_hub` del conversor Python (`postmortem_converter.py`) no son suficientes: no cubren Pendientes, Tiempo Medio de Resolución, ni la regla de "resuelta el mismo día del PaP" incorporada más tarde solo en el JS. Hace falta una función nueva, no reutilizar esos metadatos tal cual.

**Alternatives considered**:
- Ampliar el conversor Python (`PostmortemConverter`) para que sus `_metadata.kpis` incluyan ya todos estos KPIs, y que el generador de informes simplemente los lea: se descarta como alcance de ESTA feature porque tocaría el conversor existente (usado también en producción vía el backend FastAPI del repo hermano) y sus contratos de salida; el cálculo aislado en el módulo de informes es más seguro y no introduce cambios en `data/output/*.json` ya consumidos por los dashboards. Queda anotado como posible refactor futuro (unificar el cálculo en un solo lugar) si la duplicación demuestra ser un problema real.

## 4. Lectura de los datos generales de KPIs de Release

**Decision**: `dashboards/release-kpis/releases-data.js` define `const RAW_RELEASES = [...]` como un array de arrays de literales (strings y números), sin ninguna expresión JavaScript dinámica. Se extrae el contenido entre `const RAW_RELEASES = ` y el `;` final con una expresión regular simple y se parsea con `ast.literal_eval` de Python — la sintaxis de un array-de-arrays de literales es válida simultáneamente en JS y en Python, así que no hace falta un intérprete JS embebido ni una reescritura manual del fichero.

**Rationale**: Evita añadir un motor JS a Python (Node subprocess, PyExecJS, etc.) solo para leer una constante de datos. Es la misma fuente de verdad que ya usa `dashboards/release-kpis/app.js` en el navegador, así que no hay divergencia de datos entre el dashboard y el informe (solo divergencia de lógica de agregación de gráficas, ya aceptada en la sección 2).

**Alternatives considered**:
- Mover `RAW_RELEASES` a un `.json` que ambos (JS y Python) consuman: mejora real a futuro, pero implica tocar `release-kpis/app.js` y su forma de carga (`<script src="releases-data.js">`), fuera del alcance mínimo de esta feature.

## 5. Disparo de la generación (dónde vive el código, cómo se invoca)

**Decision**: Un nuevo script `converters/cli/generate_postmortem_report.py`, invocable como CLI (`python generate_postmortem_report.py <release_name> [-o output.pptx]` y en modo `--all` para todas las releases con datos, cubriendo la User Story 3) y como librería (`from converters.cli.generate_postmortem_report import generate_report`). Se expone en los dashboards mediante un endpoint HTTP nuevo (`GET /api/reports/postmortem/<release_name>`) que invoca ese script y devuelve el `.pptx` como descarga — implementado en `serve_app.py` (desarrollo local) y replicado en el backend FastAPI del repo hermano (producción), siguiendo el mismo patrón ya usado por `converters/cli/upload_csv.py` (orquestación única, invocable como librería o como subproceso desde otro repo).

**Rationale**: Consistente con la arquitectura ya existente (`convert_postmortems.py`, `convert_incidents.py`, `upload_csv.py`) — scripts CLI reutilizables como librería, con un backend delgado que solo los invoca. Cubre FR-001 (botón en el dashboard) y FR-011 (generación masiva) con el mismo código.

**Alternatives considered**: Generar el informe únicamente desde el navegador (JS) usando una librería de generación de PPTX en cliente: se descarta porque no existe una librería JS madura equivalente a `python-pptx` con la fidelidad necesaria, y porque el cálculo de KPIs/gráficas ya vive en Python en el resto del proyecto de conversión — hacerlo en el navegador duplicaría aún más lógica sin necesidad.

## 6. Ubicación y ciclo de vida del fichero generado

**Decision**: Los informes se escriben en un nuevo directorio `data/reports/`, con nombre de fichero derivado y saneado del nombre de la release (p. ej. `2026R7-postmortem-report.pptx`). Regenerar el informe de una release sobrescribe el fichero anterior de esa misma release (mismo criterio de "una versión activa" ya aplicado a `data/output/`, ver `converters/cli/convert_postmortems.py` y `cleanup_output.py`).

**Rationale**: Coherente con la convención de directorios de datos ya documentada en `CLAUDE.md` (`data/input/`, `data/output/`, `data/errors/`, `data/archive/`) y con la decisión de "una versión activa, no acumular" ya aplicada a `data/output/`. `data/reports/` queda protegido por las mismas reglas de `.gitignore` que el resto de `data/` (nunca se commitea contenido generado).

**Alternatives considered**: Guardar el informe dentro de `data/output/` junto a los JSON: se descarta para no mezclar formatos/propósitos distintos (datos fuente vs. documento de salida) en el mismo directorio que ya escanea `build_index_for_hub()`.
