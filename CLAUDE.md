# Release Dashboard Application - Documentación

## Descripción General

Aplicación con dos dashboards interactivos para análisis de incidencias:
- **Postmortem Dashboard**: Análisis de post-mortem con desglose por despliegues y segmentos
- **Massive Incidents Dashboard**: Análisis de incidencias masivas con temporal charts y tendencias

## Archivos Principales

### Herramientas
- **csv_to_json.py**: Convierte archivos CSV a JSON con auto-detección de delimitadores
- **README.md**: Documentación del conversor CSV a JSON

### Dashboards HTML
- **postmortem-dashboard.html**: Dashboard de post-mortem de incidencias
- **massive-incidents-dashboard.html**: Dashboard de incidencias masivas (PRINCIPAL)

### Configuración
- **.gitignore**: Archivos y carpetas a ignorar en git
- **CLAUDE.md**: Este archivo (documentación para Claude)

## Dashboard: Massive Incidents Dashboard

### Ubicación
`c:\Users\jose.delafuente\proyectos\release-dashboard-application\massive-incidents-dashboard.html`

### Características Principales

#### 1. **Carga de Datos**
- Interfaz drag-and-drop para cargar archivos JSON
- Auto-detección de formato y encoding
- Validación de estructura JSON

#### 2. **Filtro de Tiempo Global** ⭐
Períodos predefinidos que afectan TODOS los componentes:
- Todo (todos los datos)
- Últimos 7 días
- Últimos 15 días
- Últimos 30 días
- Últimos 90 días
- Últimos 6 meses
- Último año
- **Año en curso** (del 1/1/2026 hasta hoy)

**Campo de filtro**: "Fecha de envío"

#### 3. **KPI Cards**
| KPI | Descripción | Campo |
|-----|-------------|-------|
| Total Incidencias | Todas las incidencias del período | Count |
| Incidencias Pdtes | Incidencias pendientes (no Cerrado/Resuelto/Cancelado) | Count |
| Tendencia 7 días | % cambio backlog vs 7 días atrás | % con color |
| Tendencia 15 días | % cambio backlog vs 15 días atrás | % con color |
| Tendencia 30 días | % cambio backlog vs 30 días atrás | % con color |

**Colores de tendencia**:
- 🟢 Verde: Reducción (< -2%)
- 🔴 Rojo: Aumento (> +2%)
- ⚫ Gris: Estable (-2% a +2%)

#### 4. **Gráficas Temporales**
**A. Evolución Diaria de Incidencias Operativas**
- Eje X: Fechas cronológicas
- Eje Y (izquierda): Entradas y Solucionadas (barras apiladas, naranja)
- Eje Y (derecha): Backlog Acumulado (línea, naranja oscuro)

**B. Incidencias Abiertas por Día y Backlog**
- Eje X: Fechas cronológicas
- Eje Y (izquierda): Conteo de incidencias apiladas por Status (colores)
- Eje Y (derecha): Backlog (línea)

#### 5. **Filtros de Tabla** (aplican DESPUÉS del filtro de tiempo)
- **Estado**: Filtra por Estatus
- **Sistema**: Filtra por Grupo asignado
- **Urgencia**: Filtra por Urgencia

#### 6. **Tabla de Incidencias**
Columnas (todas ordenables con click):
- **Código**: Link a Remedy (https://soptmc.si.orange.es/MonTMC/epsilon/remedyC/{ID})
- **Descripción**: Texto del incidente
- **Estado**: Badge con color según status
- **Urgencia**: Nivel de urgencia
- **Grupo Asignado**: Equipo responsable
- **Impacto**: Nivel de impacto
- **Fecha Envío**: Fecha/hora de reporte (**ordenación cronológica correcta**)

**Ordenación especial por fecha**: Usa parseDate() para comparar cronológicamente

#### 7. **Tabla de Debug** (colapsible)
Muestra cálculos diarios para verificación:
- Fecha
- Entradas (incidencias abiertas ese día)
- Solucionadas (incidencias cerradas ese día)
- Neto (Entradas - Solucionadas)
- Backlog (count de incidencias abiertas)

### Estructura de Datos JSON Esperada

```json
[
  {
    "ID de incidencia": "INC000004002774",
    "Descripción": "[2026R4] - Descripción del problema",
    "Estatus": "Cerrado",
    "Fecha de envío": "26/04/2026 8:40 a",
    "Grupo asignado": "SOP_CRMB2B",
    "Urgencia": "Alta",
    "Impacto": "Medio",
    "Fecha de última resolución": "26/04/2026 10:00 p"
  }
]
```

### Campos Críticos para Cada Característica

| Característica | Campo Requerido | Formato |
|----------------|-----------------|---------|
| Filtro de Tiempo | "Fecha de envío" | "dd/mm/yyyy HH:mm a" |
| KPI Pendientes | "Estatus" | String (case-insensitive) |
| Temporal Charts | "Fecha de envío", "Estatus" | dd/mm/yyyy HH:mm |
| Backlog Trend | globalBacklogData (generado) | Calculated |
| Tabla | Todos menos "Fecha de última resolución" | String/Date |

### Funciones Clave

#### Filtrado de Tiempo
```javascript
applyTimeFilter(incidents, startDate, endDate)
// Filtra por "Fecha de envío" en rango [startDate, endDate]
// Excluye incidencias sin fecha cuando hay filtro activo
```

#### Cálculo de Fecha de Inicio
```javascript
calculateStartDate(period)
// 'all' → null
// '7' → today - 7 days
// 'currentyear' → January 1 of current year
// '365' → today - 365 days
```

#### Parsing de Fechas
```javascript
parseDate(dateStr)
// Input: "17/03/2025 18:44 a"
// Output: Date object normalized to midnight
```

#### Ordenación de Tabla
```javascript
filterTable() // Sort logic
// Detecta columnas de fecha ("Fecha de envío", "Fecha de última resolución")
// Convierte a Date objects antes de comparar
// Usa getTime() para comparación cronológica correcta
```

### Flujo de Datos

```
JSON cargado
    ↓
[allIncidents] (todos)
    ↓
[globalTimeFilter] aplicado (startDate, endDate)
    ↓
[timeFilteredIncidents] (período seleccionado)
    ↓
    ├─→ KPIs (Total, Pendientes, Tendencias)
    ├─→ createTemporalChart() → [globalBacklogData], [globalAllDates]
    ├─→ createOpenIncidentsTemporalChart()
    ├─→ populateFilterSelects() (Status, Sistema, Urgencia)
    └─→ filterTable(timeFilteredIncidents)
            ↓
        [filteredIncidents] (tabla filtrada)
            ↓
        populateTable() (render con colores)
```

### Variables Globales Importantes

```javascript
let allIncidents = [];              // Todos los datos cargados
let filteredIncidents = [];         // Datos después de filtros de tabla
let globalBacklogData = {};         // { "2026-05-12": 5, ... }
let globalAllDates = [];            // Array de Date objects
let globalTimeFilter = {            // Estado del filtro de tiempo
    period: 'all',
    startDate: null,
    endDate: new Date()
};
let sortColumn = 'Fecha Apertura';  // Columna de ordenamiento actual
let sortDirection = 'asc';          // Dirección: 'asc' o 'desc'
```

### Notas de Implementación

#### BOM Handling
Función `getIncidentValue()` maneja automáticamente caracteres BOM (\uFEFF) en nombres de campos.

#### Exclusiones de Estado
Incidencias con estos estados se excluyen de tabla y KPIs:
- "Cerrado"
- "Resuelto"
- "Cancelado"

#### Normalización de Fechas
- Todas las fechas normalizadas a medianoche (00:00:00) para comparación consistente
- Timezone: Local (sin conversión)

#### Edge Cases Manejados
1. **Período sin datos**: KPIs = 0, gráficas vacías
2. **Incidencias sin fecha**: Excluidas con filtro activo
3. **Backlog con datos insuficientes**: Muestra "-" en KPIs
4. **Rango de fecha futura**: Solo muestra hoy como máximo

## Conversor CSV a JSON (csv_to_json)

### Módulo Principal

El módulo `csv_to_json` convierte archivos CSV de incidencias a formato JSON compatible con el Massive Incidents Dashboard.

**Características:**
- ✅ Auto-detección de encoding (UTF-8, UTF-8-sig, Windows-1252, Latin-1, ISO-8859-15)
- ✅ Auto-detección de delimitadores (coma, punto-y-coma, tabulación)
- ✅ **Normalización de campos**: Urgencia "4-Baja" → "Baja", Estatus → title case
- ✅ Validación de campos requeridos y valores permitidos
- ✅ Reporte de errores detallado (sin detener procesamiento)
- ✅ Preservación de todos los campos en salida JSON

### Estructura del Módulo

```
csv_to_json/
├── __init__.py           # Exporta CsvToJsonConverter
├── encoding.py           # Detección de encoding
├── delimiter.py          # Detección de delimitador
├── normalizers.py        # Normalización de campos
├── validators.py         # Validación de datos
├── schemas.py            # Definición de campos y reglas
└── converter.py          # Orquestador principal
```

### Uso Programático

```python
from csv_to_json import CsvToJsonConverter

converter = CsvToJsonConverter()
success, report = converter.convert_file(
    input_path='data/input/datos.csv',
    output_path='data/output/datos.json',
    error_report_path='data/errors/errors.json'
)

# Resultado
print(f"Exitoso: {report['stats']['successful']}")
print(f"Errores: {report['stats']['failed']}")
print(f"Encoding detectado: {report['encoding_detected']}")
```

### Flujo de Conversión

1. **Detección de Encoding**: Lee primero 4KB, busca BOM, intenta encodings comunes
2. **Detección de Delimitador**: Usa csv.Sniffer con fallback a conteo manual
3. **Parsing CSV**: Lee con csv.DictReader usando delimitador detectado
4. **Normalización**: Aplica transformaciones campo por campo
   - **Urgencia**: "4-Baja" → "Baja" (extrae texto después del guión)
   - **Estatus**: "cerrado" → "Cerrado" (title case)
   - **Impacto**: "masiva" → "Masiva" (title case)
   - **Descripción**: Trim whitespace
   - **Fechas**: Valida formato dd/mm/yyyy HH:mm a/p
5. **Validación**: Verifica campos requeridos, valores permitidos
6. **Escritura**: Salida JSON con registros válidos + reporte de errores

### Salida del Conversor

**Archivo JSON (valid records):**
```json
[
  {
    "ID de incidencia": "INC000003884945",
    "Descripción": "LIVEPERSON // DERIO // ERROR FUNCIONAL",
    "Estatus": "Cerrado",
    "Fecha de envío": "02/01/2026 8:14 AM",
    "Grupo asignado": "CEP CAU AGI",
    "Urgencia": "Baja",         ← NORMALIZADO (sin prefijo numérico)
    "Impacto": "Masiva",        ← NORMALIZADO (title case)
    "Fecha de última resolución": "12/01/2026 8:24 AM"
  }
]
```

**Reporte de Errores (invalid records):**
```json
{
  "summary": {
    "total_records": 100,
    "successful": 95,
    "failed": 5,
    "success_rate": 95.0
  },
  "errors": [
    {
      "row": 23,
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

### Uso Anterior (Deprecated)

El script `csv_to_json.py` anterior era un conversor simple sin validación ni normalización. El nuevo módulo reemplaza esta funcionalidad con:
- Formato de salida compatible (idéntico al esperado por el dashboard)
- Validación automática de datos
- Normalización de campos (especialmente Urgencia)
- Reporte de errores para depuración

## Características en Desarrollo

<!-- SPECKIT START: Active feature implementation plans -->

### Feature: Postmortem CSV to JSON Converter (004-postmortem-converter)

**Status**: Planning Phase Complete (Spec ✅ | Research ✅ | Data Model ✅ | Quickstart ✅)

**Plan Reference**: [specs/004-postmortem-converter/plan.md](specs/004-postmortem-converter/plan.md)

**Objective**: Create validation and normalization script to convert postmortem CSV data to JSON format compatible with Postmortem Dashboard and Dashboard Hub auto-load system.

**Key Features**:
- Auto-detect CSV encoding (UTF-8, UTF-8-sig, Windows-1252, Latin-1, ISO-8859-15)
- Auto-detect delimiter (comma, semicolon, tab)
- Normalize 13 postmortem fields (Spanish names preserved)
- **Derive Despliegue field**: oldest date = PAP, others = MESA
- Pre-calculate KPIs: total, by_status, by_urgency, by_impact
- Generate error report for invalid records
- Output JSON with `-postmortem` suffix for Dashboard Hub discovery
- <5 second conversion for 1000+ record files

**Related Documentation**:
- Specification: [specs/004-postmortem-converter/spec.md](specs/004-postmortem-converter/spec.md)
- Research decisions: [specs/004-postmortem-converter/research.md](specs/004-postmortem-converter/research.md)
- Data model: [specs/004-postmortem-converter/data-model.md](specs/004-postmortem-converter/data-model.md)
- Testing guide: [specs/004-postmortem-converter/quickstart.md](specs/004-postmortem-converter/quickstart.md)

## Plan Reference

**Current Implementation Plan**: [specs/005-project-organization/plan.md](specs/005-project-organization/plan.md)

The plan defines the organizational and architectural foundation for the project, including:
- Technical context (languages, frameworks, testing strategy)
- Constitutional compliance gates
- Project structure and file organization
- Phase 0: Research (completed) with key technical decisions
- Phase 1: Design & Contracts (completed) with data model and deployment contracts
- Phase 2: Implementation tasks (to be generated via `/speckit-tasks`)

**Next Step**: Run `/speckit-tasks` to generate granular task breakdown and implementation checklist

<!-- SPECKIT END -->

## 📁 Estructura de Directorios de Datos

El proyecto utiliza una estructura clara y organizada para datos de entrada y salida:

```
data/
├── input/      # Archivos CSV de incidencias masivas y postmortem
├── output/     # Archivos JSON generados por los conversores
├── errors/     # Reportes de errores de conversión
└── archive/    # Archivos históricos (opcionales)
```

**Directorios protegidos por .gitignore**: Todos los directorios `data/` están protegidos para evitar commit accidental de datos sensibles de incidencias.

**Convenciones de nombres**:
- **Input (CSV)**: `cs-masiva-202605.csv`, `2026r4-postmortem.csv`, `cs-informe-diario.csv`
- **Output (JSON)**: Mismo nombre base que el CSV, extensión `.json`
- **Errores**: `{nombre-base}_errors.json`
- **Sufijos automáticos**: `-massive` para masivas, `-postmortem` para postmortems

**Ejemplos**:
```
data/input/CS_Masiva_20260514.csv
  ↓ (conversión)
data/output/CS_Masiva_20260514-massive.json
data/errors/CS_Masiva_20260514_errors.json
```

## Idioma de Comunicación

- 🇪🇸 **Todas las conversaciones deben ser en español**. Esta es la lengua preferida para toda la comunicación con Claude.

## Preferencias de Colaboración

- ✅ Implementar features completas sin dividir en PRs pequeños
- ✅ Verificar lógica de cálculos con tabla de debug
- ✅ Mantener orden cronológico en todas las gráficas
- ✅ Usar colores naranja para tema visual consistente
- ✅ Manejar BOM y diferentes encodings automáticamente
- ✅ Aplicar filtros globales ANTES que filtros específicos

## Referencias Útiles

- Campo de filtro de tiempo: "Fecha de envío"
- URL Remedy: https://soptmc.si.orange.es/MonTMC/epsilon/remedyC/{ID}
- Colores naranja: #f97316 (entradas), #fb923c (solucionadas), #c2410c (backlog)
- Formato fecha: dd/mm/yyyy HH:mm a (parseDate() lo convierte a Date)
