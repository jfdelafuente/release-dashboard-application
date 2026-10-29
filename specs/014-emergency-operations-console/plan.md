# Implementation Plan: Consola Operativa de Emergencias Orange en Tiempo Real (014-emergency-operations-console)

**Branch**: `production` | **Date**: 2026-10-29 | **Spec**: [`specs/014-emergency-operations-console/spec.md`](./spec.md)

**Input**: Feature specification from [`specs/014-emergency-operations-console/spec.md`](./spec.md)

---

## Summary

Esta funcionalidad evoluciona y amplía el frontal `incident-manager-monitor` existente (`dashboards/incident-manager-monitor/`) transformándolo en una **Consola Operativa de Emergencias IT de Orange en Tiempo Real**, totalmente alineada con la skill corporativa **`orange-it-emergency-management`** y la matriz **`it-severity-matrix`**.

La consola incorpora:
1. **Detección de Discrepancias con Métricas Cuantitativas Exactas**: Supera la etiqueta genérica de subescalación mostrando el Proceso Crítico vulnerado (de entre los 6 procesos: ATC, Ventas, Portabilidad, Prepago, Provisión, Facturación y Cobros) y la métrica de umbral exacta superada.
2. **Motor de Cronometraje en Tiempo Real y Alertas de Escalado Telefónico**: Monitorea de forma continua el tiempo transcurrido desde la apertura (`fecha_apertura`), disparando alertas visuales y operativas en los hitos de **45 minutos** (1er escalado a proveedores N2/N3) y **+1 hora adicional (105 min)** (2º escalado a estamentos superiores), recordando la **Regla de Oro** de obligatoriedad del canal telefónico en SL1.
3. **Gobernanza de Workarounds y Bloqueo de Desescaladas Indebidas**: Identifica parches y contenciones provisionales, audita su estatus de autorización por Customer & Service Ops (IM-CSO) y bloquea físicamente en la interfaz cualquier intento de desescalada o cierre prematuro mientras el impacto persista.
4. **Reporte de Emergencia Normalizado en 4 Bloques y Matriz RACI**: Visualizador monospaced interactivo y botón de copia en 1 clic del informe oficial estructurado en 4 bloques ([1] Clasificación, [2] Comunicaciones/SLAs, [3] Plan de Acción/Workaround, [4] Escalado Telefónico), con panel de referencia RACI y acceso a matrices de guardia (GRIAL / Confluence).

---

## Technical Context

**Language/Version**:
- Backend / CLI: Python 3.10+ (compatible con Python 3.9+ en Rocky Linux 9).
- Frontend: Vanilla JavaScript (ES6+), HTML5 semántico y CSS3 nativo sin frameworks externos.

**Primary Dependencies**:
- Backend: Standard library (`json`, `urllib`, `pathlib`, `http.server`, `re`, `datetime`). Testing con `pytest`.
- Frontend: Estilos institucionales compartidos (`topbar.css`, `shared.css`, `resumen-ia.css`, `resumen-ia.js`) y módulos específicos de la consola (`monitor.css`, `monitor.js`).

**Storage**:
- Catálogo de alertas activas evaluadas: `data/output/high_priority_notifications.json`.
- Almacén de redacciones de agente: `data/agent_executive_messages.json`.
- Interfaz web: `dashboards/incident-manager-monitor/`.

**Testing**:
- Pruebas unitarias de parsing temporal, alertas de 45m/+1h y gobernanza de workarounds en `converters/tests/unit/test_incident_manager_monitor.py`.
- Pruebas de contrato y verificación de aislamiento respecto al portal público general.

**Target Platform**:
- Servidor de desarrollo local: Windows con `serve_app.py` (puerto 8080).
- Servidor de producción: Rocky Linux 9 con Nginx.

**Project Type**:
- Frontend Web Cockpit (`dashboards/incident-manager-monitor/`) + API extensions en `serve_app.py`.

**Performance Goals**:
- Precisión de cronómetros en cliente: actualización cada 10 segundos con $\pm 1\text{ s}$ de precisión.
- Carga y renderizado inicial: $< 400\text{ ms}$.
- Filtrado y despliegue del reporte de emergencia: $< 20\text{ ms}$.

**Constraints**:
- **Aislamiento**: 0 enlaces en `dashboards/portal/index.html` ni `dashboards/index.html`.
- **Regla de Oro**: Ninguna desescalada permitida si existe un workaround activo sin autorización de IM-CSO o sin erradicación total del impacto.
- **Canal Telefónico**: Indicación explícita de vía telefónica en incidencias SL1.

---

## Constitution Check

*GATE: Evaluado y verificado conforme a la Constitución del proyecto.*

| Principio | Estado | Justificación y Cumplimiento |
| :--- | :---: | :--- |
| **I. Code Quality** | ✅ PASS | Funciones modulares para el cálculo de cronómetros, renderizado de discrepancias y gobernanza de workarounds. Naming camelCase consistente. |
| **II. Testing Standards** | ✅ PASS | Cobertura de tests unitarios que validan cálculo de minutos, activación de alertas a los 45 min y 105 min, y bloqueo de desescalada. |
| **III. User Experience Consistency** | ✅ PASS | Estética de alta densidad corporativa Orange (`#FF7900`), badges de severidad consistentes (SL1 Rojo, SL2 Ámbar), candado de bloqueo visual accesible. |
| **IV. Performance Requirements** | ✅ PASS | Cronómetros calculados en cliente vía `Date.now() - timestamp` sin sobrecargar el backend con polling de alta frecuencia. |
| **V. Security & Data Integrity** | ✅ PASS | Aislamiento estricto del portal público general. Sanitización y escapado contra XSS en todos los textos de tickets. |
| **VI. Documentation & Maintainability** | ✅ PASS | Cobertura documental completa: `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md` y `plan.md`. |

---

## Project Structure

### Documentation (this feature)

```text
specs/014-emergency-operations-console/
├── spec.md              # Especificación funcional de requisitos e historias de usuario
├── checklists/
│   └── requirements.md  # Validación de completitud y criterios de aceptación
├── research.md          # Investigación técnica: cronómetros, discrepancias, gobernanza
├── data-model.md        # Esquemas de datos: EmergencyIncident, Timeline, Workaround
├── contracts/           # Contratos de interfaz y gobernanza
│   ├── emergency-console-api-contract.md
│   └── workaround-governance-contract.md
├── quickstart.md        # Guía rápida de ejecución y verificación
└── plan.md              # Este plan de implementación
```

### Source Code (repository root)

```text
dashboards/
├── incident-manager-monitor/     # Consola Operativa de Emergencias Orange
│   ├── index.html                # Estructura semántica con módulos de emergencia, RACI y cronómetros
│   ├── monitor.css               # Estilos de alta densidad, alertas de 45m, candado de bloqueo
│   └── monitor.js                # Motor de tiempo real, lógica de discrepancias cuantitativas y gobernanza
├── assets/                       # Componentes compartidos existentes (topbar, shared, resumen-ia)
└── portal/
    └── index.html                # [INTACTO] Portal público general (aislamiento estricto)

serve_app.py                      # Extensiones API /api/incident-manager/emergency-cockpit y pending

converters/
└── tests/
    └── unit/
        └── test_incident_manager_monitor.py # Pruebas unitarias de emergencias, SLAs y aislamiento
```

---

## Implementation Roadmap

### Paso 1: Extensiones Backend en `serve_app.py`
1. Enriquecer `GET /api/incident-manager/pending` y crear `GET /api/incident-manager/emergency-cockpit` conforme a [`contracts/emergency-console-api-contract.md`](./contracts/emergency-console-api-contract.md).
2. Proveer timestamps normalizados (`apertura_epoch_ms`), métricas cuantitativas de proceso crítico, evaluación de escalado telefónico a 45 min y texto formateado del reporte de emergencia.

### Paso 2: Motor de Cronometraje y Alertas en `dashboards/incident-manager-monitor/`
1. Implementar el motor de tiempo real en `monitor.js`:
   - Parseo resiliente de `fecha_apertura` a epoch.
   - Intervalo cada 10 segundos para actualizar tiempos transcurridos en pantalla (`Math.floor((Date.now() - epoch) / 60000)`).
   - Detección de hitos: `< 20m` (1ª notif), `45m` (1er escalado telefónico N2/N3), `105m` (2º escalado estamentos superiores).
2. Renderizar badges de tiempo reactivos con estilos diferenciados en `monitor.css`.

### Paso 3: Visualizador de Discrepancias con Métricas Exactas
1. Implementar en `monitor.js` y `index.html` el componente de contraste de discrepancia:
   - Tabla comparativa: *Remedy (Media/Baja)* vs *Orange ITIL (SL1/SL2)*.
   - Detalle del Proceso Crítico (de los 6 procesos corporativos) y umbral numérico exacto superado.

### Paso 4: Gobernanza de Workarounds y Bloqueo de Desescaladas
1. Implementar en `monitor.js` el control de gobernanza conforme a [`contracts/workaround-governance-contract.md`](./contracts/workaround-governance-contract.md):
   - Identificación de workarounds activos y estatus de autorización por IM-CSO.
   - Bloqueo en UI de desescalada o cierre prematuro mediante banner con icono de candado y Regla de Oro institucional.

### Paso 5: Reporte de Emergencia en 4 Bloques y Panel RACI
1. Integrar el visualizador monospaced del Reporte de Emergencia normalizado de 4 bloques en cada tarjeta con botón de copia rápida en 1 clic al portapapeles.
2. Añadir en la cabecera operativa el modal/drawer de gobernanza RACI (IM como Responsable, IM-CSO como Aprobador) y enlaces a matrices de guardia (GRIAL / Confluence).

### Paso 6: Pruebas Automatizadas y Verificación
1. Ampliar `converters/tests/unit/test_incident_manager_monitor.py` para cubrir:
   - Contrato del nuevo endpoint de emergencias.
   - Reglas de bloqueo de desescalada por workarounds.
   - Preservación del aislamiento del portal general.
2. Ejecutar la suite completa y validar en navegador.
