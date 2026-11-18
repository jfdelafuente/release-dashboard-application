# Backlog de Mejoras — Mesa de Release

Lista priorizada de evolutivos para la consola **[Mesa de Release](/05-postmortem-y-reportes/mesa-de-release.md)** (`dashboards/release-desk/`), diseñada para abordarse de forma incremental.

---

## Resumen de Prioridades

| ID | Mejora | Categoría | Impacto | Estado |
| :-: | :--- | :--- | :--- | :---: |
| **M1** | Precarga pasiva de Resumen IA ya cacheado | Datos / Rendimiento | Alto | `[ ] Pendiente` |
| **M2** | Extracción automática del bug de `JIRA` | Datos | Alto | `[ ] Pendiente` |
| **M3** | KPIs clicables como filtros rápidos | UX / Operativa | Medio | `[ ] Pendiente` |
| **M4** | Exportación de la vista filtrada (CSV / Excel) | Operativa | Alto | `[ ] Pendiente` |
| **M5** | Ordenación por cabeceras de columna | UX / Operativa | Medio | `[ ] Pendiente` |
| **M6** | Importación de CSV de proyectos desde la UI | Mantenimiento | Medio | `[ ] Pendiente` |
| **M7** | Indicador de antigüedad (Aging) en `Fecha Apertura` | Operativa | Medio | `[x] Completada` |
| **M8** | Edición y persistencia de `Fecha Prevista` acordada | Seguimiento | Alto | `[x] Completada` |

---

## Detalle de Mejoras

### M1 · Precarga pasiva de Resumen IA ya cacheado (coste 0 en Epsilon)
- **Situación actual:** Al cargar una release, las columnas `Descripción problema` y `Acciones` solo se enriquecen con Resumen IA después de que el usuario despliegue manualmente cada fila en esa sesión.
- **Propuesta:** Añadir un endpoint o parámetro de solo lectura (p. ej. `GET /api/epsilon/resumenIA/cached?ids=...` o `?cache_only=1`) que devuelva únicamente los resúmenes ya guardados en disco en el servidor **sin disparar llamadas externas a Epsilon IA**.
- **Componentes afectados:** servidor HTTP (`converters/` / API local) y `dashboards/release-desk/release-desk.js`.
- **Criterio de aceptación:** Al abrir una release, las incidencias que ya tengan Resumen IA en caché muestran automáticamente `iaData.problema` y `iaData.siguienteAccion` sin generar tráfico hacia Epsilon IA.

---

### M2 · Extracción automática del bug de `JIRA`
- **Situación actual:** La columna `JIRA` lee `inc['JIRA'] || inc['Jira'] || inc['jira']`, pero los registros de MonTMC/Remedy suelen incluir el código del bug dentro de texto libre y no en un campo estructurado.
- **Propuesta:** Detectar claves de Jira con expresión regular (`\b[A-Z][A-Z0-9]+-\d+\b`) excluyendo códigos de proyecto `PRJ-\d+` en `Descripción`, `detalleSolucion` y en el `Resumen IA` cacheado, renderizándolo como badge/enlace clicable.
- **Componentes afectados:** `dashboards/release-desk/release-desk.js` y `converters/tests/unit/test_release_desk.py`.
- **Criterio de aceptación:** Si una incidencia menciona un ticket tipo `BUG-1234` o `OPS-567` en su descripción/solución, aparece en la columna `JIRA` sin confundirse con `PRJ-*`.

---

### M3 · KPIs clicables como filtros rápidos
- **Situación actual:** Los 4 KPIs superiores son informativos; para filtrar por P1–P2 o por incidencias resueltas pendientes de cierre hay que usar los desplegables.
- **Propuesta:** Convertir cada tarjeta `.rd-kpi-card` en un botón/filtro rápido (con estado activo visual) que aplique o limpie el filtro correspondiente al hacer clic:
  - `Incidencias activas` → limpia filtros de estado y prioridad.
  - `Prioridad Alta / Crítica (P1–P2)` → filtra P1–P2.
  - `Asignadas / En Curso / Pendientes` → excluye `Resuelto`/`Resuelta`.
  - `Resueltas pendientes de cierre` → filtra `Resuelto`/`Resuelta`.
- **Componentes afectados:** `dashboards/release-desk/index.html`, `dashboards/release-desk/release-desk.js`.
- **Criterio de aceptación:** Pulsar un KPI filtra la tabla al instante y volver a pulsarlo restaura la vista completa.

---

### M4 · Exportación de la vista filtrada (CSV / Excel)
- **Situación actual:** Para compartir el estado de la mesa en actas o correos solo existe la copia individual (`📋 Copiar seguimiento`) dentro de cada desplegable.
- **Propuesta:** Añadir un botón `📥 Exportar tabla` junto al contador de incidencias que genere un CSV (separado por `;` con BOM UTF-8 para abrir directo en Excel) con las filas actualmente visibles y las 12 columnas de la tabla.
- **Componentes afectados:** `dashboards/release-desk/index.html`, `dashboards/release-desk/release-desk.js`.
- **Criterio de aceptación:** El fichero descargado respeta los filtros activos, incluye `PROYECTO` y `Acciones` (con Resumen IA si está en caché) y se abre sin problemas de tildes en Excel.

---

### M5 · Ordenación por cabeceras de columna
- **Situación actual:** La tabla mantiene el orden de llegada del JSON de postmortem.
- **Propuesta:** Permitir ordenar ascendente/descendente al pulsar en cabeceras clave (`Código Incidencia`, `Fecha Apertura`, `Prioridad / Urg.`, `PROYECTO`, `Status`, `Fecha Prevista`) manteniendo la fila desplegada si sigue visible.
- **Componentes afectados:** `dashboards/release-desk/index.html`, `dashboards/release-desk/release-desk.js`.
- **Criterio de aceptación:** Clicar una cabecera ordena la tabla mostrando indicador visual (`▲` / `▼`) y un segundo clic invierte el orden.

---

### M6 · Importación de CSV de proyectos desde la UI
- **Situación actual:** Cada mes hay que ejecutar por terminal `python converters/cli/update_projects_catalog.py <csv> --release <YYYYRMM>`.
- **Propuesta:** Añadir un botón `📁 Importar proyectos CSV` en la cabecera que permita subir el fichero `;`-separado para la release seleccionada mediante un endpoint `POST /api/projects-catalog/import`, invocando internamente `update_projects_catalog(...)`.
- **Componentes afectados:** backend API, `dashboards/release-desk/index.html`, `dashboards/release-desk/release-desk.js`.
- **Criterio de aceptación:** Tras subir el CSV desde el navegador, `data/projects_catalog.json` se actualiza conservando releases previas y la tabla refresca inmediatamente la columna `PROYECTO`.

---

### M7 · Indicador de antigüedad (Aging) en `Fecha Apertura`
- **Situación actual:** Todas las fechas de apertura se muestran con el mismo estilo visual, dificultando detectar tickets estancados a simple vista.
- **Propuesta:** Calcular los días transcurridos desde `Fecha de envío` para incidencias no resueltas y mostrar una etiqueta discreta de antigüedad (p. ej. `> 3d` en ámbar, `> 7d` en rojo).
- **Componentes afectados:** `dashboards/release-desk/index.html`, `dashboards/release-desk/release-desk.js`.
- **Criterio de aceptación:** Las incidencias abiertas con mayor antigüedad destacan visualmente sin saturar el ancho de la columna.

---

### M8 · Edición y persistencia de `Fecha Prevista` acordada
- **Situación actual:** En incidencias no resueltas, la columna `FECHA PREVISTA` queda vacía porque Remedy no siempre aporta fecha comprometida.
- **Propuesta:** Permitir registrar una fecha prevista acordada en la Mesa (inline o dentro del desplegable) guardándola en un fichero auxiliar por release (p. ej. `data/release_desk_overrides.json`), sin alterar los datos crudos de MonTMC.
- **Componentes afectados:** backend API, `dashboards/release-desk/release-desk.js`.
- **Criterio de aceptación:** Al guardar una fecha prevista en un ticket abierto, persiste entre recargas y cuando el ticket pasa a `Resuelta` prevalece la `Fecha de última resolución` real.
