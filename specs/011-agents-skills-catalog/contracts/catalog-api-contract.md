# Contrato de API: /api/agents-catalog

**Feature**: `011-agents-skills-catalog`

---

## 1. Endpoints de Consulta y Sincronización

### 1.1 `GET /api/agents-catalog`

Obtiene el catálogo completo en formato JSON Envelope.

#### Query Parameters:
- `refresh` (opcional, booleano, default `false`):
  - Si es `true` y el servidor cuenta con acceso a la biblioteca local, ejecuta la extracción en tiempo real antes de responder.
  - Si es `false` o no se puede refrescar, lee el fichero `data/output/agents_catalog.json`.

#### Respuestas:
- **`200 OK`**:
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
      "domains": [...],
      "agents": [...],
      "skills": [...]
    }
  }
  ```
- **`404 Not Found`**:
  Si el fichero `data/output/agents_catalog.json` no existe y no se pudo generar.
  ```json
  {
    "error": "Catálogo no encontrado. Ejecuta converters/cli/build_agents_catalog.py para generarlo."
  }
  ```

---

## 2. Fallback Estático del Cliente Frontend

El cliente JavaScript en `dashboards/agents-catalog/agents-catalog.js` implementa un orden de resolución en cascada:
1. Petición a `/api/agents-catalog`.
2. Si falla (ej. en despliegue estático o Nginx sin backend Python), solicita directamente `/data/output/agents_catalog.json`.
3. Si ambos fallan, muestra un estado amigable (*Empty State*) con indicaciones claras para el operador.

