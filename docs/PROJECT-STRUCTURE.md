# Estructura del Proyecto

Este documento describe la organización real y auditada del repositorio: qué vive en cada carpeta, cómo se ejecuta en el entorno local de desarrollo y cómo se despliega y sirve en producción (VPS + Nginx con arquitectura Standalone Runtime y Storage Desacoplado).

> **Estado**: Auditado y verificado el 2026-10-20 conforme a la arquitectura de producción en `10.132.26.96`, configuración activa de Nginx (`nginx.conf`), scripts de automatización (`deploy-production.ps1`, `status.sh`, `rollback.sh`), almacenamiento desacoplado (`/infocodes/var/storage/`) y workflows de CI en `.github/workflows/`.

---

## 📁 Estructura del Repositorio (Raíz)

```text
release-dashboard-application/
│
├── 📄 README.md                     # Punto de entrada: qué es, arquitectura y cómo arrancar en local
├── 📄 CLAUDE.md                     # Guía funcional de dashboards y conversores
├── 📄 CHANGELOG.md                  # Registro histórico de versiones y cambios
├── 📄 CONTRIBUTING.md               # Guía de contribución y flujo de desarrollo
├── 📄 SECURITY.md                   # Políticas de reporte de vulnerabilidades
├── 📄 VERSION                       # Versión semántica actual de la aplicación
├── 📄 requirements.txt              # Dependencias Python principales de producción
├── 📄 requirements-dev.txt          # Herramientas de testing, linting y análisis estático
├── 📄 skills-lock.json              # Registro de dependencias de agentes de IA
├── 📄 serve_app.py                  # Servidor local de desarrollo (puerto 8080, estáticos, subida CSV, proxies)
├── 📄 deploy.sh                     # Script informativo de ayuda (redirige a deploy-production.ps1 / status.sh)
├── 📄 nginx.conf                    # Configuración de Nginx (copia activa en /infocodes/nginx/conf/nginx.conf)
│
├── 📁 converters/                   # Todo el código Python (CLI, lógica core, tests, docs, specs)
├── 📁 dashboards/                   # Todo el frontend estático (HTML/CSS/JS in-line y assets compartidos)
├── 📁 data/                         # input/output/reports/errors/archive — gitignored (fallback local)
├── 📁 scripts/                      # Scripts de despliegue PowerShell, sondas de salud, rollback y cron batch
├── 📁 docs/                         # Documentación técnica y operacional del proyecto
├── 📁 specs/                        # Especificaciones de features a nivel de repositorio (spec-kit)
├── 📁 config/                       # Plantillas .env.example, .env.development y hooks git
├── 📁 .github/workflows/            # CI: tests.yml y lint.yml (GitHub Actions para main y production)
├── 📁 .specify/                     # Plantillas y scripts del framework spec-kit
└── 📁 .agents/                      # Skills y extensiones de agentes locales (frontend-design, etc.)
```

**Principios de organización**:
- **Separación de responsabilidades**: Las carpetas `converters/` (lógica Python) y `dashboards/` (frontend estático) son independientes de primer nivel. No existe directorio `src/` ni componentes huérfanos.
- **Punto de entrada unificado**: El portal (`dashboards/portal/`) es el centro neurálgico que aglutina el acceso a todos los dashboards, métricas y herramientas del ecosistema.
- **Identidad corporativa**: Todo el frontend cumple estrictamente con el manual de marca corporativo **Orange** (prohibido el uso de MASORANGE u otras marcas).

---

## 📁 `converters/` — Código Python

```text
converters/
├── cli/                             # Puntos de entrada ejecutables por línea de comandos
│   ├── convert_incidents.py         # CSV de incidencias masivas → JSON
│   ├── convert_postmortems.py       # CSV de postmortem → JSON
│   ├── build_index.py               # Genera el catálogo data/output/index.json
│   ├── validate_kpis.py             # Valida el cálculo de KPIs contra el dataset
│   ├── upload_csv.py                # Invocado por serve_app.py para la subida interactiva
│   ├── generate_postmortem_report.py # Generación de informes ejecutivos PowerPoint
│   └── test_performance.py          # Benchmark y métricas de procesamiento
│
├── src/csv_to_json/                 # Lógica de conversión (paquete modular)
│   ├── converter.py                 # Orquestador de incidencias masivas
│   ├── postmortem_converter.py      # Orquestador de postmortems
│   ├── encoding.py                  # Detección y normalización de encoding (UTF-8, Latin-1, CP1252)
│   ├── delimiter.py                 # Detección inteligente de delimitadores (;, ,, \t)
│   ├── normalizers.py               # Normalización de campos (fechas ISO, Urgencia, Estatus...)
│   ├── validators.py                # Validación de integridad de registros
│   ├── schemas.py                   # Esquemas y contratos para incidencias masivas
│   └── postmortem_schemas.py        # Esquemas y contratos para postmortems
│
├── scripts/bin/                     # Wrappers de ejecución rápida en terminal
│   ├── convert_incidents.sh / .bat
│   └── convert_postmortems.sh / .bat
│
├── tests/                           # Suite de pruebas automatizadas (516+ tests)
│   ├── unit/                        # Tests unitarios de conversores, delimitadores y normalizadores
│   ├── integration/                 # Tests de integración end-to-end con archivos CSV reales
│   ├── e2e/                         # Verificación de flujo completo CSV → JSON → index.json
│   ├── performance/                 # Pruebas de carga, memoria y rendimiento
│   └── utils/                       # Generadores de fixtures y aserciones comunes
├── docs/                            # Documentación técnica interna de converters
│   ├── API.md                       # Contrato de datos y esquemas JSON de salida
│   ├── ARCHITECTURE.md              # Diseño de arquitectura del motor conversor
│   ├── CODE_QUALITY.md              # Métricas de cobertura y estándares de código
│   ├── CSV-TO-JSON-WORKFLOW.md      # Flujo de conversión y tratamiento de errores
│   └── PERFORMANCE.md               # Análisis de complejidad algorítmica y tiempos
├── specs/                           # Especificaciones de features de conversión (001, 004, 006)
├── requirements.txt / requirements-dev.txt
├── pytest.ini                       # Configuración de pytest (paths, markers y cobertura)
└── README.md                        # Documentación rápida del paquete
```

El módulo `converters/` es autocontenido y puede ejecutarse de manera desacoplada del frontend tanto en local como en los cron jobs del servidor.

---

## 📁 `dashboards/` — Frontend Estático

```text
dashboards/
├── index.html                       # Redirección automática hacia /dashboards/portal/
├── portal/index.html                # Portal principal unificado: buscador, KPIs globales y accesos
├── massive-incidents/index.html     # Dashboard de Incidencias Masivas (filtros, tabla y gráficos)
├── postmortem/index.html            # Dashboard de Postmortem e Informes ejecutivos
├── release-kpis/                    # Dashboard de KPIs de Releases y Despliegues
│   ├── index.html
│   ├── app.js
│   ├── style.css
│   ├── colors_and_type.css
│   └── releases-data.js
├── reportes-incidencias/            # Dashboard y panel de gestión de informes de incidencias
├── assets/                          # Recursos compartidos por todos los dashboards
│   ├── orange-logo.svg              # Isotipo y logotipo oficial Orange
│   ├── tokens.css                   # Variables de diseño (colores #FF7900, tipografías, espaciados)
│   ├── topbar.css                   # Estilos de la barra de navegación superior unificada
│   ├── topbar.js                    # Inyección dinámica de cabecera con navegación activa
│   ├── shared.css                   # Framework CSS común para vistas de dashboards
│   ├── resumen-ia.css               # Estilos visuales del modal flotante Epsilon IA
│   └── resumen-ia.js                # Cliente JavaScript y lógica interactiva de Epsilon IA
└── README.md                        # Guía funcional de los dashboards
```

**Características frontend**:
- **Zero Build Step**: Sin Node.js ni bundlers en tiempo de despliegue. Archivos HTML/CSS/JavaScript nativos listos para ser servidos directamente por Nginx o `serve_app.py`.
- **Librerías externas**: Plotly.js para visualizaciones y fuentes tipográficas cargadas eficientemente.
- **Asistencia con IA**: Componente flotante `resumen-ia.js` integrado en los dashboards para consultar análisis semánticos vía Epsilon IA.

---

## 📁 `data/` vs Almacenamiento Desacoplado (`/infocodes/var/storage/`)

El tratamiento de los datos difiere deliberadamente entre el desarrollo local y el entorno de producción para garantizar que **ningún despliegue sobrescriba datos reales**:

```text
Estructura de Datos:
├── input/      # Archivos CSV origen (subidos manualmente o por endpoint /api/upload)
├── output/     # Archivos JSON convertidos (*-massive.json, *-postmortem.json, index.json)
├── reports/    # Informes generados (presentaciones PowerPoint ejecutivas .pptx)
├── errors/     # Informes de errores y discrepancias de validación por CSV
└── archive/    # Archivos históricos archivados
```

| Ámbito | Ubicación Física | Comportamiento |
|---|---|---|
| **Local (Desarrollo)** | `<repo>/data/` | Ignorado por `.gitignore`. Sirve como fallback local automático para `serve_app.py` y los conversores CLI. |
| **Producción (VPS)** | `/infocodes/var/storage/release-dashboard/` | Almacenamiento persistente fuera del ciclo de vida del código. Las releases se conectan vía enlace simbólico (`current/data -> /infocodes/var/storage/release-dashboard`). |
| **Informes Ejecutivos** | `/infocodes/var/storage/executive_pptx/` | Almacenamiento persistente para PPTX individuales generados por el backend CSO (`reports/executive` es un symlink a esta ruta). |

---

## 📁 `scripts/` — Automatización y Despliegue

```text
scripts/
├── deploy-production.ps1    # Script principal de despliegue Standalone Runtime desde Windows
├── status.sh                # Sondas de salud Nginx, endpoints HTTP y métricas de storage en VPS
├── rollback.sh              # Reversión instantánea a backups preventivos o releases previas en VPS
├── generate-dashboards.sh   # Cron de procesamiento batch de CSVs a JSON en el VPS
├── deploy.sh                # Script informativo en servidor (orienta hacia status.sh o despliegue local)
└── README.md                # Referencia detallada de parámetros, crontab y diagnósticos
```

**Mecanismo de Despliegue Standalone Runtime (`deploy-production.ps1`)**:
1. **Validación Git**: Exige rama `production` limpia y sincronizada con GitHub.
2. **Empaquetado Selectivo**: Genera un artefacto ligero (`dist/release-dashboard-runtime.tar.gz`, ~2.3 MB) conteniendo únicamente `dashboards/`, `converters/`, `scripts/`, `nginx.conf`, `requirements.txt` y `VERSION`. Excluye `.git`, tests, documentación y `data/`.
3. **Transferencia SCP**: Sube el tarball al host `infocodes@10.132.26.96:/tmp/`.
4. **Copia Preventiva**: Crea backup en `/infocodes/var/backups/release-dashboard-application/backup_<TIMESTAMP>.tar.gz`.
5. **Extracción Atómica**: Descomprime en `/infocodes/project/release-dashboard-application/releases/<TIMESTAMP>`.
6. **Enlace Simbólico**: Actualiza el symlink atómico `current -> releases/<TIMESTAMP>` y reconecta `current/data` al almacenamiento persistente desacoplado.
7. **Validación y Recarga**: Ejecuta `nginx -t` y `nginx -s reload` sin caída de servicio (con rollback automático si la sintaxis falla).
8. **Smoke Tests**: Verifica respuestas HTTP 200 en todos los dashboards y proxies.

---

## 🖥️ `serve_app.py` — Servidor de Desarrollo Local

Servidor HTTP basado en Python (`http.server` + `socketserver`) diseñado para desarrollo rápido en Windows/Linux sin dependencias complejas.

```bash
# Ejecutar desde la raíz del proyecto
python serve_app.py

# Salida:
# Dashboard Portal: http://localhost:8080/dashboards/portal/
# API FastAPI (proxy/referencia): http://localhost:8000/docs
```

**Capacidades integradas**:
- **Puerto 8080 por defecto**: Evita conflictos con FastAPI (que opera en el puerto `8000`). Configurable mediante `--port <puerto>` o la variable de entorno `PORT`.
- **Servicio de estáticos**: Sirve `dashboards/`, `assets/` y datos con cabeceras de no-caché para refresco instantáneo.
- **Endpoint `POST /api/upload`**: Permite arrastrar CSVs desde la interfaz, almacenándolos en `data/input/` y ejecutando automáticamente `upload_csv.py` para generar el JSON correspondiente.
- **Proxy Epsilon IA (`/api/epsilon/*`)**: Reenvía peticiones al servicio oficial de Epsilon IA con caché en memoria para probar el modal de Resumen IA en local.
- **Generación de informes PowerPoint**: Integra soporte para emitir reportes postmortem ejecutivos (`/api/v1/reports/executive-incident/...`).
- **Proxy `/problemas`**: Redirige peticiones a `http://localhost:3001` si la aplicación Next.js de Gestión de Problemas está activa.

---

## 🔄 CI: `.github/workflows/`

El repositorio dispone de integración continua automatizada para las ramas `main` y `production`:

```text
.github/workflows/
├── tests.yml    # Pytest, cobertura (gate >= 80%), Python 3.11 en ubuntu-latest
└── lint.yml     # Flake8, Black, isort y Pylint en ubuntu-latest
```

- **Ejecución en subdirectorio**: Ambos workflows están configurados con `defaults.run.working-directory: converters`, asegurando la resolución exacta de dependencias y rutas de módulos.
- **Gate de Calidad**: `tests.yml` ejecuta los 516+ tests automatizados con verificación de cobertura estricta.
- **Despliegue fuera de CI**: Por seguridad y aislamiento de red en la infraestructura interna de Orange, no existe despliegue directo desde GitHub Actions hacia el VPS. El despliegue se gestiona de forma controlada mediante `deploy-production.ps1` desde puestos autorizados.

---

## 🌐 Producción (VPS) — Arquitectura y Nginx

### Topología del Servidor

- **Host**: `10.132.26.96` (`infocodes@10.132.26.96`)
- **Dominio**: `infocodes.si.orange.es`
- **Puerto Nginx**: Escucha en `8081` (y proxy reverso HTTP estándar)
- **Ruta Base del Proyecto**: `/infocodes/project/release-dashboard-application`
- **Ruta de Releases**: `/infocodes/project/release-dashboard-application/releases/`
- **Symlink Activo**: `/infocodes/project/release-dashboard-application/current`
- **Storage Persistente**: `/infocodes/var/storage/release-dashboard/`
- **Executive Storage**: `/infocodes/var/storage/executive_pptx/`

### Mapeo de Rutas en `nginx.conf`

```text
Petición entrante (infocodes.si.orange.es:8081)
│
├── /dashboards/ ─────────► alias .../current/dashboards/ (HTML/JS/CSS estático)
├── /data/ ───────────────► alias /infocodes/var/storage/release-dashboard/ (JSON datasets)
├── /api/epsilon/ ────────► proxy_pass https://soptmc.si.orange.es/MonTMC/api/epsilon/
├── /reportes-incidencias ─► conf.d/cso-incident.conf (Frontend incidencias masivas)
├── /api/ ────────────────► proxy_pass http://localhost:8000 (FastAPI backend - cso-incident)
├── /problemas ───────────► proxy_pass http://localhost:3001 (Next.js con pm2)
├── /static/ ─────────────► alias .../dashboardsonar-application-python/static/
└── / (raíz) ─────────────► proxy_pass http://unix:/infocodes/var/run/infocodes.sock
```

---

## 📋 Tabla: Quién Sirve Qué (Matriz de Responsabilidades)

| Recurso / Ruta | Entorno Local (Desarrollo) | Entorno Producción (VPS) | Notas |
|---|---|---|---|
| `/dashboards/portal/` y dashboards | `serve_app.py` (:8080) | Nginx (`alias .../current/dashboards`) | Frontend estático sin compilación |
| `/dashboards/assets/*` (logos, tokens) | `serve_app.py` (:8080) | Nginx (`alias .../current/dashboards/assets`) | Identidad visual estricta Orange |
| `/data/output/*.json` e `index.json` | `serve_app.py` desde `<repo>/data/` | Nginx (`alias /infocodes/var/storage/release-dashboard`) | Almacenamiento desacoplado persistente |
| `/api/upload` (subida CSV) | `serve_app.py` (invoca `upload_csv.py`) | No expuesto públicamente / vía cron batch | Cron: `scripts/generate-dashboards.sh` |
| `/api/epsilon/*` | Proxy local en `serve_app.py` con caché | Proxy reverso Nginx hacia `soptmc.si.orange.es` | Provee datos para el modal flotante IA |
| `/api/v1/reports/executive-incident` | `serve_app.py` (motor CSO integrado) | Backend FastAPI en `localhost:8000` | Generación de presentaciones PPTX |
| `/problemas` | Proxy local opcional (:3001) | Next.js en `localhost:3001` (vía pm2) | Aplicación hermana en el VPS |

---

## 🚀 Local vs Producción, en Síntesis

- **Local (Desarrollo)**: Se ejecuta `python serve_app.py` en el puerto `8080`. Sirve directamente los archivos de trabajo locales de `dashboards/` y `data/`, ofrece el endpoint interactivo `POST /api/upload` para procesar nuevos CSVs y actúa como proxy para los servicios auxiliares sin interferir con FastAPI en el puerto `8000`.
- **Producción (VPS)**: Nginx atiende peticiones en el puerto `8081` sirviendo el código estático desde el release activo (`current/dashboards`) y los datasets desde el almacenamiento persistente desacoplado (`/infocodes/var/storage/release-dashboard`). Las actualizaciones se efectúan sin Git mediante artefactos atómicos generados por `deploy-production.ps1` con posibilidad de rollback inmediato.

---

## Referencias y Documentación Relacionada

- [README.md](../README.md) — Visión general y arranque rápido del proyecto.
- [DEPLOYMENT.md](DEPLOYMENT.md) — Manual integral de despliegue, topología de red y protocolos de contingencia.
- [DEVELOPMENT.md](DEVELOPMENT.md) — Guía completa de configuración de entorno, ejecución de tests y convenciones.
- [GITHUB-BRANCH-PROTECTION.md](GITHUB-BRANCH-PROTECTION.md) — Reglas de protección de ramas para `production` y `main`.
- [CI.md](CI.md) — Arquitectura y detalle de pipelines de GitHub Actions.
- [LOGS.md](LOGS.md) — Estándar unificado de bitácora y registro de actividad técnica.
- [INFORME-EJECUTIVO-POSTMORTEM.md](INFORME-EJECUTIVO-POSTMORTEM.md) — Guía de generación de informes individuales ejecutivos.
- [INFORME-PPT-POSTMORTEM.md](INFORME-PPT-POSTMORTEM.md) — Generación masiva batch de informes PowerPoint.
- [MIGRATION.md](MIGRATION.md) — Histórico de modernización, esquemas y compatibilidad con JavaScript.
