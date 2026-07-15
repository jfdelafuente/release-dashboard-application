---

description: "Task list template for feature implementation"
---

# Tasks: Dashboards por Release

**Input**: Design documents from `/specs/007-per-release-dashboards/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md (todos presentes)

**Tests**: Se incluyen tareas de test para la cadena de conversión (`converters/`), tal como comprometió el Constitution Check de `plan.md` (principio "Testing Standards", no negociable). El frontend no tiene infraestructura de tests automatizados en ningún dashboard del proyecto — se verifica manualmente vía `quickstart.md` (Fase de Polish), siguiendo el mismo precedente ya aceptado.

**Organization**: Tareas agrupadas por historia de usuario (spec.md) para permitir implementación y prueba independientes de cada una.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede ejecutarse en paralelo (archivo distinto, sin dependencia de tareas incompletas)
- **[Story]**: Historia de usuario a la que pertenece (US1, US2, US3)
- Cada tarea incluye la ruta de archivo exacta

## Path Conventions

Proyecto único, sin `src/`/`backend/`/`frontend/` separados — las rutas reales del repo:
- Backend de conversión: `converters/cli/`, `converters/src/csv_to_json/`, `converters/tests/`
- Servidor local: `serve_app.py` (raíz del repo)
- Dashboards: `dashboards/release-kpis/`, `dashboards/postmortem/`
- Documentación: `converters/docs/`, `dashboards/README.md`

---

## Phase 1: Setup

**Purpose**: Resolver un riesgo ya identificado en `research.md` (R6) antes de tocar tests, para no editar el conjunto de archivos equivocado.

- [X] T001 Determinar qué conjunto de tests de `converters/tests/` es el que realmente ejecuta CI: correr `pytest --collect-only` desde la raíz del repo y desde `converters/`, comparar con los archivos duplicados detectados (`converters/tests/integration/` vs `converters/tests/integration/postmortem/`; `converters/tests/unit/` vs `converters/tests/unit/schemas/`), y anotar en una línea de comentario en este archivo (`tasks.md`) cuál es el conjunto canónico a usar en las Fases 2+
  - **Hallazgo**: no hay un conjunto "canónico" — `pytest --collect-only` desde la raíz del repo (que es como se ejecuta hoy, ver `converters/pytest.ini`) recoge **ambas copias** de cada par duplicado (477 tests en total). `unit/test_postmortem_schemas.py` y `unit/schemas/test_postmortem_schemas.py` son byte-idénticos; `integration/test_error_handling.py` y `integration/postmortem/test_error_handling.py` han divergido (comentarios/nombres de variable, mismo comportamiento). Decisión: para no dejar una copia obsoleta que pueda fallar, cualquier test nuevo para `release_name` se añade a **ambos** archivos de cada par afectado (T002 toca `unit/test_postmortem_schemas.py` y `unit/schemas/test_postmortem_schemas.py`; no se toca `test_metadata_generation.py` ni sus duplicados porque no cubren `release_name`). Resolver la duplicación en sí sigue fuera de alcance (research.md R6).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Propagar `release_name` por toda la cadena de conversión y subida ya existente (ver `contracts/upload-endpoint.md` y `data-model.md`). Ninguna historia de usuario puede completarse sin esto: es el dato que hace posible que exista más de un dashboard de postmortem distinguible por release.

**⚠️ CRITICAL**: Ninguna tarea de las Fases 3-5 puede empezar hasta que esta fase esté completa.

### Tests para la cadena de conversión (escribir primero, deben fallar antes de implementar)

- [X] T002 [P] Test: `ConversionMetadata.to_dict()` incluye `release_name` cuando se pasa, y lo omite/`None` cuando no, en el archivo de test canónico determinado en T001 para `postmortem_schemas.py`
- [X] T003 [P] Test: `PostmortemConverter.convert_file(..., release_name=...)` escribe `release_name` dentro de `_metadata` del JSON de salida, en el archivo de test canónico determinado en T001 para la conversión end-to-end de postmortem
- [X] T004 [P] Test: `build_index_for_hub()` incluye `release_name` por archivo (leído de `_metadata.release_name`) y usa `None`/ausente para archivos de postmortem ya existentes sin ese campo, en `converters/tests/unit/test_convert_postmortems_build_index.py` (archivo nuevo, no existe cobertura previa de `build_index_for_hub` según la investigación)

### Implementación de la cadena de conversión

- [X] T005 Añadir el atributo `release_name` (opcional, por defecto `None`) al constructor y a `to_dict()` de `ConversionMetadata` en `converters/src/csv_to_json/postmortem_schemas.py:144-165` (depende de T001, T002)
- [X] T006 Añadir el parámetro `release_name` a `generatePostmortemJSON()` (`converters/src/csv_to_json/postmortem_converter.py:189-249`) y a `PostmortemConverter.convert_file()` (`converters/src/csv_to_json/postmortem_converter.py:269-273`), reenviándolo hasta `ConversionMetadata` (depende de T005, T003)
- [X] T007 Extender `build_index_for_hub()` en `converters/cli/convert_postmortems.py:258-329` para abrir cada JSON de postmortem y copiar `_metadata.release_name` (o `None` si no existe) a la clave `release_name` de su entrada en `postmortem.files[]` (depende de T006, T004)
- [X] T008 Añadir el argumento `--release-name` (opcional) a `converters/cli/convert_postmortems.py` (parseo `argparse` + reenvío a `PostmortemConverter.convert_file()`) (depende de T006)
- [X] T009 Añadir el parámetro `release_name` a `run_upload()` en `converters/cli/upload_csv.py:28-49`, reenviado como `--release-name <valor>` al invocar el subprocess de `convert_postmortems.py` únicamente cuando `dashboard_type == 'postmortem'` (depende de T008)
- [X] T010 Añadir el manejo del campo `release_name` del formulario multipart en `handle_upload()` (`serve_app.py:37-92`): leerlo del form-data, exigirlo (error 400 si falta o está vacío) solo cuando `type == 'postmortem'`, e ignorarlo cuando `type == 'massive'`; reenviarlo a `run_upload()` (depende de T009)

**Checkpoint**: `python converters/cli/convert_postmortems.py <csv> --release-name "X"` produce un JSON con `_metadata.release_name == "X"`, y `index.json` refleja ese `release_name` en la entrada correspondiente. Listo para que las historias de usuario empiecen.

---

## Phase 3: User Story 1 - Ver el dashboard de una release concreta (Priority: P1) 🎯 MVP

**Goal**: Abrir `/dashboards/postmortem/?release=<nombre>` muestra únicamente los datos de esa release, con su nombre como identificador de cabecera.

**Independent Test**: Con la Fase 2 completa, generar un JSON de postmortem con `--release-name "2026R4-PRUEBA"` (vía CLI, sin pasar por la UI de subida), refrescar `index.json`, y comprobar que `/dashboards/postmortem/?release=2026R4-PRUEBA` carga solo esos datos y muestra ese nombre en la cabecera.

### Implementation for User Story 1

- [X] T011 [US1] En `dashboards/postmortem/index.html`, leer `new URLSearchParams(location.search).get('release')` y sustituir `indexData.postmortem.files[0]` (línea ~1281 de `autoLoadLatestData`) por `indexData.postmortem.files.find(f => f.release_name === releaseParam)`
- [X] T012 [US1] En `dashboards/postmortem/index.html`, sustituir el título estático `<h1>Análisis <span class="accent">Postmortem</span></h1>` y su subtítulo (línea ~286-287) por una versión que muestre el nombre de la release cargada (vía JS, tras `autoLoadLatestData`), escapando el valor con la misma utilidad de escape ya usada en el resto del dashboard
  - Nota de implementación: se usa `textContent` (no `innerHTML`) para insertar el nombre de release en `#releaseHeading`, lo que escapa automáticamente cualquier HTML — no hace falta una utilidad de escape aparte para este caso.

**Checkpoint**: User Story 1 funciona y se puede probar de forma independiente.

---

## Phase 4: User Story 2 - Encontrar y navegar entre dashboards de distintas releases (Priority: P2)

**Goal**: La columna "RELEASE" de `dashboards/release-kpis/` enlaza a cada dashboard de postmortem; visitar postmortem sin `release` o con una release sin datos muestra el estado correspondiente en vez de romperse.

**Independent Test**: Con dos o más releases cargadas (vía Fase 2 + Fase 3), abrir `dashboards/release-kpis/`, hacer clic en dos nombres de release distintos y confirmar que cada uno lleva al dashboard correcto; hacer clic en una release sin datos y confirmar que se ve la pantalla de subida con el nombre ya asociado; visitar `/dashboards/postmortem/` sin parámetro y confirmar el mensaje de "accede desde release-kpis".

### Implementation for User Story 2

- [X] T013 [P] [US2] En `dashboards/release-kpis/app.js`, función `renderTable()` (líneas 255-259), sustituir `<div class="cell-name">${escapeHtml(r.name)}</div>` por `<a class="cell-name" href="/dashboards/postmortem/?release=${encodeURIComponent(r.name)}">${escapeHtml(r.name)}</a>`
- [X] T014 [US2] En `dashboards/postmortem/index.html`, cuando el parámetro `release` esté ausente o vacío, omitir la llamada a `autoLoadLatestData()` y mostrar un mensaje ("Accede a una release desde el dashboard de KPIs de Release") con enlace a `/dashboards/release-kpis/`, sin dejar la pantalla de carga en un estado ambiguo
  - Implementado como una pantalla nueva `#noReleaseScreen` (reutiliza la clase `.upload-screen`), visible por defecto en el HTML estático y mostrada por `showNoReleaseState()`.
- [X] T015 [US2] En `dashboards/postmortem/index.html`, cuando el parámetro `release` esté presente pero `indexData.postmortem.files.find(...)` (de T011) no encuentre coincidencia, mostrar la pantalla de subida (`upload-screen`) ya existente con el nombre de la release (tomado del parámetro de URL) visible de forma no editable, en vez de dejar la pantalla de subida sin contexto de qué release se está cargando
  - Implementado vía `showUploadScreenForRelease(releaseName)`, que rellena `#uploadReleaseName` (span de solo lectura en el `<h2>` de la pantalla de subida).

**Checkpoint**: Historias 1 y 2 funcionan juntas de forma independiente.

---

## Phase 5: User Story 3 - Dar nombre a una release al cargar sus datos (Priority: P3)

**Goal**: Subir un CSV desde la pantalla de subida de una release concreta (alcanzada vía Historia 2) asocia automáticamente el nombre de esa release a los datos convertidos, sin que el usuario tenga que escribirlo.

**Independent Test**: Desde `dashboards/release-kpis/`, hacer clic en una release sin datos, soltar un CSV de prueba en la pantalla de subida, y comprobar que — sin escribir ningún nombre a mano — el dashboard resultante queda etiquetado con el nombre correcto y es alcanzable de nuevo desde `release-kpis` con el mismo enlace.

### Implementation for User Story 3

- [X] T016 [US3] En `dashboards/postmortem/index.html`, actualizar el manejador de subida de CSV (mismo mecanismo de `FormData`/`fetch('/api/upload', ...)` ya usado hoy) para incluir el campo `release_name` tomado del parámetro `?release=` de la URL actual, junto a `file` y `type=postmortem`
- [X] T017 [US3] En `dashboards/postmortem/index.html`, tras una respuesta de subida exitosa, volver a ejecutar la lógica de carga scoped a esa release (T011) para que el dashboard muestre los datos recién convertidos sin necesidad de recargar la página manualmente
  - El código existente ya llamaba a `autoLoadLatestData()` tras un upload exitoso (`.then(() => autoLoadLatestData())`); como esa función ahora es release-aware (T011), este comportamiento se hereda sin cambios adicionales.

**Checkpoint**: Las 3 historias de usuario funcionan de forma independiente y en conjunto.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentación, verificación end-to-end y auditoría de seguridad transversal a las 3 historias.

- [X] T018 [P] Actualizar `converters/docs/API.md` documentando el campo `release_name` en `_metadata` del JSON de postmortem y en `postmortem.files[]` de `index.json`
  - Desviación: `converters/docs/API.md` documenta únicamente el conversor de incidencias masivas, no tiene ninguna sección de postmortem que extender. Se documentó en su lugar en `CLAUDE.md`, sección "Conversor de Postmortem (Postmortem Converter)" — es la documentación viva real del esquema JSON de postmortem en este repo.
- [X] T019 [P] Actualizar `dashboards/README.md`: eliminar las referencias al dashboard combinado de Postmortem/Release y documentar el nuevo flujo de navegación por release desde `dashboards/release-kpis/`
- [X] T020 Auditoría de escape/codificación: confirmar que `release_name` se escapa con la utilidad de escape HTML ya usada en el dashboard antes de mostrarse (T012, T015) y se codifica con `encodeURIComponent` en todos los puntos donde se usa en una URL (T011 lectura, T013, T016), conforme al principio de Seguridad de la Constitución
  - `releaseHeading`/`uploadReleaseName` se rellenan con `textContent` (no `innerHTML`), que escapa automáticamente — no se necesita una utilidad de escape aparte.
  - `release-kpis/app.js` usa `encodeURIComponent(r.name)` en el `href` y `escapeHtml(r.name)` en el texto visible del enlace (T013).
  - `URLSearchParams.get('release')` decodifica automáticamente el valor codificado en la URL (T011); no hace falta decodificación manual.
  - El backend pasa `release_name` a `subprocess.run([...])` en forma de lista (no `shell=True`), por lo que no hay riesgo de inyección de shell aunque el valor contenga caracteres especiales.
- [X] T021 Ejecutar completa la guía de `quickstart.md` (las 6 secciones) y confirmar cada paso
  - Verificado mediante `serve_app.py` real + `curl` + inspección directa de los JSON (no hay navegador disponible en este entorno de implementación): secciones 3 (aislamiento entre dos releases reales, `RELEASE-A`/`RELEASE-B`, IDs de incidencia no se mezclan), 5 (CLI `--release-name` propaga a `_metadata` e `index.json`) y 6 (el archivo legacy `2026R6-MESA-POST-...json`, sin `release_name`, sigue apareciendo en `index.json` con `release_name: null` sin romper `build_index_for_hub`) confirmadas end-to-end contra datos reales. Secciones 1, 2 y 4 (renderizado visual: cabecera con nombre de release, pantalla de subida pre-rellenada, mensaje de "accede desde release-kpis") verificadas por revisión de código + comprobación de sintaxis JS, ya que dependen de renderizado real en navegador — pendiente de una pasada visual manual del usuario, siguiendo el mismo patrón ya aceptado en este proyecto para el resto de dashboards (sin framework de tests de UI).
  - Todos los artefactos de prueba (`RELEASE-A`/`RELEASE-B`/`E2E-TEST-RELEASE` en `data/input/`, `data/output/`, `data/errors/`) se eliminaron y `data/output/index.json` se regeneró a su estado real tras la verificación.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sin dependencias — empieza inmediatamente
- **Foundational (Phase 2)**: Depende de Setup — BLOQUEA las 3 historias de usuario
- **User Story 1 (Phase 3)**: Depende solo de Foundational
- **User Story 2 (Phase 4)**: Depende de Foundational y de T011 de US1 (usa la misma función de búsqueda por `release_name`)
- **User Story 3 (Phase 5)**: Depende de Foundational, de T011 (US1) y de T015 (US2, la pantalla de subida con el nombre ya asociado)
- **Polish (Phase 6)**: Depende de que las historias que se quieran entregar estén completas

### User Story Dependencies

- **User Story 1 (P1)**: Ninguna dependencia de otras historias — es el MVP
- **User Story 2 (P2)**: Reutiliza la función de búsqueda de US1 (T011); añade sus propios estados de UI
- **User Story 3 (P3)**: Se apoya en la UI de "release sin datos" de US2 (T015) y en la recarga de datos de US1 (T011) — es la historia con más dependencias, coherente con ser P3

### Parallel Opportunities

- T002, T003, T004 (tests de la Fase 2) pueden escribirse en paralelo — archivos de test distintos, sin dependencia entre sí
- T013 (US2, `release-kpis/app.js`) puede hacerse en paralelo con T014/T015 (US2, `postmortem/index.html`) — archivos distintos
- Las tareas T018/T019 (Polish, documentación) pueden hacerse en paralelo entre sí

---

## Parallel Example: Fase 2 (tests)

```bash
Task: "Test ConversionMetadata.to_dict() incluye release_name en el archivo canónico de postmortem_schemas"
Task: "Test PostmortemConverter.convert_file() propaga release_name a _metadata en el archivo canónico de conversión e2e"
Task: "Test build_index_for_hub() incluye release_name por archivo en converters/tests/unit/test_convert_postmortems_build_index.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Completar Fase 1 (Setup) y Fase 2 (Foundational) — sin esto no hay datos que ver por release
2. Completar Fase 3 (User Story 1)
3. **Parar y validar**: generar un JSON de prueba vía CLI con `--release-name`, confirmar que `/dashboards/postmortem/?release=...` lo carga y muestra correctamente
4. Este es ya un incremento demostrable, aunque todavía sin navegación desde `release-kpis` ni subida end-to-end desde el navegador

### Incremental Delivery

1. Setup + Foundational → cadena de `release_name` lista de extremo a extremo en el backend
2. User Story 1 → probar de forma independiente (vía CLI + URL manual) → demo
3. User Story 2 → navegación real desde `release-kpis` + estados de "sin release"/"release sin datos" → demo
4. User Story 3 → subida end-to-end desde el navegador con nombre heredado de la URL → demo completo
5. Polish → documentación y verificación final con `quickstart.md`

---

## Notes

- `release_name` viaja siempre como texto plano por una cadena de llamadas ya existente — no se introduce ningún modelo de datos ni almacenamiento nuevo (ver `data-model.md`)
- El nombre de release nunca se escribe a mano en un campo de texto libre en el flujo principal: se hereda del parámetro `?release=` de la URL (T016), lo que resuelve por construcción el riesgo de errata que motivó el requisito FR-011 de la spec
- Verificar que los tests de la Fase 2 fallan antes de implementar (T002-T004 antes que T005-T007)
- Confirmar cada checkpoint de historia de usuario antes de avanzar a la siguiente
- Evitar: añadir un campo de texto libre para el nombre de release (decisión de diseño ya descartada en `research.md` R5)
