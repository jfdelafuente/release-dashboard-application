# Estructura del Proyecto

Este documento describe la organización real del repositorio: qué vive en cada carpeta, cómo se ejecuta en local y cómo se sirve en producción (VPS + Nginx).

> Verificado explorando el repositorio y leyendo `nginx.conf`, `scripts/generate-dashboards.sh` y `.github/workflows/*.yml` el 2026-07-09. Donde no ha sido posible confirmar un dato con certeza absoluta, se indica explícitamente como **"no confirmado"**.

---

## 📁 Estructura del repositorio (raíz)

```
release-dashboard-application/
│
├── 📄 README.md                     # Punto de entrada: qué es, cómo arrancar en local
├── 📄 CLAUDE.md                     # Guía funcional de los dashboards para Claude Code
├── 📄 CHANGELOG.md
├── 📄 CONTRIBUTING.md
├── 📄 SECURITY.md
├── 📄 DIRECTORY-STRUCTURE.md        # Otro documento de estructura (histórico; ver nota más abajo)
├── 📄 DEPLOYMENT-LOG.md
├── 📄 VERSION
├── 📄 requirements.txt              # Dependencias Python de producción (raíz del repo)
├── 📄 requirements-dev.txt
├── 📄 project.json
├── 📄 skills-lock.json
├── 📄 serve_app.py                  # Servidor de desarrollo (estáticos + POST /api/upload)
├── 📄 nginx.conf                    # Config Nginx real usada en el VPS (gitignored, solo local)
│
├── 📁 converters/                   # Todo el código Python (CLI, lógica, tests, docs, specs)
├── 📁 dashboards/                   # Todo el frontend estático (HTML/CSS/JS in-line)
├── 📁 data/                         # input/output/errors — gitignored, datos reales de incidencias
├── 📁 scripts/                      # Automatización de la conversión batch en el VPS
├── 📁 docs/                         # Documentación del proyecto (este archivo incluido)
├── 📁 specs/                        # Specs de features a nivel de repo (spec-kit)
├── 📁 config/                       # .env.example, .env.development, hook de pre-commit
├── 📁 .github/workflows/            # CI: lint.yml y tests.yml (no hay deploy.yml)
├── 📁 .specify/                     # Plantillas y scripts del framework spec-kit
└── 📁 .agents/                      # Skills de agente instaladas localmente (frontend-design, etc.)
```

**Nota sobre `DIRECTORY-STRUCTURE.md`**: existe otro documento de estructura en la raíz del repo, además de este. No se ha verificado si está alineado con la realidad actual; si contradice lo que dice este documento, este documento (`docs/PROJECT-STRUCTURE.md`) es el que se acaba de auditar contra el repo real.

**Cambio importante respecto a versiones anteriores de este documento**: ya no existe un directorio `src/` con `src/converters/`, `src/dashboards/` y `src/scripts/`. El repo se reorganizó (ver `specs/005-project-organization/`) y ahora `converters/` y `dashboards/` son carpetas de primer nivel, independientes entre sí. Tampoco existe ya el concepto de "Dashboard Hub" (`dashboard-hub.html/css/js`): el punto de entrada real es `dashboards/portal/`.

---

## 📁 `converters/` — Código Python

```
converters/
├── cli/                             # Puntos de entrada ejecutables
│   ├── convert_incidents.py         # CSV de incidencias masivas → JSON
│   ├── convert_postmortems.py       # CSV de postmortem → JSON
│   ├── build_index.py               # Genera data/output/index.json
│   ├── validate_kpis.py             # Valida KPIs calculadas contra el dataset
│   └── upload_csv.py                # Usado por serve_app.py para el endpoint de subida
│
├── src/csv_to_json/                 # Lógica de conversión (paquete importado por cli/)
│   ├── converter.py                 # Orquestador principal (incidencias masivas)
│   ├── postmortem_converter.py      # Orquestador específico de postmortem
│   ├── encoding.py                  # Detección de encoding
│   ├── delimiter.py                 # Detección de delimitador
│   ├── normalizers.py               # Normalización de campos (Urgencia, Estatus, fechas...)
│   ├── validators.py                # Validación de registros
│   ├── schemas.py                   # Reglas de campo para incidencias masivas
│   └── postmortem_schemas.py        # Reglas de campo para postmortem
│
├── scripts/bin/                     # Wrappers de conveniencia para invocar los CLI
│   ├── convert_incidents.sh / .bat
│   └── convert_postmortems.sh / .bat
│
├── tests/                           # unit/, integration/, e2e/, performance/, utils/
├── docs/                            # API.md, ARCHITECTURE.md, CODE_QUALITY.md,
│                                     # CSV-TO-JSON-WORKFLOW.md, PERFORMANCE.md,
│                                     # TESTING_BEST_PRACTICES.md, TEST_STRUCTURE*.md
├── specs/                           # 001-csv-to-json-workflow/, 004-postmortem-converter/,
│                                     # 006-optimize-csv-converters/
├── requirements.txt / requirements-dev.txt
├── pytest.ini
└── README.md
```

`converters/` es autocontenido: tiene su propio `README.md`, sus propios `requirements*.txt` y su propia suite de tests (duplican, casi al carácter, los de la raíz del repo — no se ha confirmado por qué existen ambos conjuntos ni cuál es la fuente de verdad; **no confirmado**).

Ver [`converters/README.md`](../converters/README.md) y [`converters/docs/API.md`](../converters/docs/API.md) para el uso detallado de cada conversor.

---

## 📁 `dashboards/` — Frontend estático

```
dashboards/
├── index.html                # Redirige (meta-refresh + JS) a /dashboards/portal/
├── portal/index.html         # Portal / punto de entrada principal
├── massive-incidents/index.html
├── postmortem/index.html
├── release-kpis/             # index.html, app.js, style.css, colors_and_type.css, releases-data.js
├── assets/                   # Compartido por los 4 dashboards
│   ├── masorange-logo-negative.svg
│   ├── masorange-logo-positive.svg
│   ├── masorange-mark.svg
│   ├── tokens.css            # Variables de diseño (única fuente de tokens)
│   ├── topbar.css            # Barra superior MASORANGE
│   ├── topbar.js             # Inyecta la barra superior con la nav activa marcada
│   └── shared.css            # Framework de los 3 dashboards "clásicos" (importa tokens.css/topbar.css)
└── README.md
```

Sin build step: cada dashboard es un `.html` con su CSS y JavaScript propios en línea (salvo Plotly.js y Google Fonts, vía CDN), más el framework compartido de `assets/`. El portal (`dashboards/portal/`) es el punto de acceso único, con tarjetas hacia cada dashboard y hacia los paneles hermanos (`/reportes-incidencias`, `/problemas`), que **no** forman parte de este repositorio.

Ver [`dashboards/README.md`](../dashboards/README.md) para el detalle funcional de cada dashboard.

---

## 📁 `data/` — Datos (no versionados)

```
data/
├── input/     # CSVs de origen (colocados manualmente o vía POST /api/upload)
├── output/    # JSONs generados por los conversores + index.json
└── errors/    # Reportes de error por cada conversión (uno por CSV)
```

Los tres subdirectorios están cubiertos por `.gitignore` (línea `data/` en `.gitignore`): nada de lo que hay dentro se versiona. No existe un directorio `data/archive/` en el repo actual (a diferencia de lo que describían versiones anteriores de este documento).

---

## 📁 `scripts/` — Automatización

```
scripts/
├── generate-dashboards.sh   # Cron de conversión batch en el VPS
└── README.md
```

Es el único script que queda en `scripts/` (las anteriores menciones a `health-check.sh`, `backup.sh`, `watch-and-convert.sh` ya no existen). `generate-dashboards.sh`:

- Define `PROJECT_ROOT="/infocodes/project/release-dashboard-application"` (corregido recientemente, ver commit `df2550d`).
- Recorre `data/input/*.csv`; si el nombre de archivo contiene `postmortem` usa `convert_postmortems.py`, en caso contrario `convert_incidents.py`.
- Al terminar, regenera `data/output/index.json` con `build_index.py`.
- Pensado para ejecutarse por `crontab` en el VPS (ver ejemplos en [`scripts/README.md`](../scripts/README.md)).

**Nota de coherencia**: `scripts/README.md` todavía muestra algunos ejemplos con la ruta `/infocodes/release-dashboard-application/` (sin `/project/`), que no coincide con el `PROJECT_ROOT` real del script ni con las rutas de `nginx.conf`. La ruta correcta y confirmada es `/infocodes/project/release-dashboard-application/`.

---

## 🖥️ `serve_app.py` — Servidor de desarrollo

Servidor HTTP en Python puro (`http.server` + `socketserver`), pensado para desarrollo local en Windows. Se lanza desde la raíz del repo:

```bash
python serve_app.py
# http://localhost:8000/dashboards/portal/
```

Responsabilidades:
- Sirve todos los archivos estáticos del repo (dashboards, data, etc.) desde `PROJECT_ROOT`.
- Sirve `data/output/index.json` de forma dinámica (relee el archivo en cada petición, con `Cache-Control: no-cache`, para evitar que el navegador cachee un índice desactualizado).
- Expone `POST /api/upload`: recibe un CSV vía `multipart/form-data` (campos `file` y `type`), lo guarda en `data/input/`, invoca `converters/cli/upload_csv.py::run_upload()` para convertirlo, y devuelve el resultado como JSON.

Si solo se necesita lectura de datos ya generados (sin subir CSVs desde el navegador), basta con `python -m http.server 8000` o Live Server — pero entonces `POST /api/upload` no existe y la subida desde el navegador falla con "Failed to fetch".

---

## 🔄 CI: `.github/workflows/`

```
.github/workflows/
├── lint.yml    # flake8, black, isort, pylint, bandit (sobre push/PR a main, develop)
└── tests.yml   # pytest + cobertura (matriz Python 3.8-3.11), gate de 80% de cobertura
```

**No existe `deploy.yml`**: se eliminó porque no se usaba y estaba roto. Actualmente no hay ningún pipeline de despliegue automático desde GitHub Actions; el despliegue al VPS es manual (ver más abajo).

Aviso de coherencia interna en `lint.yml` y `tests.yml`: ambos siguen invocando `src`/`src.converters` (p. ej. `flake8 src tests`, `pytest --cov=src.converters`), rutas que ya no existen tras la reorganización a `converters/`. **No confirmado** si estos workflows pasan realmente en su estado actual o si están rotos por este desajuste; no se ha ejecutado el CI como parte de esta auditoría.

---

## 🌐 Producción (VPS) — configuración real de `nginx.conf`

A diferencia de lo que describían versiones anteriores de este documento, **no existe** una estructura `/var/www/release-dashboard/{static,app}` ni un paso de "copia" de archivos al servidor. En producción, Nginx apunta **directamente** al checkout de este repositorio (actualizado con `git pull` manual) mediante `alias`, sin build ni etapa intermedia.

Datos confirmados leyendo `nginx.conf` (archivo local, no versionado — está en `.gitignore`):

- El repo vive en el VPS en `/infocodes/project/release-dashboard-application` (coincide con `PROJECT_ROOT` de `generate-dashboards.sh`).
- Nginx escucha en el puerto `8081`, `server_name 10.132.68.85 infocodes.si.orange.es`.
- `location /dashboards` → `alias /infocodes/project/release-dashboard-application/dashboards;` (sirve el HTML estático directamente desde el repo).
- `location /data` → `alias /infocodes/project/release-dashboard-application/data;` con `autoindex off` (sirve los JSON generados por los conversores).
- `location /api` → `proxy_pass http://fastapi_backend;` con `upstream fastapi_backend { server localhost:8000; }`. Este backend FastAPI vive en el repo hermano `cso-incident-masivas-report` (**no confirmado directamente desde `nginx.conf`**, que solo define el upstream por puerto; la asociación con ese repo se da por indicación externa a este documento).
- `location /reportes-incidencias` → `alias /infocodes/project/cso-incident-masivas-report/app;` — app estática de otro repo hermano, ajena a este proyecto.
- `location /problemas` → `proxy_pass http://gestion_problemas_backend;` con `upstream gestion_problemas_backend { server localhost:3001; }`. Es una app Next.js con `basePath=/problemas`, gestionada con `pm2` (según comentario en el propio `nginx.conf`); tampoco pertenece a este repositorio.
- `location /static` → `alias /infocodes/project/dashboardsonar-application-python/infocodest/static;` — de otra aplicación distinta (`dashboardsonar-application-python`), no relacionada con este proyecto.
- `location /` (raíz) → `proxy_pass http://unix:/infocodes/var/run/infocodes.sock;` con `proxy_cache`, es decir, delega a otra aplicación vía socket Unix; este proyecto no ocupa la raíz del dominio.

En resumen, este repositorio solo controla `/dashboards` (estático) y `/data` (JSON generados); todo lo demás en `nginx.conf` pertenece a aplicaciones hermanas que conviven en el mismo VPS y mismo dominio.

**Generación de los JSON en el VPS**: no vía CI/CD, sino por `scripts/generate-dashboards.sh` ejecutado periódicamente (cron — la periodicidad exacta configurada en el `crontab` real del VPS **no está confirmada**; `scripts/README.md` solo documenta opciones sugeridas).

---

## 📋 Tabla: quién sirve qué

| Recurso | Ubicación en el repo | Quién lo sirve en producción |
|---|---|---|
| `portal/index.html`, resto de `*.html` de `dashboards/` | `dashboards/` | Nginx, `alias /dashboards` |
| Logos SVG | `dashboards/assets/` | Nginx, `alias /dashboards` |
| `index.json`, `*-massive.json`, `*-postmortem.json` | `data/output/` | Nginx, `alias /data` (autoindex off) |
| CSVs de origen | `data/input/` | No se sirven vía Nginx; los escribe `serve_app.py` (dev) o se colocan manualmente (VPS) |
| Conversores Python | `converters/` | Se ejecutan por `scripts/generate-dashboards.sh` (cron) en el VPS, o manualmente/vía `serve_app.py` en local |
| `/api/*` | Fuera de este repo | Backend FastAPI de otro repo (proxy Nginx a `localhost:8000`) |

---

## 🚀 Local vs Producción, en una frase

- **Local (desarrollo)**: `python serve_app.py` desde la raíz sirve todo el repo (`dashboards/`, `data/`) y añade `POST /api/upload` para convertir CSVs desde el navegador. Alternativa de solo lectura: `python -m http.server 8000` o Live Server (sin subida de CSV).
- **Producción (VPS)**: Nginx sirve `dashboards/` y `data/` directamente desde el checkout git del repo vía `alias` (sin copiar archivos a otra ruta); los JSON de `data/output/` se regeneran periódicamente con `scripts/generate-dashboards.sh` vía cron; no hay backend propio de este repo para `/api` (es de un repo hermano) ni pipeline de despliegue automático (no hay `deploy.yml`).

---

## Referencias

- [`../CLAUDE.md`](../CLAUDE.md) — comportamiento funcional detallado de ambos dashboards y de los conversores
- [`../converters/README.md`](../converters/README.md) — uso de los conversores CSV→JSON
- [`../converters/docs/API.md`](../converters/docs/API.md) — contrato de los JSON de salida
- [`../dashboards/README.md`](../dashboards/README.md) — estructura y uso de los dashboards
- [`../scripts/README.md`](../scripts/README.md) — instalación y crontab de `generate-dashboards.sh`
- [`../.github/workflows/lint.yml`](../.github/workflows/lint.yml), [`../.github/workflows/tests.yml`](../.github/workflows/tests.yml) — pipelines de CI

---

**Última actualización**: 2026-07-09
