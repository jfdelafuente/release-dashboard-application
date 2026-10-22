# Contrato de Datos: agents_catalog.json Schema

**Feature**: `011-agents-skills-catalog`
**Fichero de salida**: `data/output/agents_catalog.json`

---

## 1. JSON Schema (Draft 7)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "AgentsCatalogEnvelope",
  "type": "object",
  "required": ["_metadata", "data"],
  "properties": {
    "_metadata": {
      "type": "object",
      "required": ["schema_version", "type", "generated_at", "source_library", "kpis"],
      "properties": {
        "schema_version": { "type": "string", "example": "1.0.0" },
        "type": { "type": "string", "enum": ["agents_catalog"] },
        "generated_at": { "type": "string", "format": "date-time" },
        "source_library": { "type": "string" },
        "kpis": {
          "type": "object",
          "required": ["total_agents", "total_domains", "total_skills"],
          "properties": {
            "total_agents": { "type": "integer", "minimum": 0 },
            "total_domains": { "type": "integer", "minimum": 0 },
            "total_skills": { "type": "integer", "minimum": 0 }
          }
        }
      }
    },
    "data": {
      "type": "object",
      "required": ["domains", "agents", "skills"],
      "properties": {
        "domains": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["id", "label", "agent_count"],
            "properties": {
              "id": { "type": "string" },
              "label": { "type": "string" },
              "agent_count": { "type": "integer", "minimum": 0 }
            }
          }
        },
        "agents": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["id", "name", "version", "domain", "description", "recommended_skills", "file_path"],
            "properties": {
              "id": { "type": "string" },
              "name": { "type": "string" },
              "alias": { "type": "string" },
              "version": { "type": "string" },
              "domain": { "type": "string" },
              "domain_label": { "type": "string" },
              "description": { "type": "string" },
              "recommended_skills": {
                "type": "array",
                "items": { "type": "string" }
              },
              "file_path": { "type": "string" },
              "markdown_content": { "type": "string" },
              "tools": {
                "type": "array",
                "items": { "type": "string" }
              }
            }
          }
        },
        "skills": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["id", "name", "description", "file_path", "used_by_agents"],
            "properties": {
              "id": { "type": "string" },
              "name": { "type": "string" },
              "description": { "type": "string" },
              "file_path": { "type": "string" },
              "used_by_agents": {
                "type": "array",
                "items": { "type": "string" }
              },
              "markdown_content": { "type": "string" }
            }
          }
        }
      }
    }
  }
}
```

---

## 2. Ejemplo Representativo de Carga

```json
{
  "_metadata": {
    "schema_version": "1.0.0",
    "type": "agents_catalog",
    "generated_at": "2026-10-22T16:15:00Z",
    "source_library": "C:\\Users\\jose.delafuente\\Claude\\Projects\\biblioteca-agentes",
    "kpis": {
      "total_agents": 5,
      "total_domains": 2,
      "total_skills": 6
    }
  },
  "data": {
    "domains": [
      {
        "id": "brand-content",
        "label": "Contenido y Marca",
        "agent_count": 1
      },
      {
        "id": "it-incidents",
        "label": "Incidencias IT",
        "agent_count": 4
      }
    ],
    "agents": [
      {
        "id": "incident-analyzer",
        "name": "incident-analyzer",
        "alias": "analizador-incidencias-it",
        "version": "1.2.0",
        "domain": "it-incidents",
        "domain_label": "Incidencias IT",
        "description": "Analiza incidencias IT y genera diagnósticos detallados...",
        "recommended_skills": [
          "it-severity-matrix",
          "postmortem-pir-workflow"
        ],
        "file_path": "agents/it-incidents/incident-analyzer.md",
        "markdown_content": "# Agente de Análisis de Incidencias IT..."
      }
    ],
    "skills": [
      {
        "id": "it-severity-matrix",
        "name": "it-severity-matrix",
        "description": "Calcula y justifica el nivel de Severidad/Prioridad (P1 a P4)...",
        "file_path": ".agents/skills/it-severity-matrix/SKILL.md",
        "used_by_agents": [
          "incident-analyzer",
          "incident-describer",
          "incident-reporter"
        ],
        "markdown_content": "# IT Severity Matrix..."
      }
    ]
  }
}
```

