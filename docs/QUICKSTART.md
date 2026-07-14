# Guía de Inicio Rápido

Pon en marcha Release Dashboard Application en 5 minutos.

## Configuración en 5 minutos

### Requisitos previos
- Python 3.8+ instalado
- git instalado (opcional, para clonar el repositorio)

### Paso 1: Clona o descarga el proyecto
```bash
# Opción A: Clonar con git
git clone <repository-url> release-dashboard-application
cd release-dashboard-application

# Opción B: Descargar y descomprimir el ZIP
# Descomprime la carpeta del proyecto y navega hasta ella
cd release-dashboard-application
```

### Paso 2: (Opcional) Crea un entorno virtual
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### Paso 3: Instala las dependencias
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

> Los dashboards en sí no necesitan dependencias Python (son HTML/CSS/JS con
> Plotly.js vía CDN). Estas dependencias son para `serve_app.py` y para los
> conversores/tests en `converters/`.

### Paso 4: (Opcional) Configura variables de entorno
```bash
# Copia la plantilla a un archivo local
cp config/.env.example config/.env

# Edita config/.env con tus valores (opcional para desarrollo local)
```

### Paso 5: Arranca el servidor local
```bash
python serve_app.py
# Abre: http://localhost:8000/dashboards/portal/
```

> ⚠️ **No uses `python -m http.server` ni Live Server de VSCode.** Ambos
> solo sirven archivos estáticos: no implementan `POST`, así que la subida
> de CSV desde el navegador fallará con "Failed to fetch". `serve_app.py`
> añade el endpoint `/api/upload`, necesario para poder subir un CSV desde
> la interfaz web.

### Paso 6: Carga tu primer CSV

**Opción A: Desde el navegador (recomendado)**

Con `serve_app.py` corriendo, entra en el dashboard de Incidencias Masivas o
de Postmortem/Release. Si no hay datos cargados, cada uno muestra una
pantalla de subida: arrastra el CSV o haz clic para seleccionarlo. El
servidor lo guarda en `data/input/` y ejecuta automáticamente el conversor
correspondiente, dejando el JSON en `data/output/`.

**Opción B: Manualmente, con los scripts de conversión**
```bash
# Windows - Incidencias Masivas
converters\scripts\bin\convert_incidents.bat data/input/tu-archivo.csv

# Windows - Postmortems
converters\scripts\bin\convert_postmortems.bat data/input/postmortem.csv

# Linux/Mac - Incidencias Masivas
./converters/scripts/bin/convert_incidents.sh data/input/tu-archivo.csv

# Linux/Mac - Postmortems
./converters/scripts/bin/convert_postmortems.sh data/input/postmortem.csv
```

**✅ Listo.** Tus archivos JSON estarán en `data/output/`.

### Paso 7: Abre el Portal

Con `serve_app.py` corriendo, ve a:
```
http://localhost:8000/dashboards/portal/
```
(o simplemente `http://localhost:8000/dashboards/`, que redirige ahí a
través de `dashboards/index.html`).

**El Portal enlaza a:**
- 📊 **Incidencias Masivas** (`dashboards/massive-incidents/`): evolución
  temporal, backlog, tendencias, filtros por estado/sistema/urgencia.
- 📋 **Postmortem / Release** (`dashboards/postmortem/`): análisis por
  despliegue (PAP/MESA), KPIs de resolución.
- 🔗 Enlaces a los paneles de los repos hermanos (Reportes de Incidencias,
  Gestión de Problemas), que no forman parte de este repositorio.

Cada dashboard carga automáticamente los datos más recientes de
`data/output/` (vía `index.json`) al abrirse.

## Siguientes pasos

### Opción A: Explora los dashboards especializados
Desde el Portal, haz clic en "Incidencias Masivas" o "Postmortem/Release"
para el análisis detallado de cada uno.

### Opción B: Procesa tus propios datos
```bash
# Coloca tu CSV en data/input/
cp tu-archivo.csv data/input/

# Conviértelo (o simplemente súbelo desde el navegador, ver Paso 6)
converters\scripts\bin\convert_incidents.bat data/input/tu-archivo.csv

# Revisa el resultado en data/output/
```

### Opción C: Desarrollo
```bash
# Lee la guía de desarrollo
cat docs/DEVELOPMENT.md

# O la guía de contribución
cat CONTRIBUTING.md
```

## Tareas comunes

### Convertir todos los CSV de un directorio
```bash
converters\scripts\bin\convert_incidents.bat data/input/ -o data/output/
```

### Ver el resumen de errores de conversión
```bash
converters\scripts\bin\convert_incidents.bat data/input/archivo.csv --show-errors
```

### Salida detallada (verbose)
```bash
converters\scripts\bin\convert_incidents.bat data/input/archivo.csv -v
```

### Ver la ayuda del conversor
```bash
converters\scripts\bin\convert_incidents.bat --help

# Documentación técnica completa
cat converters/docs/API.md
```

### Ejecutar la suite de tests de los conversores
```bash
cd converters
pytest tests/ -v

# Con reporte de cobertura
pytest tests/ --cov=src --cov-report=html
```

## Solución de problemas

### "Python no encontrado"
```bash
# Verifica que Python está instalado
python --version

# Si no aparece, instálalo desde: https://www.python.org/
```

### "Module not found" / "No module named ..."
```bash
# Asegúrate de tener el entorno virtual activado
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### "Permission denied" (Linux/Mac)
```bash
# Da permisos de ejecución a los scripts
chmod +x converters/scripts/bin/*.sh
```

### Errores de conversión
```bash
# Revisa el reporte de errores generado
cat data/errors/tu-archivo_errors.json

# Para más detalle
cat docs/TROUBLESHOOTING.md
```

### El dashboard no carga datos / "Failed to fetch" al subir un CSV
```bash
# Causa más común: estás usando `python -m http.server` o Live Server,
# que no soportan POST. Usa `python serve_app.py` en su lugar (Paso 5).

# ✅ Correcto:  http://localhost:8000/dashboards/portal/
# ❌ Incorrecto: file:///C:/Users/.../dashboards/portal/index.html (bloquea CORS)

# Verifica que data/output/ tiene archivos JSON
ls data/output/
# Debería mostrar: *.json y un index.json

# Revisa la consola del navegador (F12) por errores
# - Abre DevTools → Console
# - Busca errores de fetch o 404
# - Verifica: GET http://localhost:8000/data/output/index.json (debería ser 200)
```

## Documentación

- **Setup completo / desarrollo**: [DEVELOPMENT.md](DEVELOPMENT.md)
- **Solución de problemas**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Despliegue**: [DEPLOYMENT.md](DEPLOYMENT.md)
- **Contribución**: [CONTRIBUTING.md](CONTRIBUTING.md) (o [../CONTRIBUTING.md](../CONTRIBUTING.md))
- **API de los conversores**: [../converters/docs/API.md](../converters/docs/API.md)
- **Arquitectura de los conversores**: [../converters/docs/ARCHITECTURE.md](../converters/docs/ARCHITECTURE.md)
- **Seguridad**: [../SECURITY.md](../SECURITY.md)

## Estructura del proyecto

```
release-dashboard-application/
├── serve_app.py             # Servidor local (dashboards + /api/upload)
├── dashboards/               # Dashboards HTML/CSS/JS, cada uno en su subcarpeta
│   ├── index.html            # Redirige a /dashboards/portal/
│   ├── portal/                # Portal principal
│   ├── massive-incidents/
│   ├── postmortem/
│   └── release-kpis/
├── converters/                # Módulo Python de conversión CSV→JSON
│   ├── cli/                   # convert_incidents.py, convert_postmortems.py, upload_csv.py
│   ├── src/csv_to_json/       # Lógica de conversión (encoding, normalización, validación)
│   ├── scripts/bin/           # Wrappers .bat/.sh para los CLI
│   ├── tests/                 # Suite de tests (unit/integration/e2e)
│   └── docs/                  # Documentación técnica de los conversores
├── data/
│   ├── input/                 # Coloca aquí tus archivos CSV
│   ├── output/                 # JSON generados + index.json
│   └── errors/                 # Reportes de error de validación
├── config/                    # Plantillas de configuración
├── docs/                      # Documentación general del proyecto
└── requirements.txt / requirements-dev.txt
```

## Archivos clave

| Archivo | Propósito |
|---------|-----------|
| `serve_app.py` | Servidor local recomendado (soporta subida de CSV vía `/api/upload`) |
| `dashboards/portal/index.html` | **Portal principal** - punto de acceso a los dashboards |
| `dashboards/massive-incidents/index.html` | Dashboard de incidencias masivas |
| `dashboards/postmortem/index.html` | Dashboard de postmortem/release |
| `converters/scripts/bin/convert_incidents.bat` / `.sh` | Conversor de incidencias masivas |
| `converters/scripts/bin/convert_postmortems.bat` / `.sh` | Conversor de postmortems |
| `config/.env.example` | Plantilla de configuración de entorno |
| `data/input/` | Carpeta de entrada de CSV |
| `data/output/` | JSON generados (salida) |

## Siguiente paso: despliegue a producción

Cuando te sientas cómodo con el uso local:

1. Lee [DEPLOYMENT.md](DEPLOYMENT.md) para los procedimientos de despliegue.
2. Revisa [../SECURITY.md](../SECURITY.md) para la gestión de secretos en producción.
3. Consulta [CONTRIBUTING.md](CONTRIBUTING.md) para los estándares de código.
4. ¡Empieza a contribuir!

---

**Tiempo estimado**: 5 minutos
**Dificultad**: Principiante
**Última actualización**: 2026-07-09
