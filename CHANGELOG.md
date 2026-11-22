# Registro de Cambios (Changelog)

Todos los cambios notables en el proyecto **Release Dashboard Application** se documentan en este archivo.

El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto se adhiere a [Semantic Versioning](https://semver.org/lang/es/).

---

## [0.5.0] - 2026-11-22

### Añadido (Nuevas Funcionalidades y Ecosistema)

#### Carga Web de Argos PaP y Generación Bajo Demanda en Mesa de Release (Feature 017)
- **Modal web de subida de pruebas PaP (`#argosUploadModal`)**: Integrado en la consola de Mesa de Release (`dashboards/release-desk/`) con soporte de arrastre (drag-and-drop) o selector de archivos para los CSVs de Grafana Argos (*Avance progresión por PRJ* y *Regresión por Test Plan y dominio*).
- **Capa unificada de servicios (`converters/src/desk_service.py`)**:
  - `handle_argos_upload()`: Ingesta, detección automática de tipología y fusión atómica e inteligente en `data/storage/projects/{release}_grafana_pap.csv`, preservando las pruebas existentes de la otra tipología si solo se sube una.
  - `generate_release_report()`: Generación programática del Informe Ejecutivo Global 360° en HTML (`dashboards/informes/comunicado-release-{release}/index.html`).
- **Endpoints de backend en local y producción VPS**:
  - `POST /api/release-desk/upload-argos`: Recepción multipart de ficheros CSV, consolidación de dataset y compilación automática del informe.
  - `POST /api/release-desk/generate-report`: Compilación del informe HTML bajo demanda sin re-subir archivos.
  - Soportados con idéntico comportamiento en `serve_app.py` (servidor local) y `fastapi_remedy_router.py` (FastAPI en producción VPS).
- **Controles interactivos en Mesa de Release**:
  - Botón `📊 Cargar Argos PaP` (`#btnUploadArgos`): Apertura del modal interactivo de carga en cabecera.
  - Botón unificado `🌐 Informe Ejecutivo PaP` (`#btnGenerateReportHtml`): Compilación en caliente bajo demanda y apertura automática del informe corporativo en una nueva pestaña.
  - **Visibilidad condicional por fecha PaP**: `#btnGenerateReportHtml` se muestra de manera condicional exclusivamente el día de la fecha de PaP (`Fecha PaP` en `releases-data.js`) y al día siguiente (día PaP + 1), manteniéndose oculto durante el resto del ciclo para focalizar la operativa.
  - Barra inferior simplificada: 4 acciones esenciales y no redundantes (`Copiar briefing`, `Briefing por Sistema`, `Informe Ejecutivo PaP`, `Exportar tabla`).
- **Diseño visual y ergonomía**:
  - Ajuste del fondo de página de la **Mesa de Release** (`--bg-page: #EBE8E2`) y del **Informe Ejecutivo PaP** (`--mo-bg: #EBE8E2`) a un tono sutilmente más oscuro, cálido y equilibrado, mejorando la elevación y el contraste de las tarjetas blancas (`#FFFFFF`), reduciendo la fatiga visual y unificando la identidad estética entre ambas vistas.
  - **Separación visual de bloques de incidencia en la tabla**: Cada fila de incidencia se presenta ahora como un bloque/tarjeta independiente elevado sobre el fondo cálido (`#EBE8E2`), con separación vertical de 5px, bordes de contorno sutiles, acolchado ampliado (`9px 8px`) y acento de criticidad lateral continuo, eliminando la sensación de bloque monolítico pegado y facilitando la lectura individualizada.
  - **Oscurecimiento enfático en foco y despliegue**: Al situar el cursor (`:hover`), enfocar por teclado (`:focus`, `:focus-within`, `tabindex="0"`) o desplegar una incidencia (`.is-selected`), la fila se oscurece intencionadamente hacia un tono cálido diferenciado (`#EDE6DB` en foco y `#E5D5C0` en despliegue) junto con la fila de detalle (`#EDE6DC`), resaltando el bloque activo y facilitando el seguimiento visual de la incidencia seleccionada.
  - **Homogeneización estética de la Consola de Triaje (`dashboards/emergency-triage-console/`)**:
    - Adopción del fondo unificado cálido (`--triage-bg: #EBE8E2`, `--triage-border: #D5CEC2`, `--triage-border-light: #E2DDD5`), coordinando la paleta con la Mesa de Release y el Informe Ejecutivo PaP.
    - Transformación de las filas de la tabla de triaje (`.triage-row-main`) en tarjetas independientes con separación de 5px, borde perimetral sutil (`#EBE5DC`), y preservación prioritaria de los acentos laterales de discrepancia (`is-discrepancy-delta2`, `is-discrepancy-delta1`, `is-correct`).
    - Oscurecimiento adaptativo en hover y foco por teclado (`:hover`, `:focus`, `:focus-within` a `#EDE6DB`), así como en fila desplegada (`.is-expanded` a `#E5D5C0` y su fila de detalle `.triage-row-detail td` a `#EDE6DC`), elevando el contenedor interior blanco `#FFFFFF`.
- **Refinado de Resumen Agregado por Proyecto en Informe Ejecutivo PaP**:
  - **Foco en iniciativas en seguimiento (pruebas y tickets activos)**: La tabla resume las iniciativas que tienen incidencias activas en seguimiento (incluyendo estado *Pendiente*, *Asignado*, *En Curso* y *Resuelto* no cerrado) y aquellas con pruebas PaP en curso o bloqueadas. Se incorporan explícitamente iniciativas con incidencias activas sin pruebas PaP en Grafana Argos (ej. `AB2CJ-222` y `PRJ-12386` con tickets en estado *Pendiente*), mostrando indicador `Sin pruebas PaP` y totalizando 7 iniciativas en seguimiento en 2026R11.
  - **Eliminación de la columna Responsable**: Se retira la columna Responsable de la tabla de resumen agregado para optimizar el ancho visual y focalizar la matriz en métricas de pruebas e incidencias.
  - **Visualización de estados de incidencias Remedy**: En la columna *Incidencias Remedy*, cada ticket se acompaña ahora de su distintivo de estado operativo en Remedy (Asignado, En Curso, Pendiente, Resuelto), permitiendo identificar de un vistazo la situación técnica de cada iniciativa.
- **Visualización Integral de Iniciativas con Pruebas PaP (Vía A)**:
  - En el Informe Ejecutivo de Release (`converters/cli/generate_release_report_html.py`), la tabla *Resumen Agregado por Proyecto* ahora incluye **todas las iniciativas con pruebas PaP registradas** (progresión `PRJ-*` y regresión transversal `TRANSVERSAL`), resolviendo la visualización vacía (`0 iniciativas afectadas`) cuando se cargan avances de pruebas donde todas las pruebas están superadas o en ejecución (`block == 0`).
  - Ordenación jerárquica inteligente: iniciativas con bloqueos activos al frente (mayor número de bloqueos descendente, mayor porcentaje de bloqueo), seguidas de iniciativas en curso o completadas (progresión primero, menor porcentaje de superadas para priorizar seguimiento de las incompletas, mayor volumen de pruebas).
  - Adaptación dinámica de cabeceras y distintivos según la existencia o ausencia de bloqueos (`0 bloqueos · N pruebas` en verde con badge esmeralda vs indicador de alerta cuando existen bloqueos).
  - **Filtrado de Iniciativas Completadas sin Incidencias en Resumen Agregado**:
    - Para clarificar la visualización y evitar ruido en la tabla agregada, se ocultan automáticamente aquellas iniciativas que cumplan simultáneamente dos condiciones: tener el 100% de sus pruebas completadas y superadas (`pass >= total`, `block == 0`, `pending == 0`, `executing == 0`) y no tener ninguna incidencia abierta asignada (`incidencias == 0`).
    - Las iniciativas con bloqueos, con pruebas pendientes o en ejecución, o que cuenten con incidencias activas asignadas (como `PRJ-11763`), se mantienen en seguimiento prioritario en la tabla.
    - La cabecera y subtítulo informan con precisión del número de iniciativas en seguimiento activo y del total de completadas limpias ocultadas (ej. `15 iniciativas con seguimiento · 6 completadas sin incidencias ocultadas`). En caso de que todas las iniciativas estén completadas sin incidencias, se muestra un estado informativo de cierre exitoso.
- **Persistencia de fechas de compromiso acordadas en la Mesa**:
  - Edición en caliente del campo `fecha_prevista` en el seguimiento operativo de Mesa de Release con sincronización local y en servidor.
  - Indicador visual `(Acordada Mesa)` tanto en la consola interactiva como en las tarjetas ejecutivas de proyecto del informe HTML.
- **Exclusión estricta de incidencias «Cerrado»**:
  - Depuración y alineación matemática estricta: las incidencias con estatus `Cerrado` o `Closed` se omiten por completo de la tabla resumen de bloqueos y de las fichas de seguimiento por proyecto y transversal, contabilizándose exclusivamente en el KPI superior general (*Resueltas / Cerradas*).

---

## [0.4.0] - 2026-10-22

### Añadido (Nuevas Funcionalidades y Ecosistema)

#### Catálogo Interactivo de Agentes IA y Skills (Feature 011)
- **Dashboard web corporativo**: Nueva interfaz interactiva en [`dashboards/agents-catalog/`](dashboards/agents-catalog/) (`index.html`, `agents-catalog.css`, `agents-catalog.js`) con diseño visual Orange (`#FF7900`), cabecera con 4 métricas KPI, pestañas Agentes/Skills y filtrado en tiempo real.
- **Fichas técnicas y visor de prompts**: Modal interactivo accesible con renderizado de Markdown para explorar el contenido detallado de agentes y habilidades.
- **Generador de comandos CLI**: Generador con 1 clic de comandos de despliegue (`.\deploy-agents.cmd "<TargetRepo>" -Agents "<name>"`) con persistencia del repositorio destino en `localStorage` y feedback visual (`Toast`).
- **Extractor CLI de catálogo**: Script [`converters/cli/build_agents_catalog.py`](converters/cli/build_agents_catalog.py) que analiza la biblioteca externa (`biblioteca-agentes`), correlaciona dependencias bidireccionales `used_by_agents` y emite el dataset envelope estándar a [`data/output/agents_catalog.json`](data/output/agents_catalog.json).
- **Endpoint API y fallback**: Endpoint `GET /api/agents-catalog` integrado en `serve_app.py` con fallback estático transparente para entornos desacoplados (VPS de producción).
- **Integración global**: Enlace "Agentes IA" añadido a la barra superior unificada ([`dashboards/assets/topbar.js`](dashboards/assets/topbar.js)) y tarjeta de acceso rápido con badge `.tag-ai` en el Hub de Portales ([`dashboards/portal/index.html`](dashboards/portal/index.html)).
- **Pruebas unitarias**: Suite de 11 tests automatizados passing al 100% en [`converters/tests/unit/test_build_agents_catalog.py`](converters/tests/unit/test_build_agents_catalog.py).

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

**Versión actual**: v0.5.0  
**Última actualización**: 2026-11-22
