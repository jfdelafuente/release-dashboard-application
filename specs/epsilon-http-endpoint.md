# Especificación: Endpoints HTTP de Epsilon Resumen IA

## Objetivo
Exponer el motor de generación, validación estricta y calibración de resúmenes técnicos de incidencias IT (Epsilon Resumen IA) como servicio HTTP integrado en `serve_app.py` (puerto 8080). El servicio debe permitir la generación bajo demanda vía `POST /api/epsilon/generate` (recibiendo el JSON en bruto de una incidencia Remedy o una petición encapsulada) y actuar como contingencia y fallback inteligente en `GET /api/epsilon/resumenIA/{codigo}` cuando el servicio corporativo externo SOPTMC no esté accesible o falle, garantizando la trazabilidad temporal del dato para evitar inconsistencias de estado (`LIFECYCLE_STATUS_MISMATCH`) entre los volcados locales y Remedy en vivo.

## Requisitos

### Requisitos Obligatorios
1. **Desacoplamiento del Motor a Servicio Reutilizable (`converters/src/epsilon_service.py`)**:
   - Extraer la lógica de carga de variables de entorno (`load_project_env`), System Prompt oficial de Epsilon (`EPSILON_SYSTEM_PROMPT`), clientes de proveedores LLM (Anthropic LiteLLM MasOrange, OpenAI, Gemini y Mock offline) y validación Pydantic (`EpsilonResumenModel`) desde `scripts/test_epsilon_prompt.py`.
   - El nuevo módulo de servicio debe ofrecer una interfaz programática limpia tipada:
     `generate_epsilon_summary(incident_data: dict, provider: Optional[str] = None, model: Optional[str] = None, mock: bool = False) -> Tuple[bool, dict, dict]`
     donde devuelve `(is_valid, data_or_errors, meta)`.
   - El CLI `scripts/test_epsilon_prompt.py` debe refactorizarse para importar y delegar en `converters/src/epsilon_service.py` sin alterar ninguna de sus opciones de línea de comandos ni romper sus tests existentes.

2. **Endpoint de Generación `POST /api/epsilon/generate`**:
   - Aceptar formato dual en el cuerpo de la petición:
     - Formato A (Directo): JSON íntegro con los datos del ticket Remedy.
     - Formato B (Wrapper): `{"incident_data": { ... }, "mock": false, "model": "..."}`.
   - Si `mock: true` o si la variable de entorno `MOCK=true`, generar el resumen simulado sin invocar al proveedor LLM ni consumir tokens.
   - Ejecutar la llamada al LLM, validar estrictamente contra el esquema `EpsilonResumenModel` (límites de palabras, orden cronológico de hitos y prefijos estandarizados de bloqueos).
   - Códigos de respuesta HTTP:
     - `200 OK`: Generación y validación exitosa. Devuelve JSON estructurado con `{"success": true, "data": { ... }, "meta": { ... }}`.
     - `400 Bad Request`: Si el cuerpo de la petición está vacío, no es JSON válido o carece de datos mínimos de la incidencia.
     - `422 Unprocessable Entity`: Si el LLM responde pero el JSON no supera la validación estricta de Pydantic, devolviendo el detalle estructurado de campos fallidos.
     - `502 Bad Gateway`: Si ocurre un error de conexión, autenticación, timeout o error 4xx/5xx del proveedor LLM / proxy LiteLLM.
   - Si los datos de la incidencia contienen un identificador reconocible (ej. `codigo`, `id_incidencia`, `incident_number` con prefijo `INC`), guardar automáticamente el resultado generado en `data/.epsilon_cache/{codigo}.json` y en la caché en memoria `EPSILON_CACHE`.
   - Soporte CORS completo (`OPTIONS` y cabeceras `Access-Control-Allow-Origin: *`).

3. **Fallback Inteligente y Detección de Estado en `GET /api/epsilon/resumenIA/{codigo}`**:
   - Mantener la jerarquía de consulta:
     1. Comprobar caché en memoria (`EPSILON_CACHE`) si no se solicita `no-cache` o `force=true`.
     2. Consultar el servicio corporativo de SOPTMC (`https://soptmc.si.orange.es/MonTMC/api/epsilon/resumenIA/{codigo}`).
     3. Si SOPTMC responde `200 OK`, devolver la respuesta y guardarla en caché.
     4. Si SOPTMC falla (timeout, error de red, 502/503 o 404):
        - Buscar si existe snapshot previo en `data/.epsilon_cache/{codigo}.json`.
        - Si no existe snapshot en disco, buscar los datos técnicos del ticket en los archivos locales `data/output/*-massive.json` y `data/output/*-postmortem.json`.
        - Si se localiza la incidencia en los volcados locales, invocar automáticamente al motor LLM (`generate_epsilon_summary`), persistir el resultado en `data/.epsilon_cache/{codigo}.json` y responder `200 OK` incorporando metadatos de trazabilidad:
          `"meta": {"source": "local_dump_fallback", "dump_file": "...", "dump_timestamp": "...", "is_stale_warning": bool}`.
        - Si no se localiza en los volcados locales, responder `502 Bad Gateway` informando de que la incidencia no está disponible en vivo ni en los volcados locales.

4. **Salvaguardas de Frescura e Invalidación de Caché**:
   - Si se envía la cabecera `Cache-Control: no-cache` o el parámetro de consulta `?force=true`, ignorar la caché en memoria y la caché en disco en `data/.epsilon_cache/{codigo}.json`, forzando la consulta en vivo o la regeneración.
   - En `serve_app.py`, cuando se procese una subida exitosa de CSV en `POST /api/upload`, invalidar la caché en memoria (`EPSILON_CACHE.clear()`) para evitar servir resúmenes con estados desactualizados de tickets recién refrescados.

### Requisitos Opcionales (Fase 2)
1. Integración en el dashboard `dashboards/assets/resumen-ia.js` de un botón explícito de *"Refrescar con IA"* cuando el resumen provenga de un volcado local con advertencia de obsolescencia.
2. Endpoint por lotes `POST /api/epsilon/batch-generate` para precalcular en segundo plano los resúmenes de todas las incidencias P1/P2 recién ingresadas.

## Restricciones
1. **Pila Tecnológica**: Implementación nativa en Python sin añadir frameworks pesados externos al servidor principal `serve_app.py` (mantener el servidor base `http.server` existente en puerto 8080).
2. **Entorno MasOrange**: Preservar y dar prioridad a las credenciales configuradas en `.env`:
   - `ANTHROPIC_AUTH_TOKEN`
   - `ANTHROPIC_BASE_URL` (`https://llm.tools.cloud.masorange.es`)
   - `ANTHROPIC_MODEL` / `ANTHROPIC_DEFAULT_SONNET_MODEL`
   - Soporte opcional para OpenAI (`OPENAI_API_KEY`, `OPENAI_MODEL`).
3. **Integridad de Pruebas**: No degradar la suite de pruebas unitarias existente (`pytest converters/tests/`). Todo nuevo código debe disponer de tests unitarios que se ejecuten automáticamente en modo sandboxed (usando mocks/fixtures).
4. **Respeto a Reglas de Dominio**: El System Prompt y la validación Pydantic deben preservar estrictamente las reglas anti-alucinación, formato de hitos adaptativos (`[DD/MM/YYYY HH:mm]: ` / `[S/F]`), prefijos de bloqueos y límites de palabras.

## Casos Límite
1. **Cuando el cuerpo en `POST /api/epsilon/generate` está vacío o mal formado**: El sistema debe responder HTTP 400 con un JSON `{"success": false, "error": "Cuerpo de solicitud vacío o JSON inválido"}`.
2. **Cuando los datos de la incidencia carecen de campos mínimos**: El sistema debe responder HTTP 400 con `{"success": false, "error": "Datos de incidencia insuficientes para generar resumen"}`.
3. **Cuando el LLM responde un JSON que no cumple el esquema Pydantic (ej. excede límite de palabras o formato de hito inválido)**: El sistema debe responder HTTP 422 con `{"success": false, "error": "Error de validación de esquema Epsilon", "validation_errors": [ ... ]}`.
4. **Cuando el proveedor LLM o proxy LiteLLM devuelve error HTTP (400, 401, 429, 500) o timeout**: El sistema debe capturar la excepción y responder HTTP 502 con `{"success": false, "error": "Fallo en el servicio LLM: <detalle>"}`.
5. **Cuando se solicita `GET /api/epsilon/resumenIA/{codigo}` con un código inexistente tanto en SOPTMC como en los ficheros locales**: El sistema debe responder HTTP 502 (o 404) con `{"success": false, "error": "Incidencia <codigo> no encontrada ni en SOPTMC ni en los datos locales"}`.
6. **Cuando se incluye `?force=true` o `Cache-Control: no-cache`**: El sistema debe omitir la lectura de `EPSILON_CACHE` y de `data/.epsilon_cache/{codigo}.json` y ejecutar la llamada en vivo o regeneración fresca.
7. **Cuando se pasa `mock: true` en el JSON de POST**: El sistema debe generar la respuesta simulada inmediatamente sin realizar peticiones de red ni requerir tokens de autenticación.

## Definición de Terminado
1. **Módulo de Servicio**: Existe `converters/src/epsilon_service.py` que contiene `generate_epsilon_summary()`, `EpsilonResumenModel`, `EPSILON_SYSTEM_PROMPT` y clientes LLM con fallback a `urllib.request`.
2. **Compatibilidad del CLI**: `scripts/test_epsilon_prompt.py` utiliza `converters/src/epsilon_service.py` y pasa el 100 % de los tests en `converters/tests/unit/test_epsilon_prompt_cli.py`.
3. **Nuevos Tests Unitarios**: Existe `converters/tests/unit/test_epsilon_service.py` y `converters/tests/unit/test_epsilon_endpoints.py` que verifican unitariamente las funciones del servicio y los handlers de `serve_app.py` sin llamadas de red reales.
4. **Endpoints en `serve_app.py`**:
   - `POST /api/epsilon/generate` implementado, aceptando tanto formato directo como wrapper, devolviendo 200/400/422/502 según corresponda y soportando CORS.
   - `GET /api/epsilon/resumenIA/{codigo}` ampliado con fallback de auto-generación desde `data/output/*` cuando SOPTMC no responde, con metadatos de trazabilidad temporal y soporte de `?force=true`.
   - `POST /api/upload` invalida la caché en memoria al cargar un nuevo archivo CSV.
5. **Verificación Práctica**: Se comprueba con comandos HTTP reales (`Invoke-RestMethod` o `curl`) contra `serve_app.py` que:
   - `POST /api/epsilon/generate` con `--mock` o payload de prueba responde 200 OK con el esquema esperado.
   - `GET /api/epsilon/resumenIA/{codigo}` responde adecuadamente con fallback local.
6. **Documentación Actualizada**: Se actualiza `docs/03-arquitectura-y-datos/dashboards-api.md` reflejando el nuevo endpoint `POST /api/epsilon/generate` y los metadatos de frescura en `GET /api/epsilon/resumenIA/{codigo}`.
