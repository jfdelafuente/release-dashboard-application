# Guía de Triaje ITIL Automatizado y Matriz de Criticidad

📖 **Manual técnico y operacional del motor de triaje determinista para la priorización y gestión de emergencias IT en Orange.**

---

## 1. Introducción y Propósito

En grandes infraestructuras de telecomunicaciones y servicios, la clasificación manual inicial de incidencias en soporte de primer nivel (**N1**) suele adolecer de dispersión y **subescalación**: incidencias con cortes severos o degradaciones críticas de frontales se catalogan nominalmente en Remedy como *Prioridad Media (P3)* o *Baja (P4)*, retrasando la intervención de los equipos de guardia y la convocatoria del Incident Manager.

El **Triaje ITIL Automatizado** es el motor algorítmico y determinista que evalúa el **impacto real sobre el negocio y los servicios** de cada incidencia activa, aplicando de forma estricta:

1. La **Matriz de Severidad y Criticidad IT** ([`.agents/skills/it-severity-matrix/SKILL.md`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/.agents/skills/it-severity-matrix/SKILL.md)).
2. El **Marco Operativo de Gestión de Emergencias IT de Orange** ([`.agents/skills/orange-it-emergency-management/SKILL.md`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/.agents/skills/orange-it-emergency-management/SKILL.md)).
3. La detección automática de **Discrepancias de Prioridad** (alertando al Incident Manager cuando la prioridad sugerida supera la nominal del ticket).

---

## 2. Arquitectura del Motor de Triaje

El motor se implementa en la clase [`SeverityEvaluator`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/converters/cli/evaluate_incident_notifications.py#L152) dentro de la utilidad CLI [`converters/cli/evaluate_incident_notifications.py`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/converters/cli/evaluate_incident_notifications.py):

```mermaid
flowchart TD
    A["Fichero Masivo de Incidencias<br>(CSV / JSON)"] --> B["Filtro de Estados Terminales<br>(Excluye Cerrado, Resuelto, Cancelado)"]
    B -->|Incidencias Activas| C["Cliente Epsilon Resumen IA<br>(Proxy 8081 / Dev 8080 / soptmc.si.orange.es)"]
    C --> D["SeverityEvaluator.evaluate(ticket, epsilon_data)"]
    
    subgraph "Motor de Triaje (SeverityEvaluator)"
        D --> E1["1. Clasificación en 10 Procesos Críticos<br>(_classify_process)"]
        D --> E2["2. Análisis Heurístico de Impacto<br>(_evaluate_impact)"]
        D --> E3["3. Análisis de Urgencia y Workarounds<br>(_evaluate_urgency)"]
        E1 & E2 & E3 --> E4["4. Cruce Matriz ITIL + Reglas de Oro<br>(_calculate_matrix)"]
        E4 --> E5["5. Comprobación Suelo Explícito (/SL1 o /SL2)"]
    end

    E5 --> F["Detección de Discrepancias<br>(detect_priority_discrepancy)"]
    F --> G["Cálculo de Tiempos y SLAs de Crisis<br>(compute_emergency_sla_status)"]
    G --> H["Catálogo Unificado<br>data/output/high_priority_notifications.json"]
```

---

## 3. Las 5 Fases del Algoritmo de Triaje

### Fase 1: Ingesta y Filtrado de Estados Terminales

El evaluador analiza cada ticket del informe masivo y descarta de forma inmediata los tickets en estados finales para no sobrecargar a los operadores ni desvirtuar los SLAs activos:

* Estados omitidos: `Cerrado`, `Cerrada`, `Closed`, `Resuelto`, `Resuelta`, `Resolved`, `Cancelado`, `Cancelada`, `Cancelled`, `Canceled`.
* Métrica resultante: `_metadata.kpis.terminal_skipped_count`.

### Fase 2: Enriquecimiento Contextual Dual (Remedy + Epsilon IA)

Para superar la brevedad o ambigüedad del título de Remedy, el evaluador construye un corpus textual unificado combinando:

* **Metadatos Remedy**: `Descripción`, `Impacto`, `Urgencia`, `Grupo Asignado`, `Fecha de Envío`.
* **Diagnóstico Epsilon IA**: `problema`, `impacto`, `solucion`, `sistemas`, `bloqueos`, `siguienteAccion`.

> [!NOTE]
> Gracias al cliente [`EpsilonClient`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/converters/cli/evaluate_incident_notifications.py#L762) con fallback inteligente y caché en disco ([`data/.epsilon_cache/`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/data/.epsilon_cache/)), si el microservicio Epsilon no estuviera disponible, el sistema degrada elegantemente y realiza el triaje usando únicamente los campos nativos de Remedy.

---

### Fase 3: Clasificación en los 10 Procesos Críticos mediante Matriz Ponderada Multidominio

A diferencia de los analizadores tradicionales basados en estructuras secuenciales rígidas (`if/elif`), el evaluador implementa una **Matriz de Puntuación Ponderada Multidominio** (`_classify_process_multi_domain`). Este mecanismo evita sesgos posicionales y asigna pesos diferenciales según la autoridad de cada metadato:

```mermaid
flowchart LR
    A["Corpus del Ticket"] --> B["Extracción de Evidencias"]
    B --> W1["Grupo Resolutor Remedy<br><b>Peso 4.0x</b>"]
    B --> W2["Sistemas Epsilon IA<br><b>Peso 3.0x</b>"]
    B --> W3["Título del Ticket<br><b>Peso 2.0x</b>"]
    B --> W4["Descripción y Problema<br><b>Peso 1.0x</b>"]
    
    W1 & W2 & W3 & W4 --> S["Matriz Ponderada de Coincidencias<br>(Regex Compiladas con \b)"]
    S --> C1["Proceso de Negocio Crítico<br>(ej. Atención al Cliente - ATC)"]
    S --> C2["Dominio Técnico de Infraestructura<br>(ej. Sistemas Core / Middleware)"]
```

#### Prevención de Falsos Positivos con Regex Compiladas (`\b`)
Todos los patrones de detección utilizan límites de palabra (`\bpattern\b`). Esto erradica falsos positivos históricos donde subcadenas cortas disparaban clasificaciones incorrectas:
* `operaciones` ya **no** se clasifica como O&M (eliminada coincidencia espuria de `rac`).
* `pasaporte` ya **no** se clasifica como Facturación (eliminada coincidencia de `sap`).
* `comunicación` ya **no** se clasifica como O&M (eliminada coincidencia de `uca`).
* `precaución` ya **no** se clasifica como O&M (eliminada coincidencia de `cau`).

#### Doble Etiquetado ITIL: Negocio vs Infraestructura
El motor etiqueta simultáneamente dos dimensiones operativas:
1. `proceso_negocio`: Impacto sobre el flujo cliente (ej. *Atención al Cliente*, *Ventas*, *Portabilidad*, *Prepago*, *Provisión*, *Facturación*).
2. `dominio_tecnico`: Capa técnica subyacente (ej. *Middleware e Integración*, *Conectividad de Sedes/Circuitos*, *Infraestructura Core/Cloud*, *Identidad y Automatización*).

| # | Proceso Crítico | Sistemas y Grupos Resolutores Típicos | Criterio de Activación de Emergencia (SL1) |
| :---: | :--- | :--- | :--- |
| **3.1** | **Atención al Cliente (ATC)** | `Ficha de Cliente Orange`, `DES_SOE_FICHA`, `APL_MOV_SOE`, `IVR`, `CTI`, `Siebel 8`, `CRM Jazztel`, `CRM4TELCO`, `LivePerson`, `Djingo`, `Onuris`. | Frontales/CRM con desviación >20% en 30 min, o IVR descartando >20% llamadas. |
| **3.2** | **Ventas** | `CERES`, `NEG_CAMP_CERES`, `ECONTRATO`, `PANGEA`, `Televenta`, `updateCommercialActSPA`, canal comercial. | Afectación >30% del volumen de operaciones, o caída >15% de ventas diarias. |
| **3.3** | **Prepago** | `RECARGAS APRS`, `OCS`, `SOP_OCS`, altas de líneas/eSIM prepago. | >10% de errores o >30 minutos sin recargas/altas. |
| **3.4** | **Portabilidad** | Flujo nocturno 2:00 AM, entidad de referencia, `POMV`, `NCRN`. | Fallo en arranque flujo 2 AM o >2 horas de retraso con entidad de referencia. |
| **3.5** | **Provisión y Cobertura** | `TEIDE`, `SOP_SMC_TEIDE`, `LUNA`, `IP24`, `SIGMA`, `ALTAIR a BRÚJULA`, `MYADDRESS`, `GIS Fibra`. | Órdenes en error (>20% móvil / >30% fijo), o 100% provisiones paradas >10 min. |
| **3.6** | **Facturación y Cobros** | `BSCS`, `OPEN COBROS`, `EXCALIBUR`, `HPFMS` (Fraude), `SAP`, `Mediación HP-IUM`. | >3 horas sin tarificación online, o indisponibilidad en ventana ±3 días de ciclo. |
| **3.7** | **Middleware Transversal** | `APIGEE`, `OPENAPI`, `TIBCO`, `GC Middleware`, `Datapower`, conectores `OCCI`, `SBL_EAI`. | Caída, saturación de hilos o errores masivos (504/500) en el bus de integración. |
| **3.8** | **Conectividad de Sedes y Tiendas** | `RTV-TECSE RED DATOS`, `GNOC`, circuitos `Ulises` y `Meneses`, Call Centers / `MSC`, tiendas. | Aislamiento total de sede/MSC, o caída simultánea de circuitos principal y backup. |
| **3.9** | **Infraestructura Core IT y Cloud** | `Atlas_Soporte_Unix` (`PSeries Power9`), `VMware ESX`, clúster `Exadata`, `OCI`, `GCP`, SAN `HWSAN`. | Corte troncal Cloud (OCI/GCP), o caída de servidor/hipervisor sin absorción por HA. |
| **3.10** | **Identidad y Automatización** | `GDU`, `EVIDIAN`, `GDU/ACM`, `ROBOTFACTORY`, SSO corporativo. | Caída global de autenticación/SSO o bloqueo en factoría de robots de backoffice. |

---

### Fase 4: Evaluación Heurística de Impacto, Urgencia y Cálculo de `impacto_justificacion`

#### A. Nivel de Impacto y Justificación Contextual (`_evaluate_impact`)

> [!IMPORTANT]
> **Desacoplamiento del Campo "Impacto: Masiva" de Remedy:**
> En los informes exportados de BMC Remedy / Smart IT, **el 100% de las incidencias del fichero origen vienen tipificadas con `Impacto: Masiva`** (condición inherente al informe de seguimiento de incidencias de servicio).
> El motor algorítmico **no asume ciegamente que "Masiva" equivalga a un corte total SL1 / Alto**. De hacerlo, todas las incidencias colapsarían en P1, destruyendo la discriminación operativa entre Emergencias Críticas (SL1) e Incidencias Mayores (SL2).
> El impacto y el campo `impacto_justificacion` se evalúan mediante una jerarquía discriminativa de 5 pasos:

1. **Fallo Cosmético o Sin Afectación Operativa**:
   * Si el texto o diagnóstico contiene `error tipográfico`, `cosmético` o `sin afectación al servicio`:
     * `impacto = "Bajo"`
     * `impacto_justificacion = "Fallo cosmético sin interrupción de servicio."`
2. **Umbrales Cuantitativos Directos (SL1 Objetivo)**:
   * **Sedes / Tiendas / Call Centers:** $\ge 3$ sedes afectadas.
   * **Usuarios / Clientes / Líneas:** $\ge 500$ abonados afectados.
   * **Desviación / Errores %:** $\ge 20\%$ de desviación o error.
   *(Salvo que se documente enlace secundario con tráfico principal cursando bajo redundancia activa).*
   * `impacto = "Alto"`
   * `impacto_justificacion = "Umbral cuantitativo superado: {X} sedes/tiendas afectadas (umbral crítico >= 3), {Y}% de afectación (umbral crítico >= 20%)."`
3. **Diagnóstico y Síntesis de Epsilon Resumen IA**:
   * Si Epsilon IA diagnostica afectación crítica o califica el impacto como "Alto", "Crítico", o "100% en operativa":
     * `impacto = "Alto"`
     * `impacto_justificacion = "Epsilon IA: {diagnóstico conciso del impacto en clientes/sedes}"`
   * Si Epsilon IA reporta afectación acotada a sedes/usuarios específicos (ej. 5 clientes, 10 usuarios, degradación funcional):
     * `impacto = "Medio"`
     * `impacto_justificacion = "Epsilon IA: {diagnóstico conciso de afectación parcial}"`
4. **Palabras Clave Críticas y Moderadas con Filtro de Negación Sintáctica (`is_phrase_negated`)**:
   * Términos críticos (`caída total`, `corte total`, `sin servicio`, `bloqueo general`) no negados:
     * `impacto = "Alto"`
     * `impacto_justificacion = "Afectación crítica detectada ('{kw}') sobre el servicio principal sin alternativa viable."`
   * Términos de degradación (`degradación`, `lentitud`, `retraso`, `parcial`, `intermitente`):
     * `impacto = "Medio"`
     * `impacto_justificacion = "Degradación funcional reportada ('{kw}') con servicio parcialmente operativo."`
5. **Inferencia Determinista sobre Tickets Masivos de Remedy**:
   * Si el ticket viene con `Impacto: Masiva` pero no presenta evidencias de corte total ni supera umbrales cuantitativos:
     * `impacto = "Medio"` (incidencia de alcance masivo evaluada como degradación funcional parcial o incidente mayor SL2).
     * `impacto_justificacion = "Incidencia catalogada Masiva en Remedy evaluada como degradación funcional parcial sin corte total de servicio."`
   * Si no cumple ninguna condición anterior:
     * `impacto = "Bajo"`
     * `impacto_justificacion = "Afectación acotada a componentes secundarios o usuarios aislados."`

#### B. Nivel de Urgencia y Análisis de Bloqueos (`_evaluate_urgency`)

* **Explotación de Bloqueos de Epsilon IA**:
  El motor analiza el campo `bloqueos` de Epsilon Resumen IA. Si se reportan dependencias críticas activas (`sin alternativa`, `bloqueo`, `esperando proveedor`) y no consta workaround, la urgencia se eleva de forma prioritaria a **Alta**.
* **Detección de Workaround**:
  * `Sí`: Presencia confirmada de `workaround`, `solución temporal`, `solucion alternativa`, `export alternativo`.
  * `No`: Indicación expresa de `sin alternativa`, `sin workaround`, o bloqueo sin mitigación.
  * `Desconocido`: Ausencia de datos explícitos de mitigación.
* **Niveles de Urgencia**:
  * **Alta (`Alta`)**: Bloqueos reportados sin workaround, términos críticos en vivo (`afectando en vivo`, `urgente`, `crítico`), o campo Remedy `Urgencia: Crítica` / `Alta`.
  * **Media (`Media`)**: Incidencias en tratamiento activo (`en curso`, `asignado`, o `Urgencia: Media` nativa).
  * **Baja (`Baja`)**: Baja sensibilidad temporal, tickets resueltos o cerrados.

---

### Fase 5: Matriz de Cruce ITIL y Reglas de Oro de Orange

#### Matriz de Cruce Estándar

La función `_calculate_matrix(impact, urgency, has_workaround)` cruza las variables según la tabla normativa:

| Nivel de Impacto | Nivel de Urgencia | ¿Existe Workaround? | Prioridad Calculada | Severidad Oficial | SLA Máximo Resolución |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **Alto** | **Alta** | Cualquiera | **P1** | **SL1 — Emergencia Crítica** | 120 min (2 h) |
| **Alto** | **Media** | Cualquiera | **P1** | **SL1 — Emergencia Crítica** | 120 min (2 h) |
| **Alto** | **Baja** | Cualquiera | **P2** | **SL2 — Incidencia Mayor** | 240 min (4 h) |
| **Medio** | **Alta** | Cualquiera | **P2** | **SL2 — Incidencia Mayor** | 240 min (4 h) |
| **Medio** | **Media** | **No** o **Desconocido** | **P2** | **SL2 — Incidencia Mayor** | 240 min (4 h) |
| **Medio** | **Media** | **Sí** | **P3** | **SL3 — Incidencia Menor** | 480 min (8 h) |
| **Medio** | **Baja** | Cualquiera | **P3** | **SL3 — Incidencia Menor** | 480 min (8 h) |
| **Bajo** | **Alta** / **Media** | Cualquiera | **P3** | **SL3 — Incidencia Menor** | 480 min (8 h) |
| **Bajo** | **Baja** | Cualquiera | **P4** | **SL4 — Informativa** | 1440 min (24 h) |

#### Las Reglas de Oro de Orange

1. **Principio de Precaución (Regla de Oro N1):**
   > En caso de duda sobre el alcance de una afectación en un proceso crítico, se clasifica preventivamente como **SL1 / P1**. Solo se desescalará cuando se confirme fehacientemente que el impacto es acotado.
2. **Suelo Mínimo por Etiquetado Explícito (`/SL1` y `/SL2`):**
   Si el título del ticket contiene la etiqueta `/SL1` (ej. `INDISPONIBILIDAD // FICHA // SL1`) o `/SL2`, el evaluador establece **P1** o **P2** como suelo mínimo no negociable, invalidando campos erróneos de Remedy (`Prioridad: Media` o `Urgencia: Baja`).
3. **Gobernanza Estricta de Workarounds:**
   > [!WARNING]
   > La aplicación de un workaround en una incidencia de Impacto Alto **NO reduce automáticamente la severidad del ticket**. La emergencia SL1 solo se da por finalizada cuando el impacto sobre el negocio ha desaparecido en su totalidad y el Incident Manager con el CSO autorizan el cierre.
4. **Escalado Operativo por Envejecimiento (*Aging Escalation*):**
   > [!IMPORTANT]
   > Si una incidencia activa clasificada como **P2 / SL2** acumula **$\ge 120$ minutos** desde su apertura sin que exista un workaround efectivo autorizado ni resolución, el motor la escala automáticamente a **P1 / SL1** (`aging_escalated = true`), exigiendo la intervención urgente del Incident Manager y convocatoria de War Room.

---

## 4. Detección de Discrepancias (Subescalación N1) y Clasificación por Niveles $\Delta$

Una de las aportaciones más críticas del motor es la detección de tickets mal clasificados en origen mediante la función `compute_discrepancy_details`:

```python
def compute_discrepancy_details(original_priority: Optional[str], calculated_priority: str, reasons: Optional[list[str]] = None) -> dict[str, Any]:
    norm_orig = normalize_priority(original_priority)
    norm_calc = normalize_priority(calculated_priority)
    orig_rank = PRIORITY_RANKS.get(norm_orig, 3)   # P1=1, P2=2, P3=3, P4=4
    calc_rank = PRIORITY_RANKS.get(norm_calc, 3)
    
    delta = max(0, orig_rank - calc_rank)
    # delta > 0 indica que la prioridad calculada por ITIL supera la nominal de Remedy
    ...
```

### Escala Gradual de Gravedad por Salto de Nivel ($\Delta$)

| Nivel $\Delta$ | Clasificación de Gravedad | Salto de Prioridad Típico | Impacto Operativo y Acción Requerida |
| :---: | :--- | :--- | :--- |
| **$\Delta = 0$** | **Sin Discrepancia** | P1 $\to$ P1, P2 $\to$ P2 | La clasificación de N1 es correcta y coincide con los umbrales ITIL. |
| **$\Delta = 1$** | **Moderada** | P3 $\to$ P2 o P2 $\to$ P1 | Subescalación de un nivel. Requiere ajuste administrativo y seguimiento prioritario. |
| **$\Delta = 2$** | **Mayor Severa** | P3 $\to$ P1 o P4 $\to$ P2 | Salto de dos niveles. Típico de tickets críticos abiertos como *Media* por N1. Requiere reetiquetado inmediato en Remedy y reporte a IM-CSO. |
| **$\Delta \ge 3$** | **Crítica Extrema** | P4 $\to$ P1 | Subescalación masiva (ticket registrado como *Baja* con caída global o $\ge 500$ usuarios). Activa alarma inmediata de triaje y feedback a supervisión de N1. |

### Causa Determinante y Explicabilidad
Cada discrepancia genera un texto explicativo auditable (`discrepancia_motivo`) combinando la gravedad del salto con la causa técnica directa (ej. umbral de sedes, afectación crítica de frontales o envejecimiento operativo).

---

## 5. Control de SLAs Operativos y Escalados de Crisis

Para cada ticket evaluado en alta prioridad (P1, P2 o Discrepancia), la función `compute_emergency_sla_status` calcula los cronómetros oficiales de Orange IT Emergency Management:

```mermaid
timeline
    title Cronología de Escalados de Emergencias IT (Orange)
    T + 0 min : Apertura del Ticket / Detección
    T + 20 min : Vencimiento SLA 1ª Notificación a Dirección
    T + 45 min : Escalado Telefónico Obligatorio a N3 / Proveedor (Vía Telefónica)
    T + 60 min : Cadencia de actualización obligatoria a Negocio
    T + 105 min : 2º Escalado Telefónico a Estamentos Superiores y CSO (+1h tras 45m)
    T + 120 min : Alarma de Incumplimiento SLA Objetivo P1 (War Room activa)
```

* **`minutos_desde_apertura`**: Tiempo transcurrido desde la creación en Remedy.
* **`sla_primera_notificacion_vencido`**: `True` si han transcurrido más de **20 minutos** sin emitir comunicación oficial.
* **`requiere_escalado_telefonico`**: `True` si han transcurrido **$\ge$ 45 minutos** (exige llamada telefónica obligatoria, no correo ni chat).
* **`escalado_estamentos_superiores`**: `True` si han transcurrido **$\ge$ 105 minutos** (45 min + 1 hora adicional sin resolución).

---

## 6. Salida Estructurada en el Catálogo JSON

El resultado del triaje se almacena dentro de cada incidencia en el campo `"evaluacion"` del fichero [`high_priority_notifications.json`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/data/output/high_priority_notifications.json):

```json
{
  "id": "INC000004122710",
  "titulo": "FICHA DE CLIENTE // OEST OVIEDO // ERROR FUNCIONAL",
  "sistemas": ["Ficha de Cliente", "TEIDE", "PeopleSoft", "MDG", "Siebel 8", "BSCS/PS"],
  "prioridad_original": "Media",
  "prioridad_sugerida": "P1",
  "es_alta_prioridad": true,
  "es_discrepancia": true,
  "discrepancia_delta": 2,
  "discrepancia_gravedad": "Mayor Severa",
  "discrepancia_motivo": "Subescalación severa (+2 niveles): Ticket registrado como P3 y evaluado como P1. Causa determinante: Afectación crítica o corte global sobre el servicio principal sin alternativa viable.; Impacto activo en vivo que requiere restablecimiento inmediato.",
  "aging_escalated": false,
  "evaluacion": {
    "proceso": "Atención al Cliente (ATC)",
    "proceso_negocio": "Atención al Cliente (ATC)",
    "dominio_tecnico": "Sistemas Core",
    "criterio": "ATC (3.1): Frontales/CRM (>20% desviación en 30m) o Regla de Oro N1",
    "impacto": "Alto",
    "impacto_justificacion": "Epsilon IA: Alto. Afecta a proceso crítico de recogidas de equipos en bajas de servicios fijo. Riesgo de comunicaciones fallidas y penalizaciones incorrectas a clientes. Impacto 100% en operativa.",
    "urgencia": "Alta",
    "urgencia_justificacion": "Impacto activo en vivo que requiere restablecimiento inmediato.",
    "workaround": "No",
    "workaround_gobernanza": "Sin workaround (Resolución directa requerida)",
    "metricas_cuantitativas": {
      "sedes": null,
      "usuarios": null,
      "desviacion_pct": null,
      "detalles": []
    },
    "sla_objetivo_minutos": 120,
    "fecha_apertura": "14/10/2026 13:26",
    "minutos_desde_apertura": 4240,
    "sla_primera_notificacion_vencido": true,
    "requiere_escalado_telefonico": true,
    "escalado_estamentos_superiores": true,
    "proxima_ventana_update_minutos": 20
  }
}
```

### KPIs de Metadatos del Catálogo
El encabezado `_metadata.kpis` consolida el resumen ejecutivo de la evaluación:
* `total_scanned`, `terminal_skipped_count`, `active_evaluated_count`.
* `total_high_priority`, `p1_critical_count`, `p2_high_count`.
* `discrepancies_count`, `discrepancias_delta1_moderada_count`, `discrepancias_delta2_mayor_count`, `discrepancias_delta3_critica_count`.
* `aging_escaladas_p1_count`.
* `sla_primera_notificacion_vencidos_count`, `requiere_escalado_telefonico_count`, `workaround_pendientes_cso_count`.

---

## 7. Ejecución y Diagnóstico CLI

El triaje se ejecuta automáticamente en cada subida de CSV o puede ejecutarse manualmente desde la consola:

### Modo estándar (con fallback inteligente a Epsilon IA)

```powershell
python converters/cli/evaluate_incident_notifications.py
```

### Forzar fichero de entrada específico y salida

```powershell
python converters/cli/evaluate_incident_notifications.py `
    --input "data/output/CS-Informe incidencias P1,  P2 y P3 - 2026 - 30 Oct 2026-massive.json" `
    --output "data/output/high_priority_notifications.json"
```

### Ejecución en modo simulador (Dry Run)

Permite inspeccionar los KPIs de triaje y discrepancias en pantalla sin escribir en disco:

```powershell
python converters/cli/evaluate_incident_notifications.py --dry-run
```

---

## 8. Documentos y Referencias Relacionadas

* **[CATALOGO-INCIDENCIAS-ALTA-PRIORIDAD.md](CATALOGO-INCIDENCIAS-ALTA-PRIORIDAD.md)**: Especificación técnica integral del catálogo JSON `high_priority_notifications.json`.
* **[INCIDENT-EXECUTIVE-NOTIFICATIONS-WORKFLOW.md](INCIDENT-EXECUTIVE-NOTIFICATIONS-WORKFLOW.md)**: Flujo de redacción de mensajes oficiales para Dirección con la skill `incident-executive-notifications`.
* **[MANUAL-OPERADOR-CONSOLA-OPERATIVA.md](MANUAL-OPERADOR-CONSOLA-OPERATIVA.md)**: Manual del Incident Manager en la Consola de Emergencias IT.
* **[it-severity-matrix SKILL.md](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/.agents/skills/it-severity-matrix/SKILL.md)**: Matriz cuantitativa oficial de severidades IT.
* **[orange-it-emergency-management SKILL.md](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/.agents/skills/orange-it-emergency-management/SKILL.md)**: Protocolos operativos de escalado, War Room y gobernanza RACI.
