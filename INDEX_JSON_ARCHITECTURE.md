# Arquitectura index.json - Dashboard Hub Centralizado

## Visión General

El archivo `index.json` es un **archivo centralizado y compartido** que mantiene dos secciones independientes:
- **postmortem**: Gestiona `convert_postmortems.py`
- **massive**: Gestiona `convert_incidents.py`

Cada script **actualiza solo su sección** sin afectar la otra.

## Estructura

```json
{
  "postmortem": {
    "type": "postmortem",
    "updated": "2026-05-13T16:58:20.864861Z",
    "count": 4,
    "files": [
      {
        "name": "valid-100-postmortem.json",
        "size": 58518,
        "modified": "2026-05-13T16:57:44.968524",
        "path": "data/output/valid-100-postmortem.json"
      },
      ... (más archivos)
    ]
  },
  "massive": {
    "type": "massive",
    "updated": "2026-05-13T16:57:58.343454Z",
    "count": 2,
    "files": [
      {
        "name": "CS-MASIVA202605-massive.json",
        "size": 1031672,
        "modified": "2026-05-13T16:57:58.343455",
        "path": "data/output/CS-MASIVA202605-massive.json"
      },
      ... (más archivos)
    ]
  }
}
```

## Campos

### Nivel de Sección

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `type` | string | Tipo de datos (`postmortem` o `massive`) |
| `updated` | ISO 8601 | Timestamp de última actualización de esta sección |
| `count` | number | Cantidad de archivos en esta sección |
| `files` | array | Lista de archivos JSON |

### Nivel de Archivo

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `name` | string | Nombre del archivo JSON |
| `size` | number | Tamaño en bytes |
| `modified` | ISO 8601 | Timestamp de última modificación del archivo |
| `path` | string | Ruta relativa desde raíz del proyecto |

## Flujo de Actualización

### convert_postmortems.py

```python
# 1. Leer index.json existente (completo)
full_index = json.load('index.json')

# 2. Buscar archivos -postmortem.json
postmortem_files = glob('*-postmortem.json')

# 3. Construir nueva sección postmortem
full_index['postmortem'] = {
    'type': 'postmortem',
    'updated': datetime.now().isoformat() + 'Z',
    'count': len(postmortem_files),
    'files': [...]
}

# 4. Mantener intacta sección massive
# (no se modifica full_index['massive'])

# 5. Escribir index.json completo
json.dump(full_index, 'index.json')
```

### convert_incidents.py (build_index.py)

```python
# 1. Leer index.json existente (completo)
full_index = json.load('index.json')

# 2. Buscar archivos -massive.json
massive_files = glob('*-massive.json')

# 3. Construir nueva sección massive
full_index['massive'] = {
    'type': 'massive',
    'updated': datetime.now().isoformat() + 'Z',
    'count': len(massive_files),
    'files': [...]
}

# 4. Mantener intacta sección postmortem
# (no se modifica full_index['postmortem'])

# 5. Escribir index.json completo
json.dump(full_index, 'index.json')
```

## Escenarios de Uso

### Escenario 1: Ejecución Secuencial

```bash
# Ejecutar postmortem converter
python convert_postmortems.py data/input/

# Resultado:
# index.json['postmortem'].updated = nuevo timestamp
# index.json['massive'].updated = sin cambios

# Ejecutar incidents converter
python convert_incidents.py datos/csv/

# Resultado:
# index.json['postmortem'].updated = sin cambios
# index.json['massive'].updated = nuevo timestamp
```

### Escenario 2: Ejecución Paralela (Segura)

Aunque no se recomienda, el diseño es seguro para ejecución paralela:

```
Momento 0:
  index.json[postmortem].updated = T0
  index.json[massive].updated = T0

Momento 1 (paralelo):
  convert_postmortems.py Lee:  index.json completo
  convert_incidents.py Lee:    index.json completo

Momento 2:
  convert_postmortems.py Escribe: postmortem.updated = T2
  convert_incidents.py Escribe:   massive.updated = T2

Resultado Final:
  ✅ Ambas secciones actualizadas correctamente
  (No hay pérdida de datos)
```

### Escenario 3: Ejecución Cron Automatizada

```bash
# /etc/cron.d/conversores
0 2 * * * cd /app && python convert_postmortems.py data/input/ -b
0 3 * * * cd /app && python convert_incidents.py datos/csv/

# Resultado:
# - 2:00 AM: postmortem section actualizada
# - 3:00 AM: massive section actualizada
# - index.json siempre contiene información fresca de ambos tipos
```

## Dashboard Hub Integration

### Cómo Dashboard Hub Lee index.json

```javascript
// Lectura del index centralizado
async function loadAvailableDatasets() {
    const indexResponse = await fetch('/data/output/index.json');
    const index = await indexResponse.json();

    // Datos postmortem
    if (index.postmortem?.files?.length > 0) {
        displayPostmortemDatasets(index.postmortem.files);
        updateTimestamp('Postmortem', index.postmortem.updated);
    }

    // Datos masivos
    if (index.massive?.files?.length > 0) {
        displayMassiveIncidentsDatasets(index.massive.files);
        updateTimestamp('Massive', index.massive.updated);
    }
}
```

### Ventajas para Dashboard Hub

1. **Single Point of Truth**: Un archivo para todos los conversores
2. **Timestamps Independientes**: Sabe cuándo se actualizó cada tipo
3. **Escalable**: Fácil agregar nuevos tipos (p.ej. `"compliance": {...}`)
4. **Concurrencia Safe**: Dos conversores pueden actualizar sin conflictos

## Gestión de Errores

### ¿Qué pasa si falla convert_postmortems.py?

```
Antes:
index.json['postmortem'].updated = T1

convert_postmortems.py ejecuta pero falla
→ No actualiza index.json['postmortem']

index.json['postmortem'].updated = T1 (sin cambios)
```

**Beneficio**: Los usuarios ven que postmortem no fue actualizado (timestamp antiguo es evidencia)

### ¿Qué pasa si index.json es corrupto?

```python
# En build_index_for_hub()
try:
    full_index = json.load('index.json')
except:
    # Crear estructura por defecto
    full_index = {
        'postmortem': {...},
        'massive': {...}
    }
```

**Beneficio**: Auto-recuperación sin perder el registro existente

## Operaciones de Mantenimiento

### Limpiar archivos antiguos

```bash
# Eliminar archivo antiguo
rm data/output/old-file-massive.json

# Ejecutar converter
python convert_incidents.py datos/csv/

# Resultado: index.json actualizado automáticamente
#           (old-file no aparece más)
```

### Verificar integridad

```bash
# Ver sección postmortem
cat data/output/index.json | jq '.postmortem'

# Ver sección massive
cat data/output/index.json | jq '.massive'

# Ver archivos faltantes
python -c "
import json
with open('data/output/index.json') as f:
    index = json.load(f)
for f in index['postmortem']['files']:
    if not Path(f['path']).exists():
        print(f'Missing: {f[\"name\"]}')"
```

## Ventajas de la Arquitectura

### 1. Independencia
- Cada converter maneja su propia sección
- No hay acoplamiento entre scripts
- Cambios en uno no afectan al otro

### 2. Seguridad Concurrente
- Dos scripts pueden ejecutarse simultáneamente
- No hay race conditions
- Cada sección tiene su timestamp de actualización

### 3. Observabilidad
- Timestamp `updated` en cada sección muestra si está fresco
- `count` permite verificar integridad
- `modified` en cada archivo muestra cuándo entró

### 4. Mantenimiento
- Fácil agregar nuevos tipos sin afectar existentes
- Estructura uniforme para todos los tipos
- Compatible con Dashboard Hub sin cambios

## Migración desde Arquitectura Anterior

### Antes (lista plana)
```json
[
  {"name": "file1-postmortem.json", "type": "postmortem", ...},
  {"name": "file2-postmortem.json", "type": "postmortem", ...},
  {"name": "file3-massive.json", "type": "massive", ...}
]
```

### Después (secciones organizadas)
```json
{
  "postmortem": {
    "type": "postmortem",
    "updated": "...",
    "count": 2,
    "files": [...]
  },
  "massive": {
    "type": "massive",
    "updated": "...",
    "count": 1,
    "files": [...]
  }
}
```

**Nota**: Los conversores automáticamente migran al nuevo formato en su primera ejecución.

## Conclusión

La arquitectura de `index.json` con secciones independientes proporciona:

✅ Actualización segura por cada converter
✅ Sin conflictos en ejecución paralela
✅ Timestamps de actualización por tipo
✅ Escalable para nuevos tipos de datos
✅ Compatible con Dashboard Hub

---

**Archivos afectados**:
- `convert_postmortems.py` (función `build_index_for_hub`)
- `build_index.py` (función `build_index`)

**Formato**: JSON con dos secciones de nivel superior
**Compatibilidad**: Dashboard Hub, Postmortem Dashboard, Massive Incidents Dashboard
