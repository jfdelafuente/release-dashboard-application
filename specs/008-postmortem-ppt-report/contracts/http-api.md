# Contrato: API HTTP del informe PPT

Implementado igual en `serve_app.py` (desarrollo local) y en el backend FastAPI del repo hermano
`cso-incident-masivas-report` (producción), ambos invocando el mismo script compartido
(`converters/cli/generate_postmortem_report.py`) — mismo patrón que `/api/upload` con
`converters/cli/upload_csv.py`.

## `GET /api/reports/postmortem/{release_name}`

Genera (o regenera) el informe .pptx de la release indicada y lo devuelve como descarga binaria.

**Path params**:
- `release_name` (string, requerido): nombre exacto de la release, tal como aparece en
  `_metadata.release_name` de sus ficheros de postmortem. Se valida contra los ficheros
  existentes en `data/output/` antes de generar nada (no se acepta como ruta de fichero literal,
  para evitar path traversal).

**Respuesta 200 OK**:
- `Content-Type: application/vnd.openxmlformats-officedocument.presentationml.presentation`
- `Content-Disposition: attachment; filename="<release_name_saneado>-postmortem-report.pptx"`
- Cuerpo: bytes del `.pptx` generado.

**Respuesta 404 Not Found** (FR-009):
```json
{ "error": "No hay datos de postmortem cargados para la release '<release_name>'" }
```

**Respuesta 500 Internal Server Error**: si la generación falla por una causa no relacionada con
datos ausentes (p. ej. fallo de Kaleido al exportar una imagen).
```json
{ "error": "No se pudo generar el informe", "details": "<mensaje truncado>" }
```

## `POST /api/reports/postmortem/batch`

Genera el informe de todas las releases con datos de postmortem disponibles (User Story 3).

**Body**: ninguno.

**Respuesta 200 OK**:
```json
{
  "generated": ["2026R7", "2026R6", "2026R4"],
  "failed": []
}
```
Cada entrada de `failed` (si las hay) incluye `{ "release_name": "...", "error": "..." }`.
No devuelve los ficheros binarios directamente (serían potencialmente varios MB cada uno); el
cliente web, tras recibir la lista de generados, descarga cada uno con el endpoint individual
anterior si los necesita, o el usuario los recoge directamente de `data/reports/` si tiene acceso
al servidor.
