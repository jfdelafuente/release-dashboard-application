# Migración de Estructura de Directorios: datos/ → data/

**Fecha de efectividad**: 2026-05-14

## Resumen

El proyecto ha reorganizado la estructura de directorios para datos de incidencias con el objetivo de mejorar seguridad, claridad y escalabilidad. Se ha pasado de una estructura inconsistente a una estructura clara, predecible y bien documentada.

## Cambios Principales

### Estructura Anterior (Deprecada)

```
proyecto/
├── datos/
│   ├── csv/              # Archivos CSV de entrada
│   ├── json/             # Archivos JSON de salida
│   └── errors/           # Reportes de errores
├── incidencias/          # (documentada pero no existía)
└── output/               # (documentada pero no existía)
```

**Problemas**:
- ❌ Inconsistencia: documentación menciona rutas que no existen
- ❌ Seguridad: `.gitignore` no protegía completamente `datos/`
- ❌ Claridad: usuarios confundidos sobre dónde colocar archivos
- ❌ Escalabilidad: sin estructura para archivo histórico

### Nueva Estructura (Actual)

```
proyecto/
└── data/
    ├── input/           # Archivos CSV de entrada (usuarios colocan aquí)
    ├── output/          # Archivos JSON generados (dashboard carga de aquí)
    ├── errors/          # Reportes de errores de validación
    └── archive/         # Archivos históricos (año/mes)
```

**Ventajas**:
- ✅ Claridad inmediata: nombres auto-explicativos
- ✅ Seguridad: `data/` totalmente protegido en `.gitignore`
- ✅ Documentación alineada: rutas coinciden con código y docs
- ✅ Escalabilidad: estructura para históricos indefinidos

## Migración de Archivos

### Para Usuarios (Analistas, Equipos de Operaciones)

#### Paso 1: Identifica tus archivos CSV

```bash
# Si tienes CSVs en la estructura anterior
find datos/csv/ -name "*.csv"
```

#### Paso 2: Copia tus CSVs a la nueva ubicación

```bash
# Windows
copy "datos\csv\*" "data\input\"

# Linux/Mac
cp datos/csv/* data/input/
```

#### Paso 3: Usa los nuevos conversores

Los conversores detectan automáticamente la nueva estructura:

```bash
# Windows
convert_incidents.bat "data/input/tu-archivo.csv"

# Linux/Mac
./convert_incidents.sh "data/input/tu-archivo.csv"
```

El JSON se genera automáticamente en `data/output/`.

### Para Desarrolladores

#### Código Python

Si tienes código que lee de la estructura antigua:

**Antes**:
```python
from csv_to_json import CsvToJsonConverter

converter.convert_file(
    input_path='datos/csv/archivo.csv',
    output_path='datos/json/archivo.json'
)
```

**Ahora**:
```python
from csv_to_json import CsvToJsonConverter

converter.convert_file(
    input_path='data/input/archivo.csv',
    output_path='data/output/archivo.json'
)
```

#### Scripts y Automatización

Los scripts `convert_incidents.py` y `convert_postmortems.py` incluyen **backward compatibility**:
- Por defecto usan `data/output/` y `data/errors/`
- Si `data/` no existe, caen atrás a `datos/json/` y `datos/errors/`

**No requiere cambios inmediatos**, pero se recomienda actualizar en próxima iteración.

## Período de Transición

### Ahora hasta 30 de Junio de 2026

- ✅ Ambas estructuras (`datos/` y `data/`) soportadas
- ✅ Conversores usan `data/` por defecto
- ✅ Código de fallback soporta `datos/` para compatibilidad atrás

### Después del 30 de Junio de 2026

- ❌ Estructura `datos/` será removida
- ❌ Código de fallback será eliminado
- ✅ Solo `data/` será soportado

## Dashboard Hub - Carga Automática

El Dashboard Hub ahora busca archivos JSON en `data/output/`:

```javascript
// Dashboard Hub busca automáticamente en:
data/output/*.json
data/output/*-massive.json
data/output/*-postmortem.json
```

**Para que tus archivos aparezcan en Dashboard Hub**:
1. Convierte tu CSV usando los scripts
2. JSON se genera automáticamente en `data/output/`
3. Dashboard Hub detecta y carga automáticamente
4. No requiere acción manual

## Verificación: ¿Está el cambio completo?

Puedes verificar que el cambio está completo revisando:

### ✅ Estructura de directorios

```bash
# Debe existir y tener archivos
ls -la data/input/
ls -la data/output/
ls -la data/errors/

# Debe estar vacío o con archivos de backup
ls -la datos/ 2>/dev/null || echo "datos/ ya está removido"
```

### ✅ Documentación alineada

```bash
# No debe encontrar referencias a incidencias/ o datos/
grep -r "incidencias/" README.md CONVERTER_USAGE.md
grep -r "datos/csv" *.py *.sh *.bat

# Si encuentra algo, actualizar manualmente
```

### ✅ Archivos protegidos en git

```bash
# Verificar que data/ está protegido
grep "^data/" .gitignore

# Intentar agregar archivo (debe ser rechazado)
echo "test" > data/input/test.csv
git add data/input/test.csv
# Resultado esperado: "The following paths are ignored"
```

## Preguntas Frecuentes

### P: ¿Dónde coloco mis archivos CSV?
**R**: En la carpeta `data/input/`. El dashboard y los conversores buscarán allí automáticamente.

### P: ¿Mi antiguo código seguirá funcionando?
**R**: Sí, durante el período de transición (hasta 30 junio 2026). Los conversores mantienen compatibilidad atrás.

### P: ¿Qué pasa si vuelvo a ejecutar un viejo script?
**R**: Los scripts incluyen lógica de fallback. Si especificas rutas antiguas, intentarán usar `datos/` si `data/` no existe.

### P: ¿Los datos antiguos se pierden?
**R**: No. Los archivos en `datos/` permanecen y son respaldados. Puedes migrar en tu propio horario.

### P: ¿Necesito actualizar mis dashboards?
**R**: No. Los dashboards actuales buscan en ambas ubicaciones durante el período de transición.

## Soporte

Si tienes dudas sobre la migración:
1. Revisa este documento
2. Consulta [README.md](README.md) para ejemplos actualizados
3. Revisa los comentarios en los scripts de conversión

## Más Información

- [README.md](README.md) - Documentación del conversor
- [CONVERTER_USAGE.md](CONVERTER_USAGE.md) - Guía de uso
- [CLAUDE.md](CLAUDE.md) - Detalles técnicos de la arquitectura
