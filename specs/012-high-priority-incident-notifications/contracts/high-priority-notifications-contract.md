# Contract: High Priority Notifications JSON Schema

**Feature**: `012-high-priority-incident-notifications` | **Date**: 2026-10-26

Este contrato define la estructura JSON del fichero `data/output/high_priority_notifications.json` y el endpoint `/api/incident-notifications`.

---

## 1. Esquema JSON (JSON Schema Draft-07)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "HighPriorityNotificationsCatalog",
  "type": "object",
  "required": ["_metadata", "data"],
  "properties": {
    "_metadata": {
      "type": "object",
      "required": ["type", "version", "generated_at", "kpis"],
      "properties": {
        "type": { "type": "string", "const": "high_priority_notifications" },
        "version": { "type": "string" },
        "generated_at": { "type": "string", "format": "date-time" },
        "source_file": { "type": "string" },
        "kpis": {
          "type": "object",
          "required": ["total_scanned", "total_high_priority", "p1_critical_count", "p2_high_count", "discrepancies_count"],
          "properties": {
            "total_scanned": { "type": "integer", "minimum": 0 },
            "total_high_priority": { "type": "integer", "minimum": 0 },
            "p1_critical_count": { "type": "integer", "minimum": 0 },
            "p2_high_count": { "type": "integer", "minimum": 0 },
            "discrepancies_count": { "type": "integer", "minimum": 0 }
          }
        }
      }
    },
    "data": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "id",
          "prioridad_original",
          "prioridad_sugerida",
          "es_alta_prioridad",
          "es_discrepancia",
          "evaluacion",
          "mensajes_ejecutivos"
        ],
        "properties": {
          "id": { "type": "string", "pattern": "^INC[0-9]+$" },
          "titulo": { "type": "string" },
          "sistemas": { "type": "array", "items": { "type": "string" } },
          "prioridad_original": { "type": "string" },
          "prioridad_sugerida": { "type": "string", "enum": ["P1", "P2", "P3", "P4"] },
          "es_alta_prioridad": { "type": "boolean" },
          "es_discrepancia": { "type": "boolean" },
          "estatus": { "type": "string" },
          "fecha_envio": { "type": "string" },
          "evaluacion": {
            "type": "object",
            "required": ["impacto", "urgencia", "sla_objetivo_minutos"],
            "properties": {
              "impacto": { "type": "string", "enum": ["Alto", "Medio", "Bajo"] },
              "impacto_justificacion": { "type": "string" },
              "urgencia": { "type": "string", "enum": ["Alta", "Media", "Baja"] },
              "urgencia_justificacion": { "type": "string" },
              "workaround": { "type": "string", "enum": ["Sí", "No", "Desconocido"] },
              "sla_objetivo_minutos": { "type": "integer" }
            }
          },
          "resumen_ia": {
            "type": "object",
            "properties": {
              "problema": { "type": "string" },
              "impacto": { "type": "string" },
              "solucion": { "type": "string" },
              "bloqueos": { "type": "string" },
              "siguiente_accion": { "type": "string" }
            }
          },
          "mensajes_ejecutivos": {
            "type": "object",
            "properties": {
              "apertura": { "$ref": "#/definitions/ExecutiveMessage" },
              "seguimiento": { "$ref": "#/definitions/ExecutiveMessage" },
              "cierre": { "$ref": "#/definitions/ExecutiveMessage" }
            }
          }
        }
      }
    }
  },
  "definitions": {
    "ExecutiveMessage": {
      "type": "object",
      "required": ["completo", "breve", "conteo_palabras_completo", "conteo_palabras_breve"],
      "properties": {
        "completo": { "type": "string" },
        "breve": { "type": "string" },
        "conteo_palabras_completo": { "type": "integer", "maximum": 90 },
        "conteo_palabras_breve": { "type": "integer", "maximum": 30 }
      }
    }
  }
}
```

