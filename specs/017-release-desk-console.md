# Especificación: Consola de Seguimiento de Mesa de Incidencias de Release

## Objetivo

El seguimiento operativo de las incidencias de una release con los responsables funcionales y grupos soportes requiere revisar todas las incidencias activas (todas excepto las que ya están en estado `Cerrado`) junto con su contexto técnico y ejecutivo generado por **Resumen IA**. Actualmente, el dashboard `postmortem` está orientado a métricas retrospectivas por despliegue y gráficas globales, no a una operativa ágil de Mesa de Seguimiento.

Esta función incorpora una consola dedicada en el portal (**Mesa de Release**) que reutiliza los datasets por release (`*-postmortem.json`) y la capa de **Resumen IA** existente para facilitar las rondas de seguimiento con responsables y soportes, permitiendo filtrar incidencias no cerradas, sincronizarlas online desde MonTMC, consultar o regenerar su Resumen IA y copiar mensajes de seguimiento listos para compartir.

## Requisitos

### Obligatorios

1. **Consola dedicada e integrada en el portal:**
   - Nueva vista web ubicada en `dashboards/release-desk/` (`index.html` + `release-desk.js` / `release-desk.css` o equivalente) accesible desde el menú superior común del portal (`dashboards/assets/topbar.js`).

2. **Filtrado base estricto (`Estatus != "Cerrado"`):**
   - Al cargar una release desde `/data/output/index.json` (sección `postmortem.files`), la consola debe excluir todas las incidencias cuyo `Estatus` sea `Cerrado` (insensible a mayúsculas/minúsculas y espacios) y mostrar todas las demás (`Asignado`, `En Curso`, `En Progreso`, `Pendiente`, `Resuelto`, `Abierto`, etc.) junto con sus KPIs de seguimiento activo.

3. **Selector de release y filtros operativos:**
   - Selector de release poblado con las releases disponibles en `index.json` / `RAW_RELEASES` (permitiendo parámetro `?release=<nombre>` en URL).
   - Filtros interactivos por **Estado**, **Grupo asignado / Resolutor**, **Urgencia / Prioridad** y buscador en tiempo real por ID de incidencia, descripción o responsable/peticionario.

4. **Panel de detalle con Resumen IA:**
   - Al seleccionar una incidencia del listado, mostrar su ficha completa de seguimiento: ID, descripción, estado, prioridad, urgencia, despliegue (`PAP`/`MESA`), grupo asignado, grupo resolutor, responsable/peticionario (`Grupo Remitente`), fechas de envío/resolución y solución registrada.
   - Integrar la sección de **Resumen IA** mostrando los datos obtenidos desde `/api/epsilon/resumen` (o caché disponible) y un botón **"Generar / Refrescar Resumen IA"** que invoque `POST /api/epsilon/resumen` (con `force_refresh: true` al refrescar) para obtener o actualizar la síntesis ejecutiva/técnica de la incidencia.

5. **Sincronización MonTMC y copiado rápido:**
   - Botón **"⚡ Sincronizar Epsilon"** que invoque `POST /api/sync-postmortem` para la release seleccionada y recargue automáticamente los datos de la consola al completar.
   - Botón **"Copiar seguimiento"** en la ficha de detalle que copie al portapapeles un texto estructurado listo para pegar en Teams o correo (incluyendo ID, release, estado, grupo soporte/resolutor, responsable y Resumen IA).

6. **Carga Web de Pruebas PaP de Grafana Argos y Regeneración Bajo Demanda del Informe Ejecutivo PaP:**
   - Botón **"📊 Cargar Argos PaP"** (`#btnUploadArgos`) en la barra de acciones superior que despliega un modal web interactivo (`#argosUploadModal`) con zonas de arrastre (drag-and-drop) y selectores de archivo para los CSVs de Progresión (`PRJ-*`) y Regresión Transversal E2E.
   - Endpoint unificado `POST /api/release-desk/upload-argos` (implementado en `desk_service.py` y soportado tanto en `serve_app.py` en local como en `fastapi_remedy_router.py` en VPS) que:
     - Detecta automáticamente la tipología de cada fichero.
     - Realiza una fusión inteligente y atómica en `data/storage/projects/{release}_grafana_pap.csv`, preservando las filas existentes de la otra tipología si solo se sube una de ellas.
     - Compila y publica automáticamente el Informe Ejecutivo PaP en HTML (`dashboards/informes/comunicado-release-{release}/index.html`) y lo abre en una nueva pestaña.
   - Botón unificado **"🌐 Informe Ejecutivo PaP"** (`#btnGenerateReportHtml`) en la barra inferior que invoca `POST /api/release-desk/generate-report` para compilar en caliente y abrir inmediatamente el informe HTML corporativo consolidado en una nueva pestaña del navegador.
     - **Regla de visibilidad condicional:** El botón `#btnGenerateReportHtml` permanece oculto por defecto y únicamente se muestra de forma condicional el mismo día de la fecha de PaP (`Fecha PaP` en `dashboards/release-kpis/releases-data.js`) y al día siguiente (día PaP + 1), manteniendo la consola limpia y focalizada durante el resto del ciclo mensual.
   - Persistencia de fechas acordadas (`fecha_prevista`) editadas en la mesa, visibles con el distintivo `(Acordada Mesa)` tanto en la consola como en el informe ejecutivo generado.

### Opcionales / Fuera de alcance (Fase 2)

- Envío directo de mensajes a canales de Microsoft Teams desde la propia consola.
- Edición y persistencia de notas manuales internas de seguimiento por incidencia.

## Restricciones

- Implementación en HTML, CSS y JavaScript vanilla estático integrado con `dashboards/assets/topbar.js`, sin añadir frameworks ni dependencias externas pesadas.
- Reutilizar la capa de servicio común `converters/src/desk_service.py` para garantizar total paridad funcional entre el servidor local (`serve_app.py`) y el servicio de producción (`fastapi_remedy_router.py`).
- Excluir estrictamente únicamente el estado `Cerrado` en la vista activa de la Mesa de Release.
- Mantener el 100 % de compatibilidad y cero regresiones en la suite de tests existente del repositorio.

## Casos límite

- **Cuando la release seleccionada no tiene fichero JSON en `index.json`:** la consola debe mostrar un estado vacío claro indicando que la release no tiene datos locales todavía y ofrecer el botón directo **"⚡ Sincronizar Epsilon"** para inicializarla.
- **Cuando todas las incidencias de la release están en estado `Cerrado` (0 activas):** la consola debe mostrar `0` en los contadores activos y un mensaje informativo indicando que no hay incidencias pendientes de seguimiento en esa release.
- **Cuando se sube únicamente un CSV de Progresión o Regresión:** el backend debe conservar las pruebas existentes de la otra tipología en `{release}_grafana_pap.csv`, evitando el borrado accidental de métricas previamente consolidadas.
- **Cuando una incidencia no tiene Resumen IA en caché o falla la llamada a `/api/epsilon/resumen`:** la consola debe mostrar igualmente todos los datos base de la incidencia, informar del estado/error de forma clara y mantener disponible el botón de reintento sin bloquear el resto de la interfaz.
- **Cuando hay una petición en curso ("Sincronizar Epsilon", "Cargar Argos" o "Actualizar Informe HTML"):** los botones correspondientes deben deshabilitarse mostrando estado de carga hasta finalizar la operación, evitando peticiones duplicadas concurrentes.

## Definición de terminado

- La consola `dashboards/release-desk/` es accesible desde `dashboards/assets/topbar.js` y permite seleccionar cualquier release disponible.
- Ninguna incidencia con `Estatus` igual a `Cerrado` aparece en la tabla ni en los contadores activos de la consola.
- Al seleccionar una incidencia se muestra su ficha de seguimiento con los datos de Resumen IA, el botón **"Generar / Refrescar Resumen IA"** invoca `/api/epsilon/resumen` y **"Copiar seguimiento"** copia el texto formateado al portapapeles.
- Al pulsar **"⚡ Sincronizar Epsilon"** se invoca `POST /api/sync-postmortem` con la release activa y se recarga la consola sin modificar `massive-incidents` ni `high_priority_notifications.json`.
- El modal **"📊 Cargar Argos PaP"** permite arrastrar o seleccionar archivos CSV de Grafana, llama a `POST /api/release-desk/upload-argos`, consolida los datos y genera el informe HTML corporativo.
- El botón unificado **"🌐 Informe Ejecutivo PaP"** llama a `POST /api/release-desk/generate-report`, compila el informe en tiempo real tanto en local como en producción VPS y lo abre en una nueva pestaña del navegador, mostrándose condicionalmente solo el día de la fecha de PaP y al día siguiente.
- Existen pruebas automatizadas que cubren los endpoints de subida, generación y los componentes de UI, con la suite completa aprobada al 100%.
