# Research: Consola Operativa de Emergencias Orange en Tiempo Real (014-emergency-operations-console)

**Feature**: `014-emergency-operations-console`  
**Date**: 2026-10-29  
**Status**: Completed  

---

## 1. Cronometraje de Emergencias y Tiempos de Escalado en Tiempo Real

### Contexto y Problema
El protocolo operativo de Orange Tech Operations ([`.agents/skills/orange-it-emergency-management/SKILL.md`](../../.agents/skills/orange-it-emergency-management/SKILL.md)) estipula plazos taxativos:
1. **< 20 minutos**: SLA de 1ª Notificación a Dirección (SMS/Email).
2. **45 minutos**: Si no existen avances técnicos significativos, el Incident Manager (IM) debe ejecutar de forma obligatoria un **1er escalado telefónico** a proveedores/resolutores N2/N3 y convocar reunión de alineación.
3. **+1 hora adicional (105 min totales)**: Si continúa la falta de resolución, se debe ejecutar un **2º escalado telefónico** a estamentos superiores.
4. **Regla de Oro**: La vía de escalado en emergencias SL1 debe ser siempre telefónica.

### Decisiones Técnicas
* **Motor de Tiempo en Cliente (Anti-Drift)**:
  - Las fechas de apertura de tickets en Remedy (`fecha_apertura`, ej. `"08/10/2026 13:00 a"` o `"29/10/2026 08:15"`) se parsean a timestamps epoch UTC en la carga inicial.
  - El cálculo de minutos transcurridos en cliente se efectúa mediante `Math.floor((Date.now() - aperturaTimestamp) / 60000)`.
  - Un temporizador global en `setInterval(..., 10000)` (cada 10 segundos) recalcula y actualiza los cronómetros visibles sin saturar la CPU ni depender de peticiones de red continuas.
* **Formateo Humano de Tiempos**:
  - Para duraciones `< 60 min`: formato `"XX min"`.
  - Para duraciones entre 1h y 24h: formato `"Xh Ym"`.
  - Para duraciones `> 24h`: formato `"Xd Yh"` con aviso de ticket de larga duración.
* **Estados Visuales del Cronómetro**:
  - **Estado Normal (`< 20 min`)**: Verde/Neutro con indicación de SLA 1ª Notificación en curso.
  - **Estado Tratamiento (`20 min - 44 min`)**: Azul/Cian, frecuencia de actualización obligatoria cada 60 min.
  - **Alerta 1er Escalado (`45 min - 104 min`)**: Ámbar pulsante con mensaje: *"⚠️ 45 min rebasados: 1er Escalado Telefónico OBLIGATORIO a resolutores N2/N3"*.
  - **Alerta Crítica 2º Escalado (`≥ 105 min`)**: Rojo de alta visibilidad: *"🚨 2º Escalado Requerido a Estamentos Superiores (Vía Telefónica obligatoria)"*.

### Alternativas Consideradas y Rechazadas
* *Polling del backend cada segundo*: Rechazado. Genera sobrecarga innecesaria en `serve_app.py` y Nginx; el cliente web puede calcular la diferencia temporal con total precisión matemática a partir de la fecha de apertura original.
* *Dependencia de librerías externas pesadas (Moment.js/Day.js)*: Rechazado. El parseo de fechas Remedy y la aritmética de minutos se resuelve de forma óptima con funciones nativas en JS de menos de 40 líneas.

---

## 2. Detección y Visualización de Discrepancias con Métricas Cuantitativas Exactas

### Contexto y Problema
En el triaje inicial de Service Desk / Remedy, múltiples incidencias de alto impacto son registradas erróneamente con prioridad "Media" o "Baja". El sistema actual marcaba "Subescalación", pero no detallaba la métrica exacta vulnerada ni el umbral de los 6 Procesos Críticos.

### Decisiones Técnicas
* **Modelo Cuantitativo de los 6 Procesos Críticos de Negocio**:
  Se estructuran los umbrales objetivos definidos en `orange-it-emergency-management`:
  1. **Atención al Cliente (ATC)**: Desviación >20% en 30 min en Frontales/CRM; colapso >20% de llamadas durante 1h; caída total del IVR.
  2. **Ventas**: Impacto >30% en volumen de operaciones; <15% de ventas diarias vs promedio 4 días.
  3. **Portabilidad**: Fallo de inicio a las 2:00 AM; indisponibilidad o retraso >2h entre 8:00 AM y 8:00 PM.
  4. **Prepago**: Recargas o altas con >10% de errores o >30 min sin operaciones.
  5. **Provisión**: Indisponibilidad 100% renovación beneficios; Órdenes Móvil >20% errores o 100% error >10 min; Órdenes Fijo >30% errores o 100% error >30 min.
  6. **Facturación y Cobros**: Desviación >1 día en batch; >3h sin tarificación online; ventana crítica ±3 días de ciclo.
* **Componente de Contraste de Discrepancia**:
  En cada tarjeta de ticket discrepante, se renderiza una tabla visual de triaje:
  - Columna A: *Prioridad Remedy*: "Media" (o "Baja").
  - Columna B: *Severidad Real ITIL*: "SL1 / P1 - Emergencia Crítica".
  - Fila inferior: *Proceso Crítico y Criterio Numérico*: Texto exacto del umbral superado.

---

## 3. Gobernanza de Workarounds y Bloqueo de Desescaladas Indebidas

### Contexto y Problema
La Regla de Oro institucional establece taxativamente:
> *"La aplicación de cualquier workaround o parche temporal requiere siempre la autorización explícita de Customer & Service Ops (IM-CSO). Un workaround NO reduce automáticamente la severidad del ticket. Una Emergencia solo se da por resuelta cuando el impacto sobre el negocio o servicio ha desaparecido por completo."*

### Decisiones Técnicas
* **Detección Automática y Marcaje de Gobernanza**:
  - Se analiza el diagnóstico técnico y el campo `workaround_detectado` generado por `evaluate_incident_notifications.py`.
  - Estados posibles:
    1. `SIN_WORKAROUND`: No se registra mitigación temporal.
    2. `WORKAROUND_PENDIENTE_CSO`: Mitigación aplicada/propuesta sin confirmación formal de CSO.
    3. `WORKAROUND_AUTORIZADO_CSO`: Mitigación temporal autorizada formalmente por IM-CSO.
* **Mecanismo de Bloqueo Visual y Lógico**:
  - Si un ticket SL1 tiene un workaround activo, la interfaz **deshabilita cualquier control de desescalada** (cambio de severidad a P2/P3 o marcado como resuelto).
  - Se muestra un banner distintivo con icono de candado:
    *"🔒 Desescalada Bloqueada: La severidad SL1 no se puede desescalar mediante workaround temporal sin erradicación total del impacto (Regla de Oro Orange)"*.
  - Si no está autorizado por CSO, se muestra un badge de alerta parpadeante indicando la necesidad de validación inmediata por IM-CSO.

---

## 4. Consola Operativa en Tiempo Real y Despliegue del Reporte de Emergencia

### Contexto y Problema
El Incident Manager necesita emitir reportes estandarizados a comités de crisis y canales de Teams sin tener que redactar a mano el estado de comunicaciones y escalados.

### Decisiones Técnicas
* **Estructura Normalizada de 4 Bloques**:
  - `[1] Clasificación del Ticket`: SL1/SL2, proceso crítico y justificación.
  - `[2] Estado de Comunicaciones y SLAs`: Minutos transcurridos, 1ª notificación y frecuencia.
  - `[3] Plan de Acción y Gobernanza de Workarounds`: Diagnóstico, rollback PaP, estado del workaround y Regla de Oro.
  - `[4] Estado de Escalado Telefónico`: Minuto actual vs ventana 45m / +1h y canal telefónico obligatorio.
* **Acción Rápida en 1 Clic**:
  - Botón "Desplegar Reporte de Emergencia" que expande el bloque visualmente con estilos terminal/monospaced.
  - Botón "Copiar Reporte de Emergencia" que utiliza la Clipboard API nativa y proporciona feedback accesible ("¡Reporte de Emergencia copiado al portapapeles!").
* **Panel RACI y Referencias de Contactos**:
  - Incorporar en la cabecera un modal/drawer de gobernanza operativa que documente:
    - Incident Manager (IM): Responsable (R).
    - Customer & Service Ops (IM-CSO): Aprobador (A).
    - Acceso a matrices de guardia en GRIAL (Orange) y Confluence (MasMóvil).

---

## 5. Arquitectura de Integración Backend (`serve_app.py`)

### Decisiones Técnicas
* **Ampliación de Endpoint `/api/incident-manager/pending`**:
  - Mantener compatibilidad hacia atrás agregando campos enriquecidos:
    `minutos_desde_apertura`, `sla_primera_notificacion_vencido`, `requiere_escalado_telefonico`, `escalado_estamentos_superiores`, `workaround_estado`, `reporte_emergencia`.
* **Nuevo Endpoint `/api/incident-manager/emergency-cockpit`**:
  - Devuelve el conjunto consolidado de emergencias activas, KPIs globales de escalado y estado de workarounds sin requerir transformaciones pesadas en el navegador.
* **Degradación Elegante**:
  - Si el endpoint dinámico no responde (entornos con servidor estático puro), el frontend lee directamente `/data/output/high_priority_notifications.json` y ejecuta el cronometraje en vivo a partir de `fecha_apertura`.

