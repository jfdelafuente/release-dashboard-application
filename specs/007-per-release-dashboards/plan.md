# Implementation Plan: Dashboards por Release

**Branch**: `007-per-release-dashboards` | **Date**: 2026-07-15 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/007-per-release-dashboards/spec.md`

## Summary

Sustituir el dashboard combinado de Postmortem/Release (que hoy solo auto-carga el archivo JSON más reciente) por un dashboard por release, identificado por el nombre que el usuario le da al subir el CSV. La navegación entre releases reutiliza la tabla ya existente en `dashboards/release-kpis/`: cada nombre de release de su columna "RELEASE" se convierte en un enlace a `/dashboards/postmortem/?release=<nombre>`. El nombre de release se propaga desde el formulario de subida hasta `_metadata.release_name` del JSON de postmortem y hasta `index.json`, sin tocar el motor de conversión existente más allá de un parámetro adicional. Todo se resuelve en el cliente (query string sobre la misma página estática) para no romper el principio "sin build step" del proyecto.

## Technical Context

**Language/Version**: Python 3.8+ (conversores, sin cambios de versión) · HTML5/CSS3/JavaScript ES6+ vanilla (dashboards, sin cambios)

**Primary Dependencies**: Ninguna nueva. Backend: `http.server`/`socketserver` (ya en uso vía `serve_app.py`), `argparse` (CLI de conversores). Frontend: Plotly.js vía CDN (ya en uso), `URLSearchParams` (API nativa del navegador, sin dependencia nueva).

**Storage**: Archivos JSON en `data/output/` (sin base de datos, sin cambios de mecanismo — se añade un campo a un esquema JSON ya existente).

**Testing**: `pytest` para el conversor (`converters/tests/`, siguiendo el patrón ya existente de tests unitarios/integración para `postmortem_converter.py` y `postmortem_schemas.py`). Verificación manual en navegador para los cambios de frontend (`quickstart.md`), igual que el resto de dashboards del proyecto — no existe hoy infraestructura de tests JS para ningún dashboard, y esta feature no la introduce.

**Target Platform**: Navegador de escritorio (principal), servido por `serve_app.py` en local o Nginx en producción — sin cambios de plataforma.

**Project Type**: Aplicación web (frontend estático + backend Python de conversión) — ya establecido, sin cambios de tipo de proyecto.

**Performance Goals**: Hereda los objetivos ya vigentes de la Constitución (carga inicial <2s con 100 incidencias, filtros <200ms, gráficas <500ms hasta 500 incidencias). No se espera regresión: cada dashboard de release carga un único archivo JSON ya acotado a esa release, en lugar de un archivo potencialmente creciente que mezclara todo el histórico.

**Constraints**: Sin build step (HTML/CSS/JS servidos directos); sin enrutamiento dinámico de servidor por segmentos de ruta (Nginx sirve `dashboards/` como alias estático); rutas root-absolutas ya establecidas en la reestructuración anterior (`/data/output/...`, `/dashboards/assets/...`).

**Scale/Scope**: Del orden de 40-50 releases históricas ya visibles en `dashboards/release-kpis/`; crecimiento moderado esperado (unas pocas releases nuevas por trimestre, no miles).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Evaluación |
|---|---|
| I. Code Quality | ✅ Cambios aditivos y localizados (un parámetro nuevo propagado por una cadena de llamadas ya existente); sin funciones nuevas por encima de la complejidad ciclomática permitida. |
| II. Testing Standards | ✅ con nota: se añaden/actualizan tests de `pytest` para `PostmortemConverter`/`ConversionMetadata`/`build_index_for_hub` cubriendo `release_name` (presente, ausente, y compatibilidad con JSON antiguos sin el campo). El frontend no tiene tests automatizados hoy en ningún dashboard del proyecto — esta feature sigue el mismo precedente ya aceptado (verificación manual vía `quickstart.md`), no introduce una regresión de cobertura nueva. |
| III. User Experience Consistency | ✅ Reutiliza topbar, paleta de color y patrones de layout ya existentes; la terminología ("Release", KPIs, Despliegue PAP/MESA) no cambia. |
| IV. Performance Requirements | ✅ Sin operaciones bloqueantes nuevas; cada dashboard de release carga un JSON típicamente más pequeño que el actual archivo combinado, no mayor. |
| V. Security & Data Integrity | ✅ `release_name` se trata como cadena de usuario: se escapa con `escapeHtml`/equivalente al mostrarse (mismo patrón ya usado en `release-kpis/app.js`) y se codifica con `encodeURIComponent` al construir la URL, evitando inyección vía query string. Sin `eval()` ni ejecución dinámica nueva. |
| VI. Documentation & Maintainability | ✅ Este plan, `research.md`, `data-model.md` y `contracts/` documentan el cambio de esquema; `dashboards/README.md` y la documentación de `converters/docs/API.md` se actualizan como parte de la implementación (tarea de documentación, no de código). |

Sin violaciones que requieran justificación — no aplica tabla de Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/007-per-release-dashboards/
├── plan.md              # Este archivo
├── research.md          # Fase 0: decisiones técnicas y alternativas descartadas
├── data-model.md         # Fase 1: esquema de Release y extensión de _metadata/index.json
├── quickstart.md        # Fase 1: guía de verificación manual end-to-end
├── contracts/
│   ├── upload-endpoint.md   # Contrato de POST /api/upload y CLI convert_postmortems.py
│   └── dashboard-url.md     # Contrato de la URL /dashboards/postmortem/?release=...
└── tasks.md             # Fase 2 (creado por /speckit-tasks, no por este comando)
```

### Source Code (repository root)

```text
serve_app.py                                          # handle_upload(): + campo release_name

converters/
├── cli/
│   ├── upload_csv.py                                  # run_upload(): + parámetro release_name → --release-name
│   └── convert_postmortems.py                         # + argparse --release-name; build_index_for_hub(): + lectura de _metadata.release_name
├── src/csv_to_json/
│   ├── postmortem_converter.py                        # convert_file()/generatePostmortemJSON(): + parámetro release_name
│   └── postmortem_schemas.py                           # ConversionMetadata: + atributo release_name en __init__/to_dict()
└── tests/
    └── (actualizar/añadir casos en los ficheros de test ya existentes para
        PostmortemConverter, ConversionMetadata y build_index — ver research.md R6
        sobre la duplicación de tests a resolver antes de decidir dónde añadirlos)

dashboards/
├── release-kpis/
│   └── app.js                                          # renderTable(): columna RELEASE pasa a <a> enlazando a /dashboards/postmortem/?release=...
└── postmortem/
    └── index.html                                     # autoLoadLatestData() + lectura de URLSearchParams; 3 estados
                                                          # (sin parámetro / release con datos / release sin datos);
                                                          # cabecera dinámica con el nombre de la release

converters/docs/API.md                                  # documentar el nuevo campo release_name en _metadata e index.json
dashboards/README.md                                    # documentar el nuevo flujo de navegación por release
```

**Structure Decision**: No se crean carpetas ni proyectos nuevos. El cambio se reparte entre el backend de conversión ya existente (`converters/`) y dos de los dashboards ya existentes (`release-kpis`, `postmortem`), siguiendo exactamente los mismos archivos y patrones que ya usan hoy para funciones equivalentes (propagación de parámetros opcionales en el conversor; queries client-side en JS vanilla). No aplica ninguna de las estructuras de opción del template (no es una librería, ni una app móvil, ni requiere una carpeta `backend/`/`frontend/` separada — el patrón real de este repo, "conversores Python + dashboards estáticos como componentes independientes", ya está reflejado directamente en el árbol de arriba).

## Complexity Tracking

*No aplica — sin violaciones de la Constitución que justificar.*
