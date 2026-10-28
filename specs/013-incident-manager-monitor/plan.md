# Implementation Plan: Frontal Web de Monitorización para Incident Manager (013-incident-manager-monitor)

**Branch**: `013-incident-manager-monitor` | **Date**: 2026-10-28 | **Spec**: [`specs/013-incident-manager-monitor/spec.md`](./spec.md)

**Input**: Feature specification from [`specs/013-incident-manager-monitor/spec.md`](./spec.md)

---

## Summary

Esta funcionalidad implementa una consola web especializada de monitorización (*Cockpit*) para el **Incident Manager** que centraliza y vigila en tiempo real las incidencias activas de alta prioridad (P1, P2 y discrepancias de triaje) que están **pendientes de redacción ejecutiva de agente**.

La herramienta se apoya plenamente en los artefactos ya existentes en el repositorio (`high_priority_notifications.json`, `agent_executive_messages.json`, `scan_pending_incidents.py`, `update_agent_message.py` y `serve_app.py`), ofreciendo:
1. **Aislamiento estricto**: Despliegue en `/dashboards/incident-manager-monitor/` **sin ningún enlace ni referencia en el portal general** (`dashboards/portal/index.html` ni `dashboards/index.html`).
2. **Cockpit Operativo de Alta Densidad**: Barra de KPIs en tiempo real (pendientes con resalte visual, completadas, P1/P2 y discrepancias) y cola filtrable orientada por defecto a tickets pendientes.
3. **Inspección de Contexto y Copia de Prompts**: Visualización del Proceso Crítico de Negocio, Criterio ITIL, Sistemas y Epsilon IA, con botón de copia en 1 clic del prompt de cada fase (`Apertura`, `Seguimiento`, `Cierre`) listo para el agente `incident-reporter`.
4. **Asistente de Ingesta con Validación en Vivo**: Validación reactiva de límites de palabras ($\le$ 90 monopárrafo y $\le$ 30 breve) con persistencia directa en el almacén persistente o generación de comandos CLI de contingencia.

---

## Technical Context

**Language/Version**:
- Backend / CLI: Python 3.10+ (compatible con Python 3.9+ en Rocky Linux 9).
- Frontend: Vanilla JavaScript (ES6+), HTML5 semántico y CSS3 nativo sin dependencias de frameworks externos.

**Primary Dependencies**:
- Backend: Bibliotecas estándar de Python (`json`, `urllib`, `argparse`, `pathlib`, `http.server`, `re`, `datetime`). Testing con `pytest`.
- Frontend: Reutilización de estilos existentes (`topbar.css`, `shared.css`, `resumen-ia.css`, `resumen-ia.js`).

**Storage**:
- Catálogo de alertas activas: `data/output/high_priority_notifications.json`.
- Almacén de redacciones de agente: `data/agent_executive_messages.json`.
- Servidor web: Ficheros estáticos servidos en `dashboards/incident-manager-monitor/`.

**Testing**:
- Pruebas unitarias en Python para los endpoints de soporte y validación de palabras (`pytest converters/tests/unit/`).
- Pruebas de contrato y verificación estática de aislamiento (asegurando que `portal/index.html` no contenga referencias a `incident-manager-monitor`).

**Target Platform**:
- Entorno de desarrollo local: Windows 10/11 con `serve_app.py` (puerto 8080).
- Entorno de producción: Servidor VPS Rocky Linux 9 con Nginx.

**Project Type**:
- Frontend Web Dashboard (`dashboards/incident-manager-monitor/`) + API extensions en `serve_app.py`.

**Performance Goals**:
- Carga inicial y renderizado completo de la consola en $< 500\text{ ms}$.
- Filtrado dinámico en cliente (búsqueda, severidad, proceso) en $< 30\text{ ms}$.
- Copia de prompt y feedback visual en $< 5\text{ ms}$.

**Constraints**:
- **Aislamiento**: 0 enlaces en el portal público general.
- **Límites de Palabras**: Restricción estricta de longitud en mensajes ejecutivos ($\le$ 90 palabras en versión completa monopárrafo, $\le$ 30 palabras en versión breve).
- **Guardrail Anti-Alucinación**: Todos los datos mostrados deben proceder exclusivamente de los ficheros de catálogo y almacén.
- **Tolerancia a Fallos**: Si el guardado HTTP falla, la interfaz siempre provee el comando CLI `update_agent_message.py` listo para copiar.

**Scale/Scope**:
- 1 nuevo dashboard web especializado (`dashboards/incident-manager-monitor/index.html`, `monitor.css`, `monitor.js`).
- 2 endpoints HTTP en `serve_app.py` (`/api/incident-manager/pending` y `/api/incident-manager/save-message`).
- 1 suite de pruebas de aislamiento y endpoints.

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Estado | Justificación y Cumplimiento |
| :--- | :--- | :--- |
| **I. Code Quality** | ✅ PASS | Separación nítida entre lógica de filtrado, renderizado DOM y gestión de API. Funciones JS puras y modulares. Naming consistente. |
| **II. Testing Standards** | ✅ PASS | Tests con `pytest` que cubren contratos de API, validación de palabras, aislamiento estricto de `portal/index.html` y degradación elegante. |
| **III. User Experience Consistency** | ✅ PASS | Estética corporativa de alta densidad inspirada en centros de control de incidentes mayores. Contrastes accesibles WCAG AA, foco visible `#FF7900`. |
| **IV. Performance Requirements** | ✅ PASS | Carga asíncrona no bloqueante de los JSON, renderizado por fragmentos del DOM y auto-refresco ligero por sondeo configurable. |
| **V. Security & Data Integrity** | ✅ PASS | Aislamiento estricto del portal general. Escapado HTML riguroso en cliente contra inyecciones XSS. Normalización monopárrafo antes de persistir. |
| **VI. Documentation & Maintainability** | ✅ PASS | Cobertura documental completa: `spec.md`, `research.md`, `data-model.md`, `quickstart.md`, `contracts/` y `plan.md`. |

---

## Project Structure

### Documentation (this feature)

```text
specs/013-incident-manager-monitor/
├── spec.md              # Especificación funcional de requisitos e historias de usuario
├── checklists/
│   └── requirements.md  # Validación de completitud y criterios de aceptación
├── research.md          # Investigación técnica: arquitectura, rutas y enfoque dual
├── data-model.md        # Esquemas de datos: cola, KPIs, payload de guardado y estados
├── quickstart.md        # Guía rápida de ejecución, flujo operativo y testing
├── contracts/           # Contratos formales de interfaces y restricciones
│   ├── incident-manager-api-contract.md
│   └── monitor-ui-isolation-contract.md
└── plan.md              # Este plan de implementación
```

### Source Code (repository root)

```text
dashboards/
├── incident-manager-monitor/     # [NUEVO] Consola aislada del Incident Manager
│   ├── index.html                # Estructura semántica del cockpit
│   ├── monitor.css               # Estilos de alta densidad, tarjetas y badges
│   └── monitor.js                # Lógica de carga, filtrado, copia de prompts e ingesta
├── assets/                       # Activos compartidos existentes (topbar, resumen-ia)
└── portal/
    └── index.html                # [INTACTO] Portal general: sin enlaces a esta herramienta

serve_app.py                      # Rutas API /api/incident-manager/pending y save-message

converters/
├── cli/
│   ├── update_agent_message.py   # Reutilizado para persistencia y reevaluación
│   └── scan_pending_incidents.py # Referencia de lógica de pendientes
└── tests/
    └── unit/
        └── test_incident_manager_monitor.py # [NUEVO] Tests de API y aislamiento
```

---

## Implementation Roadmap (Phase 2 Breakdown)

### Paso 1: Endpoints de Soporte en `serve_app.py`
1. Implementar `GET /api/incident-manager/pending`:
   - Lee `high_priority_notifications.json` y `agent_executive_messages.json`.
   - Filtra incidencias pendientes (`is_pending`).
   - Calcula métricas `kpis` y devuelve respuesta JSON.
2. Implementar `POST /api/incident-manager/save-message`:
   - Valida el payload (longitud completa $\le$ 90 palabras monopárrafo, breve $\le$ 30 palabras).
   - Invoca `update_agent_store()` y `run_re_evaluation()`.
   - Devuelve confirmación JSON.

### Paso 2: Interfaz Web del Frontal (`dashboards/incident-manager-monitor/`)
1. Crear `dashboards/incident-manager-monitor/index.html`:
   - Cabecera operativa con controles de auto-refresco y conexión.
   - Barra de KPIs (Pendientes, Completadas, Total Activas, P1/P2, Discrepancias).
   - Barra de herramientas con filtros por severidad, proceso y buscador de texto.
   - Contenedor de la cola de incidencias con renderizado dinámico.
2. Crear `dashboards/incident-manager-monitor/monitor.css`:
   - Paleta de diseño institucional Orange con alta legibilidad.
   - Badges de criticidad (SL1 Rojo, SL2 Ámbar, Subescalación).
   - Componentes colapsables de prompts y asistente de ingesta.
3. Crear `dashboards/incident-manager-monitor/monitor.js`:
   - Carga de datos híbrida (API con fallback a fetch estático directo).
   - Selector reactivo de fases (`apertura`, `seguimiento`, `cierre`).
   - Botón de copia al portapapeles con feedback accesible.
   - Validador en tiempo real de conteo de palabras.
   - Integración con modal de Epsilon IA (`window.openResumenIA`).
   - Sincronización automática periódica (30s / 60s).

### Paso 3: Suite de Pruebas Automatizadas
1. Crear `converters/tests/unit/test_incident_manager_monitor.py`:
   - Test de aislamiento: Verifica que `portal/index.html` y `dashboards/index.html` no contengan referencias a `incident-manager-monitor`.
   - Test de endpoint `GET /api/incident-manager/pending`: Verifica estructura y cálculo de KPIs.
   - Test de endpoint `POST /api/incident-manager/save-message`: Verifica validación de palabras ($\le$ 90 y $\le$ 30) y rechazo de sobrelongitud.
   - Test de filtrado en cliente: Comprueba paridad con `scan_pending_incidents.py`.

### Paso 4: Verificación Integral y Despliegue
1. Ejecutar batería completa de tests (`pytest`).
2. Probar manualmente la consola en `http://localhost:8080/dashboards/incident-manager-monitor/`.
3. Actualizar la documentación operativa [`docs/INCIDENT-EXECUTIVE-NOTIFICATIONS-WORKFLOW.md`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/docs/INCIDENT-EXECUTIVE-NOTIFICATIONS-WORKFLOW.md) añadiendo la referencia al monitor para los Incident Managers.
