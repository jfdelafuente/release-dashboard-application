# Contrato: `POST /api/upload` (campo `release_name` nuevo)

## Request

`multipart/form-data`, servido por `serve_app.py:handle_upload()`.

| Campo | Obligatorio | Descripción | Cambio |
|---|---|---|---|
| `file` | Sí | CSV a convertir | Sin cambios |
| `type` | Sí | `massive` \| `postmortem` | Sin cambios |
| `release_name` | Sí, solo si `type=postmortem` | Nombre de la release a asociar a los datos convertidos | **Nuevo** |

Si `type=postmortem` y `release_name` está ausente o vacío, la petición se rechaza igual que hoy se rechaza la ausencia de `file` (mismo patrón de error ya usado en `handle_upload`, línea ~69-71: `_send_json(400, {'success': False, 'error': '...'})`).

Si `type=massive`, `release_name` se ignora si se envía (no aplica a incidencias masivas).

## Response

Sin cambios de forma. `result` sigue siendo el dict devuelto por `run_upload()`. Internamente, `run_upload()` pasa `release_name` como argumento CLI adicional (`--release-name <valor>`) al invocar `convert_postmortems.py` únicamente cuando `dashboard_type == 'postmortem'`.

## Contrato del CLI: `convert_postmortems.py`

Nuevo argumento opcional:

```bash
python converters/cli/convert_postmortems.py <input.csv> --release-name "2026R6-MESA"
```

- Si se omite `--release-name`, el comportamiento es idéntico al actual (el JSON de salida no incluye `release_name` en `_metadata`, igual que los archivos generados antes de esta feature).
- Cuando se invoca desde `run_upload()` (flujo de subida por navegador), el argumento se pasa siempre que `dashboard_type == 'postmortem'`.
