# Quickstart: Generación y Prueba del Informe Ejecutivo de Incidencias

**Feature**: `010-incident-executive-report`

---

## 1. Verificación del Generador en Local vía CLI

Puedes probar la generación del archivo PowerPoint directamente con un script de prueba antes de levantar los servicios:

```powershell
# Ejecutar prueba de generación con datos de ejemplo basados en la plantilla
python converters/tests/unit/report_generator/test_executive_report_builder.py
```

El script tomará la plantilla `20260609 Incidencia IVR ExMM.pptx` (o su copia en `converters/src/report_generator/assets/executive_template.pptx`), generará el archivo `data/reports/executive/RESUMEN_EJECUTIVO_2606S77393.pptx` y verificará:
- Diapositiva 1 con títulos, inicio, duración, cajas de texto y tabla de 4 columnas.
- Diapositivas 2 y 3 con la tabla cronológica de eventos.

---

## 2. Arranque del Servidor Local

1. **Arrancar el servidor de dashboards y backend de informes**:
```powershell
python serve_app.py
```
El servidor estará escuchando en `http://localhost:8000`.

2. **Arrancar el panel de Gestión de Problemas (en otra terminal)**:
```powershell
cd ..\gestion-problemas-dashboard
$env:NEXT_PUBLIC_BASE_PATH='/problemas'
npm run dev -- -p 3001
```

3. **Acceder a la aplicación**:
Abre tu navegador en `http://localhost:8000/problemas` y dirígete a la pestaña de **Postmortems**.

---

## 3. Flujo de Prueba de Usuario

1. En la tabla de **Detalle de postmortems**, localiza una fila que cuente con postmortem (ej. `2606S77393` o cualquier otra incidencia).
2. Haz clic en el botón **"📄 Generar PPT"**.
3. Revisa la URL de Confluence en el modal y haz clic en **"Generar y Descargar PPT"**.
4. Verifica que el archivo `.pptx` se descarga automáticamente en tu navegador.
5. Abre el `.pptx` en PowerPoint y valida que conserva la estética corporativa de Orange, los bloques narrativos y las tablas formateadas.
6. Regresa al dashboard y comprueba que la fila ahora muestra el botón **"⬇️ Descargar PPT"** para descargas instantáneas sin recálculo.
