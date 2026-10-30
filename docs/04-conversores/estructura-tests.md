# Estructura de la Suite de Pruebas

Este documento detalla la organización modular, categorización y modo de ejecución de la suite de pruebas automatizadas del módulo `converters`.

---

## 🏛️ Organización de la Suite

Las pruebas están estructuradas de forma híbrida combinando la **funcionalidad evaluada** con la **profundidad de la prueba** (pruebas unitarias puras, pruebas de integración con I/O y pruebas extremo a extremo/rendimiento).

```text
converters/tests/
├── conftest.py              # Fixtures compartidos globales y configuración
├── test_data/               # Fixtures inmutables de entrada (CSVs de prueba)
├── utils/                   # Utilidades y funciones auxiliares para tests
│
├── unit/                    # PRUEBAS UNITARIAS (Lógica pura, sin I/O en repo)
│   ├── encoding/            # Detección y manejo de codificaciones (UTF-8, Latin-1, CP1252...)
│   ├── delimiter/           # Detección de delimitadores (, ; \t)
│   ├── normalizers/         # Normalizadores de fechas, cadenas, urgencias y estados
│   ├── validators/          # Reglas de validación, presencia de campos y tipos
│   ├── schemas/             # Estructura de salida, generación de _metadata y KPIs
│   ├── derivation/          # Algoritmos de derivación (PAP vs MESA)
│   └── report_generator/    # Pruebas unitarias de construcción PPTX, calculadoras y gráficos
│
├── integration/             # PRUEBAS DE INTEGRACIÓN (Pipelines con I/O aislado vía tmp_path)
│   ├── converters/          # Pipeline de conversión CSV a JSON de incidencias
│   ├── postmortem/          # Pipeline de conversión y cálculo de postmortems
│   └── report_generator/    # Generación real de informes PPTX por lotes y contextos
│
└── e2e/                     # PRUEBAS EXTREMO A EXTREMO Y RENDIMIENTO
    └── performance/         # Benchmarks de escalabilidad, memoria y velocidad
```

---

## 📂 Detalle de Categorías

### 1. Pruebas Unitarias (`tests/unit/`)

Verifican la lógica algorítmica sin realizar operaciones de disco persistentes:

* **`encoding/`**: Verifica la detección de UTF-8, UTF-8-sig (con BOM), Windows-1252, ISO-8859-15 y preservación de tildes/caracteres especiales.
* **`delimiter/`**: Comprueba la precisión del sniffer para coma (`,`), punto y coma (`;`) y tabulación (`\t`).
* **`normalizers/`**: Valida transformaciones de fechas (`DD/MM/YYYY HH:mm a/p`), normalización de estados a formato *Title Case* y limpieza de prefijos numéricos ("4-Alta" → "Alta").
* **`validators/`**: Evalúa que los registros con valores incorrectos o campos obligatorios ausentes sean rechazados y anotados en el reporte de errores.
* **`schemas/`**: Asegura la estructura Envelope (`_metadata` con KPIs precalculadas + `data`), agregación matemática y métricas de resolución.
* **`derivation/`**: Comprueba la asignación determinista del despliegue (asignando PAP al registro más temprano y MESA a los subsiguientes).
* **`report_generator/`**: Valida utilidades gráficas Plotly, resolutores de rutas seguras, constructores de tablas y cálculo de KPIs consolidadas.

### 2. Pruebas de Integración (`tests/integration/`)

Ejecutan flujos completos utilizando ficheros CSV reales de `tests/test_data/` y escribiendo sus salidas en directorios temporales aislados mediante el fixture `tmp_path`:

* **`converters/`**: Ingesta de CSVs masivos, verificación de cabeceras, manejo de registros mixtos válidos/inválidos y preservación de estadísticas.
* **`postmortem/`**: Ingesta de postmortems por release, agregación por `--release-name`, validación de cero pérdidas silenciosas de datos y cálculo del porcentaje de éxito.
* **`report_generator/`**: Construcción física de presentaciones ejecutivas PowerPoint (`.pptx`), generación de diapositivas y renderizado de gráficos.

### 3. Pruebas Extremo a Extremo (`tests/e2e/`)

Evalúan el comportamiento global y el rendimiento del sistema:

* **`performance/`**: Comprueba que la velocidad de conversión supere los 19.000 registros/segundo y que el consumo de memoria se mantenga por debajo de 50 MB de RAM.

---

## 🚀 Comandos de Ejecución

> **Importante**: Para asegurar que las rutas relativas a las fixtures de prueba se resuelvan de manera fiable, ejecute siempre los comandos situándose en el subdirectorio `converters`:

```bash
cd converters
```

### Ejecutar Todas las Pruebas
```bash
pytest tests/ -v
```

### Ejecutar por Categoría
```bash
# Solo pruebas unitarias
pytest tests/unit/ -v

# Solo pruebas de integración
pytest tests/integration/ -v

# Solo pruebas de rendimiento
pytest tests/e2e/performance/ -v
```

### Ejecutar por Módulo Funcional
```bash
# Normalizadores
pytest tests/unit/normalizers/ -v

# Generador de reportes PPTX
pytest tests/unit/report_generator/ tests/integration/report_generator/ -v

# Validación y esquemas
pytest tests/unit/validators/ tests/unit/schemas/ -v
```

### Ejecutar en Paralelo
```bash
# Utiliza todos los núcleos de CPU disponibles
pytest tests/ -n auto
```

### Medir Cobertura de Código
```bash
# Reporte en consola
pytest tests/ --cov=src --cov-report=term-missing

# Reporte interactivo HTML
pytest tests/ --cov=src --cov-report=html
```

---

## 📊 Métricas de la Suite

* **Total de pruebas**: 581 tests
* **Tiempo de ejecución**: ~12 segundos (ejecución completa)
* **Cobertura de código**: ≥ 80% requerida
* **Aislamiento**: 100% de los tests que generan ficheros emplean el fixture `tmp_path` de pytest.
