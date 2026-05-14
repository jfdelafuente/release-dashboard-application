# CSV → JSON Conversión y Carga Automática

Documento que especifica la operativa completa para convertir archivos CSV a JSON y que la aplicación los cargue automáticamente.

---

## 🔄 Flujo Completo

```
Paso 1: Usuario coloca CSV
        ↓
    data/input/incidencias.csv
        ↓
Paso 2: Ejecutar conversor
        ↓
    python convert_incidents.py data/input/incidencias.csv
        ↓
Paso 3: Conversor procesa CSV
        │
        ├─ Detecta encoding (UTF-8, Windows-1252, etc)
        ├─ Detecta delimitador (coma, punto-coma, tab)
        ├─ Normaliza datos (Urgencia "4-Baja" → "Baja")
        ├─ Valida campos requeridos
        └─ Genera reportes de errores
        ↓
Paso 4: Output generado
        ├─ data/output/incidencias.json (datos convertidos)
        ├─ data/errors/incidencias_errors.json (errores)
        └─ data/output/index.json (índice actualizado)
        ↓
Paso 5: Dashboard Hub carga automáticamente
        ├─ Abre index.json
        ├─ Lee lista de archivos JSON
        ├─ Carga datos en memoria
        └─ Muestra KPIs en tiempo real
```

---

## 📁 Estructura de Directorios

```
data/
├── input/                    # CSVs ORIGINALES (usuario pone aquí)
│   ├── incidencias.csv      # Incidencias masivas
│   ├── postmortem.csv       # Datos postmortem
│   └── ...otros archivos
│
├── output/                   # JSONs GENERADOS (automático)
│   ├── incidencias.json     # JSON convertido
│   ├── postmortem.json      # JSON convertido
│   ├── index.json           # ÍNDICE (actualizado por conversor)
│   └── ...otros JSONs
│
├── errors/                   # REPORTES DE ERRORES
│   ├── incidencias_errors.json  # Errores de conversión
│   ├── postmortem_errors.json   # Errores de conversión
│   └── ...
│
└── archive/                  # HISTÓRICO (opcional)
    └── YYYY/MM/...         # Organizados por fecha
```

**Importante**: Todos estos directorios están en `.gitignore` (datos sensibles protegidos).

---

## 🔧 Paso 1: Colocar CSVs de Entrada

### Ubicación
```
data/input/
```

### Formato esperado

**Para Incidencias Masivas**:
```csv
ID de incidencia,Descripción,Estatus,Fecha de envío,Grupo asignado,Urgencia,Impacto,Fecha de última resolución
INC000004002774,Descripción,Cerrado,26/04/2026 8:40 a,SOP_CRMB2B,4-Alta,Masiva,26/04/2026 10:00 p
```

**Campos requeridos**:
- `ID de incidencia` - Identificador único
- `Descripción` - Texto del incidente
- `Estatus` - Estado (Abierto, Cerrado, etc)
- `Fecha de envío` - Cuándo se reportó (formato: dd/mm/yyyy HH:mm a/p)
- `Grupo asignado` - Equipo responsable
- `Urgencia` - Nivel (4-Alta, 3-Media, etc → normalizado a Alta, Media)
- `Impacto` - Nivel de impacto
- `Fecha de última resolución` - Cuándo se cerró

**Para Postmortems**:
```csv
ID,Descripción,Estatus,Fecha,Urgencia,Impacto,Tipo Despliegue,Centro
POST001,Postmortem de incidente,Cerrado,15/04/2026,Alta,Crítica,PAP,MADRID
```

### Convenciones de nombres (recomendado)

```
Formato: <tipo>-<identificador>-<fecha>.csv

Ejemplos:
data/input/cs-masiva-202605.csv           (incidencias masivas mayo 2026)
data/input/2026r4-postmortem.csv          (postmortems de release 2026 R4)
data/input/cs-informe-diario.csv          (informe automático)
```

---

## ⚙️ Paso 2: Ejecutar Conversores

### Conversor de Incidencias Masivas

```bash
# Convertir archivo específico
python src/converters/convert_incidents.py data/input/incidencias.csv

# Convertir y especificar salida
python src/converters/convert_incidents.py data/input/incidencias.csv \
    -o data/output/incidents.json

# Convertir con reporte de errores detallado
python src/converters/convert_incidents.py data/input/incidencias.csv \
    -e data/errors/incidents_errors.json \
    --show-errors

# Convertir todos los CSVs en un directorio
python src/converters/convert_incidents.py data/input/
```

### Conversor de Postmortems

```bash
# Mismo uso que incidencias
python src/converters/convert_postmortems.py data/input/postmortem.csv

# Con opciones completas
python src/converters/convert_postmortems.py data/input/postmortem.csv \
    -o data/output/postmortems.json \
    -e data/errors/postmortem_errors.json
```

### Scripts Batch/Shell (Windows, Linux, Mac)

**Windows**:
```batch
# Convertir incidencias
convert_incidents.bat data/input/incidencias.csv

# Convertir postmortems
convert_postmortems.bat data/input/postmortem.csv
```

**Linux/Mac**:
```bash
# Convertir incidencias
./convert_incidents.sh data/input/incidencias.csv

# Convertir postmortems
./convert_postmortems.sh data/input/postmortem.csv
```

---

## 📊 Paso 3: ¿Qué hace el Conversor?

### Auto-Detección

```python
# 1. ENCODING (detecta automáticamente)
   UTF-8                  ✅
   UTF-8-sig (BOM)        ✅
   Windows-1252 (Latin)   ✅
   ISO-8859-15 (Western)  ✅

# 2. DELIMITADOR (detecta automáticamente)
   Coma (,)               ✅
   Punto-coma (;)         ✅
   Tabulación (\t)        ✅
```

### Normalización

| Campo | Antes | Después |
|-------|-------|---------|
| Urgencia | "4-Alta" | "Alta" |
| Urgencia | "1-Baja" | "Baja" |
| Estatus | "cerrado" | "Cerrado" |
| Impacto | "masiva" | "Masiva" |
| Descripción | "  texto  " | "texto" |

### Validación

```
Campos requeridos:
  ✅ ID de incidencia (no vacío, único)
  ✅ Fecha de envío (formato dd/mm/yyyy HH:mm a/p)
  ✅ Estatus (válido según enum)
  ✅ Urgencia (valores permitidos)

Si falla validación:
  → Se registra en .errors.json
  → Registro NO se incluye en output JSON
  → Conversión continúa (no se detiene)
```

### Output del Conversor

**Archivo JSON generado** (`data/output/incidencias.json`):
```json
[
  {
    "ID de incidencia": "INC000004002774",
    "Descripción": "[2026R4] - Descripción del problema",
    "Estatus": "Cerrado",
    "Fecha de envío": "26/04/2026 8:40 a",
    "Grupo asignado": "SOP_CRMB2B",
    "Urgencia": "Alta",           ← NORMALIZADO
    "Impacto": "Masiva",          ← NORMALIZADO
    "Fecha de última resolución": "26/04/2026 10:00 p"
  }
]
```

**Reporte de errores** (`data/errors/incidencias_errors.json`):
```json
{
  "summary": {
    "total_records": 1000,
    "successful": 985,
    "failed": 15,
    "success_rate": 98.5
  },
  "errors": [
    {
      "row": 42,
      "fields": {
        "Urgencia": {
          "original": "5-Desconocida",
          "error": "Invalid value: must be one of [Bajo, Medio, Alto, Crítica]"
        }
      }
    }
  ]
}
```

**Índice actualizado** (`data/output/index.json`):
```json
{
  "massive": {
    "lastUpdated": "2026-05-14T14:30:00Z",
    "files": [
      {
        "name": "incidencias.json",
        "path": "data/output/incidencias.json",
        "records": 985,
        "errors": 15
      }
    ]
  },
  "postmortem": {
    "lastUpdated": "2026-05-14T14:25:00Z",
    "files": [
      {
        "name": "postmortem.json",
        "path": "data/output/postmortem.json",
        "records": 42,
        "errors": 0
      }
    ]
  }
}
```

---

## 📖 Paso 4: Carga Automática en Dashboard Hub

### ¿Cómo carga el Dashboard?

```javascript
// 1. Al abrir dashboard-hub.html
window.addEventListener('load', initHub);

// 2. initHub() llama a loadLatestJSON()
async function loadLatestJSON() {
    // 3. Busca data/output/index.json
    const indexResponse = await fetch('data/output/index.json');
    const indexData = await indexResponse.json();

    // 4. Lee lista de archivos disponibles
    const files = [
        ...indexData.massive.files,      // Incidencias
        ...indexData.postmortem.files    // Postmortems
    ];

    // 5. Carga cada JSON
    for (const file of files) {
        const response = await fetch(file.path);
        const incidents = await response.json();
        // 6. Procesa y muestra datos
    }
}

// 7. Extrae KPIs del dashboard-hub
const kpis = extractKPIs(incidents, massiveMetadata, postmortemMetadata);

// 8. Renderiza KPIs en tiempo real
renderHub(kpis);
```

### Requisitos para Auto-Carga

✅ **Obligatorio**:
- `data/output/index.json` debe existir
- `data/output/*.json` deben existir y ser válidos
- JSONs deben tener estructura correcta

❌ **NO funciona si**:
- No existe `index.json`
- JSONs son archivos vacíos
- Rutas en `index.json` son incorrectas
- Dashboard se abre sin servidor HTTP (CORS)

### Error: "No hay datos disponibles"

**Significa**: `index.json` no existe o está vacío

**Solución**:
1. Verifica que ejecutaste el conversor
2. Verifica que `data/output/` existe
3. Verifica que `data/output/index.json` existe
4. Abre dashboard con servidor HTTP:
   ```bash
   python -m http.server 8000
   # Luego: http://localhost:8000/src/dashboards/dashboard-hub.html
   ```

---

## 🚀 Operativa en Staging / Producción

### En Staging (VPS)

```bash
# 1. SSH al servidor staging
ssh -i deploy_key app@staging.example.com

# 2. Coloca CSV en data/input/
scp -P 22 local-file.csv app@staging.example.com:/var/www/release-dashboard-staging/data/input/

# 3. Ejecuta conversor manualmente (o cron job)
cd /var/www/release-dashboard-staging
python3 src/converters/convert_incidents.py data/input/local-file.csv

# 4. Verifica que data/output/index.json fue generado
ls -la data/output/

# 5. Abre Dashboard Hub en navegador
https://staging.example.com/src/dashboards/dashboard-hub.html
```

### En Producción (VPS)

```bash
# 1. SSH al servidor producción
ssh -i deploy_key app@prod.example.com

# 2. Coloca CSV en data/input/
scp -P 22 local-file.csv app@prod.example.com:/var/www/release-dashboard/data/input/

# 3. Ejecuta conversor
cd /var/www/release-dashboard
python3 src/converters/convert_incidents.py data/input/local-file.csv

# 4. Verifica data/output/
ls -la data/output/

# 5. Accede a Dashboard Hub
https://example.com/src/dashboards/dashboard-hub.html
```

---

## ⚡ Automatización con CI/CD

### Opción 1: Conversor en GitHub Actions (Pipeline de Deploy)

Cuando haces `git push main`, el CI/CD:

```yaml
# .github/workflows/deploy.yml

steps:
  - name: Deploy to Staging VPS
    # ... código de deploy ...

  - name: Convert CSV to JSON (Staging)
    run: |
      ssh app@staging.example.com << 'EOF'
      cd /var/www/release-dashboard-staging
      python3 src/converters/convert_incidents.py data/input/*.csv
      python3 src/converters/convert_postmortems.py data/input/*.csv
      EOF
```

### Opción 2: Cron Job en VPS (Conversión Automática)

Ejecuta conversores cada hora:

```bash
# En el VPS, edita crontab como usuario 'app'
crontab -e

# Añade (ejecuta cada hora)
0 * * * * cd /var/www/release-dashboard && \
  python3 src/converters/convert_incidents.py data/input/*.csv && \
  python3 src/converters/convert_postmortems.py data/input/*.csv
```

### Opción 3: Watch Script (Monitoreo en Tiempo Real)

Monitorea `data/input/` y convierte automáticamente:

```bash
#!/bin/bash
# watch-and-convert.sh

while true; do
    # Busca archivos CSV nuevos (modificados hace menos de 1 minuto)
    find /var/www/release-dashboard/data/input -name "*.csv" -mmin -1 | while read file; do
        echo "Detectado CSV nuevo: $file"
        python3 /var/www/release-dashboard/src/converters/convert_incidents.py "$file"
    done

    sleep 60  # Revisar cada minuto
done
```

Ejecutar como servicio:
```bash
# /etc/systemd/system/csv-monitor.service
[Unit]
Description=CSV to JSON Monitor
After=network.target

[Service]
Type=simple
User=app
WorkingDirectory=/var/www/release-dashboard
ExecStart=/var/www/release-dashboard/scripts/watch-and-convert.sh
Restart=always

[Install]
WantedBy=multi-user.target

# Habilitar
sudo systemctl enable csv-monitor
sudo systemctl start csv-monitor
```

---

## 🔍 Verificación y Troubleshooting

### Verificar que todo funciona

```bash
# 1. Verificar estructura de directorios
ls -la data/input/
ls -la data/output/
ls -la data/errors/

# 2. Verificar que index.json existe
cat data/output/index.json | jq '.'

# 3. Verificar que JSONs son válidos
cat data/output/incidencias.json | jq '.' | head -20

# 4. Contar registros convertidos
jq 'length' data/output/incidencias.json

# 5. Contar errores
jq '.summary.failed' data/errors/incidencias_errors.json
```

### Problema: CSV no se convierte

**Error: "FileNotFoundError: No such file or directory"**
```bash
# Solución: Verifica que el CSV existe
ls -la data/input/incidencias.csv

# Si no existe, cópialo
cp /path/to/your/file.csv data/input/incidencias.csv
```

**Error: "UnicodeDecodeError: 'utf-8' codec can't decode"**
```bash
# Problema: Encoding incorrecto
# Solución: El conversor intenta automáticamente otros encodings
# Si sigue fallando, convierte el archivo:

# En Windows
iconv -f WINDOWS-1252 -t UTF-8 input.csv > output.csv

# En Linux/Mac
iconv -f CP1252 -t UTF-8 input.csv > output.csv
```

**Error: "Invalid value for field 'Urgencia'"**
```bash
# Problema: Urgencia tiene valores no permitidos
# Solución: Revisa data/errors/incidencias_errors.json
# para ver qué valores están mal

jq '.errors[] | select(.fields.Urgencia)' data/errors/incidencias_errors.json
```

### Problema: Dashboard no carga datos

**Error en navegador: "No hay datos disponibles"**

```bash
# 1. Verifica que index.json existe
curl http://localhost:8000/data/output/index.json

# 2. Verifica contenido de index.json
cat data/output/index.json | jq '.'

# 3. Verifica que JSONs existen
curl http://localhost:8000/data/output/incidencias.json | jq 'length'

# 4. Verifica que servidor HTTP está activo
# Si abres archivo localmente (file://), no cargará por CORS
python -m http.server 8000
# Luego: http://localhost:8000/src/dashboards/dashboard-hub.html
```

---

## 📋 Checklist: Configuración Inicial

- [ ] Directorio `data/input/` creado
- [ ] Directorio `data/output/` creado
- [ ] Directorio `data/errors/` creado
- [ ] CSV colocado en `data/input/`
- [ ] Conversor ejecutado
- [ ] `data/output/index.json` generado
- [ ] `data/output/*.json` contiene datos
- [ ] Dashboard Hub accedido vía servidor HTTP
- [ ] KPIs visibles en tiempo real
- [ ] Errores revisados en `data/errors/`

---

## 📝 Archivos Relacionados

| Archivo | Propósito |
|---------|-----------|
| `src/converters/convert_incidents.py` | Conversor de incidencias masivas |
| `src/converters/convert_postmortems.py` | Conversor de postmortems |
| `src/converters/csv_to_json/` | Módulo de conversión (encoding, delimitador, validación) |
| `src/converters/build_index.py` | Generador de index.json |
| `src/dashboards/dashboard-hub.html` | Dashboard principal (carga automática) |
| `src/dashboards/assets/js/dashboard-hub.js` | JavaScript para carga de datos |
| `.github/workflows/deploy.yml` | CI/CD automation (include conversores) |

---

## 🎯 Resumen de Operativa

```
1. Usuario coloca CSV en data/input/
   ↓
2. Ejecuta conversor (manual, cron, o CI/CD)
   ↓
3. Conversor genera JSON + index.json en data/output/
   ↓
4. Dashboard Hub abre index.json automáticamente
   ↓
5. KPIs se renderizan en tiempo real
   ↓
6. Usuario visualiza datos en navegador
```

**Totalmente automático una vez que el JSON está en `data/output/`**.

---

**Fecha de Actualización**: 2026-05-14
**Versión**: 1.0
