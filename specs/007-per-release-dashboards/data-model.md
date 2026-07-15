# Data Model: Dashboards por Release

## Release

Agrupación lógica de incidencias de postmortem identificada por un nombre. No es una tabla ni una clase nueva en el backend Python — es un **nombre de cadena** (`release_name`) que se propaga desde la subida del CSV hasta el JSON de salida y hasta `index.json`, y que el frontend usa como clave de búsqueda.

| Campo | Tipo | De dónde sale | Dónde vive |
|---|---|---|---|
| `name` | string | Introducido por el usuario al subir el CSV (o heredado del parámetro `?release=` de la URL si la subida se inició desde una release ya listada en `release-kpis` sin datos aún) | `_metadata.release_name` del JSON de postmortem; `postmortem.files[].release_name` en `index.json`; primer elemento de cada fila de `RAW_RELEASES` en `dashboards/release-kpis/releases-data.js` |
| `incidents` | array de Incidencia de Postmortem | Filas válidas del CSV convertido | `data` del JSON de postmortem correspondiente |
| `kpis` | objeto | Calculado por `PostmortemConverter` (sin cambios) | `_metadata.kpis` del JSON de postmortem |

**Reglas de validación**:
- `release_name` no puede estar vacío cuando `type=postmortem` en la subida (FR-005, FR-007).
- Cada archivo de postmortem en `data/output/` tiene como máximo un `release_name` (relación 1:1 archivo↔release); no se soporta dividir un mismo CSV en varias releases (ver Assumptions de spec.md).
- No hay unicidad forzada a nivel de sistema entre `release_name` y las releases de `release-kpis` — la consistencia se logra por construcción (R5 de research.md: el nombre siempre se hereda del parámetro de URL cuando la subida se origina desde `release-kpis`), no por una validación de backend que rechace nombres no reconocidos.

## Incidencia de Postmortem *(entidad ya existente, sin cambios de esquema)*

Pertenece exactamente a una Release (relación implícita: todas las incidencias de un mismo archivo JSON pertenecen a la release de ese archivo). Conserva los atributos que ya usa el dashboard de Postmortem/Release: `Estatus`, `Urgencia`, `Impacto`, `Despliegue` (PAP/MESA), `Fecha de envío`, `Fecha de última resolución`, `Grupo asignado`.

## Extensión de esquema: `_metadata` del JSON de postmortem

Antes:
```json
{
  "_metadata": {
    "type": "postmortem",
    "version": "1.0",
    "created": "...",
    "source_filename": "...",
    "record_count": 105,
    "conversion_timestamp": "...",
    "kpis": { ... }
  },
  "data": [ ... ]
}
```

Después (un único campo nuevo, opcional para no romper JSONs ya generados sin él):
```json
{
  "_metadata": {
    "type": "postmortem",
    "version": "1.0",
    "created": "...",
    "source_filename": "...",
    "release_name": "2026R6-MESA",
    "record_count": 105,
    "conversion_timestamp": "...",
    "kpis": { ... }
  },
  "data": [ ... ]
}
```

## Extensión de esquema: `index.json` → sección `postmortem`

Antes, cada entrada de `postmortem.files[]`:
```json
{
  "name": "2026R6-MESA-POST-20260707-postmortem.json",
  "size": 69301,
  "modified": "2026-07-10T01:01:07.721482",
  "path": "data/output/2026R6-MESA-POST-20260707-postmortem.json"
}
```

Después (un campo nuevo, leído de `_metadata.release_name` del propio archivo; `null` para archivos generados antes de esta feature, sin `release_name`):
```json
{
  "name": "2026R6-MESA-POST-20260707-postmortem.json",
  "size": 69301,
  "modified": "2026-07-10T01:01:07.721482",
  "path": "data/output/2026R6-MESA-POST-20260707-postmortem.json",
  "release_name": "2026R6-MESA"
}
```

**Compatibilidad hacia atrás**: los JSON de postmortem ya existentes en `data/output/` no tienen `release_name`. `build_index_for_hub` debe tratar su ausencia como `null`, no como error. El dashboard de postmortem, al buscar `files.find(f => f.release_name === releaseParam)`, simplemente no encontrará esos archivos antiguos por nombre — quedan accesibles solo si se les asigna un `release_name` re-convirtiendo el CSV original con el nuevo flujo (fuera de alcance de esta feature: no se re-procesan datos históricos).
