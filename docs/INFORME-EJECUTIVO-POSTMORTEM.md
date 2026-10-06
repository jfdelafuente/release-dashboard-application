# Informe Ejecutivo de Incidencias Postmortem (Feature 010)

## Resumen

Esta funcionalidad permite generar bajo demanda una presentación corporativa PowerPoint (`.pptx`) con el diseño y formato oficial de Orange a partir de datos estructurados o páginas de postmortem de incidencias en Confluence.

La funcionalidad está integrada en:
1. **Gestión de Problemas Dashboard** (`http://localhost:8000/problemas`): Botón interactivo `📊 Generar PPT` en cada fila de postmortem de la tabla de incidencias.
2. **Servidor API Backend** (`serve_app.py`): Endpoints de generación, consulta de estado y descarga de presentaciones.
3. **Herramienta CLI** (`converters/cli/generate_executive_report.py`): Generación directa por terminal o scripts de automatización.

---

## Arquitectura y Componentes

### 1. Plantilla PowerPoint de Referencia
- Ubicación: `converters/src/report_generator/assets/executive_template.pptx`
- Formato oficial Orange (color corporativo `#FF7900`, tipografía Helve, cajas de impacto, causa, solución, tabla de acciones y tablas cronológicas paginadas).

### 2. Generador (`ExecutiveReportBuilder`)
- Ubicación: `converters/src/report_generator/executive_report_builder.py`
- Utiliza `python-pptx` para cargar la plantilla y actualizar los campos y tablas sin perder estilos de fuente, bordes ni colores.
- Distribuye cronologías de incidentes extensos a lo largo de las Diapositivas 2, 3 y diapositivas adicionales clonadas si es necesario.

### 3. Parser Confluence (`ConfluenceParser`)
- Ubicación: `converters/src/report_generator/confluence_parser.py`
- Parser tolerante a fallos para contenido HTML o texto copiado de Confluence.
- Extrae automáticamente:
  - Referencia de incidencia y título
  - Hora de inicio y duración
  - Bloques de Impacto, Causa y Solución
  - Tabla de Puntos de Acción Relevantes (`Pain Point | Descripción | Owner | Forecast`)
  - Tabla cronológica (`Hora | Evento`)

### 4. Endpoints REST
- `POST /api/reports/executive-incident`: Genera la presentación y devuelve metadatos con URL de descarga. Acepta `force=true` para sobrescribir caché.
- `GET /api/reports/executive-incident/{incidentRef}`: Descarga el archivo binario `.pptx` generado.
- `GET /api/reports/executive-incident/{incidentRef}/status`: Devuelve `{ "exists": true|false, "filename": ..., "downloadUrl": ... }`.

### 5. UI Modal (`ExecutiveReportModal.tsx`)
- Ubicación: `gestion-problemas-dashboard/components/ExecutiveReportModal.tsx`
- Modal accesible con confirmación de URL de Confluence o pegado directo de contenido, comprobación automática de versión existente en caché y descarga en un clic.

---

## Uso desde Línea de Comandos (CLI)

```bash
# Generación rápida por código
python converters/cli/generate_executive_report.py --ref 2606S77393 --title "Problema llamadas IVR"

# Con archivo HTML de postmortem
python converters/cli/generate_executive_report.py --ref 2606S77393 --file postmortem.html --force

# Con URL de Confluence
python converters/cli/generate_executive_report.py --ref 2606S77393 --url "https://confluence.si.orange.es/display/POSTMORTEM/INC-2606S77393"
```

Los informes generados se guardan por defecto en:
`data/reports/executive/RESUMEN_EJECUTIVO_{incidentRef}.pptx`

---

## Suite de Pruebas

Ejecutar las pruebas unitarias:
```bash
pytest converters/tests/unit/report_generator/test_executive* converters/tests/unit/report_generator/test_confluence* -v
```
