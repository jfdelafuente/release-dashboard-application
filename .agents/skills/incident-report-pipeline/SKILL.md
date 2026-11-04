---
name: incident-report-pipeline
alias: publicar-informe-incidencias
description: Extrae datos de ficheros Excel (.xlsm/.xlsx) de la Mesa de Seguimiento de Incidencias, construye y verifica programáticamente el Informe de Incidencias Pendientes por Proyecto en Markdown y lo convierte a HTML estático para el portal release-dashboard-application. Úsese siempre que se procese un Excel de seguimiento de incidencias post-release o se invoque el agente incident-report-publisher.
---

# Especificación Técnica: Pipeline de Publicación de Informes de Incidencias (`incident-report-pipeline`)

Esta skill proporciona las reglas normativas de extracción, transformación literal, verificación programática y conversión a HTML para el informe de **Incidencias Pendientes por Proyecto** a partir del fichero `.xlsm` de la Mesa de Seguimiento.

---

## 1. Extracción Segura del Excel vía COM (`scripts/extract_excel.ps1`)

En entornos Windows sin Python o con libros `.xlsm` con macros, la extracción se realiza mediante automatización COM de Excel en PowerShell con macros deshabilitadas (`AutomationSecurity = 3`) y apertura en modo solo lectura (`ReadOnly = $true`).

### Script oficial incluido en la skill
```powershell
powershell -ExecutionPolicy Bypass -File ".agents/skills/incident-report-pipeline/scripts/extract_excel.ps1" -ExcelPath "R9-2026. Mesa.Seguimiento Incidencias...xlsm" -OutJsonPath "incidencias.json"
```

### Reglas críticas de extracción y codificación
1. **Errores de fórmula en `Value2`:** Para celdas vacías con fórmula rota (`#¡VALOR!`, `#N/A`, `#REF!`), `Value2` devuelve enteros negativos grandes (ej. `-2146826273`, `-2146826246`, `-2146826265`). Nunca confíes ciegamente en `Value2`: verifica `.Text` de la celda; si `.Text` empieza por `#` o está vacío, trátalo como cadena vacía `""`.
2. **Liberación del objeto COM:** Todo bloque de apertura de Excel debe cerrarse dentro de un bloque `finally` con `$excel.Quit()` y `[System.Runtime.InteropServices.Marshal]::ReleaseComObject($excel)` para no dejar procesos `EXCEL.EXE` huérfanos.
3. **Codificación UTF-8 con BOM en PowerShell 5.1:** Windows PowerShell 5.1 interpreta scripts `.ps1` sin BOM como ANSI (`Windows-1252`). Guarda siempre cualquier script auxiliar en **UTF-8 con BOM** (`New-Object System.Text.UTF8Encoding $true`) o utiliza expresiones regulares insensibles a tildes (ej. `^En An.lisis`, `^Soluci.n`) para evitar mojibake o falsos negativos.

---

## 2. Reglas de Negocio y Construcción del Informe Markdown

### A. Estructura general y Título
- **Nombre del archivo Markdown:** `informe-incidencias-pdtes-{slug-release}-{fecha}.md` (ej. `informe-incidencias-pdtes-r7-2026-20260731.md`).
- **Título principal (`# `):** Usa exclusivamente el código de release y la fecha del export, **sin prefijo genérico**:
  - ✅ Correcto: `# R7 2026 (Mesa de Seguimiento, export 31/07/2026)`
  - ❌ Incorrecto: `# Informe de Incidencias Pendientes por Proyecto — R7 2026 (...)`

### B. Agrupación por Proyecto y Jerarquía de Descripciones
- **`prj` con error de Excel** (`.Text` vacío pese a `Value2` negativo): se agrupa bajo `## Proyecto: Sin proyecto asignado`.
- **`prj` con valor no estándar pero no vacío** (ej. `"REGRESION"`, sin formato `PRJ-XXXXX`): forma su propio grupo de proyecto usando `Descripción Proyecto` como nombre visible; nunca lo fuerces a `"Sin proyecto asignado"`.
- **Orden de prioridad para obtener la descripción funcional de cada proyecto** (se coloca en cursiva con un solo asterisco `*texto*` justo debajo de `## Proyecto: ...` y antes de la tabla):
  1. **1ª Fuente (`proyectos.md` en OneDrive):** `C:\Users\jose.delafuente\OneDrive - MASORANGE\Mesa Postproduccion\PostProduccion {AÑO}\{RELEASE}\proyectos.md` (emparejamiento directo por código `PRJ-XXXXX`).
  2. **2ª Fuente (`ProyectosR{N}.xlsx` en el repositorio):** emparejamiento por nombre entre la columna `PROYECTO` y `Descripción Proyecto`. Si el emparejamiento no es evidente al 100%, **detente y pregunta al usuario** antes de asignarlo.
  3. **3ª Fuente (`Plan de Coordinación Release ... vfinal.pdf` en OneDrive):** carpeta de la release en OneDrive si no aparece en las dos fuentes anteriores.
  4. **Fallback:** si el proyecto no figura en ninguna fuente, **omite la línea de descripción** (nunca inventes ni pongas texto de relleno).

### C. Columnas de la Tabla y Reglas de `Estado`
Cada proyecto contiene una única tabla GFM continua, ordenada por severidad descendente, con **7 columnas exactas**:
`| Código | Fecha Apertura | Sistema | Estado | Descripción | Impacto | Solución |`

- **Columna `Estado`:** Utiliza siempre la columna **`Status`** del Excel (nunca `Estatus`, ya que `Status` distingue `"Solución Rechazada"`).
- **Formato de fecha integrada en `Estado` (usando `Fecha Prevista`):**
  | Valor en `Status` | Formato obligatorio en la tabla | Regla clave |
  | :--- | :--- | :--- |
  | **`En Análisis`** | `En Análisis` | **Sin fecha** (se muestra a secas). |
  | **`Pendiente`** | `Pendiente (Estimado: DD/MM/AAAA)` o `Pendiente (Estimado: sin fecha)` | Conserva siempre la palabra **`Estimado:`**. |
  | **`Resuelto`** | `Resuelto (DD/MM/AAAA)` o `Resuelto (sin fecha)` | **Sin** la palabra `"Estimado"`. |
  | **`Solución Rechazada`** | `Solución Rechazada (DD/MM/AAAA)` o `Solución Rechazada (sin fecha)` | **Sin** la palabra `"Estimado"`. |

### D. Split Mecánico y Literal de la Columna `Acciones` (Cero Parafraseo)
> **PROHIBIDO parafrasear, resumir, reordenar o recortar frases** al transcribir `Descripción`, `Impacto` o `Solución`.

1. **Si `Acciones` está completamente vacío/null:** detén el proceso y pregunta al usuario el texto real de esa incidencia indicando su código `INC...` y `Descripción problema`.
2. **Partición mecánica por marcadores `⚠ Impacto` y `✓ Solución`:**
   - **Con `⚠ Impacto` y `✓ Solución`:**
     - `Descripción` = texto antes de `⚠ Impacto`
     - `Impacto` = texto entre `⚠ Impacto` y `✓ Solución`
     - `Solución` = texto después de `✓ Solución`
   - **Solo con `⚠ Impacto`:**
     - `Descripción` = texto antes de `⚠ Impacto`
     - `Impacto` = texto después de `⚠ Impacto`
     - `Solución` = `Pendiente de solución` (incluso si `Status` figura como `"Resuelto"`, nunca infieras una solución no escrita).
   - **Solo con `✓ Solución` (sin `⚠ Impacto`):**
     - `Descripción` = texto antes de `✓ Solución`. Si está vacío (porque `Acciones` empieza directamente en `✓ Solución`), toma la columna `Descripción problema` limpiando el prefijo `^\[2026R\d+\]\s*(-|\s*\[PRJ-\d+\]\s*-?)?\s*`.
     - `Impacto` = `Impacto no especificado`
     - `Solución` = texto después de `✓ Solución`
   - **Sin ningún marcador (`⚠ Impacto` ni `✓ Solución`, pero con texto):**
     - `Descripción` = texto íntegro de `Acciones`
     - `Impacto` = `Impacto no especificado`
     - `Solución` = `Pendiente de solución`
3. **Subsecciones dentro de `Impacto` o `Solución` (`Bloqueos`, `Siguiente acción`, `Hitos técnicos`):**
   - En **Markdown**: separa cada subsección con `<br><br>` y título en negrita:
     `[Texto principal]<br><br>**Bloqueos:** [detalle]<br><br>**Siguiente acción:** [detalle]<br><br>**Hitos técnicos:**<br>• DD/MM/AAAA: [detalle 1]<br>• DD/MM/AAAA: [detalle 2]`
   - En **Hitos técnicos**, cada fecha debe ir en su propia línea precedida por `<br>• DD/MM/AAAA:`.
4. **Escape de tuberías (`|`):** Sustituye cualquier carácter `|` literal del texto extraído por `\|` antes de insertarlo en una celda Markdown.

---

## 3. Verificación Programática Obligatoria (`scripts/verify_report.ps1`)

Nunca des por válido un informe revisándolo únicamente "a ojo". Ejecuta siempre el verificador incluido en esta skill:

```powershell
powershell -ExecutionPolicy Bypass -File ".agents/skills/incident-report-pipeline/scripts/verify_report.ps1" -JsonPath "incidencias.json" -MdPath "informe-incidencias-pdtes-....md" -HtmlPath "C:\Users\jose.delafuente\proyectos\release-dashboard-application\dashboards\informes\{slug}\index.html"
```

El script comprueba automáticamente:
1. Coincidencia exacta entre `rowCount` del JSON y filas `INC...` en el Markdown.
2. Suma de filas por proyecto igual al total.
3. Correspondencia exacta de `Fecha Apertura` y formato estricto de `Estado` (`En Análisis` sin fecha vs. estados con fecha).
4. Recálculo mecánico de `Descripción`, `Impacto` y `Solución` carácter por carácter (`0` discrepancias requeridas).
5. Conteo de filas `<tr><td>INC...` en el archivo HTML generado.

---

## 4. Especificación de Conversión a HTML y Tarjeta del Portal

- **Ruta de salida HTML:** `C:\Users\jose.delafuente\proyectos\release-dashboard-application\dashboards\informes\{slug}\index.html`
  - **El `{slug}` de carpeta NO lleva fecha** (ej. `incidencias-pdtes-r7-2026`), ya que sobrescribe siempre la vista más reciente de esa release.
- **Reglas del parser Markdown → HTML:**
  1. **Protección de `\|`:** Reemplaza `\|` por un token temporal antes de hacer `split('|')` en cada fila de tabla, y restáuralo después.
  2. **Detección de descripción de proyecto (`*texto*`):** Verifica que la línea empiece y termine con **un solo asterisco** (`^(\*[^*].*[^*]\*)$`) y **no** con doble asterisco `**`, para no capturar por error `**Análisis de impactos:**`. Renderízala como `<p class="project-description">`.
  3. **Badges de Estado (`.status-badge`):** Localiza la columna `Estado` por nombre de cabecera y aplica:
     - `status-pendiente` para `Pendiente`
     - `status-cerrada` para `Resuelto`
     - `status-en-progreso` para `En Análisis`
     - `status-rechazada` (definida en el `<style>` de la página) para `Solución Rechazada`
  4. **Subbloques enriquecidos en celdas:** Convierte `Bloqueos`, `Siguiente acción` e `Hitos técnicos` en bloques `<div class="cell-subblock cell-bloqueos">`, `cell-siguiente-accion` y `cell-hitos` con `.cell-tag` y lista `.cell-hitos-list` / `.cell-hito-item` (`<span class="hito-date">DD/MM/AAAA:</span>`).
  5. **Layout y Cabecera:** Reutiliza `dashboards/assets/shared.css` y `dashboards/assets/topbar.js` (`<div id="mo-topbar-root" data-active="informes">`). Incluye únicamente el eyebrow (`"Fiabilidad de servicio · Customer & Service Operations"`), el `<h1>` con el título corto del Paso 2.A y el divisor, **sin subtítulo explicativo**.
- **Tarjeta en `dashboards/portal/index.html`:** Añade o actualiza `<a class="dashboard-card" href="/dashboards/informes/{slug}/">` justo antes del cierre de `.dashboards-grid`.

