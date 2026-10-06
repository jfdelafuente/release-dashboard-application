# Contract: Epsilon IA Resumen Proxy API

**Feature**: `009-portal-incident-search` | **Date**: 2026-10-06

Este documento define el contrato HTTP del endpoint proxy consumido por `resumen-ia.js` para obtener la síntesis de una incidencia.

---

## 1. Endpoint Proxy

`GET /api/epsilon/resumenIA/{codigo}`

### Parámetros de Ruta
- `{codigo}`: Identificador alfanumérico de la incidencia (ej. `INC000004141215`).

### Cabeceras de Petición
- `Accept: application/json`
- `Cache-Control: no-cache` (opcional, enviado únicamente al pulsar el botón "Refrescar" del modal para forzar bypass de caché en Nginx).

---

## 2. Respuestas

### Código 200 OK (Éxito)
Devuelve el JSON estructurado con la síntesis del motor Epsilon IA.

**Cabeceras de respuesta destacadas**:
- `Content-Type: application/json`
- `X-Cache-Status: HIT | MISS | BYPASS | EXPIRED` (generada por la zona `proxy_cache my_cache` de Nginx)

**Cuerpo de respuesta (Ejemplo)**:
```json
{
  "codigo": "INC000004141215",
  "titulo": "Degradación en pasarela de pagos móviles",
  "estado": "Cerrado",
  "sistemas": ["PAGOS", "GATEWAY-CORE"],
  "problema": "Incremento de tiempos de respuesta en autorizaciones.",
  "impacto": "Afectación a transacciones durante 25 minutos.",
  "solucion": "Reciclado preventivo del pool y ajuste de timeouts.",
  "bloqueos": "",
  "siguienteAccion": "Seguimiento en comité de cambios.",
  "hitos": [
    {
      "fecha": "2026-10-02 08:30",
      "texto": "Alarma de latencia superada en gateway."
    },
    {
      "fecha": "2026-10-02 08:55",
      "texto": "Servicio restablecido y parámetros normalizados."
    }
  ]
}
```

### Código 404 Not Found
Devuelve error informativo cuando la incidencia no existe o no dispone aún de resumen procesado por el motor de IA.
- Cacheado en Nginx durante 1 minuto (`proxy_cache_valid 404 1m`) para mitigar peticiones repetitivas erróneas.
