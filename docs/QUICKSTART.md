# Guía de Inicio Rápido

Pon en marcha Release Dashboard Application en 5 minutos en tu entorno local.

---

## ⚡ Configuración en 5 Minutos

### Requisitos previos
- **Python 3.10+** instalado (recomendado **Python 3.11**).
- **Git** instalado (para clonar y versionar).
- Navegador web moderno (Chrome, Firefox, Edge).

---

### Paso 1: Clona o descarga el proyecto

```bash
# Opción A: Clonar con git (rama production recomendada para despliegue)
git clone <repository-url> release-dashboard-application
cd release-dashboard-application

# Opción B: Descargar y descomprimir el ZIP
cd release-dashboard-application
```

---

### Paso 2: Crea un entorno virtual

```bash
# En Windows (PowerShell / CMD)
python -m venv venv
.\venv\Scripts\Activate.ps1   # En PowerShell
# o bien: venv\Scripts\activate.bat en CMD

# En Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

---

### Paso 3: Instala las dependencias

```bash
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

> **Nota**: El frontend es estático (HTML5, CSS3, JavaScript ES6+ con Plotly.js vía CDN) y no requiere Node.js ni build step. Las dependencias Python se utilizan exclusivamente para el servidor local (`serve_app.py`), el motor conversor CLI (`converters/`) y la suite de pruebas automatizadas.

---

### Paso 4: (Opcional) Configura variables de entorno

```bash
# Copia la plantilla base
cp config/.env.example config/.env

# El archivo .env incluye configuraciones por defecto listas para funcionar en local:
# PORT=8080
# FASTAPI_BACKEND_URL=http://127.0.0.1:8000
```

---

### Paso 5: Arranca el servidor local de desarrollo

```bash
python serve_app.py
```

La consola confirmará el inicio del servicio:
```text
==================================================
Release Dashboard Server (Estático & Provisión)
Sirviendo desde: C:\...\release-dashboard-application
URL: http://localhost:8080/
Dashboard Portal: http://localhost:8080/dashboards/portal/
Gestión de Problemas (proxy :3001): http://localhost:8080/problemas
Nota: API principal FastAPI disponible en http://localhost:8000/docs
==================================================
```

> ⚠️ **Importante**: No utilices `python -m http.server` ni Live Server de VSCode. Estos servidores genéricos no implementan métodos `POST` (la subida de archivos fallará con `Failed to fetch`), ni configuran los proxies locales hacia Epsilon IA o el backend de generación PowerPoint. Utiliza siempre `serve_app.py`.

---

### Paso 6: Carga tu primer CSV

#### Opción A: Desde el navegador (Recomendado)
1. Con `serve_app.py` en ejecución, abre en tu navegador el **Dashboard de Incidencias Masivas** o **Postmortem**.
2. Si no existen datos previos, aparecerá automáticamente el panel interactivo de carga.
3. Arrastra tu archivo CSV o haz clic para examinarlo.
4. El servidor guardará el CSV en `data/input/`, ejecutará el conversor correspondiente y generará de inmediato el JSON normalizado en `data/output/` refrescando el catálogo `index.json`.

#### Opción B: Desde la línea de comandos (CLI)

```bash
# Windows - Conversión de Incidencias Masivas
converters\scripts\bin\convert_incidents.bat data/input/tu-archivo.csv

# Windows - Conversión de Postmortems
converters\scripts\bin\convert_postmortems.bat data/input/postmortem.csv

# Linux/macOS - Incidencias Masivas
./converters/scripts/bin/convert_incidents.sh data/input/tu-archivo.csv

# Linux/macOS - Postmortems
./converters/scripts/bin/convert_postmortems.sh data/input/postmortem.csv
```

Los JSON generados se depositarán en `data/output/`.

---

### Paso 7: Explora el Portal y los Dashboards

Con el servidor corriendo, accede a:
```text
http://localhost:8080/dashboards/portal/
```
*(O `http://localhost:8080/dashboards/`, que redirige automáticamente al portal).*

El ecosistema cuenta con los siguientes paneles integrados:

- 🚪 **Portal General** (`dashboards/portal/`): Punto de entrada único con buscador global de incidencias, métricas agregadas y accesos rápidos.
- 📊 **Incidencias Masivas** (`dashboards/massive-incidents/`): Seguimiento temporal de volumen, backlog, SLA, filtros dinámicos por estado/sistema/urgencia y gráficos Plotly.
- 📋 **Postmortem y Despliegues** (`dashboards/postmortem/`): Análisis de incidencias por ventana de despliegue (PAP/MESA) y tiempos de resolución.
- 📈 **Release KPIs** (`dashboards/release-kpis/`): Métricas de calidad y estabilidad de releases.
- 📑 **Reportes de Incidencias** (`dashboards/reportes-incidencias/`): Panel de consulta y gestión de informes de incidencias.
- 🤖 **Catálogo de Agentes IA y Skills** (`dashboards/agents-catalog/`): Catálogo interactivo de agentes y habilidades (*skills*), visor Markdown de fichas técnicas y generador CLI de comandos de despliegue.
- 🤖 **Resumen IA (Epsilon)**: Modal flotante inteligente disponible en los dashboards para generar resúmenes automáticos de incidencias.

---

## 🛠️ Tareas Comunes

### Procesamiento batch de múltiples CSVs
```bash
# Procesa todos los CSVs ubicados en data/input/ y emite a data/output/
converters\scripts\bin\convert_incidents.bat data/input/ -o data/output/
```

### Visualizar errores y discrepancias de validación
```bash
converters\scripts\bin\convert_incidents.bat data/input/archivo.csv --show-errors
```

### Generación de Informes Ejecutivos PowerPoint
```bash
python converters/cli/generate_postmortem_report.py --input data/output/incidencias.json --output data/reports/informe_ejecutivo.pptx
```

### Generación y Actualización del Catálogo de Agentes IA
```bash
python converters/cli/build_agents_catalog.py
# Genera o refresca data/output/agents_catalog.json desde la biblioteca de agentes
```

### Ejecución de la Suite de Tests Automatizados
La suite cuenta con más de **516 tests** automatizados (unitarios, de integración y end-to-end):

```bash
# Ejecutar desde el subdirectorio converters
cd converters
pytest tests/ -v

# Ejecutar con reporte de cobertura (gate mínimo del 80%)
pytest tests/ -v --cov=src --cov-report=term-missing
cd ..
```

---

## ❓ Solución de Problemas Frecuentes

### 1. "Python no encontrado" o comando no reconocido
Comprueba que Python 3.10+ esté instalado y registrado en la variable de entorno `PATH`:
```bash
python --version
```

### 2. "Failed to fetch" al arrastrar o subir un CSV
- **Causa**: Estás usando `python -m http.server`, una extensión Live Server o abriendo el HTML directamente con doble clic (`file:///...`).
- **Solución**: Detén el proceso y arranca con `python serve_app.py`. Accede a través de `http://localhost:8080/dashboards/portal/`.

### 3. El puerto 8080 ya está en uso
Puedes especificar un puerto alternativo:
```bash
python serve_app.py --port 8090
```

### 4. "ModuleNotFoundError: No module named 'src'" o fallos de importación
Asegúrate de tener activado el entorno virtual (`venv`) con todas las dependencias instaladas:
```bash
pip install -r requirements.txt -r requirements-dev.txt
```

---

## 📁 Datos: Local vs Producción

- **Entorno Local**: Los datos se almacenan en la carpeta local `data/` (`input/`, `output/`, `reports/`, `errors/`, `archive/`). Esta carpeta está ignorada por Git (`.gitignore`).
- **Entorno Producción (VPS `10.132.26.96`)**: El almacenamiento está estrictamente desacoplado en `/infocodes/var/storage/release-dashboard/` y `/infocodes/var/storage/executive_pptx/`. Las nuevas releases se conectan a estos datos mediante symlinks persistentes.

---

## 🚀 Siguiente Paso: Despliegue a Producción

Cuando tus cambios estén listos y probados localmente:

1. Consulta [DEPLOYMENT.md](DEPLOYMENT.md) para el flujo de despliegue mediante el script `deploy-production.ps1` (Standalone Runtime).
2. Revisa [DEVELOPMENT.md](DEVELOPMENT.md) para estándares de desarrollo, linting y Git hooks.
3. Consulta [GITHUB-BRANCH-PROTECTION.md](GITHUB-BRANCH-PROTECTION.md) para las reglas de PR y ramas protegidas (`main` y `production`).
4. Revisa [LOGS.md](LOGS.md) para el formato unificado de bitácora técnica.

---

**Tiempo estimado de configuración**: 5 minutos  
**Dificultad**: Principiante / Intermedio  
**Última actualización**: 2026-10-20
