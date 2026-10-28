# Contract: Incident Manager Monitor API

**Feature**: `013-incident-manager-monitor` | **Date**: 2026-10-28  
**Spec Reference**: [`specs/013-incident-manager-monitor/spec.md`](../spec.md)

Este contrato formaliza las interfaces HTTP provistas por `serve_app.py` para soportar el Frontal de Monitorización del Incident Manager.

---

## 1. `GET /api/incident-manager/pending`

Devuelve el listado procesado de incidencias activas de alta prioridad que están pendientes de redacción de agente, junto con los KPIs globales calculados.

### Request
- **Method**: `GET`
- **Path**: `/api/incident-manager/pending`
- **Headers**:
  - `Accept: application/json`

### Success Response (`200 OK`)
```json
{
  "kpis": {
    "total_active": 15,
    "completed_count": 14,
    "pending_count": 1,
    "p1_count": 6,
    "p2_count": 9,
    "discrepancies_count": 14,
    "generated_at": "2026-10-28T08:52:13Z",
    "source_file": "CS-Informe incidencias P1,  P2 y P3 - 2026 - 28 Oct 2026-massive.json"
  },
  "pending_incidents": [
    {
      "id": "INC000004168775",
      "titulo": "INDISPONIBILIDAD // MIDDLEWARE // SL1",
      "sistemas": ["SPAIN ALMACENAMIENTO"],
      "prioridad_original": "Crítica",
      "prioridad_sugerida": "P2",
      "es_alta_prioridad": true,
      "es_discrepancia": false,
      "estatus": "Pendiente",
      "fecha_envio": "27/10/2026 18:21 a",
      "evaluacion": {
        "proceso": "Sistemas Core",
        "criterio": "SL2 Mayor: Degradación funcional o afectación en sede sin indisponibilidad global",
        "impacto": "Alto",
        "impacto_justificacion": "Afectación crítica o corte global sobre el servicio principal sin alternativa viable.",
        "urgencia": "Baja",
        "urgencia_justificacion": "Incidencia de baja sensibilidad temporal o sin bloqueo activo.",
        "workaround": "Desconocido",
        "sla_objetivo_minutos": 60
      },
      "resumen_ia": null,
      "tiene_epsilon": false,
      "prompts": {
        "apertura": "Actúa como el agente incident-reporter...",
        "seguimiento": "Actúa como el agente incident-reporter...",
        "cierre": "Actúa como el agente incident-reporter..."
      }
    }
  ]
}
```

---

## 2. `POST /api/incident-manager/save-message`

Registra en el almacén persistente `data/agent_executive_messages.json` una redacción oficial del agente y desencadena la reevaluación del catálogo de notificaciones.

### Request
- **Method**: `POST`
- **Path**: `/api/incident-manager/save-message`
- **Headers**:
  - `Content-Type: application/json; charset=utf-8`
  - `Accept: application/json`
- **Body**:
```json
{
  "incident_id": "INC000004168775",
  "phase": "apertura",
  "completo": "Se comunica incidencia P2 (INC000004168775) por degradación en la plataforma SPAIN ALMACENAMIENTO en Sistemas Core...",
  "breve": "Apertura P2 (INC000004168775): Fallo en middleware de almacenamiento afecta servicios core. Soporte investigando...",
  "origen": "incident-reporter"
}
```

### Validation Rules:
1. `incident_id`: Requerido. Formato alfanumérico Remedy válido.
2. `phase`: Requerido. Uno de `["apertura", "seguimiento", "cierre"]`.
3. `completo`: Requerido. Longitud máxima: 90 palabras. Debe ser monopárrafo.
4. `breve`: Requerido. Longitud máxima: 30 palabras.

### Success Response (`200 OK`)
```json
{
  "success": true,
  "incident_id": "INC000004168775",
  "phase": "apertura",
  "entry": {
    "completo": "Se comunica incidencia P2...",
    "breve": "Apertura P2...",
    "generado_por_agente": true,
    "origen": "incident-reporter",
    "conteo_palabras_completo": 75,
    "conteo_palabras_breve": 21
  },
  "reevaluated": true,
  "message": "Mensaje oficial guardado y notificaciones actualizadas con éxito."
}
```

### Error Responses:
- **`400 Bad Request`**: Datos incompletos o exceso de palabras.
  ```json
  {
    "success": false,
    "error": "Límite de palabras excedido: versión completa tiene 96 palabras (máx 90)."
  }
  ```
- **`500 Internal Server Error`**: Error de escritura en disco o reevaluación fallida.
  ```json
  {
    "success": false,
    "error": "Error al persistir en data/agent_executive_messages.json: Permiso denegado."
  }
  ```

