---
name: incident-report-pipeline
alias: publicar-informe-incidencias
description: Extrae datos de ficheros Excel (.xlsm/.xlsx) de la Mesa de Seguimiento de Incidencias, construye y verifica programáticamente el Informe de Incidencias Pendientes por Proyecto en Markdown y lo convierte a HTML estático para el portal release-dashboard-application. Úsese siempre que se procese un Excel de seguimiento de incidencias post-release o se invoque el agente incident-report-publisher.
---

# Especificación Técnica: Pipeline de Publicación de Informes de Incidencias (`incident-report-pipeline`)

Esta skill proporciona las reglas normativas de extracción, transformación literal, verificación programática y conversión a HTML para el informe de **Incidencias Pendientes por Proyecto** a partir del fichero `.xlsm` de la Mesa de Seguimiento.

**Propósito en una frase:** convertir de forma mecánica y sin pérdida de información un Excel `.xlsm` de seguimiento de incidencias en un informe Markdown verificado y su publicación HTML en el portal, sin que el modelo reescriba, resuma ni invente ningún dato.

---

## 0. Flujo Completo del Pipeline (orden obligatorio)

Ejecuta siempre las fases en este orden. No saltes ni reordenes ninguna:

1. **Extracción** — corre `scripts/extract_excel.ps1` sobre el `.xlsm` de origen y genera `incidencias.json` (ver §1).
2. **Construcción del Markdown** — agrupa por proyecto, resuelve `Estado` y divide `Acciones` fila por fila según las reglas mecánicas (ver §2).
3. **Verificación obligatoria** — corre `scripts/verify_report.ps1` contra el JSON y el Markdown generados; si reporta cualquier discrepancia, corrige el Markdown y vuelve a verificar hasta obtener 0 discrepancias (ver §3). No continúes a la fase 4 sin esto.
4. **Conversión a HTML** — transforma el Markdown verificado en `index.html` siguiendo el parser y las clases de badge especificadas (ver §4).
5. **Publicación en el portal** — añade o actualiza la tarjeta correspondiente en `dashboards/portal/index.html` (ver §4, último punto).

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
- **Definición exacta de `{slug-release}`:** toma el código de release tal como figura en el Excel (ej. `"R7 2026"`), conviértelo a minúsculas y sustituye cada espacio por un guion (`-`). No elimines ni reordenes los componentes: `"R7 2026"` → `r7-2026`.
- **Definición exacta de `{fecha}`:** fecha del export del Excel en formato `AAAAMMDD` (ej. `31/07/2026` → `20260731`).
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
> **PROHIBIDO parafrasear, resumir, reordenar, corregir redacción/ortografía o recortar frases** al transcribir `Descripción`, `Impacto` o `Solución`. El texto resultante debe ser una subcadena literal, carácter por carácter, del contenido original de `Acciones` (solo recortando espacios en los extremos de cada tramo, ver regla 5).

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
5. **Recorte de espacios en los bordes del split:** el marcador (`⚠ Impacto`, `✓ Solución`) y cualquier espacio o salto de línea inmediatamente adyacente a él se eliminan; el texto interior se conserva íntegro y solo se le aplica `trim()` en sus dos extremos. No se elimina ni se normaliza ningún espacio o puntuación dentro del cuerpo del texto.

#### Ejemplo concreto obligatorio (úsalo como referencia de formato exacto)

**Celda `Acciones` original en el Excel** (una sola celda, incidencia `INC000012345678`, `Status` = `Resuelto`, `Fecha Prevista` = `15/07/2026`):

```text
El servicio de facturación presenta cortes intermitentes desde el 03/07/2026 afectando a clientes empresariales de la región norte.⚠ Impacto Los clientes no pueden consultar sus facturas electrónicas, lo que genera llamadas al CAU y reclamaciones formales.✓ Solución Se ha desplegado un parche en el servicio de facturación que corrige el timeout de conexión a la base de datos histórica.
```

**Resultado del split mecánico (regla "con `⚠ Impacto` y `✓ Solución`"):**

| Campo | Valor literal resultante |
| :--- | :--- |
| `Descripción` | `El servicio de facturación presenta cortes intermitentes desde el 03/07/2026 afectando a clientes empresariales de la región norte.` |
| `Impacto` | `Los clientes no pueden consultar sus facturas electrónicas, lo que genera llamadas al CAU y reclamaciones formales.` |
| `Solución` | `Se ha desplegado un parche en el servicio de facturación que corrige el timeout de conexión a la base de datos histórica.` |

**Fila de tabla Markdown resultante** (7 columnas exactas, `Estado` con fecha de `Resuelto`):

```text
| INC000012345678 | 03/07/2026 | Facturación | Resuelto (15/07/2026) | El servicio de facturación presenta cortes intermitentes desde el 03/07/2026 afectando a clientes empresariales de la región norte. | Los clientes no pueden consultar sus facturas electrónicas, lo que genera llamadas al CAU y reclamaciones formales. | Se ha desplegado un parche en el servicio de facturación que corrige el timeout de conexión a la base de datos histórica. |
```

Este mismo caso, convertido a HTML, se usa como referencia en §4.

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

**Criterio de aceptación:** el informe solo se considera terminado cuando `verify_report.ps1` reporta 0 discrepancias en los 5 puntos anteriores. Si reporta cualquier discrepancia, corrige el Markdown (nunca el JSON de origen) y vuelve a ejecutar el verificador antes de pasar a la fase de HTML.

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

### Ejemplo concreto obligatorio del fragmento HTML (misma fila que en §2.D)

Fila Markdown de entrada:

```text
| INC000012345678 | 03/07/2026 | Facturación | Resuelto (15/07/2026) | El servicio de facturación presenta cortes intermitentes desde el 03/07/2026 afectando a clientes empresariales de la región norte. | Los clientes no pueden consultar sus facturas electrónicas, lo que genera llamadas al CAU y reclamaciones formales. | Se ha desplegado un parche en el servicio de facturación que corrige el timeout de conexión a la base de datos histórica. |
```

HTML resultante (badge `status-cerrada` porque `Status` = `Resuelto`):

```html
<tr>
  <td>INC000012345678</td>
  <td>03/07/2026</td>
  <td>Facturación</td>
  <td><span class="status-badge status-cerrada">Resuelto (15/07/2026)</span></td>
  <td>El servicio de facturación presenta cortes intermitentes desde el 03/07/2026 afectando a clientes empresariales de la región norte.</td>
  <td>Los clientes no pueden consultar sus facturas electrónicas, lo que genera llamadas al CAU y reclamaciones formales.</td>
  <td>Se ha desplegado un parche en el servicio de facturación que corrige el timeout de conexión a la base de datos histórica.</td>
</tr>
```

---

## 5. Prohibiciones Explícitas (Nunca hagas esto)

- **Nunca parafrasees, resumas, reordenes, corrijas ortografía/redacción ni recortes** el texto original de `Descripción`, `Impacto` o `Solución`: deben ser subcadenas literales de `Acciones` o `Descripción problema` según la regla aplicable de §2.D.
- **Nunca inventes datos** (proyecto, descripción funcional, impacto o solución) cuando la fuente esté vacía o el emparejamiento no sea evidente al 100%: detente y pregunta al usuario, u omite la línea según indique la regla correspondiente.
- **Nunca proceses una fila con `Acciones` completamente vacío** sin antes preguntar al usuario el texto real de esa incidencia.
- **Nunca infieras una `Solución` no escrita explícitamente** solo porque `Status` figure como `"Resuelto"`.
- **Nunca saltes ni sustituyas por una revisión visual** la ejecución de `scripts/verify_report.ps1`; el informe no está terminado hasta que reporte 0 discrepancias.
- **Nunca dejes procesos `EXCEL.EXE` huérfanos**: toda apertura COM de Excel debe liberarse en un bloque `finally` con `$excel.Quit()` y `ReleaseComObject`.
- **Nunca uses la columna `Estatus`** para rellenar `Estado`; usa siempre `Status`.
- **Nunca fuerces a `"Sin proyecto asignado"`** un `prj` con valor no estándar pero no vacío (ej. `"REGRESION"`).
- **Nunca inserte `|` sin escapar** en una celda Markdown, ni confunda una línea `**negrita**` con la descripción de proyecto en cursiva simple (`*texto*`).
