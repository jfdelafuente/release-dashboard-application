# Tasks: Informe Ejecutivo de Incidencias Postmortem (010-incident-executive-report)

**Input**: Design documents from `specs/010-incident-executive-report/`
- Spec: [spec.md](spec.md)
- Plan: [plan.md](plan.md)
- Research: [research.md](research.md)
- Data Model: [data-model.md](data-model.md)
- Contracts: [contracts/](contracts/)
- Quickstart: [quickstart.md](quickstart.md)

**Prerequisites**: Python 3.12 con `python-pptx` instalado; plantilla de referencia `20260609 Incidencia IVR ExMM.pptx` disponible.

**Organization**: Tareas agrupadas por historia de usuario para permitir desarrollo y verificación independiente.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Inicialización del entorno de plantillas corporativas y directorios de almacenamiento.

- [X] T001 Copiar y registrar la plantilla corporativa `20260609 Incidencia IVR ExMM.pptx` en `converters/src/report_generator/assets/executive_template.pptx`
- [X] T002 Crear el directorio de persistencia para informes ejecutivos generados en `data/reports/executive/.gitkeep`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Modelos de datos compartidos, validación y gestión de rutas que bloquean la implementación de las historias de usuario.

**⚠️ CRITICAL**: Completar esta fase antes de comenzar la implementación de las historias de usuario.

- [X] T003 Definir modelos y esquemas de datos tipados en `converters/src/report_generator/executive_models.py`
- [X] T004 [P] Implementar resolución de rutas y sanitización de nombres de informe en `converters/src/report_generator/executive_paths.py`

**Checkpoint**: Base de datos e infraestructura común lista. Las historias de usuario pueden proceder.

---

## Phase 3: User Story 1 - Solicitud y Descarga del Informe Ejecutivo desde Gestión de Problemas (Priority: P1) 🎯 MVP

**Goal**: Permitir la generación y descarga bajo demanda de una presentación ejecutiva PowerPoint (`.pptx`) con la estética de Orange a partir de datos estructurados, activada desde la tabla de candidatos de Gestión de Problemas.

**Independent Test**: Ejecutar `pytest converters/tests/unit/report_generator/test_executive_report_builder.py` para generar el `.pptx` y comprobar la descarga del binario mediante `GET /api/reports/executive-incident/{incidentRef}` en `serve_app.py`.

### Tests para User Story 1

- [X] T005 [P] [US1] Implementar tests unitarios para el generador de presentaciones ejecutivas en `converters/tests/unit/report_generator/test_executive_report_builder.py`

### Implementación para User Story 1

- [X] T006 [US1] Implementar el generador de presentaciones `ExecutiveReportBuilder` en `converters/src/report_generator/executive_report_builder.py` (mapeo de diapositiva 1 con resumen, cajas y tabla de acciones; diapositivas 2 y 3 con cronología)
- [X] T007 [US1] Implementar endpoints de generación y descarga (`POST /api/reports/executive-incident` y `GET /api/reports/executive-incident/{incidentRef}`) en `serve_app.py`
- [X] T008 [P] [US1] Crear componente interactivo `ExecutiveReportModal.tsx` en `../gestion-problemas-dashboard/components/ExecutiveReportModal.tsx`
- [X] T009 [US1] Integrar el botón "Generar PPT" en las filas de postmortems de `../gestion-problemas-dashboard/components/IssuesTable.tsx` conectado con `ExecutiveReportModal.tsx`

**Checkpoint**: User Story 1 (MVP) completamente funcional e independientemente verificable.

---

## Phase 4: User Story 2 - Ingesta Estructurada y Resiliente desde Confluence (Priority: P2)

**Goal**: Extraer de forma tolerante a fallos la información de la página de postmortem de Confluence (metadatos, impacto, causa, solución, tabla de acciones y cronología) operando con la sesión del navegador o entrada del operador.

**Independent Test**: Ejecutar `pytest converters/tests/unit/report_generator/test_confluence_parser.py` con contenido de muestra de Confluence y validar la correcta extracción y mapeo a `ExecutiveIncidentData`.

### Tests para User Story 2

- [X] T010 [P] [US2] Implementar tests unitarios para el parser de Confluence en `converters/tests/unit/report_generator/test_confluence_parser.py`

### Implementación para User Story 2

- [X] T011 [US2] Implementar el módulo `confluence_parser.py` en `converters/src/report_generator/confluence_parser.py` para extracción y normalización de bloques y tablas
- [X] T012 [US2] Conectar el parser en `../gestion-problemas-dashboard/components/ExecutiveReportModal.tsx` y en el backend para auto-cargar datos desde la URL o contenido pegado

**Checkpoint**: Ingesta automatizada desde Confluence conectada de extremo a extremo.

---

## Phase 5: User Story 3 - Consulta Rápida y Reutilización de Informes Generados (Priority: P3)

**Goal**: Evitar recomputaciones innecesarias permitiendo la descarga inmediata (`0 ms`) si el `.pptx` ya fue generado, ofreciendo la opción de "Regenerar" si Confluence se actualizó.

**Independent Test**: Solicitar el informe de una incidencia, refrescar la vista en el dashboard y validar que el botón cambia a "Descargar PPT" con opción secundaria de "Regenerar".

### Implementación para User Story 3

- [X] T013 [P] [US3] Implementar endpoint de comprobación de estado `GET /api/reports/executive-incident/{incidentRef}/status` en `serve_app.py`
- [X] T014 [US3] Actualizar estados dinámicos del botón en `../gestion-problemas-dashboard/components/IssuesTable.tsx` (Generar / Descargar directo / Regenerar)
- [X] T015 [US3] Implementar soporte para parámetro `force=true` en el backend para regeneración y reemplazo del archivo en disco

**Checkpoint**: Ciclo de vida completo del informe (creación, caché, descarga directa y actualización forzada) operativo.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Herramientas de automatización CLI, documentación técnica y validación final.

- [X] T016 [P] Implementar script CLI de generación directa en `converters/cli/generate_executive_report.py`
- [X] T017 [P] Crear documentación de uso y arquitectura en `docs/INFORME-EJECUTIVO-POSTMORTEM.md` y actualizar `README.md`
- [X] T018 Ejecutar validación de aceptación de extremo a extremo conforme a `specs/010-incident-executive-report/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sin dependencias - ejecutable de inmediato.
- **Foundational (Phase 2)**: Depende de Phase 1 - BLOQUEA todas las historias de usuario.
- **User Story 1 (Phase 3)**: Depende de Phase 2 - Flujo central y MVP de generación PPTX.
- **User Story 2 (Phase 4)**: Depende de Phase 2 - Automatiza la extracción de Confluence para alimentar US1.
- **User Story 3 (Phase 5)**: Depende de US1 y US2 - Optimiza el reuso con caché y regeneración.
- **Polish (Phase 6)**: Depende de la finalización de las historias de usuario deseadas.

---

## Parallel Opportunities

- **Fase 2**: `T003` y `T004` pueden desarrollarse en paralelo.
- **Fase 3**: `T005` (test) y `T008` (modal UI) pueden implementarse en paralelo con `T006` y `T007`.
- **Fase 4**: `T010` (test parser) puede desarrollarse en paralelo con `T011`.
- **Fase 6**: `T016` (CLI) y `T017` (docs) pueden ejecutarse en paralelo.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Completar Phase 1: Setup (`T001`-`T002`)
2. Completar Phase 2: Foundational (`T003`-`T004`)
3. Completar Phase 3: User Story 1 (`T005`-`T009`)
4. **Validar MVP**: Ejecutar test de generación de PowerPoint y verificar la descarga de la presentación `.pptx` en local.

### Entrega Incremental

1. MVP funcional con generación manual/estructurada de la presentación.
2. Ingesta inteligente y parsing de páginas de Confluence (US2).
3. Caché de informes generados y regeneración bajo demanda en la UI (US3).
4. Herramienta CLI y documentación consolidada (Fase 6).

