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
| **M9** | Semáforo de `Fecha Prevista` vencida / sin compromiso | Seguimiento | Alto | `[x] Completada` |
| **M10** | Notas rápidas de seguimiento de Mesa por incidencia | Seguimiento | Alto | `[ ] Pendiente` |
| **M11** | Filtros por `Despliegue` y por `Producto` | UX / Operativa | Medio | `[ ] Pendiente` |
| **M12** | Botón "Copiar briefing de Mesa" para actas y Teams | Operativa | Alto | `[x] Completada` |
| **M13** | Indicador de novedades desde la última sincronización | Operativa | Medio | `[x] Completada` |
| **M14** | Vista agrupada por Proyecto (`PRJ-*`) con semáforo de salud | Seguimiento | Medio | `[x] Completada` |
| **M15** | Detector de tickets sin movimiento / "ping-pong" entre grupos | Operativa | Medio | `[ ] Pendiente` |
| **M16** | Cache-busting y cabeceras `Cache-Control` en despliegue | Despliegue | Alto | `[x] Completada` |
| **M17** | Extracción de CSS y modularización de `release-desk.js` | Mantenimiento | Alto | `[ ] Pendiente` |
| **M18** | Concurrencia segura, retención de caché y backup de `overrides` | Datos / Despliegue | Alto | `[ ] Pendiente` |
| **M19** | Sync programada, concurrencia en `remedyG` y endpoint `/api/health/release-desk` | Operación / Despliegue | Medio | `[ ] Pendiente` |
| **M20** | Validación CI (`node --check` + `pytest`) y smoke test post-despliegue | Despliegue | Medio | `[ ] Pendiente` |
| **M21** | Unificación de servicios backend (`serve_app.py` y FastAPI) | Mantenimiento | Medio | `[ ] Pendiente` |

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
- **Propuesta:** Ampliar `data/release_desk_overrides.json` para guardar notas breves de seguimiento por ticket sin alterar los datos crudos de MonTMC, reflejándolas en la tabla, en la exportación CSV (`M4`) y en los briefings de Teams (`M12`).
- **Opciones de implementación:**
  - **Opción A · Nota única en el desplegable (MVP):**
    - Añadir `nota_mesa` (texto breve + `updated_at`) en `data/release_desk_overrides.json` junto a `fecha_prevista`.
    - Caja de texto editable dentro del panel desplegable de la incidencia con botón `Guardar nota` / `Limpiar`.
    - Mostrar un badge discreto `📝 Nota` en la columna `Acciones` (con el texto completo como tooltip) e incluir la columna `Nota Mesa` en el CSV y en los briefings.
  - **Opción B · Nota + etiqueta de situación de Mesa e edición inline:**
    - Añadir además un selector rápido de etiqueta (`En seguimiento`, `Bloqueada`, `Escalada`, `Pendiente validación`, `Paso a PRO`) con badge de color en la tabla.
    - Permitir editar la nota tanto desde el desplegable como inline en la fila (patrón `+ Nota` análogo al `+ Fecha` de `M8`).
    - Permitir filtrar en barra superior por etiquetas críticas (ej. `Bloqueada` / `Escalada`).
  - **Opción C · Bitácora cronológica de acuerdos por comité:**
    - Persistir un historial `notas_historial: [{ fecha, texto }]` en `data/release_desk_overrides.json` en lugar de sobrescribir la nota anterior.
    - Mostrar la última entrada en la tabla, CSV y briefing, y el histórico completo ordenado por fecha dentro del desplegable de detalle.
- **Recomendación:** **Opción A** para entrega inmediata reutilizando `/api/release-desk/overrides`, o **Opción B** si se desea filtrar rápidamente tickets `Bloqueados` / `Escalados` durante el comité.
- **Componentes afectados:** backend API (`overrides`), `dashboards/release-desk/index.html`, `dashboards/release-desk/release-desk.js`, `converters/tests/unit/test_release_desk.py`.
- **Criterio de aceptación:** Las notas persisten entre recargas y sincronizaciones de MonTMC sin alterar los datos crudos de Remedy, y quedan visibles en tabla, CSV y briefings.

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

---

### M16 · Cache-busting y cabeceras `Cache-Control` en despliegue
- **Situación actual:** `dashboards/release-desk/index.html` referencia `/dashboards/release-desk/release-desk.js` y `/dashboards/assets/ui-feedback.js` sin parámetro de versión (`?v=...`), por lo que tras un despliegue en VPS los navegadores pueden conservar JS/CSS obsoletos en caché.
- **Propuesta:** Incorporar versionado automático por hash/timestamp en los assets estáticos y configurar cabeceras `Cache-Control: no-cache` para HTML, JS/CSS de la consola y `data/output/*.json`.
- **Componentes afectados:** `dashboards/release-desk/index.html`, servidor web / configuración de despliegue (`serve_app.py` / Nginx).
- **Criterio de aceptación:** Tras cualquier despliegue nuevo, los usuarios reciben inmediatamente la última versión de la UI sin necesitar recarga forzada (`Ctrl+F5`).

---

### M17 · Extracción de CSS y modularización de `release-desk.js`
- **Situación actual:** `index.html` supera las 650 líneas con CSS embebido y `release-desk.js` supera las 1.600 líneas en un único IIFE, dificultando el mantenimiento y la revisión de cambios.
- **Propuesta:** Extraer los estilos a `dashboards/release-desk/release-desk.css` y dividir `release-desk.js` en módulos claros (lógica pura/dominio, cliente API/estado y renderizado DOM/eventos), manteniendo la exportabilidad para tests en Node.
- **Componentes afectados:** `dashboards/release-desk/index.html`, `dashboards/release-desk/release-desk.css`, `dashboards/release-desk/release-desk.js`, `converters/tests/unit/test_release_desk.py`.
- **Criterio de aceptación:** Código separado por responsabilidades, menor tamaño por fichero y 100% de tests unitarios pasando sin cambios de comportamiento.

---

### M18 · Concurrencia segura, retención de caché y backup de `overrides`
- **Situación actual:** Las escrituras concurrentes en `data/release_desk_overrides.json` podrían sobrescribirse entre peticiones simultáneas, y los ficheros de caché en disco (`remedyG` / `resumenIA`) crecen sin política de limpieza ni verificación de volumen persistente en despliegues.
- **Propuesta:** Proteger la escritura de `release_desk_overrides.json` con `threading.Lock` + escritura atómica, añadir limpieza/TTL para cachés antiguas en `data/cache/` y documentar/verificar en despliegue que `data/` reside en almacenamiento persistente con copia de seguridad.
- **Componentes afectados:** backend API (`overrides`), gestión de `data/cache/`, scripts de mantenimiento/despliegue.
- **Criterio de aceptación:** Sin pérdida de datos ante guardados simultáneos y tamaño acotado de la caché en disco.

---

### M19 · Sync programada, concurrencia en `remedyG` y endpoint `/api/health/release-desk`
- **Situación actual:** La sincronización con MonTMC depende de acción manual desde la UI y la reconciliación de tickets faltantes (`fetch_remedy_detail`) se ejecuta secuencialmente, lo que puede alargar la respuesta si hay muchos tickets antiguos sin cerrar.
- **Propuesta:** Permitir ejecutar `sync_montmc_postmortem.py` de forma programada (cron/scheduler), acotar/paralelizar con `ThreadPoolExecutor` y timeouts las consultas a `fetch_remedy_detail`, y exponer `/api/health/release-desk` reportando última sync, conectividad MonTMC/Epsilon y permisos de escritura en `data/`.
- **Componentes afectados:** `converters/cli/sync_montmc_postmortem.py`, `serve_app.py`, `converters/src/fastapi_remedy_router.py`.
- **Criterio de aceptación:** Sincronización más rápida y observable mediante healthcheck antes y después de cada despliegue.

---

### M20 · Validación CI (`node --check` + `pytest`) y smoke test post-despliegue
- **Situación actual:** Los tests unitarios cubren funciones aisladas, pero no hay verificación automática previa al despliegue de sintaxis JS (`node --check`) ni un smoke test HTTP contra el servidor levantado.
- **Propuesta:** Integrar en el flujo de despliegue la ejecución automática de `node --check dashboards/release-desk/release-desk.js`, `pytest` completo de Mesa de Release y un smoke check HTTP sobre `/dashboards/release-desk/`, `/data/output/index.json` y `/api/epsilon/resumenIA/cached`.
- **Componentes afectados:** scripts de CI/despliegue, `converters/tests/`.
- **Criterio de aceptación:** Ningún despliegue en producción avanza si falla la sintaxis JS, los tests unitarios o la disponibilidad de los endpoints críticos.

---

### M21 · Unificación de servicios backend (`serve_app.py` y FastAPI)
- **Situación actual:** Existen rutas y lógica paralela entre `serve_app.py` y `converters/src/fastapi_remedy_router.py`, lo que obliga a duplicar cambios cuando se añade un endpoint o parámetro nuevo.
- **Propuesta:** Extraer la lógica compartida de endpoints de Mesa de Release (`overrides`, `sync-postmortem`, `resumenIA/cached`, `remedyG`) a un módulo de servicio único invocado por ambos servidores (o migrar completamente al router FastAPI).
- **Componentes afectados:** `serve_app.py`, `converters/src/fastapi_remedy_router.py`, `converters/src/`.
- **Criterio de aceptación:** Un único punto de mantenimiento para cada operación backend, garantizando paridad exacta entre entorno local y producción.
