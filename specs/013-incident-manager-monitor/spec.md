# Feature Specification: Frontal Web de Monitorización para Incident Manager (013-incident-manager-monitor)

**Feature Branch**: `013-incident-manager-monitor`

**Created**: 2026-10-28

**Status**: Draft

**Input**: User description: "speckit-specify crea un frontal web que muestre las incidencias activas de alta prioridad que estén pendientes de redaccion de agente. Este frontal no debe verse en el portal general sino que sea una herramienta de monitorizacion del incident manager. Apoyate en las herramientas que tenemos desarrolladas actualmente en el proyecto."

---

## 🧭 Contexto y Origen de Datos

En la gestión de incidentes mayores de Orange, tras la ingesta de un nuevo informe masivo de incidencias (ficheros `CS-Informe incidencias P1, P2 y P3 - *.csv` procesados hacia `data/output/*-massive.json`), el sistema evalúa la severidad ITIL/SRE a través del motor `converters/cli/evaluate_incident_notifications.py` y genera el catálogo persistente `data/output/high_priority_notifications.json`.

Dicho catálogo cruza los metadatos de tickets con la síntesis de **Epsilon IA** y aplica las reglas de la skill corporativa **`it-severity-matrix`** ([`.agents/skills/it-severity-matrix/SKILL.md`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/.agents/skills/it-severity-matrix/SKILL.md)) para identificar:
1. **Incidencias de Alta Prioridad Activas**: Incidentes clasificados como **P1 (Crítica)** o **P2 (Alta)** con estatus operativo no terminal (`Asignado`, `En Curso`, `Pendiente`).
2. **Discrepancias de Triaje (Subescalaciones)**: Tickets nominalmente clasificados como P3 (Media) o P4 (Baja) en Remedy cuya afectación real amerita SL1/P1 o SL2/P2 según los umbrales de los 6 Procesos Críticos de Negocio y la Regla de Oro N1.
3. **Estado de Redacción Ejecutiva**: Cada incidencia evaluada requiere mensajes ejecutivos oficiales para Dirección redactados en dos niveles estrictos (versión completa de hasta 90 palabras en monopárrafo y versión breve de hasta 30 palabras) por el agente corporativo **`incident-reporter`** ([`agents/it-incidents/incident-reporter.md`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/agents/it-incidents/incident-reporter.md)) para tres fases: `apertura`, `seguimiento` y `cierre`.

### Herramientas y Componentes Existentes Reutilizados

El proyecto ya cuenta con un ecosistema robusto de herramientas que deben servir de base directa para este frontal:
- **`data/output/high_priority_notifications.json`**: Almacena el catálogo unificado en tiempo real con las incidencias activas, su prioridad sugerida, proceso de negocio, criterio/umbral, justificación ITIL, resumen de Epsilon IA y el estado de sus mensajes ejecutivos (`generado_por_agente: true/false`, `estado: "pendiente"` y el campo `prompt_agente` precalculado).
- **`data/agent_executive_messages.json`**: Almacén persistente oficial de las redacciones emitidas por el agente `incident-reporter`.
- **`scan_pending_incidents.py`** ([`.agents/skills/incident-executive-notifications/scripts/scan_pending_incidents.py`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/.agents/skills/incident-executive-notifications/scripts/scan_pending_incidents.py)): Script de escaneo que cruza el catálogo y el almacén para aislar las incidencias con redacciones pendientes, ofreciendo modos `--json` y `--id <INC>`.
- **`update_agent_message.py`** ([`converters/cli/update_agent_message.py`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/converters/cli/update_agent_message.py)): Utilidad CLI para registrar redacciones oficiales validadas y desencadenar la regeneración automática de las notificaciones.
- **Proxy Epsilon IA** (`/api/epsilon/resumenIA/{codigo}`): Servicio en `serve_app.py` y Nginx para consultar la síntesis contextual de problemas, bloqueos y soluciones.
- **Activos UI y Estilos Corporativos**: `/dashboards/assets/topbar.css`, `/dashboards/assets/shared.css`, `/dashboards/assets/incident-notifications.css` y `/dashboards/assets/resumen-ia.css` (modal de Epsilon).

El objetivo de esta especificación es definir el **Frontal Web de Monitorización para el Incident Manager** (*Cockpit IM*), una consola operativa dedicada y de alta densidad que centraliza la vigilancia de las incidencias activas pendientes de redacción de agente, facilitando el acceso a su contexto, la obtención rápida del prompt para el agente y la ingesta inmediata de las comunicaciones hacia el almacén oficial.

---

## 💡 Clarificaciones y Decisiones de Diseño

### Q1: Ubicación, Enrutamiento y Aislamiento del Portal General
- **Requisito del Usuario**: *"Este frontal no debe verse en el portal general sino que sea una herramienta de monitorizacion del incident manager."*
- **Decisión**: **Ruta Dedicada No Enlazada en el Portal Público**.
- **Detalle**:
  - El frontal se implementará en una ruta operativa específica: `/dashboards/incident-manager-monitor/` (fichero físico `dashboards/incident-manager-monitor/index.html`).
  - **Aislamiento estricto**: Queda expresamente prohibido incluir tarjetas, enlaces o accesos a esta ruta en la página principal del portal general (`dashboards/portal/index.html` y `dashboards/index.html`).
  - **Canal de acceso**: Los Incident Managers accederán mediante URL directa, marcadores de navegador o enlaces en la documentación operativa interna ([`docs/INCIDENT-EXECUTIVE-NOTIFICATIONS-WORKFLOW.md`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/docs/INCIDENT-EXECUTIVE-NOTIFICATIONS-WORKFLOW.md)).

### Q2: Arquitectura de Datos y Estrategia de Carga
- **Decisión**: **Carga Directa del Catálogo JSON con API de Soporte en Servidor**.
- **Detalle**:
  - El frontal web consumirá por defecto `/data/output/high_priority_notifications.json` y `/data/agent_executive_messages.json`, los cuales ya son servidos de forma estática y ultrarrápida por `serve_app.py` y Nginx.
  - La lógica de discriminación de pendientes replica fielmente el criterio de `scan_pending_incidents.py`: una incidencia está pendiente si su fase `apertura` (o cualquiera requerida) tiene `estado == "pendiente"`, carece de texto en `completo` o no se encuentra registrada con `generado_por_agente: true` en el almacén oficial.
  - Para entornos que soporten peticiones dinámicas, `serve_app.py` expondrá adicionalmente un endpoint de conveniencia `/api/incident-manager/pending` y un endpoint `/api/incident-manager/save-message` que invoca `update_agent_store()` y reevalúa el catálogo sin necesidad de abandonar el navegador.

### Q3: Experiencia de Usuario y Flujo de Trabajo del Incident Manager
- **Decisión**: **Cockpit de Alta Densidad con Acciones Rápidas en 1 Clic**.
- **Detalle**:
  - **Barra de KPIs**: Contadores destacados de *Total Activas Alta Prioridad*, *Con Mensaje Oficial*, *Pendientes de Redacción* (con alerta visual prominente si > 0), *Críticas P1*, *Altas P2* y *Discrepancias*.
  - **Filtro de Cola**: Visualización por defecto de **"Solo Pendientes"** (foco operativo inmediato), con opción de conmutar a **"Todas las Activas"**.
  - **Ficha de Incidencia Pendiente**: Cada ticket muestra su cabecera (ID, fecha de envío, sistemas, estado Remedy, SLA objetivo), insignia de prioridad P1/P2 con badge de discrepancia, bloque de Proceso de Negocio y Criterio ITIL, y contexto de Epsilon IA.
  - **Espacio de Redacción de Agente**:
    - Selector de fase (`Apertura`, `Seguimiento`, `Cierre`).
    - Visualizador del prompt generado para `incident-reporter`.
    - Botón **"Copiar Prompt"**: copia el prompt completo al portapapeles para pegarlo en la sesión del agente LLM.
    - Asistente de Ingesta: campo para pegar la respuesta del agente con validación visual inmediata del conteo de palabras ($\le$ 90 palabras para versión completa monopárrafo y $\le$ 30 palabras para versión breve).
    - Botón **"Guardar Mensaje Oficial"**: persiste en el almacén mediante API o genera el comando CLI exacto de `update_agent_message.py` listo para copiar en terminal.

### Q4: Modos de Refresco y Monitorización en Tiempo Real
- **Decisión**: **Sincronización Automática Configurable y Detección de Cambios de Fichero**.
- **Detalle**:
  - La interfaz incluirá un selector de auto-refresco (Desactivado, cada 30 segundos, cada 60 segundos) y un botón de refresco manual.
  - Cada refresco comprobará la cabecera `Last-Modified` o el campo `_metadata.generated_at` para alertar al operador si se ha subido un nuevo CSV a producción.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cockpit de Detección y Monitorización de Incidencias Pendientes (Priority: P1) 🎯 MVP

Como Incident Manager en guardia operativa, quiero acceder a una consola web dedicada que me muestre exclusivamente las incidencias activas de alta prioridad que tienen pendiente la redacción ejecutiva de agente, para identificar al instante qué incidentes críticos carecen de comunicación oficial para Dirección.

**Why this priority**: Constituye la necesidad operativa nuclear: eliminar la ceguera sobre qué incidencias P1/P2 están pendientes de comunicación tras la subida de un nuevo CSV o cambio de turno.

**Independent Test**: Acceder a `/dashboards/incident-manager-monitor/` teniendo al menos una incidencia con `estado: "pendiente"` en `high_priority_notifications.json` y verificar que la tarjeta aparece en la cola principal con su indicador de prioridad P1/P2 y badge de alerta.

**Acceptance Scenarios**:

1. **Given** un catálogo con 15 incidencias activas de alta prioridad de las cuales 1 está en estado "pendiente" (ej. `INC000004168775`), **When** el Incident Manager carga la herramienta, **Then** el contador KPI muestra "1 Pendiente de Redacción" en color de alerta y el listado muestra únicamente la ficha de dicha incidencia.
2. **Given** un catálogo donde todas las incidencias activas disponen de mensajes oficiales completados, **When** el Incident Manager consulta la herramienta, **Then** se muestra un estado de felicitación ("✅ Todas las incidencias activas disponen de mensajes ejecutivos oficiales. No hay redacciones pendientes").
3. **Given** una incidencia con discrepancia de severidad (ticket nominalmente P3 pero clasificado P1 por Regla de Oro N1), **When** se visualiza en la cola, **Then** resalta con la insignia "⚠️ Subescalación detectada (Ticket: Media → Sugerida: P1)".

---

### User Story 2 - Inspección de Contexto Operativo y Copia del Prompt de Agente (Priority: P1) 🎯 MVP

Como Incident Manager, quiero consultar el desglose contextual de la incidencia (Proceso de Negocio, Criterio, Sistemas y Epsilon IA) y copiar en un solo clic el prompt preconfigurado para el agente `incident-reporter`, para solicitar la redacción ejecutiva al agente sin redactar instrucciones complejas desde cero.

**Why this priority**: Garantiza que las redacciones cumplan con la matriz de severidad corporativa y ahorra minutos críticos en el triaje de incidentes mayores.

**Independent Test**: Pulsar sobre una incidencia pendiente, alternar entre las pestañas "Apertura", "Seguimiento" y "Cierre", pulsar "Copiar Prompt" y validar que el portapapeles contiene el texto estructurado con los metadatos y límites de 90/30 palabras.

**Acceptance Scenarios**:

1. **Given** una incidencia pendiente en la interfaz, **When** el usuario hace clic en la pestaña "Apertura", **Then** se visualiza el prompt exacto precalculado que incluye Proceso (`Atención al Cliente (ATC)`), Criterio (`ATC: Frontales/CRM...`), Sistemas y las instrucciones de extensión monopárrafo.
2. **Given** el visualizador de prompt, **When** el usuario pulsa "Copiar Prompt para Agente", **Then** el contenido se copia al portapapeles del sistema y el botón muestra feedback temporal ("¡Prompt copiado!").
3. **Given** una incidencia con síntesis en Epsilon IA disponible, **When** el usuario pulsa "Ver Resumen Epsilon", **Then** se abre el modal interactivo de Epsilon IA con la información de diagnóstico y bloqueos.

---

### User Story 3 - Asistente de Ingesta y Persistencia en el Almacén Oficial (Priority: P2)

Como Incident Manager, una vez obtenida la redacción generada por el agente, quiero validar de inmediato el cumplimiento de los límites de palabras ($\le$ 90 palabras en versión completa y $\le$ 30 palabras en versión breve) e ingresarla en el almacén oficial para que la incidencia se marque automáticamente como resuelta en la monitorización.

**Why this priority**: Cierra el ciclo operativo: asegura la calidad antes de publicar y actualiza el estado de la cola sin requerir manipulación manual de ficheros JSON.

**Independent Test**: Pegar una redacción de prueba en el asistente de ingesta, comprobar que el contador de palabras valida en verde (o advierte en rojo si supera 90/30 palabras), enviar el formulario y comprobar que la incidencia desaparece de la cola de pendientes tras la reevaluación.

**Acceptance Scenarios**:

1. **Given** el formulario de ingesta de un ticket, **When** el usuario introduce una versión completa de 82 palabras y una breve de 22 palabras, **Then** los contadores marcan "82/90 palabras (Válido)" y "22/30 palabras (Válido)" con estilos positivos.
2. **Given** un texto que supera el límite (ej. 95 palabras), **When** el usuario lo introduce, **Then** el contador marca "95/90 palabras (Excede límite)" en color rojo y advierte al operador para recortar antes de guardar.
3. **Given** mensajes válidos introducidos, **When** el usuario pulsa "Guardar en Almacén Oficial", **Then** el sistema persiste los datos en `data/agent_executive_messages.json`, regenera el catálogo de notificaciones y actualiza la vista mostrando la incidencia como completada.
4. **Given** un entorno donde el Incident Manager prefiere usar terminal CLI, **When** pulsa "Copiar Comando CLI", **Then** se genera y copia la sintaxis exacta de `python converters/cli/update_agent_message.py --id <INC> --phase <FASE> --completo "..." --breve "..."`.

---

### User Story 4 - Supervisión Integral y Filtrado de Incidencias Activas (Priority: P2)

Como Incident Manager o Coordinador de Operaciones, quiero alternar entre la cola de pendientes y la vista de todas las incidencias de alta prioridad activas, pudiendo filtrar por severidad (P1 / P2), por Proceso de Negocio o buscar por código de ticket, para disponer de una visión panorámica de la situación operativa del turno.

**Why this priority**: Facilita auditorías de guardia, revisiones cruzadas y comprobación de mensajes previamente emitidos para incidencias en seguimiento o cierre.

**Independent Test**: Cambiar el conmutador de filtro a "Todas las Activas", aplicar un filtro por severidad "Solo P1" o por proceso "Facturación y Cobros", y comprobar que la lista se filtra instantáneamente en el cliente.

**Acceptance Scenarios**:

1. **Given** la consola de monitorización, **When** el usuario activa la pestaña "Todas las Activas", **Then** se presentan tanto las incidencias con mensajes oficiales completados como las pendientes, mostrando el badge de su estado respectivo.
2. **Given** la lista de incidencias, **When** el usuario escribe un término en el campo de búsqueda (ej. `BSCS` o `INC000004168617`), **Then** la lista filtra en tiempo real los registros coincidentes.
3. **Given** una incidencia completada en la vista general, **When** el usuario pulsa "Ver Mensajes Oficiales", **Then** se despliegan las versiones aprobadas de Apertura, Seguimiento y Cierre para su lectura o reenvío.

---

### User Story 5 - Aislamiento Estricto del Portal General (Priority: P3)

Como Administrador de la plataforma y responsable de usabilidad de la herramienta, quiero garantizar que esta interfaz operativa del Incident Manager no aparezca en el menú ni en las tarjetas públicas del portal general (`dashboards/portal/index.html`), asegurando que solo el personal operativo de guardia acceda a ella.

**Why this priority**: Cumple con la restricción expresa del usuario para evitar confundir a usuarios de negocio o audiencias no técnicas con herramientas de gestión interna de agentes.

**Independent Test**: Inspeccionar el código HTML y visual del portal principal (`/dashboards/portal/` y `/dashboards/`) y verificar que no existe ningún enlace, botón ni tarjeta que apunte a `/dashboards/incident-manager-monitor/`.

**Acceptance Scenarios**:

1. **Given** la página principal del portal general (`dashboards/portal/index.html`), **When** se examinan todas las secciones y tarjetas de dashboards disponibles, **Then** NO existe ninguna referencia ni enlace a `incident-manager-monitor`.
2. **Given** un navegador web apuntando a `/dashboards/incident-manager-monitor/`, **When** se realiza la petición, **Then** la página carga correctamente como herramienta autónoma con su propia cabecera y controles operativos.

---

## Edge Cases

- **Catálogo no generado o archivo ausente (`high_priority_notifications.json` no existe)**: La interfaz debe mostrar un banner de advertencia claro indicando que se debe ejecutar primero la evaluación de notificaciones (`evaluate_incident_notifications.py`), proporcionando el comando CLI correspondiente.
- **Sin incidencias activas de alta prioridad en el último CSV masivo**: La interfaz debe presentar una pantalla de estado limpio ("Zero Active P1/P2 Incidents") confirmando que no hay alertas activas en el período actual.
- **Fallo temporal de conectividad con la API local al guardar**: Si el guardado vía HTTP falla, la interfaz debe mostrar un mensaje de error no intrusivo y resaltar el botón de copia del comando CLI como mecanismo de contingencia para que el usuario no pierda el texto redactado.
- **Incidencia sin datos en Epsilon IA (solo metadatos Remedy)**: La tarjeta de la incidencia debe mostrar claramente el distintivo *"ℹ️ Solo metadatos Remedy"* y generar el prompt correspondiente basado en la descripción y categorización del ticket.
- **Redacción con saltos de línea múltiples en la versión completa**: El asistente de ingesta debe normalizar automáticamente el texto a un único párrafo cohesionado conforme a las directrices de `incident-reporter`.
- **Textos con comillas o caracteres especiales en español (tildes, eñes, comillas angulares)**: El sistema debe asegurar codificación UTF-8 estricta en el guardado y en la generación de comandos CLI para evitar errores de codificación en entornos Windows.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE proveer un frontal web autónomo ubicado en `/dashboards/incident-manager-monitor/` accesible mediante su URL directa.
- **FR-002**: El sistema DEBE garantizar el **aislamiento visual**, NO incluyendo enlaces, tarjetas ni accesos a este frontal en la interfaz pública del portal general (`dashboards/portal/index.html` ni `dashboards/index.html`).
- **FR-003**: El sistema DEBE consumir los datos de incidencias de alta prioridad activas a partir de `data/output/high_priority_notifications.json` y del almacén `data/agent_executive_messages.json`.
- **FR-004**: El sistema DEBE clasificar una incidencia como **Pendiente de Redacción** cuando no disponga de mensajes oficiales generados por agente (`generado_por_agente != true`), su estado sea `"pendiente"` o no figure en el almacén oficial.
- **FR-005**: El sistema DEBE presentar un panel superior de KPIs que refleje en tiempo real:
  - Total de incidencias de alta prioridad activas.
  - Incidencias completadas con redacción oficial.
  - Incidencias pendientes de redacción de agente (con resalte visual crítico si el valor es superior a 0).
  - Desglose por Severidad (Críticas P1 vs Altas P2).
  - Número de discrepancias de severidad detectadas.
  - Fecha y hora de la última sincronización / evaluación.
- **FR-006**: El sistema DEBE mostrar por defecto la cola de **"Solo Pendientes"**, permitiendo al usuario conmutar mediante pestañas o interruptor hacia la vista de **"Todas las Activas"**.
- **FR-007**: Cada tarjeta de incidencia en la cola DEBE exhibir de forma prominente:
  - Identificador único (`INC00000XXXXXX`) y título oficial del ticket.
  - Severidad sugerida calculada (`P1 - Crítica` o `P2 - Alta`).
  - Badge de discrepancia si la prioridad original era inferior (`⚠️ Subescalación`).
  - Proceso Crítico de Negocio asignado (uno de los 6 procesos: Atención al Cliente, Ventas, Facturación, Provisión, Servicios de Red, Sistemas Core).
  - Criterio / Umbral específico de la matriz de severidad aplicado.
  - Sistemas y componentes afectados (`sistemas`).
  - Estatus operativo en ticket (`Asignado`, `En Curso`, `Pendiente`) y fecha/hora de envío.
  - Indicador de estado de Epsilon IA con acceso al modal de detalle.
- **FR-008**: Para cada incidencia pendiente, el sistema DEBE proporcionar un selector de fase operativa (`Apertura`, `Seguimiento`, `Cierre`) con su correspondiente prompt precalculado para el agente `incident-reporter`.
- **FR-009**: El sistema DEBE ofrecer un botón de **"Copiar Prompt para el Agente"** que traslade el texto completo al portapapeles con confirmación visual.
- **FR-010**: El sistema DEBE incorporar un asistente de ingesta que permita introducir o pegar el texto generado por el agente, validando en tiempo real:
  - Conteo de palabras de la Versión Completa (límite: $\le$ 90 palabras, monopárrafo).
  - Conteo de palabras de la Versión Breve (límite: $\le$ 30 palabras).
- **FR-011**: El sistema DEBE permitir guardar las redacciones validadas en el almacén persistente `data/agent_executive_messages.json` y desencadenar la actualización del catálogo de notificaciones.
- **FR-012**: El sistema DEBE ofrecer un botón alternativo de **"Copiar Comando CLI"** que genere la sintaxis ejecutable de `converters/cli/update_agent_message.py` para operadores que utilicen terminal.
- **FR-013**: El sistema DEBE ofrecer controles de filtrado dinámico en cliente: por severidad (P1, P2), por discrepancia, por proceso crítico y por búsqueda de texto libre.
- **FR-014**: El sistema DEBE incluir un mecanismo de auto-refresco configurable (Manual, cada 30s, cada 60s) con indicador de estado visual.
- **FR-015**: El servidor local `serve_app.py` y la configuración de producción Nginx DEBEN servir los archivos del frontal y proveer las rutas API necesarias para la consulta y actualización de mensajes.

---

### Key Entities

- **`PendingIncidentQueueItem`**: Representación en la interfaz de un ticket pendiente de redacción.
  - Atributos: `id`, `titulo`, `sistemas`, `prioridad_sugerida` (P1 | P2), `prioridad_original`, `es_discrepancia` (boolean), `proceso`, `criterio`, `fecha_envio`, `estatus`, `tiene_epsilon` (boolean), `prompts` (mapa de fase a string de prompt).
- **`AgentDraftInput`**: Estructura de captura de redacciones en la interfaz.
  - Atributos: `incident_id`, `fase` (apertura | seguimiento | cierre), `version_completa` (string), `version_breve` (string), `conteo_completo` (int), `conteo_breve` (int), `valido` (boolean).
- **`MonitorKPIs`**: Métricas operativas mostradas en la cabecera.
  - Atributos: `total_activas`, `completadas`, `pendientes`, `total_p1`, `total_p2`, `discrepancias`, `ultimo_refresco`.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de las incidencias activas de alta prioridad identificadas con estado "pendiente" en el catálogo son visibles inmediatamente en el frontal del Incident Manager.
- **SC-002**: El tiempo medio para que un Incident Manager copie el prompt listo para el agente se reduce a menos de 5 segundos desde la apertura del frontal.
- **SC-003**: El 100% de los mensajes validados a través del asistente de ingesta cumplen de forma estricta los límites máximos ($\le$ 90 palabras para versión completa y $\le$ 30 palabras para versión breve).
- **SC-004**: La interfaz del portal general (`dashboards/portal/index.html`) mantiene un 0% de enlaces hacia la herramienta de monitorización, preservando el aislamiento funcional requerido.
- **SC-005**: La carga inicial y el refresco de la cola de incidencias se ejecuta en menos de 500 milisegundos en condiciones normales de red local.

---

## Assumptions

- **Disponibilidad de Catálogos**: El proceso de carga de CSV ejecuta periódicamente `evaluate_incident_notifications.py` asegurando que `data/output/high_priority_notifications.json` se encuentre actualizado.
- **Rol del Usuario**: Quien interactúa con este frontal es un Incident Manager o miembro del equipo de operaciones de guardia con permisos para registrar redacciones oficiales en nombre del agente.
- **Entorno de Despliegue**: El frontal es servido a través del servidor HTTP local de desarrollo `serve_app.py` (puerto 8080) y por Nginx en el entorno de producción Orange.
- **Compatibilidad de Navegadores**: Navegadores modernos compatibles con ES6+, CSS Grid, Flexbox y Clipboard API (Chrome, Edge, Firefox).
