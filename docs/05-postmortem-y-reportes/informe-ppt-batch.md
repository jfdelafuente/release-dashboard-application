# Informe PPT de Postmortem por Release — Guía de Usuario y Operación

Guía de referencia para generar presentaciones PowerPoint (`.pptx`) con las métricas y KPIs agregados de una Release, tanto desde el navegador web como desde la consola (CLI).

---

## 📌 ¿Qué es este informe y en qué se diferencia del informe individual?

En la plataforma conviven dos tipos de presentaciones corporativas PowerPoint:

| Característica | Informe PPT de Postmortem por Release (Este documento) | Informe Ejecutivo de Incidencia ([`INFORME-EJECUTIVO-POSTMORTEM.md`](INFORME-EJECUTIVO-POSTMORTEM.md)) |
|---|---|---|
| **Ámbito** | **Una release completa** (ej: `2026R7`, `2026R8`). | **Una incidencia crítica individual** (ej: `2606S77393`). |
| **Origen de Datos** | `dashboards/release-kpis/releases-data.js` (histórico de despliegues). | Postmortem en Confluence (URL o HTML) o datos estructurados. |
| **Contenido** | KPIs agregados de despliegue PaP vs Mesa (% éxito, 1ª semana) y 3 gráficas evolutivas de las últimas 9 releases. | Resumen ejecutivo, impacto en negocio, causa raíz, solución, tabla de acciones (*Pain Points*) y cronología de eventos. |
| **Generación Web** | Icono ⬇ en **KPIs de Release** y botón en **Postmortem**. | Botón `📊 Generar PPT` en **Gestión de Problemas** (`/problemas`). |
| **Script CLI** | `converters/cli/generate_postmortem_report.py` | `converters/cli/generate_executive_report.py` |
| **Fichero generado** | `{release}-postmortem-report.pptx` | `RESUMEN_EJECUTIVO_{incidentRef}.pptx` |

---

## 🎨 Estructura del Documento PPTX

El informe consta de **3 diapositivas** diseñadas con la identidad visual corporativa de **Orange**:

1. **Diapositiva 1 (Portada)**:
   - Título corporativo con el identificador oficial de la release (ej: `Release 2026R7`).
2. **Diapositiva 2 (Métricas Globales)**:
   - **3 Tarjetas de KPI**:
     - *Total Incidencias*: Volumen total de incidencias registradas en la release.
     - *% Resueltas PaP*: Porcentaje de incidencias resueltas el día del despliegue (Puesta a Producción).
     - *% Resueltas Mesa*: Porcentaje de incidencias resueltas durante el seguimiento en Mesa.
     - *Criterio de color*: Verde si alcanza o supera el objetivo (**75%**) o rojo si queda por debajo. Cada tarjeta detalla el conteo real (ej. *"54 de 70 resueltas"*).
   - **Gráfica evolutiva "Incidencias por Release"**: Muestra la tendencia de volumen de incidencias a lo largo de las **últimas 9 releases**.
3. **Diapositiva 3 (Comparativa de KPIs por Release)**:
   - Dos gráficas enfrentadas:
     - *KPI % PaP*: Evolución del porcentaje de resolución en PaP en las últimas 9 releases frente al umbral objetivo.
     - *KPI % 1ª Semana*: Evolución del porcentaje de estabilidad en la primera semana de despliegue.

> [!NOTE]
> Todos los KPIs y gráficas se calculan a partir de `dashboards/release-kpis/releases-data.js`, garantizando que los datos de la presentación coincidan exactamente con lo visualizado en el dashboard web.

---

## 💻 Generación desde la Interfaz Web (Vía Habitual)

El usuario no necesita ejecutar comandos manuales en el flujo operativo ordinario. La descarga está disponible en dos dashboards:

1. **Dashboard de KPIs de Release** (`/dashboards/release-kpis/`):
   - En la tabla de releases, pulsa el icono de descarga **⬇** situado junto al nombre de la release.
2. **Dashboard de Postmortem** (`/dashboards/postmortem/?release=...`):
   - Pulsa el botón **"Descargar informe PPT"** en la barra superior del análisis de la release.

Ambos botones invocan el endpoint REST `GET /api/reports/postmortem/{release}` en [`serve_app.py`](../../serve_app.py) (local) o en el servidor Nginx de producción.

---

## ⌨️ Generación por Línea de Comandos (CLI)

La vía CLI es idónea para tareas de automatización, generar informes por lotes o diagnosticar posibles errores de renderizado.

### 1. Requisitos Previos

Ejecuta los comandos desde la **raíz del proyecto** (`release-dashboard-application/`) con el entorno virtual activado:

```bash
# Windows
venv\Scripts\Activate.ps1
# Linux / macOS
source venv/bin/activate

# Instalar dependencias necesarias (python-pptx, plotly, kaleido)
pip install -r requirements.txt
```

### 2. Generar el Informe de una Release Concreta

```bash
python converters/cli/generate_postmortem_report.py 2026R7
```

Salida esperada:
```text
C:\...\release-dashboard-application\data\reports\2026R7-postmortem-report.pptx
```

Para especificar una ruta de salida personalizada, utiliza la opción `-o`:
```bash
python converters/cli/generate_postmortem_report.py 2026R7 -o C:\informes\2026R7-informe.pptx
```

### 3. Generar Informes para Todas las Releases en Lote (`--all`)

```bash
python converters/cli/generate_postmortem_report.py --all
```

El script procesa secuencialmente todas las releases de `releases-data.js` y genera un resumen al finalizar:
```text
Generados: 51 (2021R1, 2021R3, ..., 2026R7)
```

> [!TIP]
> Puedes cambiar el directorio de destino del lote con `--output-dir <ruta>`. Si una release individual contiene datos anómalos, el script no se detiene; procesa las demás y lista al final las que hayan fallado.

---

## 🏛️ Persistencia Desacoplada y Mecanismo de Caché

### Ubicaciones de Almacenamiento

El módulo de rutas (`report_generator.paths.get_default_reports_dir()`) gestiona la ubicación según el entorno:

| Entorno | Directorio Persistente de Informes |
|---|---|
| **VPS Producción** | `/infocodes/var/storage/release-dashboard/reports/{release}-postmortem-report.pptx` |
| **Desarrollo Local** | `data/reports/{release}-postmortem-report.pptx` (en la raíz del repositorio) |

### Lógica de Caché Inteligente

La generación de las 3 gráficas vectoriales mediante Kaleido toma entre 15 y 30 segundos por informe. Para optimizar el rendimiento:
- Si el archivo `.pptx` ya existe y su fecha de modificación es **posterior** a la de `dashboards/release-kpis/releases-data.js`, el servidor lo entrega **inmediatamente** (1-2 segundos) sin re-renderizar.
- Si has actualizado `releases-data.js`, el sistema detecta que el origen de datos es más nuevo y regenera el archivo automáticamente.

#### Cómo invalidar la caché manualmente:
Si necesitas forzar la regeneración sin haber modificado `releases-data.js`:

```bash
# En Windows (local):
del data\reports\2026R7-postmortem-report.pptx

# En Linux / VPS:
rm /infocodes/var/storage/release-dashboard/reports/2026R7-postmortem-report.pptx
```

Al volver a solicitar la descarga, se recomputará íntegramente.

---

## 🛠️ Solución de Problemas Frecuentes

### 1. "No hay datos de KPIs de Release para la release 'X'"
La release solicitada no figura en `dashboards/release-kpis/releases-data.js`. Verifica la coincidencia exacta de mayúsculas/minúsculas y el formato del nombre (ej: `2026R7`).

### 2. "No se pudieron cargar los datos de KPIs de Release"
El archivo `releases-data.js` no se ha encontrado o contiene un error de sintaxis JS. Asegúrate de estar ejecutando el comando desde la raíz del proyecto.

### 3. "PermissionError: el fichero anterior está abierto en otro programa"
El archivo PowerPoint ya generado está bloqueado porque permanece abierto en Microsoft PowerPoint. Cierra la aplicación y vuelve a lanzar el comando.

### 4. "ModuleNotFoundError: No module named 'pptx'" (o `plotly` / `kaleido`)
Faltan las librerías de generación y renderizado. Instálalas en el entorno virtual activo:
```bash
pip install -r requirements.txt
```

### 5. "Kaleido requires Google Chrome to be installed"
Desde la versión 1.x de `kaleido`, la exportación de gráficas Plotly a imagen rasterizada requiere un navegador basado en Chromium. Para instalarlo dentro del entorno Python del servidor sin requerir `sudo`:
```bash
plotly_get_chrome -y
```

### 6. "The browser seemed to close immediately after starting" (en Linux headless)
Ocurre si el VPS carece de librerías nativas que Chrome requiere para ejecutarse en modo headless (`libnss3`, `libgtk-3`, etc.).
Para comprobar qué dependencias faltan en el sistema:
```bash
ldd ~/.local/share/choreographer/deps/chrome-linux64/chrome | grep "not found"
```
Instala las bibliotecas faltantes en el servidor mediante el gestor de paquetes del sistema (`sudo apt install` o `sudo dnf install`). Consulta la sección de prerrequisitos de Linux en [`docs/VPS-REQUIREMENTS.md`](../03-arquitectura-y-datos/vps-infraestructura.md).

---

## 🔗 Documentación Relacionada

- [**`INFORME-EJECUTIVO-POSTMORTEM.md`**](INFORME-EJECUTIVO-POSTMORTEM.md): Guía del informe ejecutivo PowerPoint para **incidencias individuales**.
- [**`DASHBOARDS-API.md`**](../03-arquitectura-y-datos/dashboards-api.md): Catálogo de APIs y servicios consumidos por los dashboards.
- [**`DEPLOYMENT.md`**](../06-operaciones-y-gobernanza/despliegue-vps.md): Procedimiento de despliegue y topología VPS (`/infocodes/`).
- [**`DEVELOPMENT.md`**](../01-primeros-pasos/desarrollo.md): Entorno de desarrollo local y testing.
- [**`PROJECT-STRUCTURE.md`**](../03-arquitectura-y-datos/estructura-proyecto.md): Organización y persistencia desacoplada.
- [**`VPS-REQUIREMENTS.md`**](../03-arquitectura-y-datos/vps-infraestructura.md): Requisitos del sistema y paquetes del servidor Linux.
