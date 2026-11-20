# Consola Mesa de Release

La consola **Mesa de Release** (`/dashboards/release-desk/`) centraliza el seguimiento operativo de las incidencias de release que **no están cerradas** (`Estatus !== "Cerrado"`), integrando el catálogo de proyectos por release mensual, fechas previstas acordadas, vista agregada por proyecto, exportación/briefings y el **Resumen IA** de Epsilon bajo demanda.

---

## 1. Ubicación y Archivos Principales

| Componente | Ruta | Responsabilidad |
| :--- | :--- | :--- |
| Interfaz web | `dashboards/release-desk/index.html`, `dashboards/release-desk/release-desk.css` | Estructura HTML, estilos externos con cache-busting, KPIs clicables, filtros, conmutador de vista y tabla de 12 columnas |
| Lógica de dominio | `dashboards/release-desk/release-desk-domain.js` | Funciones puras (filtros, aging, ordenación, resolución `PRJ-*`, vista por proyecto, exportación CSV, briefings Teams), exportables a navegador y Node |
| Lógica UI y estado | `dashboards/release-desk/release-desk.js` | Carga de releases, estado de pantalla, eventos DOM y llamadas API |
| Notificaciones UI | `dashboards/assets/ui-feedback.css`, `dashboards/assets/ui-feedback.js` | Sistema central de toasts (`window.Toast`) usado en avisos y confirmaciones |
| Navegación | `dashboards/assets/topbar.js` | Registro del enlace **Mesa de Release** en la barra superior (`id: 'release-desk'`) |
| Sincronización MonTMC | `converters/cli/sync_montmc_postmortem.py` | Sincronización incremental desde `/api/epsilon/release`, reconciliación paralela vía `remedyG` (`ThreadPoolExecutor`) y registro de novedades (`last_sync_changes`) |
| Almacenamiento y salud | `converters/src/storage_utils.py`, `converters/src/release_desk_overrides.py` | Locks por fichero (`threading.Lock`), escritura atómica JSON con backup `.bak`, retención de caché (30d / 2000 ficheros) y diagnóstico `/api/health/release-desk` |
| Catálogo CLI | `converters/cli/update_projects_catalog.py` | Importación incremental y no destructiva de CSVs mensuales de proyectos hacia `data/projects_catalog.json` |
| Versionado estáticos | `converters/cli/bump_asset_versions.py` | Actualización automática de `?v=<version>` en CSS/JS locales de Mesa de Release y Consola de Triaje |
| Tests unitarios | `converters/tests/unit/test_release_desk.py`, `test_sync_montmc_postmortem.py`, `test_m18_storage_concurrency.py`, `test_m19_health_and_parallel_sync.py` | Validación de controles HTML, reglas JS, sincronización MonTMC, concurrencia/retención y endpoint de salud |

---

## 2. Fuentes de Datos, Sincronización y Optimización de Resumen IA

- **Índice de releases**: lee `data/output/index.json` (sección `postmortem.files`) y combina con `RAW_RELEASES` (`dashboards/release-kpis/releases-data.js`) para poblar el selector mensual (`2026R11`, `2026R10`, etc.).
- **Aislamiento de datos**: **no** consume `high_priority_notifications.json` ni `*-massive.json`; opera exclusivamente sobre los datasets de seguimiento postmortem de cada release.
- **Sincronización con MonTMC**:
  - El botón **⚡ Sincronizar Epsilon** invoca `POST /api/sync-postmortem` con `{ release_name }`.
  - Realiza un *upsert* incremental de `/api/epsilon/release` y **reconcilia en paralelo** (`ThreadPoolExecutor`, timeout `15s`, tope `MONTMC_RECONCILE_MAX=50`) vía `GET /api/eps/remedyG/{idRemedy}` los tickets locales no cerrados que ya no aparezcan en ese feed (detectando cierres en Remedy).
  - Opcionalmente, `serve_app.py --sync-interval <minutos>` (o `SYNC_INTERVAL_MINUTES`) activa una sincronización periódica en segundo plano para Mesa de Release y Consola de Triaje.
  - Registra en `_metadata.last_sync_changes` los IDs nuevos, actualizados y con cambio de estado para mostrarlos con badges en la tabla.
- **Persistencia auxiliar (`overrides`) y seguridad en disco**: las fechas previstas acordadas en Mesa se persisten por release en `data/release_desk_overrides.json` mediante `/api/release-desk/overrides` con `threading.Lock`, escritura atómica (`os.replace`) y backup `.bak`, sin alterar los JSON crudos de MonTMC. Al arrancar `serve_app.py`, se comprueba la escritura en `STORAGE_DIR` y se podan las cachés `.epsilon_cache` y `.remedy_cache` (30 días / máx. 2.000 ficheros).
- **Diagnóstico de salud**: `GET /api/health/release-desk` expone el estado de escritura en `data/`, última sincronización de postmortem, disponibilidad de `high_priority_notifications.json` (Triaje), `projects_catalog.json` e integraciones MonTMC / Epsilon IA.
- **Minimización y frescura de Resumen IA**:
  1. Al cargar una release se realiza una **precarga pasiva a coste 0** (`POST /api/epsilon/resumenIA/cached`) que recupera únicamente los resúmenes ya cacheados en disco sin invocar a Epsilon IA.
  2. La consulta en vivo `GET /api/epsilon/resumenIA/<inc_id>` se ejecuta **bajo demanda** al pulsar sobre una fila concreta (o automáticamente con `?force=1` si `fechaUltimaModificacion` de Remedy es posterior a la caché, marcado en tabla con `↻ Nuevo en Remedy`).
  3. Solo se fuerza una nueva consulta manual cuando el usuario pulsa **↻ Refrescar Resumen IA** (o **✨ Generar Resumen IA**).

---

## 3. Interfaz y Reglas de Visualización

### 3.1. KPIs Clicables y Filtros
- **5 KPIs clicables como filtros rápidos** (con estado `aria-pressed` y toggle al volver a pulsar):
  - `Incidencias activas (≠ Cerrado)`
  - `Prioridad Alta / Crítica (P1–P2)`
  - `Asignadas / En Curso / Pendientes`
  - `Resueltas pendientes de cierre`
  - `Vencidas / Sin fecha` *(abiertas con `Fecha Prevista` vencida o sin fecha acordada)*
- **Filtros combinables**: búsqueda libre (`filterSearch`), estado (`filterStatus`), grupo (`filterGroup`), prioridad/urgencia (`filterPriority`) y proyecto (`filterProject`, mostrando solo el código `PRJ-*` con `summary` en tooltip).

### 3.2. Conmutador de Vista (`Tabla` / `Por proyecto`)
- **Tabla**: vista operativa detallada con **ordenación por cabeceras** (`▲` / `▼`) en `Código Incidencia`, `Fecha Apertura`, `Prioridad / Urg.`, `PROYECTO`, `Status` y `Fecha Prevista`.
- **Por proyecto**: agrupa las incidencias visibles por `PRJ-*` mostrando `Despliegue`, `summary`, conteo por prioridad (`P1`, `P2`, `P3/Otras`), resueltas, vencidas/sin fecha y un **semáforo de salud** (`Riesgo alto`, `Atención`, `Controlado`), con botones directos para filtrar en tabla o abrir cada incidencia.

### 3.3. Tabla «Incidencias en seguimiento» (12 columnas)

| # | Columna | Origen / Regla de renderizado |
| :-: | :--- | :--- |
| 1 | `Código Incidencia` | `ID de incidencia` con badge monoespaciado (`.rd-badge-code`), indicador `▸`/`▾` y badge de novedad tras sync (`Nuevo`, `Cambió estado`, `Actualizada`). |
| 2 | `Fecha Apertura` | `Fecha de envío` + indicador de antigüedad (*Aging*) para incidencias no resueltas (`> 3d` en ámbar, `> 7d` en rojo). |
| 3 | `Descripción problema` | Badge de `producto` (si existe) + `iaData.problema` (si Resumen IA está en caché) o `Descripción` de Remedy, mostrado completo sin recorte. |
| 4 | `Prioridad / Urg.` | `Prioridad` o `Urgencia` con badge semántico (`.rd-badge-critica`, `.rd-badge-alta`, `.rd-badge-media`). |
| 5 | `Sistema` | `Grupo asignado` con badge teal (`.rd-badge-sistema`). |
| 6 | `JIRA` | Bug correspondiente en Jira (`JIRA` / `Jira` / `jira`), o `-` si no viene informado. |
| 7 | `PROYECTO` | Badge de `Despliegue` con color diferenciado (`Completo` verde, `Piloto` ámbar, `Modo Oculto` morado, `PaP Técnico` azul) seguido del badge `PRJ-XXXXX`; `summary` disponible en el tooltip. |
| 8 | `Acciones` | `siguienteAccion` / `solucion` de Resumen IA (si está cargado) o `detalleSolucion`, limitado a 3 líneas con tooltip e indicador `↻ Nuevo en Remedy` si la caché está desactualizada. |
| 9 | `Status` | `Estatus` con badge de estado (`.rd-badge-asignado`, `.rd-badge-curso`, `.rd-badge-pendiente`, `.rd-badge-resuelto`). |
| 10 | `Fecha Prevista` | Si está resuelta: `Fecha de última resolución` en verde (`.rd-badge-fecha`). Si está abierta: fecha acordada editable inline (`+ Fecha` / `<input type="date">`) con semáforo (`⚠` rojo si vencida, naranja si vence hoy/mañana, amarillo si futura). |
| 11 | `Motivo Estado Resuelto` | `Motivo de estado` o `MotivoEstado_Anterior`. |
| 12 | `Grupo Peticionario` | `Grupo Remitente`. |

Además, las filas incorporan una barra lateral de acento en la primera celda según prioridad/estado (rojo para crítica/P1, naranja para alta/P2, verde para resuelta).

### 3.4. Acciones de Pie de Tabla (Footer)
En `.rd-card-footer` debajo de la tabla:
- **📋 Copiar briefing**: copia en formato doble para **Microsoft Teams / Outlook** (`text/html` + `text/plain` limpio) el resumen agrupado por prioridad, destacando compromisos vencidos y próximas acciones.
- **📋 Briefing por Sistema**: mismo formato enriquecido para Teams agrupado por la columna **Sistema** (`Grupo asignado`).
- **📥 Exportar tabla**: descarga las filas visibles respetando filtros y orden activo en CSV (`;` + BOM UTF-8) compatible con Excel español.

### 3.5. Desplegable Inline de Seguimiento (Resumen IA)
Al pulsar sobre cualquier fila de la tabla se despliega inmediatamente debajo una fila acordeón (`tr.rd-detail-row`) que muestra:
- Cabecera `Seguimiento · <ID>` con botones **📋 Copiar seguimiento**, **↻ Refrescar Resumen IA** / **✨ Generar Resumen IA** y **✕ Cerrar**.
- El apartado **✨ Resumen IA** (`Resumen Ejecutivo`, `Problema Detectado`, `Impacto`, `Causa Raíz`, `Solución Aplicada / Propuesta`, `Siguiente Acción`, `Bloqueos` e `Hitos Técnicos`).

---

## 4. Catálogo Mensual de Proyectos (`PRJ-XXXXX`) y Despliegue

Dado que las releases son mensuales, el catálogo `data/projects_catalog.json` mantiene dos índices:
- `by_release.<RELEASE>`: proyectos específicos de cada release mensual (`2026R11`, `2026R12`, etc.).
- `projects`: índice global de respaldo con metadata de release de origen.

Para importar el CSV de proyectos de una nueva release sin sobrescribir releases anteriores:

```bash
python converters/cli/update_projects_catalog.py ruta/al/fichero_proyectos.csv --release 2026R12
```

El CSV debe usar `;` como separador y contener las columnas: `JIRA;Summary;Despliegue;Descripcion`.

Para actualizar el cache-busting (`?v=...`) de CSS/JS locales en Mesa de Release y Consola de Triaje antes de desplegar:

```bash
python converters/cli/bump_asset_versions.py
```

---

## 5. Verificación

Ejecutar la suite unitaria de Mesa de Release y sincronización MonTMC:

```bash
python -m pytest converters/tests/unit/test_release_desk.py converters/tests/unit/test_sync_montmc_postmortem.py converters/tests/unit/test_m18_storage_concurrency.py converters/tests/unit/test_m19_health_and_parallel_sync.py -v
```
