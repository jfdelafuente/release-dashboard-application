# Implementation Plan: Buscador de Incidencias con Resumen IA en Portal Principal

**Branch**: `009-portal-incident-search` | **Date**: 2026-10-06 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/009-portal-incident-search/spec.md`

## Summary

Integrar en la parte superior del portal principal (`dashboards/portal/index.html`) un buscador destacado de incidencias que permita a los operadores y responsables consultar cualquier identificador de incidencia (ej. `INC000004141215`) y abrir inmediatamente la pantalla flotante interactiva de Resumen IA. Se reutiliza la arquitectura modular existente (`dashboards/assets/resumen-ia.js` y `dashboards/assets/resumen-ia.css`), aprovechando el singleton `window.ResumenIAModal`, el bypass CORS y la protección de doble capa de caché (cliente + Nginx `proxy_cache`), garantizando normalización inteligente de entrada, accesibilidad WCAG por teclado y diseño corporativo alineado con Orange.

## Technical Context

**Language/Version**: HTML5, Vanilla JavaScript (ES2020+), CSS3 (CSS Variables, Flexbox, CSS Grid) — coherente con la arquitectura frontend sin frameworks de la aplicación

**Primary Dependencies**: 
- `dashboards/assets/resumen-ia.js` (componente modal y gestor de peticiones Epsilon IA)
- `dashboards/assets/resumen-ia.css` (estilos visuales del modal y animaciones)
- Endpoint proxy `/api/epsilon/resumenIA/<codigo>` en `serve_app.py` (desarrollo local) y Nginx `nginx.conf` (producción)

**Storage**: `sessionStorage` del navegador para la caché de respuestas recientes (15 min) gestionada por `resumen-ia.js`; sin persistencia en base de datos adicional

**Testing**: Pruebas manuales estructuradas y scripts de verificación de formato/normalización de entrada con Node.js o PowerShell/Python

**Target Platform**: Servidor Linux VPS (Nginx 1.24+ en espacio no privilegiado `/infocodes`), navegadores modernos de escritorio (Chrome, Edge, Firefox, Safari) y visualización adaptable a tablets y móviles

**Project Type**: Mejora de interfaz frontend en portal de entrada (`dashboards/portal/index.html`) con reutilización de componentes estáticos compartidos

**Performance Goals**: Apertura del modal en <2 segundos en primera consulta de red; resolución instantánea (0 ms) si la incidencia ya reside en caché local de sesión; validación local y prevención de envío en 0 ms

**Constraints**: Sin librerías o frameworks pesados (React, Vue); código nativo que no requiera proceso de compilación (build step); plena compatibilidad con las directivas de seguridad y proxies del entorno

**Scale/Scope**: Un componente de búsqueda hero en `dashboards/portal/index.html` consumido por operadores de operaciones de servicio de Orange

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Evaluación |
|---|---|
| I. Code Quality | ✅ Cumple. Lógica de normalización encapsulada en funciones de responsabilidad única (`sanitizeIncidentCode()`, `handleIncidentSearch()`). Sin números mágicos, usando constantes documentadas (`DEFAULT_INCIDENT_PREFIX = 'INC'`). |
| II. Testing Standards | ✅ Cumple. Se definen escenarios de prueba independientes (P1, P2, P3) y una suite de pruebas de normalización para todas las variantes de código de incidencia y casos de borde. |
| III. User Experience Consistency | ✅ Cumple. Identidad visual de Orange (#FF7900), tipografía Inter/Plex Mono, feedback visual no intrusivo, estados de foco accesibles y soporte íntegro de navegación por teclado (Enter, Esc, Tab). |
| IV. Performance Requirements | ✅ Cumple. 0 ms de latencia en validación local, reutilización de la caché en cliente y en servidor Nginx (`proxy_cache my_cache`). Sin impacto en el tiempo de carga del portal. |
| V. Security & Data Integrity | ✅ Cumple. Saneamiento estricto de la entrada del usuario antes de invocar la API o renderizar el DOM, previniendo XSS o inyecciones de parámetros. |
| VI. Documentation & Maintainability | ✅ Cumple. Especificación, plan, modelo de datos, contratos y quickstart documentados en `specs/009-portal-incident-search/` y reflejados en `CLAUDE.md`. |

Sin violaciones que requieran justificación en Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/009-portal-incident-search/
├── spec.md              # Feature specification
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   ├── search-component-contract.md
│   └── epsilon-api-contract.md
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code (repository root)

```text
dashboards/
├── portal/
│   └── index.html       # MODIFICADO: Bloque hero buscador + estilos + integración resumen-ia
├── assets/
│   ├── resumen-ia.js    # EXISTENTE: Singleton window.ResumenIAModal (consumido sin alterar)
│   └── resumen-ia.css   # EXISTENTE: Estilos del modal (consumido sin alterar)

serve_app.py             # EXISTENTE: Proxy local /api/epsilon/resumenIA/<codigo> con caché

nginx.conf               # EXISTENTE: Proxy de producción location /api/epsilon/ con proxy_cache
```

**Structure Decision**: La funcionalidad se implementa directamente en `dashboards/portal/index.html` reutilizando los componentes transversales `dashboards/assets/resumen-ia.{js,css}` ya probados y estabilizados en los dashboards de Incidencias Masivas y Postmortem.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

*No hay violaciones. El diseño se apoya 100% en componentes existentes y patrones estándar del proyecto.*
