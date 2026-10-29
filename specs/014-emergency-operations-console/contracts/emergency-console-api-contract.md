# Contract: Emergency Console API (`emergency-console-api-contract`)

**Feature**: `014-emergency-operations-console`  
**Protocol**: HTTP / REST  
**Data Format**: JSON (UTF-8)  
**Consumer**: `dashboards/incident-manager-monitor/monitor.js`  
**Provider**: `serve_app.py`  

---

## 1. Endpoints

### 1.1 `GET /api/incident-manager/emergency-cockpit`

Retorna la telemetría consolidada en tiempo real de emergencias activas, estado de SLAs y gobernanza de escalados.

#### Request
* **Method**: `GET`
* **Path**: `/api/incident-manager/emergency-cockpit`
* **Query Parameters**:
  * `only_pending` (opcional, boolean): Si es `true`, filtra únicamente las incidencias pendientes de redacción de agente.
  * `severity` (opcional, string): `"SL1"`, `"SL2"` o `"all"` (default: `"all"`).

#### Response (200 OK)
```json
{
  "_metadata": {
    "version": "1.0.0",
    "generated_at": "2026-10-29T09:00:00Z",
    "server_time": "2026-10-29T09:00:00Z",
    "source_file": "CS-Informe incidencias P1,  P2 y P3 - 2026 - 29 Oct 2026-massive.json"
  },
  "kpis": {
    "total_activas": 12,
    "sl1_criticas": 6,
    "sl2_altas": 6,
    "discrepancias_subescalacion": 11,
    "alertas_escalado_45m": 12,
    "alertas_escalado_superior": 12,
    "workarounds_pendientes_cso": 0,
    "redacciones_pendientes": 0
  },
  "incidents": [
    {
      "id": "INC000004152079",
      "titulo": "INCIFAC-1540 Stihl - Error en facturacion Lego Deporte",
      "sistemas": "SOP_TMC_EXCALIBUR",
      "prioridad_original": "Media",
      "severidad_calculada": "SL1",
      "es_discrepancia": true,
      "fecha_apertura": "08/10/2026 13:00 a",
      "apertura_epoch_ms": 1791464400000,
      "minutos_desde_apertura": 29995,
      "discrepancia": {
        "es_discrepancia": true,
        "prioridad_remedy": "Media",
        "severidad_itil": "SL1 / P1 - Emergencia Crítica",
        "proceso_critico": "Facturación y Cobros",
        "criterio_umbral": "Facturación: >3h sin tarificación online o ventana +/-3 días ciclo",
        "justificacion": "Afectación en proceso crítico de facturación comercial activa sin alternativa viable."
      },
      "timeline": {
        "minutos_transcurridos": 29995,
        "sla_1a_notif_vencido": true,
        "fase_escalado": "ESCALADO_SUPERIOR_REQUERIDO",
        "requiere_canal_telefonico": true,
        "estamento_convocado": "Estamentos Superiores vía IM-CSO",
        "frecuencia_updates_min": 60
      },
      "workaround": {
        "workaround_detectado": false,
        "estado_gobernanza": "SIN_WORKAROUND",
        "autorizado_cso": false,
        "impacto_erradicado": false,
        "desescalada_bloqueada": false,
        "motivo_bloqueo": null
      },
      "reporte_emergencia": "🚨 REPORTE DE EMERGENCIA IT - ORANGE TECH OPERATIONS\n...",
      "mensajes_ejecutivos": {
        "apertura": {
          "completo": "Se declara incidencia crítica P1 (INC000004152079)...",
          "breve": "Apertura P1 (INC000004152079)...",
          "generado_por_agente": true
        },
        "seguimiento": {
          "completo": "Seguimiento de la incidencia P1 (INC000004152079)...",
          "breve": "Seguimiento P1 (INC000004152079)...",
          "generado_por_agente": true
        },
        "cierre": {
          "completo": "Cerrada la incidencia crítica P1 (INC000004152079)...",
          "breve": "Cierre P1 (INC000004152079)...",
          "generado_por_agente": true
        }
      }
    }
  ]
}
```

---

### 1.2 `GET /api/incident-manager/pending` (Extensión Compatible)

Mantiene compatibilidad con las aplicaciones existentes enriqueciendo cada registro de la lista `incidents` con los metadatos de emergencia:
- `fecha_apertura`
- `apertura_epoch_ms`
- `minutos_desde_apertura`
- `requiere_escalado_telefonico`
- `escalado_estamentos_superiores`
- `reporte_emergencia`
- `discrepancia_proceso`
- `discrepancia_criterio`

---

## 2. Manejo de Errores

| Código HTTP | Motivo | Estructura de Respuesta |
| :---: | :--- | :--- |
| `500 Internal Server Error` | Fallo al leer o parsear `high_priority_notifications.json` | `{"error": "Error interno cargando catálogo de emergencias", "details": "..."}` |
| `503 Service Unavailable` | Archivo de notificaciones no disponible temporalmente | `{"error": "Catálogo no generado", "suggestion": "Ejecutar evaluate_incident_notifications.py"}` |

---

## 3. SLA y Rendimiento

* **Latencia objetivo**: p95 $< 100\text{ ms}$ en peticiones locales a `serve_app.py`.
* **Caché en servidor**: Validación rápida de `mtime` del fichero JSON para evitar recálculos si no ha habido ingesta de un nuevo CSV.

