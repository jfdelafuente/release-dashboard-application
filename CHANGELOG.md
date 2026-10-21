# Registro de Cambios (Changelog)

Todos los cambios notables en el proyecto **Release Dashboard Application** se documentan en este archivo.

El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto se adhiere a [Semantic Versioning](https://semver.org/lang/es/).

---

## [0.3.0] - 2026-10-21

### Añadido (Nuevas Funcionalidades y Ecosistema)

#### Buscador de Incidencias con Resumen IA (Feature 009)
- **Buscador hero corporativo**: Integrado en el Portal Principal ([`dashboards/portal/index.html`](dashboards/portal/index.html)) con estética Orange y badge de Epsilon IA.
- **Normalización inteligente**: Función `sanitizeIncidentCode()` tolerante a códigos numéricos abreviados (auto-padding a 12 dígitos, ej. `4141215` → `INC000004141215`).
- **Modal interactivo Resumen IA**: Pantalla flotante con consulta a `/api/epsilon/resumenIA/{ID}` y doble capa de caché (15 min en memoria/cliente) para optimizar el tráfico de red.
- **Tests unitarios JS**: Suite de pruebas en `dashboards/tests/test_sanitize_incident_code.js`.

#### Informe Ejecutivo de Incidencias Postmortem en PowerPoint (Feature 010)
- **Generador corporativo `.pptx`**: Implementación de `ExecutiveReportBuilder` basada en la plantilla corporativa oficial `converters/src/report_generator/assets/executive_template.pptx`.
- **Parser resiliente de Confluence**: Ingesta y parseo automático de páginas de postmortem en HTML y texto plano.
- **Endpoints dedicados en `serve_app.py`**:
  - `POST /api/reports/executive-incident`: Generación y caché de informe.
  - `GET /api/reports/executive-incident/{incidentRef}`: Descarga binaria del archivo PowerPoint.
  - `GET /api/reports/executive-incident/{incidentRef}/status`: Consulta rápida de existencia.
- **Modal interactivo**: Componente `ExecutiveReportModal.tsx` integrado en la tabla de candidatos a postmortem.
- **Tests unitarios Python**: 71 pruebas passing al 100% en `converters/tests/unit/report_generator/`.

#### Informe PPT de Postmortem por Release (Feature 008)
- **Presentación corporativa de release**: Generación programática de 3 diapositivas con KPIs y gráficas generadas con Plotly y Kaleido.
- **CLI autónomo**: Script `converters/cli/generate_postmortem_report.py` con sistema de caché por timestamp de `releases-data.js`.
- **Endpoints en servidor**: Integración en `serve_app.py` para descarga directa desde los dashboards de Postmortem y Release KPIs.

#### Frontend de Reportes de Incidencias
- **Suite de reportes**: Módulo completo en [`dashboards/reportes-incidencias/`](dashboards/reportes-incidencias/) compuesto por catálogo (`index.html`), editor con selector de marcas (`editor.html`) y visor con exportación a PDF y PPTX (`preview.html`).
- **Integración con backend**: Conexión vía API REST con el servicio FastAPI de `cso-incident-masivas-report`.

#### Optimización de Conversores CSV→JSON (Feature 006)
- **Streaming y rendimiento**: Procesamiento eficiente de archivos CSV sin saturación de memoria.
- **Auto-detección y validación**: Detección automática de encoding (BOM, UTF-8, Windows-1252, etc.) y delimitador, con normalización automática de campos y reporte de errores en `data/errors/`.
- **Pre-cálculo de KPIs**: Agregaciones y tendencias (7d, 15d, 30d) calculadas en metadatos para optimizar la carga del frontend.

#### Suite Integral de Pruebas Automatizadas
- **516+ tests pasando**: Cobertura superior al 80% en `converters/tests/` (unitarios, integración y end-to-end).

#### Infraestructura de Despliegue Standalone Runtime
- **Despliegue desatendido en 1 clic**: Script PowerShell [`scripts/deploy-production.ps1`](scripts/deploy-production.ps1) desde local hacia el VPS (`10.132.26.96:8081`).
- **Zero Git en VPS**: Despliegue mediante paquete runtime comprimido sin repositorio Git en el servidor de producción.
- **Almacenamiento desacoplado**: Persistencia aislada en `/infocodes/var/storage/release-dashboard/` y `/infocodes/var/storage/executive_pptx/` (con fallback local a `data/`).
- **Sondas de salud y rollback**: Verificación sintáctica `nginx -t`, sondeos HTTP y rotación de 5 copias de seguridad.

### Modificado
- Servidor de desarrollo [`serve_app.py`](serve_app.py) configurado por defecto en el puerto `8080` para evitar colisiones con el backend FastAPI en `:8000`.
- Actualización de los requerimientos de Python a versiones 3.10+ / 3.11.
- Estandarización de la marca corporativa exclusivamente como **Orange** (eliminando referencias a MASORANGE).
- Revisión, saneamiento y armonización completa de toda la documentación técnica en `docs/` y en la raíz del repositorio.

---

## [0.2.0] - 2026-05-14

### Añadido - Infraestructura de Despliegue Seguro e Integración Continua
- **Flujos de trabajo de GitHub Actions**:
  - `tests.yml`: Ejecución de pytest en cada PR con umbral mínimo de 80% de cobertura.
  - `lint.yml`: Validación de estilo de código, sintaxis Python y formateo.
  - `deploy.yml`: Automatización de despliegues controlados.
- **Plantillas de Issues**: `.github/ISSUE_TEMPLATE/` para reporte de bugs y peticiones de características.
- **Automatización de Despliegues Inicial**:
  - Scripts en `scripts/deploy/` (`deploy.sh`, `rollback.sh`, `health-check.sh`).
- **Trazabilidad y Auditoría**:
  - `DEPLOYMENT-LOG.md` y estructura de logs en `logs/deployments/`.
- **Gestión de Versiones**:
  - Archivo `VERSION` y directrices en `docs/VERSION-MANAGEMENT.md`.

### Modificado
- Mejora de la protección de directorios `data/` y `datos/` en `.gitignore`.
- Refactorización de scripts de verificación de salud en diferentes entornos.

### Seguridad
- Reversión automática en caso de error de despliegue.
- Trazabilidad y registro de despliegues.

---

## [0.1.0] - 2026-05-14

### Añadido - Organización del Proyecto y Arquitectura Inicial (MVP)
- **Estructura Modular de Directorios**:
  - `src/converters/` para módulos de conversión en Python.
  - `src/dashboards/` para dashboards HTML y recursos estáticos.
  - `scripts/bin/` para wrappers `.bat` y `.sh`.
  - `data/` estructurado en `input/`, `output/`, `errors/` y `archive/`.
- **Documentación Técnica Inicial**:
  - Guías `docs/README.md`, `docs/QUICKSTART.md`, `docs/DEVELOPMENT.md`, `docs/DEPLOYMENT.md`, `docs/TROUBLESHOOTING.md`.
- **Gestión Segura de Configuración**:
  - `config/.env.example`, `config/pre-commit-hook.sh` y directrices de protección de secretos.
- **Conversores Base**:
  - Scripts de conversión inicial para incidencias masivas y postmortem.

---

**Versión actual**: v0.3.0  
**Última actualización**: 2026-10-21
