# Implementation Plan: Sistema de Notificaciones de Incidencias de Alta Prioridad

**Branch**: `production` | **Date**: 2026-10-26 | **Spec**: [`specs/012-high-priority-incident-notifications/spec.md`](./spec.md)

**Input**: Feature specification from [`specs/012-high-priority-incident-notifications/spec.md`](./spec.md)

---

## Summary

El sistema escanea de manera automatizada las incidencias masivas registradas en el dashboard (`dashboards/massive-incidents/`), consulta la API de Epsilon (`/api/epsilon/resumenIA/{codigo}`) para obtener el diagnóstico y resumen sintético generado por IA, y evalúa la severidad real de cada incidencia utilizando la matriz ITIL/SRE de la skill `it-severity-matrix` (cruce de impacto en el negocio y urgencia operativa). 

Cuando una incidencia resulta clasificada como **P1 (Crítica)** o **P2 (Alta)**, o cuando se detecta una **discrepancia de prioridad** respecto al ticket original, el sistema:
1. Registra la alerta en un catálogo estructurado (`data/output/high_priority_notifications.json`).
2. Genera automáticamente propuestas de mensajes ejecutivos para Dirección según las directrices del agente `incident-reporter` (fases *Apertura*, *Seguimiento*, *Cierre* con versiones completa $\le$ 90 palabras y breve $\le$ 30 palabras).
3. Despliega en la interfaz de `dashboards/massive-incidents/` un **Centro de Notificaciones** integrado (icono de campana con contador dinámico, drawer lateral desplegable, KPIs de impacto, filtrado por criticidad/discrepancia, copia de mensajes ejecutivos en 1 clic y persistencia del estado operativo en `localStorage`).

---

## Technical Context

**Language/Version**: 
- Backend/CLI: Python 3.10+ (compatible con Python 3.9+ en servidor Rocky Linux 9).
- Frontend: Vanilla JavaScript (ES6+) y HTML5/CSS3 nativo.

**Primary Dependencies**:
- Backend: Librerías estándar de Python (`json`, `urllib`, `argparse`, `pathlib`, `re`, `datetime`). Para testing: `pytest`, `requests`.
- Frontend: Sin frameworks pesados; utiliza los componentes y estilos ya existentes (`dashboards/assets/resumen-ia.js`, `dashboards/assets/styles/design-tokens.css`).

**Storage**:
- Catálogo de alertas: `data/output/high_priority_notifications.json`.
- Caché de respuestas Epsilon: `data/.epsilon_cache/` y proxy en memoria en `serve_app.py`.
- Estado de lectura y gestión por usuario: `localStorage` del navegador bajo la clave `hp_incident_notifications_state_v1`.

**Testing**:
- Pruebas unitarias y de contrato ejecutadas con `pytest` en `converters/tests/unit/test_evaluate_incident_notifications.py`.
- Cobertura de inferencia ITIL, conteo estricto de palabras, detección de discrepancias y degradación elegante si Epsilon está offline.

**Target Platform**:
- Entorno de desarrollo local: Windows 10/11 con `serve_app.py` (puerto 8081).
- Entorno de producción: Rocky Linux 9 (`10.132.26.96`) servido por Nginx y backend en puerto 8081.

**Project Type**:
- CLI Processor (`converters/cli/`) + Web Dashboard UI (`dashboards/massive-incidents/`).

**Performance Goals**:
- Ejecución CLI: Escaneo y evaluación de 50 incidencias en menos de 15 segundos (utilizando caché local y concurrencia moderada).
- Frontend: Apertura del drawer lateral de notificaciones en menos de 100 ms; filtrado de tarjetas en menos de 30 ms.
- Sobrecarga de memoria en navegador: Menor a 5 MB adicionales.

**Constraints**:
- **Identidad de Marca**: Uso riguroso de tokens de Orange (`#FF7900`), tipografía Helvetica Neue / Arial, sin referencias erróneas de marca.
- **Límites de Palabras**: Restricción estricta de longitud en mensajes ejecutivos ($\le$ 90 palabras en versión completa monopárrafo, $\le$ 30 palabras en versión breve).
- **Guardrail Anti-Alucinación**: No inventar horas, IPs, ni volúmenes de clientes ficticios; ceñirse estrictamente a los hechos registrados en el ticket y en Epsilon.
- **Tolerancia a Fallos**: Si Epsilon no está disponible o no tiene resumen para un ticket, el evaluador debe funcionar sin bloquearse usando los metadatos del ticket original.

**Scale/Scope**:
- 1 dashboard principal (`dashboards/massive-incidents/`).
- Catálogos de incidencias masivas de 30 a 200 tickets por lote.
- 1 script CLI de evaluación y generación.
- 1 módulo frontend reutilizable (`dashboards/assets/incident-notifications.js` y `.css`).

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Estado | Justificación y Cumplimiento |
| :--- | :--- | :--- |
| **I. Code Quality** | ✅ PASS | Separación estricta de responsabilidades: funciones atómicas para inferencia ITIL, conteo de palabras, consulta a API y renderizado UI. Complejidad ciclomática $< 10$. Naming consistente (camelCase en JS, snake_case en Python). |
| **II. Testing Standards** | ✅ PASS | Suite de tests con `pytest` que verifica casos felices y de borde: prioridad P1..P4, textos largos que requieren condensación, tickets sin resumen de Epsilon y formato JSON Schema. Nombres de test con convención `should_[action]_when_[condition]`. |
| **III. User Experience Consistency** | ✅ PASS | Paleta de colores Orange (`#FF7900`), drawer con navegación accesible (Escape para cerrar, foco accesible), botones con retroalimentación táctil de copiado y badges de estado acordes a la guía de estilo. Terminología en español ("Estatus", "Grupo asignado", "Prioridad"). |
| **IV. Performance Requirements** | ✅ PASS | Carga asíncrona no bloqueante del catálogo de notificaciones (`fetch` diferido), almacenamiento en caché de peticiones Epsilon y renderizado eficiente en el DOM. |
| **V. Security & Data Integrity** | ✅ PASS | Sanitización de cadenas antes de renderizar para prevenir XSS. URLs a Remedy e informes siempre bajo HTTPS. Validación de esquemas JSON antes de persistir. |
| **VI. Documentation & Maintainability** | ✅ PASS | Documentación completa: especificación (`spec.md`), investigación (`research.md`), modelo de datos (`data-model.md`), contratos de interfaz (`contracts/`), guía rápida (`quickstart.md`) y plan (`plan.md`). |

---

## Project Structure

### Documentation (this feature)

```text
specs/012-high-priority-incident-notifications/
├── spec.md              # Especificación funcional de requisitos e historias de usuario
├── checklists/
│   └── requirements.md  # Validación de completitud y criterios de aceptación
├── research.md          # Investigación técnica: arquitectura, proxy Epsilon, reglas ITIL
├── data-model.md        # Esquemas de datos: catálogo, evaluación y estado de usuario
├── quickstart.md        # Guía rápida para desarrolladores y operadores
├── contracts/           # Contratos formales de interfaces y esquemas JSON
│   ├── high-priority-notifications-contract.md
│   ├── severity-evaluation-contract.md
│   └── executive-notification-contract.md
└── plan.md              # Este plan de implementación
```

### Source Code (repository root)

```text
converters/
├── cli/
│   ├── evaluate_incident_notifications.py   # CLI evaluador y generador de notificaciones
│   └── upload_csv.py                        # (Existente) Conversor y uploader de incidencias
└── tests/
    └── unit/
        ├── test_evaluate_incident_notifications.py  # Tests unitarios del evaluador y generador
        └── test_upload_csv.py                       # Tests existentes

dashboards/
├── assets/
│   ├── incident-notifications.js    # Componente UI: campana, drawer, filtrado, portapapeles
│   ├── incident-notifications.css   # Estilos del Centro de Notificaciones (Tokens Orange)
│   ├── resumen-ia.js                # (Existente) Modal y cliente de Epsilon Resumen IA
│   └── styles/
│       └── design-tokens.css        # (Existente) Tokens CSS corporativos
└── massive-incidents/
    ├── index.html                   # Inclusión del componente de notificaciones y campana
    └── app.js                       # Coordinación del dashboard masivo con notificaciones

data/
├── output/
│   ├── high_priority_notifications.json     # Catálogo generado de alertas de alta prioridad
│   └── index.json                           # Registro índice de ficheros de datos
└── .epsilon_cache/                          # Caché local opcional de respuestas Epsilon
```

**Structure Decision**: Se mantiene la arquitectura desacoplada existente en el repositorio:
1. Un componente CLI Python en `converters/cli/` para la ingesta, consulta a Epsilon y evaluación ITIL, aprovechando los datos procesados por los convertidores existentes.
2. Un componente web modular en `dashboards/assets/` reutilizable que expone el Centro de Notificaciones en `dashboards/massive-incidents/index.html` sin sobrecargar la lógica de visualización del dashboard principal.

---

## Complexity Tracking

> **Constitution Check: No violations detected.** La solución no introduce abstracciones innecesarias ni dependencias externas pesadas.

---

## Implementation Phases & Milestones

### Fase 0: Investigación y Validación de Viabilidad (Completada)
- [x] Análisis del endpoint y formato de datos de Epsilon Resumen IA.
- [x] Estudio de la matriz ITIL de severidad (`it-severity-matrix`) y del agente de comunicación (`incident-reporter`).
- [x] Definición de estrategias de caché y mitigación de latencia.
- [x] Creación de `specs/012-high-priority-incident-notifications/research.md`.

### Fase 1: Diseño y Contratos Formales (Completada)
- [x] Modelado de datos de catálogo y estado de lectura (`data-model.md`).
- [x] Contrato JSON Schema del catálogo (`contracts/high-priority-notifications-contract.md`).
- [x] Contrato de reglas de inferencia ITIL (`contracts/severity-evaluation-contract.md`).
- [x] Contrato de mensajes ejecutivos y guardrails de palabras (`contracts/executive-notification-contract.md`).
- [x] Guía rápida de ejecución y testing (`quickstart.md`).

### Fase 2: Implementación Técnica (Tareas a desglosar en `/speckit-tasks`)
- [ ] **Módulo Backend/CLI**:
  - Implementar cliente HTTP con caché para Epsilon (`EpsilonClient`).
  - Implementar motor de inferencia de matriz de severidad ITIL (`SeverityEvaluator`).
  - Implementar generador de mensajes ejecutivos monopárrafo con conteo de palabras (`ExecutiveMessageGenerator`).
  - Implementar CLI principal `evaluate_incident_notifications.py` con argumentos de control y persistencia a JSON.
- [ ] **Módulo de Pruebas Unitarias**:
  - Implementar `test_evaluate_incident_notifications.py` cubriendo P1..P4, discrepancias, guardrails de longitud y tolerancia a desconexión.
- [ ] **Módulo Frontend (Centro de Notificaciones)**:
  - Crear `dashboards/assets/incident-notifications.css` con estética Orange y drawer accesible.
  - Crear `dashboards/assets/incident-notifications.js` con lógica de campana, renderizado de tarjetas, copiado al portapapeles y persistencia en `localStorage`.
  - Integrar la campana y los scripts en `dashboards/massive-incidents/index.html`.
- [ ] **Verificación y Despliegue**:
  - Validar flujo end-to-end con datos reales y en `serve_app.py`.
  - Integrar el paso de evaluación en el ciclo de actualización o despliegue (`scripts/deploy-production.ps1`).
