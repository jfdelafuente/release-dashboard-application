# Data Model: Consola Operativa de Emergencias Orange en Tiempo Real (014-emergency-operations-console)

**Feature**: `014-emergency-operations-console`  
**Date**: 2026-10-29  
**Status**: Draft  

---

## 1. Diagrama Conceptual de Entidades

```
┌─────────────────────────────────────────────────────────────┐
│                   EmergencyCockpitState                     │
│  - kpis: EmergencyCockpitKPIs                                │
│  - incidents: List[EmergencyIncident]                       │
│  - raciMatrix: RACIGovernanceInfo                           │
└──────────────────────────────┬──────────────────────────────┘
                               │ 1..*
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                     EmergencyIncident                       │
│  - id: String ("INC000004152079")                           │
│  - titulo: String                                           │
│  - sistemas: String                                         │
│  - prioridad_original: String ("Media")                     │
│  - severidad_calculada: String ("SL1" | "SL2")              │
│  - es_discrepancia: Boolean                                 │
│  - fecha_apertura: String ("08/10/2026 13:00 a")            │
│  - apertura_epoch_ms: Number (1791464400000)                │
│  - minutos_desde_apertura: Number                           │
│  - tiempo_formateado: String ("48 min" | "2d 4h")           │
│  - discrepancia: DiscrepancyMetric                          │
│  - timeline: EscalationTimeline                             │
│  - workaround: WorkaroundGovernance                         │
│  - reporte_emergencia: String                               │
│  - mensajes_ejecutivos: IncidentExecutiveMessages           │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Entidades Principales

### 2.1 `EmergencyIncident`
Representa una incidencia mayor bajo supervisión operativa en la consola de emergencias.

| Campo | Tipo | Obligatorio | Descripción |
| :--- | :--- | :---: | :--- |
| `id` | `String` | Sí | Código único de ticket Remedy (ej. `"INC000004152079"`). |
| `titulo` | `String` | Sí | Título limpio y resumido del incidente. |
| `sistemas` | `String` | Sí | Aplicaciones o plataformas afectadas (ej. `"SOP_TMC_EXCALIBUR"`). |
| `prioridad_original`| `String` | Sí | Severidad registrada en Remedy (`"Crítica"`, `"Alta"`, `"Media"`, `"Baja"`). |
| `severidad_calculada`| `Enum` | Sí | Nivel ITIL/Orange asignado (`"SL1"`, `"SL2"`, `"SL3"`, `"SL4"`). |
| `es_discrepancia` | `Boolean` | Sí | `true` si la prioridad Remedy difiere de la calculada (subescalación). |
| `fecha_apertura` | `String` | Sí | Cadena original de apertura en Remedy. |
| `apertura_epoch_ms` | `Number` | Sí | Timestamp UTC en milisegundos para cálculo del cronómetro reactivo. |
| `minutos_desde_apertura` | `Number` | Sí | Minutos totales transcurridos calculados en tiempo real. |
| `discrepancia` | `DiscrepancyMetric` | Sí | Detalle cuantitativo del umbral vulnerado. |
| `timeline` | `EscalationTimeline`| Sí | Estado temporal frente a los hitos de escalado telefónico. |
| `workaround` | `WorkaroundGovernance`| Sí | Estado de soluciones provisionales y bloqueo de desescalada. |
| `reporte_emergencia`| `String` | Sí | Texto formateado del reporte en 4 bloques normalizado. |
| `mensajes_ejecutivos`| `Object` | Sí | Redacciones oficiales de agente para `apertura`, `seguimiento`, `cierre`. |

---

### 2.2 `DiscrepancyMetric`
Contiene la métrica cuantitativa objetiva que fundamenta la reclasificación de severidad.

| Campo | Tipo | Obligatorio | Descripción |
| :--- | :--- | :---: | :--- |
| `es_discrepancia` | `Boolean` | Sí | Indica si existe subescalación o tipificación errónea en Remedy. |
| `prioridad_remedy` | `String` | Sí | Valor original registrado en el ticket (ej. `"Media"`). |
| `severidad_itil` | `String` | Sí | Clasificación real según Orange (ej. `"SL1 / P1 - Emergencia Crítica"`). |
| `proceso_critico` | `String` | Sí | Uno de los 6 Procesos Críticos de Negocio o Infraestructura/O&M. |
| `criterio_umbral` | `String` | Sí | Umbral cuantitativo superado (ej. *">3h sin tarificación online"*). |
| `justificacion` | `String` | Sí | Texto descriptivo de la afección sobre el servicio. |

---

### 2.3 `EscalationTimeline`
Estructura de control cronológico para los SLAs de comunicación y protocolos de escalado telefónico.

| Campo | Tipo | Obligatorio | Descripción |
| :--- | :--- | :---: | :--- |
| `minutos_transcurridos` | `Number` | Sí | Minutos exactos desde `fecha_apertura`. |
| `sla_1a_notif_vencido` | `Boolean` | Sí | `true` si `minutos_transcurridos > 20` sin 1ª notificación emitida. |
| `fase_escalado` | `Enum` | Sí | `EN_TIEMPO` (< 45m), `ESCALADO_45M_REQUERIDO` (45m - 104m), `ESCALADO_SUPERIOR_REQUERIDO` (≥ 105m). |
| `requiere_canal_telefonico`| `Boolean` | Sí | Siempre `true` para incidencias SL1 (Regla de Oro). |
| `estamento_convocado` | `String` | Sí | `Proveedores N2/N3` a los 45 min; `Estamentos Superiores vía IM-CSO` a +1h. |
| `frecuencia_updates_min`| `Number` | Sí | Frecuencia de emisión de reportes (60 min o 30 min ante cambios). |

---

### 2.4 `WorkaroundGovernance`
Modelo de control y gobernanza sobre soluciones de contención temporal.

| Campo | Tipo | Obligatorio | Descripción |
| :--- | :--- | :---: | :--- |
| `workaround_detectado` | `Boolean` | Sí | Indica si el ticket menciona mitigación temporal o parche en curso. |
| `estado_gobernanza` | `Enum` | Sí | `SIN_WORKAROUND`, `PENDIENTE_AUTORIZACION_CSO`, `AUTORIZADO_CSO`. |
| `autorizado_cso` | `Boolean` | Sí | `true` si Customer & Service Ops ha aprobado explícitamente el workaround. |
| `impacto_erradicado` | `Boolean` | Sí | `true` si el servicio está 100% normalizado en producción. |
| `desescalada_bloqueada` | `Boolean` | Sí | `true` si el workaround no permite rebajar severidad o cerrar el ticket. |
| `motivo_bloqueo` | `String` | No | Explicación basada en la Regla de Oro institucional de Orange. |

---

### 2.5 `EmergencyCockpitKPIs`
Resumen consolidado en tiempo real exhibido en la cabecera operativa.

| Campo | Tipo | Obligatorio | Descripción |
| :--- | :--- | :---: | :--- |
| `total_activas` | `Number` | Sí | Número total de incidencias SL1 y SL2 activas. |
| `sl1_criticas` | `Number` | Sí | Total de incidentes de severidad SL1. |
| `sl2_altas` | `Number` | Sí | Total de incidentes de severidad SL2. |
| `discrepancias_subescalacion` | `Number` | Sí | Total de tickets con prioridad Remedy inferior a la calculada. |
| `alertas_escalado_45m` | `Number` | Sí | Incidentes que han superado los 45 minutos sin resolución. |
| `alertas_escalado_superior` | `Number` | Sí | Incidentes que han superado los 105 minutos sin resolución. |
| `workarounds_pendientes_cso` | `Number` | Sí | Workarounds aplicados en espera de autorización de IM-CSO. |
| `redacciones_pendientes` | `Number` | Sí | Tickets pendientes de mensaje ejecutivo de agente `incident-reporter`. |
| `ultima_sincronizacion` | `String` | Sí | Timestamp ISO de la última actualización de catálogo. |

---

## 3. Máquinas de Estados y Transiciones

### 3.1 Ciclo Temporal de Escalado Telefónico
```
  [Apertura Ticket]
         │
         ▼
 ┌───────────────┐  minutos < 20
 │ 1ª Notif SLA  ├──────────────────────────────────┐
 └───────┬───────┘                                  │
         │ minutos >= 20                            │
         ▼                                          │
 ┌───────────────┐                                  │
 │ SLA 1ª Vencido│                                  │
 └───────┬───────┘                                  │
         │ minutos >= 45                            │
         ▼                                          │
 ┌──────────────────────────────────────┐           │
 │ 🚨 1er Escalado Telefónico Requerido │           │
 │    (Proveedores / Resolutores N2/N3) │           │
 └───────┬──────────────────────────────┘           │
         │ minutos >= 105 (+1 hora adic.)           │
         ▼                                          │
 ┌──────────────────────────────────────┐           │
 │ 🚨 2º Escalado a Estamentos Sup.     │           │
 │    (Dirección técnica vía IM-CSO)    │           │
 └───────┬──────────────────────────────┘           │
         │                                          │
         ▼ (Erradicación total impacto)             ▼
 ┌──────────────────────────────────────────────────┐
 │                  Cierre / Resuelto               │
 └──────────────────────────────────────────────────┘
```

### 3.2 Gobernanza de Workarounds y Desescalada
```
                    [Ticket SL1 Activo]
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
   [Sin Workaround]                 [Workaround Aplicado]
            │                                 │
            │                                 ▼
            │               ┌───────────────────────────────────┐
            │               │  Gobernanza: PENDIENTE_CSO        │
            │               │  Desescalada: 🔒 BLOQUEADA        │
            │               └─────────────────┬─────────────────┘
            │                                 │ Aprobación IM-CSO
            │                                 ▼
            │               ┌───────────────────────────────────┐
            │               │  Gobernanza: AUTORIZADO_CSO       │
            │               │  Desescalada: 🔒 BLOQUEADA        │
            │               │  (Impacto residual aún activo)    │
            │               └─────────────────┬─────────────────┘
            │                                 │ Erradicación Total
            ▼                                 ▼
 ┌──────────────────────────────────────────────────────────────┐
 │   Desescalada / Cierre Autorizado por IM-CSO                 │
 └──────────────────────────────────────────────────────────────┘
```

---

## 4. Reglas de Validación de Datos

1. **RV-001 (Parseo de Apertura)**: Si `fecha_apertura` contiene sufijo `"a"` o `"p"`, el parser debe interpretar correctamente `a.m.` / `p.m.` o formato 24 horas (`DD/MM/YYYY HH:mm`) para calcular el epoch exacto.
2. **RV-002 (Invariante de Regla de Oro)**: Todo ticket con `severidad_calculada == "SL1"` tiene `requiere_canal_telefonico = true` de forma no anulable.
3. **RV-003 (Invariante de Workaround)**: Si `workaround_detectado == true` y `impacto_erradicado == false`, `desescalada_bloqueada` DEBE ser estrictamente `true`.
4. **RV-004 (Normalización de Redacciones)**: Al persistir mensajes ejecutivos, la versión completa debe normalizarse a un único párrafo cohesionado con longitud $\le$ 90 palabras y la versión breve con longitud $\le$ 30 palabras.

