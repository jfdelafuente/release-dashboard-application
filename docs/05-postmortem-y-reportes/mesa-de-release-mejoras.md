# Backlog de Mejoras — Mesa de Release

Lista priorizada de evolutivos para la consola **[Mesa de Release](/05-postmortem-y-reportes/mesa-de-release.md)** (`dashboards/release-desk/`), diseñada para abordarse de forma incremental.

---

## Resumen de Prioridades

| ID | Mejora | Categoría | Impacto | Estado |
| :-: | :--- | :--- | :--- | :---: |
| **M1** | Precarga pasiva de Resumen IA ya cacheado | Datos / Rendimiento | Alto | `[x] Completada` |
| **M2** | Extracción automática del bug de `JIRA` | Datos | Alto | `[ ] Pendiente` |
| **M3** | KPIs clicables como filtros rápidos | UX / Operativa | Medio | `[x] Completada` |
| **M4** | Exportación de la vista filtrada (CSV / Excel) | Operativa | Alto | `[x] Completada` |
| **M5** | Ordenación por cabeceras de columna | UX / Operativa | Medio | `[x] Completada` |
| **M6** | Importación de CSV de proyectos desde la UI | Mantenimiento | Medio | `[ ] Pendiente` |
| **M7** | Indicador de antigüedad (Aging) en `Fecha Apertura` | Operativa | Medio | `[x] Completada` |
| **M8** | Edición y persistencia de `Fecha Prevista` acordada | Seguimiento | Alto | `[x] Completada` |
| **M9** | Semáforo de `Fecha Prevista` vencida / sin compromiso | Seguimiento | Alto | `[ ] Pendiente` |
| **M10** | Notas rápidas de seguimiento de Mesa por incidencia | Seguimiento | Alto | `[ ] Pendiente` |
| **M11** | Filtros por `Despliegue` y por `Producto` | UX / Operativa | Medio | `[ ] Pendiente` |
| **M12** | Botón "Copiar briefing de Mesa" para actas y Teams | Operativa | Alto | `[x] Completada` |
| **M13** | Indicador de novedades desde la última sincronización | Operativa | Medio | `[ ] Pendiente` |
| **M14** | Vista agrupada por Proyecto (`PRJ-*`) con semáforo de salud | Seguimiento | Medio | `[ ] Pendiente` |
| **M15** | Detector de tickets sin movimiento / "ping-pong" entre grupos | Operativa | Medio | `[ ] Pendiente` |

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

---

### M9 · Semáforo de `Fecha Prevista` vencida / sin compromiso
- **Situación actual:** La `Fecha Prevista` acordada (`M8`) se muestra siempre con el mismo estilo visual, sin alertar si el compromiso ya ha vencido o si está próximo a vencer.
- **Propuesta:** Resaltar en rojo las incidencias no resueltas cuya `Fecha Prevista` sea anterior a hoy, en ámbar las que vencen hoy o mañana, y añadir un filtro rápido (o KPI) para listar tickets con compromiso vencido o sin fecha asignada.
- **Componentes afectados:** `dashboards/release-desk/index.html`, `dashboards/release-desk/release-desk.js`, `converters/tests/unit/test_release_desk.py`.
- **Criterio de aceptación:** En el comité diario se identifican a simple vista las fechas incumplidas y los tickets abiertos sin fecha comprometida.

---

### M10 · Notas rápidas de seguimiento de Mesa por incidencia
- **Situación actual:** Los acuerdos verbales del comité (bloqueos, escalados, responsables puntuales) no tienen un campo propio si no se reflejan aún en Remedy.
- **Propuesta:** Ampliar `data/release_desk_overrides.json` para guardar una nota breve de seguimiento por ticket (editable desde el detalle o la fila), mostrar un indicador visual en la tabla cuando exista nota e incluirla en la exportación CSV (`M4`).
- **Componentes afectados:** backend API (`overrides`), `dashboards/release-desk/index.html`, `dashboards/release-desk/release-desk.js`.
- **Criterio de aceptación:** Las notas persisten entre recargas y sincronizaciones de MonTMC sin alterar los datos crudos de Remedy.

---

### M11 · Filtros por `Despliegue` y por `Producto`
- **Situación actual:** Se puede filtrar por proyecto (`PRJ-*`), estado, prioridad y grupo, pero no directamente por fase de `Despliegue` (`Completo`, `Piloto`, `Modo Oculto`, `PaP Técnico`) ni por `Producto` (`AURORA`, etc.).
- **Propuesta:** Añadir selectores de `Despliegue` y `Producto` en la barra de filtros (`.rd-filters`) poblados dinámicamente con los valores presentes en la release activa.
- **Componentes afectados:** `dashboards/release-desk/index.html`, `dashboards/release-desk/release-desk.js`.
- **Criterio de aceptación:** Permite priorizar en segundos la revisión de incidencias en `Completo` o `Piloto`, o acotar por un producto concreto.

---

### M12 · Botón "Copiar briefing de Mesa" para actas y Teams
- **Situación actual:** Tras el comité hay que redactar manualmente el resumen de seguimiento o copiar ticket a ticket.
- **Propuesta:** Añadir un botón en la consola que genere en el portapapeles un resumen en texto/Markdown de la vista filtrada (agrupado por prioridad o proyecto, destacando P1/P2, compromisos vencidos y próximas fechas previstas).
- **Componentes afectados:** `dashboards/release-desk/index.html`, `dashboards/release-desk/release-desk.js`.
- **Criterio de aceptación:** Con un clic se obtiene un resumen estructurado listo para pegar en Teams o correo corporativo respetando los filtros activos.

---

### M13 · Indicador de novedades desde la última sincronización
- **Situación actual:** Tras pulsar `Sincronizar MonTMC`, la tabla se refresca completa sin distinguir qué tickets son nuevos o han cambiado de estado respecto a la foto anterior.
- **Propuesta:** Guardar en respuesta de `/api/postmortem/sync` (o metadatos locales) los IDs nuevos y los que cambiaron de estado en la última sincronización y mostrar un badge discreto (`Nuevo` / `Actualizada`) durante la sesión.
- **Componentes afectados:** `converters/cli/sync_montmc_postmortem.py`, `dashboards/release-desk/index.html`, `dashboards/release-desk/release-desk.js`.
- **Criterio de aceptación:** El Release Manager identifica inmediatamente qué tickets requieren atención nueva tras sincronizar con MonTMC.

---

### M14 · Vista agrupada por Proyecto (`PRJ-*`) con semáforo de salud
- **Situación actual:** La vista única es plana por incidencia, dificultando evaluar de golpe el estado agregado de cada `PRJ-*` de la release.
- **Propuesta:** Añadir un conmutador `Tabla / Por proyecto` que agrupe las incidencias activas por `PRJ-*`, mostrando `Despliegue`, resumen, conteo por prioridad (`P1/P2/P3`) y si existen compromisos vencidos.
- **Componentes afectados:** `dashboards/release-desk/index.html`, `dashboards/release-desk/release-desk.js`.
- **Criterio de aceptación:** Al cambiar a vista por proyecto se visualiza el riesgo agregado de cada iniciativa y se puede desplegar o filtrar sus incidencias.

---

### M15 · Detector de tickets sin movimiento / "ping-pong" entre grupos
- **Situación actual:** El indicador de `Aging` (`M7`) mide la antigüedad total desde apertura, pero no detecta si un ticket lleva días sin actividad reciente en worklogs o si ha rebotado entre varios grupos.
- **Propuesta:** Usar `fechaUltimaModificacion` (y opcionalmente los worklogs/eventos de `remedyG` ya cacheados) para marcar tickets abiertos sin movimiento reciente (p. ej. `> 48h`) o con múltiples reasignaciones de grupo.
- **Componentes afectados:** `dashboards/release-desk/index.html`, `dashboards/release-desk/release-desk.js`.
- **Criterio de aceptación:** Los tickets estancados o en "ping-pong" destacan en la tabla para que el Release Manager desbloquee su asignación.
