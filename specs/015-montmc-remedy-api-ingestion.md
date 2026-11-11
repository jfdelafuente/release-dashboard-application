# Especificación: Ingesta Automatizada de Incidencias Remedy vía API MonTMC y Enriquecimiento On-Demand de Worklogs

## Objetivo

Actualmente, la actualización del dataset de incidencias masivas y de la Consola de Triaje de Emergencias requiere que los operadores descarguen manualmente un archivo CSV/Excel desde las herramientas corporativas y lo suban a la plataforma. Este proceso manual introduce fricción operativa, desfase temporal de los datos durante guardias críticas y dependencia de acciones humanas repetitivas.

Esta función resuelve el problema integrando directamente la plataforma con las APIs corporativas de MonTMC / Epsilon (`https://soptmc.si.orange.es`), permitiendo sincronizar incidencias masivas de forma automática o mediante un solo clic, y enriquecer el detalle de las incidencias con las anotaciones técnicas de los resolutores (worklogs de Remedy) bajo demanda. El impacto es una reducción a cero del tiempo de espera para disponer de datos actualizados en el triaje de emergencias y una visibilidad inmediata de las acciones técnicas en curso.

## Requisitos

### Requisitos Obligatorios

1. **Modo Híbrido de Sincronización:**
   - La sincronización debe poder dispararse bajo demanda desde un botón interactivo en la cabecera de la Consola de Triaje ("Sincronizar Remedy").
   - La sincronización debe poder ejecutarse de forma programada y desatendida mediante una tarea periódica en el servidor (cron) o comando CLI.
2. **Upsert Incremental No Destructivo:**
   - La consulta a `GET /MonTMC/api/epsilon/masivas` debe usar por defecto una ventana deslizante de 3 a 7 días para optimizar la velocidad y el tráfico.
   - Para cada incidencia obtenida de la API:
     - Si ya existe en el dataset masivo semestral local (`data/output/*-massive.json`), debe actualizar su estado, grupo asignado, grupo resolutor, fecha de modificación y atributos relevantes (Update).
     - Si no existe, debe insertarse en el dataset (Insert).
     - Si una incidencia del dataset local no figura en la respuesta de la API (por tener fecha anterior a la ventana solicitada), debe conservarse íntegra e inalterada para mantener el histórico de los 600+ tickets semestrales.
   - Debe permitirse forzar una ventana temporal amplia (ej. `--dias 135`) mediante parámetro CLI o configuración cuando se requiera una reconciliación completa del semestre.
3. **Mapeo y Normalización Canónica de Campos:**
   - Los registros de MonTMC deben transformarse fielmente al esquema JSON estándar del proyecto:
     - `idRemedy` $\rightarrow$ `"ID de incidencia"`
     - `prioridad` / `prioridadP` $\rightarrow$ `"Prioridad"` (mapeo homogéneo de niveles P1 a P4)
     - `resumen` $\rightarrow$ `"Descripción"`
     - `estadoDesc` $\rightarrow$ `"Estatus"` (normalización a capitalización estándar: 'Asignado', 'Resuelto', etc.)
     - `fechaCreacion` $\rightarrow$ `"Fecha de envío"` (conversión de formato ISO-8601 al formato de visualización)
     - `grupoAsignado` $\rightarrow$ `"Grupo asignado"`
     - `fechaResolucion` $\rightarrow$ `"Fecha de última resolución"`
     - `grupoResolutor` $\rightarrow$ `"Grupo Resolutor"`
     - `urgencia` $\rightarrow$ `"Urgencia"`
     - `producto` o `"Masiva"` $\rightarrow$ `"Impacto"`
     - `peticionarioNombre` $\rightarrow$ `"Grupo Remitente"`
4. **Enriquecimiento On-Demand de Worklogs y Detalle Técnico (Lazy Loading):**
   - El endpoint `GET /MonTMC/api/eps/remedyG/{idRemedy}` solo debe consultarse cuando el usuario abre la ficha de la incidencia en la Consola de Triaje o solicita explícitamente ver el detalle técnico.
   - Las respuestas de `remedyG` deben almacenarse en una caché local temporal con tiempo de vida (TTL) para evitar peticiones redundantes sobre la misma incidencia durante la sesión.
   - La interfaz de la Consola de Triaje debe presentar una sección dedicada ("Worklog / Notas Remedy") que liste cronológicamente las anotaciones de los técnicos resolutores, indicando fecha, autor y texto de la nota.
5. **Configuración del Usuario de Conexión:**
   - El parámetro `usuario` enviado a las peticiones MonTMC debe obtenerse de la variable de entorno `MON_TMC_USER` o de la configuración del servicio, utilizando `'jdelat'` como valor predeterminado si no se especifica otro.
6. **Encadenamiento Automático con Auditoría y Notificaciones:**
   - Tras completar una sincronización con éxito, el sistema debe registrar el evento en el log de auditoría de ingestas (`data/output/ingestion_summary.json` y `ingestion.log`) indicando el origen `montmc_api` y el balance de registros (nuevas, actualizadas, sin cambios).
   - Debe recalcularse automáticamente la matriz de alertas de alta prioridad (`evaluate_incident_notifications.py` $\rightarrow$ `data/output/high_priority_notifications.json`) para reflejar de inmediato los escalados y resoluciones recientes.
7. **Preservación del Mecanismo CSV (Fallback):**
   - La carga manual de archivos CSV/Excel a través del portal y endpoints existentes debe seguir operativa como vía de contingencia y no verse afectada por la nueva integración.

---

## Restricciones

1. **Librería estándar de Python:** El cliente MonTMC y los scripts de sincronización deben desarrollarse utilizando exclusivamente librerías estándar de Python 3 (`urllib.request`, `json`, `pathlib`, `datetime`, `dataclasses`, `os`), sin incorporar paquetes externos adicionales en `requirements.txt`.
2. **Prohibición de escaneos masivos a `remedyG`:** Está terminantemente prohibido invocar el endpoint `remedyG/{idRemedy}` en bucles indiscriminados o para el conjunto completo de incidencias históricas. Su consumo debe ser estrictamente individual y bajo demanda.
3. **Compatibilidad total de tests:** Todos los tests preexistentes del repositorio (`converters/tests/`) deben continuar ejecutándose y aprobándose sin regresiones.
4. **Ejecución en Sandbox (Sandboxed First):** Las suites de pruebas unitarias e integración no deben depender de conectividad real a la intranet ni a `soptmc.si.orange.es`, debiendo emplear fixtures pregrabados o emulaciones (`unittest.mock`) para garantizar su ejecución en entornos de testing aislados.

---

## Casos límite

1. **Cuando la API MonTMC no responde, produce timeout o devuelve un error HTTP 5xx:** El sistema no debe modificar ni corromper el dataset masivo existente en disco, debe registrar una advertencia en la auditoría de ingesta, retornar una respuesta JSON de error controlada (HTTP 502/504) y mostrar un aviso no bloqueante al usuario en la interfaz indicando la falta de conectividad temporal.
2. **Cuando la API MonTMC devuelve una lista de incidencias vacía (`incidencias: []`):** El sistema debe interpretar la respuesta como una anomalía de la ventana o del servicio, abortar la escritura para no vaciar el dataset local y generar una alerta en el log.
3. **Cuando se consulta el detalle técnico de una incidencia inexistente en Remedy (`codigoResp != 0`):** El endpoint backend debe responder con HTTP 404 estructurado y la interfaz debe informar amigablemente que no existen notas registradas en Remedy para ese identificador, sin bloquear el resto del modal.
4. **Cuando una incidencia contiene campos nulos o con formatos inesperados:** El normalizador debe asignar valores por defecto seguros (`None`, `""` o fechas estándar) sin generar excepciones que interrumpan el procesamiento del lote.
5. **Cuando ocurren dos sincronizaciones simultáneas (concurrencia):** El proceso de persistencia en disco debe emplear un mecanismo de guardado atómico (escritura en fichero temporal `.tmp` y reemplazo atómico) para prevenir corrupción de datos en concurrencia entre cron y botón web.

---

## Definición de terminado

1. **Cliente MonTMC implementado y probado:** Existe el módulo `converters/src/montmc_client.py` con métodos para consultar `fetch_masivas` y `fetch_remedy_detail`, junto con la suite `converters/tests/unit/test_montmc_client.py` alcanzando 100% de éxito con mocks.
2. **CLI de Sincronización Funcional:** Existe `converters/cli/sync_montmc_incidents.py` ejecutable por terminal con parámetros `--dias`, `--usuario`, `--dry-run` y `--output`, validado con tests en `converters/tests/unit/test_sync_montmc.py` que verifiquen el algoritmo de upsert no destructivo.
3. **Endpoints Backend en Funcionamiento:** El servidor `serve_app.py` expone `POST /api/sync-remedy` (disparo de sincronización) y `GET /api/remedy/detail/{idRemedy}` (consulta con caché local temporal), respondiendo con esquemas válidos y códigos HTTP esperados.
4. **Interfaz de Usuario Operativa:**
   - La Consola de Triaje de Emergencias incluye el botón funcional de sincronización con indicador de carga y feedback tras ejecución.
   - El modal de incidencia en la Consola de Triaje incluye la pestaña/bloque de "Worklog / Notas Remedy" que carga perezosamente los eventos de `remedyG`.
5. **Auditoría e Integración de Notificaciones Verificada:** Tras una sincronización de prueba, `data/output/ingestion_summary.json` y `data/output/high_priority_notifications.json` se actualizan automáticamente reflejando la fuente `montmc_api`.
6. **No Regresión:** Se ejecuta `python -m pytest converters/tests` en local y el 100% de las pruebas preexistentes y nuevas resultan aprobadas (verdes).
7. **Documentación Actualizada:** Se documenta la configuración del servicio, variables de entorno y nuevos endpoints en `docs/03-arquitectura-y-datos/dashboards-api.md`.
