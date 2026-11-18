---
name: release-opening-workflow
description: Automatiza la apertura de una nueva Release mensual (YYYYRMM, ej. 2026R12): valida el código de release, la registra de forma idempotente en dashboards/release-kpis/releases-data.js, importa opcionalmente el catálogo de proyectos PRJ-* en data/projects_catalog.json y dispara o verifica la sincronización con MonTMC. Úsese siempre que se invoque el agente release-opener o el usuario pida abrir una release.
---

# Flujo de Apertura de Release Mensual (`release-opening-workflow`)

Esta skill define el procedimiento determinista para abrir una nueva Release mensual en `release-dashboard-application` a partir únicamente del código `YYYYRMM` (por ejemplo, `2026R12`).

---

## 1. Entrada y Validación

1. **Código obligatorio (`YYYYRMM`):**
   - Debe cumplir el patrón `^\d{4}R([1-9]|1[0-2])$` (ej. `2026R12`).
   - Si el usuario no indica `YYYYRMM` o el formato es ambiguo, detente y pregúntale el código exacto antes de modificar ficheros.
2. **Parámetros opcionales (no bloqueantes si faltan):**
   - `--fecha-pap`: fecha de PaP en formato `"D-mes."` (ej. `"13-dic."`). Si no se indica, se deja `""` y `open_release.py` infiere automáticamente el nombre del mes en español.
   - `--projects-csv`: ruta a un CSV (`;`-separado con columnas `JIRA;Summary;Despliegue;Descripcion`). Si existe un fichero candidato evidente (p. ej. `proyecto_r12.csv` o `ProyectosR12.md`), pregunta antes si hay ambigüedad; si no hay catálogo todavía, continúa con el alta de la release e informa de que puede importarse más tarde.
   - `--sync-url`: URL del servidor del dashboard (p. ej. `http://localhost:8000`) si está levantado para ejecutar `POST /api/sync-postmortem`.

---

## 2. Pasos de Ejecución

### Paso 1 · Ejecutar el script oficial `open_release.py`
Ejecuta el CLI determinista en la raíz del repositorio:

```bash
python converters/cli/open_release.py <YYYYRMM> [--fecha-pap "<fecha>"] [--projects-csv "<ruta_csv>"] [--sync-url "http://localhost:8000"]
```

Qué realiza este comando:
1. Valida `YYYYRMM` y calcula `Año` y `Mes`.
2. Registra `["<YYYYRMM>", <Año>, "<fecha_pap>", "<Mes>", 0, 0, 0, 0],` en `dashboards/release-kpis/releases-data.js` de forma idempotente (si ya existe, no la duplica).
3. Si se proporcionó `--projects-csv`, llama a `update_projects_catalog(...)` para añadir `by_release["<YYYYRMM>"]` en `data/projects_catalog.json` preservando el histórico de releases previas.
4. Si se proporcionó `--sync-url`, lanza `POST /api/sync-postmortem` con `{"release_name": "<YYYYRMM>"}`.

### Paso 2 · Si se proporciona un Markdown de proyectos (ej. `ProyectosR12.md`)
Si el usuario entrega un `.md` en lugar de un `.csv`, extrae `JIRA;Summary;Despliegue;Descripcion` a un CSV temporal en `scratch/` y ejecuta `converters/cli/open_release.py <YYYYRMM> --projects-csv <scratch_csv>`.

### Paso 3 · Verificar tests unitarios
Ejecuta siempre tras los cambios:

```bash
python -m pytest converters/tests/unit/test_open_release.py converters/tests/unit/test_release_desk.py -v
```

### Paso 4 · Sincronización MonTMC (si el servidor no estaba activo)
Si no se pudo sincronizar automáticamente porque el servidor web no estaba levantado, indícale al usuario que al abrir **Mesa de Release** (`/dashboards/release-desk/?release=<YYYYRMM>`) solo tiene que pulsar **⚡ Sincronizar MonTMC**.

---

## 3. Reglas de Seguridad y Git

- **No** añadas ni commitees `data/output/*.json`, `data/projects_catalog.json` ni otros ficheros locales de `data/` (están en `.gitignore`).
- Si el usuario solicita subir los cambios, commitea únicamente `dashboards/release-kpis/releases-data.js` (y no ficheros de datos locales).
