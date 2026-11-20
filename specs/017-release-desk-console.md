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
   - Botón **"⚡ Sincronizar MonTMC"** que invoque `POST /api/sync-postmortem` para la release seleccionada y recargue automáticamente los datos de la consola al completar.
   - Botón **"Copiar seguimiento"** en la ficha de detalle que copie al portapapeles un texto estructurado listo para pegar en Teams o correo (incluyendo ID, release, estado, grupo soporte/resolutor, responsable y Resumen IA).

### Opcionales / Fuera de alcance (Fase 2)

- Envío directo de mensajes a canales de Microsoft Teams desde la propia consola.
- Edición y persistencia de notas manuales internas de seguimiento por incidencia.

## Restricciones

- Implementación en HTML, CSS y JavaScript vanilla estático integrado con `dashboards/assets/topbar.js`, sin añadir frameworks ni dependencias externas nuevas.
- Reutilizar exclusivamente los endpoints existentes (`/data/output/index.json`, `POST /api/sync-postmortem` y `POST /api/epsilon/resumen`), sin modificar los datasets de `massive-incidents` ni `data/output/high_priority_notifications.json`.
- Excluir estrictamente únicamente el estado `Cerrado` en la vista activa de la Mesa de Release.
- Mantener el 100 % de compatibilidad y cero regresiones en la suite de tests existente del repositorio.

## Casos límite

- **Cuando la release seleccionada no tiene fichero JSON en `index.json`:** la consola debe mostrar un estado vacío claro indicando que la release no tiene datos locales todavía y ofrecer el botón directo **"⚡ Sincronizar MonTMC"** para inicializarla.
- **Cuando todas las incidencias de la release están en estado `Cerrado` (0 activas):** la consola debe mostrar `0` en los contadores activos y un mensaje informativo indicando que no hay incidencias pendientes de seguimiento en esa release.
- **Cuando una incidencia no tiene Resumen IA en caché o falla la llamada a `/api/epsilon/resumen`:** la consola debe mostrar igualmente todos los datos base de la incidencia, informar del estado/error de forma clara y mantener disponible el botón de reintento sin bloquear el resto de la interfaz.
- **Cuando hay una petición en curso ("Sincronizar MonTMC" o "Generar / Refrescar Resumen IA"):** el botón pulsado debe deshabilitarse mostrando estado de carga hasta finalizar la operación, evitando peticiones duplicadas concurrentes.

## Definición de terminado

- La consola `dashboards/release-desk/` es accesible desde `dashboards/assets/topbar.js` y permite seleccionar cualquier release disponible.
- Ninguna incidencia con `Estatus` igual a `Cerrado` aparece en la tabla ni en los contadores activos de la consola.
- Al seleccionar una incidencia se muestra su ficha de seguimiento con los datos de Resumen IA, el botón **"Generar / Refrescar Resumen IA"** invoca `/api/epsilon/resumen` y **"Copiar seguimiento"** copia el texto formateado al portapapeles.
- Al pulsar **"⚡ Sincronizar MonTMC"** se invoca `POST /api/sync-postmortem` con la release activa y se recarga la consola sin modificar `massive-incidents` ni `high_priority_notifications.json`.
- Existen pruebas automatizadas que verifican el nuevo enlace en `topbar.js`, el filtrado estricto (`!= Cerrado`) y la estructura de la nueva consola, y toda la suite existente del repositorio pasa sin regresiones.
