# Migración de Estructura de Directorios - CSV/JSON

## 🎯 Nueva Estructura (Desde 2026-05-13)

La estructura de directorios ha sido reorganizada para mejorar la claridad y la seguridad:

**Ubicación de Archivos:**
- 📁 **Colocar CSVs en**: `data/input/`
- 📁 **JSONs generados en**: `data/output/`
- 📁 **Reportes de errores en**: `data/errors/`
- 📁 **Archivos históricos en**: `data/archive/`

## 📋 Pasos de Migración

Si estabas usando la estructura anterior (`datos/`), sigue estos pasos:

### Paso 1: Mover tus CSVs
```bash
# Si tienes archivos en datos/csv/, cópialos a data/input/
cp datos/csv/* data/input/

# Verifica que se copiaron correctamente
ls data/input/
```

### Paso 2: Mover archivos JSON existentes (opcional)
```bash
# Si tienes JSONs antiguos que quieras preservar
cp datos/json/* data/output/
```

### Paso 3: Actualizar tus scripts/procesos
Si tienes scripts que usan rutas antiguas, actualiza referencias de:
- `incidencias/` → `data/input/`
- `csv/` → `data/input/`
- `output/` → `data/output/`

### Paso 4: Comenzar a usar la nueva estructura
```bash
# Todos los nuevos archivos CSVs deben ir en data/input/
# El conversor los procesará y guardará el JSON en data/output/

convert_incidents.bat data/input/datos.csv
# → Genera: data/output/datos.json
```

## ⏱️ Período de Transición

**Fechas importantes:**
- **Inicio de migración**: 2026-05-13
- **Fin del soporte dual-path**: 2026-06-12 (30 días después)
- **Después de esa fecha**: Solo `data/` será soportado

**Durante el período de transición (hasta 2026-06-12):**
- ✅ El código soporta AMBAS estructuras
- ✅ Puedes usar `datos/` o `data/` indistintamente
- ✅ Tiempo para migrar gradualmente sin prisa

**Después del 2026-06-12:**
- ❌ Soporte para `datos/` será removido
- ✅ Solo funcionará con `data/`

## 🔒 Seguridad

### Problema resuelto ✅
Anteriormente:
- `.gitignore` NO protegía el directorio `datos/`
- Datos sensibles de incidencias podían ser comiteados a git por error
- Riesgo de exposición de información confidencial

Ahora:
- `data/` está agregado a `.gitignore`
- Los archivos en `data/input/`, `data/output/`, `data/errors/` son protegidos automáticamente
- No pueden ser comiteados a git accidentalmente

**Verifica la seguridad:**
```bash
# Esto NO debe agregar nada a git status
echo "test" > data/input/test.csv
git status
# Esperado: "nothing to commit" (test.csv es ignorado)
```

## 📊 Ventajas de la Nueva Estructura

| Aspecto | Antes | Ahora |
|---------|-------|-------|
| **Claridad** | Documentación menciona `incidencias/` pero no existe | Directorios claros y auto-documentados |
| **Seguridad** | `datos/` no ignorado en git | `data/` protegido en .gitignore |
| **Organización** | Mezcla incidencias/csv/output | input/output/errors/archive |
| **Escalabilidad** | Archivo histórico indefinido | Posibilidad de archive/YYYY/MM/ |
| **Usabilidad** | Usuario confundido sobre dónde colocar archivos | Instrucciones claras: `data/input/` |

## 🔄 Compatibilidad

### Convertidor CSV-to-JSON (convert_incidents.py)

El script ahora tiene **soporte dual-path**:

```python
# Preferencia: usar data/
DEFAULT_OUTPUT_DIR = Path("data/output")

# Fallback: si data/ no existe, usar datos/
if not DEFAULT_OUTPUT_DIR.exists():
    if Path("datos/json").exists():
        DEFAULT_OUTPUT_DIR = Path("datos/json")
```

**Esto significa:**
- Si ejecutas el conversor sin especificar salida: intenta usar `data/output/`
- Si `data/output/` no existe pero existe `datos/json/`: usa la estructura antigua
- Si especificas `-o output_dir`: respeta tu elección

### Ejemplo 1: Migración gradual
```bash
# Día 1: Copiaste algunos CSVs a data/input/
cp datos/csv/archivo1.csv data/input/

# Día 1: Ejecutar el conversor
python convert_incidents.py data/input/archivo1.csv
# → genera: data/output/archivo1.json ✅

# Día 5: Todavía hay archivos en datos/csv/
python convert_incidents.py datos/csv/archivo2.csv -o datos/json/
# → genera: datos/json/archivo2.json ✅ (respeta tu opción -o)
```

### Ejemplo 2: Especificar salida personalizada
```bash
# Puedes seguir usando la estructura antigua si lo necesitas
python convert_incidents.py datos/csv/datos.csv -o datos/json/

# O usar la nueva estructura
python convert_incidents.py data/input/datos.csv
# → usa data/output/ automáticamente
```

## 📚 Referencias

- **Documentación principal**: [README.md](README.md)
- **Guía de uso del conversor**: [CONVERTER_USAGE.md](CONVERTER_USAGE.md)
- **Especificación técnica**: [specs/001-csv-to-json-workflow/spec.md](specs/001-csv-to-json-workflow/spec.md)

## ❓ Preguntas Frecuentes

### P: ¿Se eliminarán mis archivos antiguos?
**R**: No. Los archivos en `datos/` permanecen intactos. La migración es gradual y voluntaria durante los próximos 30 días. Después de 2026-06-12, se recomienda archivo en `data/archive/`.

### P: ¿Puedo usar ambas estructuras a la vez?
**R**: Sí, durante el período de transición (hasta 2026-06-12). El código soporta ambas.

### P: ¿Qué pasa si olvido migrar antes del 2026-06-12?
**R**: El soporte para la estructura antigua será removido. Necesitarás migrar antes de esa fecha para que los nuevos procesos funcionen.

### P: ¿Cómo cargo archivos en el Dashboard?
**R**:
1. Coloca tu CSV en `data/input/`
2. Ejecuta `convert_incidents.bat data/input/archivo.csv`
3. Abre `massive-incidents-dashboard.html`
4. En la sección de carga, busca en `data/output/archivo.json`
5. Cárgalo en el dashboard

### P: ¿Qué pasa con `data/archive/`?
**R**: Es opcional. Úsalo para archivar JSONs antiguos organizados por año/mes. Ejemplo: `data/archive/2026/05/`

## 🚀 Próximos Pasos

1. **Hoy (o esta semana)**: Migra tus CSVs a `data/input/`
2. **Esta semana**: Verifica que los conversores funcionan con la nueva estructura
3. **Antes del 2026-06-12**: Completa la migración
4. **Después del 2026-06-12**: La estructura antigua no será soportada

---

**Versión**: 1.0 | **Fecha**: 2026-05-13 | **Próxima revisión**: 2026-06-12
