# Data Model: Sistema de Notificación de Incidencias de Alta Prioridad (012-high-priority-incident-notifications)

**Feature**: `012-high-priority-incident-notifications` | **Date**: 2026-10-26

Este documento define las entidades de datos, esquemas JSON y modelos de estado utilizados por el conversor backend y el componente frontend del sistema de notificaciones.

---

## 1. Entidad: `HighPriorityNotificationsCatalog` (Contrato Envelope)

Archivo persistente: `data/output/high_priority_notifications.json`

```json
{
  "_metadata": {
    "type": "high_priority_notifications",
    "version": "1.0.0",
    "generated_at": "2026-10-26T15:30:00Z",
    "source_file": "data/output/CS-Informe incidencias P1,  P2 y P3 - 2026 - 14 Oct 2026-massive.json",
    "kpis": {
      "total_scanned": 1506,
      "total_high_priority": 14,
      "p1_critical_count": 3,
      "p2_high_count": 11,
      "discrepancies_count": 5
    }
  },
  "data": [
    {
      "id": "INC000004141215",
      "titulo": "Degradación en pasarela de pagos móviles",
      "sistemas": ["PAGOS", "GATEWAY-CORE"],
      "prioridad_original": "Media",
      "prioridad_sugerida": "P1",
      "es_alta_prioridad": true,
      "es_discrepancia": true,
      "estatus": "En Curso",
      "fecha_envio": "14/10/2026 10:15",
      "evaluacion": {
        "impacto": "Alto",
        "impacto_justificacion": "Afectación crítica a transacciones de pago con >50% de fallos.",
        "urgencia": "Alta",
        "urgencia_justificacion": "Incidencia en curso en horario pico productivo.",
        "workaround": "No",
        "sla_objetivo_minutos": 15
      },
      "resumen_ia": {
        "problema": "Incremento de tiempos de respuesta en autorizaciones.",
        "impacto": "Afectación a transacciones durante 25 minutos.",
        "solucion": "Reciclado preventivo del pool y ajuste de timeouts.",
        "bloqueos": "",
        "siguiente_accion": "Seguimiento en comité de cambios."
      },
      "mensajes_ejecutivos": {
        "apertura": {
          "completo": "Apertura INC000004141215 (P1). Se ha detectado una degradación crítica en la pasarela de pagos móviles afectando a transacciones de clientes. El equipo de operaciones investiga la causa y aplica reciclado de conexiones. Próxima actualización en 30 minutos.",
          "breve": "Apertura P1 INC000004141215: Caída en pasarela de pagos móviles. Equipo técnico interviniendo.",
          "conteo_palabras_completo": 36,
          "conteo_palabras_breve": 14
        },
        "seguimiento": {
          "completo": "Seguimiento INC000004141215 (P1). Continúa el aislamiento del fallo en pasarela de pagos. Los tiempos de respuesta comienzan a estabilizarse tras el reciclado de pools. Se mantiene monitorización activa.",
          "breve": "Seguimiento P1 INC000004141215: Parámetros estabilizándose tras reciclado. Monitorización activa.",
          "conteo_palabras_completo": 28,
          "conteo_palabras_breve": 10
        },
        "cierre": {
          "completo": "Cierre INC000004141215 (P1). Servicio de pasarela de pagos completamente restablecido. Pruebas de transacción verificadas al 100%. Se procederá a análisis postmortem formal.",
          "breve": "Cierre P1 INC000004141215: Pasarela de pagos restablecida y operativa normalizada.",
          "conteo_palabras_completo": 23,
          "conteo_palabras_breve": 9
        }
      }
    }
  ]
}
```

---

## 2. Entidad: `NotificationUserState` (Estado en Cliente)

Almacenamiento: `localStorage` bajo `rd_incident_notifications_state_v1`

```json
{
  "INC000004141215": {
    "estado": "comunicada",
    "updated_at": "2026-10-26T15:35:10Z",
    "fase_notificada": "apertura",
    "notas": "Emitido por correo a Dirección de Operaciones"
  },
  "INC000003885040": {
    "estado": "pendiente",
    "updated_at": "2026-10-26T15:30:00Z"
  }
}
```

### Valores de `estado`:
- `pendiente`: Estado inicial por defecto; cuenta activamente para el badge de alertas.
- `comunicada`: El operador ha generado y transmitido la comunicación a los comités.
- `en_seguimiento`: Notificación abierta con monitorización en curso.
- `descartada`: Omitida por el operador (falso positivo o fuera de alcance).

---

## 3. Matriz de Severidad: Esquema de Clasificación

| Campo de Evaluación | Tipo | Valores Posibles | Regla de Derivación |
| :--- | :--- | :--- | :--- |
| `impacto` | Enum | `Alto`, `Medio`, `Bajo` | Basado en alcance de usuarios, servicios críticos y existencia de workaround viable. |
| `urgencia` | Enum | `Alta`, `Media`, `Baja` | Basado en estado del ticket (en curso vs cerrado), horario y sensibilidad temporal. |
| `prioridad_sugerida` | Enum | `P1`, `P2`, `P3`, `P4` | Cruce exacto según tabla de `it-severity-matrix`. |
| `es_alta_prioridad` | Boolean | `true` si P1 o P2 | Disparador del Centro de Notificaciones. |
| `es_discrepancia` | Boolean | `true` si sugerida > ticket | Discrepancia cuando sugerida es más crítica que la nominal. |

