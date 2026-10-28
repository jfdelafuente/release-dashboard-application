# Phase 0 Research: Frontal Web de Monitorización para Incident Manager (013-incident-manager-monitor)

**Feature**: `013-incident-manager-monitor` | **Date**: 2026-10-28  
**Status**: Completed  
**Spec Reference**: [`specs/013-incident-manager-monitor/spec.md`](./spec.md)

---

## 1. Objetivos de Investigación

El propósito de esta fase de investigación técnica es determinar la arquitectura óptima, las decisiones técnicas y los mecanismos de integración para el Frontal Web de Monitorización del Incident Manager, garantizando el cumplimiento de los dos requisitos clave:
1. **Aislamiento estricto**: La herramienta es una consola técnica interna para Incident Managers y **no debe aparecer ni enlazarse en el portal general** (`dashboards/portal/index.html` ni `dashboards/index.html`).
2. **Reutilización del ecosistema**: Debe apoyarse directamente en las herramientas desarrolladas en el proyecto (`data/output/high_priority_notifications.json`, `data/agent_executive_messages.json`, `scan_pending_incidents.py`, `update_agent_message.py`, `serve_app.py`, y estilos/componentes compartidos).

---

## 2. Decisiones de Arquitectura y Diseño

### Decisión 1: Ubicación Física y Enrutamiento del Frontal

* **Problema**: Dónde alojar la aplicación y cómo garantizar que quede fuera del portal general sin romper la infraestructura de servidores existente.
* **Opciones evaluadas**:
  1. *Subdirectorio bajo `dashboards/incident-manager-monitor/index.html`*: Se sirve automáticamente mediante la ruta existente de dashboards en `serve_app.py` y Nginx (`/dashboards/incident-manager-monitor/`).
  2. *Nueva carpeta `tools/incident-manager-monitor/index.html`*: Requiere reconfigurar reglas específicas de Nginx en producción y rutas en `serve_app.py`.
* **Decisión seleccionada**: **Opción 1 (`dashboards/incident-manager-monitor/index.html`)**.
* **Justificación**:
  - `serve_app.py` y Nginx ya mapean `/dashboards/*` hacia la carpeta física `dashboards/`.
  - El aislamiento del portal general no depende de la ruta del archivo, sino de **no incluir ninguna tarjeta ni enlace** en `dashboards/portal/index.html` ni `dashboards/index.html`.
  - El Incident Manager accederá directamente por URL o desde la documentación operativa de guardia ([`docs/INCIDENT-EXECUTIVE-NOTIFICATIONS-WORKFLOW.md`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/docs/INCIDENT-EXECUTIVE-NOTIFICATIONS-WORKFLOW.md)).

---

### Decisión 2: Estrategia de Ingesta y Consulta de Datos en el Cliente

* **Problema**: Cómo obtiene el frontal web la lista de incidencias pendientes y sus metadatos sin sobrecargar el servidor y garantizando que coincida con `scan_pending_incidents.py`.
* **Análisis de fuentes**:
  - `data/output/high_priority_notifications.json` ya contiene el catálogo completo de incidencias activas de alta prioridad evaluadas, con:
    - Metadatos de ticket (ID, título, sistemas, fecha de envío, estatus).
    - Inferencia de severidad (prioridad sugerida, prioridad original, discrepancia).
    - Proceso de negocio y criterio/umbral de la matriz.
    - Justificación de impacto y urgencia.
    - Síntesis de Epsilon IA o indicación de sólo metadatos Remedy.
    - Mensajes ejecutivos para las 3 fases (`apertura`, `seguimiento`, `cierre`) con `generado_por_agente`, `estado` y el `prompt_agente` precalculado.
  - `data/agent_executive_messages.json` almacena las redacciones oficiales aprobadas.
* **Decisión seleccionada**: **Carga Híbrida en Cliente con API Opcional de Backend**.
  - **Capa 1 (Cliente Estático Ultra-Rápido)**: La página web realiza un `fetch('/data/output/high_priority_notifications.json')` y un `fetch('/data/agent_executive_messages.json')`. La función en JS `isIncidentPending(inc, agentStore)` replica con exactitud milimétrica la lógica de `scan_pending_incidents.py`:
    ```javascript
    function isIncidentPending(inc, agentStore) {
        const incId = inc.id;
        const apertura = (inc.mensajes_ejecutivos && inc.mensajes_ejecutivos.apertura) || {};
        const inStore = agentStore && agentStore[incId] && Boolean(agentStore[incId].apertura && agentStore[incId].apertura.completo);
        return apertura.estado === 'pendiente' || !apertura.completo || !inStore;
    }
    ```
  - **Capa 2 (Endpoint de Conveniencia en `serve_app.py`)**: Para entornos dinámicos, se expone `/api/incident-manager/pending` que ejecuta este mismo filtrado en el backend y devuelve JSON pre-procesado, reduciendo la lógica en clientes móviles.

---

### Decisión 3: Asistente de Ingesta y Persistencia de Redacciones

* **Problema**: El Incident Manager necesita enviar o persistir la redacción generada por el agente de forma rápida y sin errores.
* **Opciones evaluadas**:
  1. *Solo copia de comando CLI*: El usuario copia el comando `python converters/cli/update_agent_message.py ...` y lo ejecuta en su terminal. (Muy seguro, pero requiere tener terminal abierta).
  2. *Solo formulario web con API HTTP*: Guarda mediante `POST` directamente desde el navegador. (Muy cómodo, pero si el servidor no tiene endpoint de escritura habilitado falla).
  3. *Enfoque Dual (API HTTP directa + Generador de Comando CLI como contingencia)*: La UI ofrece el botón "Guardar en Almacén Oficial" (hace POST a `/api/incident-manager/save-message`) y simultáneamente el botón "Copiar Comando CLI" con el comando pre-rellenado.
* **Decisión seleccionada**: **Opción 3 (Enfoque Dual)**.
* **Justificación**:
  - Proporciona la mejor experiencia de usuario para el Incident Manager en el navegador.
  - Si por restricciones de red o permisos el guardado HTTP no estuviera disponible, el operador tiene en un clic el comando CLI exacto de contingencia sin perder los datos redactados.
  - La API de `serve_app.py` llamará a la función `update_agent_store` de `converters/cli/update_agent_message.py` y a `run_re_evaluation()`, manteniendo exactamente el mismo comportamiento probado y validado.

---

### Decisión 4: Validación de Longitud y Monopárrafo en Tiempo Real

* **Problema**: Asegurar que las comunicaciones ejecutivas respeten las reglas de `incident-reporter` ($\le$ 90 palabras monopárrafo para versión completa; $\le$ 30 palabras para versión breve).
* **Solución**:
  - Implementación en cliente de un contador de palabras reactivo (`input` event):
    ```javascript
    function countWords(str) {
        return (str || '').trim().split(/\s+/).filter(Boolean).length;
    }
    ```
  - Indicador visual dinámico:
    - Verde: Dentro del límite ($1..90$ palabras para versión completa; $1..30$ palabras para versión breve).
    - Rojo: Excede el límite ($>90$ o $>30$ palabras) con advertencia visible de recorte.
  - Normalización automática al guardar: reemplaza saltos de línea y dobles espacios por un espacio único en la versión completa para garantizar que sea un único párrafo cohesionado.

---

### Decisión 5: Reutilización de Componentes de Estilo y Epsilon IA

* **Problema**: Mantener coherencia estética institucional con la plataforma Orange y permitir inspeccionar Epsilon IA.
* **Solución**:
  - Carga de tokens y estilos corporativos existentes:
    - `/dashboards/assets/topbar.css` (para la cabecera operativa).
    - `/dashboards/assets/resumen-ia.css` y `/dashboards/assets/resumen-ia.js` (para abrir el modal de Epsilon con `window.openResumenIA(id)`).
  - Hoja de estilos específica de alta densidad: `dashboards/incident-manager-monitor/monitor.css` con estética ejecutiva limpia (tarjetas tipo cockpit, badges de severidad SL1 rojo y SL2 ámbar, contadores numéricos y contrastes accesibles WCAG AA).

---

## 3. Riesgos Técnicos y Mitigaciones

| Riesgo | Impacto | Mitigación |
| :--- | :--- | :--- |
| **Inclusión accidental en el portal general** | Alto (viola requisito de usuario) | Verificación formal en test y checklist: `dashboards/portal/index.html` no debe contener referencias al monitor. |
| **Desfase de datos tras subida de nuevo CSV** | Medio | Auto-refresco configurable (30s / 60s) y badge con timestamp de la última generación del catálogo (`_metadata.generated_at`). |
| **Fallo en peticiones POST en servidores estáticos (Nginx puro)** | Medio | Enfoque dual: el botón "Copiar Comando CLI" está siempre disponible y genera la sintaxis exacta de `update_agent_message.py`. |
| **Problemas de codificación UTF-8 con tildes/eñes** | Bajo | Cabeceras explícitas `Content-Type: application/json; charset=utf-8` en respuestas y lectura de archivos en Python con `encoding="utf-8"`. |

---

## 4. Conclusión

La investigación confirma que la solución es viable, limpia y altamente desacoplada, aprovechando al 100% las herramientas ya construidas en el proyecto sin duplicar lógica de negocio ni alterar los portales públicos.

