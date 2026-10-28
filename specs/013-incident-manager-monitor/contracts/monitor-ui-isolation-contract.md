# Contract: Monitor UI & Isolation Constraints

**Feature**: `013-incident-manager-monitor` | **Date**: 2026-10-28  
**Spec Reference**: [`specs/013-incident-manager-monitor/spec.md`](../spec.md)

Este documento especifica los requisitos de aislamiento visual y el contrato de interfaz de usuario para el Frontal de Monitorización del Incident Manager.

---

## 1. Regla de Aislamiento Estricto (Portal General)

| Archivo / Ruta Pública | Condición Obligatoria | Mecanismo de Verificación |
| :--- | :--- | :--- |
| `dashboards/portal/index.html` | **PROHIBIDO** incluir enlaces, tarjetas, botones o scripts que referencien `incident-manager-monitor`. | Test unitario / estático que analiza el contenido HTML y falla si contiene `incident-manager-monitor`. |
| `dashboards/index.html` | **PROHIBIDO** redirigir o enlazar a `incident-manager-monitor`. | Inspección estática del fichero. |
| `dashboards/incident-manager-monitor/index.html` | Punto de entrada único del frontal de monitorización. | Carga autónoma con status HTTP 200. |

---

## 2. Contrato de Componentes UI y Accesibilidad

### 2.1. Cabecera Operativa (`.im-header`)
- **Identidad**: Título *"Monitor de Incidencias de Alta Prioridad - Incident Manager"* con subtítulo *"Vigilancia de redacciones de agente pendientes"*.
- **Controles**:
  - Selector de auto-refresco (`Auto-refresco: Desactivado | 30s | 60s`).
  - Botón de refresco manual (`Refrescar ahora`).
  - Indicador de estado de conexión (`🟢 Conectado` / `🟡 Sincronizando` / `🔴 Sin conexión`).

### 2.2. Barra de KPIs (`.im-kpi-bar`)
- Tarjeta 1: **Pendientes de Redacción** (Contador numérico. Estilo crítico rojo/pulsante si $> 0$, verde si $= 0$).
- Tarjeta 2: **Completadas con Agente** (Contador verde).
- Tarjeta 3: **Total Activas Alta Prioridad** (Contador neutral).
- Tarjeta 4: **Críticas P1 / Altas P2** (Desglose bicolor).
- Tarjeta 5: **Discrepancias (Subescalación)** (Contador ámbar de alerta).

### 2.3. Tarjeta de Incidencia Pendiente (`.incident-card`)
- **Cabecera**:
  - Badge de Prioridad: `.badge-p1` (Rojo `#D32F2F`) o `.badge-p2` (Ámbar `#E65100`).
  - Badge de Discrepancia: `⚠️ Subescalación (Ticket: {nominal} → Sugerida: {sugerida})`.
  - ID de Incidencia con enlace seguro a Remedy.
  - Estatus operativo del ticket y tiempo transcurrido desde el envío.
- **Cuerpo Contextual**:
  - Título y sistemas afectados.
  - Bloque de Proceso Crítico (`Atención al Cliente`, `Facturación`, etc.) y Criterio ITIL aplicado.
  - Indicador de Epsilon IA con botón "Ver Resumen IA" que dispara `window.openResumenIA(id)`.
- **Panel de Agente**:
  - Pestañas de Fase (`Apertura` [activa por defecto], `Seguimiento`, `Cierre`).
  - Caja de código de solo lectura con el prompt para `incident-reporter`.
  - Botón `Copiar Prompt para el Agente` con feedback accesible `aria-live="polite"`.
  - Asistente de Ingesta colapsable/expandible con contadores de palabras dinámicos ($\le$ 90 / $\le$ 30) y botones `Guardar en Almacén` y `Copiar Comando CLI`.

---

## 3. Contrato de Interacción y Accesibilidad (WCAG 2.1 AA)

- **Navegación por teclado**: Todo control interactivo (pestañas, botones, campos de texto) es accesible con `Tab` / `Shift+Tab` y activable con `Enter` / `Space`.
- **Foco visible**: Anillo de foco de 3px en naranja corporativo (`#FF7900`) con `outline-offset: 2px`.
- **Anuncios para lectores de pantalla**:
  - Al copiar un prompt: mensaje en contenedor con `role="status"` y `aria-live="polite"` ("Prompt de apertura copiado al portapapeles").
  - Al validar palabras: mensaje accesible si se excede el límite.

