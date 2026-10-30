# Release Dashboard Application

Plataforma analítica y de reporting para la monitorización de calidad técnica en despliegues (*releases*), gestión de incidencias masivas y análisis postmortem operativo (entorno Orange).

El repositorio centraliza:

1. **La suite completa de frontends web (dashboards)**: Portal unificado con buscador y Resumen IA en tiempo real (Epsilon IA), Incidencias Masivas, Postmortem/Release, KPIs Históricos de Release, el editor/visor de **Reportes de Incidencias** y el **Catálogo de Agentes IA y Skills**.
2. **El motor de conversión y normalización en Python**: Ingesta por lotes o web de CSVs de Remedy, detección de encoding/delimitador y pre-cálculo de KPIs analíticas.
3. **El generador de presentaciones ejecutivas en PowerPoint (`.pptx`)**: Informes corporativos de release e incidencias individuales bajo demanda.
4. **Infraestructura de servidor local y producción**: Servidor de desarrollo [`serve_app.py`](serve_app.py) con proxy CORS para Epsilon IA y backend FastAPI, y configuración Nginx para el servidor VPS.

---

## 📦 Arquitectura de Componentes

| Componente | Ubicación | Descripción | Tecnología |
| ----------- | ----------- | ------------- | ----------- |
| **Dashboards** | [`dashboards/`](dashboards/) | Frontends web estáticos: Portal, Incidencias Masivas, Postmortem/Release, Release KPIs, Reportes de Incidencias y **Catálogo de Agentes IA** | HTML5 / CSS3 / JavaScript (Vanilla ES6+) |
| **Converters** | [`converters/`](converters/) | Motor de procesamiento CSV→JSON, saneamiento, validación y métricas pre-calculadas | Python 3.10+ / 3.11 |
| **Report Generator** | [`converters/src/report_generator/`](converters/src/report_generator/) | Generación programática de presentaciones ejecutivas corporativas (`.pptx`) | `python-pptx`, `matplotlib`, `plotly` |
| **Servidor / Gateway** | [`serve_app.py`](serve_app.py) / [`nginx.conf`](nginx.conf) | Servidor local con endpoints de subida `/api/upload`, proxy Epsilon IA y FastAPI, y config Nginx VPS | Python / Nginx |

---

## 🚀 Inicio Rápido (5 minutos)

### 1️⃣ Arranca el servidor local

```bash
python serve_app.py
# Abre: http://localhost:8080/dashboards/portal/
```

> ⚠️ **No uses `python -m http.server` ni Live Server.** Solo sirven
> archivos estáticos: no implementan `POST` (la subida de CSV
> desde el navegador fallaría con "Failed to fetch") ni el proxy para evitar
> restricciones CORS al consultar Epsilon IA. `serve_app.py` añade los
> endpoints `/api/upload` y `/api/epsilon/resumenIA/<codigo>`, imprescindibles
> para el funcionamiento completo en local.

### 2️⃣ Carga un CSV

**Opción A: Desde el navegador (recomendado)**

Cada dashboard (Incidencias Masivas, Postmortem) muestra una pantalla de
subida si no hay datos cargados: arrastra el CSV o haz clic para
seleccionarlo. El propio servidor lo guarda en `data/input/` y ejecuta el
conversor correspondiente automáticamente.

**Opción B: Manualmente, con los scripts de conversión**

```
data/input/
├── incidencias.csv         (para Incidencias Masivas)
└── postmortem.csv          (para Postmortem/Release)
```

```bash
# Windows
converters/scripts/bin/convert_incidents.bat data/input/incidencias.csv
converters/scripts/bin/convert_postmortems.bat data/input/postmortem.csv

# Linux/Mac
./converters/scripts/bin/convert_incidents.sh data/input/incidencias.csv
./converters/scripts/bin/convert_postmortems.sh data/input/postmortem.csv
```

Los JSONs se generan en `data/output/` e `index.json` se actualiza automáticamente.

### 3️⃣ Abre el Portal

Con `serve_app.py` corriendo, ve a `http://localhost:8080/dashboards/portal/` (o simplemente `/dashboards/`, que redirige ahí vía `dashboards/index.html`).

### 4️⃣ Paneles y Dashboards Disponibles

El directorio [`dashboards/`](dashboards/) aloja las interfaces web estáticas del ecosistema (sin necesidad de build step ni frameworks pesados):

- **[Portal Hub](dashboards/portal/)** (`dashboards/portal/`): Punto de entrada y acceso central. Incluye un **buscador directo de incidencias de Remedy** con panel modal interactivo de **Resumen IA en tiempo real** (conectado a Epsilon IA con doble capa de caché de 15 min), normalización inteligente de códigos (ej. `4141215` o `INC000004141215`) y tarjetas de acceso directo a todos los módulos.
- **[Incidencias Masivas](dashboards/massive-incidents/)** (`dashboards/massive-incidents/`): Monitorización analítica del backlog de incidencias masivas: tendencias temporales, distribución por estado/sistema/urgencia y consulta de Resumen IA al pulsar sobre cualquier incidencia.
- **[Postmortem / Release](dashboards/postmortem/)** (`dashboards/postmortem/`): Análisis de incidencias surgidas en ventanas de despliegue operativo (PAP/MESA), seguimiento de SLAs y tiempos de resolución.
- **[KPIs de Release](dashboards/release-kpis/)** (`dashboards/release-kpis/`): Serie histórica comparativa de métricas de calidad, incidencias y estabilidad entre distintas releases.
- **[Reportes de Incidencias](dashboards/reportes-incidencias/)** (`dashboards/reportes-incidencias/`): Frontend del editor y visor de reportes semanales de incidencias de Orange. Incluye catálogo histórico (`index.html`), editor interactivo con selector de marcas (`editor.html`) y vista previa con exportación a PDF y PowerPoint (`preview.html`). Se comunica vía API REST con el backend FastAPI de `cso-incident-masivas-report`.
- **[Catálogo de Agentes IA y Skills](dashboards/agents-catalog/)** (`dashboards/agents-catalog/`): Catálogo interactivo de agentes de IA y habilidades técnicas (*skills*) de la biblioteca corporativa. Incluye cabecera sobria y unificada con los dashboards hermanos, filtrado facetado por dominio tecnológico, buscador en tiempo real, visor modal de fichas técnicas completas con renderizado Markdown y generador en un clic de comandos CLI de despliegue (`.\deploy-agents.cmd`). Regenerado automáticamente desde `biblioteca-agentes` en cada despliegue a producción. Conectado a `GET /api/agents-catalog` con fallback estático.

> **Integración con otros sistemas**: Desde el Portal y la barra superior compartida también se enlaza a **Gestión de Problemas** (`/problemas`), aplicación servida por el backend de otro repositorio hermano en el mismo servidor VPS.

---

## 📦 Scripts de Conversión

Los scripts de conversión están en [`converters/scripts/bin/`](converters/scripts/bin/) y son la vía manual/batch para generar los JSONs (la vía normal desde el navegador ya los invoca automáticamente vía `serve_app.py` o el endpoint `/api/upload`):

| Script | Propósito | Entrada |
|--------|-----------|---------|
| `convert_incidents.bat/sh` | Convierte incidencias masivas a JSON | `data/input/*.csv` |
| `convert_postmortems.bat/sh` | Convierte postmortems a JSON | `data/input/*.csv` |

**Características:**

- ✅ Auto-detección de encoding (UTF-8, Windows-1252, Latin-1, ISO-8859-15)
- ✅ Auto-detección de delimitadores (coma, punto y coma, tabulación)
- ✅ Normalización de campos automática
- ✅ Reporte de errores detallado (en `data/errors/`)
- ✅ Estadísticas de conversión
- ✅ KPIs pre-calculadas en metadata
- ✅ Suite de tests con >80% de cobertura (ver [Testing](#-testing--calidad-de-código))

### Uso Programático en Python

**Convertir Incidencias Masivas:**

```python
import sys
from pathlib import Path

# Agregar converters/src al path
sys.path.insert(0, str(Path('converters/src')))

from csv_to_json import CsvToJsonConverter

converter = CsvToJsonConverter()
success, report = converter.convert_file(
    input_path='data/input/incidencias.csv',
    output_path='data/output/incidencias-massive.json',
    error_report_path='data/errors/incidencias_errors.json'
)

print(f"Conversión exitosa: {success}")
print(f"Registros procesados: {report['stats']['successful']}/{report['stats']['total_records']}")
print(f"Encoding detectado: {report['encoding_detected']}")
```

**Convertir Postmortems:**

```python
import sys
from pathlib import Path

# Agregar converters/src al path
sys.path.insert(0, str(Path('converters/src')))

from csv_to_json.postmortem_converter import PostmortemConverter

converter = PostmortemConverter()
success, report = converter.convert_file(
    input_path='data/input/postmortem.csv',
    output_path='data/output/postmortem.json',
    error_report_path='data/errors/postmortem_errors.json'
)

print(f"Conversión exitosa: {success}")
print(f"Registros procesados: {report['stats']['successful']}/{report['stats']['total_records']}")
```

### Acceder a los KPIs en JavaScript

Una vez generados los JSONs, los dashboards acceden a los KPIs automáticamente:

```javascript
const result = JSON.parse(massiveIncidentsJSON);
const metadata = result._metadata;

console.log(`Total incidencias: ${metadata.kpis.total}`);
console.log(`Incidencias pendientes: ${metadata.kpis.pending}`);
console.log(`Tendencia 7 días: ${metadata.kpis.trend_7d}%`);
```

---

## 📋 Requisitos

- **Python 3.10+ / 3.11**
- **Sin dependencias externas** para los dashboards (usan librerías estándar del navegador + Plotly.js vía CDN)
- Ver [`converters/requirements.txt`](converters/requirements.txt) y [`converters/requirements-dev.txt`](converters/requirements-dev.txt) para dependencias de desarrollo/test de los converters

---

## 📚 Documentación

El repositorio cuenta con una estructura de documentación temática organizada y un **visor web interactivo Docsify** accesible localmente en `http://localhost:8080/docs/`.

### Guías Principales

| Documento | Contenido |
| ----------- | ----------- |
| **[docs/01-primeros-pasos/quickstart.md](docs/01-primeros-pasos/quickstart.md)** | Setup completo y primeros pasos |
| **[docs/README.md](docs/README.md)** | Índice maestro de documentación y mapa temático |
| **[docs/01-primeros-pasos/troubleshooting.md](docs/01-primeros-pasos/troubleshooting.md)** | Solución de problemas comunes |
| **[docs/01-primeros-pasos/desarrollo.md](docs/01-primeros-pasos/desarrollo.md)** | Entorno de desarrollo local |
| **[docs/06-operaciones-y-gobernanza/despliegue-vps.md](docs/06-operaciones-y-gobernanza/despliegue-vps.md)** | Procedimientos de despliegue en VPS |

### Gestión de Emergencias IT

| Documento | Contenido |
| ----------- | ----------- |
| **[docs/02-gestion-emergencias/triaje-itil-automatizado.md](docs/02-gestion-emergencias/triaje-itil-automatizado.md)** | Manual del motor de triaje ITIL determinista, reglas de oro y detección de discrepancias N1 |
| **[docs/02-gestion-emergencias/catalogo-alta-prioridad.md](docs/02-gestion-emergencias/catalogo-alta-prioridad.md)** | Especificación técnica del catálogo de alta prioridad (`high_priority_notifications.json`) |
| **[docs/02-gestion-emergencias/manual-consola-operativa.md](docs/02-gestion-emergencias/manual-consola-operativa.md)** | Manual de usuario para la Consola Operativa de Emergencias Orange |
| **[docs/02-gestion-emergencias/flujo-gestion-incidencias.md](docs/02-gestion-emergencias/flujo-gestion-incidencias.md)** | Flujo de gestión operativa y escalados telefónicos |
| **[docs/02-gestion-emergencias/notificaciones-ejecutivas.md](docs/02-gestion-emergencias/notificaciones-ejecutivas.md)** | Comunicaciones ejecutivas oficiales para Dirección e IM-CSO |

### Conversores y Testing

| Documento | Contenido |
| ----------- | ----------- |
| **[docs/04-conversores/README.md](docs/04-conversores/README.md)** | Referencia técnica de los conversores y catálogo de módulos |
| **[docs/03-arquitectura-y-datos/estructura-proyecto.md](docs/03-arquitectura-y-datos/estructura-proyecto.md)** | Arquitectura y estructura del proyecto |
| **[docs/04-conversores/rendimiento.md](docs/04-conversores/rendimiento.md)** | Decisiones de optimización, benchmarks |
| **[docs/04-conversores/estructura-tests.md](docs/04-conversores/estructura-tests.md)** | Organización de tests por funcionalidad |
| **[docs/04-conversores/buenas-practicas-testing.md](docs/04-conversores/buenas-practicas-testing.md)** | Guía de pytest fixtures y aislamiento |

### Especificaciones

| Documento | Contenido |
| ----------- | ----------- |
| **[converters/specs/006-optimize-csv-converters/](converters/specs/006-optimize-csv-converters/)** | Optimización de los conversores |
| **[converters/specs/004-postmortem-converter/](converters/specs/004-postmortem-converter/)** | Conversor de postmortem |
| **[converters/specs/001-csv-to-json-workflow/](converters/specs/001-csv-to-json-workflow/)** | Flujo CSV→JSON original |

---

## ✅ Estado del Proyecto

- **Tests**: ✅ 516+ tests passing (cobertura >80%) — ver `converters/tests/`
- **Dashboards**: ✅ Portal, Incidencias Masivas, Postmortem/Release, Release KPIs, Reportes de Incidencias y Catálogo de Agentes IA funcionales
- **Subida de CSV desde el navegador**: ✅ vía `serve_app.py` (`/api/upload`)
- **Conversores**: ✅ Incidencias masivas + Postmortems (CLI y batch)
- **Informes Ejecutivos**: ✅ Generación PPTX bajo demanda y exportación PDF en cliente

---

## 🧪 Testing & Calidad de Código

### Ejecutar Tests

```bash
cd converters

# Todos los tests
pytest tests/

# Por categoría
pytest tests/unit/                    # Tests unitarios (pura lógica)
pytest tests/integration/             # Tests de integración (con I/O)
pytest tests/e2e/                     # Tests end-to-end (flujos completos)

# Por funcionalidad específica
pytest tests/unit/encoding/           # Solo tests de encoding
pytest tests/unit/normalizers/        # Solo tests de normalización
pytest tests/unit/validators/         # Solo tests de validación

# Con opciones útiles
pytest tests/ -v                      # Verbose (muestra cada test)
pytest tests/ -k "normalization"      # Filtra por patrón
pytest tests/ --cov=src --cov-report=html  # Genera reporte de coverage

# En paralelo (requiere pytest-xdist)
pip install pytest-xdist
pytest tests/ -n auto                 # Auto-detecta número de CPUs
```

### Estructura de Tests

```
converters/tests/
├── unit/                    # Tests de lógica pura (sin I/O)
│   ├── encoding/           # Detección de encoding
│   ├── delimiter/          # Detección de delimitadores
│   ├── normalizers/        # Normalización de datos
│   ├── validators/         # Validación de campos
│   ├── schemas/            # Estructuras de datos
│   └── derivation/         # Lógica derivada (Despliegue)
├── integration/             # Tests con I/O (archivos, CSV)
└── e2e/                     # Tests end-to-end (incluye benchmarks de performance)
```

Ver [docs/04-conversores/estructura-tests.md](docs/04-conversores/estructura-tests.md) para detalle completo.

### Calidad de Código

```bash
cd converters

# Linting (PEP 8)
pip install flake8
flake8 src/ cli/ --max-line-length=120

# Formatting
pip install black
black --check src/ cli/

# Import sorting
pip install isort
isort --check-only src/ cli/
```

---

## 🔧 Estructura del Proyecto

```
release-dashboard-application/
├── serve_app.py                  # Servidor local (dashboards + /api/upload + proxies IA y FastAPI + PPT gen)
├── nginx.conf                    # Configuración de Nginx para el servidor VPS
├── dashboards/                   # Suite de Dashboards (HTML/CSS/JS)
│   ├── index.html                # Redirige a /dashboards/portal/
│   ├── portal/                   # Portal principal con buscador y Resumen IA
│   ├── massive-incidents/        # Dashboard de incidencias masivas
│   ├── postmortem/               # Dashboard de postmortem / release
│   ├── release-kpis/             # Dashboard de KPIs históricos de release
│   ├── reportes-incidencias/     # Frontend de reportes de incidencias (listado, editor, preview PDF/PPTX)
│   ├── agents-catalog/           # Catálogo interactivo de agentes IA y skills (index.html, CSS, JS)
│   ├── tests/                    # Tests unitarios JavaScript para lógica de dashboards
│   └── assets/                   # Logos corporativos, tokens.css, topbar.css/js, resumen-ia.css/js
├── converters/                   # Módulo Python de conversión CSV→JSON y reporting
│   ├── cli/                      # convert_incidents.py, convert_postmortems.py, build_index.py, build_agents_catalog.py, etc.
│   ├── src/csv_to_json/          # Lógica de conversión (encoding, normalización, validación)
│   ├── src/report_generator/     # Motor de generación de presentaciones PPTX
│   ├── scripts/bin/              # Wrappers .bat/.sh para los CLI
│   ├── tests/                    # Suite de tests (unit/integration/e2e)
│   ├── docs/                     # Redirección y referencia a docs/04-conversores/
│   └── specs/                    # Especificaciones de features de los converters
├── data/                         # Almacenamiento de datos (git-ignored)
│   ├── input/                    # CSVs de entrada
│   ├── output/                   # JSONs generados + index.json
│   └── errors/                   # Reportes de error de conversión
├── scripts/                      # Scripts de despliegue Standalone (deploy-production.ps1) y operación (status, rollback)
├── docs/                         # Documentación general y visor interactivo Docsify (:8080/docs/)
└── config/                       # Configuración (.env.example, hook pre-commit)
```

---

## 💡 Flujo de Datos

```
CSVs de Remedy (subidos vía web o en data/input/)
    ↓
serve_app.py [/api/upload]  o  converters/cli/convert_incidents.py / convert_postmortems.py
    ↓
JSON estructurado + KPIs en metadata (data/output/) + build_index.py → index.json
    ↓
Portal Hub (dashboards/portal/)  <-- [Consultas en tiempo real a Epsilon IA]
    ↓
├── Incidencias Masivas (dashboards/massive-incidents/)
├── Postmortem / Release (dashboards/postmortem/)
├── KPIs de Release (dashboards/release-kpis/)
├── Reportes de Incidencias (dashboards/reportes-incidencias/)  <-- [CRUD vía FastAPI :8000]
└── Catálogo de Agentes IA (dashboards/agents-catalog/)  <-- [API /api/agents-catalog o estático]
    ↓
Generación de Informes PPTX / PDF (report_generator / html2pdf / pptxgen)
```

---

## 📊 Informe Ejecutivo de Incidencias Postmortem (PowerPoint)

Genera bajo demanda presentaciones PowerPoint corporativas (`.pptx`) con el diseño y formato oficial de Orange a partir de datos de postmortem o páginas de Confluence:

- **UI en Gestión de Problemas**: Botón `📊 Generar PPT` en cada incidencia en `/problemas`.
- **CLI**: `python converters/cli/generate_executive_report.py --ref <CODIGO> --title "<TITULO>"`
- **Detalles y arquitectura**: Ver [docs/05-postmortem-y-reportes/informe-ejecutivo-postmortem.md](docs/05-postmortem-y-reportes/informe-ejecutivo-postmortem.md).

---

## 🚀 Despliegue en Producción (VPS)

El despliegue se realiza en 1 clic de forma segura y desatendida desde tu terminal local de Windows (PowerShell en rama `production`), mediante un artefacto comprimido (*Standalone Runtime*, ~2.3 MB) transferido por SCP, con regeneración automática del catálogo de agentes IA (`data/output/agents_catalog.json`), persistencia estricta en almacenamiento desacoplado (`/infocodes/var/storage/release-dashboard/` para datos analíticos y `/infocodes/var/storage/executive_pptx/` para informes ejecutivos generados, con fallback a `data/` en local), backup automático en rotación de 5 copias, validación sintáctica de Nginx (`nginx -t`) y sondas de salud HTTP:

```powershell
.\scripts\deploy-production.ps1
```

Opciones comunes:

```powershell
.\scripts\deploy-production.ps1 -SkipCatalogBuild  # Desplegar sin regenerar el catálogo de agentes
.\scripts\deploy-production.ps1 -VerifyOnly        # Consultar sondas de salud y estado en el VPS sin desplegar
.\scripts\deploy-production.ps1 -Rollback          # Revertir a la copia de seguridad anterior
.\scripts\deploy-production.ps1 -DryRun            # Simular el proceso sin aplicar cambios
```

En el propio servidor (`/infocodes/project/release-dashboard-application`), se dispone de herramientas de consulta rápida:

- `./status.sh`: Sondas de salud Nginx y comprobación de endpoints HTTP.
- `./rollback.sh`: Reversión inmediata a una copia previa si fuera necesario.

Ver [docs/06-operaciones-y-gobernanza/despliegue-vps.md](docs/06-operaciones-y-gobernanza/despliegue-vps.md) y [scripts/README.md](scripts/README.md) para más detalles.

---

## 🔐 Seguridad

- ✅ Datos sensibles protegidos por `.gitignore`
- ✅ Configuración mediante variables de entorno
- ✅ Pre-commit hooks para evitar secrets en git
- ✅ Tests de validación automatizados

---

## 📞 Soporte

- **¿Cómo empiezo?** → [docs/01-primeros-pasos/quickstart.md](docs/01-primeros-pasos/quickstart.md)
- **¿Problemas?** → [docs/01-primeros-pasos/troubleshooting.md](docs/01-primeros-pasos/troubleshooting.md)
- **¿Desarrollo?** → [docs/01-primeros-pasos/desarrollo.md](docs/01-primeros-pasos/desarrollo.md)
- **Visor interactivo de documentación** → `http://localhost:8080/docs/`

---

**Última actualización**: 2026-10-30
