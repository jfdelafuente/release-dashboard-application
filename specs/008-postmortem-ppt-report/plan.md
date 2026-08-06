# Implementation Plan: Informe PPT de Postmortem por Release

**Branch**: `008-postmortem-ppt-report` | **Date**: 2026-08-04 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/008-postmortem-ppt-report/spec.md`

## Summary

Generar, por release, un informe `.pptx` descargable con el estilo visual del dashboard de
postmortem: sus 8 KPIs globales, sus 4 gráficas propias, y las 3 gráficas generales (todas las
releases) del dashboard de KPIs de Release. Se implementa como un script Python nuevo
(`converters/cli/generate_postmortem_report.py`, reutilizable como CLI y como librería, mismo
patrón que `upload_csv.py`), que recalcula los KPIs con la misma lógica del JS actual, reconstruye
las 7 gráficas con Plotly (Python) + Kaleido para exportarlas a PNG, y las ensambla con
`python-pptx`. Se expone en los dashboards mediante un endpoint HTTP nuevo, implementado tanto en
`serve_app.py` (local) como en el backend del repo hermano (producción).

## Technical Context

**Language/Version**: Python 3.11 (mismo runtime que el resto de `converters/`)

**Primary Dependencies**: `python-pptx` (ensamblado del .pptx), `plotly` + `kaleido` (reconstrucción y exportación a PNG de las 7 gráficas) — nuevas dependencias de producción, añadidas a `converters/requirements.txt`

**Storage**: Ficheros (`data/output/*.json` como entrada, `dashboards/release-kpis/releases-data.js` como entrada, `data/reports/*.pptx` como salida) — sin base de datos

**Testing**: pytest (mismo framework y convenciones que `converters/tests/`)

**Target Platform**: Servidor Linux (producción) y Windows (desarrollo local), igual que el resto del proyecto

**Project Type**: Extensión de la CLI/librería de conversión existente (`converters/`) + un endpoint HTTP nuevo en el backend ya existente (local y producción)

**Performance Goals**: Generar un informe completo (KPIs + 7 gráficas) en menos de 1 minuto (SC-001), para datasets de hasta ~1000 incidencias por release (mismo orden de magnitud que maneja hoy el dashboard)

**Constraints**: Sin dependencias de navegador/UI headless (ver research.md §2); el .pptx debe abrir sin errores en PowerPoint, LibreOffice Impress y Google Slides (SC-003)

**Scale/Scope**: Un informe por release; generación bajo demanda (no programada), volumen esperado de pocas releases activas a la vez (igual que hoy en `release-kpis`)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Evaluación |
|---|---|
| I. Code Quality | ✅ Cumple. El nuevo módulo se divide en funciones pequeñas de responsabilidad única (una por KPI/gráfica), sin números mágicos (constantes nombradas para colores/objetivo KPI, reutilizando los mismos valores hex que el JS) |
| II. Testing Standards | ✅ Cumple, con matiz. Se añaden tests unitarios (≥80% cobertura) para el cálculo de KPIs y la agregación de cada gráfica, con casos ya verificados manualmente en JS durante el desarrollo de los dashboards (mismos datos de entrada esperando el mismo resultado). Ver riesgo de duplicación de lógica JS↔Python documentado en research.md §2-3: no hay forma de compartir literalmente el mismo código entre navegador y servidor sin añadir una dependencia de navegador headless (descartada por coste/beneficio) |
| III. User Experience Consistency | ✅ Cumple. Paleta de colores MASORANGE/Orange (#FF7900 etc.) replicada en las gráficas Python; terminología idéntica a la de los dashboards (mismos nombres de KPI y de gráficas) |
| IV. Performance Requirements | ✅ Cumple. La generación es una operación batch bajo demanda (no en el hot path de carga de los dashboards existentes); el objetivo de <1 minuto (SC-001) es holgado frente al volumen de datos actual |
| V. Security & Data Integrity | ✅ Cumple, con acción explícita. `release_name` llega desde una URL/parámetro externo y se usa para derivar un nombre de fichero — se sanea explícitamente (FR-008) y se valida contra los datos ya existentes en `data/output/` antes de generar nada, evitando path traversal o generación de ficheros arbitrarios |
| VI. Documentation & Maintainability | ✅ Cumple. `CLAUDE.md` se actualiza con la nueva feature (este comando); el riesgo de duplicación de lógica JS↔Python queda documentado explícitamente en `research.md` para que un cambio futuro en el JS recuerde revisar el módulo Python equivalente |

Sin violaciones que requieran justificación en Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/008-postmortem-ppt-report/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
converters/
├── cli/
│   └── generate_postmortem_report.py   # NUEVO — CLI + librería (generate_report())
├── src/
│   └── report_generator/               # NUEVO paquete
│       ├── __init__.py
│       ├── kpi_calculator.py           # Réplica de analyzeData() (dashboards/postmortem)
│       ├── postmortem_charts.py        # Réplica de las 4 gráficas del dashboard de postmortem
│       ├── release_kpis_charts.py      # Réplica de las 3 gráficas de release-kpis/app.js
│       ├── release_kpis_data.py        # Parser de RAW_RELEASES (releases-data.js) — ver research.md §4
│       └── pptx_builder.py             # Ensamblado de las diapositivas con python-pptx
└── tests/
    └── unit/
        └── report_generator/           # NUEVO — tests de kpi_calculator, charts, pptx_builder

serve_app.py                            # + endpoint GET /api/reports/postmortem/{release_name}
                                         # + endpoint POST /api/reports/postmortem/batch

dashboards/
├── release-kpis/
│   └── app.js                          # + botón "Descargar informe PPT" por fila de release
└── postmortem/
    └── index.html                      # + botón "Descargar informe PPT" en la cabecera

data/
└── reports/                            # NUEVO directorio de salida (protegido por .gitignore, igual que data/output)
```

**Structure Decision**: Se extiende `converters/` (ya existente) con un paquete nuevo
`report_generator` y un script CLI nuevo, siguiendo exactamente el mismo patrón que
`convert_postmortems.py`/`convert_incidents.py`/`upload_csv.py` (script fino + lógica en `src/`,
invocable como CLI o como librería). No se crea un proyecto/carpeta de nivel superior nuevo: esta
feature es una extensión natural de la CLI de conversión existente, más dos endpoints delgados en
el backend ya existente y dos botones en dashboards ya existentes.

## Complexity Tracking

*Sin violaciones — el Constitution Check no encontró incumplimientos que requieran justificación.*
