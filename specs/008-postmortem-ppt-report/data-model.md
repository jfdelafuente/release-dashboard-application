# Data Model: Informe PPT de Postmortem por Release

Esta feature no introduce almacenamiento persistente propio más allá del fichero de salida
(`.pptx`); todos los datos de entrada ya existen en el sistema. Este documento describe las
estructuras de datos intermedias que maneja el generador de informes, no un modelo de base de datos.

## PostmortemReportData (estructura intermedia, en memoria)

Resultado de leer y agregar los datos de una release concreta, antes de construir el `.pptx`.

| Campo | Tipo | Origen | Notas |
|---|---|---|---|
| `release_name` | string | Parámetro de entrada | Nombre exacto tal como aparece en `_metadata.release_name` de los ficheros de postmortem |
| `total_incidencias` | int | Calculado | Nº de registros del fichero `-postmortem.json` de esa release |
| `total_pendientes` | int | Calculado | Incidencias sin Cerrado/Resuelto, en cualquier momento |
| `pct_cerradas` | int (0-100) | Calculado | Redondeado, igual que el dashboard |
| `cerradas_detalle` | string | Calculado | "`X` de `Y` incidencias" |
| `tiempo_medio_resolucion` | string \| null | Calculado | Formato "Xd Yh" / "Xh Ym" / "Xm"; `null` si no hay ninguna incidencia cerrada con ambas fechas válidas |
| `tiempo_medio_detalle` | string | Calculado | "`X` de `Y` incidencias cerradas con fechas válidas" |
| `pct_resueltas_pap` | int (0-100) | Calculado | Solo cuentan resoluciones el mismo día calendario que el despliegue PaP |
| `pap_pendientes` | int | Calculado | Incidencias PaP sin Cerrado/Resuelto, en cualquier momento |
| `pct_resueltas_mesa` | int (0-100) | Calculado | |
| `mesa_pendientes` | int | Calculado | |
| `evolution_chart` | ChartData | Calculado | Ver abajo |
| `pap_evolution_chart` | ChartData \| null | Calculado | `null` si la release no tiene incidencias PaP |
| `open_incidents_chart` | ChartData | Calculado | |
| `system_chart` | ChartData | Calculado | |

**Validation rules**:
- Si no existe ningún fichero `-postmortem.json` con `release_name` coincidente → error explícito (FR-009), no se genera `PostmortemReportData` vacío con ceros.
- Todos los porcentajes se redondean igual que el dashboard (`Math.round` → `round()` de Python, con la misma regla de redondeo al par más cercano en `.5` documentada como diferencia conocida y aceptable a este nivel de precisión).

## ReleaseKpisContext (estructura intermedia, en memoria)

Resultado de leer `RAW_RELEASES` (ver research.md §4) y calcular las mismas series que
`dashboards/release-kpis/app.js`, para las gráficas generales (no filtradas a una release).

| Campo | Tipo | Origen | Notas |
|---|---|---|---|
| `releases` | list[ReleaseKpiRow] | `RAW_RELEASES` | Una fila por release, orden cronológico ascendente (igual que las gráficas del dashboard, no la tabla) |
| `incidencias_por_release_chart` | ChartData | Calculado | Réplica de `renderBarChart()` |
| `kpi_pap_chart` | ChartData | Calculado | Réplica de `buildKpiChartData(..., "papEntrada", "papResueltas", "pctPaP", ...)`, incluye línea de objetivo (75%) |
| `kpi_post_chart` | ChartData | Calculado | Réplica de `buildKpiChartData(..., "postEntrada", "postResueltas", "pctFirstWeek", ...)`, incluye línea de objetivo (75% — ver discrepancia documentada en `spec.md`) |

### ReleaseKpiRow

| Campo | Tipo | Notas |
|---|---|---|
| `name` | string | p. ej. "2026R7" |
| `year` | int | |
| `pap_entrada`, `pap_resueltas`, `post_entrada`, `post_resueltas` | int | Tal como están en `RAW_RELEASES` |
| `pct_pap`, `pct_first_week` | int (0-100) | Derivados, misma fórmula que `buildReleases()` en `app.js` |

## ChartData (estructura intermedia, en memoria)

Representa una gráfica ya lista para exportar a imagen; no es un tipo persistido.

| Campo | Tipo | Notas |
|---|---|---|
| `figure` | `plotly.graph_objects.Figure` | Construida en Python replicando colores/trazas del original JS |
| `title` | string | Para el pie de imagen/diapositiva, coincide con el `<h3>` del dashboard |
| `png_bytes` | bytes | Resultado de exportar `figure` vía Kaleido; se incrusta directamente en la diapositiva sin escribir a disco intermedio |

## Informe de Release (entidad de la especificación, `spec.md`)

Mapea a un fichero físico `.pptx` en `data/reports/<release_name_saneado>-postmortem-report.pptx`.
No tiene representación en memoria más allá del objeto `pptx.Presentation` de `python-pptx` mientras
se construye. Relación 1:1 con una `Release` existente identificada por `release_name`; regenerar
sobrescribe el fichero anterior de esa misma release (ver research.md §6).
