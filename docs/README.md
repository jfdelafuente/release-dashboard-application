# Índice General de Documentación

📖 Guía y referencia completa de la documentación técnica, arquitectónica y operacional de **Release Dashboard Application**.

> **Punto de inicio rápido**: Si eres un desarrollador nuevo en el proyecto, comienza por [QUICKSTART.md](QUICKSTART.md) o por la visión general en [../README.md](../README.md).

---

## 📚 Mapa de Documentación

### 🚀 Primeros Pasos y Desarrollo Local
- **[QUICKSTART.md](QUICKSTART.md)**: Puesta en marcha en 5 minutos, entorno virtual, arranque de `serve_app.py` en el puerto `8080`, catálogo completo de dashboards y comandos esenciales.
- **[DEVELOPMENT.md](DEVELOPMENT.md)**: Manual integral de desarrollo, configuración del entorno Python 3.10+/3.11, suite de 516+ tests con pytest, linters (`flake8`, `black`, `isort`) y hooks de pre-commit.
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)**: Diagnóstico paso a paso y resolución de incidencias en entorno local, conversores CLI, dashboards y servidor de producción VPS (`10.132.26.96`).

### 📊 Dashboards y Reportes Ejecutivos
- **[INFORME-EJECUTIVO-POSTMORTEM.md](INFORME-EJECUTIVO-POSTMORTEM.md)**: Guía de generación del informe ejecutivo PowerPoint individual por incidencia (Single Source of Truth en backend CSO y storage `/infocodes/var/storage/executive_pptx/`).
- **[INFORME-PPT-POSTMORTEM.md](INFORME-PPT-POSTMORTEM.md)**: Guía de generación masiva batch del informe PPT postmortem por release (PAP/MESA) mediante `generate_postmortem_report.py`.
- **[DASHBOARDS-API.md](DASHBOARDS-API.md)**: Catálogo de APIs, endpoints, contratos de datos e integraciones con Epsilon IA y backend CSO.

### 🤖 Agentes IA y Notificaciones Ejecutivas
- **[INCIDENT-EXECUTIVE-NOTIFICATIONS-WORKFLOW.md](INCIDENT-EXECUTIVE-NOTIFICATIONS-WORKFLOW.md)**: Manual operativo integral para procesar nuevos ficheros CSV de incidencias, redactar comunicaciones oficiales para Dirección con la skill `incident-executive-notifications` y sincronizar con producción de forma segura.

### ⚙️ Conversores y Tratamiento de Datos
- **[../converters/docs/API.md](../converters/docs/API.md)**: Contrato de datos y especificación de esquemas JSON generados (`_metadata` + `data`).
- **[../converters/docs/CSV-TO-JSON-WORKFLOW.md](../converters/docs/CSV-TO-JSON-WORKFLOW.md)**: Flujo detallado de ingesta, normalización heurística, detección de encoding y validaciones.
- **[../converters/docs/ARCHITECTURE.md](../converters/docs/ARCHITECTURE.md)**: Diseño y arquitectura modular del paquete conversor Python.
- **[MIGRATION.md](MIGRATION.md)**: Historial de evolución de esquemas, normalización de campos y compatibilidad hacia atrás en JavaScript.

### 🏛️ Arquitectura y Estructura del Sistema
- **[PROJECT-STRUCTURE.md](PROJECT-STRUCTURE.md)**: Organización detallada del repositorio, arquitectura de producción con runtime atómico (`releases/` + symlink `current`), storage desacoplado y matriz "quién sirve qué".
- **[VPS-REQUIREMENTS.md](VPS-REQUIREMENTS.md)**: Requisitos de infraestructura, topología de red (`10.132.26.96:8081`), configuración activa de Nginx y entorno compartido del VPS.

### 🚀 Despliegue, Operaciones y Trazabilidad
- **[DEPLOYMENT.md](DEPLOYMENT.md)**: Manual integral de despliegue Standalone Runtime mediante `deploy-production.ps1`, empaquetado selectivo, Zero Git en VPS y protocolo de Rollback Dual.
- **[VERSION-MANAGEMENT.md](VERSION-MANAGEMENT.md)**: Política oficial de versionado semántico (SemVer 2.0.0), trazabilidad en producción y etiquetado Git obligatorio.
- **[LOGS.md](LOGS.md)**: Estándar unificado de bitácora técnica, estructura de logs persistentes en `/infocodes/var/log/` y rotación de copias de seguridad.
- **[../scripts/README.md](../scripts/README.md)**: Referencia y manual de uso de los scripts operacionales (`deploy-production.ps1`, `status.sh`, `rollback.sh`, `generate-dashboards.sh`).

### 🛡️ Calidad, Seguridad y Gobernanza
- **[CI.md](CI.md)**: Arquitectura de integración continua en GitHub Actions (`tests.yml` y `lint.yml`) para ramas `main` y `production`.
- **[GITHUB-BRANCH-PROTECTION.md](GITHUB-BRANCH-PROTECTION.md)**: Reglas de protección de ramas, requerimiento de PRs aprobados y status checks obligatorios de CI.
- **[CONTRIBUTING.md](CONTRIBUTING.md)**: Guía para colaboradores, flujo de Git y convenciones de código.
- **[../SECURITY.md](../SECURITY.md)**: Políticas de seguridad, gestión de credenciales y reporte de vulnerabilidades.
- **[../CHANGELOG.md](../CHANGELOG.md)**: Registro histórico de versiones y cambios del proyecto.

---

## 🎯 Catálogo de Dashboards

| Dashboard | Ruta Relativa | Puerto Local / Prod | Propósito |
|---|---|---|---|
| **Portal General** | `dashboards/portal/index.html` | `:8080` / `:8081` | Centro neurálgico con buscador global de incidencias, métricas agregadas y modal flotante de Epsilon IA. |
| **Incidencias Masivas** | `dashboards/massive-incidents/index.html` | `:8080` / `:8081` | Análisis temporal y evolutivo de incidencias masivas con gráficos Plotly y filtros por urgencia/estado. |
| **Postmortem / Despliegues** | `dashboards/postmortem/index.html` | `:8080` / `:8081` | Seguimiento de incidencias por ventana de despliegue (PAP/MESA), tiempos de resolución y exportación. |
| **Release KPIs (Histórico)** | `dashboards/release-kpis/index.html` | `:8080` / `:8081` | Serie histórica de KPIs por release y análisis de tendencias. |
| **Reportes de Incidencias** | `dashboards/reportes-incidencias/index.html` | `:8080` / `:8081` | Gestión tabular, reportes de impacto y exportación de informes ejecutivos PowerPoint. |
| **Catálogo de Agentes IA** | `dashboards/agents-catalog/index.html` | `:8080` / `:8081` | Catálogo de agentes IA y skills, visor de prompts/fichas técnicas y generador de comandos CLI de despliegue. |

> `dashboards/index.html` redirige de forma automática al **Portal General** (`/dashboards/portal/`).

---

## 🔄 Flujo de Datos y Almacenamiento Desacoplado

```text
Entrada de Datos (CSVs)
  ├─ En local: Subida arrastrando en dashboard (POST /api/upload) o archivo en data/input/
  └─ En VPS: Transferencia SCP / carga batch directa a /infocodes/var/storage/release-dashboard/input/
          │
          ▼
Procesamiento y Conversión (Python CLI / Cron)
  ├─ En local: serve_app.py invoca upload_csv.py en tiempo real
  └─ En VPS: crontab ejecuta generate-dashboards.sh periódicamente
          │
          ▼
Almacenamiento Desacoplado (JSONs y Reportes)
  ├─ En local: data/output/*.json, data/output/index.json, data/reports/
  └─ En VPS: /infocodes/var/storage/release-dashboard/output/ (*-massive.json, index.json)
             /infocodes/var/storage/executive_pptx/ (Informes PowerPoint individuales)
          │
          ▼
Consumo en Frontend (Dashboards Estáticos)
  ├─ Portal Hub (/dashboards/portal/) lee index.json
  ├─ Peticiones semánticas delegadas al proxy Epsilon IA (/api/epsilon/*)
  └─ Generación de presentaciones ejecutivas (.pptx) vía backend CSO (:8000)
```

---

## 📊 Stack Tecnológico y Entornos

- **Lenguaje Core**: Python 3.10+ (recomendado **Python 3.11**).
- **Servidor Local de Desarrollo**: `serve_app.py` en puerto **`8080`** (con reverse proxy hacia FastAPI en `:8000`, Next.js en `:3001` y Epsilon IA con caché).
- **Servidor Web de Producción**: Nginx en puerto **`8081`** en el host **`10.132.26.96`** (`infocodes.si.orange.es`).
- **Arquitectura de Despliegue**: Standalone Runtime selectivo (~2.3 MB) empaquetado por `deploy-production.ps1` con releases inmutables y symlink atómico `current`.
- **Frontend**: HTML5 semántico, CSS3 modular (tokens de diseño corporativos **Orange**), JavaScript moderno sin build step y gráficos interactivos Plotly.js vía CDN.
- **Testing y Calidad**: 516+ tests automatizados con `pytest` en `converters/tests/` (gate de cobertura $\ge 80\%$) y linters (`flake8`, `black`, `isort`).

---

## ✅ Estado de Certificación del Ecosistema

- **Dashboards**: ✅ Catálogo completo operativo bajo manual de marca Orange.
- **Conversores CSV→JSON**: ✅ Motor validado con detección de encoding, delimitador dinámico y esquemas estandarizados.
- **Generación de Reportes**: ✅ Soporte dual para presentaciones postmortem masivas y reportes ejecutivos individuales.
- **CI / Calidad**: ✅ Workflows `tests.yml` y `lint.yml` verificados y activos para ramas `main` y `production`.
- **Despliegue y VPS**: ✅ Despliegue atómico en 1 clic (`deploy-production.ps1`), Zero Git en el servidor, copias de seguridad rotativas y Rollback Dual validado.
- **Almacenamiento Persistente**: ✅ Desacoplado en `/infocodes/var/storage/` garantizando persistencia absoluta entre releases.

---

**Última actualización**: 2026-10-20  
**Versión de documentación**: 2.0
