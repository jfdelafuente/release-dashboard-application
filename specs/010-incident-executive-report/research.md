# Research & Technical Decisions: Informe Ejecutivo de Incidencias Postmortem (010-incident-executive-report)

**Feature**: `010-incident-executive-report`
**Date**: 2026-10-06

---

## 1. Motor de Generación del Informe PowerPoint (`.pptx`)

### Decisión
Utilizar `python-pptx` (ya disponible en el ecosistema del proyecto) para clonar y cumplimentar dinámicamente la plantilla de referencia [`20260609 Incidencia IVR ExMM.pptx`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/20260609%20Incidencia%20IVR%20ExMM.pptx) preservada en `converters/src/report_generator/assets/executive_template.pptx`.

### Rationale
- **Fidelidad Visual Absoluta**: La plantilla `20260609 Incidencia IVR ExMM.pptx` ya contiene los estilos aprobados por la dirección de Orange: paleta de colores, márgenes, proporciones de cajas de texto, cabeceras con el color corporativo (`#FF7900`), tamaños de fuente y estilos de tabla.
- **Sin Dependencias Externas de Navegador**: A diferencia de la exportación a PDF o generación de capturas HTML (que requerían Chrome headless / kaleido con configuraciones de `sudo`), `python-pptx` manipula archivos XML comprimidos nativos de Office, siendo 100% autónomo, ultrarrápido (< 1 segundo por informe) y sin requerir permisos especiales en el servidor.
- **Paginación Dinámica de Tablas**:
  - *Diapositiva 1*: Se actualizan los títulos, subtítulos (Inicio / Duración), cuadros de texto para `IMPACTO`, `CAUSA`, `SOLUCION` y la tabla de `PUNTOS DE ACCION RELEVANTES` (máx. 6-7 filas; si hay más, se ajusta el espaciado o se añade una diapositiva anexa).
  - *Diapositivas 2 y 3*: La tabla cronológica (`Hora | Evento`) admite ~18-20 filas por diapositiva. Si el postmortem tiene más de 38 eventos, el generador clona el diseño de la diapositiva 3 para crear diapositivas adicionales manteniendo la continuidad.

### Alternativas Evaluadas
- **Generar desde cero con `python-pptx`**: Descartado porque requiere recrear programáticamente docenas de coordenadas, colores RGB, bordes y tipografías que ya están perfectamente afinados en la plantilla `.pptx`.
- **Exportación HTML a PDF**: Descartado porque el usuario solicitó expresamente PowerPoint (`.pptx`) editable para que los comités directivos puedan incorporar notas o diapositivas adicionales.

---

## 2. Ingesta y Extracción de Contenido desde Confluence

### Decisión
Diseñar un extractor híbrido tolerante a fallos:
1. **Modal Interactivo en el Frontend**: Cuando el operador pulsa "Generar Informe" en una fila de la tabla de candidatos, el modal precarga la URL de Confluence registrada en la incidencia (`issue.wikiPage.url`).
2. **Extracción mediante Sesión del Operador**:
   - Dado que Confluence en Orange está protegido bajo SSO corporativo, la interfaz de usuario en el navegador del operador puede realizar la petición o pasar el token/contenido al endpoint de backend.
   - Si la API directa no es accesible desde el backend por restricciones de red/firewall, el modal ofrece una pestaña secundaria de "Pegar contenido" (HTML o texto copiado de Confluence), garantizando que el operador **nunca quede bloqueado**.
3. **Mapeo Inteligente de Secciones (Parser)**:
   - El parser busca encabezados y etiquetas estándar de postmortem:
     - Metadatos: Código TT / Incidencia, Fecha/Hora inicio, Fecha/Hora fin / resolución, Duración.
     - Bloques narrativos: "Impacto" / "Afectación", "Causa raíz" / "Causa", "Solución" / "Acciones de contención".
     - Tabla de Puntos de Acción: Detecta columnas `Pain Point`, `Descripción`, `Owner` / `Responsable`, `Forecast` / `Fecha Prevista`.
     - Tabla de Cronología: Detecta columnas `Hora` / `Tiempo`, `Evento` / `Hito`.

### Rationale
- Se adapta al flujo de trabajo real del operador que ya tiene Confluence abierto en su navegador.
- No requiere crear ni mantener cuentas de servicio de larga duración en Confluence con permisos administrativos.

---

## 3. Arquitectura del Backend y Endpoints de Servicio

### Decisión
Exponer una API REST ligera y estandarizada en el servicio backend (`serve_app.py` en local y el backend de producción):
- `POST /api/reports/executive-incident`:
  - Recibe JSON con `incidentRef`, `confluenceUrl`, y opcionalmente `extractedData` / `htmlContent`.
  - Procesa y genera el archivo `.pptx` en `data/reports/executive/RESUMEN_EJECUTIVO_{incidentRef}.pptx`.
  - Devuelve `{ "success": true, "downloadUrl": "/api/reports/executive-incident/{incidentRef}", "incidentRef": "...", "generatedAt": "..." }`.
- `GET /api/reports/executive-incident/{incidentRef}`:
  - Descarga directa del archivo binario con cabecera `Content-Type: application/vnd.openxmlformats-officedocument.presentationml.presentation` y `Content-Disposition: attachment; filename="RESUMEN_EJECUTIVO_{incidentRef}.pptx"`.
- `GET /api/reports/executive-incident/{incidentRef}/status`:
  - Comprueba si el informe ya existe en almacenamiento, permitiendo a la UI mostrar de inmediato el botón "Descargar" sin coste de procesamiento.

### Rationale
- Sigue exactamente el mismo patrón probado y consolidado de `/api/reports/postmortem/{release_name}` en la aplicación.
- Permite la integración tanto desde `gestion-problemas-dashboard` (Next.js) como desde cualquier otro dashboard o script CLI.

---

## 4. Integración en la Interfaz de Gestión de Problemas (`gestion-problemas-dashboard`)

### Decisión
1. **Modificación de `IssuesTable.tsx`**:
   - En la tabla de *Postmortems*, añadir una columna "Informe Ejecutivo" o integrar un botón de acción junto al enlace de `wikiPage`.
   - Si no existe informe: Botón `[ 📄 Generar ]` con estilo Orange.
   - Si ya existe informe generado: Botón `[ ⬇️ Descargar ]` con opción contextual de `[ 🔄 Regenerar ]`.
2. **Componente `ExecutiveReportModal.tsx`**:
   - Diálogo accesible e interactivo con:
     - Cabecera: Código de la incidencia y título.
     - Campo de URL de Confluence (precargado con `wikiPage.url`).
     - Botón "Generar y Descargar".
     - Indicador visual de progreso durante la generación (<15s).
     - Visualización de errores con mensaje comprensible si el enlace es inaccesible.

---

## 5. Resumen de Decisiones Técnicas

| Aspecto | Elección | Justificación Principal |
|---|---|---|
| **Formato y Motor** | `python-pptx` sobre `20260609 Incidencia IVR ExMM.pptx` | 100% fidelidad visual Orange, sin dependencias de Chrome headless ni sudo. |
| **Ingesta Confluence** | Diálogo interactivo con URL y soporte de sesión | Evita bloqueos por firewalls y no exige tokens de servicio globales. |
| **Punto de Entrada UI** | Botón por fila en tabla de Postmortems (`IssuesTable.tsx`) | Acceso contextual directo donde el operador evalúa los postmortems candidatos. |
| **Persistencia** | `data/reports/executive/` en disco | Caché inmediata para descargas repetidas y soporte de regeneración bajo demanda. |
