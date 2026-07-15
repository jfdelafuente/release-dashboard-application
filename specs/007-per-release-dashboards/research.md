# Research: Dashboards por Release

## R1. Cómo propagar el nombre de release desde la subida de CSV hasta el JSON

**Decision**: Añadir `release_name` como campo opcional de nivel superior a lo largo de toda la cadena: formulario de subida → `serve_app.py:handle_upload()` → `run_upload()` (`converters/cli/upload_csv.py`) → argumento CLI `--release-name` de `convert_postmortems.py` → `PostmortemConverter.convert_file(release_name=...)` → `generatePostmortemJSON(release_name=...)` → `ConversionMetadata(release_name=...)` → clave `_metadata.release_name` en el JSON de salida.

**Rationale**: Es la cadena de llamadas real, verificada línea a línea (`serve_app.py:37-92`, `upload_csv.py:28,44-49`, `postmortem_converter.py:189-249,252-367`, `postmortem_schemas.py:144-165`). Cada eslabón ya acepta parámetros con nombre y tiene un punto de extensión claro (kwargs opcionales), así que añadir uno más es un cambio aditivo, no una reestructuración.

**Alternatives considered**:
- Derivar el nombre automáticamente del nombre de archivo del CSV: rechazado por decisión ya tomada con el usuario (Q1 de `/speckit-specify`) — el nombre lo da el usuario, no se infiere.
- Guardar el nombre de release en un fichero/aparte (mapping externo nombre→archivo en vez de dentro del propio JSON): rechazado porque duplica el dato fuera de la fuente de verdad y complica la sincronización; `_metadata` ya es el lugar donde vive el resto de metadatos de conversión (encoding, timestamps, kpis).

## R2. Cómo incluir el nombre de release en `index.json`

**Decision**: Extender `build_index_for_hub()` en `converters/cli/convert_postmortems.py:258-329` para que, al construir cada entrada de `postmortem.files[]`, abra el JSON correspondiente y copie `_metadata.release_name` a una clave `release_name` en esa entrada del índice.

**Rationale**: `build_index_for_hub` ya es quien genera hoy la sección `postmortem` de `index.json` (confirmado; `build_index.py` solo gestiona `massive` y no toca `postmortem`). Ya itera los archivos `*-postmortem.json` y arma un `file_info` por archivo (líneas 316-321) — añadir una lectura del `_metadata` de cada archivo (que de todas formas ya se abre para construir `data/output/*-postmortem.json`, no supone I/O nuevo por archivo, ya se tiene el contenido a mano en el propio proceso de conversión, o se puede leer el fichero ya escrito) es una extensión local a esa función, no un rediseño.

**Alternatives considered**:
- Que el frontend derive el nombre de release a partir del nombre de archivo (`2026R6-MESA-POST-20260707-postmortem.json` → "2026R6-MESA-POST"): rechazado, ya que el nombre de archivo no es necesariamente el nombre de release limpio que el usuario introdujo (pueden diferir en formato/mayúsculas/sufijos de fecha).

## R3. Cómo asocia el dashboard de postmortem una release con su archivo

**Decision**: Usar un parámetro de query string en la URL: `/dashboards/postmortem/?release=<nombre-url-encoded>`. Al cargar la página, leer `URLSearchParams(location.search).get('release')` y, en vez de `indexData.postmortem.files[0]` (comportamiento actual en `autoLoadLatestData`, línea 1281), hacer `indexData.postmortem.files.find(f => f.release_name === releaseParam)`.

**Rationale**: El proyecto no tiene build step ni enrutamiento de servidor por segmentos de ruta (nginx sirve `dashboards/` como alias estático con `try_files`, sin reescritura dinámica). Un query string sobre la misma página estática (`dashboards/postmortem/index.html`) es el único mecanismo de "una URL por release" alcanzable sin añadir infraestructura nueva, y es coherente con que ningún dashboard de este proyecto usa hoy `URLSearchParams` — no hay un patrón previo que romper, se introduce limpio.

**Alternatives considered**:
- Generar un archivo HTML estático por release (`dashboards/postmortem/2026r4.html`): rechazado — requeriría un paso de generación (build step) que hoy no existe en el proyecto, y contradice el principio "sin build step" ya establecido para todo `dashboards/`.
- Subcarpeta por release (`dashboards/postmortem/2026r4/`): mismo problema — requiere generar contenido en tiempo de conversión, no solo datos.

## R4. Cómo enlaza `release-kpis` con el dashboard de postmortem de cada release

**Decision**: En `renderTable()` (`dashboards/release-kpis/app.js:255-259`), sustituir el `<div class="cell-name">${escapeHtml(r.name)}</div>` de la columna RELEASE por `<a class="cell-name" href="/dashboards/postmortem/?release=${encodeURIComponent(r.name)}">${escapeHtml(r.name)}</a>`. El enlace se genera para **todas** las filas, sin comprobar de antemano si esa release ya tiene datos de postmortem cargados.

**Rationale**: Comprobar de antemano cuáles de las 40+ releases de `releases-data.js` ya tienen JSON de postmortem requeriría que `release-kpis` (que hoy no hace ningún `fetch`, es 100% estático) empezara a consultar `data/output/index.json` — acoplamiento nuevo entre dos dashboards que hoy son independientes. Es más simple que el propio dashboard de destino (`postmortem`) decida qué mostrar según si encuentra o no un archivo para esa release (ver R5), dejando `release-kpis` sin cambios de comportamiento de datos, solo de marcado HTML.

**Alternatives considered**:
- Añadir un indicador visual (icono/color) en `release-kpis` para distinguir releases con/sin postmortem cargado: fuera de alcance de esta feature (no lo pide la spec); se podría añadir después sin romper este diseño.

## R5. Qué ocurre en `/dashboards/postmortem/` según el estado del parámetro `release`

**Decision**: Tres estados posibles, resueltos completamente en el cliente (sin cambios de servidor):
1. **Sin parámetro `release`** (URL antigua o visita directa a `/dashboards/postmortem/`): ya no existe el dashboard combinado (FR-006); se muestra un estado informativo pidiendo acceder desde `dashboards/release-kpis/`, con un enlace directo a esa página. No se intenta cargar ningún dato.
2. **Con parámetro `release` que SÍ tiene archivo asociado** en `index.json`: se carga y muestra igual que hoy (KPIs, gráfica temporal, distribución, tabla), pero con el nombre de la release en la cabecera en vez del título genérico "Postmortem".
3. **Con parámetro `release` que NO tiene archivo asociado todavía**: se muestra la pantalla de subida de CSV ya existente (`upload-screen`), con el nombre de la release pre-rellenado (de solo lectura, tomado del propio parámetro de URL) en vez de un campo de texto libre — así la subida queda automáticamente asociada al nombre correcto sin que el usuario tenga que volver a escribirlo, eliminando por diseño el riesgo de errata que motivaba FR-011.

**Rationale**: Esta división de estados cubre exactamente los 2 escenarios de aceptación de la Historia 2 de la spec (release con datos / release sin datos) y el requisito FR-010 (estado vacío sin errores). Al tomar el nombre de release siempre del parámetro de URL (nunca de un campo de texto libre en el formulario), FR-011 ("avisar si no coincide") deja de ser necesario como aviso explícito: por construcción, el nombre siempre coincide con el que aparece en `release-kpis`, porque es de ahí de donde viene.

**Alternatives considered**:
- Mantener un campo de texto libre para el nombre de release en el formulario de subida, con validación cliente contra `releases-data.js`: rechazado tras diseño — es estrictamente más complejo (requiere cargar `releases-data.js` en `postmortem/index.html`, comparar cadenas, mostrar avisos) y no aporta nada frente a simplemente heredar el nombre de la URL, dado que el único punto de entrada soportado es la tabla de `release-kpis`.

## R6. Riesgo pre-existente: duplicación de tests de converters

**Decision**: No se toca en este plan. Se documenta como riesgo a tener en cuenta al añadir tests para `release_name`.

**Rationale**: La investigación confirmó archivos de test duplicados entre `converters/tests/integration/` (raíz) y `converters/tests/integration/postmortem/`, y entre `converters/tests/unit/` y `converters/tests/unit/schemas/` (ver lista completa en el hallazgo de investigación). Añadir cobertura para `release_name` implicará actualizar aserciones de forma exacta del `_metadata` dict en varios de estos archivos — hay que localizar cuál conjunto es el que realmente ejecuta CI antes de escribir tests nuevos, para no mantener dos copias divergentes. Resolver la duplicación en sí es deuda técnica independiente de esta feature.

## R7. Compatibilidad con el resto de la aplicación

- `dashboards/assets/topbar.js` (`NAV_ITEMS`, id `postmortem` → `/dashboards/postmortem/`) no depende de que la URL de postmortem carezca de query string; confirmado que el resaltado de pestaña activa se basa solo en `data-active`, no en la URL completa. Sin cambios necesarios.
- Ningún otro dashboard (`massive-incidents`, `portal`) usa `URLSearchParams` hoy; introducirlo en `postmortem/index.html` no interfiere con patrones existentes en otros archivos.
