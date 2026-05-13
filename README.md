# CSV to JSON Converter

Herramienta Python para convertir archivos CSV a formato JSON de manera simple y eficiente.

## Características

- ✅ Convierte archivos CSV individuales a JSON
- ✅ Convierte múltiples archivos CSV en un directorio
- ✅ **Auto-detección de delimitadores** (coma, punto y coma, tabulación)
- ✅ Soporta múltiples codificaciones (UTF-8, UTF-8-sig, Latin-1, etc.)
- ✅ Genera JSON con formato legible e indentación
- ✅ Preserva caracteres especiales y acentos

## Requisitos

- Python 3.6 o superior
- Sin dependencias externas (usa librerías estándar: `csv`, `json`, `pathlib`)

## Instalación

No requiere instalación especial. Solo necesitas tener Python instalado.

## Uso

### 1. Convertir un archivo CSV individual

```bash
python csv_to_json.py archivo.csv -o salida.json
```

**Ejemplo:**
```bash
python csv_to_json.py csv/2026R4MESAPOST.csv -o 2026R4MESAPOST.json
```

Si no especificas `-o`, la salida se imprime en consola:
```bash
python csv_to_json.py archivo.csv
```

### 2. Convertir todos los CSV en un directorio

```bash
python csv_to_json.py csv/
```

Genera un archivo JSON para cada CSV en el mismo directorio.

### 3. Especificar otra codificación

Si tu archivo no es UTF-8, especifica la codificación:

```bash
# Para archivos UTF-8 con BOM
python csv_to_json.py archivo.csv -o salida.json -e utf-8-sig

# Para archivos Latin-1/ISO-8859-1
python csv_to_json.py archivo.csv -o salida.json -e latin-1

# Para archivos Windows-1252
python csv_to_json.py archivo.csv -o salida.json -e cp1252
```

### 4. Especificar delimitador manualmente

Si quieres forzar un delimitador específico:

```bash
# Usar punto y coma como delimitador
python csv_to_json.py archivo.csv -o salida.json -d ';'

# Usar tabulación
python csv_to_json.py archivo.csv -o salida.json -d $'\t'

# Usar coma (por defecto)
python csv_to_json.py archivo.csv -o salida.json -d ','
```

## Opciones

| Opción | Forma larga | Descripción | Ejemplo |
|--------|------------|-------------|---------|
| `input` | — | Archivo CSV o directorio | `csv/datos.csv` |
| `-o` | `--output` | Archivo o directorio de salida | `-o output.json` |
| `-e` | `--encoding` | Codificación del CSV | `-e utf-8-sig` |
| `-d` | `--delimiter` | Delimitador del CSV | `-d ';'` |

## Ejemplos Prácticos

### Ejemplo 1: Convertir un CSV sencillo
```bash
python csv_to_json.py datos.csv -o datos.json
```

### Ejemplo 2: Convertir CSV con punto y coma (delimitador español)
```bash
python csv_to_json.py facturas.csv -o facturas.json -e utf-8-sig -d ';'
```

### Ejemplo 3: Procesar todos los CSV de una carpeta
```bash
python csv_to_json.py reports/
```

Genera:
- `reports/archivo1.json`
- `reports/archivo2.json`
- `reports/archivo3.json`

### Ejemplo 4: Auto-detección (recomendado)
```bash
# El script detecta automáticamente el delimitador
python csv_to_json.py datos.csv -o datos.json
```

## Formato de Salida

El script genera JSON con estructura clara y legible:

```json
[
  {
    "ID de incidencia": "INC000004002774",
    "Descripción": "[2026R4] - [PRJ-10523] No deja modificar el producto",
    "Estatus": "Cerrado",
    "Fecha de envío": "26/04/2026 8:40 a",
    "Grupo asignado": "SOP_CRMB2B"
  },
  {
    "ID de incidencia": "INC000004002775",
    "Descripción": "[2026R4] - MICROSERVICIOS - Error 500",
    "Estatus": "Cerrado",
    "Fecha de envío": "26/04/2026 8:43 a",
    "Grupo asignado": "SOP_TURING_OSP"
  }
]
```

## Codificaciones Soportadas

- **utf-8** - UTF-8 estándar
- **utf-8-sig** - UTF-8 con BOM (Microsoft)
- **latin-1** - ISO-8859-1 (Europa Occidental)
- **iso-8859-1** - Igual que latin-1
- **cp1252** - Windows-1252 (Windows)
- **iso-8859-15** - Latin-9 (Europa)

## Solución de Problemas

### Error: "No se encontró el archivo"
```
Error: No se encontró el archivo datos.csv
```
✓ Verifica que la ruta del archivo es correcta
✓ Usa rutas relativas desde el directorio actual

### Error de codificación
```
Error al procesar: 'charmap' codec can't encode character
```
✓ Especifica la codificación correcta con `-e`
✓ Intenta con `-e utf-8-sig` para archivos de Windows

### Datos mal parseados
```
Las columnas no se separan correctamente
```
✓ Especifica el delimitador con `-d`
✓ El script intenta auto-detectar, pero puedes forzarlo manualmente

## Notas

- **Campos vacíos**: Se preservan como cadenas vacías `""`
- **Caracteres especiales**: Se preservan correctamente en UTF-8
- **Acentos y ñ**: Soportados completamente
- **Saltos de línea**: Se preservan dentro de los campos
- **Comillas**: Se manejan correctamente según estándar CSV

## Contribuciones

Para mejoras o reportar problemas, contacta al equipo de desarrollo.

## Licencia

Este script es de uso interno del proyecto.
