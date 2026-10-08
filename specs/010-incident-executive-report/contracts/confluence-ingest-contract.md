# Contract: Ingesta y Extracción de Postmortem desde Confluence

**Feature**: `010-incident-executive-report`

---

## 1. Estructura Esperada en la Página de Postmortem de Confluence

El extractor analiza el contenido de la página de Confluence identificando bloques estándar de postmortems de Orange:

### 1.1 Metadatos de Cabecera
- **Título**: Encabezado principal de la página (`<h1>` o macro de título).
  - Patrón: `Postmortem Incidencia - TT {ID} - {Título}` o `Incidencia {ID} - {Título}`.
- **Fechas**: Cajas de metadatos o tabla inicial:
  - `Inicio`: `DD/MM/YYYY HH:MM:SS` o `DD/MM/YYYY HH:MM`
  - `Fin` o `Recuperación`: `DD/MM/YYYY HH:MM:SS`
  - `Duración`: Calculada como `Fin - Inicio` o leída directamente (ej. `3h 25m`).

### 1.2 Secciones de Resumen Técnico
- **Impacto / Afectación**: Párrafos bajo encabezado `Impacto`, `Afectación del Servicio` o similar.
- **Causa Raíz**: Párrafos bajo encabezado `Causa Raíz`, `Causa del Incidente` o `Root Cause`.
- **Solución / Recuperación**: Párrafos bajo encabezado `Solución`, `Acciones de Recuperación` o `Workaround`.

### 1.3 Tabla de Puntos de Acción (`PUNTOS DE ACCION RELEVANTES`)
Tabla en Confluence con encabezados coincidentes o equivalentes a:
- Columna 1: `Pain Point` | `Categoría` | `Tipo`
- Columna 2: `Descripción` | `Acción` | `Detalle`
- Columna 3: `Owner` | `Responsable` | `Equipo`
- Columna 4: `Forecast` | `Fecha Prevista` | `Estado` | `Semana`

### 1.4 Tabla Cronológica (`CRONOLOGÍA`)
Tabla en Confluence con encabezados coincidentes o equivalentes a:
- Columna 1: `Hora` | `Fecha/Hora` | `Timestamp`
- Columna 2: `Evento` | `Descripción` | `Hito` | `Acción`

---

## 2. Comportamiento ante Variaciones o Datos Faltantes (Graceful Degradation)

| Situación | Comportamiento del Extractor |
|---|---|
| Faltan columnas en la tabla de acciones | Las columnas omitidas se rellenan con `"—"` |
| Duración no explícita | Se calcula la diferencia entre `Inicio` y `Fin` en formato `Xh Ym` |
| Tabla cronológica muy extensa (>38 filas) | Se reparte ordenadamente: 18 filas en Slide 2, 20 filas en Slide 3, y diapositivas adicionales si supera 38 filas |
| Bloques de impacto/causa vacíos | Se inserta texto por defecto `"Pendiente de detallar en postmortem"` |
| Página no accesible por falta de sesión | La UI muestra mensaje claro invitando a iniciar sesión o a pegar el contenido en el modal |

