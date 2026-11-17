# Catálogo de APIs e Integraciones de Dashboards

Este documento describe todas las APIs, rutas y servicios backend que consumen los distintos dashboards de la plataforma:

- Los dashboards estáticos bajo [`dashboards/`](../../dashboards/):
  - **Portal Hub** (`dashboards/portal/`)
  - **Incidencias Masivas** (`dashboards/massive-incidents/`)
  - **Postmortem / Release** (`dashboards/postmortem/`)
  - **KPIs de Release** (`dashboards/release-kpis/`)
  - **Reportes de Incidencias** (`dashboards/reportes-incidencias/`)
  - **Catálogo de Agentes IA y Skills** (`dashboards/agents-catalog/`)
  - **Informes Específicos** (`dashboards/informes/incidencias-pdtes-r9-2026/`)
- La aplicación Next.js de **Gestión de Problemas** bajo `/problemas` (alojada en el repositorio hermano `gestion-problemas-dashboard`).
- Los componentes transversales de cliente: [`topbar.js`](../../dashboards/assets/topbar.js) (sondeo de salud) y [`resumen-ia.js`](../../dashboards/assets/resumen-ia.js) (Epsilon IA).

---

## 🏛️ Arquitectura de Comunicación

```mermaid
flowchart TD
    subgraph Frontend["Frontends y Dashboards"]
        P["Portal Hub<br/>(dashboards/portal)"]
        MI["Incidencias Masivas<br/>(dashboards/massive-incidents)"]
        PM["Postmortem / Release<br/>(dashboards/postmortem)"]
        RK["KPIs de Release<br/>(dashboards/release-kpis)"]
        RI["Reportes de Incidencias<br/>(dashboards/reportes-incidencias)"]
        AC["Catálogo de Agentes IA<br/>(dashboards/agents-catalog)"]
        ETC["Consola de Triaje IT<br/>(emergency-triage-console)"]
        GP["Gestión de Problemas<br/>(Next.js /problemas)"]
        TB["Barra Superior Unificada<br/>(topbar.js)"]
    end

    subgraph Backend["Capa de Servidor (serve_app.py :8080 / FastAPI :8000 / Nginx :8081)"]
        UPL["POST /api/upload"]
        PPT["GET /api/reports/postmortem/{rel}"]
        EXEC["API Informe Ejecutivo<br/>/api/reports/executive-incident/*"]
        REP_CRUD["API CRUD Reportes<br/>/api/reports/*"]
        EPS["GET /api/epsilon/resumenIA/{cod}"]
        SYNC["POST /api/sync-remedy"]
        REMD["GET /api/remedy/detail/{id}"]
        HLTH["GET /api/health y /healthz"]
        JIRA["GET /api/dashboard"]
        DATA["GET /data/output/*"]
        AGCAT["GET /api/agents-catalog"]
    end

    subgraph StorageAndEngines["Almacenamiento y Motores de Procesamiento"]
        CONV["Conversores Python<br/>(upload_csv / convert_incidents / convert_postmortems)"]
        STORAGE["Almacenamiento Desacoplado<br/>/infocodes/var/storage/release-dashboard/"]
        PPT_ENG["Motor PPTX Postmortem<br/>(converters/src/report_generator)"]
        EXEC_ENG["Motor Informe Ejecutivo PPTX<br/>(cso-incident-masivas-report / backend)"]
        EPS_SVC["Motor Interno Epsilon IA<br/>(epsilon_service.py + LiteLLM MasOrange)"]
        TMC_SVC["MonTMC API Corporativa<br/>(soptmc.si.orange.es: remedyG + masivas)"]
        JIRA_SVC["Jira API Corporativa"]
    end

    %% Conexiones Frontend -> Backend
    P --> DATA
    P --> EPS
    MI --> DATA
    MI --> UPL
    MI --> EPS
    PM --> DATA
    PM --> UPL
    PM --> PPT
    PM --> EPS
    RK --> PPT
    RI --> REP_CRUD
    RI --> HLTH
    AC --> AGCAT
    AC --> DATA
    ETC --> DATA
    ETC --> EPS
    ETC --> SYNC
    ETC --> REMD
    GP --> JIRA
    GP --> EXEC
    TB --> HLTH

    %% Conexiones Backend -> Motores / Almacenamiento
    UPL --> CONV
    CONV --> STORAGE
    DATA --> STORAGE
    PPT --> PPT_ENG
    PPT_ENG --> STORAGE
    EXEC --> EXEC_ENG
    EXEC_ENG --> STORAGE
    EPS --> EPS_SVC
    EPS_SVC --> TMC_SVC
    EPS_SVC --> STORAGE
    SYNC --> TMC_SVC
    SYNC --> EPS_SVC
    SYNC --> STORAGE
    REMD --> TMC_SVC
    REMD --> STORAGE
    JIRA --> JIRA_SVC
```

---

## 📋 Matriz de Consumo por Dashboard

| Dashboard | Ruta Web | APIs que invoca |
| :--- | :--- | :--- |
| **Portal Hub** | `/dashboards/portal/` | `GET /data/output/index.json`<br/>`GET /api/epsilon/resumenIA/{codigo}` (buscador) |
| **Incidencias Masivas** | `/dashboards/massive-incidents/` | `POST /api/upload`<br/>`GET /api/epsilon/resumenIA/{codigo}`<br/>`GET /data/output/index.json`<br/>`GET /data/output/*-massive.json` |
| **Postmortem de Release** | `/dashboards/postmortem/` | `POST /api/upload`<br/>`GET /api/reports/postmortem/{release_name}`<br/>`GET /api/epsilon/resumenIA/{codigo}`<br/>`GET /data/output/index.json`<br/>`GET /data/output/*-postmortem.json` |
| **KPIs de Release** | `/dashboards/release-kpis/` | `GET /api/reports/postmortem/{release_name}`<br/>*Nota: datos base leídos de `releases-data.js`* |
| **Reportes de Incidencias** | `/dashboards/reportes-incidencias/` | `GET /api/reports`<br/>`POST /api/reports`<br/>`GET /api/reports/{id}`<br/>`PUT /api/reports/{id}`<br/>`DELETE /api/reports/{id}`<br/>`POST /api/reports/{id}/duplicate?new_week={week}`<br/>`GET /api/reports/{id}/export`<br/>`GET /api/reports/{id}/legacy-pptx`<br/>`GET /api/health` |
| **Catálogo de Agentes IA** | `/dashboards/agents-catalog/` | `GET /api/agents-catalog`<br/>`GET /data/output/agents_catalog.json` (fallback estático) |
| **Gestión de Problemas** | `/problemas` | `GET /api/dashboard` (Jira)<br/>`POST /api/reports/executive-incident`<br/>`GET /api/reports/executive-incident/{ref}/status`<br/>`GET /api/reports/executive-incident/{ref}`<br/>`GET /api/healthz` y `GET /api/readyz` |
| **Consola de Triaje y Emergencias IT (Cockpit)** | `/dashboards/emergency-triage-console/` | `GET /api/incident-manager/pending`<br/>`GET /api/incident-manager/emergency-cockpit`<br/>`GET /api/logs/ingestion`<br/>`POST /api/ingestion/retry-ia` (alias `/api/epsilon/retry`)<br/>`POST /api/sync-remedy`<br/>`GET /api/remedy/detail/{idRemedy}`<br/>`GET /data/output/high_priority_notifications.json`<br/>`GET /data/output/ingestion_audit_summary.json` |
| **Componentes Compartidos (Epsilon Modal)** | *Compartido en todos (`resumen-ia.js`)* | `GET /api/epsilon/resumenIA/{codigo}`<br/>`GET /api/remedy/detail/{idRemedy}` |
| **Barra Superior Unificada** | *Compartida en todos (`topbar.js`)* | `GET /api/health` (fallback a `GET /healthz`) |

---

## 🔌 Detalle de Endpoints

### 1. Ingesta y Subida de Archivos CSV

#### `POST /api/upload`

* **Invocado por**: Modales de subida de CSV en `massive-incidents` y `postmortem`.
- **Formato petición**: `multipart/form-data`
  - `file`: Archivo `.csv` con la exportación de incidencias de Remedy.
  - `type`: `"massive"` o `"postmortem"`.
  - `release_name`: Obligatorio si el tipo es `"postmortem"` (ej: `"2026R7"`).
- **Respuesta exitosa (`200 OK`)**:

  ```json
  {
    "success": true,
    "message": "Conversión completada",
    "output_file": "2026R7-postmortem.json"
  }
  ```

* **Procesamiento y almacenamiento**:
  - El archivo se deposita en el directorio de almacenamiento desacoplado:
    - **Producción**: `/infocodes/var/storage/release-dashboard/input/`
    - **Desarrollo**: `data/input/` (o ruta indicada por `RELEASE_DASHBOARD_STORAGE_DIR`).
  - Se invoca la función `run_upload()` de [`converters/cli/upload_csv.py`](../../converters/cli/upload_csv.py).
  - El conversor genera el JSON estructurado en `output/` y actualiza automáticamente `output/index.json`.

---

### 2. Generación y Descarga de Informes Postmortem (.pptx)

#### `GET /api/reports/postmortem/{release_name}`

* **Invocado por**: Botón *"Descargar informe PPT"* en `dashboards/postmortem/index.html` y botones de descarga directa en la tabla de `dashboards/release-kpis/app.js`.
- **Respuesta**: Stream binario con cabecera `Content-Type: application/vnd.openxmlformats-officedocument.presentationml.presentation` y descarga del fichero:
  `{release_name}-postmortem-report.pptx` (ej: `2026R7-postmortem-report.pptx`).
- **Ubicación de almacenamiento**:
  - **Producción**: `/infocodes/var/storage/release-dashboard/reports/{release_name}-postmortem-report.pptx`
  - **Desarrollo**: `data/reports/{release_name}-postmortem-report.pptx`
- **Optimización de Caché**: Si el informe ya existe y su fecha de modificación es igual o posterior a la de `releases-data.js`, se sirve inmediatamente desde disco sin regenerar las gráficas con Plotly/Kaleido.

---

### 3. Informes Ejecutivos de Incidencias (PowerPoint Corporativo Orange)

#### `POST /api/reports/executive-incident` (o `/api/v1/reports/executive-incident`)

* **Invocado por**: Modal de informe ejecutivo (`ExecutiveReportModal.tsx`) en el dashboard de Gestión de Problemas.
- **Formato petición**: `application/json`

  ```json
  {
    "incidentRef": "2606S77393",
    "title": "Corte pasarela de pagos",
    "url": "https://confluence.si.orange.es/display/...",
    "htmlContent": "...",
    "mode": "confluence"
  }
  ```

* **Respuesta (`200 OK`)**:

  ```json
  {
    "success": true,
    "incidentRef": "2606S77393",
    "filename": "RESUMEN_EJECUTIVO_2606S77393.pptx",
    "downloadUrl": "/api/reports/executive-incident/2606S77393",
    "generatedAt": "2026-10-20T10:30:00Z",
    "sizeBytes": 145820,
    "slideCount": 3
  }
  ```

#### `GET /api/reports/executive-incident/{incident_ref}/status`

* **Invocado por**: `ExecutiveReportModal.tsx` al abrir el modal para comprobar si ya existe un informe generado.
- **Respuesta**:

  ```json
  {
    "exists": true,
    "incidentRef": "2606S77393",
    "filename": "RESUMEN_EJECUTIVO_2606S77393.pptx",
    "downloadUrl": "/api/reports/executive-incident/2606S77393",
    "sizeBytes": 145820
  }
  ```

#### `GET /api/reports/executive-incident/{incident_ref}`

* **Invocado por**: Navegador o cliente para descargar directamente el binario PowerPoint generado.
- **Respuesta**: `200 OK` con cabeceras `Content-Type: application/vnd.openxmlformats-officedocument.presentationml.presentation` y `Content-Disposition: attachment; filename="RESUMEN_EJECUTIVO_{incident_ref}.pptx"`.
- **Almacenamiento**: Los ficheros se generan en `/infocodes/var/storage/executive_pptx/` (enlazado simbólicamente con `/infocodes/var/storage/release-dashboard/reports/executive/`).

---

### 4. API de Reportes de Incidencias (`/api/reports/*`)

Invocada por el cliente [`dashboards/reportes-incidencias/api-client.js`](../../dashboards/reportes-incidencias/api-client.js):

| Método | Endpoint | Propósito |
| --- | --- | --- |
| `GET` | `/api/reports` | Listar todos los reportes operativos registrados |
| `POST` | `/api/reports` | Crear un nuevo reporte semanal o mensual |
| `GET` | `/api/reports/{id}` | Obtener el detalle estructurado de un reporte por identificador |
| `PUT` | `/api/reports/{id}` | Actualizar datos, incidencias o hitos de un reporte existente |
| `DELETE` | `/api/reports/{id}` | Eliminar un reporte |
| `POST` | `/api/reports/{id}/duplicate?new_week={week}` | Duplicar la estructura de un reporte previo para una nueva semana |
| `GET` | `/api/reports/{id}/export` | Exportación completa del reporte en formato JSON |
| `GET` | `/api/reports/{id}/legacy-pptx` | Descarga de la presentación PowerPoint ejecutiva generada |

---

### 5. Inteligencia Artificial (Epsilon / Remedy)

#### `POST /api/epsilon/generate` (y alias `/api/epsilon/resumen`)

* **Propósito**: Genera y valida un resumen técnico de incidencia IT ejecutando el motor oficial de Epsilon IA con validación estricta Pydantic (`converters/src/epsilon_service.py`), integrando soporte con Claude Sonnet (Anthropic LiteLLM MasOrange), OpenAI y Mock offline.
- **Formatos de Entrada Soportados**:
  - **Formato A (Directo)**: Objeto JSON íntegro con los campos Remedy de la incidencia (`ID de incidencia`, `Descripción`, `Estatus`, `Prioridad`, etc.). Admite parámetro de consulta `?mock=true`.
  - **Formato B (Wrapper)**:

    ```json
    {
      "incident_data": {
        "ID de incidencia": "INC000004174655",
        "Descripción": "Fallo de sincronización en Ficha de Cliente...",
        "Estatus": "Asignado",
        "Prioridad": "Crítica"
      },
      "mock": false,
      "provider": "anthropic",
      "model": "claude-sonnet-4-5"
    }
    ```

* **Códigos de Respuesta HTTP**:
  - `200 OK`: Resumen generado y validado con éxito. Si incluye código con prefijo `INC`, se persiste automáticamente en `data/.epsilon_cache/{codigo}.json` y en memoria (`EPSILON_CACHE`).
  - `400 Bad Request`: Cuerpo de solicitud vacío, JSON inválido o datos de incidencia insuficientes.
  - `422 Unprocessable Entity`: La respuesta del LLM no superó el contrato estricto de Pydantic (ej. `problema` excede 40 palabras o violación de orden cronológico). Devuelve `validation_errors` detallados.
  - `502 Bad Gateway`: Error de conectividad, autenticación o respuesta 4xx/5xx del proveedor LLM o proxy corporativo.
- **Estructura de Respuesta (200 OK)**:

  ```json
  {
    "success": true,
    "titulo": "Ficha de Cliente - Error en sincronización de teléfono",
    "estadoActual": "Asignado",
    "problema": "El módulo de recogidas de equipamiento fijo no propaga el teléfono de contacto modificado hacia PS y Siebel 8 debido a un fallo en MDG.",
    "impacto": "Medio. Afecta a la logística inversa de routers en bajas de fibra, con riesgo de envíos fallidos al transportista. Sin método alternativo disponible.",
    "solucion": "Bug identificado en microservicio MDG. Parche comprometido para despliegue en ventana release del 12/11/2026.",
    "sistemas": ["Ficha de Cliente", "Siebel 8", "MDG", "PS"],
    "hitosTecnicos": [
      "[02/11/2026 09:15:00]: Detección de inconsistencia entre Ficha de Cliente y sistemas downstream.",
      "[03/11/2026 14:00:00]: N2 aísla el error en el microservicio MDG y traslada requerimiento a desarrollo."
    ],
    "bloqueos": [
      "[Ventana Release]: Dependencia de entrega y despliegue de parche por proveedor planificado para release del 12/11/2026."
    ],
    "siguienteAccion": "Despliegue y validación del parche en ventana del 12/11/2026.",
    "meta": {
      "provider": "anthropic",
      "model": "claude-sonnet-4-5",
      "mock": false,
      "tokens": 620,
      "elapsed_seconds": 1.45,
      "timestamp": "2026-11-06T12:00:00Z"
    }
  }
  ```

---

#### `GET /api/epsilon/resumenIA/{codigo}`

* **Invocado por**: [`dashboards/assets/resumen-ia.js`](../../dashboards/assets/resumen-ia.js) al hacer clic sobre cualquier identificador de incidencia o botón "✨ Resumen IA · Epsilon" en el Portal y dashboards.
- **Propósito**: Orquestador propio de Epsilon Resumen IA (`resolve_or_generate_epsilon_summary` en [`converters/src/epsilon_service.py`](../../converters/src/epsilon_service.py)), alimentado directamente con los datos crudos de Remedy y gobernado por el System Prompt [`data/resumen_incidencia_epsilon.md`](../../data/resumen_incidencia_epsilon.md).
- **Cadena de Resolución y Smart Fingerprint Cache (`EPSILON_PROVIDER_MODE=internal` por defecto)**:
  1. **Caché rápida en memoria (`MEMORY_HIT` / `HIT`)**: Si no se solicita `?force=1` / `?refresh=1` ni `Cache-Control: no-cache`, sirve desde memoria (TTL 15 min).
  2. **Lectura de detalle crudo Remedy**: Consulta `GET https://soptmc.si.orange.es/MonTMC/api/eps/remedyG/{codigo}` (con respaldo local en `data/.remedy_cache/{codigo}.json`) y normaliza marcas temporales UTC (`+00:00`/`Z`) a `Europe/Madrid`.
  3. **Smart Fingerprint Cache (`FINGERPRINT_HIT`)**: Calcula la huella del ticket (`fechaUltimaModificacion`, `estadoDesc`, `detalleSolucion`, número y último apunte de `worklog` y `paps`) junto con el `prompt_hash` de `resumen_incidencia_epsilon.md`. Si coincide con `data/.epsilon_cache/{codigo}.json`, responde al instante sin consumir tokens LLM.
  4. **Síntesis y Autocorrección (`INTERNAL_LLM_GENERATED`)**: Si el ticket o el prompt cambiaron, sintetiza el resumen contra el Gateway LLM corporativo (`https://llm.tools.cloud.masorange.es/v1/messages`), valida las 10 reglas de `EpsilonResumenModel` (con **1 reintento autocorrectivo** si detecta incumplimiento) y guarda en caché:

     ```json
     {
       "success": true,
       "meta": {
         "source": "internal_epsilon_engine",
         "remedy_source": "montmc_remedy_live",
         "remedy_fingerprint": "1df8323c03c7bc6b",
         "prompt_hash": "b682cbe20574",
         "worklog_count": 21,
         "is_stale_warning": false
       }
     }
     ```

  5. **Contingencia progresiva**:
     - Si `EPSILON_PROVIDER_MODE=internal_with_soptmc_fallback`, recurre automáticamente al endpoint legado `https://soptmc.si.orange.es/MonTMC/api/epsilon/resumenIA/{codigo}` (`SOPTMC_FALLBACK_HIT`) en caso de caída del LLM.
     - Si `EPSILON_PROVIDER_MODE=soptmc`, opera 100% contra el endpoint externo de SopTMC (`LIVE_SOPTMC_HIT`).
     - Ante desconexión total, recurre a snapshot previo en disco (`DISK_HIT`) o genera sobre volcados locales `data/output/*-massive.json` / `*-postmortem.json` (`LOCAL_DUMP_FALLBACK`, marcando `is_stale_warning: true` si supera 2 horas).
  6. Si no existe información en ninguna fuente, responde `502 Bad Gateway`.
- **Invalidación de Caché**:
  - Al procesar una subida exitosa de CSV en `POST /api/upload`, se invoca automáticamente `EPSILON_CACHE.clear()` para garantizar que los tickets modificados o reabiertos en el nuevo CSV no sirvan datos cacheados obsoletos.
- **Topología de Ejecución**:
  - **Desarrollo**: Servido directamente por `serve_app.py` en el puerto `:8080`.
  - **Producción (VPS)**: Proxificado por Nginx en `:8081` (`location /api/epsilon/`, con bypass en `?force` / `?refresh`) hacia el backend FastAPI en `:8000` montando [`converters/src/fastapi_epsilon_router.py`](../../converters/src/fastapi_epsilon_router.py).

---

### 6. Datasets y Catálogo JSON

#### `GET /data/output/index.json`

* **Invocado por**: `dashboards/portal/index.html` y selectores de versión en los dashboards de Incidencias Masivas y Postmortem.
- **Propósito**: Devuelve el índice completo de datasets disponibles, ordenados cronológicamente:

  ```json
  {
    "massive": [
      { "filename": "20260213-massive.json", "date": "2026-02-13", "records": 482 }
    ],
    "postmortem": [
      { "release": "2026R7", "filename": "2026R7-postmortem.json", "records": 34 }
    ],
    "last_updated": "2026-10-20T14:30:00Z"
  }
  ```

#### `GET /data/output/{filename}.json`

* **Invocado por**: Lógica de cliente en cada dashboard para descargar el dataset completo.
- **Ruta de almacenamiento**:
  - En producción, Nginx mapea `/data` como un alias a `/infocodes/var/storage/release-dashboard`.
  - En local, `serve_app.py` intercepta `/data/` y lo sirve desde `STORAGE_DIR` (`data/` o variable de entorno `RELEASE_DASHBOARD_STORAGE_DIR`).

---

### 7. Integración con Jira (Gestión de Problemas)

#### `GET /api/dashboard` (o `/problemas/api/dashboard`)

* **Invocado por**: Vista principal de Next.js (`page.tsx`) en el panel de Gestión de Problemas.
- **Parámetros**: `?refresh=true` (fuerza la recarga omitiendo la caché de Jira).
- **Propósito**: Conecta con la API REST de Jira para recuperar problemas, incidencias vinculadas, KPIs de resolución y tiempos de ciclo.

---

### 8. Monitorización y Salud del Sistema

#### `GET /api/health`

* **Invocado por**: [`dashboards/assets/topbar.js`](../../dashboards/assets/topbar.js) y [`api-client.js`](../../dashboards/reportes-incidencias/api-client.js).
- **Propósito**: Valida que la API REST (FastAPI) está viva. Actualiza el indicador visual circular de la barra superior a verde (`API OK`) o rojo (`API Offline`).

#### `GET /healthz` y `GET /readyz`

* **Invocado por**: Topbar (como fallback de salud) y sondas de infraestructura de servidor o balanceador.

---

### 9. Catálogo de Agentes IA y Skills

#### `GET /api/agents-catalog`

* **Invocado por**: [`dashboards/agents-catalog/agents-catalog.js`](../../dashboards/agents-catalog/agents-catalog.js).
- **Propósito**: Proporciona el catálogo interactivo de agentes de IA y habilidades técnicas (*skills*) de la biblioteca corporativa (`biblioteca-agentes`), correlacionando qué agentes emplean cada skill, métricas de reusabilidad y comando de despliegue.
- **Respuesta (`200 OK`)**: Estructura Envelope (`success`, `data`, `metadata`). Si la biblioteca externa no está presente localmente (entorno VPS), sirve de forma transparente el dataset estático generado en `data/output/agents_catalog.json`.
- **Esquema**:

  ```json
  {
    "success": true,
    "data": {
      "agents": [ ... ],
      "skills": [ ... ],
      "domains": [ ... ],
      "kpis": {
        "total_agents": 5,
        "total_skills": 6,
        "total_domains": 2,
        "skills_coverage_percent": 100.0
      },
      "deployment": {
        "command_template": ".\\deploy-agents.cmd \"<TargetRepo>\" -Agents \"<AgentName>\"",
        "source_repo": "C:\\Users\\jose.delafuente\\Claude\\Projects\\biblioteca-agentes"
      }
    },
    "metadata": {
      "generated_at": "2026-10-22T16:30:00+02:00",
      "version": "1.0.0",
      "source": "biblioteca-agentes"
    }
  }
  ```

---

### 10. Auditoría de Ingesta y Telemetría Semántica

#### `GET /api/logs/ingestion`

* **Invocado por**: Consola de Auditoría y Telemetría IA en el Cockpit del Incident Manager (<kbd>Shift</kbd> + <kbd>I</kbd>).
- **Parámetros**: `?lines=N` (número de líneas a leer desde el final del log; por defecto `100`, máximo `1000`).
- **Propósito**: Devuelve en tiempo real las últimas líneas de [`data/logs/ingestion_audit.log`](../../data/logs/ingestion_audit.log) para diagnóstico de la carga de ficheros CSV, tiempos de conversión, llamadas a Epsilon y estado de enriquecimiento.
- **Respuesta (`200 OK`)**: Texto plano estructurado (`text/plain; charset=utf-8`) o JSON envelope conteniendo las trazas.

#### `POST /api/ingestion/retry-ia` (alias: `POST /api/epsilon/retry`)

* **Invocado por**: Botón *"Forzar Refresco / Reintentar Resumen IA"* en la Consola de Auditoría.
- **Payload JSON (opcional)**:

  ```json
  {
    "incident_ids": ["INC000004167733", "INC000004152079"],
    "force": true
  }
  ```

* **Propósito**: Relanza de forma controlada el enriquecimiento semántico mediante el **Motor Interno Epsilon IA** (`resolve_or_generate_epsilon_summary`, o SopTMC si `EPSILON_PROVIDER_MODE=soptmc`) para aquellas incidencias activas que hayan quedado en estado `PARCIAL` o `INCOMPLETA`, o para forzar la regeneración global (`force: true`).
- **Comportamiento**:
  1. Filtra automáticamente las incidencias en estado terminal (evitando peticiones redundantes).
  2. Sintetiza/valida los resúmenes con nuestro motor interno actualizando la caché local en `data/.epsilon_cache/`.
  3. Regenera [`data/output/high_priority_notifications.json`](../../data/output/high_priority_notifications.json) y [`data/output/ingestion_audit_summary.json`](../../data/output/ingestion_audit_summary.json).
  4. Registra el detalle del reintento en `data/logs/ingestion_audit.log`.
- **Respuesta (`200 OK`)**:

  ```json
  {
    "success": true,
    "message": "Reintento de Resumen IA ejecutado correctamente",
    "processed_count": 18,
    "enriched_count": 18,
    "failed_count": 0
  }
  ```

---

### 11. Ingesta y Detalle Remedy MonTMC API

#### `POST /api/sync-remedy`

* **Invocado por**: Botón *"⚡ Sincronizar Remedy"* en la cabecera de la Consola de Triaje (`dashboards/emergency-triage-console/`).
- **Parámetros Query / Body JSON (opcionales)**:

  ```json
  {
    "dias": 3,
    "usuario": "jdelat"
  }
  ```

  *(Por defecto `dias=3` y `usuario="jdelat"`, configurables mediante variables de entorno).*
- **Propósito**: Ejecuta la sincronización incremental de incidencias masivas consultando la API corporativa MonTMC (`GET https://soptmc.si.orange.es/MonTMC/api/eps/incidenciasMasivas/{dias}/{usuario}`), realiza upsert no destructivo sobre el dataset masivo activo, **pre-genera en paralelo (`pregenerate_epsilon_summaries`, `EPSILON_SYNC_PREGEN=1`) los resúmenes IA de incidencias activas nuevas o actualizadas** y reevalúa las notificaciones ejecutivas de alta prioridad (`evaluate_incident_notifications.py`).
- **Códigos de Estado**:
  - `200 OK`: Sincronización finalizada correctamente. Devuelve métricas de inserción/actualización.
  - `500 Internal Server Error`: Fallo interno durante la persistencia o reevaluación.
  - `502 Bad Gateway`: Error de conectividad o HTTP en la llamada a MonTMC.
- **Respuesta (`200 OK`)**:

  ```json
  {
    "success": true,
    "source": "api_montmc",
    "total_remote": 14,
    "inserted": 2,
    "updated": 12,
    "historical_total": 612,
    "message": "Sincronización completada con éxito. Insertadas 2, actualizadas 12 incidencias."
  }
  ```

#### `GET /api/remedy/detail/{idRemedy}`

* **Invocado por**: Sección colapsable *"Notas Técnicas y Worklog Remedy"* en el Modal Orquestador de la Consola de Triaje (`triage.js`) y en el modal compartido de Epsilon IA (`resumen-ia.js`).
- **Parámetros**:
  - `{idRemedy}` en el path (ej: `INC000004179897`).
  - `?refresh=true` (opcional): Invalida la caché y fuerza una nueva llamada a la API corporativa MonTMC.
- **Propósito**: Recupera el detalle enriquecido de una incidencia desde MonTMC (`GET https://soptmc.si.orange.es/MonTMC//api/eps/remedyG/{idRemedy}`), incluyendo notas de trabajo (worklogs), asignaciones y estados técnicos.
- **Estrategia de Caché**:
  1. Caché en memoria `REMEDY_DETAIL_CACHE` con TTL de 10 minutos.
  2. Caché persistente en disco en `data/.remedy_cache/{idRemedy}.json` con TTL de 1 hora.
  3. Soporte para parámetro `?refresh=true` para forzar invalidación inmediata.
- **Códigos de Estado**:
  - `200 OK`: Detalle recuperado (desde caché o API remota).
  - `400 Bad Request`: Formato de identificador inválido (debe coincidir con `^INC\d+$`).
  - `404 Not Found`: Incidencia no encontrada en Remedy / MonTMC.
  - `502 Bad Gateway`: Error de comunicación con la API corporativa MonTMC.
- **Respuesta (`200 OK`)**:

  ```json
  {
    "idRemedy": "INC000004179897",
    "resumen": "CORTE FIBRA OPTICA SEVILLA",
    "estado": "En curso",
    "prioridad": "P1",
    "urgencia": "1-Crítica",
    "impacto": "1-Extenso / Generalizado",
    "grupoAsignado": "SOPORTE RED FIBRA",
    "personaAsignada": "Juan Pérez",
    "fechaApertura": "2026-10-24 08:30:00",
    "fechaResolucion": null,
    "worklogs": [
      {
        "fecha": "2026-10-24 09:15:00",
        "autor": "Juan Pérez",
        "texto": "Localizado corte físico en tramo troncal. Técnico de campo desplazado a arqueta."
      }
    ],
    "_cached": true,
    "_cache_source": "memory"
  }
  ```

#### Variables de Entorno MonTMC y Motor Epsilon IA

* `MON_TMC_BASE_URL`: URL base de la API corporativa (por defecto `https://soptmc.si.orange.es/MonTMC`).
- `MON_TMC_USER`: Usuario corporativo para las consultas (por defecto `jdelat`).
- `MON_TMC_DEFAULT_DAYS`: Días de histórico hacia atrás para la consulta masiva (por defecto `3`).
- `MON_TMC_TIMEOUT`: Timeout en segundos para las peticiones HTTP (por defecto `10`).
- `MON_TMC_RETRIES`: Número de reintentos con backoff exponencial (por defecto `2`).
- `EPSILON_PROVIDER_MODE`: Conmuta el flujo de generación de Resumen IA (`internal` por defecto, `internal_with_soptmc_fallback` o `soptmc` legado).
- `EPSILON_SYNC_PREGEN`: Pre-generación proactiva en background durante `sync_montmc_incidents.py` (`1` activo por defecto, `0` desactivado).

---

## ⚙️ Diferencias entre Entornos

| Concepto | Desarrollo Local (`serve_app.py`) | Producción (Nginx + FastAPI + Next.js) |
| :--- | :--- | :--- |
| **Servidor Principal** | Python `http.server` enriquecido en **puerto `8080`** (`SERVE_APP_PORT`) | **Nginx en puerto `8081`** (`nginx.conf`) |
| **Backend de APIs** | Delega a FastAPI (`:8000`) si está levantado; si no, ejecuta fallback local en proceso sobre el motor de `cso-incident-masivas-report` | **FastAPI (`uvicorn` en puerto `8000`)**, enrutado por Nginx vía `conf.d/cso-incident.conf` |
| **Almacenamiento Persistente** | Directorio `data/` en la raíz del repo (o variable `RELEASE_DASHBOARD_STORAGE_DIR`) | Directorio desacoplado **`/infocodes/var/storage/release-dashboard/`** (`input/`, `output/`, `reports/`) |
| **Informes Ejecutivos PPTX** | `data/reports/executive/` | **`/infocodes/var/storage/executive_pptx/`** (symlink en `reports/executive`) |
| **Proxy Epsilon IA** | Emulado en `serve_app.py` con caché en memoria `EPSILON_CACHE` (15 min) | Configurado en `nginx.conf` (`location /api/epsilon/`) con `proxy_cache` compartido (15 min) y stale-on-error |
| **Gestión de Problemas** | Proxy en `serve_app.py` reenviando `/problemas` a `http://localhost:3001` (o `:3000`) | Proxy en Nginx (`location /problemas`) hacia upstream `localhost:3001` con cabeceras de proxy y caché |
| **Servicio de Ficheros `/data`** | `serve_app.py` intercepta `/data/` y lee de `STORAGE_DIR` | Nginx sirve directamente mediante directiva `alias /infocodes/var/storage/release-dashboard;` |
