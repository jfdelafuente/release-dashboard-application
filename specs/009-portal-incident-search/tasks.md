# Tasks: Buscador de Incidencias con Resumen IA en Portal Principal

**Feature**: `009-portal-incident-search` | **Branch**: `009-portal-incident-search`

**Input**: Design documents from `/specs/009-portal-incident-search/`
- Spec: [`specs/009-portal-incident-search/spec.md`](spec.md)
- Implementation Plan: [`specs/009-portal-incident-search/plan.md`](plan.md)
- Research: [`specs/009-portal-incident-search/research.md`](research.md)
- Data Model: [`specs/009-portal-incident-search/data-model.md`](data-model.md)
- Contracts: [`specs/009-portal-incident-search/contracts/`](contracts/)
- Quickstart: [`specs/009-portal-incident-search/quickstart.md`](quickstart.md)

---

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Tarea paralelizable (modifica archivos distintos sin dependencia previa directa)
- **[Story]**: Identificador de historia de usuario (`[US1]`, `[US2]`, `[US3]`)
- Rutas explícitas incluidas en cada descripción de tarea

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Preparación de dependencias frontend y verificación de assets compartidos en el proyecto

- [x] T001 Verificar la disponibilidad de los recursos compartidos [`dashboards/assets/resumen-ia.js`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/dashboards/assets/resumen-ia.js) y [`dashboards/assets/resumen-ia.css`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/dashboards/assets/resumen-ia.css)
- [x] T002 [P] Comprobar el funcionamiento del proxy local de Epsilon en [`serve_app.py`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/serve_app.py) para simulación de respuestas de Resumen IA

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Integración de estilos y dependencias del modal en el portal principal antes de construir los componentes de interacción

**⚠️ CRITICAL**: Ninguna historia de usuario puede funcionar sin enlazar previamente los assets del modal en el portal

- [x] T003 Enlazar la hoja de estilos [`dashboards/assets/resumen-ia.css`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/dashboards/assets/resumen-ia.css) en el `<head>` de [`dashboards/portal/index.html`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/dashboards/portal/index.html)
- [x] T004 Enlazar el script [`dashboards/assets/resumen-ia.js`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/dashboards/assets/resumen-ia.js) con atributo `defer` antes del cierre de `</body>` en [`dashboards/portal/index.html`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/dashboards/portal/index.html)

**Checkpoint**: El singleton global `window.ResumenIAModal` queda disponible en el contexto del portal.

---

## Phase 3: User Story 1 - Consulta Directa de Incidencia desde el Portal Principal (Priority: P1) 🎯 MVP

**Goal**: Permitir al operador introducir un identificador de incidencia en un buscador hero destacado del portal y abrir la pantalla flotante interactiva de Resumen IA mediante botón o pulsación de la tecla `Enter`.

**Independent Test**: Cargar `http://localhost:8000/dashboards/portal/`, escribir `INC000004141215`, pulsar "Consultar" o pulsar `Enter` y verificar que el modal flotante se despliega con el resumen ejecutivo, la causa raíz y las opciones de Remedy/Refresco.

### Implementation for User Story 1

- [x] T005 [P] [US1] Añadir la estructura HTML del bloque hero `<section class="portal-search-hero">` dentro de `<main id="main-content">` en [`dashboards/portal/index.html`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/dashboards/portal/index.html) según el contrato [`specs/009-portal-incident-search/contracts/search-component-contract.md`](contracts/search-component-contract.md)
- [x] T006 [P] [US1] Añadir estilos CSS corporativos de Orange (`#FF7900`) para la tarjeta hero, el formulario de búsqueda, el input y el botón de acción en `<style>` de [`dashboards/portal/index.html`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/dashboards/portal/index.html)
- [x] T007 [US1] Implementar el manejador del evento `submit` en el formulario `#incident-search-form` en [`dashboards/portal/index.html`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/dashboards/portal/index.html) para invocar `window.ResumenIAModal.open(code)`
- [x] T008 [US1] Asegurar soporte nativo de navegación y confirmación por teclado (tecla `Enter` para enviar formulario y tecla `Escape` para cerrar el modal) en [`dashboards/portal/index.html`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/dashboards/portal/index.html)

**Checkpoint**: User Story 1 (MVP) completamente operativa: el usuario ya puede buscar y visualizar incidencias desde el portal.

---

## Phase 4: User Story 2 - Normalización y Tolerancia en el Formato de Entrada (Priority: P2)

**Goal**: Aceptar códigos con espacios superfluos, en minúsculas, o códigos puramente numéricos (ej. `4141215`) auto-completando automáticamente el formato estándar `INC000004141215`.

**Independent Test**: Introducir `  inc000004141215  ` o `4141215` y verificar que el sistema abre el modal consultando el identificador canónico `INC000004141215`.

### Implementation for User Story 2

- [x] T009 [US2] Implementar la función de normalización pura `sanitizeIncidentCode(input)` en [`dashboards/portal/index.html`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/dashboards/portal/index.html) siguiendo las reglas definidas en [`specs/009-portal-incident-search/research.md`](research.md)
- [x] T010 [US2] Integrar la normalización en el flujo de envío de `#incident-search-form` antes de la llamada a `window.ResumenIAModal.open()` en [`dashboards/portal/index.html`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/dashboards/portal/index.html)
- [x] T011 [P] [US2] Crear un script de pruebas unitarias/verificación de normalización en [`tests/test_sanitize_incident_code.js`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/tests/test_sanitize_incident_code.js) para verificar todas las casuísticas de entrada (numéricas, con espacios, minúsculas y caracteres especiales)

**Checkpoint**: User Stories 1 y 2 plenamente operativas y robustas ante errores tipográficos comunes.

---

## Phase 5: User Story 3 - Validación Local Accesible y Prevención de Errores (Priority: P3)

**Goal**: Validar en 0 ms si el campo de búsqueda se encuentra vacío al intentar consultar, impidiendo envíos innecesarios, proporcionando aviso visual accesible y devolviendo el foco al input.

**Independent Test**: Con el campo vacío, hacer clic en "Consultar" o pulsar `Enter` y verificar que no se realiza petición de red, el campo muestra borde de alerta accesible y el cursor permanece enfocado en el campo.

### Implementation for User Story 3

- [x] T012 [US3] Implementar la comprobación de campo vacío en el envío de `#incident-search-form` en [`dashboards/portal/index.html`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/dashboards/portal/index.html) previniendo el envío si `!sanitizedCode`
- [x] T013 [US3] Añadir clases de error `.is-invalid` y mensaje de alerta accesible `#search-error` con `role="alert"` y `aria-live="polite"` en [`dashboards/portal/index.html`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/dashboards/portal/index.html)
- [x] T014 [US3] Añadir listener de evento `input` en `#incident-search-input` para limpiar automáticamente el estado de error en cuanto el usuario vuelve a escribir en [`dashboards/portal/index.html`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/dashboards/portal/index.html)

**Checkpoint**: Validación local accesible y sin recargas de página completada.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Perfeccionamiento de la interfaz, responsive design, validación completa del flujo y documentación final

- [x] T015 [P] Validar el diseño responsive del bloque hero en resoluciones móviles (<768px), tablet y escritorio en [`dashboards/portal/index.html`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/dashboards/portal/index.html)
- [x] T016 Ejecutar todas las pruebas descritas en [`specs/009-portal-incident-search/quickstart.md`](quickstart.md) sobre `http://localhost:8000/dashboards/portal/`
- [x] T017 [P] Actualizar la documentación de dashboards en [`dashboards/README.md`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/dashboards/README.md) reflejando la nueva funcionalidad de búsqueda directa desde el portal

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1: Setup ────► Phase 2: Foundational ────► Phase 3: User Story 1 (MVP)
                                                           │
                                                           ▼
                                                 Phase 4: User Story 2 (P2)
                                                           │
                                                           ▼
                                                 Phase 5: User Story 3 (P3)
                                                           │
                                                           ▼
                                                 Phase 6: Polish & Quickstart
```

### Parallel Opportunities

- **T001 y T002**: Pueden ejecutarse en paralelo.
- **T005 (HTML) y T006 (CSS)**: Pueden diseñarse de manera coordinada o paralela en `dashboards/portal/index.html`.
- **T011 (Test de normalización)**: Puede redactarse en paralelo a la implementación de `sanitizeIncidentCode`.
- **T015 y T017**: Pueden abordarse en paralelo una vez finalizada la integración funcional.

---

## Implementation Strategy (MVP First)

1. **Incremento 1 (MVP)**: Completar Fases 1 a 3. El portal ya permite buscar incidencias con código exacto y ver el modal de Resumen IA.
2. **Incremento 2**: Completar Fase 4 (Normalización inteligente y tolerancia a formatos abreviados o numéricos).
3. **Incremento 3**: Completar Fase 5 (Validación local accesible sin peticiones erróneas).
4. **Incremento 4**: Completar Fase 6 (Responsive polish, ejecución de quickstart y actualización de documentación).

