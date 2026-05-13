# 🚀 Guía de Uso - Script de Conversión CSV → JSON

Scripts listos para ejecutar la conversión de archivos CSV de incidencias masivas a formato JSON compatible con el Dashboard.

## 📋 Archivos de Script

| Sistema | Archivo | Uso |
|---------|---------|-----|
| **Windows** | `convert_incidents.bat` | `convert_incidents.bat archivo.csv` |
| **Linux/Mac** | `convert_incidents.sh` | `./convert_incidents.sh archivo.csv` |
| **Python directo** | `convert_incidents.py` | `python convert_incidents.py archivo.csv` |

## 🎯 Inicio Rápido

### En Windows (CMD o PowerShell)

**Opción 1: Desde CMD (recomendado)**
```batch
REM Abrir CMD (símbolo del sistema)
REM Luego ejecutar:

REM Convertir archivo específico
convert_incidents.bat data/input/datos.csv

REM Convertir archivo con espacios en el nombre
convert_incidents.bat "data/input/datos con espacios.csv"

REM Convertir con directorio de salida
convert_incidents.bat data/input/datos.csv -o data/output/

REM Convertir directorio completo
convert_incidents.bat data/input/

REM Ver reporte de errores después
convert_incidents.bat data/input/datos.csv --show-errors
```

**Opción 2: Directamente con Python (si hay problemas con el batch)**
```powershell
# PowerShell
python convert_incidents.py "data/input/datos.csv"
python convert_incidents.py "data/input/archivo con espacios.csv" -o data/output/

# CMD
python convert_incidents.py data/input/datos.csv
python convert_incidents.py "data/input/archivo con espacios.csv" -o data/output/
```

### En Linux/Mac

```bash
# Convertir archivo específico
./convert_incidents.sh data/input/datos.csv

# Convertir con directorio de salida
./convert_incidents.sh data/input/datos.csv -o data/output/

# Convertir directorio completo
./convert_incidents.sh data/input/

# Ver reporte de errores después
./convert_incidents.sh data/input/datos.csv --show-errors
```

### Directamente con Python (todas las plataformas)

```bash
python convert_incidents.py data/input/datos.csv
python convert_incidents.py data/input/ -o data/output/ -e data/errors/
```

## 📖 Ejemplos Prácticos

### Ejemplo 1: Convertir archivo de ejemplo

```bash
# Windows
convert_incidents.bat "data/input/CS-Informe incidencias P1,  P2 y P3 - 2026 - 13 May 2026.csv"

# Linux/Mac
./convert_incidents.sh "data/input/CS-Informe incidencias P1,  P2 y P3 - 2026 - 13 May 2026.csv"
```

**Salida esperada**:
```
══════════════════════════════════════════════════════════════════
    CSV to JSON Converter - Dashboard de Incidencias Masivas
══════════════════════════════════════════════════════════════════

ℹ Encontrados 1 archivo(s) CSV para procesar

[1/1]
ℹ Procesando: CS-Informe incidencias P1,  P2 y P3 - 2026 - 13 May 2026.csv
ℹ Tamaño: 118.6KB
  Total registros: 487
  Exitosos: 487
  Tasa éxito: 100.0%
  Encoding: utf-8
✓ JSON guardado: CS-Informe incidencias P1,  P2 y P3 - 2026 - 13 May 2026.json
           Tamaño: 234.5KB

══════════════════════════════════════════════════════════════════
                    Resumen de Conversión
══════════════════════════════════════════════════════════════════

✓ Conversión completada sin errores fatales

ℹ Para más información, consulta: specs/001-csv-to-json-workflow/quickstart.md
```

### Ejemplo 2: Convertir múltiples archivos con reporte de errores

```bash
# Windows
convert_incidents.bat data/input/ -o data/output/ -e data/errors/ --show-errors

# Linux/Mac
./convert_incidents.sh data/input/ -o data/output/ -e data/errors/ --show-errors
```

**Salida esperada con errores**:
```
══════════════════════════════════════════════════════════════════
    CSV to JSON Converter - Dashboard de Incidencias Masivas
══════════════════════════════════════════════════════════════════

ℹ Encontrados 3 archivo(s) CSV para procesar

[1/3]
ℹ Procesando: 2026R4MESAPOST.csv
ℹ Tamaño: 20.9KB
  Total registros: 84
  Exitosos: 81
  Fallidos: 3
  Tasa éxito: 96.4%
  Encoding: utf-8
✓ JSON guardado: data/output/2026R4MESAPOST.json
⚠ Errores reportados: data/errors/2026R4MESAPOST_errors.json (3 registros)

[2/3]
ℹ Procesando: 2026R4POSTMORTEM.csv
...

══════════════════════════════════════════════════════════════════
                    Resumen de Conversión
══════════════════════════════════════════════════════════════════

✓ Conversión completada sin errores fatales

Archivo: 2026R4MESAPOST_errors.json

Primeros 5 errores encontrados:

Error 1 (Fila 23):
  • Urgencia:
    Valor: 5-Desconocida
    Razón: Invalid value: must be one of [Baja, Medio, Alta, Crítica]

Error 2 (Fila 45):
  • Estatus:
    Valor: En Pausa
    Razón: Invalid value: must be one of [Abierto, Pendiente, En Progreso, Resuelto, Cerrado, Cancelado]
```

## 🔧 Opciones Disponibles

### `-o, --output`
Especifica el archivo o directorio de salida para el JSON.

```bash
# Archivo específico
convert_incidents.bat datos.csv -o incidents.json

# Directorio (usa mismo nombre del CSV)
convert_incidents.bat datos.csv -o data/output/
```

### `-e, --errors`
Especifica archivo o directorio para el reporte de errores.

```bash
# Archivo específico
convert_incidents.bat datos.csv -e errors.json

# Directorio (usa nombre automático)
convert_incidents.bat datos.csv -e data/errors/
```

### `--show-errors`
Muestra resumen de errores en la consola después de la conversión.

```bash
convert_incidents.bat datos.csv --show-errors
```

### `-v, --verbose`
Output más detallado durante la conversión.

```bash
convert_incidents.bat datos.csv -v
```

### `--help`
Muestra ayuda completa.

```bash
convert_incidents.bat --help
```

## 📊 Archivos Generados

### JSON Output (`incidents.json`)

```json
[
  {
    "ID de incidencia": "INC000003884945",
    "Descripción": "LIVEPERSON // DERIO // ERROR FUNCIONAL",
    "Estatus": "Cerrado",
    "Fecha de envío": "02/01/2026 8:14 AM",
    "Grupo asignado": "CEP CAU AGI",
    "Urgencia": "Baja",
    "Impacto": "Masiva",
    "Fecha de última resolución": "12/01/2026 8:24 AM"
  },
  ...
]
```

### Error Report (`incidents_errors.json`)

```json
{
  "summary": {
    "total_records": 487,
    "successful": 484,
    "failed": 3,
    "success_rate": 99.4
  },
  "errors": [
    {
      "row": 23,
      "fields": {
        "Urgencia": {
          "original": "5-Desconocida",
          "error": "Invalid value: must be one of [Baja, Medio, Alta, Crítica]"
        }
      }
    },
    ...
  ]
}
```

## 🎨 Características del Script

✅ **Salida con colores**
- Verde para éxitos
- Rojo para errores
- Amarillo para advertencias
- Cyan para información

✅ **Información detallada**
- Tamaño de archivos
- Tasa de éxito en porcentaje
- Encoding detectado
- Cantidad de errores

✅ **Manejo de rutas**
- Acepta archivos y directorios
- Crea directorios de salida automáticamente
- Preserva nombres de archivos

✅ **Procesamiento multiple**
- Convierte todos los CSV en un directorio
- Reporta progreso [1/N]
- Resumen final de conversión

## 🐛 Solución de Problemas

### Error en Windows: "No se esperaba..." o caracteres no reconocidos

**Causa**: PowerShell interpreta los argumentos de forma diferente a CMD.

**Soluciones**:

1. **Opción A**: Ejecutar desde CMD (recomendado)
```batch
REM Abre CMD (símbolo del sistema) en lugar de PowerShell
REM Luego ejecuta:
convert_incidents.bat "data/input/datos.csv"
```

2. **Opción B**: Usar comillas dobles en PowerShell
```powershell
# PowerShell
python convert_incidents.py "data/input/datos.csv"
```

3. **Opción C**: Usar Python directamente
```batch
REM Omite el batch file y usa Python directamente
python convert_incidents.py "data/input/archivo con espacios.csv" -o data/output/
```

### Error: "Python no encontrado"

**Windows**:
```
Instala Python desde: https://www.python.org/downloads/
Asegúrate de marcar "Add Python to PATH" durante la instalación
```

**Linux/Mac**:
```bash
# Instalar Python 3
sudo apt-get install python3  # Ubuntu/Debian
brew install python3           # Mac
```

### Error: "Path no encontrado"

```bash
# Verifica que el archivo existe
dir data/input/          # Windows
ls data/input/          # Linux/Mac

# Usa ruta correcta
convert_incidents.bat data/input/datos.csv
```

### Error: "Invalid Estatus value"

Verifica que el CSV tenga valores válidos en Estatus:
- Abierto
- Pendiente
- En Progreso
- Resuelto
- Cerrado
- Cancelado

El script normaliza a Title Case automáticamente, pero debe ser uno de estos valores.

### Error: "Required field is empty"

Asegúrate que todos los campos requeridos tengan datos:
- ID de incidencia
- Descripción
- Estatus
- Fecha de envío
- Grupo asignado
- Urgencia
- Impacto

## 📈 Workflow Completo

```
1. Preparar archivos CSV
   └─ Colocar en directorio (ej: data/input/)

2. Ejecutar conversión
   └─ convert_incidents.bat data/input/ -o data/output/ -e data/errors/

3. Revisar resultados
   ├─ data/output/archivo.json (datos válidos)
   └─ data/errors/archivo_errors.json (registros con error)

4. Cargar en Dashboard
   ├─ Abrir Massive Incidents Dashboard
   ├─ Cargar JSON
   └─ Verificar datos

5. (Opcional) Revisar errores
   └─ convert_incidents.bat data/input/ --show-errors
```

## 📞 Soporte

Para más información técnica:
- Documentación completa: [CLAUDE.md](CLAUDE.md)
- Especificación: [specs/001-csv-to-json-workflow/spec.md](specs/001-csv-to-json-workflow/spec.md)
- Guía rápida: [specs/001-csv-to-json-workflow/quickstart.md](specs/001-csv-to-json-workflow/quickstart.md)

## ✨ Características del Script

| Característica | Detalles |
|---|---|
| **Encoding automático** | UTF-8, UTF-8-sig, Windows-1252, Latin-1, ISO-8859-15 |
| **Delimiter automático** | Coma, punto y coma, tabulación |
| **Normalización** | Urgencia, Estatus, Impacto (automática) |
| **Validación** | Campos requeridos, valores permitidos, formatos |
| **Error handling** | Skip de registros inválidos, reporte detallado |
| **Batch processing** | Procesa múltiples archivos en un comando |
| **Output legible** | Colores, estadísticas, tamaños formateados |

---

**Versión**: 1.0 | **Última actualización**: 2026-05-13
