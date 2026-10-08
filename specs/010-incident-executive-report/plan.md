# Implementation Plan: Informe Ejecutivo de Incidencias Postmortem (010-incident-executive-report)

**Branch**: `010-incident-executive-report` | **Date**: 2026-10-06 | **Spec**: [specs/010-incident-executive-report/spec.md](spec.md)

**Input**: Feature specification from `specs/010-incident-executive-report/spec.md` y plantilla corporativa `20260609 Incidencia IVR ExMM.pptx`.

---

## Summary

Implementar un flujo integral y bajo demanda para generar informes ejecutivos de incidencias postmortem en formato Microsoft PowerPoint (`.pptx`), con fidelidad visual absoluta a la plantilla de referencia `20260609 Incidencia IVR ExMM.pptx` (Diapositiva 1 con metadatos temporales, impacto, causa, solución y tabla de puntos de acción; Diapositivas 2 y 3 con cronología paginada de eventos). La generación se solicita desde la tabla de candidatos a postmortem del dashboard de Gestión de Problemas (`IssuesTable.tsx`), permitiendo validar/introducir el enlace de Confluence en un modal interactivo, procesando los datos mediante un servicio en Python (`python-pptx`) y ofreciendo descarga directa y almacenamiento en disco para consultas instantáneas y regeneraciones.

---

## Technical Context

**Language/Version**: Python 3.12 (backend / generador) + TypeScript / React (Next.js 15 en `gestion-problemas-dashboard`) + Vanilla JS / CSS en dashboards estáticos.

**Primary Dependencies**: `python-pptx` (generación y manipulación de presentaciones Office OpenXML), `urllib` / `requests` / `BeautifulSoup4` o regex nativo (parseo de HTML/Confluence), React / Tailwind / Lucide Icons (modal y botón en frontend).

**Storage**: Sistema de archivos local (`data/reports/executive/RESUMEN_EJECUTIVO_{incidentRef}.pptx`) con control de timestamps y metadatos JSON para descargas instantáneas en 0 ms.

**Testing**: `pytest` para la suite de pruebas unitarias y de integración de Python (`converters/tests/unit/report_generator/test_executive_report_builder.py` y `test_confluence_parser.py`); `npm test` o tests unitarios en Next.js para los componentes UI.

**Target Platform**: Linux servidor (producción Debian/Ubuntu en `10.132.68.85` bajo Nginx y FastAPI/pm2) y Windows (entorno de desarrollo local con PowerShell y Python 3.12).

**Project Type**: Servicio web y CLI con integración entre backend (`serve_app.py` / FastAPI) y frontend (`gestion-problemas-dashboard` / Portal de Dashboards).

**Performance Goals**: Generación completa del `.pptx` en < 15 segundos; respuesta de descarga de informe en caché en < 1 segundo; interacción UI modal en < 200 ms.

**Constraints**: Sin dependencias de navegadores externos con permisos de root (evitar headless Chrome / kaleido con `sudo`); compatibilidad estricta con la paleta de color Orange (`#FF7900`) y tipografía corporativa; memoria < 100MB durante la generación.

**Scale/Scope**: ~10 a 50 postmortems candidatos al mes; soporte para tablas cronológicas extensas (>40 eventos) mediante paginación automática sin deformar plantillas.

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

- **Principio I (Calidad de Código)**: ✅ Cumple. Se modularizan las responsabilidades: módulo extractor (`confluence_parser.py`), módulo constructor PPT (`executive_report_builder.py`), endpoint HTTP y componente UI (`ExecutiveReportModal.tsx`). Complejidad ciclomática < 10 por función.
- **Principio II (Estándares de Testing)**: ✅ Cumple. Pruebas unitarias para el parser de Confluence (casos con datos completos, faltantes, tablas largas) y para el generador de PowerPoint (validación de diapositivas, textos y tablas).
- **Principio III (Consistencia de UX)**: ✅ Cumple. Colores corporativos oficiales de Orange (`#FF7900`), términos consistentes en español ("Informe Ejecutivo", "Generar", "Descargar", "Regenerar"), soporte de teclado y accesibilidad (WCAG 2.1 AA).
- **Principio IV (Rendimiento)**: ✅ Cumple. El uso de `python-pptx` permite generar el archivo en < 1.5s, muy por debajo del objetivo de 15s. Almacenamiento en disco para descargas inmediatas (< 1s).
- **Principio V (Seguridad e Integridad)**: ✅ Cumple. Se limpian y sanitizan los códigos de incidencia y entradas de texto. Enlaces externos usan HTTPS. La sesión del usuario valida el acceso al postmortem sin exponer credenciales globales.
- **Principio VI (Documentación y Mantenibilidad)**: ✅ Cumple. Documentación completa en `specs/010-incident-executive-report/`, `quickstart.md`, contratos API y actualización de `CLAUDE.md`.

---

## Project Structure

### Documentation (this feature)

```text
specs/010-incident-executive-report/
├── spec.md              # Especificación funcional validada
├── checklists/
│   └── requirements.md  # Checklist de requisitos (100% verificado)
├── research.md          # Decisiones técnicas y análisis de alternativas
├── data-model.md        # Entidades, campos y diagrama de relaciones
├── quickstart.md        # Guía paso a paso para pruebas locales
├── contracts/           # Contratos formales de interfaces
│   ├── executive-report-api-contract.md
│   ├── confluence-ingest-contract.md
│   └── ui-button-modal-contract.md
└── plan.md              # Este plan de implementación
```

### Source Code

```text
# Repositorio Principal: release-dashboard-application
converters/
├── src/
│   └── report_generator/
│       ├── assets/
│       │   └── executive_template.pptx      # Plantilla base copiada de 20260609 Incidencia IVR ExMM.pptx
│       ├── executive_report_builder.py      # Generador python-pptx de 3+ diapositivas
│       └── confluence_parser.py             # Parser tolerante a fallos de Confluence
├── cli/
│   └── generate_executive_report.py         # Punto de entrada CLI para pruebas y automatización
└── tests/
    └── unit/
        └── report_generator/
            ├── test_executive_report_builder.py
            └── test_confluence_parser.py

serve_app.py                                 # Endpoints /api/reports/executive-incident/*

# Repositorio Hermano: gestion-problemas-dashboard
components/
├── ExecutiveReportModal.tsx                 # Modal interactivo con input URL y feedback de progreso
└── IssuesTable.tsx                          # Integración del botón Generar/Descargar/Regenerar por fila
```

**Structure Decision**: Se aloja el motor de generación, la plantilla y los endpoints de API en `release-dashboard-application` (aprovechando el entorno Python existente y la suite de `converters`), y se conecta visualmente desde `gestion-problemas-dashboard` mediante el proxy ya configurado en Nginx y en `serve_app.py`.

---

## Complexity Tracking

| Decisión | Justificación | Alternativa Más Simple Rechazada Porque |
|---|---|---|
| Reutilización de plantilla `.pptx` preexistente | Garantiza el 100% de la identidad corporativa Orange sin remaquetar desde cero por código. | Generar formas en blanco: rechazada por fragilidad visual y desajustes tipográficos. |
| Extracción con sesión de operador en modal | Permite el acceso transparente a Confluence bajo SSO corporativo sin configurar tokens globales. | Cuentas de servicio centralizadas: rechazada porque requieren aprobaciones de seguridad prolongadas y rotación de tokens. |
