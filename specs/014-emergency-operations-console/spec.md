# Feature Specification: Consola Operativa de Emergencias Orange en Tiempo Real (014-emergency-operations-console)

**Feature Branch**: `014-emergency-operations-console`

**Created**: 2026-10-29

**Status**: Draft

**Input**: User description: "ampliar incident-manager-monitor para sea una consola operativa de emergencias Orange en tiempo real, que detecte discrepancias con métricas exactas, controle los tiempos de escalado telefónico (45 min) y bloquee desescaladas indebidas por workarounds."

---

## 🧭 Contexto y Misión Operativa

En las operaciones de telecomunicaciones y TI de Orange Tech Operations, la gestión de incidentes mayores (SL1/SL2) exige un control milimétrico del tiempo, triaje riguroso sin ambigüedades y una estricta gobernanza en la toma de decisiones técnicas. 

La herramienta actual `incident-manager-monitor` (especificada en [`013-incident-manager-monitor`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/specs/013-incident-manager-monitor/spec.md) y desplegada en `/dashboards/incident-manager-monitor/`) nació orientada a la vigilancia de redacciones ejecutivas de agente pendientes de emisión. 

Esta especificación define la **evolución y transformación integral de `incident-manager-monitor` en una Consola Operativa de Emergencias IT de Orange en Tiempo Real**, integrando formalmente los principios de la skill corporativa **`orange-it-emergency-management`** ([`.agents/skills/orange-it-emergency-management/SKILL.md`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/.agents/skills/orange-it-emergency-management/SKILL.md)) y de la matriz de severidad **`it-severity-matrix`** ([`.agents/skills/it-severity-matrix/SKILL.md`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/.agents/skills/it-severity-matrix/SKILL.md)).

### Pilares de la Consola de Emergencias

1. **Detección de Discrepancias con Métricas Cuantitativas Exactas**: Superar la etiqueta genérica de "subescalación" para mostrar con precisión matemática qué umbral objetivo de los 6 Procesos Críticos de Negocio ha sido rebasado (ej. Atención al Cliente: *">20% llamadas en 1 hora"* o *">20% desviación en Frontales/CRM"*; Facturación: *">3h sin tarificación online"* o *"ventana ±3 días de ciclo"*; Provisión: *">20% errores en órdenes móvil"* o *">30% en fijo"*).
2. **Control Cronológico y Alertas de Escalado Telefónico (Hito 45 min y +1h)**: Cronometraje dinámico y en tiempo real desde la apertura del ticket, disparando avisos y alertas operativas ante los hitos críticos:
   - `< 20 min`: SLA 1ª Notificación a Dirección (SMS/Email).
   - `45 min`: 1er Escalado Telefónico obligatorio al siguiente nivel de proveedores/resolutores N2/N3 y convocatoria de reunión de alineación.
   - `+1 hora adicional (105 min)`: 2º Escalado Telefónico a estamentos superiores.
   - Regla de Oro: Ejecución obligatoria por canal telefónico para SL1.
3. **Gobernanza de Workarounds y Bloqueo de Desescaladas Indebidas**: Aplicación taxativa de la Regla de Oro: *"Un workaround NO reduce automáticamente la severidad del ticket"*. La consola debe detectar la aplicación de workarounds o mitigaciones provisionales, verificar su estado de autorización por Customer & Service Ops (IM-CSO) y **bloquear activamente** cualquier desescalada o cierre prematuro en la interfaz hasta que se verifique la erradicación total del impacto en producción.
4. **Gobernanza RACI y War Room Virtual**: Reflejo claro de roles (Incident Manager como Responsable [R] y Customer & Service Ops [IM-CSO] como Aprobador [A]), integración de enlaces directos a matrices de contacto (GRIAL/Confluence) y visualización del Reporte de Emergencia normalizado en 4 bloques.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Detección y Análisis de Discrepancias con Métricas Cuantitativas Exactas (Priority: P1) 🎯 MVP

Como Incident Manager en guardia de emergencias, quiero que la consola identifique de forma inmediata cada ticket con discrepancia de severidad (ej. registrado en Remedy como P3/Media pero que realmente califica como SL1/P1 o SL2/P2) y exhiba la métrica cuantitativa exacta del proceso crítico vulnerado, para fundamentar el triaje técnico y corregir la subescalación en Remedy sin margen de error.

**Why this priority**: Evita la invisibilidad de emergencias críticas mal tipificadas en el primer nivel (N1/Service Desk) que ponen en riesgo la facturación, los frontales de venta o la provisión masiva de Orange.

**Independent Test**: Cargar una incidencia con discrepancia (ej. `INC000004152079` o `INC000004169386`) y comprobar que la interfaz despliega un panel destacado con:
- Severidad Remedy original vs Severidad Real ITIL/Orange.
- Nombre del Proceso Crítico afectado.
- Umbral numérico exacto superado (ej. *"Facturación y Cobros: >3h sin tarificación online o ventana +/-3 días ciclo"*).
- Métrica estimada de impacto y justificación técnica objetiva.

**Acceptance Scenarios**:

1. **Given** un catálogo de incidencias con un ticket catalogado en Remedy como "Media" pero cuyo texto y sistemas evidencian fallo en ciclo de facturación (ej. `INC000004152079`), **When** el Incident Manager visualiza la incidencia en la consola, **Then** la tarjeta resalta con borde de alerta roja, insignia "⚠️ Discrepancia Crítica (Subescalación)", y un bloque de datos que contrasta: "Remedy: Media" frente a "Emergencia Real: SL1 / P1", indicando el umbral exacto: *"Facturación y Cobros: ventana ±3 días de ciclo comercial"*.
2. **Given** una incidencia que afecta a Frontales/CRM en sede comercial (ej. `INC000004169386`), **When** se examina en la consola, **Then** el sistema presenta el proceso *"Atención al Cliente / Provisión"* y detalla el umbral: *"Desviación >20% en 30 min en Frontales o bloqueo de consulta de parque/clientes"*.
3. **Given** el panel de KPIs superiores, **When** existen tickets discrepantes, **Then** el contador de "Subescalaciones / Discrepancias" muestra la cifra exacta en color ámbar/rojo con desglose de cuántas corresponden a SL1 y cuántas a SL2.

---

### User Story 2 - Cronometraje y Control de Tiempos de Escalado Telefónico (45 min y +1h) (Priority: P1) 🎯 MVP

Como Incident Manager, quiero controlar visualmente los minutos transcurridos desde la apertura de cada incidente crítico y recibir alertas dinámicas al cumplirse la ventana de 45 minutos y la ventana de +1 hora adicional, recordando la obligatoriedad del canal telefónico y los estamentos a convocar según la gobernanza de Orange.

**Why this priority**: El protocolo de escalado de emergencias de Orange establece que la falta de avances técnicos a los 45 min obliga a un escalado telefónico a niveles resolutores superiores; el retraso en este escalado prolonga innecesariamente el tiempo medio de recuperación (MTTR).

**Independent Test**: Visualizar una incidencia con tiempo transcurrido superior a 45 minutos y verificar que el cronómetro se marca en estado de alerta ("🚨 1er Escalado Telefónico Requerido"), mostrando el estamento objetivo, y pasando a alerta crítica superior ("🚨 2º Escalado Requerido a Estamentos Superiores") si supera los 105 minutos.

**Acceptance Scenarios**:

1. **Given** una incidencia SL1 abierta hace menos de 20 minutos, **When** el Incident Manager observa su cronómetro, **Then** el reloj muestra el conteo en verde/neutro con el recordatorio: *"SLA 1ª Notificación a Dirección: < 20 min"* y cuenta atrás a la siguiente actualización obligatoria (cada 60 min).
2. **Given** una incidencia SL1 abierta hace 52 minutos sin registro de solución, **When** se consulta en la consola, **Then** el badge temporal parpadea en ámbar/rojo con el mensaje: *"⚠️ 45 min rebasados (+7 min): 1er Escalado Telefónico OBLIGATORIO a proveedores/resolutores N2/N3 y convocatoria de alineación"*.
3. **Given** una incidencia SL1 abierta hace más de 105 minutos (ej. 130 min o casos históricos de varios días), **When** se presenta en la consola, **Then** el badge temporal indica: *"🚨 2º Escalado Requerido a Estamentos Superiores (Dirección técnica vía IM-CSO)"*, indicando explícitamente: *"Canal: Vía Telefónica obligatoria (Regla de Oro)"*.
4. **Given** la consola en ejecución continua, **When** el reloj del sistema avanza en tiempo real, **Then** los cronómetros de las tarjetas se actualizan minuto a minuto sin necesidad de recargar la página.

---

### User Story 3 - Gobernanza de Workarounds y Bloqueo de Desescaladas Indebidas (Priority: P1)

Como Incident Manager y garante de la continuidad de negocio, quiero que la consola identifique la presencia de soluciones temporales (workarounds) en los incidentes, exhiba su estatus de autorización por Customer & Service Ops (IM-CSO) y bloquee en la interfaz cualquier intento de desescalada o cierre mientras el impacto persista, aplicando la Regla de Oro institucional.

**Why this priority**: La desescalada prematura por aplicación de un parche temporal es una de las causas principales de recurrencia de caídas críticas y vulneración de SLAs de cara a Dirección.

**Independent Test**: Comprobar una incidencia que tenga un workaround aplicado o propuesto en su diagnóstico técnico; verificar que el badge de gobernanza muestra el estado de aprobación por IM-CSO y que la interfaz prohíbe y bloquea explícitamente rebajar la prioridad a P3 o cerrar el ticket si no existe validación de erradicación completa.

**Acceptance Scenarios**:

1. **Given** un ticket con mitigación técnica provisional activa (ej. script de contingencia o enrutamiento secundario), **When** el Incident Manager revisa la tarjeta, **Then** la consola muestra el bloque *"Gobernanza de Workaround: Activo / En Evaluación"* e indica el estatus de aprobación de Customer & Service Ops (`Pendiente Aprobación IM-CSO` o `Autorizado IM-CSO`).
2. **Given** una incidencia SL1 con workaround aplicado pero sin erradicación de causa raíz, **When** se examinan las acciones de gestión, **Then** la consola muestra de manera visible un candado/banner de restricción: *"🔒 Desescalada Bloqueada: La severidad SL1 no se puede desescalar mediante workaround temporal sin erradicación total del impacto (Regla de Oro Orange)"*.
3. **Given** el panel de KPIs superiores, **When** hay incidencias con workarounds pendientes de validación formal, **Then** se exhibe un indicador específico *"Workarounds Pendientes CSO"* que cuantifica los casos en espera de autorización.

---

### User Story 4 - Consola Operativa en Tiempo Real con Reporte Normalizado de 4 Bloques (Priority: P2)

Como Incident Manager, quiero desplegar de forma interactiva el Reporte de Emergencia normalizado en 4 bloques de Orange Tech Operations para cualquier ticket activo, así como copiar dicho reporte en texto estructurado en 1 clic para enviarlo a los canales de crisis y comités de seguimiento.

**Why this priority**: Estandariza la comunicación operativa interna entre el Incident Manager, los equipos de soporte N2/N3 y el CSO, ahorrando tiempo en la generación manual de actas de situación.

**Independent Test**: Abrir la vista de una incidencia en la consola, hacer clic en "Desplegar Reporte de Emergencia", revisar los 4 bloques estructurados (Clasificación, Comunicaciones/SLAs, Plan de Acción/Workarounds, Estado de Escalado) y pulsar "Copiar Reporte", comprobando que el portapapeles contiene el formato exacto de la skill `orange-it-emergency-management`.

**Acceptance Scenarios**:

1. **Given** una incidencia activa en la consola, **When** el usuario activa la pestaña o botón "Reporte de Emergencia", **Then** se despliegan de forma nítida y legible los 4 bloques:
   - `[1] Clasificación del Ticket`: Severidad + Umbral superado.
   - `[2] Estado de Comunicaciones y SLAs`: Minutos transcurridos, SLA 1ª notificación y frecuencia.
   - `[3] Plan de Acción y Gobernanza de Workarounds`: Diagnóstico, rollback PaP, estado del workaround y Regla de Oro.
   - `[4] Estado de Escalado Telefónico`: Minuto actual vs ventana 45m/+1h y canal telefónico.
2. **Given** el reporte desplegado, **When** el usuario pulsa "Copiar Reporte de Emergencia", **Then** el sistema traslada el informe completo con feedback visual de copia ("¡Reporte de Emergencia copiado al portapapeles!").

---

### User Story 5 - Panel de Mandos RACI y Enlaces a Matrices de Contacto (Priority: P3)

Como Incident Manager en guardia, quiero tener visible en la consola la matriz de responsabilidades RACI aplicable (IM como Responsable, IM-CSO como Aprobador) y accesos directos o referencias a las matrices de escalado corporativas (GRIAL para Orange/Jazztel y Confluence para MasMóvil/KRT), para localizar inmediatamente los contactos resolutores durante la crisis.

**Why this priority**: En situaciones de emergencia bajo estrés operativo, el operador no debe perder tiempo buscando en qué repositorio documental se encuentran las extensiones telefónicas de guardia de cada aplicativo.

**Independent Test**: Verificar que en la cabecera operativa o barra lateral de la consola existen accesos y referencias explícitas a las matrices de escalado (GRIAL y Confluence) y la descripción del flujo RACI oficial.

**Acceptance Scenarios**:

1. **Given** la cabecera de la consola de emergencias, **When** el usuario consulta el botón o tooltip de "Protocolo & Contactos", **Then** se despliega una ficha rápida con la matriz RACI (IM vs IM-CSO) y las indicaciones para consultar contactos en GRIAL (entorno Orange) y Confluence (entorno MasMóvil).

---

## Edge Cases

- **Tiempo de apertura no parseable o ausente**: Si la fecha de apertura en Remedy viene corrupta o vacía, la consola debe indicar *"Tiempo: Desconocido (Requiere auditoría manual en Remedy)"* y aplicar el principio de precaución clasificando el escalado como prioritario.
- **Tiempos de apertura extremadamente antiguos (>10 días)**: En tickets históricos o de tratamiento prolongado que sigan abiertos en Remedy, el tiempo debe formatearse en días y horas legibles (ej. `"20d 19h 53m"` en lugar de miles de minutos en bruto) manteniendo la etiqueta de escalado superior vencido.
- **Ausencia de síntesis de Epsilon IA**: Si el servicio de IA local está apagado o no responde, la consola debe basar su triaje en los metadatos estructurados del ticket (título, descripción, grupo asignado, impacto Remedy) sin bloquear la operativa de la consola.
- **Desconexión temporal del backend local (`serve_app.py`)**: Si una llamada de refresco falla por red o permisos, la consola debe mantener en pantalla los datos de la última sincronización válida, poner el indicador de conexión en color rojo ("Desconectado / Modo Caché") y permitir al operador seguir copiando reportes y prompts sin perder datos.
- **Conflicto de marcas en procesos críticos**: Si una incidencia afecta a plataformas compartidas entre Orange y Jazztel, la consola debe priorizar los umbrales de mayor criticidad y recordar el escalado simultáneo en paralelo a todos los grupos involucrados.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: La consola DEBE operar en la ruta dedicada `/dashboards/incident-manager-monitor/`, manteniendo su aislamiento absoluto del portal general público (`dashboards/portal/index.html`).
- **FR-002**: La consola DEBE calcular y mostrar para cada incidencia activa de alta prioridad la **discrepancia cuantitativa exacta**, comparando la prioridad nominal de Remedy frente a la prioridad ITIL real (SL1/P1 o SL2/P2).
- **FR-003**: La consola DEBE asociar cada incidencia con discrepancia a uno de los **6 Procesos Críticos de Negocio** de Orange (Atención al Cliente, Ventas, Portabilidad, Prepago, Provisión, Facturación y Cobros) o Infraestructura/O&M, exhibiendo el **umbral cuantitativo específico** superado.
- **FR-004**: La consola DEBE implementar un **motor de cronometraje en vivo** que calcule los minutos transcurridos desde la fecha de apertura (`fecha_apertura`) de cada incidencia.
- **FR-005**: La consola DEBE evaluar y clasificar automáticamente el estado del **SLA de 1ª Notificación a Dirección (< 20 minutos)** como "Cumplido / En Tiempo" o "⚠️ Vencido".
- **FR-006**: La consola DEBE controlar el **Hito de 45 minutos** desde la apertura: si transcurren $\ge$ 45 min sin solución, la tarjeta DEBE mostrar una alerta prominente indicando que el **1er Escalado Telefónico a proveedores/resolutores N2/N3 es obligatorio**.
- **FR-007**: La consola DEBE controlar el **Hito de +1 hora adicional ($\ge$ 105 minutos)**: si transcurren $\ge$ 105 min, la tarjeta DEBE alertar que el **2º Escalado Telefónico a Estamentos Superiores** (a través de IM-CSO) es obligatorio.
- **FR-008**: La consola DEBE estipular expresamente en las alertas de escalado la **obligatoriedad de la vía telefónica** (Regla de Oro de Emergencias Orange).
- **FR-009**: La consola DEBE detectar si el ticket cuenta con una solución temporal (*workaround*) o parche de contención y reflejar su estatus de gobernanza: `Sin Workaround`, `Pendiente Aprobación IM-CSO`, `Autorizado IM-CSO`.
- **FR-010**: La consola DEBE **bloquear en la interfaz** cualquier desescalada o cierre indebido si existe un workaround activo no erradicado o no autorizado por IM-CSO, mostrando un banner de bloqueo con la Regla de Oro aplicable.
- **FR-011**: La consola DEBE proveer un visualizador interactivo del **Reporte de Emergencia normalizado en 4 bloques** ([1] Clasificación, [2] Estado de Comunicaciones/SLAs, [3] Plan de Acción/Workarounds, [4] Estado de Escalado Telefónico).
- **FR-012**: La consola DEBE ofrecer un botón de acción rápida para **"Copiar Reporte de Emergencia"** listo para enviar por canales de mensajería/correo de crisis.
- **FR-013**: La consola DEBE mantener la funcionalidad de visualización y copia del prompt para el agente `incident-reporter` (Apertura, Seguimiento, Cierre) y el asistente de ingesta de redacciones ($\le$ 90 palabras completo, $\le$ 30 palabras breve).
- **FR-014**: El panel superior de KPIs DEBE incorporar contadores actualizados en tiempo real:
  - Incidencias Activas SL1 (Críticas).
  - Incidencias Activas SL2 (Altas).
  - Total Discrepancias / Subescalaciones detectadas.
  - Alertas de Escalado Telefónico Requerido ($\ge$ 45 min).
  - Workarounds Pendientes de Aprobación CSO.
  - Pendientes de Redacción Ejecutiva de Agente.
- **FR-015**: La consola DEBE ofrecer auto-refresco configurable (Manual, 30s, 60s) con actualización reactiva por temporizador local para que los cronómetros de minutos no dependan exclusivamente de peticiones HTTP.
- **FR-016**: La consola DEBE incluir una sección o modal con la matriz de responsabilidades **RACI** (Incident Manager como Responsable, Customer & Service Ops como Aprobador) y las referencias documentales de matrices de contacto (GRIAL y Confluence).
- **FR-017**: Los endpoints de soporte en `serve_app.py` DEBEN suministrar el catálogo estructurado con los campos de emergencias calculados (`reporte_emergencia`, métricas de SLA, minutos transcurridos, estado de escalado y gobernanza de workaround).

---

### Key Entities

- **`EmergencyIncident`**: Registro de incidencia enriquecido para la consola de emergencias.
  - Atributos: `id`, `titulo`, `sistemas`, `prioridad_original` (Remedy), `severidad_calculada` (SL1..SL4), `es_discrepancia` (bool), `proceso_critico` (string), `umbral_violado` (string), `fecha_apertura` (datetime), `minutos_transcurridos` (int), `sla_notificacion_vencido` (bool), `estado_escalado` (`OK` | `ESCALADO_45M_REQUERIDO` | `ESCALADO_SUPERIOR_REQUERIDO`), `workaround_estado` (`NINGUNO` | `PENDIENTE_CSO` | `AUTORIZADO_CSO`), `desescalada_bloqueada` (bool), `reporte_emergencia_texto` (string).
- **`EscalationTimeline`**: Estructura de control temporal de la emergencia.
  - Atributos: `minutos_apertura`, `tiempo_formateado` (ej. "48 min" o "2d 4h"), `fase_actual` (`PRIMERA_NOTIFICACION` | `TRATAMIENTO_INICIAL` | `VENTANA_45M` | `VENTANA_SUPERIOR`), `canal_obligatorio` ("Telefónico"), `estamento_destino` (string).
- **`WorkaroundGovernanceState`**: Estructura de control de soluciones provisionales.
  - Atributos: `detectado` (bool), `descripcion_mitigacion` (string), `autorizado_cso` (bool), `impacto_erradicado` (bool), `permite_desescalada` (bool), `motivo_bloqueo` (string).
- **`EmergencyCockpitKPIs`**: Métricas operativas mostradas en la consola.
  - Atributos: `total_activas`, `total_sl1`, `total_sl2`, `total_discrepancias`, `escalados_45m_pendientes`, `workarounds_pendientes_cso`, `redacciones_pendientes`, `ultima_sincronizacion`.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de las incidencias activas clasificadas como SL1/P1 con más de 45 minutos desde su apertura muestran la alerta de "1er Escalado Telefónico Requerido" en la consola sin intervención manual.
- **SC-002**: El 100% de los incidentes que presenten una discrepancia entre la prioridad Remedy y la matriz Orange exhiben el Proceso Crítico y el umbral cuantitativo específico superado.
- **SC-003**: Cero (0%) desescaladas indebidas permitidas en la consola cuando exista un workaround activo sin autorización formal de Customer & Service Ops (IM-CSO) o sin confirmación de erradicación total del impacto.
- **SC-004**: El tiempo de despliegue y copia del Reporte de Emergencia normalizado de 4 bloques es inferior a 3 segundos para el operador.
- **SC-005**: Los cronómetros de tiempo transcurrido en pantalla se actualizan con una precisión temporal de $\pm 1$ segundo en el cliente web.
- **SC-006**: Se preserva el 100% de aislamiento visual de la herramienta respecto al portal general (`dashboards/portal/index.html`).

---

## Assumptions

- **Integración con Motor de Notificaciones**: La consola se alimenta de la salida generada por `evaluate_incident_notifications.py` y `high_priority_notifications.json`, la cual ya incorpora el cálculo de severidades SL1/SL2, los umbrales de los 6 procesos críticos y la generación del texto del reporte de emergencia en 4 bloques.
- **Canal Telefónico**: La consola actúa como sistema de alerta y orquestación visual; las llamadas telefónicas de escalado son efectuadas por el Incident Manager a través de los sistemas de telefonía y guardias de Orange.
- **Gobernanza RACI**: Customer & Service Ops (IM-CSO) es la única entidad corporativa con potestad para autorizar workarounds y validar la desescalada o cierre de emergencias SL1.
- **Compatibilidad Web**: La interfaz se ejecuta en navegadores corporativos estándar (Google Chrome, Microsoft Edge) con soporte nativo de Web API (Timers, Clipboard, Fetch).

