# Data Model: Buscador de Incidencias con Resumen IA en Portal Principal

**Feature**: `009-portal-incident-search` | **Date**: 2026-10-06

Este documento define las entidades, tipos de datos, estados de validación y modelos de interfaz para el buscador de incidencias del portal principal.

---

## 1. Entidad: `IncidentSearchQuery` (Entrada del Buscador)

Representa la solicitud de búsqueda introducida por el usuario en el portal.

### Atributos

| Campo | Tipo | Requerido | Descripción | Ejemplo |
|---|---|---|---|---|
| `rawInput` | `string` | Sí | Cadena original tecleada o pegada por el usuario en el campo de texto | `"  inc4141215  "` |
| `sanitizedCode` | `string` | Sí | Código limpio, en mayúsculas y con padding de ceros aplicado | `"INC000004141215"` |
| `isValid` | `boolean` | Sí | Indica si el código cumple las reglas de formato mínimo para consultar | `true` |
| `errorMessage` | `string \| null` | No | Mensaje de advertencia o validación si `isValid` es falso | `"Por favor, introduce un código de incidencia válido."` |
| `timestamp` | `number` | Sí | Marca de tiempo en milisegundos de la consulta (`Date.now()`) | `1791295200000` |

### Reglas de Validación
1. **No vacío**: `rawInput.trim().length > 0`.
2. **Longitud mínima**: `sanitizedCode.length >= 4`.
3. **Formato numérico abreviado**: Si `/^\d+$/`, se transforma a `'INC' + rawInput.padStart(12, '0')`.
4. **Formato con prefijo incompleto**: Si `/^INC\d+$/i`, los dígitos se rellenan con ceros a la izquierda hasta 12 dígitos.

---

## 2. Entidad: `ResumenIAPayload` (Respuesta de la API Epsilon)

Representa la respuesta estructurada devuelta por la API de Epsilon IA a través del endpoint `/api/epsilon/resumenIA/{codigo}` y procesada por `resumen-ia.js`.

### Atributos

| Campo | Tipo | Requerido | Descripción | Ejemplo |
|---|---|---|---|---|
| `codigo` | `string` | Sí | Identificador de la incidencia | `"INC000004141215"` |
| `titulo` | `string` | Sí | Resumen o título técnico de la incidencia | `"Caída de servicio de autenticación en pasarela"` |
| `estado` | `string` | Sí | Estado Remedy del ticket | `"Cerrado"`, `"Asignado"`, `"En curso"` |
| `sistemas` | `string[]` | No | Lista de sistemas o servicios impactados | `["AUTENTICACION", "API-GW"]` |
| `problema` | `string` | No | Descripción sintetizada del problema detectado | `"Saturación de conexiones en el pool JDBC..."` |
| `impacto` | `string` | No | Impacto operativo y de negocio | `"Afectación a 1.200 usuarios durante 18 minutos"` |
| `solucion` | `string` | No | Causa raíz y medidas de mitigación o resolución | `"Reinicio de nodos y escalado de conexiones"` |
| `bloqueos` | `string` | No | Impedimentos o bloqueos técnicos pendientes | `""` o `"Pendiente de parche del proveedor"` |
| `siguienteAccion` | `string` | No | Recomendación o paso operativo siguiente | `"Monitorización en siguiente ventana de cambio"` |
| `hitos` | `Array<{fecha: string, texto: string}>` | No | Cronología técnica de eventos registrados | `[{fecha: "2026-10-02 09:15", texto: "Alerta..."}]` |

---

## 3. Estados del Componente Buscador (`SearchUIState`)

```
 [ IDLE ]
    │
    ├── (Usuario pulsa Consultar con input vacío)
    │     ▼
    │   [ INVALID_INPUT ] ──(Usuario teclea caracteres)──► [ IDLE ]
    │
    └── (Usuario pulsa Consultar con código válido)
          ▼
        [ SUBMITTING ]
          │
          └── Dispara ResumenIAModal.open(sanitizedCode)
                │
                ├── Modal muestra Spinner de carga
                ├── Modal resuelve y muestra datos sintetizados (o error)
                └── [ IDLE ] (Input listo para siguiente búsqueda)
```
