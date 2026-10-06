# API Contract: Generación y Descarga de Informe Ejecutivo

**Base Path**: `/api/reports/executive-incident`

---

## 1. `POST /api/reports/executive-incident`

Genera un nuevo informe ejecutivo de incidencia a partir de los datos del postmortem.

### Request Body (`application/json`)

```json
{
  "incidentRef": "2606S77393",
  "confluenceUrl": "https://confluence.si.orange.es/display/POSTMORTEM/INC-2606S77393",
  "data": {
    "title": "Problema de llamadas numeros IVRs de ATC exMM",
    "startTime": "09/06/2026 14:45:00",
    "duration": "3h 25m",
    "impactText": "Se produjo una degradación progresiva del servicio de voz...",
    "causeText": "Saturación del límite de conexiones/prefijos BGP en la interconexión con AWS...",
    "solutionText": "Tras la revisión por parte del TMC IP, se aumenta el límite de prefijos...",
    "actionPoints": [
      {
        "painPoint": "Solución",
        "description": "Ampliación prefix-BGP para servicio AWS",
        "owner": "TMC Acceso_Fijo",
        "forecast": "Cerrado"
      }
    ],
    "timelineEvents": [
      {
        "time": "15:16",
        "event": "Se recibe ticket OPIT-906329 informando de cortes en llamadas..."
      }
    ]
  },
  "force": false
}
```

### Responses

#### `200 OK` (Informe generado exitosamente)
```json
{
  "success": true,
  "incidentRef": "2606S77393",
  "filename": "RESUMEN_EJECUTIVO_2606S77393.pptx",
  "downloadUrl": "/api/reports/executive-incident/2606S77393",
  "generatedAt": "2026-10-06T17:35:00Z",
  "sizeBytes": 1749686,
  "slideCount": 3
}
```

#### `400 Bad Request` (Datos incompletos o inválidos)
```json
{
  "success": false,
  "error": "Falta el identificador de la incidencia (incidentRef) o los datos del postmortem."
}
```

#### `500 Internal Server Error` (Fallo en la generación de PowerPoint)
```json
{
  "success": false,
  "error": "Error interno al generar el informe PowerPoint.",
  "details": "Mensaje detallado para depuración"
}
```

---

## 2. `GET /api/reports/executive-incident/{incidentRef}`

Descarga el archivo `.pptx` generado para la incidencia solicitada.

### Parámetros de Ruta
- `incidentRef`: Identificador de la incidencia (ej. `2606S77393` o `INC000004141215`).

### Parámetros Query
- `force`: `true` para forzar la regeneración antes de descargar si se acompaña de URL o datos.

### Responses

#### `200 OK`
- **Content-Type**: `application/vnd.openxmlformats-officedocument.presentationml.presentation`
- **Content-Disposition**: `attachment; filename="RESUMEN_EJECUTIVO_2606S77393.pptx"`
- **Body**: Bytes del archivo binario `.pptx`.

#### `404 Not Found` (El informe no existe)
```json
{
  "success": false,
  "error": "No existe un informe ejecutivo generado para la incidencia 2606S77393. Debe solicitar su generación primero."
}
```

---

## 3. `GET /api/reports/executive-incident/{incidentRef}/status`

Consulta si el informe ya está generado en el servidor para activar el botón de descarga inmediata.

### Responses

#### `200 OK` (Existe informe)
```json
{
  "exists": true,
  "incidentRef": "2606S77393",
  "filename": "RESUMEN_EJECUTIVO_2606S77393.pptx",
  "downloadUrl": "/api/reports/executive-incident/2606S77393",
  "generatedAt": "2026-10-06T17:35:00Z",
  "sizeBytes": 1749686
}
```

#### `200 OK` (No existe aún informe)
```json
{
  "exists": false,
  "incidentRef": "2606S77393"
}
```
