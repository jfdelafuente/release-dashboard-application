# Informe Ejecutivo de Incidencias Postmortem — Guía de Usuario y Operación

Guía para la generación de presentaciones PowerPoint (`.pptx`) corporativas Orange para **incidencias críticas individuales**, tanto desde el dashboard interactivo de Gestión de Problemas como mediante línea de comandos (CLI).

---

## 📌 ¿Qué es este informe y en qué se diferencia del informe de Release?

Existen dos tipos de informes ejecutivos PowerPoint en la plataforma:

| Característica | Informe Ejecutivo de Incidencia (Este documento) | Informe PPT de Postmortem por Release ([`INFORME-PPT-POSTMORTEM.md`](INFORME-PPT-POSTMORTEM.md)) |
|---|---|---|
| **Ámbito** | **Una incidencia crítica individual** (ej: `2606S77393`). | **Una release completa** (ej: `2026R7`, `2026R8`). |
| **Origen de Datos** | Postmortem en Confluence (URL o HTML) o datos estructurados. | Archivo `releases-data.js` con el histórico de despliegues. |
| **Contenido** | Resumen ejecutivo, impacto en negocio, causa raíz, solución, tabla de acciones (*Pain Points*) y cronología detallada de eventos. | KPIs de despliegue PaP vs Mesa (% éxito, 1ª semana) y gráficas evolutivas de las últimas 9 releases. |
| **Generación Web** | Modal interactivo en **Gestión de Problemas** (`/problemas`). | Botón ⬇ en **KPIs de Release** y **Postmortem**. |
| **Script CLI** | `converters/cli/generate_executive_report.py` | `converters/cli/generate_postmortem_report.py` |
| **Fichero generado** | `RESUMEN_EJECUTIVO_{incidentRef}.pptx` | `{release}-postmortem-report.pptx` |

---

## 🎨 Estructura y Diseño del Documento PPTX

El informe utiliza la plantilla oficial corporativa de **Orange**:
- **Paleta visual**: Naranja Orange corporativo (`#FF7900`), negro y grises neutros de alto contraste.
- **Tipografía**: Helvetica / Arial con jerarquía estandarizada.
- **Diapositiva 1 (Resumen Ejecutivo)**:
  - Cabecera con código de incidencia, título del servicio afectado, fecha de inicio y duración total.
  - Bloques visuales destacados: **Impacto en Negocio**, **Causa Raíz** y **Solución Implementada**.
  - Tabla de Puntos de Acción Relevantes (`Pain Point | Descripción | Owner | Forecast`).
- **Diapositivas 2 y siguientes (Cronología de Eventos)**:
  - Tabla cronológica detallada (`Hora | Evento`).
  - **Paginación inteligente**: Si el postmortem incluye muchos eventos, el generador distribuye las filas dinámicamente clonando diapositivas para evitar solapamientos o desbordamientos de texto.

---

## 💻 Generación desde la Interfaz Web (Vía Habitual)

La forma recomendada de generar y consultar los informes ejecutivos es a través del dashboard de **Gestión de Problemas**:

1. Accede a Gestión de Problemas:
   - **En local**: `http://localhost:8080/problemas` (servido por `serve_app.py` que reenvía a Next.js en `:3001`).
   - **En producción**: `http://10.132.26.96/problemas` (servido por Nginx).
2. En la tabla de incidencias o problemas, pulsa el botón **`📊 Generar PPT`** de la fila correspondiente.
3. Se abrirá el modal interactivo [`ExecutiveReportModal.tsx`](../gestion-problemas-dashboard/components/ExecutiveReportModal.tsx):
   - **Comprobación de caché**: El modal consulta automáticamente si ya existe un informe generado para esa referencia (`GET /api/reports/executive-incident/{ref}/status`). Si existe, ofrece descargarlo inmediatamente en 0 ms.
   - **Ingesta desde Confluence**: Puedes proporcionar la URL de la página de Confluence del postmortem (`https://confluence.si.orange.es/...`) o pegar directamente el contenido HTML o texto copiado de la página.
   - **Regeneración forzada**: Si los datos han cambiado, marca la casilla de forzar regeneración (`force=true`).
4. Pulsa **Generar y Descargar**: La presentación se generará en el servidor y comenzará la descarga directa en tu navegador.

---

## ⌨️ Generación por Línea de Comandos (CLI)

El script [`converters/cli/generate_executive_report.py`](../converters/cli/generate_executive_report.py) permite generar presentaciones directamente desde terminal o integrarlas en tareas desatendidas:

### 1. Requisitos Previos

Asegúrate de tener el entorno virtual activo con las dependencias instaladas:

```bash
# Windows
venv\Scripts\Activate.ps1
# Linux / macOS
source venv/bin/activate
```

### 2. Ejemplos de Uso

#### A. Generación básica manual con datos mínimos
```bash
python converters/cli/generate_executive_report.py --ref 2606S77393 --title "Corte pasarela de pagos IVR"
```

#### B. Generación a partir de un archivo HTML de Confluence
Si has guardado la página del postmortem de Confluence como archivo local:
```bash
python converters/cli/generate_executive_report.py --ref 2606S77393 --file postmortem_2606S77393.html --force
```

#### C. Generación con URL de Confluence
```bash
python converters/cli/generate_executive_report.py \
  --ref 2606S77393 \
  --url "https://confluence.si.orange.es/display/POSTMORTEM/INC-2606S77393"
```

#### D. Especificar una ruta de salida personalizada
```bash
python converters/cli/generate_executive_report.py \
  --ref 2606S77393 \
  --file postmortem.html \
  --output C:\informes\RESUMEN_2606S77393.pptx
```

### Opciones del CLI

| Parámetro | Obligatorio | Descripción |
|---|---|---|
| `--ref` | **Sí** | Identificador o código de la incidencia (ej: `2606S77393`). |
| `--title` | No | Título o descripción del incidente (si se omite, se extrae del postmortem). |
| `--file` | No | Ruta al archivo local HTML o texto con el postmortem de Confluence. |
| `--url` | No | URL de la página de Confluence del postmortem. |
| `--output` | No | Ruta destino personalizada para el `.pptx`. |
| `--force` | No | Sobrescribe el informe existente en caché en lugar de reutilizarlo. |

---

## 🏛️ Arquitectura y Almacenamiento Persistente

### Single Source of Truth (Fase 1.1)
El motor de generación de informes ejecutivos reside centralizado en:
👉 **`cso-incident-masivas-report/backend/report_generator/`**

- En `release-dashboard-application`, los módulos en `converters/src/report_generator/` actúan como puentes de reexportación (*compatibility shims*).
- El servidor [`serve_app.py`](../serve_app.py) delega las peticiones HTTP prioritariamente a la API FastAPI en `http://127.0.0.1:8000`, ejecutando fallback local si FastAPI no estuviera levantado.

### Ubicaciones de Almacenamiento

| Entorno | Directorio de Generación y Lectura | Enlace Simbólico de Compatibilidad |
|---|---|---|
| **VPS Producción** | `/infocodes/var/storage/executive_pptx/` | `/infocodes/var/storage/release-dashboard/reports/executive/` $\rightarrow$ `../../executive_pptx` |
| **Desarrollo Local** | `data/reports/executive/` (en la raíz del repo) | *(Ruta local gestionada automáticamente por `serve_app.py`)* |

Ambos servicios (`release-dashboard-application` y `cso-incident-masivas-report`) comparten el mismo almacenamiento físico en el VPS, evitando duplicidad de ficheros y garantizando descargas coherentes.

---

## 🔌 Endpoints REST

La API REST expone tres endpoints para interactuar con los informes ejecutivos (ver detalle completo de payloads en [`docs/DASHBOARDS-API.md`](DASHBOARDS-API.md)):

1. **`POST /api/reports/executive-incident`**:
   Genera o actualiza el `.pptx`. Acepta `incidentRef`, `title`, `confluenceUrl`, `rawHtml` y `force` (booleano).
2. **`GET /api/reports/executive-incident/{incidentRef}/status`**:
   Consulta si el informe ya existe en disco (`{ "exists": true|false, "filename": ..., "downloadUrl": ... }`).
3. **`GET /api/reports/executive-incident/{incidentRef}`**:
   Descarga directa del binario PowerPoint con las cabeceras `Content-Type: application/vnd.openxmlformats-officedocument.presentationml.presentation` y `Content-Disposition: attachment`.

---

## 🛠️ Solución de Problemas Frecuentes

### 1. "El informe para {ref} ya existe. Use --force para regenerarlo."
El sistema detecta una presentación previa en la caché del servidor. Si los datos del incidente o postmortem han cambiado, añade `--force` en el CLI o activa la casilla de regeneración en el modal web.

### 2. "PermissionError: [Errno 13] Permission denied: '...RESUMEN_EJECUTIVO_...pptx'"
El archivo `.pptx` generado anteriormente está abierto en Microsoft PowerPoint u otra aplicación en tu ordenador. Cierra PowerPoint y vuelve a ejecutar la generación.

### 3. "Faltan datos en la cronología o puntos de acción"
El parser de Confluence analiza etiquetas HTML estándar (`<table>`, `<h3>`, listas). Si la estructura del postmortem en Confluence es atípica o contiene texto plano sin formato:
- Verifica que el archivo de entrada incluya las cabeceras reconocibles (`Impacto`, `Causa`, `Solución`, `Puntos de acción`, `Cronología`).
- También puedes introducir manualmente el título y campos en el modal web.

---

## 🔗 Documentación Relacionada

- [**`DASHBOARDS-API.md`**](DASHBOARDS-API.md): Especificación técnica de los endpoints `/api/reports/executive-incident/*`.
- [**`INFORME-PPT-POSTMORTEM.md`**](INFORME-PPT-POSTMORTEM.md): Guía de generación del informe PPT por **Release**.
- [**`DEVELOPMENT.md`**](DEVELOPMENT.md): Configuración del entorno de desarrollo y ejecución de `serve_app.py`.
- [**`DEPLOYMENT.md`**](DEPLOYMENT.md): Despliegue en producción y topología de persistencia desacoplada.
- [**`PROJECT-STRUCTURE.md`**](PROJECT-STRUCTURE.md): Organización del proyecto y mapeo de rutas `/infocodes/var/storage/`.
