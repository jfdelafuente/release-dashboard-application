# Guía de Migración de Conversores CSV a JSON

Guía técnica sobre la evolución del formato de datos generado por los conversores CSV→JSON en **Release Dashboard Application**, el nuevo esquema con metadatos enriquecidos, las reglas de normalización y las pautas de compatibilidad para los dashboards frontend.

---

## 📌 Contexto de la Evolución

El módulo de conversión de datos ([`converters/`](../converters/)) evolucionó desde scripts sencillos de transformación hacia un motor robusto con validación exhaustiva de esquemas, detección automática de codificación (`UTF-8`, `Windows-1252`, `Latin-1`), normalización de campos y precalculado de KPIs.

### Comparativa de Versiones

| Característica | Versión Antigua (Legacy) | Versión Actual Optimizada |
|---|---|---|
| **Estructura JSON** | Array plano simple `[ { ... } ]` | Objeto envolvente con `_metadata` y array `data` |
| **Normalización** | Ninguna (valores crudos del CSV) | Normalización semántica de `Urgencia`, `Estatus`, `Impacto` y derivación de `Despliegue` |
| **Cálculo de KPIs** | Calculado en tiempo de ejecución por el navegador | Precalculado en Python (`_metadata.kpis`) optimizando la carga del frontend |
| **Detección de formato** | Delimitador y encoding manuales | Detección automática transparente de encoding (`BOM`, `UTF-8`, `cp1252`) y delimitador (`,`, `;`, `\t`) |
| **Gestión de Errores** | Excepciones no controladas o descarte silencioso | Informe detallado fila por fila en el directorio desacoplado `errors/` |
| **Suite de Pruebas** | Tests unitarios básicos | **> 516 tests** (unitarios, integración y e2e) con cobertura $\ge$ 80% vigilada por CI |

---

## 📄 Cambios en el Formato de Salida

### 1. Inclusión del Envoltorio de Metadatos (`_metadata`)

#### Formato Antiguo (Array Plano)
```json
[
  {
    "ID de incidencia": "INC000003884945",
    "Descripción": "Error de autenticación portal",
    "Estatus": "Cerrado",
    "Urgencia": "4-Baja"
  }
]
```

#### Formato Actual (Envoltorio Estructurado)
```json
{
  "_metadata": {
    "type": "massive",
    "version": "1.0",
    "created": "2026-10-20T10:30:00.000000",
    "record_count": 95,
    "kpis": {
      "total": 100,
      "pending": 23,
      "trend_7d": 5.2,
      "trend_15d": -3.1,
      "trend_30d": 12.8
    }
  },
  "data": [
    {
      "ID de incidencia": "INC000003884945",
      "Descripción": "Error de autenticación portal",
      "Estatus": "Cerrado",
      "Urgencia": "Baja"
    }
  ]
}
```

### 2. Contenido del Objeto `_metadata`

- **`type`**: Tipo de datos procesados (`"massive"` para incidencias masivas o `"postmortem"` para postmortems de releases).
- **`version`**: Versión del esquema del conversor (actualmente `"1.0"`).
- **`created`**: Marca de tiempo ISO 8601 del momento exacto de la conversión.
- **`record_count`**: Número total de registros válidos incluidos en el array `data`.
- **`kpis`**: Métricas e indicadores clave precalculados:
  - *Incidencias Masivas*: `total`, `pending`, y tendencias porcentuales `trend_7d`, `trend_15d`, `trend_30d`.
  - *Postmortems*: Bloque `kpis.dashboard_hub` con porcentajes de cierre (`cerradas_percent`), resolución en PaP (`pap_resueltas_percent`) y resolución en Mesa (`mesa_resueltas_percent`).

---

## 🔄 Reglas de Normalización de Campos

Los conversores limpian y estandarizan automáticamente los valores antes de volcarlos al JSON:

1. **Campo `Urgencia`**:
   - Se elimina el prefijo numérico del origen de datos Remedy y se aplica formato título:
     - `"4-Baja"` $\rightarrow$ **`"Baja"`**
     - `"3-Medio"` $\rightarrow$ **`"Medio"`**
     - `"2-Alta"` $\rightarrow$ **`"Alta"`**
     - `"1-Crítica"` $\rightarrow$ **`"Crítica"`**
2. **Campo `Estatus`**:
   - Homogeneización tipográfica: `"cerrado"`, `"CERRADO"` $\rightarrow$ **`"Cerrado"`** (aplica a *"Resuelto"*, *"Cancelado"*, *"Asignado"*, etc.).
3. **Campo `Impacto`**:
   - Corrección de mayúsculas: `"masiva"` $\rightarrow$ **`"Masiva"`**.
4. **Espacios en blanco**:
   - Aplicación de `strip()` en todos los campos textuales para eliminar espacios iniciales o finales invisibles.
5. **Derivación determinista del campo `Despliegue` (Postmortems)**:
   - Se añade automáticamente a cada registro de postmortem analizando las fechas:
     - **`"PAP"`**: Para la fecha más antigua de inicio del despliegue (Puesta a Producción).
     - **`"MESA"`**: Para las fechas subsiguientes (seguimiento en Mesa).

---

## 💻 Pautas de Adaptación en el Frontend (JavaScript)

Para asegurar compatibilidad con archivos históricos y archivos generados con el nuevo esquema, se debe emplear el siguiente patrón de extracción:

### Paso 1: Extracción Segura de Registros (Patrón Fallback)

```javascript
// Carga del JSON y extracción transparente
const result = JSON.parse(jsonText);

// Si tiene envoltorio _metadata, se usa result.data; si es un array clásico, se usa directamente
const incidents = result.data || result;

// Iteración ordinaria sobre los registros
incidents.forEach(incident => {
  console.log(incident['ID de incidencia'], incident.Estatus);
});
```

### Paso 2: Consumo de KPIs Precalculados

En lugar de recalcular manualmente los totales en el navegador, aprovecha los valores precalculados:

```javascript
// Obtener metadatos si están presentes
const metadata = result._metadata;

if (metadata && metadata.kpis) {
  // KPIs directos precalculados desde backend
  const total = metadata.kpis.total;
  const pendientes = metadata.kpis.pending;
  const tendenciaSemanal = metadata.kpis.trend_7d;
  
  actualizarTarjetasKPI(total, pendientes, tendenciaSemanal);
} else {
  // Fallback para archivos legacy sin metadatos
  const total = incidents.length;
  const pendientes = incidents.filter(i => !['Cerrado', 'Resuelto', 'Cancelado'].includes(i.Estatus)).length;
  actualizarTarjetasKPI(total, pendientes, 0);
}
```

### Paso 3: Filtros por Campo Normalizado

Si tu código realizaba comprobaciones literales incluyendo el prefijo numérico de Remedy, actualiza las condiciones:

```javascript
// ❌ Código antiguo (fallará con el nuevo esquema)
if (incident.Urgencia === "4-Baja") { ... }

// ✅ Código adaptado
if (incident.Urgencia === "Baja") { ... }

// ✅ O compatible con ambos durante transición
if (incident.Urgencia === "Baja" || incident.Urgencia === "4-Baja") { ... }
```

---

## 📁 Persistencia Desacoplada de Salidas y Errores

El conversor almacena los archivos transformados y los reportes de validación en rutas desacopladas:

| Tipo de Archivo | Ruta en VPS Producción | Ruta en Desarrollo Local |
|---|---|---|
| **Salida JSON Válida** | `/infocodes/var/storage/release-dashboard/output/` | `data/output/` |
| **Índice Global (`index.json`)** | `/infocodes/var/storage/release-dashboard/output/index.json` | `data/output/index.json` |
| **Reportes de Errores** | `/infocodes/var/storage/release-dashboard/errors/` | `data/errors/` |

### Estructura de los Informes de Error (`data/errors/`)

Cuando un CSV contiene filas que violan el esquema o tienen fechas corruptas, las filas inválidas se segregan a un reporte de errores sin descartar las filas válidas:

```json
{
  "summary": {
    "total_records": 100,
    "valid_records": 95,
    "invalid_records": 5,
    "success_rate": 95.0
  },
  "errors": [
    {
      "row": 14,
      "fields": {
        "Fecha": {
          "value": "2026/99/99",
          "error": "Formato de fecha inválido (esperado DD/MM/YYYY o ISO 8601)"
        }
      }
    }
  ]
}
```

---

## ⚡ Rendimiento y Cobertura

- **Velocidad de procesamiento**: Procesamiento en streaming de bajo consumo de memoria. Conversión de archivos de miles de registros en menos de 2 segundos.
- **Calidad garantizada**: El módulo de conversores cuenta con más de **516 pruebas automatizadas** en [`converters/tests/`](../converters/tests/) que validan delimitadores, encodings, esquemas y límites numéricos, con cobertura obligatoria $\ge$ 80% en GitHub Actions.

---

## 🔗 Documentación Relacionada

- [**`DASHBOARDS-API.md`**](DASHBOARDS-API.md): Especificación de APIs, rutas y persistencia de ficheros.
- [**`PROJECT-STRUCTURE.md`**](PROJECT-STRUCTURE.md): Estructura del repositorio y desacoplamiento de `/infocodes/var/storage/`.
- [**`CI.md`**](CI.md): Pipeline de Integración Continua y validación de cobertura.
- [**`DEVELOPMENT.md`**](DEVELOPMENT.md): Entorno de desarrollo local y pruebas con pytest.
- [**`converters/docs/API.md`**](../converters/docs/API.md): Referencia detallada de la API interna de los conversores.
