# Documento de Casos de Uso, Evaluación de Calidad y Detección de Gaps: Módulo 1
## *Motor de Inspección Continua, Umbrales Críticos y Alertas de Subescalación (SL1/P1 & SL2/P2)*

**Código del Documento:** `DOC-UCM1-TRIAGE-GAP-01`  
**Versión:** 1.0.0  
**Fecha de Publicación:** 31 de Octubre de 2026  
**Área Responsable:** Orange Tech Operations · Customer & Service Ops (IM-CSO) · QA de Software Operacional  
**Clasificación:** Uso Interno Operativo / Documentación de Ingeniería y Operaciones  
**Sistema Evaluado (SUT):** Consola de Triaje y Reclasificación Automática (`dashboards/emergency-triage-console`) — Módulo 1  

---

## 📑 Índice de Contenidos

1. [Propósito y Objetivos de la Evaluación](#1-propósito-y-objetivos-de-la-evaluación)
2. [Arquitectura Funcional del Módulo 1 Bajo Prueba (SUT)](#2-arquitectura-funcional-del-módulo-1-bajo-prueba-sut)
3. [Catálogo de Casos de Uso Operativos (Escenarios de Prueba)](#3-catálogo-de-casos-de-uso-operativos-escenarios-de-prueba)
   - [UC-M1-01: Caída de Frontales en Atención al Cliente (ATC) subescalada nominalmente a P3](#uc-m1-01-caída-de-frontales-en-atención-al-cliente-atc-subescalada-nominalmente-a-p3)
   - [UC-M1-02: Retraso en Mediación y Facturación (HPFMS / CAS) con ventana de corte inminente](#uc-m1-02-retraso-en-mediación-y-facturación-hpfms--cas-con-ventana-de-corte-inminente)
   - [UC-M1-03: Bloqueo de Aprovisionamiento (TEIDE / SGA) con 100% órdenes detenidas](#uc-m1-03-bloqueo-de-aprovisionamiento-teide--sga-con-100-órdenes-detenidas)
   - [UC-M1-04: Degradación Silenciosa de Middleware Transversal (TIBCO / JMS Colas) con Impacto Multiproceso](#uc-m1-04-degradación-silenciosa-de-middleware-transversal-tibco--jms-colas-con-impacto-multiproceso)
   - [UC-M1-05: Fallo de Nodo en Infraestructura Core Cloud (ESX / Exadata / OCI) con Alta Disponibilidad comprometida](#uc-m1-05-fallo-de-nodo-en-infraestructura-core-cloud-esx--exadata--oci-con-alta-disponibilidad-comprometida)
   - [UC-M1-06: Filtrado Anti-Saturación de Estados Terminales y Tickets Cosméticos (P4/P3 sin impacto)](#uc-m1-06-filtrado-anti-saturación-de-estados-terminales-y-tickets-cosméticos-p4p3-sin-impacto)
   - [UC-M1-07: Resiliencia ante Caída o Timeout del Microservicio Epsilon Resumen IA (Degradación Elegante)](#uc-m1-07-resiliencia-ante-caída-o-timeout-del-microservicio-epsilon-resumen-ia-degradación-elegante)
   - [UC-M1-08: Estrés de Ingesta Masiva, Polling Continuo y Estabilidad Visual (Anti-Flicker)](#uc-m1-08-estrés-de-ingesta-masiva-polling-continuo-y-estabilidad-visual-anti-flicker)
4. [Matriz de Detección de Gaps Funcionales](#4-matriz-de-detección-de-gaps-funcionales)
5. [Matriz de Detección de Gaps Operativos](#5-matriz-de-detección-de-gaps-operativos)
6. [Protocolo y Plantilla de Ejecución de Pruebas (Test Execution Protocol)](#6-protocolo-y-plantilla-de-ejecución-de-pruebas-test-execution-protocol)
7. [Matriz de Priorización de Mejoras y Roadmap de Mitigación (MoSCoW)](#7-matriz-de-priorización-de-mejoras-y-roadmap-de-mitigación-moscow)

---

## 1. Propósito y Objetivos de la Evaluación

El **Módulo 1 de la Consola de Triaje y Reclasificación Automática** fue concebido para erradicar el riesgo operativo más severo en el Command Center (N1) de Orange Tech Operations: **la subescalación inadvertida de incidencias críticas**. En infraestructuras masivas de telecomunicaciones, es frecuente que tickets con impacto devastador en clientes o ingresos sean clasificados inicialmente por agentes de primer nivel como `Prioridad Media (P3)` o `Baja (P4)` debido a descripciones ambiguas, falta de visibilidad del backend o presiones operativas.

El objetivo de este documento es:
1. **Modelar formalmente 8 casos de uso tácticos** representativos de la operación real (incluyendo situaciones nominales, bordes críticos, fallas de microservicios y picos de volumen).
2. **Establecer los criterios de aceptación cuantitativos** para verificar la exactitud algorítmica de la matriz ITIL y el comportamiento de la interfaz gráfica.
3. **Identificar y categorizar sistemáticamente los Gaps Funcionales** (debilidades lógicas, datos no cubiertos, contratos incompletos) y **Gaps Operativos** (fricción para el Incident Manager en guardia, tiempos de respuesta, integración con Remedy ITSM).
4. **Proporcionar un plan de acción priorizado (MoSCoW)** para evolucionar el módulo desde su versión actual hacia un componente de grado de producción industrial.

> [!IMPORTANT]
> **Marco Regulatorio y Reglas del Proyecto (`AGENTS.md`):**  
> Todos los casos de prueba y evaluaciones deben cumplir estrictamente la **Regla Anti-Alucinación** (no inventar métricas ni causas no soportadas por la evidencia) y la **Regla de Oro N1** (ante cualquier ambigüedad en procesos críticos, clasificar automáticamente en SL1/P1).

---

## 2. Arquitectura Funcional del Módulo 1 Bajo Prueba (SUT)

El Módulo 1 está articulado en tres funciones acopladas que procesan el flujo de datos desde la ingesta hasta la acción del operador:

```mermaid
flowchart TD
    subgraph "Entorno Externo / Fuentes de Datos"
        R["Remedy ITSM<br/>(Volcado JSON / CSV)"]
        E["Microservicio Epsilon IA<br/>(Proxy 8081 / soptmc.si.orange.es)"]
    end

    subgraph "MÓDULO 1: Motor de Triaje y Reclasificación"
        F1["Función 1: Ingesta & Inspección Continua<br/>• Polling configurable (15s / 30s / 60s)<br/>• Descarte estados terminales<br/>• Recuento de KPIs activos"]
        F2["Función 2: Evaluador Determinista ITIL<br/>• Enriquecimiento contextual dual<br/>• Ponderación multidominio (6 procesos + 4 técnicos)<br/>• Regla de Oro N1 y umbrales cuantitativos"]
        F3["Función 3: Subescalaciones & Cockpit Tabular<br/>• Detección de discrepancias nominal vs sugerida<br/>• Cálculo de Delta de Severidad<br/>• Generación de plantilla formal para Remedy<br/>• Vista tabular compacta con detalle colapsable"]
    end

    subgraph "Salidas y Acciones Operativas"
        K["Panel de KPIs en Vivo<br/>(Ingestadas / Discrepancias / SL1 / SL2)"]
        T["Tabla de Triaje Desplegable<br/>(Filtros por Proceso, Severidad y Modo)"]
        M["Modal de Justificación Técnica<br/>(Copiar al Portapapeles para Remedy)"]
        H["Handoff al Módulo 2<br/>(Paso de ticket a Orquestador / War Room)"]
    end

    R --> F1
    E --> F2
    F1 --> F2
    F2 --> F3
    F3 --> K
    F3 --> T
    F3 --> M
    F3 -.->|Confirmación SL1| H
```

### Entradas, Salidas y Estados del Módulo 1:

| Componente | Entrada (Input) | Salida Esperada (Output) | Dependencia |
| :--- | :--- | :--- | :--- |
| **Función 1: Ingesta** | `data/output/high_priority_notifications.json` o endpoint de feed masivo | Arrays de tickets activos descartando estados terminales; cálculo de aging del feed | Sistema de ficheros o API de Remedy |
| **Función 2: Evaluación** | Corpus textual Remedy + Diagnóstico de `EpsilonClient` | Objeto `evaluacion`: proceso crítico, dominio técnico, severidad sugerida (`SL1`-`SL4`), justificación de umbral | Motor `SeverityEvaluator` |
| **Función 3: Alertas** | Severidad nominal de Remedy vs Severidad sugerida | Flag `es_discrepancia`, valor `delta_severidad`, badge tabular, modal de texto formal para Remedy | Interfaz Web `triage.js` / `triage.css` |

---

## 3. Catálogo de Casos de Uso Operativos (Escenarios de Prueba)

A continuación se detallan los 8 escenarios de prueba exhaustivos para evaluar el comportamiento del Módulo 1 frente a condiciones nominales y de frontera.

---

### UC-M1-01: Caída de Frontales en Atención al Cliente (ATC) subescalada nominalmente a P3

* **Identificador:** `UC-M1-01`
* **Proceso de Negocio:** Atención al Cliente (ATC)
* **Objetivo de la Prueba:** Validar que el motor detecte la degradación de un frontal comercial crítico catalogado erróneamente como P3 por el soporte de primer nivel y fuerce su subescalación inmediata a SL1/P1 aplicando la Regla de Oro N1.
* **Actor Principal:** Incident Manager de Turno (IM-CSO) / Operador de Command Center.
* **Precondiciones:** La Consola de Triaje tiene activa la inspección continua (intervalo 30s) y el feed contiene tickets activos.

#### Datos de Entrada (Payload del Ticket):
```json
{
  "id": "INC000004171670",
  "titulo": "Lentitud generalizada y errores 504 en Ficha de Cliente Orange",
  "descripcion": "Operadores de call center reportan que la Ficha de Cliente tarda más de 20 segundos en cargar y en un 35% de los casos devuelve timeout gateway 504. Frontales afectados: CRM4TELCO y DES_SOE_FICHA.",
  "prioridad_nominal": "Media",
  "urgencia": "Media",
  "impacto": "Medio",
  "grupo_asignado": "SOPORTE FRONTALES COMERCIALES",
  "estado": "Asignado",
  "fecha_creacion": "2026-10-31T12:45:00+01:00",
  "epsilon_ia": {
    "problema": "Saturación de conexiones HTTP en ingress gateway hacia pods de Ficha de Cliente.",
    "impacto": "Más de 1.800 agentes de atención sin acceso a datos de clientes. Desvío de llamadas superior al 25% en los últimos 20 minutos.",
    "sistemas": ["Ficha de Cliente Orange", "CRM4TELCO", "DES_SOE_FICHA"],
    "solucion": "Escalado horizontal de réplicas en cluster Kubernetes y reinicio de pods colgados.",
    "bloqueos": ["Pendiente autorización de cambio de emergencia por IM"]
  }
}
```

#### Comportamiento Esperado del Motor (Paso a Paso):
1. **F1 (Ingesta):** Ingesta el ticket `INC000004171670`, verifica que su estado `Asignado` no es terminal y lo computa en el KPI `Activas Ingestadas`.
2. **F2 (Evaluación):** 
   - La matriz ponderada identifica el proceso **Atención al Cliente (ATC)** con peso prioritario por coincidencia de sistemas (`Ficha de Cliente`, `CRM4TELCO`).
   - Evalúa el umbral cuantitativo: desvío/afectación >20% en 30 minutos.
   - Aplica la **Regla de Oro N1**: ante indisponibilidad del frontal corporativo de atención, la severidad obligatoria es **SL1 / P1**.
3. **F3 (Subescalación & UI):**
   - Compara Severidad Nominal (`P3 / Media`) con Severidad Sugerida (`SL1 / P1`).
   - Calcula discrepancia activa con **Delta = +2 niveles**.
   - Incrementa el KPI `Discrepancias N1` (+1) y `Emergencias SL1 / P1` (+1).
   - En la tabla de triaje, la fila aparece con el badge ámbar `⚠️ P3 ➔ SL1` y botón destacado `📋 Ver Justificación`.
   - Al pulsar `Ver Justificación`, el modal presenta la plantilla formal de reclasificación para Remedy:
     > *"INCIDENCIA SUBCATALOGADA COMO P3. CRITERIO DE SUBCLASIFICACIÓN: Superación de umbral crítico en Proceso ATC (>20% de afectación en frontales de Ficha de Cliente). Severidad requerida: SL1 / P1 según Matriz Oficial Orange ITIL."*

#### Criterios de Aceptación Cuantitativos:
* `evaluacion.prioridad_sugerida` == `"P1"` / `SL1`.
* `es_discrepancia` == `true`.
* `delta_severidad` == `2`.
* `evaluacion.proceso_negocio` == `"Atención al Cliente (ATC)"`.
* La pestaña `Reclasificación Inmediata` debe filtrar y mostrar este ticket como primera prioridad.

---

### UC-M1-02: Retraso en Mediación y Facturación (HPFMS / CAS) con ventana de corte inminente

* **Identificador:** `UC-M1-02`
* **Proceso de Negocio:** Facturación, Mediación y Cobros
* **Objetivo de la Prueba:** Verificar que retrasos en el vaciado de ficheros de mediación o tarificación que superen la ventana de seguridad de 2 horas disparen la subescalación preventiva antes de que se produzca una pérdida de facturación no recuperable.
* **Actor Principal:** Incident Manager / Especialista de Guardia de Facturación.

#### Datos de Entrada (Payload del Ticket):
```json
{
  "id": "INC000004172890",
  "titulo": "Acumulación de ficheros CDR en mediación HPFMS interfaz CAS",
  "descripcion": "El recolector HPFMS lleva 2.5 horas sin volcar registros de llamadas y datos móviles hacia CAS de tarificación prepago. Colas de disco al 88%.",
  "prioridad_nominal": "Media",
  "urgencia": "Media",
  "impacto": "Medio",
  "grupo_asignado": "SISTEMAS DE FACTURACION Y MEDIACION",
  "estado": "En Curso",
  "fecha_creacion": "2026-10-31T11:00:00+01:00",
  "epsilon_ia": {
    "problema": "Proceso demonio de transferencia detenido por bloqueo en base de datos Oracle CAS.",
    "impacto": "Retraso de mediación de 2 horas y 30 minutos. Riesgo inminente de descarte de CDRs por overflow de colas temporales.",
    "sistemas": ["HPFMS", "CAS", "BSCS"],
    "solucion": "Liberar locks de tablas en Oracle y relanzar demonio hpfms_collector.",
    "bloqueos": []
  }
}
```

#### Comportamiento Esperado del Motor:
1. El motor clasifica el ticket en **Facturación, Mediación y Cobros**.
2. Comprueba el umbral específico de Facturación: *"Retraso >2 horas en proceso de mediación o tarificación en tiempo real"*.
3. Como el retraso documentado es de **2.5 horas**, determina que se ha rebasado el umbral de emergencia.
4. Dictamina Severidad Sugerida **SL1 / P1** frente a la nominal `P3`.
5. En la interfaz gráfica, la tarjeta desplegable muestra en la sección `Criterio Aplicado` el texto oficial del umbral de mediación y resalta en rojo las métricas cuantitativas (`2.5 horas de retraso > 2.0h límite`).

#### Criterios de Aceptación Cuantitativos:
* `evaluacion.prioridad_sugerida` == `"P1"`.
* `evaluacion.proceso_negocio` == `"Facturación, Mediación y Cobros"`.
* `evaluacion.criterio` contiene explícitamente el umbral de las 2 horas de mediación.

---

### UC-M1-03: Bloqueo de Aprovisionamiento (TEIDE / SGA) con 100% órdenes detenidas

* **Identificador:** `UC-M1-03`
* **Proceso de Negocio:** Provisión y Activación
* **Objetivo de la Prueba:** Validar la subescalación de un ticket categorizado como P2 (Alta) a SL1 (Emergencia Crítica) cuando la provisión fija o móvil está totalmente paralizada durante más de 10 minutos.
* **Actor Principal:** Incident Manager / Command Center SMC.

#### Datos de Entrada (Payload del Ticket):
```json
{
  "id": "INC000004173110",
  "titulo": "Parada de encolamiento de órdenes de fibra en TEIDE y SGA",
  "descripcion": "El gestor de colas de provisión de fibra FTTH se encuentra detenido. No se están despachando órdenes hacia la red desde las 12:50. Afecta a altas nuevas y portabilidades fijas.",
  "prioridad_nominal": "Alta",
  "urgencia": "Alta",
  "impacto": "Medio",
  "grupo_asignado": "SMC PROVISION FIJA",
  "estado": "Asignado",
  "fecha_creacion": "2026-10-31T13:05:00+01:00",
  "epsilon_ia": {
    "problema": "Deadlock en la cola JMS de despacho hacia SGA Provisioning Engine.",
    "impacto": "100% de las órdenes de provisión de fibra paradas durante 15 minutos consecutivos. Más de 450 clientes en espera de activación.",
    "sistemas": ["TEIDE", "SGA", "PeopleSoft"],
    "solucion": "Purgar mensajes con error y relanzar colas de despacho.",
    "bloqueos": []
  }
}
```

#### Comportamiento Esperado del Motor:
1. Clasifica el ticket en **Provisión y Activación**.
2. Evalúa los dos umbrales de provisión:
   - Umbral P2: >20% órdenes en error en móvil o >30% en fijo.
   - **Umbral SL1 / Emergencia:** 100% de provisiones paradas durante más de 10 minutos.
3. Al detectar que el 100% de las órdenes están paradas durante **15 minutos**, escala la prioridad sugerida a **SL1 / P1**.
4. Genera una discrepancia con Delta = +1 (`P2 ➔ SL1`).
5. La consola actualiza la fila con badge rojo de emergencia y habilita el botón de transición directa al Módulo 2 (`🚨 Abrir Orquestador SL1`).

#### Criterios de Aceptación Cuantitativos:
* `evaluacion.prioridad_sugerida` == `"P1"`.
* `prioridad_nominal` == `"P2"`.
* `delta_severidad` == `1`.
* `es_discrepancia` == `true`.

---

### UC-M1-04: Degradación Silenciosa de Middleware Transversal (TIBCO / JMS Colas) con Impacto Multiproceso

* **Identificador:** `UC-M1-04`
* **Dominio Técnico:** Middleware Transversal e Integración (TIBCO / ESB / JMS)
* **Objetivo de la Prueba:** Evaluar la capacidad de doble etiquetado del motor para tickets técnicos donde el título solo menciona infraestructura de integración, deduciendo el impacto real en los procesos de negocio dependientes.
* **Actor Principal:** Incident Manager / Ingeniero de Middleware.

#### Datos de Entrada (Payload del Ticket):
```json
{
  "id": "INC000004174005",
  "titulo": "Saturación de colas EMS en cluster TIBCO BusinessWorks nodo central",
  "descripcion": "Alertas de colas de mensajes EMS superando el umbral del 90% de capacidad en servidores TIBCO BW. No se reciben errores HTTP en frontales pero las transacciones quedan encoladas.",
  "prioridad_nominal": "Media",
  "urgencia": "Media",
  "impacto": "Medio",
  "grupo_asignado": "OPERACIONES MIDDLEWARE CORE",
  "estado": "En Curso",
  "fecha_creacion": "2026-10-31T12:00:00+01:00",
  "epsilon_ia": {
    "problema": "Desconexión entre el bus JMS de TIBCO y el backend de Siebel IP24.",
    "impacto": "Bloqueo transversal en el intercambio de mensajes entre Ficha de Cliente, Contratación y Facturación.",
    "sistemas": ["TIBCO", "EMS", "Siebel IP24", "BW"],
    "solucion": "Reinicio escalonado de engines BW y vaciado de colas muertas (DLQ).",
    "bloqueos": ["Esperando trazado de red"]
  }
}
```

#### Comportamiento Esperado del Motor:
1. El motor ejecuta la fase de doble etiquetado:
   - `dominio_tecnico`: **Middleware Transversal e Integración**.
   - `proceso_negocio`: Deduce afectación transversal en **Atención al Cliente** y **Facturación**.
2. Aplica la regla específica de Middleware Transversal: *"La saturación o corte del bus core (TIBCO/OSB) con afectación a más de 2 dominios de negocio se clasifica como SL1 / Emergencia Nacional"*.
3. Emite Severidad Sugerida **SL1 / P1** y marca discrepancia contra el nominal `P3`.
4. En el desglose de criterios del dashboard, muestra tanto la justificación de infraestructura técnica como la de negocio.

#### Criterios de Aceptación Cuantitativos:
* `evaluacion.dominio_tecnico` == `"Middleware Transversal"`.
* `evaluacion.prioridad_sugerida` == `"P1"`.
* La justificación textual cita la afectación multiproceso derivada del bus de integración.

---

### UC-M1-05: Fallo de Nodo en Infraestructura Core Cloud (ESX / Exadata / OCI) con Alta Disponibilidad comprometida

* **Identificador:** `UC-M1-05`
* **Dominio Técnico:** Infraestructura Core, Almacenamiento y Cloud
* **Objetivo de la Prueba:** Comprobar la correcta aplicación de severidad SL2 (Incidencia Mayor) ante la pérdida de redundancia en un cluster crítico sin caída del servicio final.
* **Actor Principal:** Incident Manager / DBA de Producción.

#### Datos de Entrada (Payload del Ticket):
```json
{
  "id": "INC000004175220",
  "titulo": "Caída de nodo primario en cluster Oracle Exadata DB-PROD-01",
  "descripcion": "El nodo 1 del cluster Exadata ha sufrido un kernel panic y se ha reiniciado inesperadamente. El nodo 2 ha asumido el tráfico mediante Transparent Application Failover (TAF).",
  "prioridad_nominal": "Baja",
  "urgencia": "Baja",
  "impacto": "Bajo",
  "grupo_asignado": "DBA INFRAESTRUCTURA CORE",
  "estado": "Asignado",
  "fecha_creacion": "2026-10-31T10:30:00+01:00",
  "epsilon_ia": {
    "problema": "Fallo físico en placa base del compute node 1 de Exadata.",
    "impacto": "Base de datos operando en single node (sin redundancia de alta disponibilidad). Si falla el nodo 2, caída total de cobros y facturación.",
    "sistemas": ["Oracle Exadata", "RAC", "Storage Cell"],
    "solucion": "Sustitución de componente de hardware por soporte de fabricante Oracle.",
    "bloqueos": ["Esperando técnico de campo Oracle"]
  }
}
```

#### Comportamiento Esperado del Motor:
1. El motor clasifica el ticket en **Infraestructura Core y Cloud**.
2. Evalúa la regla de redundancia: *"Caída de un nodo en cluster crítico (Exadata/ESX) con pérdida de redundancia pero sin corte de servicio actual = Severidad SL2 / P2 (Incidencia Mayor)"*.
3. Compara Nominal `P4 / Baja` contra Sugerida `SL2 / P2`.
4. Dispara discrepancia de **Delta = +2 niveles** (`P4 ➔ SL2`).
5. En la interfaz se clasifica en el contador `Incidencias SL2 / P2` y se resalta la necesidad de intervención urgente del equipo de infraestructura antes de agotar la ventana de contingencia.

#### Criterios de Aceptación Cuantitativos:
* `evaluacion.prioridad_sugerida` == `"P2"`.
* `prioridad_nominal` == `"P4"`.
* `delta_severidad` == `2`.
* `es_discrepancia` == `true`.

---

### UC-M1-06: Filtrado Anti-Saturación de Estados Terminales y Tickets Cosméticos (P4/P3 sin impacto)

* **Identificador:** `UC-M1-06`
* **Proceso de Negocio:** No Crítico / Mantenimiento
* **Objetivo de la Prueba:** Verificar que el motor filtre rigurosamente tickets en estados finales (`Cerrado`, `Resuelto`, `Cancelado`) y clasifique adecuadamente incidencias cosméticas o de bajo impacto sin generar falsas alarmas ni saturar la bandeja del Incident Manager.
* **Actor Principal:** Motor Automatizado de Ingesta (F1).

#### Datos de Entrada (Payload con 2 Tickets):
```json
[
  {
    "id": "INC000004176001",
    "titulo": "Error en color de botón de portal web corporativo",
    "descripcion": "El botón de contacto en la página informativa de empresas muestra un tono gris en lugar de naranja en navegadores Safari.",
    "prioridad_nominal": "Baja",
    "urgencia": "Baja",
    "impacto": "Bajo",
    "grupo_asignado": "FRONTEND WEB CORPORATIVA",
    "estado": "Asignado",
    "fecha_creacion": "2026-10-31T09:00:00+01:00",
    "epsilon_ia": {
      "problema": "Regla CSS mal aplicada en Safari.",
      "impacto": "Problema meramente cosmético sin afectación de navegación ni contratación.",
      "sistemas": ["WEB PUBLICA"],
      "solucion": "Ajuste de estilo CSS en próximo sprint.",
      "bloqueos": []
    }
  },
  {
    "id": "INC000004176002",
    "titulo": "Caída masiva de fibra en polígono industrial (Resuelta)",
    "descripcion": "Incidencia de corte de fibra resuelta tras empalme del cable afectado.",
    "prioridad_nominal": "Crítica",
    "urgencia": "Crítica",
    "impacto": "Alto",
    "grupo_asignado": "SOPORTE FIBRA RED",
    "estado": "Resuelto",
    "fecha_creacion": "2026-10-31T07:00:00+01:00",
    "epsilon_ia": {
      "problema": "Corte de cable por obras ajenas.",
      "impacto": "Servicio completamente restablecido a las 08:30.",
      "sistemas": ["RED FTTH"],
      "solucion": "Empalme de cable ejecutado con éxito.",
      "bloqueos": []
    }
  }
]
```

#### Comportamiento Esperado del Motor:
1. Para `INC000004176002`: Al estar en estado `Resuelto`, el motor lo **descarta inmediatamente** en la Fase 1. Se suma al contador interno de omitidos terminales y no aparece en la tabla de triaje activo.
2. Para `INC000004176001`: Ingesta el ticket activo, evalúa los umbrales y confirma que **no existe superación de ningún umbral crítico**.
3. Emite Severidad Sugerida `P4 / SL4` coincidente con la nominal `P4`.
4. El flag `es_discrepancia` es `false` y el delta es `0`.
5. No genera alertas en la pestaña `Reclasificación Inmediata`; únicamente es visible si el operador activa la pestaña `Todas las Incidencias`.

#### Criterios de Aceptación Cuantitativos:
* `INC000004176002` no aparece en el listado activo de la consola.
* `INC000004176001.evaluacion.prioridad_sugerida` == `"P4"`.
* `INC000004176001.es_discrepancia` == `false`.
* `delta_severidad` == `0`.

---

### UC-M1-07: Resiliencia ante Caída o Timeout del Microservicio Epsilon Resumen IA (Degradación Elegante)

* **Identificador:** `UC-M1-07`
* **Proceso de Negocio:** Todos (Mecanismo de Resiliencia)
* **Objetivo de la Prueba:** Comprobar que, ante la indisponibilidad de la API de Epsilon Resumen IA (código HTTP 500, timeout o sin red), el Módulo 1 no se bloquee ni arroje excepciones no controladas, sino que degrade elegantemente su análisis a los metadatos nativos de Remedy e informe de ello al usuario.
* **Actor Principal:** Cliente de Ingesta / EpsilonClient.

#### Datos de Entrada:
* Ticket con descripción de caída crítica en CRM4TELCO.
* Microservicio Epsilon configurado para simular `HTTP 503 Service Unavailable` o timeout de 5 segundos.

#### Comportamiento Esperado del Motor:
1. El backend / cliente CLI detecta el fallo de comunicación con Epsilon.
2. Utiliza la caché persistente en disco (`data/.epsilon_cache/`) si existe un diagnóstico previo del ticket.
3. Si no existe en caché, activa el **Modo de Degradación Heurística Nativa**: realiza la clasificación de proceso y severidad basándose exclusivamente en el `Título`, `Descripción`, `Grupo Asignado` e `Impacto/Urgencia` de Remedy.
4. En el catálogo generado, el objeto incluye: `"epsilon_enriquecido": false` y `"aviso_ia": "Diagnóstico IA no disponible · Análisis basado en Remedy nativo"`.
5. En la interfaz web (`triage.js`), el bloque de diagnóstico IA de la tarjeta muestra un cartel informativo en gris: `ℹ️ Diagnóstico Epsilon IA no disponible para este ticket. Clasificación efectuada con metadatos nativos de Remedy.`
6. La evaluación de severidad y detección de discrepancia sigue funcionando con total precisión.

#### Criterios de Aceptación Cuantitativos:
* El ciclo de inspección no arroja errores `Uncaught Exception` en consola.
* La severidad de emergencia SL1 se sigue calculando con los datos nativos de Remedy.
* La interfaz muestra el banner de advertencia no bloqueante.

---

### UC-M1-08: Estrés de Ingesta Masiva, Polling Continuo y Estabilidad Visual (Anti-Flicker)

* **Identificador:** `UC-M1-08`
* **Proceso de Negocio:** Transversal (Rendimiento y Usabilidad)
* **Objetivo de la Prueba:** Validar que con un catálogo de más de 100 tickets activos y un ciclo de polling intensivo (cada 15 segundos), la consola no experimente parpadeos visuales (*flickering*), mantenga el estado de las filas que el operador ha desplegado manualmente y no sufra fugas de memoria (*memory leaks*).
* **Actor Principal:** Operador en Turno de Supervisión Activa.

#### Condiciones de la Prueba:
* Dataset sintético de 120 incidencias activas (con 15 discrepancias SL1/SL2 distribuidas).
* Selector de refresco configurado en `Inspección: cada 15s`.
* Operador expande los detalles de 3 filas específicas e introduce un término de búsqueda en el input de filtrado (`"CRM"`).

#### Comportamiento Esperado del Motor:
1. Cada 15 segundos, la llamada `performInspection()` lee el origen de datos.
2. Compara el `checksum` o timestamp del feed para determinar si hubo cambios reales en el catálogo.
3. Si los datos no han cambiado: actualiza únicamente el indicador de última inspección (`hace 0s`) sin re-renderizar el DOM ni cerrar las filas expandidas.
4. Si los datos han cambiado: re-renderiza la tabla conservando el estado de expansión de las filas previamente abiertas por el usuario (`state.expandedIncidentIds`).
5. El término introducido en el filtro de búsqueda (`"CRM"`) y la pestaña activa (`Reclasificación Inmediata`) se mantienen intactos.
6. El consumo de memoria del navegador se mantiene constante tras 60 ciclos de refresco sucesivos.

#### Criterios de Aceptación Cuantitativos:
* Cero cierres accidentales de tarjetas expandidas durante el polling.
* Tiempo de ejecución de `processInspectionData()` inferior a **50 milisegundos** para 120 registros.
* Estabilidad total del foco y los inputs de formulario.

---

## 4. Matriz de Detección de Gaps Funcionales

El análisis minucioso de la implementación actual del Módulo 1 frente a los casos de uso anteriores ha permitido identificar **6 Gaps Funcionales** relevantes:

```
+--------------------+---------------------------------------------------------+----------------+
| Código de Gap      | Título del Gap Funcional                                | Criticidad     |
+--------------------+---------------------------------------------------------+----------------+
| GAP-FUNC-01        | Falta de Conector de Reclasificación Bidireccional REST | CRÍTICA (ALTA) |
| GAP-FUNC-02        | Ambigüedad en Extracción de Métricas No Estructuradas   | MEDIA          |
| GAP-FUNC-03        | Carencia de Deduplicación y Detección de Tormentas     | MEDIA-ALTA     |
| GAP-FUNC-04        | Falta de Persistencia Centralizada del Estado de Triaje | ALTA           |
| GAP-FUNC-05        | Vulnerabilidad a Coincidencias Léxicas Contextuales     | BAJA-MEDIA     |
| GAP-FUNC-06        | Desincronización ante Reasignación de Grupo en Remedy   | MEDIA          |
+--------------------+---------------------------------------------------------+----------------+
```

### Análisis Detallado de Gaps Funcionales:

#### GAP-FUNC-01: Falta de Conector de Reclasificación Bidireccional REST con Remedy ITSM
* **Descripción:** Actualmente, cuando el motor detecta una discrepancia (ej. P3 que debe ser SL1), el Incident Manager debe abrir un modal, pulsar `Copiar Justificación`, abrir la consola web de Remedy en otra pestaña, buscar el ticket, pegar el texto en los *Work Logs* y modificar a mano los desplegables de *Impacto* y *Urgencia*.
* **Impacto Operativo:** Este proceso manual introduce una demora de entre **2 y 5 minutos por ticket**, lo cual es inaceptable durante los primeros compases de una crisis donde el reloj de 20 minutos para la comunicación ejecutiva ya está corriendo.
* **Causa Raíz:** El Módulo 1 opera como un visor de solo lectura sobre el JSON de salida; no dispone aún de endpoints REST para ejecutar mutaciones sobre la API de BMC Remedy (`HPD:IncidentInterface_Create_WS`).
* **Solución Propuesta:** Implementar un botón `⚡ Reclasificar en Remedy (1-Click)` respaldado por un endpoint backend `POST /api/v1/incidents/{id}/reclassify` que actualice automáticamente Urgencia, Impacto y Work Log en Remedy.

#### GAP-FUNC-02: Ambigüedad en Extracción de Métricas Cuantitativas No Estructuradas
* **Descripción:** Si la descripción de Remedy o el resumen de Epsilon utiliza expresiones cualitativas como *"muchos usuarios afectados"*, *"múltiples quejas recibidas"* o *"lentitud notable"* sin especificar un porcentaje numérico (ej. `>20%`), el evaluador recurre a palabras clave genéricas y puede vacilar entre clasificar en P2 o P1.
* **Impacto Operativo:** Puede demorar la activación de SL1 en incidencias que están teniendo un impacto masivo pero cuyo texto inicial carece de precisión métrica por parte del operador que abrió el ticket.
* **Solución Propuesta:** Incorporar una regla de inferencia en el evaluador: ante expresiones de volumen indefinido sobre frontales comerciales únicos (como Ficha de Cliente o CRM), asumir por defecto el peor escenario aplicando de forma estricta la **Regla de Oro N1**.

#### GAP-FUNC-03: Carencia de Deduplicación y Detección de Tormentas de Tickets (Ticket Storming)
* **Descripción:** Cuando se produce una caída troncal (ej. corte de fibra en un polígono o caída de un servidor central de telefonía), pueden crearse 15 o 20 tickets Remedy independientes reportados por distintas tiendas, distribuidores o clientes VIP. El Módulo 1 los evalúa como 20 incidencias aisladas, inflando el contador de discrepancias y dispersando la atención del IM.
* **Impacto Operativo:** Sobrecarga visual y fatiga de alertas para el Incident Manager.
* **Solución Propuesta:** Implementar un motor de correlación temporal y sintáctica que agrupe tickets con similar descripción, sistemas comunes y ventana de apertura coincidente (±15 min), sugiriendo la vinculación formal de un **Ticket Padre / Masivo** en Remedy.

#### GAP-FUNC-04: Falta de Persistencia Centralizada del Estado de Triaje (Audit Trail Local)
* **Descripción:** Si un Incident Manager marca una discrepancia como "Revisada" o "En Seguimiento", ese estado se guarda en la memoria de la sesión local (`localStorage` del navegador). Si otro Incident Manager abre la consola desde otro ordenador en el cambio de turno, no puede ver qué discrepancias han sido ya gestionadas por su compañero.
* **Impacto Operativo:** Riesgo de duplicidad de llamadas telefónicas a los resolutores o de omisión de tickets asumiendo que el compañero de turno ya los ha atendido.
* **Solución Propuesta:** Crear una tabla o store centralizado (`data/audit/triage_audit_log.json` o base de datos relacional/Redis) accesible vía API REST donde se persistan las acciones y firmas de los Incident Managers sobre cada ticket.

#### GAP-FUNC-05: Vulnerabilidad a Coincidencias Léxicas Contextuales (Falsos Positivos)
* **Descripción:** A pesar del uso de regex con `\b`, si un ticket describe un fallo en una impresora interna pero añade como coletilla informativa *"ubicada en la oficina central de Facturación"*, el motor puede puntuar el proceso de Facturación y clasificarlo por encima de su severidad real.
* **Impacto Operativo:** Genera falsas alarmas que restan credibilidad a la consola ante los operadores de guardia.
* **Solución Propuesta:** Requerir que la palabra clave de proceso esté acompañada semánticamente por un verbo o sustantivo de afectación operativa (ej. *"caída"*, *"bloqueo"*, *"error"*, *"parada"*, *"timeout"*), ignorando menciones puramente locativas.

#### GAP-FUNC-06: Desincronización ante Reasignación de Grupo Resolutor en Remedy
* **Descripción:** Si un ticket clasificado inicialmente en un grupo secundario es reasignado en Remedy al grupo de especialistas (ej. `SOP_SMC_TEIDE`), el motor recalcula su prioridad solo si el feed se ha refrescado, pero no emite una alerta diferencial indicando *"Ticket reclasificado internamente por cambio de grupo resolutor"*.
* **Solución Propuesta:** Mantener un histórico del estado anterior del ticket en memoria para resaltar badges de `🔄 Grupo Resolutor Modificado`.

---

## 5. Matriz de Detección de Gaps Operativos

Los **Gaps Operativos** representan fricciones en la experiencia del operador, ergonomía de crisis y alineamiento con los protocolos de emergencia de Orange:

```
+--------------------+---------------------------------------------------------+----------------+
| Código de Gap      | Título del Gap Operativo                                | Criticidad     |
+--------------------+---------------------------------------------------------+----------------+
| GAP-OPER-01        | Fricción de Copiado y Formato en Work Logs de Remedy    | ALTA           |
| GAP-OPER-02        | Fatiga de Alarmas por Ausencia de Ranking por Pérdida   | MEDIA-ALTA     |
| GAP-OPER-03        | Ausencia de Alerta Sonora / Notificación Push en P1     | CRÍTICA        |
| GAP-OPER-04        | Falta de Protocolo de Desestimación Formal de Alarma    | ALTA           |
| GAP-OPER-05        | Transición Discontinua entre Triaje (M1) y War Room (M2)| MEDIA-ALTA     |
| GAP-OPER-06        | Ausencia de Informe de Relevo de Guardia Automatizado   | MEDIA          |
+--------------------+---------------------------------------------------------+----------------+
```

### Análisis Detallado de Gaps Operativos:

#### GAP-OPER-01: Fricción de Copiado y Formato en Work Logs de Remedy
* **Descripción:** Remedy ITSM cuenta con un editor de texto enriquecido antiguo que a menudo corrompe emojis, caracteres especiales o saltos de línea procedentes del portapapeles moderno. Cuando el Incident Manager pega la justificación, pueden aparecer caracteres extraños como `âš ï¸` en lugar de `⚠️`.
* **Impacto Operativo:** El operador pierde tiempo limpiando manualmente el texto antes de poder guardar el ticket en Remedy.
* **Solución:** Añadir un selector de formato en el modal de justificación: `Modo Texto Plano (Remedy Safe ASCII)` y `Modo Enriquecido (Teams / Correo)`.

#### GAP-OPER-02: Fatiga de Alarmas por Ausencia de Ranking Ponderado por Pérdida de Negocio
* **Descripción:** Si durante una tormenta de incidencias surgen 8 discrepancias simultáneas, la lista se presenta por orden cronológico estricto de entrada. Un ticket de ATC con 2.000 clientes afectados puede aparecer por debajo de un ticket de provisión fija que entró 2 minutos antes.
* **Impacto Operativo:** Falta de jerarquización táctica: el IM debe leer todas las filas para decidir cuál atacar primero.
* **Solución:** Implementar un algoritmo de ordenación por **Criticidad Ponderada de Negocio**:
  $$\text{Score} = (\text{Delta Severidad} \times 40) + (\text{Peso Proceso} \times 30) + (\text{Minutos Activo} \times 10)$$
  situando en primer lugar las incidencias con mayor riesgo financiero inmediato.

#### GAP-OPER-03: Ausencia de Alerta Sonora / Notificación Push del Navegador en Nuevas P1
* **Descripción:** Durante una guardia, el Incident Manager suele estar al teléfono con el SMC Bridge o revisando logs en otra pantalla. Si la Consola de Triaje detecta una subescalación crítica a SL1 en segundo plano, la pestaña no emite ningún sonido ni notificación del sistema operativo.
* **Impacto Operativo:** El ticket crítico puede permanecer desatendido durante varios minutos hasta que el operador vuelve a enfocar la pestaña.
* **Solución:** Integrar la **Web Audio API** (tono discreto de emergencia ITIL) y la **Notifications API de HTML5** solicitando permisos al cargar la consola para emitir un banner emergente en Windows cuando se detecte un nuevo SL1/P1 con Delta $\ge 1$.

#### GAP-OPER-04: Falta de Protocolo de Desestimación Formal de Alarma (Override de IM)
* **Descripción:** Si el motor sugiere SL1 para una incidencia que el Incident Manager sabe con certeza que es un simulacro programado, un entorno de preproducción o una falsa alarma verificada, no existe un mecanismo para "Marcar como Desestimada". Como consecuencia, la fila sigue apareciendo en naranja/rojo en cada ciclo de refresco.
* **Impacto Operativo:** Ruido visual permanente que degrada la confianza del operador en la herramienta.
* **Solución:** Habilitar una acción `Desestimar Discrepancia` que exija al IM introducir un motivo obligatorio (mínimo 15 caracteres) y su firma, archivando la alerta y evitando que vuelva a mostrarse como discrepancia activa.

#### GAP-OPER-05: Transición Discontinua entre Triaje (Módulo 1) y War Room (Módulo 2)
* **Descripción:** Si el IM revisa una discrepancia en la tabla y decide que efectivamente es una emergencia SL1, tiene que buscar manualmente el botón del Orquestador o cambiar de pestaña para convocar la War Room y arrancar los relojes.
* **Impacto Operativo:** Desconexión procedimental entre el diagnóstico y la ejecución del protocolo de crisis.
* **Solución:** Añadir en la propia fila y en el modal de justificación del Módulo 1 un botón directo: `🚨 Confirmar SL1 y Abrir War Room (Módulo 2)`, realizando la transición en un solo clic e inyectando todos los datos del ticket en el orquestador.

#### GAP-OPER-06: Ausencia de Informe de Relevo de Guardia Automatizado (Handover Report)
* **Descripción:** Al finalizar el turno de guardia de 8 o 12 horas, el Incident Manager saliente debe redactar manualmente un correo resumiendo qué tickets fueron subescalados, qué criterios se aplicaron y cuáles siguen abiertos.
* **Impacto Operativo:** Pérdida de 15 a 20 minutos en la confección manual del informe y riesgo de omitir detalles clave.
* **Solución:** Crear un botón `📄 Generar Informe de Relevo de Guardia` en la cabecera que compile en un clic el resumen estructurado de todas las discrepancias detectadas, atendidas y pendientes durante el turno.

---

## 6. Protocolo y Plantilla de Ejecución de Pruebas (Test Execution Protocol)

Para homologar el Módulo 1 en un entorno de pruebas o preproducción, los evaluadores deben cumplimentar la siguiente plantilla de verificación operativa:

```markdown
### 📋 Hoja de Evaluación de Pruebas: Consola de Triaje (Módulo 1)
- **Fecha de Ejecución:** [AAAA-MM-DD]  
- **Evaluador / Incident Manager:** [Nombre y Apellidos]  
- **Versión Evaluada:** [Versión Git / Commit Hash]  
- **Navegador y Resolución:** [Chrome / Edge / Firefox | 1920x1080]  

| ID Caso | Escenario Evaluado | Acción del Operador | Resultado Esperado | Resultado Obtenido | Estado (Pass / Fail / Blocker) | Gap Asociado |
| :---: | :--- | :--- | :--- | :--- | :---: | :---: |
| **UC-01** | Subescalación ATC (Ficha Cliente) | Ingestar ticket P3 con caída de frontales >20% | Sugerida SL1, Delta +2, badge ámbar visible | | | GAP-FUNC-01 |
| **UC-02** | Retraso Facturación (HPFMS) | Ingestar ticket P3 con 2.5h retraso mediación | Sugerida SL1, justificación cita umbral 2h | | | GAP-FUNC-02 |
| **UC-03** | Parada Provisión (TEIDE) | Ingestar ticket P2 con 100% órdenes detenidas >10m | Sugerida SL1, Delta +1, enlace a Orquestador | | | GAP-OPER-05 |
| **UC-04** | Middleware Transversal (TIBCO) | Ingestar saturación EMS multiproceso | Doble etiquetado correcto, sugerida SL1 | | | GAP-FUNC-05 |
| **UC-05** | Fallo Nodo Core (Exadata) | Ingestar caída nodo sin pérdida de servicio | Sugerida SL2, Delta +2, badge mayor P2 | | | - |
| **UC-06** | Filtro Estados Terminales | Cargar ticket Resuelto y ticket Cosmético P4 | Resuelto descartado de tabla, P4 sin delta | | | - |
| **UC-07** | Caída de Epsilon Resumen IA | Detener microservicio Epsilon y refrescar | Clasificación con Remedy nativo, banner gris | | | - |
| **UC-08** | Estrés 120 tickets + Polling 15s | Expandir 3 filas y esperar 4 ciclos de refresco | Cero parpadeo, filas siguen abiertas, filtro activo | | | GAP-OPER-02 |
```

---

## 7. Matriz de Priorización de Mejoras y Roadmap de Mitigación (MoSCoW)

Para transformar los hallazgos de este análisis en un plan de ingeniería accionable, los gaps identificados se ordenan según la metodología **MoSCoW**:

```mermaid
quadrantChart
    title Matriz de Priorización: Impacto Operativo vs Esfuerzo de Implementación
    x-axis "Menor Esfuerzo Técnico" --> "Mayor Esfuerzo Técnico"
    y-axis "Menor Impacto Operativo" --> "Mayor Impacto Operativo"
    quadrant-1 "Evolución Estratégica (Planificada)"
    quadrant-2 "Victorias Rápidas (Must Have Inmediato)"
    quadrant-3 "Mejoras Cosméticas (Could Have)"
    quadrant-4 "Proyectos Mayores (Should Have)"
    "GAP-OPER-03 Alertas Sonoras & Push": [0.25, 0.90]
    "GAP-OPER-05 Handoff Triaje a Orquestador": [0.30, 0.85]
    "GAP-OPER-01 Formato Remedy Safe ASCII": [0.20, 0.75]
    "GAP-FUNC-01 API Reclasificación 1-Click": [0.75, 0.95]
    "GAP-OPER-04 Desestimación con Firma IM": [0.45, 0.80]
    "GAP-OPER-02 Ranking por Pérdida Negocio": [0.35, 0.70]
    "GAP-FUNC-04 Persistencia Centralizada": [0.65, 0.75]
    "GAP-FUNC-03 Deduplicación Tormentas": [0.80, 0.65]
    "GAP-OPER-06 Informe Relevo Automatizado": [0.30, 0.55]
    "GAP-FUNC-02 NLP Métricas No Estructuradas": [0.70, 0.50]
```

### 7.1. MUST HAVE (Imprescindibles para el Próximo Release v1.1.0)

1. **GAP-OPER-03 (Alertas Sonoras y Notificaciones Push):**  
   Implementar sonido de alarma suave y notificación del navegador al detectar un ticket con Delta $\ge 1$ hacia SL1.  
   *Esfuerzo:* 0.5 días · *Impacto:* Erradica el riesgo de tickets críticos desatendidos en guardia.
2. **GAP-OPER-05 (Transición Fluida Triaje ➔ Orquestador):**  
   Añadir botón directo en la fila del Módulo 1 para abrir la War Room del Módulo 2 con un clic.  
   *Esfuerzo:* 0.5 días · *Impacto:* Reducción de 60 segundos en la convocatoria de crisis.
3. **GAP-OPER-01 (Modo de Copiado "Remedy Safe ASCII"):**  
   Añadir botón de copiado sin caracteres Unicode para evitar errores de codificación en Remedy.  
   *Esfuerzo:* 0.5 días · *Impacto:* Elimina la fricción manual en el pegado del ticket.
4. **GAP-OPER-04 (Desestimación Formal de Alarma con Firma):**  
   Permitir silenciar discrepancias no procedentes con registro obligatorio del motivo.  
   *Esfuerzo:* 1 día · *Impacto:* Cero falsos positivos molestos en pantalla.

---

### 7.2. SHOULD HAVE (Programadas para la Versión v1.2.0)

1. **GAP-FUNC-01 (Conector REST 1-Click con Remedy ITSM):**  
   Desarrollar el endpoint backend para actualizar directamente el ticket en Remedy sin intervención manual.  
   *Esfuerzo:* 3 días · *Impacto:* Ahorro de 3 a 5 minutos por incidencia crítica.
2. **GAP-OPER-02 (Ordenación Ponderada por Impacto de Negocio):**  
   Implementar algoritmo de scoring para que las discrepancias con mayor afectación encabecen la tabla.  
   *Esfuerzo:* 1 día · *Impacto:* Foco táctico inmediato en hora punta.
3. **GAP-FUNC-04 (Persistencia Centralizada del Estado de Triaje):**  
   Store compartido para sincronización multi-operador entre puestos de guardia.  
   *Esfuerzo:* 2 días · *Impacto:* Coordinación de turno robusta y sin solapamientos.

---

### 7.3. COULD HAVE (Evolutivos Futuros v2.0.0)

1. **GAP-OPER-06 (Generador de Informes de Relevo de Guardia):**  
   Exportación en 1 clic del resumen de incidencias del turno en PDF/Markdown.
2. **GAP-FUNC-03 (Correlación y Agrupación de Tormentas de Incidencias):**  
   Agrupación inteligente de tickets repetidos bajo un Ticket Maestro.
3. **GAP-FUNC-02 (Modelo NLP para Extracción Numérica Avanzada):**  
   Fine-tuning de Epsilon IA para inferir métricas a partir de descripciones difusas.

---

### 7.4. WON'T HAVE (Fuera de Alcance en esta Fase)

* Reemplazo completo de la interfaz de Remedy ITSM (la consola es un Cockpit de Triaje y Emergencias, no un sustituto de la herramienta de inventario y ticketing general).
* Modificación automática de tickets sin confirmación explícita del Incident Manager (la gobernanza ITIL de Orange exige siempre el visado de un humano en el bucle).

---
*Documento aprobado para distribución técnica y operativa en Orange Tech Operations.*
