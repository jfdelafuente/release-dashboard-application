# Especificación: Sincronización Online del Dashboard Postmortem vía API MonTMC Release

## Objetivo

Actualmente, el dashboard `postmortem` depende de cargas manuales de ficheros Excel/CSV para reflejar el estado de las incidencias de release, mientras que el flujo de `massive-incident` ya dispone de consulta online contra MonTMC. Esta dependencia manual introduce desfase temporal en el seguimiento de incidencias de release durante las ventanas de seguimiento y obliga a repetir exportaciones manuales.

Esta función equipara el dashboard `postmortem` con la capacidad de actualización online existente para `massive-incident`, integrándose con el endpoint corporativo `GET https://soptmc.si.orange.es/MonTMC/api/epsilon/release?usuario=<usuario>` para mantener actualizadas las incidencias de release bajo demanda o de forma programada, sin alterar el histórico previo ni mezclar los flujos de incidencias masivas.

## Requisitos

### Obligatorios

1. **Modo Híbrido de Sincronización:**
   - El dashboard `postmortem` debe incluir un botón interactivo en su cabecera/barra de acciones para disparar la sincronización online bajo demanda.
   - Debe existir un endpoint backend dedicado que ejecute la sincronización para `postmortem` cuando sea invocado desde la interfaz web.
   - Debe existir un comando CLI (apto para ejecución manual y programación periódica/cron en servidor) que ejecute exactamente la misma lógica de sincronización para `postmortem`.

2. **Upsert Incremental No Destructivo:**
   - La consulta al endpoint `GET /MonTMC/api/epsilon/release?usuario=<MON_TMC_USER>` debe obtener las incidencias activas de release devueltas por MonTMC.
   - Para cada incidencia devuelta en `incidencias`:
     - Si ya existe en el dataset local de `postmortem` (por `idRemedy`), debe actualizar sus atributos relevantes (estado, grupo asignado, grupo resolutor, prioridad, urgencia, fecha de resolución, fecha de modificación y demás campos mapeados).
     - Si no existe, debe insertarse como nueva incidencia en el dataset de `postmortem`.
   - Si una incidencia ya presente en el dataset local de `postmortem` no figura en la respuesta actual de la API (por ejemplo, incidencias ya resueltas/cerradas o cargadas históricamente por Excel/CSV), debe conservarse íntegra e inalterada.

3. **Mapeo y Normalización Canónica de Campos:**
   - Los registros devueltos por `/MonTMC/api/epsilon/release` deben transformarse de forma homogénea al esquema esperado por el dashboard `postmortem` a partir de campos como `idRemedy`, `resumen`, `estadoDesc`, `prioridad` / `prioridadP`, `urgencia`, `producto`, `grupoAsignado`, `grupoResolutor`, `peticionarioNombre`, `fechaCreacion`, `fechaUltimaModificacion` y `fechaResolucion`.

4. **Configuración del Usuario de Conexión:**
   - El parámetro `usuario` de la petición a MonTMC debe obtenerse de la variable de entorno `MON_TMC_USER` (o configuración equivalente del servicio), usando `'jdelat'` como valor predeterminado si no se especifica otro.

5. **Auditoría de Ingestas y Fallback Manual:**
   - Cada sincronización completada con éxito debe registrar el evento en la auditoría de ingestas (`data/output/ingestion_summary.json` e `ingestion.log`) indicando su origen y el balance de registros (nuevas, actualizadas y sin cambios).
   - La carga manual de ficheros Excel/CSV existente para `postmortem` debe seguir operativa como mecanismo de contingencia (fallback).

### Opcionales / Fuera de alcance (Fase 2 o flujos separados)

- No mezclar ni modificar `data/output/high_priority_notifications.json` desde esta sincronización: dichas alertas pertenecen al flujo de incidencias masivas, mientras que `release` incluye incidencias de release que pueden ser o no masivas.
- Enriquecimiento on-demand de worklogs (`remedyG/{idRemedy}`) en la vista detalle de `postmortem` (pospuesto fuera del alcance de esta especificación).

## Restricciones

- El cliente HTTP y la lógica de sincronización en Python deben implementarse utilizando exclusivamente la librería estándar de Python 3 (sin añadir nuevas dependencias externas).
- El usuario de consulta a MonTMC debe ser configurable mediante `MON_TMC_USER`, con `'jdelat'` por defecto.
- Aislamiento de datos: la sincronización de `postmortem` no debe modificar ni contaminar los datasets de `massive-incidents` ni `data/output/high_priority_notifications.json`.
- Las pruebas automatizadas (unitarias y de integración) deben ejecutarse 100 % offline mediante mocks/fixtures (sin conectividad real a `soptmc.si.orange.es`) y toda la suite existente del repositorio debe seguir pasando sin regresiones.

## Casos límite

- **Cuando MonTMC devuelve timeout, error de red, código HTTP >= 400 o `success: false`:** el sistema debe abortar la actualización sin sobrescribir ni corromper los datos locales de `postmortem` y devolver/mostrar un mensaje de error claro tanto en la UI como en el CLI.
- **Cuando la API responde `success: true` con `total: 0` e `incidencias: []`:** el sistema debe conservar intactos los datos locales existentes de `postmortem` y registrar `0` nuevas y `0` actualizadas en la auditoría.
- **Cuando campos opcionales del JSON de `release` llegan a `null` (`grupoResolutor`, `fechaResolucion`, `masiva`, `detalle`, etc.):** el normalizador debe procesarlos sin fallar, aplicando valores vacíos o `null` coherentes con el esquema de `postmortem`.
- **Cuando el usuario pulsa el botón de sincronización en `postmortem` mientras ya hay una petición en curso:** la interfaz debe deshabilitar el botón mostrando el estado `"Sincronizando..."` hasta que finalice la operación, evitando llamadas duplicadas concurrentes.

## Definición de terminado

- Al pulsar el botón de sincronización en el dashboard `postmortem` (con respuesta de MonTMC mockeada o real), se completa la llamada al endpoint backend, se actualiza la vista con las incidencias de release y se muestra el resumen de registros nuevos/actualizados.
- Al ejecutar el comando CLI/cron de sincronización de `postmortem`, se realiza el upsert incremental no destructivo sobre el dataset local conservando las incidencias previas no incluidas en la respuesta y se añade la entrada correspondiente en `data/output/ingestion_summary.json` e `ingestion.log`.
- Tras ejecutar la sincronización de `postmortem`, los datasets de `massive-incidents` y el fichero `data/output/high_priority_notifications.json` permanecen exactamente sin cambios.
- Las pruebas unitarias y de integración nuevas para la sincronización `release` → `postmortem` (incluyendo los casos límite de error, lista vacía y campos `null`) y toda la suite existente del repositorio pasan al 100 % sin regresiones.
