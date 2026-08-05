---

description: "Task list for Informe PPT de Postmortem por Release"

---

# Tasks: Informe PPT de Postmortem por Release

**Input**: Design documents from `/specs/008-postmortem-ppt-report/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md (todos presentes)

**Tests**: Incluidos — la Constitución del proyecto exige cobertura ≥80% para toda feature nueva (Principio II), y `plan.md` se compromete explícitamente a ello.

**Organization**: Tareas agrupadas por user story (US1/US2/US3, prioridad P1/P2/P3 de `spec.md`).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede ejecutarse en paralelo (ficheros distintos, sin dependencias pendientes)
- **[Story]**: User story a la que pertenece (US1, US2, US3)
- Rutas de fichero exactas en cada descripción

## Path Conventions

Proyecto único, extensión de `converters/` ya existente (ver `plan.md` → Project Structure):
- Código: `converters/src/report_generator/`, `converters/cli/generate_postmortem_report.py`
- Tests: `converters/tests/unit/report_generator/`, `converters/tests/integration/report_generator/`
- Backend local: `serve_app.py` (raíz del repo)
- Dashboards: `dashboards/postmortem/index.html`, `dashboards/release-kpis/app.js`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Preparar el paquete nuevo y sus dependencias antes de escribir ninguna lógica.

- [ ] T001 Crear la estructura del paquete `converters/src/report_generator/` con `__init__.py` vacío, y `converters/tests/unit/report_generator/__init__.py` + `converters/tests/integration/report_generator/__init__.py`
- [ ] T002 Añadir `python-pptx`, `plotly` y `kaleido` a `converters/requirements.txt` (ver research.md §1-2), con comentario explicando su propósito (igual que el resto del fichero, que hoy documenta por qué no hay dependencias)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infraestructura compartida que necesitan TODAS las user stories antes de poder implementarse.

**⚠️ CRITICAL**: Ninguna user story puede empezar hasta completar esta fase.

- [ ] T003 [P] Implementar `converters/src/report_generator/paths.py`: `sanitize_release_name(release_name) -> str` (FR-008, ver edge case de `spec.md` sobre caracteres no válidos) y `report_output_path(release_name, output_dir=None) -> Path` (por defecto `data/reports/<release_name_saneado>-postmortem-report.pptx`, ver research.md §6)
- [ ] T004 [P] Implementar `converters/src/report_generator/chart_utils.py`: constantes de color MASORANGE/Orange reutilizadas de los dashboards (`#FF7900`, `#FFC08A`, `#0C0B09`, etc.) y `export_figure_to_png(fig: plotly.graph_objects.Figure) -> bytes` vía Kaleido
- [ ] T005 Implementar `converters/src/report_generator/data_loader.py`: `load_postmortem_records(release_name) -> list[dict]` que busca en `data/output/*-postmortem.json` el fichero cuyo `_metadata.release_name` coincide (mismo criterio de agrupación que `converters/cli/cleanup_output.py`), y lanza `ReleaseNotFoundError` con mensaje claro si no hay ninguno (FR-009 — nunca debe generarse un informe con ceros)
- [ ] T006 Implementar el andamiaje base de `converters/src/report_generator/pptx_builder.py`: `new_presentation()` (tamaño de slide, portada con el nombre de la release), `add_kpi_slide(prs, report_data)` (tarjetas de KPI estilo dashboard), `add_chart_image_slide(prs, title, png_bytes)` (genérico, reutilizable por cualquier gráfica)

**Checkpoint**: A partir de aquí, US1, US2 y US3 pueden implementarse (US2 y US3 dependen funcionalmente de que US1 exista primero, ver Dependencies).

---

## Phase 3: User Story 1 - Generar el informe PPT de una release (Priority: P1) 🎯 MVP

**Goal**: Generar, para una release concreta con datos ya cargados, un `.pptx` descargable con sus 8 KPIs globales y sus 4 gráficas propias del dashboard de postmortem, con el mismo estilo visual y las mismas cifras que el dashboard.

**Independent Test**: Con datos de postmortem cargados para una release, generar su informe (CLI o endpoint) y comprobar que el `.pptx` se abre sin errores y que sus KPIs coinciden con los del dashboard para esa misma release.

### Tests for User Story 1

- [ ] T007 [P] [US1] Tests de `paths.py` en `converters/tests/unit/report_generator/test_paths.py` (saneado de nombres con espacios/caracteres especiales, ruta de salida por defecto)
- [ ] T008 [P] [US1] Tests de `data_loader.py` en `converters/tests/unit/report_generator/test_data_loader.py` (release encontrada, release inexistente lanza `ReleaseNotFoundError`, dos releases con `release_name` distinto no se mezclan)
- [ ] T009 [P] [US1] Tests de `kpi_calculator.py` en `converters/tests/unit/report_generator/test_kpi_calculator.py`: casos ya verificados manualmente en JS durante el desarrollo del dashboard — pendientes global/PaP/Mesa (no Cerrado/Resuelto en cualquier momento), % Cerradas incluye Cerrado y Resuelto, % Resueltas PaP solo cuenta resoluciones el mismo día calendario que el despliegue, Tiempo Medio de Resolución con fechas válidas e inválidas mezcladas, release sin incidencias PaP
- [ ] T010 [P] [US1] Tests de `postmortem_charts.py` en `converters/tests/unit/report_generator/test_postmortem_charts.py`: cada una de las 4 figuras contiene el número de trazas/puntos esperado para un dataset sintético; el rango de fechas de "Entradas, Resoluciones y Backlog" incluye resoluciones fuera del rango de "Fecha de envío" (regresión del bug corregido en `023-fix-evolution-chart-resolution-range`); "Por Sistema" excluye Cerrado/Resuelto por defecto

### Implementation for User Story 1

- [ ] T011 [P] [US1] Implementar `converters/src/report_generator/kpi_calculator.py`: `calculate_kpis(records) -> PostmortemReportData` (réplica de `analyzeData()` en `dashboards/postmortem/index.html`, ver data-model.md)
- [ ] T012 [P] [US1] Implementar `converters/src/report_generator/postmortem_charts.py`: `build_evolution_chart`, `build_pap_evolution_chart`, `build_open_incidents_chart`, `build_system_chart` (réplica de `createEvolutionChart()`, `createPapEvolutionChart()`, `createOpenIncidentsChart()`, `createSystemChart()`), usando `chart_utils.py` para colores y exportación a PNG
- [ ] T013 [US1] Extender `pptx_builder.py` con `add_postmortem_charts_slides(prs, charts)` que inserta las 4 gráficas de US1 vía `add_chart_image_slide` (depende de T006, T012)
- [ ] T014 [US1] Implementar `generate_report(release_name, output_path=None) -> dict` en `converters/cli/generate_postmortem_report.py`, orquestando `data_loader` → `kpi_calculator` → `postmortem_charts` → `pptx_builder`, devolviendo `{"success": True, "path": ...}` o `{"success": False, "error": ...}` (mismo contrato de resultado que `upload_csv.py`, ver contracts/cli.md)
- [ ] T015 [US1] Añadir el modo CLI individual (`argparse`) a `converters/cli/generate_postmortem_report.py`: `python generate_postmortem_report.py <release_name> [-o OUTPUT_PATH]`, exit code 1 si falla (contracts/cli.md)
- [ ] T016 [US1] Añadir el endpoint `GET /api/reports/postmortem/{release_name}` en `serve_app.py`: invoca `generate_report`, devuelve el `.pptx` como descarga (200), 404 si no hay datos, 500 en otro fallo (contracts/http-api.md); validar `release_name` contra los ficheros ya existentes en `data/output/` antes de generar nada (evita path traversal)
- [ ] T017 [US1] Añadir botón "Descargar informe PPT" en la cabecera de `dashboards/postmortem/index.html`, que llama al endpoint de T016 con el `release_name` actual del dashboard
- [ ] T018 [US1] Test de integración end-to-end en `converters/tests/integration/report_generator/test_generate_postmortem_report_e2e.py`: dataset sintético → `generate_report()` → abrir el `.pptx` resultante con `python-pptx` y verificar número de slides y que los 8 KPIs coinciden con los calculados manualmente para ese dataset
- [ ] T019 [US1] Validar manualmente los pasos de `quickstart.md` correspondientes a la generación individual (CLI y botón), con datos reales de una release ya cargada

**Checkpoint**: User Story 1 completa y comprobable de forma independiente — ya existe un informe PPT funcional por release, aunque sin el contexto comparativo de US2.

---

## Phase 4: User Story 2 - Incluir el contexto comparativo de release-kpis (Priority: P2)

**Goal**: Añadir al informe las 3 gráficas generales del dashboard de KPIs de Release (todas las releases, no solo la seleccionada), para dar contexto histórico.

**Independent Test**: Con al menos 3 releases cargadas, generar el informe de una de ellas y comprobar que las diapositivas de contexto muestran datos de todas las releases disponibles.

### Tests for User Story 2

- [ ] T020 [P] [US2] Tests de `release_kpis_data.py` en `converters/tests/unit/report_generator/test_release_kpis_data.py`: parseo correcto de `RAW_RELEASES` desde `dashboards/release-kpis/releases-data.js` (ver research.md §4), incluyendo el caso de una release con `papEntrada == 0`
- [ ] T021 [P] [US2] Tests de `release_kpis_charts.py` en `converters/tests/unit/report_generator/test_release_kpis_charts.py`: las 3 figuras contienen una entrada por release; la línea de objetivo del 75% aparece en las 2 gráficas de KPI (réplica fiel de `release-kpis/app.js`, incluida la discrepancia documentada en `spec.md` — no se corrige el 65% aquí)

### Implementation for User Story 2

- [ ] T022 [P] [US2] Implementar `converters/src/report_generator/release_kpis_data.py`: `load_release_kpis_context() -> ReleaseKpisContext` (lee y parsea `dashboards/release-kpis/releases-data.js`)
- [ ] T023 [P] [US2] Implementar `converters/src/report_generator/release_kpis_charts.py`: `build_incidencias_por_release_chart`, `build_kpi_pap_chart`, `build_kpi_post_chart` (réplica de `renderBarChart()` y `buildKpiChartData()` en `release-kpis/app.js`)
- [ ] T024 [US2] Extender `pptx_builder.py` con `add_release_kpis_context_slides(prs, context)` (depende de T006, T023)
- [ ] T025 [US2] Extender `generate_report()` en `converters/cli/generate_postmortem_report.py` para incluir las diapositivas de contexto de T024 (depende de T014, T022, T024)
- [ ] T026 [US2] Añadir botón "Descargar informe PPT" junto al nombre de cada release en la tabla de `dashboards/release-kpis/app.js`
- [ ] T027 [US2] Test de integración en `converters/tests/integration/report_generator/test_release_kpis_context.py`: con 3 releases sintéticas, el informe de una de ellas incluye las 3 gráficas generales con las 3 releases (no solo la seleccionada)

**Checkpoint**: User Story 1 y 2 funcionan juntas — el informe ya incluye contexto comparativo.

---

## Phase 5: User Story 3 - Generar informes para todas las releases de una vez (Priority: P3)

**Goal**: Generar los informes de todas las releases con datos disponibles en una sola acción.

**Independent Test**: Con 3 releases cargadas, solicitar la generación masiva y comprobar que se obtienen 3 ficheros `.pptx` correctos de forma independiente.

### Implementation for User Story 3

- [ ] T028 [US3] Añadir el modo `--all` a `converters/cli/generate_postmortem_report.py` (contracts/cli.md): recorre las releases con `-postmortem.json` en `data/output/`, genera el informe de cada una sin detenerse ante un fallo individual, imprime resumen final y exit code 1 si alguna falló (depende de T014, T025)
- [ ] T029 [US3] Añadir el endpoint `POST /api/reports/postmortem/batch` en `serve_app.py` (contracts/http-api.md): invoca el modo `--all` y devuelve `{"generated": [...], "failed": [...]}`
- [ ] T030 [US3] Test de integración en `converters/tests/integration/report_generator/test_generate_batch.py`: 3 releases sintéticas (una con datos inválidos que provoca fallo) → verifica 2 generadas + 1 en `failed`, sin que el fallo de una detenga las demás

**Checkpoint**: Las 3 user stories funcionan de forma independiente y conjunta.

---

## Phase 6: Cross-Repo (Producción)

**Purpose**: Replicar el endpoint en el backend real de producción, que vive en un repositorio hermano (ver research.md §5 y el patrón ya usado por `/api/upload` con `upload_csv.py`).

- [ ] T031 Replicar `GET /api/reports/postmortem/{release_name}` y `POST /api/reports/postmortem/batch` en `cso-incident-masivas-report/backend/main.py` (repositorio hermano, fuera de este repo), invocando `converters/cli/generate_postmortem_report.py` vía subproceso — mismo patrón que la integración existente de `/api/upload` con `upload_csv.py`. Requiere cambiar de repositorio para esta tarea.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Cierre de la feature una vez todas las user stories están implementadas.

- [ ] T032 [P] Actualizar `CLAUDE.md`: cambiar el estado de la feature 008 de "PLANNING COMPLETE" a "IMPLEMENTATION COMPLETE" con un resumen de lo entregado (mismo formato que la entrada de la feature 006)
- [ ] T033 Ejecutar la suite completa (`cd converters && python -m pytest tests/ -v --cov=src --cov-report=term-missing`) y confirmar que `report_generator` alcanza ≥80% de cobertura (Principio II de la Constitución)
- [ ] T034 [P] Verificar que `data/reports/` queda protegido por la regla `data/` ya existente en `.gitignore` (no debería requerir cambio; solo confirmar con `git check-ignore -v data/reports/cualquier-cosa.pptx`)
- [ ] T035 Validar manualmente el resto de `quickstart.md` (modo `--all`, botón de `release-kpis`, caso de error con una release inexistente) de principio a fin

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sin dependencias — puede empezar de inmediato
- **Foundational (Phase 2)**: Depende de Setup — BLOQUEA a US1, US2 y US3
- **User Story 1 (Phase 3)**: Depende de Foundational. Es la base funcional real del resto (US2 extiende `generate_report()` y `pptx_builder.py` que crea US1; US3 reutiliza `generate_report()` de US1)
- **User Story 2 (Phase 4)**: Depende de Foundational + de que exista `generate_report()` de US1 (T014) para poder extenderlo
- **User Story 3 (Phase 5)**: Depende de Foundational + de `generate_report()` de US1 (T014); es independiente de US2 en cuanto a lógica (generar en bucle), aunque en la práctica cada informe generado por `--all` ya incluirá el contexto de US2 si esa fase está completa
- **Cross-Repo (Phase 6)**: Depende de que Phase 3 (y opcionalmente 4-5) estén completas y estables en este repo
- **Polish (Phase 7)**: Depende de todas las fases anteriores que se hayan decidido completar

### Parallel Opportunities

- T001-T002 (Setup) en paralelo
- T003-T004 (Foundational) en paralelo; T005-T006 dependen de T003/T004 respectivamente y se hacen en serie tras ellas
- Todos los tests marcados [P] dentro de una misma user story, en paralelo entre sí
- T011 y T012 (US1) en paralelo entre sí (no dependen una de otra, ambas dependen solo de Foundational)
- T022 y T023 (US2) en paralelo entre sí

---

## Parallel Example: User Story 1

```bash
# Tests de User Story 1, en paralelo:
Task: "Tests de paths.py en converters/tests/unit/report_generator/test_paths.py"
Task: "Tests de data_loader.py en converters/tests/unit/report_generator/test_data_loader.py"
Task: "Tests de kpi_calculator.py en converters/tests/unit/report_generator/test_kpi_calculator.py"
Task: "Tests de postmortem_charts.py en converters/tests/unit/report_generator/test_postmortem_charts.py"

# Implementación, en paralelo:
Task: "Implementar kpi_calculator.py"
Task: "Implementar postmortem_charts.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Completar Fase 1: Setup
2. Completar Fase 2: Foundational (crítico, bloquea todo lo demás)
3. Completar Fase 3: User Story 1
4. **DETENERSE Y VALIDAR**: generar el informe de una release real y compararlo con el dashboard
5. El informe ya es útil y entregable en este punto (portada + KPIs + 4 gráficas propias)

### Incremental Delivery

1. Setup + Foundational → base lista
2. User Story 1 → validar de forma independiente → informe individual ya funcional (MVP)
3. User Story 2 → validar de forma independiente → informe con contexto comparativo
4. User Story 3 → validar de forma independiente → generación masiva
5. Cross-Repo → llevar la funcionalidad a producción
6. Polish → documentación, cobertura, validación final

---

## Notes

- [P] = ficheros distintos, sin dependencias pendientes entre sí
- [Story] mapea cada tarea a su user story para trazabilidad con `spec.md`
- El riesgo de duplicación de lógica JS↔Python (documentado en `research.md` §2-3) hace que los tests de T009/T010/T020/T021 sean especialmente importantes: son la única red de seguridad ante una futura divergencia entre el dashboard y el informe
- Confirmar que los tests fallan antes de implementar (TDD) donde el equipo lo considere valioso; no es bloqueante para el resto de tareas
- Detenerse en cada checkpoint para validar la user story de forma independiente antes de continuar
