# Feature Specification: Sistema de Notificación de Incidencias de Alta Prioridad (012-high-priority-incident-notifications)

**Feature Branch**: `012-high-priority-incident-notifications`

**Created**: 2026-10-26

**Status**: Draft

**Input**: User description: "crea un sistema de notificacion de incidencia de alta prioridad. para ello debes consultar cada una de las incidencias masiva que motramos en el dashboard/massive-incidents/, obtener la informacion de la misma a través de la conexion a Epsilon para extraer el Resumen IA y con esa informacion determinar la prioridad que tiene(te puedes ayudar de la skill it-sererity-matrix."

---

## 🧭 Contexto y Origen de Datos

La plataforma **Release Dashboard Application** cuenta con un dashboard especializado de **Incidencias Masivas** accesible en `/dashboards/massive-incidents/`. Dicho panel carga los conjuntos de incidencias desde `data/output/index.json` (ficheros `*-massive.json`), conteniendo campos clave como:
- `ID de incidencia` (ej. `INC000003884945`, `INC000004141215`).
- `Prioridad` (Media, Alta, Crítica, etc.).
- `Descripción`.
- `Estatus` (Abierto, Asignado, En Curso, Pendiente, Cerrado).
- `Urgencia` e `Impacto` asignados en la herramienta de tickets.
- `Grupo asignado` y `Grupo Resolutor`.

Adicionalmente, el entorno dispone de integración con el servicio **Epsilon IA** a través del endpoint proxy `/api/epsilon/resumenIA/{codigo}` (soportado en `serve_app.py` y Nginx `nginx.conf`). Este endpoint devuelve la síntesis inteligente de la incidencia estructurada con:
- `sistemas`: Sistemas y componentes afectados.
- `problema`: Causa y comportamiento anómalo detectado.
- `impacto`: Alcance real del fallo sobre el negocio y clientes.
- `solucion`: Mitigaciones, parches o acciones correctivas.
- `bloqueos`: Factores bloqueantes o dependencias.
- `siguienteAccion`: Próximos pasos operativos.
- `hitos`: Cronología de eventos significativos.

Para la determinación rigurosa y justificada de la severidad, el proyecto dispone de la skill corporativa **`it-severity-matrix`** ([`.agents/skills/it-severity-matrix/SKILL.md`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/.agents/skills/it-severity-matrix/SKILL.md)), que cruza el **Impacto en el Negocio** (Alto, Medio, Bajo) con la **Urgencia Operativa** (Alta, Media, Baja) bajo el estándar ITIL/SRE, estableciendo:
- **P1 (Crítica)** y **P2 (Alta)** como niveles de **Alta Prioridad** que exigen notificación y escalado inmediato.
- Justificación formal obligatoria: Prioridad sugerida, Impacto evaluado, Urgencia evaluada y Existencia de workaround.
- Pautas de comunicación ejecutiva alineadas con el agente corporativo **`incident-reporter`** ([`agents/it-incidents/incident-reporter.md`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/agents/it-incidents/incident-reporter.md)), produciendo mensajes para Dirección en dos niveles estrictos: versión completa (hasta 90 palabras) y versión breve (hasta 30 palabras).

El objetivo de esta especificación es definir el **Sistema de Notificación de Incidencias de Alta Prioridad**, que identifica, evalúa y notifica las incidencias críticas (P1/P2) combinando los datos masivos con la inteligencia contextual de Epsilon IA.

---

## 💡 Clarificaciones y Decisiones de Diseño

### Q1: Experiencia de Notificación y Canales de Entrega
- **Decisión**: **Centro de Notificaciones Interactivo en el Dashboard con Acción de Copia Ejecutiva y Exportación**.
- **Detalle**:
  - En la interfaz del dashboard de Incidencias Masivas (`/dashboards/massive-incidents/`), se incorpora un **Centro de Notificaciones** visible en la cabecera (icono de campana con contador dinámico de incidencias de alta prioridad pendientes).
  - Al pulsar la campana, se abre un panel lateral/drawer con el listado de incidencias clasificadas como **P1** o **P2**.
  - Cada tarjeta de notificación muestra: código de incidencia, sistemas afectados, prioridad calculada (P1/P2) con etiqueta de color (Rojo para P1, Ámbar para P2), badge de discrepancia si la prioridad original era inferior, justificación de impacto/urgencia, SLA de respuesta aplicable y botón de **"Copiar Notificación Ejecutiva"** con 1 clic (formato Dirección <= 90 palabras y resumen <= 30 palabras según `incident-reporter`).
  - Posibilidad de marcar la notificación como "Leída / Comunicada" o "En Seguimiento".

### Q2: Estrategia de Consulta a Epsilon y Prevención de Sobrecarga (Rate Limiting y Caché)
- **Decisión**: **Evaluación Asíncrona Progresiva con Caché de Dos Capas y Filtro de Prioridad de Escaneo**.
- **Detalle**:
  - Un fichero masivo puede contener cientos o miles de registros (ej. 1.500 incidencias). Realizar 1.500 peticiones simultáneas a Epsilon saturaría la API y degradaría el rendimiento.
  - La evaluación prioriza por defecto:
    1. Incidencias activas / no cerradas (`Estatus != 'Cerrado'`).
    2. Incidencias del período temporal seleccionado en los filtros del dashboard.
  - Se implementa una cola con control de concurrencia (máximo 3 peticiones simultáneas) y reutilización estricta de la caché existente (Nginx `proxy_cache` y `sessionStorage` / almacenamiento persistente `data/output/high_priority_notifications.json`).
  - Si una incidencia no dispone de Resumen IA en Epsilon (404 o timeout), el sistema realiza una evaluación preliminar basada en los campos disponibles del CSV masivo (`Descripción`, `Impacto`, `Urgencia`) indicando la etiqueta `"Evaluación preliminar (sin datos de Epsilon)"`.

### Q3: Motor de Reglas de Severidad (`it-severity-matrix`)
- **Decisión**: **Clasificador Heurístico Contextual ITIL/SRE**.
- **Detalle**:
  - Cruce de Impacto y Urgencia según la tabla oficial:
    - **Impacto Alto**: Detección en `impacto` o `problema` de Epsilon de palabras clave críticas (caída total, indisponibilidad masiva, transacciones bloqueadas, más del 50% de usuarios, riesgo legal/datos, o ausencia de workaround), o campo `Impacto == "Masiva"` en el CSV con afectación troncal.
    - **Impacto Medio**: Degradación severa, afectación parcial (10%-50%), workaround manual existente.
    - **Impacto Bajo**: Incidencias aisladas, consultas o entornos de pruebas.
    - **Urgencia Alta**: Incidencia en curso/abierta, horario productivo, afectación en vivo ininterrumpida.
    - **Urgencia Media/Baja**: Incidencia contenida o cerrada.
  - Asignación de Prioridad:
    - Alto × Alta = **P1 (Crítica)**
    - Alto × Media = **P1 (Crítica)** o **P2 (Alta)**
    - Medio × Alta = **P2 (Alta)**
    - Medio × Media = **P2 (Alta)** o **P3 (Media)**
    - Resto = P3/P4.
  - Se genera para cada incidencia la justificación estructurada exigida por la skill.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Identificación y Visualización de Incidencias de Alta Prioridad (Priority: P1) 🎯 MVP

Como gestor de incidencias u operador de guardia de Orange, quiero acceder al dashboard de Incidencias Masivas y ver inmediatamente qué incidencias han sido evaluadas como de alta prioridad (P1 o P2) a partir de su Resumen IA en Epsilon, para focalizar la atención en los incidentes críticos sin revisar manualmente cientos de registros.

**Why this priority**: Constituye el núcleo esencial de la funcionalidad: conectar los datos masivos con Epsilon y la matriz de severidad para aislar las alertas críticas.

**Independent Test**: Cargar el dashboard de incidencias masivas, iniciar o visualizar la evaluación de alta prioridad y comprobar que la campana de notificaciones y la tabla muestran las incidencias clasificadas como P1 y P2 con su desglose de impacto y urgencia.

**Acceptance Scenarios**:

1. **Given** un conjunto de incidencias masivas cargadas en el dashboard, **When** el sistema consulta el Resumen IA en Epsilon para una incidencia con caída de servicio crítico y afectación en vivo, **Then** la clasifica como **P1 (Crítica)** o **P2 (Alta)** y la incorpora al panel de notificaciones de alta prioridad con su justificación ITIL.
2. **Given** una incidencia cuyo Resumen IA describe una degradación menor con solución alternativa sencilla, **When** se evalúa con la matriz, **Then** se clasifica como P3 o P4 y NO genera notificación en el panel de alta prioridad.
3. **Given** el panel de notificaciones abierto, **When** el usuario hace clic en una incidencia notificada, **Then** se abre el modal de Resumen IA existente (`window.openResumenIA`) mostrando el detalle completo de Epsilon.

---

### User Story 2 - Generación de Notificaciones Ejecutivas para Dirección (Priority: P2)

Como responsable de comunicación o Incident Commander, quiero generar a partir de la incidencia evaluada un mensaje de notificación ejecutiva estandarizado para Dirección (según las directrices de `incident-reporter`) con versiones completa (hasta 90 palabras) y breve (hasta 30 palabras) y copiarlo con un clic, para informar rápidamente a los comités sin redactar desde cero.

**Why this priority**: Convierte el análisis técnico en comunicación ejecutiva inmediata y de alto impacto, ahorrando tiempo crítico durante incidentes mayores.

**Independent Test**: Seleccionar una incidencia en el panel de notificaciones de alta prioridad, pulsar "Generar Notificación Ejecutiva", seleccionar la fase (apertura, seguimiento o cierre) y verificar que se genera el texto con conteo de palabras conforme a las reglas del agente y que el botón "Copiar" traslada el texto al portapapeles.

**Acceptance Scenarios**:

1. **Given** una incidencia evaluada como P1 o P2, **When** el usuario selecciona la fase "Apertura", **Then** el sistema genera una versión completa de hasta 90 palabras (qué pasó, afectación, impacto y acciones en curso) y una versión breve de hasta 30 palabras apta para SMS o asunto de correo.
2. **Given** la notificación generada en pantalla, **When** el usuario hace clic en "Copiar versión breve" o "Copiar versión completa", **Then** el texto se copia al portapapeles del sistema y se muestra confirmación visual ("Copiado al portapapeles").

---

### User Story 3 - Detección de Discrepancias de Prioridad (Priority: P3)

Como gestor de calidad y procesos ITIL, quiero que el sistema resalte aquellas incidencias donde la prioridad original asignada en el ticket (ej. "Media" o "Baja") discrepa con la severidad real calculada por la IA (P1 o P2), para identificar tickets mal catalogados que requieren escalado urgente.

**Why this priority**: Evita incidentes desatendidos por errores de triaje manual o subestimación del impacto en la apertura del ticket.

**Independent Test**: Introducir una incidencia con prioridad nominal "Media" cuyo texto en Epsilon describe un corte total de servicio; verificar que en el panel de notificaciones aparece con la insignia distintiva "⚠️ Posible Subescalación (Ticket: Media → Sugerida: P1)".

**Acceptance Scenarios**:

1. **Given** una incidencia con campo `Prioridad: "Media"` en el CSV, **When** el análisis de Epsilon determina severidad P1 o P2, **Then** el sistema muestra un badge visible de "Discrepancia de Severidad" y destaca la incidencia en la parte superior del listado.
2. **Given** el filtro de notificaciones del dashboard, **When** el usuario selecciona filtrar por "Solo discrepancias", **Then** el panel muestra exclusivamente las incidencias cuya prioridad calculada supera la del ticket original.

---

### User Story 4 - Gestión del Estado de las Notificaciones y Persistencia (Priority: P4)

Como operador de guardia, quiero marcar las notificaciones como "Comunicada", "En seguimiento" o "Descartada", para mantener la trazabilidad del turno y que otros operadores sepan qué incidencias ya han sido notificadas.

**Why this priority**: Evita notificaciones duplicadas y proporciona control operativo durante los relevos de turno.

**Independent Test**: Cambiar el estado de una notificación a "Comunicada", recargar el dashboard o reabrir el panel y comprobar que el estado se conserva en la sesión local.

**Acceptance Scenarios**:

1. **Given** una notificación de alta prioridad en estado "Pendiente", **When** el usuario pulsa "Marcar como comunicada", **Then** el contador de la campana se reduce y la tarjeta pasa a la sección de notificaciones gestionadas.
2. **Given** el historial de notificaciones, **When** el usuario consulta la pestaña "Gestionadas", **Then** puede revisar qué operador o en qué fecha/hora se registró la última acción.

---

## Edge Cases

- **Incidencia sin datos en Epsilon IA (HTTP 404 o timeout)**: El sistema no bloquea la cola; efectúa una evaluación preliminar basada en los campos de la incidencia masiva (`Descripción`, `Urgencia`, `Impacto`) y muestra la advertencia `"Sin síntesis Epsilon (evaluación basada en metadatos del ticket)"`.
- **API Epsilon no disponible o error 5xx**: La interfaz muestra una notificación de advertencia degradada sin interrumpir la visualización normal del dashboard.
- **Incidencias con descripciones breves o ambiguas**: Si Epsilon no aporta suficiente contexto para medir el impacto, la matriz asigna el valor más conservador justificado y solicita confirmación al operador.
- **Gran volumen de incidencias simultáneas (+1.000)**: El sistema aplica paginación y limitación de tasa (rate limiting: 3 peticiones concurrentes con pausa de 100ms) procesando primero las incidencias con estatus activo (`Pendiente`, `En curso`, `Asignado`).
- **Dispositivos móviles o pantallas reducidas**: El panel lateral de notificaciones es completamente responsivo, adaptándose a pantalla completa en anchos inferiores a 768px.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE proveer un módulo de análisis de severidad que evalúe cada incidencia masiva cruzando el Impacto y la Urgencia conforme a las reglas de la skill `it-severity-matrix`.
- **FR-002**: El sistema DEBE consultar el endpoint proxy de Epsilon IA `/api/epsilon/resumenIA/{codigo}` para obtener el contexto enriquecido (sistemas, problema, impacto, solución, bloqueos, hitos) de cada incidencia evaluada.
- **FR-003**: El sistema DEBE clasificar las incidencias en los cuatro niveles estándar de prioridad: P1 (Crítica), P2 (Alta), P3 (Media) y P4 (Baja).
- **FR-004**: El sistema DEBE considerar como **Alta Prioridad** únicamente las incidencias categorizadas como **P1** o **P2**.
- **FR-005**: El sistema DEBE generar para cada incidencia clasificada como alta prioridad un bloque de justificación estructurado con:
  - Prioridad sugerida (`P1 - Crítica` o `P2 - Alta`).
  - Impacto evaluado (`Alto` / `Medio` / `Bajo`) con justificación.
  - Urgencia evaluada (`Alta` / `Media` / `Baja`) con justificación.
  - Existencia de *workaround* (`Sí` / `No` / `Desconocido`).
  - SLA de tiempo de respuesta objetivo (<15 min para P1; <30-60 min para P2).
- **FR-006**: El sistema DEBE integrar un **Centro de Notificaciones** en el dashboard de Incidencias Masivas (`dashboards/massive-incidents/index.html`) accesible mediante un icono de campana en la cabecera corporativa con badge numérico de incidencias pendientes.
- **FR-007**: El Centro de Notificaciones DEBE listar las incidencias de alta prioridad activas mostrando código, sistemas, severidad calculada, resumen del impacto y acciones rápidas.
- **FR-008**: El sistema DEBE permitir generar mensajes de notificación ejecutiva alineados con el agente `incident-reporter` en tres fases operativas (`apertura`, `seguimiento`, `cierre`), proporcionando:
  - Versión completa para Dirección de hasta 90 palabras en un único párrafo.
  - Versión breve de hasta 30 palabras para asunto de correo o SMS.
- **FR-009**: El sistema DEBE proveer botones de copia rápida al portapapeles para ambas versiones del mensaje ejecutivo con retroalimentación visual al usuario.
- **FR-010**: El sistema DEBE detectar y señalar visualmente cualquier discrepancia donde la prioridad del ticket original sea menor a la calculada por la IA (ej. Ticket Media → Sugerida P1/P2).
- **FR-011**: El sistema DEBE implementar control de concurrencia y caché (local o de sesión) para las consultas a Epsilon para no saturar el servicio y permitir tiempos de respuesta fluidos.
- **FR-012**: El sistema DEBE permitir cambiar el estado de las notificaciones (`Pendiente`, `Comunicada`, `Descartada`) persistiendo el estado en el almacenamiento local del navegador (`localStorage`/`sessionStorage`).

---

### Key Entities

- **`IncidentNotification`**: Registro de alerta de alta prioridad.
  - Atributos: `id` (código de incidencia), `fechaDeteccion`, `prioridadCalculada` (P1 | P2), `prioridadOriginal`, `esDiscrepancia` (boolean), `estadoNotificacion` (pendiente | comunicada | descartada), `justificacion`, `mensajeEjecutivo`, `resumenIA`.
- **`SeverityEvaluation`**: Resultado de la evaluación ITIL/SRE.
  - Atributos: `codigo`, `impacto` (Alto | Medio | Bajo), `impactoDetalle`, `urgencia` (Alta | Media | Baja), `urgenciaDetalle`, `workaround` (Si | No | Desconocido), `prioridad` (P1 | P2 | P3 | P4), `slaMinutos`.
- **`ExecutiveNotificationMessage`**: Mensaje adaptado para comités de dirección.
  - Atributos: `codigo`, `fase` (apertura | seguimiento | cierre), `versionCompleta` (string, <=90 palabras), `versionBreve` (string, <=30 palabras), `generadoEn`.
- **`EpsilonIncidentContext`**: Datos extraídos de la API Epsilon.
  - Atributos: `codigo`, `titulo`, `sistemas`, `problema`, `impacto`, `solucion`, `bloqueos`, `siguienteAccion`, `hitos`.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de las incidencias masivas clasificadas con impacto crítico o urgencia alta son detectadas y presentadas en el panel de notificaciones de alta prioridad.
- **SC-002**: La evaluación de una incidencia individual a partir de Epsilon IA se completa en menos de 1,5 segundos (o instantáneamente si ya reside en caché).
- **SC-003**: El 100% de los mensajes ejecutivos generados cumplen con las restricciones de extensión máxima: versión completa $\le$ 90 palabras y versión breve $\le$ 30 palabras.
- **SC-004**: Los operadores pueden copiar el mensaje ejecutivo formateado y listo para emisión en un solo clic, reduciendo el tiempo de preparación de la notificación de más de 10 minutos a menos de 15 segundos.
- **SC-005**: El sistema gestiona lotes de hasta 200 incidencias concurrentes sin exceder el límite de 3 peticiones simultáneas a Epsilon ni degradar la tasa de refresco del dashboard por debajo de 60 fps.

---

## Assumptions

- **Conectividad con Epsilon**: El proxy `/api/epsilon/resumenIA/{codigo}` está operativo en el servidor de desarrollo y en producción a través de Nginx.
- **Datos de entrada**: El dashboard de Incidencias Masivas dispone al menos de un fichero activo cargado en `data/output/index.json`.
- **Autenticación en canales externos**: La integración directa con plataformas de mensajería (Webhooks, bots de Teams/Slack) se deja abierta para una fase futura; el canal principal de entrega para esta fase es la interfaz web con copia asistida al portapapeles y almacenamiento del estado operativo.
- **Identificadores de Incidencia**: Los códigos de incidencia siguen el estándar corporativo `INC` seguido de dígitos (ej. `INC000004141215`).

