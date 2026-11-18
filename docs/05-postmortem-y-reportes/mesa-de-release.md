# Consola Mesa de Release

La consola **Mesa de Release** (`/dashboards/release-desk/`) centraliza el seguimiento operativo de las incidencias de release que **no están cerradas** (`Estatus !== "Cerrado"`), integrando el catálogo de proyectos por release mensual y el **Resumen IA** de Epsilon bajo demanda.

---

## 1. Ubicación y Archivos Principales

| Componente | Ruta | Responsabilidad |
| :--- | :--- | :--- |
| Interfaz web | `dashboards/release-desk/index.html` | Estructura HTML, estilos compactos, KPIs, filtros y tabla de 12 columnas |
| Lógica cliente | `dashboards/release-desk/release-desk.js` | Carga de releases, filtros, resolución de proyectos (`PRJ-*`), acordeón inline de Resumen IA y portapapeles |
| Navegación | `dashboards/assets/topbar.js` | Registro del enlace **Mesa de Release** en la barra superior (`id: 'release-desk'`) |
| Catálogo CLI | `converters/cli/update_projects_catalog.py` | Importación incremental y no destructiva de CSVs mensuales de proyectos hacia `data/projects_catalog.json` |
| Tests unitarios | `converters/tests/unit/test_release_desk.py` | Validación de navegación, controles HTML, cabeceras de tabla, exclusión de cerradas y catálogo multi-release |

---

## 2. Fuentes de Datos y Optimización de Resumen IA

- **Índice de releases**: lee `data/output/index.json` (sección `postmortem.files`) y combina con `RAW_RELEASES` (`dashboards/release-kpis/releases-data.js`) para poblar el selector mensual (`2026R11`, `2026R10`, etc.).
- **Aislamiento de datos**: **no** consume `high_priority_notifications.json` ni `*-massive.json`; opera exclusivamente sobre los datasets de seguimiento postmortem de cada release.
- **Sincronización manual**: el botón **⚡ Sincronizar MonTMC** invoca `POST /api/sync-postmortem` con `{ release_name }` para actualizar el dataset local de la release seleccionada.
- **Minimización de consultas a Resumen IA**:
  1. Al cargar la release no se selecciona automáticamente ninguna fila ni se dispara ninguna petición a `/api/epsilon/resumenIA/`.
  2. La consulta `GET /api/epsilon/resumenIA/<inc_id>` se ejecuta **bajo demanda** únicamente al pulsar sobre una fila concreta.
  3. Los resultados se almacenan en caché en memoria (`state.iaCache`) durante la sesión y se reutilizan si se vuelve a abrir o filtrar la tabla.
  4. Solo se fuerza una nueva consulta (`?force=1`) cuando el usuario pulsa explícitamente **↻ Refrescar Resumen IA** (o **✨ Generar Resumen IA**).

---

## 3. Interfaz y Reglas de Visualización

### 3.1. KPIs y Filtros
- **KPIs compactos en barra superior**:
  - `Incidencias activas (≠ Cerrado)`
  - `Prioridad Alta / Crítica (P1–P2)`
  - `Asignadas / En Curso / Pendientes`
  - `Resueltas pendientes de cierre`
- **Filtros combinables**: búsqueda libre (`filterSearch`), estado (`filterStatus`), grupo (`filterGroup`), prioridad/urgencia (`filterPriority`) y proyecto (`filterProject`).

### 3.2. Tabla «Incidencias en seguimiento» (12 columnas)

| # | Columna | Origen / Regla de renderizado |
| :-: | :--- | :--- |
| 1 | `Código Incidencia` | `ID de incidencia` con badge monoespaciado (`.rd-badge-code`) e indicador de despliegue (`▸` / `▾`). |
| 2 | `Fecha Apertura` | `Fecha de envío`. |
| 3 | `Descripción problema` | `iaData.problema` (si Resumen IA está en caché) o `Descripción` de Remedy, limitado a 3 líneas con tooltip completo. |
| 4 | `Prioridad / Urg.` | `Prioridad` o `Urgencia` con badge semántico (`.rd-badge-critica`, `.rd-badge-alta`, `.rd-badge-media`). |
| 5 | `Sistema` | `producto` → `Grupo Resolutor` → `Grupo asignado` con badge teal (`.rd-badge-sistema`). |
| 6 | `JIRA` | Bug correspondiente en Jira (`JIRA` / `Jira` / `jira`), o `-` si no viene informado. |
| 7 | `PROYECTO` | Código `PRJ-XXXXX` resuelto desde el catálogo con badge índigo (`.rd-badge-jira`) + resumen del proyecto. |
| 8 | `Acciones` | `siguienteAccion` / `solucion` de Resumen IA (si está cargado) o `detalleSolucion`, limitado a 3 líneas con tooltip. |
| 9 | `Status` | `Estatus` con badge de estado (`.rd-badge-asignado`, `.rd-badge-curso`, `.rd-badge-pendiente`, `.rd-badge-resuelto`). |
| 10 | `Fecha Prevista` | Muestra `Fecha de última resolución` con badge verde (`.rd-badge-fecha`) **solo** si el estado contiene `resuelt` (`Resuelta` / `Resuelto`); en el resto de estados queda vacía. |
| 11 | `Motivo Estado Resuelto` | `Motivo de estado` o `MotivoEstado_Anterior`. |
| 12 | `Grupo Peticionario` | `Grupo Remitente`. |

Además, las filas incorporan una barra lateral de acento en la primera celda según prioridad/estado (rojo para crítica/P1, naranja para alta/P2, verde para resuelta).

### 3.3. Desplegable Inline de Seguimiento (Resumen IA)
Al pulsar sobre cualquier fila de la tabla se despliega inmediatamente debajo una fila acordeón (`tr.rd-detail-row`) que muestra exclusivamente:
- Cabecera `Seguimiento · <ID>` con botones **📋 Copiar seguimiento** (formatea un bloque listo para pegar en seguimientos) y **✕ Cerrar**.
- El apartado **✨ Resumen IA** (`Resumen Ejecutivo`, `Problema Detectado`, `Impacto`, `Causa Raíz`, `Solución Aplicada / Propuesta`, `Siguiente Acción`, `Bloqueos` e `Hitos Técnicos`).

Pulsar de nuevo sobre la misma fila o sobre **✕ Cerrar** pliega el desplegable.

---

## 4. Catálogo Mensual de Proyectos (`PRJ-XXXXX`)

Dado que las releases son mensuales, el catálogo `data/projects_catalog.json` mantiene dos índices:
- `by_release.<RELEASE>`: proyectos específicos de cada release mensual (`2026R11`, `2026R12`, etc.).
- `projects`: índice global de respaldo con metadata de release de origen.

Para importar el CSV de proyectos de una nueva release sin sobrescribir releases anteriores:

```bash
python converters/cli/update_projects_catalog.py ruta/al/fichero_proyectos.csv --release 2026R12
```

El CSV debe usar `;` como separador y contener las columnas: `JIRA;Summary;Despliegue;Descripcion`.

---

## 5. Verificación

Ejecutar la suite unitaria específica de Mesa de Release:

```bash
python -m pytest converters/tests/unit/test_release_desk.py -v
```
