# Integración Dashboard Hub - Análisis de Cambios

## Resumen Ejecutivo

Se ha actualizado `convert_postmortems.py` para que **auto-genere y actualice `index.json`** después de cada conversión, permitiendo que Dashboard Hub descubra automáticamente los archivos JSON convertidos sin intervención manual.

## Cómo Funciona el Sistema

### 1. Arquitectura de Descubrimiento (Dashboard Hub)

```
Dashboard Hub (interfaz web)
    ↓
    Lee: data/output/index.json
    ↓
    Descubre archivos disponibles con sus metadatos
    ↓
    Permite cargar automáticamente en dashboards
```

### 2. Flujo de Conversión Actualizado

```
CSV Input (data/input/)
    ↓
convert_postmortems.py (o convert_incidents.py)
    ↓
    1. Procesa CSV → JSON
    2. Genera reporte de errores
    ↓
data/output/ (JSON files)
    ↓
build_index_for_hub() [NEW]
    ↓
data/output/index.json [ACTUALIZADÓ]
    ↓
Dashboard Hub descubre archivos automáticamente
```

## Cambios Realizados en convert_postmortems.py

### 1. **Funciones de Formato y Output** (líneas 45-99)

Se agregaron funciones para mejorar la experiencia del usuario:

```python
class Colors:
    """Códigos de color ANSI para output en consola."""
    HEADER, BLUE, CYAN, GREEN, YELLOW, RED, ENDC, BOLD, UNDERLINE

def print_header(text)      # Encabezados formateados
def print_success(text)     # Mensajes verdes [OK]
def print_error(text)       # Mensajes rojos [ERROR]
def print_info(text)        # Mensajes azules [INFO]
def print_warning(text)     # Mensajes amarillos [WARN]
def format_size(bytes)      # Convierte bytes a legible (17.6KB, etc)
```

**Beneficio**: Output similar a `convert_incidents.py` para consistencia

### 2. **Rutas por Defecto Configurables** (líneas 33-42)

```python
DATA_ROOT = Path("data")
DEFAULT_OUTPUT_DIR = DATA_ROOT / "output"
DEFAULT_ERROR_DIR = DATA_ROOT / "errors"

# Backward compatibility fallback
if not DEFAULT_OUTPUT_DIR.exists():
    if Path("datos/json").exists():
        DEFAULT_OUTPUT_DIR = Path("datos/json")
```

**Beneficio**: Compatibilidad con estructura antigua + nueva

### 3. **Nueva Función: build_index_for_hub()** (líneas 200-260)

Esta es la **función clave** para la integración Dashboard Hub:

```python
def build_index_for_hub(output_dir=None):
    """
    Genera index.json para Dashboard Hub.

    1. Busca archivos con sufijo -postmortem.json
    2. Busca archivos con sufijo -massive.json
    3. Ordena por fecha (más recientes primero)
    4. Genera index.json con metadatos
    """
```

**Detalle de la función**:

```python
# Buscar archivos postmortem (nuevos)
postmortem_files = [p for p in output_path.glob('*-postmortem.json')]

# Buscar archivos masivos (existentes)
massive_files = [p for p in output_path.glob('*-massive.json')]

# Combinar y ordenar por fecha
all_json_files = postmortem_files + massive_files
sorted_by_mtime(reverse=True)  # Más recientes primero

# Para cada archivo, crear entry en index
{
    "name": "valid-100-postmortem.json",
    "type": "postmortem",        # Tipo detectado automáticamente
    "size": 58518,               # Bytes
    "modified": "2026-05-13T...", # ISO 8601
    "path": "data/output/..."     # Ruta relativa
}

# Escribir index.json
data/output/index.json
```

### 4. **Llamada a build_index_for_hub() en main()** (líneas 315-325)

```python
def main():
    # ... procesar archivos CSV ...

    # Generar index.json DESPUÉS de conversión
    print_info("Generando index.json para Dashboard Hub...")
    try:
        if build_index_for_hub(str(DEFAULT_OUTPUT_DIR)):
            print_success(f"Index actualizado para Dashboard Hub")
        else:
            print_warning("No se pudo generar index.json")
    except Exception as e:
        print_warning(f"Error al generar index.json: {e}")
```

**Timing importante**: Se ejecuta **al final** de la conversión, garantizando que index.json siempre refleja el estado actual.

## Comparación con convert_incidents.py

### Similitudes

| Aspecto | convert_incidents.py | convert_postmortems.py |
|---------|----------------------|------------------------|
| Clase Colors | ✅ Sí | ✅ Sí (ahora) |
| Print helpers | ✅ Sí | ✅ Sí (ahora) |
| Rutas por defecto | ✅ Sí | ✅ Sí (ahora) |
| Sufijo automático | `-massive` | `-postmortem` |
| build_index() | ✅ Llamada | ✅ Llamada (ahora) |

### Diferencias Intencionales

| Aspecto | convert_incidents.py | convert_postmortems.py |
|---------|----------------------|------------------------|
| Tipos en index | Solo `massive` | `postmortem` + `massive` |
| Función build | Importa desde build_index.py | Define build_index_for_hub() |
| Mezcla de tipos | ❌ No (solo masivos) | ✅ Sí (ambos tipos) |

**Rationale**: `convert_postmortems.py` agrega archivos postmortem junto con los masivos ya existentes, por eso `build_index_for_hub()` es interna y detecta ambos tipos.

## Estructura del index.json

### Formato

```json
[
  {
    "name": "valid-100-postmortem.json",
    "type": "postmortem",
    "size": 58518,
    "modified": "2026-05-13T16:51:11.998460",
    "path": "data/output/valid-100-postmortem.json"
  },
  {
    "name": "CS_Masiva_20260513-massive.json",
    "type": "massive",
    "size": 1033147,
    "modified": "2026-05-13T16:47:01.633429",
    "path": "data/output/CS_Masiva_20260513-massive.json"
  }
]
```

### Campos

- **name**: Nombre del archivo JSON (sufijo identifica tipo)
- **type**: Tipo automáticamente detectado (`postmortem` o `massive`)
- **size**: Tamaño en bytes (para validación de carga)
- **modified**: ISO 8601 timestamp (para ordenamiento)
- **path**: Ruta relativa desde raíz del proyecto

### Ordenamiento

**Regla**: Archivos más recientes primero (por `modified` timestamp)

**Razón**: Dashboard Hub puede mostrar "Archivos recientes" sin lógica adicional

## Flujo de Uso Completo

### Escenario 1: Conversión Manual Single File

```bash
python convert_postmortems.py data/input/postmortem.csv
```

**Que sucede**:
```
1. Lee: data/input/postmortem.csv
2. Valida y normaliza registros
3. Escribe: data/output/postmortem-postmortem.json
4. Escribe: data/errors/postmortem-postmortem_errors.json
5. Ejecuta: build_index_for_hub()
   └─ Actualiza: data/output/index.json
6. Dashboard Hub detecta automáticamente el nuevo archivo
```

### Escenario 2: Batch Conversion

```bash
python convert_postmortems.py data/input/ -b
```

**Que sucede**:
```
1. Procesa: file1.csv → file1-postmortem.json
2. Procesa: file2.csv → file2-postmortem.json
3. Procesa: file3.csv → file3-postmortem.json
4. Ejecuta: build_index_for_hub()
   └─ Index contiene: [file1, file2, file3] + [existing masivos]
5. Dashboard Hub ve todos los archivos disponibles
```

### Escenario 3: Integración Manual con Dashboard Hub

```bash
# Usuario abre Dashboard Hub en navegador
# Dashboard Hub:
#   1. Carga: data/output/index.json
#   2. Presenta lista de archivos disponibles
#   3. Usuario selecciona: "valid-100-postmortem.json"
#   4. Dashboard carga automáticamente el Postmortem Dashboard
#   5. Muestra KPIs y datos convertidos
```

## Comparación de Experiencia de Usuario

### Antes (sin index.json)

```
1. Usuario: "¿Dónde están mis JSONs?"
2. Usuario: "¿Cuál es el archivo más reciente?"
3. Usuario: "¿Cuál es el tamaño del archivo?"
→ Usuario debe navegar manualmente data/output/
→ Copia ruta a mano
→ Carga manualmente en dashboard
```

### Después (con index.json)

```
1. Usuario: python convert_postmortems.py data/input/
2. Dashboard Hub:
   ✓ Lee index.json automáticamente
   ✓ Muestra lista de archivos con metadatos
   ✓ Usuario selecciona archivo
   ✓ Dashboard carga automáticamente
→ Experiencia sin fricción
```

## Implementación Técnica

### Detección de Tipo de Archivo

```python
if '-postmortem.json' in file_path.name:
    file_type = 'postmortem'
elif '-massive.json' in file_path.name:
    file_type = 'massive'
else:
    file_type = 'unknown'
```

**Ventaja**: No requiere configuración, usa convención de nombres

### Codificación UTF-8

```python
with open(index_file, 'w', encoding='utf-8') as f:
    json.dump(index, f, indent=2, ensure_ascii=False)
```

**Razón**: Soporta caracteres españoles (Descripción, Postmortem, etc)

### Timestamps ISO 8601

```python
'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
# Resultado: "2026-05-13T16:51:11.998460"
```

**Beneficio**: Formato estándar, fácil de parsear en cualquier lenguaje

## Validación del Sistema

### Test 1: Generación de index.json

```bash
python convert_postmortems.py tests/test_data/valid-100.csv
# Output: [OK] Index actualizado para Dashboard Hub
ls -l data/output/index.json
# Resultado: Archivo creado con contenido válido JSON
```

✅ **Resultado**: index.json generado correctamente

### Test 2: Detección de Tipos

```bash
cat data/output/index.json | grep type
# Resultado:
# "type": "postmortem",
# "type": "massive"
```

✅ **Resultado**: Ambos tipos detectados correctamente

### Test 3: Ordenamiento por Fecha

```bash
cat data/output/index.json | grep modified
# Resultado: Timestamps en orden descendente (recientes primero)
```

✅ **Resultado**: Ordenamiento correcto

### Test 4: Rutas Relativas

```bash
cat data/output/index.json | grep path
# Resultado: "path": "data/output/..."
```

✅ **Resultado**: Rutas relativas correctas para Dashboard Hub

## Integración con Dashboard Hub (Lado Dashboard)

### Como Dashboard Hub Lee index.json

```javascript
// dashboard-hub.js (hipotético)
async function loadAvailableFiles() {
    const response = await fetch('/data/output/index.json');
    const files = await response.json();

    // Agrupar por tipo
    const postmortems = files.filter(f => f.type === 'postmortem');
    const massive = files.filter(f => f.type === 'massive');

    // Mostrar en UI
    displayPostmortems(postmortems);
    displayMassive(massive);
}
```

### Ventajas para Dashboard Hub

1. **Auto-descubrimiento**: No requiere configuración manual
2. **Metadatos**: Puede mostrar tamaño, fecha, sin cargar JSON completo
3. **Ordenamiento**: Archivos recientes arriba automáticamente
4. **Tipificación**: Puede mostrar dashboards correctos para cada tipo

## Recomendaciones

### 1. Para Usuarios

```bash
# Forma estándar de usar
python convert_postmortems.py data/input/ -b

# Dashboard Hub automáticamente:
# - Descubre archivos
# - Muestra lista actualizada
# - Permite cargar sin paso manual
```

### 2. Para Integraciones

```bash
# Cron job diario
0 2 * * * cd /app && python convert_postmortems.py data/input/ -b

# Resultado automático:
# - Todos los CSVs convertidos
# - index.json actualizado
# - Dashboard Hub listo
```

### 3. Para Documentación

Los usuarios deberían saber:
- ✅ Los archivos con sufijo `-postmortem.json` se auto-descubren
- ✅ El `index.json` se genera automáticamente tras conversión
- ✅ Dashboard Hub carga datos sin intervención manual
- ❌ NO copiar `index.json` manualmente (se sobrescribe)

## Conclusión

La integración de `build_index_for_hub()` en `convert_postmortems.py` proporciona:

1. **Automatización**: Sin pasos manuales post-conversión
2. **Descubrimiento**: Dashboard Hub encuentra archivos automáticamente
3. **Consistencia**: Mismo patrón que `convert_incidents.py`
4. **Escalabilidad**: Soporta múltiples tipos de archivos (postmortem + massive)
5. **UX Mejorada**: Usuarios no navegan directorios manualmente

---

**Archivos modificados**: `convert_postmortems.py`
**Archivos generados**: `data/output/index.json` (automático)
**Compatible con**: Dashboard Hub, Postmortem Dashboard, Massive Incidents Dashboard
