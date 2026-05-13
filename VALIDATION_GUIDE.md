# Guía de Validación: Dashboard Hub vs Dashboard de Masivas

## Resumen del Problema Encontrado y Corregido

### Problema Identificado
El Dashboard Hub estaba calculando las tendencias de KPI de forma **INCORRECTA**. La lógica no consideraba la fecha de resolución de las incidencias, lo que resultaba en valores de tendencia que no coincidían con el Dashboard de Masivas.

**Valores incorrectos calculados:**
- Tendencia 7d: 180.0%
- Tendencia 15d: 366.7%
- Tendencia 30d: 600.0%

### Solución Implementada
Se corrigió la función `countPendingAtDate()` en `dashboard-hub.js` para:
1. Considerar la "Fecha de última resolución" de las incidencias
2. Contar una incidencia como "abierta" en una fecha pasada solo si:
   - Fue abierta antes o en esa fecha, Y
   - (No estaba cerrada O se resolvió después de esa fecha)

**Valores correctos calculados:**
- Tendencia 7d: **-22.2%** (reducción del backlog)
- Tendencia 15d: **-36.4%** (reducción del backlog)
- Tendencia 30d: **-26.3%** (reducción del backlog)

---

## Procedimiento de Validación Manual

### Paso 1: Verificar archivo de datos
El archivo de prueba está disponible en:
```
data/output/CS_Masiva_20260513-massive.json
```

**Características del archivo:**
- Total de incidencias: 2147
- Incidencias pendientes: 14
- Período de datos: 17/03/2025 a 13/05/2026

### Paso 2: Validar con script de Python
Ejecutar el script de validación:
```bash
python validate_kpis.py
```

**Salida esperada:**
```
Total incidencias: 2147
Incidencias pendientes (HOY): 14

Tendencia 7 días: -22.2%
Tendencia 15 días: -36.4%
Tendencia 30 días: -26.3%
```

### Paso 3: Comparar con Dashboard de Masivas (Validación Manual en Navegador)

1. **Abre el Dashboard de Masivas:**
   - Archivo: `massive-incidents-dashboard.html`
   - Abre en navegador (Chrome, Firefox, Safari o Edge)

2. **Carga el archivo JSON:**
   - Click en "Cargar Datos" (drag-and-drop area)
   - Selecciona: `data/output/CS_Masiva_20260513-massive.json`
   - El Dashboard cargará automáticamente

3. **Verifica los KPIs en el Dashboard:**
   - **Total Incidencias**: Debe mostrar **2147**
   - **Incidencias Pendientes**: Debe mostrar **14**
   - **Tendencia 7 días**: Debe mostrar **-22.2%** (con color verde = reducción)
   - **Tendencia 15 días**: Debe mostrar **-36.4%** (con color verde = reducción)
   - **Tendencia 30 días**: Debe mostrar **-26.3%** (con color verde = reducción)

4. **Compara con Dashboard Hub:**
   - Abre `dashboard-hub.html` en otra pestaña
   - El Dashboard Hub debe mostrar los MISMOS valores que el Dashboard de Masivas
   - Los valores se cargan automáticamente desde `data/output/index.json`

### Paso 4: Validación Final

✅ **Validación EXITOSA si:**
- Todos los valores KPI coinciden exactamente entre ambos dashboards
- Las tendencias muestran el MISMO color (verde para reducción)
- No hay errores en la consola del navegador

❌ **Validación FALLIDA si:**
- Los valores no coinciden
- Las tendencias tienen colores diferentes
- Hay errores en console.log

---

## Detalles Técnicos

### Lógica de Cálculo de Pendientes en Fecha Específica

**Código corregido en `countPendingAtDate()`:**

```javascript
// Una incidencia se cuenta como ABIERTA en targetDate si:
// 1. Fue abierta ANTES O EN targetDate
// 2. Y una de estas condiciones:
//    - Su estatus actual NO es "cerrado/resuelto/cancelado"
//    - O si está cerrada, fue resuelta DESPUÉS de targetDate

if (incidentDate > targetDate) return false;  // No cuenta si fue abierta después

const status = incident['Estatus'].toLowerCase();

if (status.includes('cerrado') || ...) {
    // Si está cerrada, verificar fecha de resolución
    const resolveDate = parseDate(incident['Fecha de última resolución']);
    // Solo contar si se resolvió DESPUÉS de targetDate
    return resolveDate > targetDate;
} else {
    // No está cerrada = estaba abierta
    return true;
}
```

### Fórmula de Tendencia

```
% Cambio = ((BacklogHoy - BacklogPasado) / BacklogPasado) × 100

Ejemplo para 7d:
- BacklogHoy = 14
- BacklogHace7Días = 18
- % Cambio = ((14 - 18) / 18) × 100 = -22.2%
```

---

## Archivos Relacionados

| Archivo | Descripción |
|---------|-------------|
| `dashboard-hub.js` | Contiene `countPendingAtDate()` corregido |
| `validate_kpis.py` | Script de validación independiente |
| `massive-incidents-dashboard.html` | Fuente de verdad para los valores |
| `data/output/CS_Masiva_20260513-massive.json` | Archivo de prueba |

---

## Pasos Siguientes

1. **Ejecutar validación:** `python validate_kpis.py`
2. **Abrir navegadores:** `dashboard-hub.html` y `massive-incidents-dashboard.html`
3. **Cargar datos:** Subir `CS_Masiva_20260513-massive.json` a Dashboard de Masivas
4. **Comparar:** Verificar que los KPIs coinciden exactamente
5. **Documentar:** Anotar los valores reales observados

---

## Notas Importantes

- Los datos contienen incidencias desde marzo 2025 hasta mayo 2026
- El backlog muestra una **tendencia NEGATIVA** (reducción) en los últimos 7, 15 y 30 días
- Los valores de pendientes (14) ya incluyen la lógica de filtrado por estatus
- Las tendencias solo son significativas si hay suficientes datos históricos

---

**Última actualización:** 2026-05-13
**Estado:** Listo para validación manual en navegador
