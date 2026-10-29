---
name: it-severity-matrix
alias: matriz-severidad-it
description: >-
  Calcula y justifica el nivel de Severidad y Prioridad (SL1/P1 a SL4/P4) de incidencias IT
  en Orange, aplicando los umbrales de los Procesos Críticos de Negocio, Middleware Transversal,
  Conectividad de Sedes/Circuitos, Infraestructura Core/Cloud (ESX/PSeries/Exadata/OCI/GCP),
  Identidad/Automatización (GDU/EVIDIAN/ROBOTFACTORY), la Regla de Oro del triaje N1 y el
  protocolo oficial de escalados de Emergencias (45 min / +1 hora / Alarma >2h) con IM-CSO.
---

# Matriz de Severidad, Prioridad y Protocolo de Escalados IT (Orange) — v2

Esta skill establece el criterio estándar, objetivo y determinista para la detección, clasificación, asignación de severidad y protocolo de escalado técnico en la gestión de incidencias de Orange.

---

## 1. Principios Generales del Triaje

* **Responsable del Triaje Inicial:**
  La detección y clasificación inicial la realiza el nivel **N1** (`CEP CAU AGI`, `GNOC`, `RTV-TECSE RED DATOS`, `SOPORTE N1 CSO`) mediante la monitorización directa de alarmas, análisis de tickets reiterativos, alertas de clientes o escalados procedentes de Negocio y Atención al Cliente (ATC).

* **La "Regla de Oro" (Principio de Precaución):**
  > En caso de duda o información incompleta sobre el impacto real de una incidencia, **debe clasificarse inicialmente como Emergencia (SL1 / P1 / Crítica)**, gestionarse y comunicarse como tal. Únicamente se reducirá la severidad si se confirma de forma explícita y verificada que el impacto es menor.

* **Regla de Etiquetado Operativo Explícito (`/SL1` y `/SL2`) en Nomenclatura de N1:**
  Si el título o descripción normalizada del ticket incluye la etiqueta explícita `/SL1` (`INDISPONIBILIDAD / <SISTEMA> / SL1`) o `/SL2` (`DEGRADACIÓN / <SISTEMA> / SL2`), dicha severidad actúa como **suelo mínimo obligatorio** (`SL1 / P1` o `SL2 / P2` respectivamente), prevaleciendo sobre posibles errores de grabación en los campos `Prioridad` (`Media`/`Alta`) o `Urgencia` (`Baja`/`Medio`) de Remedy.

* **Normalización de Campos Remedy (`Urgencia` y `Estatus`):**
  En las exportaciones de Remedy, `Urgencia = Crítica` equivale siempre a **Urgencia Alta** y `Urgencia = Medio` (masculino) equivale a **Urgencia Media**. El paso de un ticket a estado administrativo `Pendiente` (ej. a la espera de proveedor o ventana técnica) **nunca degrada su urgencia ni su severidad** mientras el impacto técnico o funcional persista.

---

## 2. Niveles Generales de Severidad en IT (SL1 a SL4 / P1 a P4)

| Nivel de Severidad | Denominación | Criterio de Afectación Operativa | SLAs Objetivos y Protocolo |
| :---: | :--- | :--- | :--- |
| **SL1 / P1** | **Emergencia (Crítica)** | Alto impacto o alto riesgo de generarlo en Procesos Críticos de Negocio, aislamiento de sedes/MSC, infraestructura core/cloud sin HA efectiva, middleware/integraciones, identidad/SSO, ciberseguridad o herramientas esenciales de O&M (monitorización/ticketing). | • **Respuesta:** < 15 min.<br>• **Comunicación:** Cada 30-60 min.<br>• **Puente:** War Room activa con Incident Manager.<br>• **Cierre:** Informe PIR (*Post-Mortem*) obligatorio. |
| **SL2 / P2** | **Mayor** | Incidencias que afectan a equipos, circuitos, tiendas o infraestructuras (p. ej., degradación parcial, caída de un único circuito o nodo con redundancia/HA activa), pero donde **el servicio o proceso global sigue siendo funcional sin causar indisponibilidad masiva**. | • **Respuesta:** < 30-60 min.<br>• **Comunicación:** Cada 2-4 horas.<br>• **Acción:** Escalado inmediato a guardia N2/N3. |
| **SL3 / P3** | **Menor** | Bajo o nulo impacto en procesos de negocio (p. ej., fallo parcial en procesos no críticos, alarmas menores o fallos aislados). | • **Respuesta:** < 4 horas laborales.<br>• **Acción:** Gestión en cola estándar de soporte N2. |
| **SL4 / P4** | **Informativa** | Sin impacto directo en los servicios; incidencias o problemas de software que solo requieren registro y seguimiento. | • **Respuesta:** < 24 horas laborales.<br>• **Acción:** Registro en backlog evolutivo o seguimiento. |

---

## 3. Criterios de Emergencia (`SL1 / P1`) y Mayor (`SL2 / P2`) por Procesos Críticos, Integraciones e Infraestructura

Cualquier incidencia que supere los umbrales críticos de los bloques `3.1` a `3.10` se cataloga **de forma automática como Emergencia (`SL1 / P1`)** (o como **`SL2 / P2`** cuando cumpla la condición de degradación parcial o redundancia activa indicada):

### 3.1 Atención al Cliente (ATC) y Canales Digitales
* **IVR y CTI:** Indisponibilidad o degradación en `IVR` o `CTI` (`SOP_TECNICO_CALL_CENTER`) que colapse o impida atender a **>20% de las llamadas** para cualquier marca/segmento, o cualquier IVR **descartando >20% de llamadas durante 1 hora**.
* **Frontales / CRM y Asistentes:** Indisponibilidad o degradación con desviación de **>20% en 30 minutos** en volumen o errores en frontales y herramientas de operación: `Ficha de Cliente Orange` (`DES_SOE_FICHA` / `APL_MOV_SOE`), `CRM Jazztel` (`SOP_BSS_JAZZTEL`), `CRM4TELCO`, `Siebel 8`, `POLAR`, `LIVEPERSON` (`SOP_ASISTENTE`), `DJINGO` (`DES_DJINGO`), `ONURIS` (`SOP_ONURIS`), `ONCONNECT`, `NABOO`, `BOREAL`.
* **Canales de Autogestión Digital (`SL2 / P2` -> `SL1 / P1`):** Degradación o indisponibilidad en `APP MI ORANGE`, `MIJAZZTEL` o `Web Mantenedores` (`SL2 / P2` en degradación funcional parcial; `SL1 / P1` si provoca corte total de acceso o supera los umbrales de ventas/recargas).

### 3.2 Ventas
* **Volumen de Operaciones:** Afectación en cualquier canal, segmento o marca que suponga un impacto en **más del 30% del volumen de operaciones**.
* **Caída Diaria:** Registrar **menos del 15% de ventas diarias** respecto al promedio de los 4 días equivalentes anteriores.
* **Sistemas Críticos de Ventas:** Indisponibilidad o bloqueo en campañas, renoves y altas en `CERES` (`APL_MOV_CERES` / `NEG_CAMP_CERES`), grabación/cierre de `Actos Comerciales` (`updateCommercialActSPA`), firma y contratación en `ECONTRATO` (`Econtrato_N2`), `PANGEA` (altas/portas/migras) o `Televenta`.

### 3.3 Portabilidad
* **Flujo Nocturno:** Imposibilidad de iniciar el flujo de portabilidad a las **2:00 AM**.
* **Entidad de Referencia:** Fallos de comunicación con la entidad de referencia entre las **8:00 AM y las 8:00 PM** (indisponibilidad total o degradación con **>2 horas de retraso**).
* **Sistemas Asociados:** Nodos de portabilidad fija/móvil y flujos de portabilidad en `PANGEA` / `TEIDE`.

### 3.4 Prepago
* **Recargas:** **>10% de errores** o **>30 minutos sin actividad** por marca o canal (incluyendo `RECARGAS APRS`, `Recargas Web - App` y pasarelas de recarga).
* **Alta de Líneas y eSIM Prepago:** **>10% de errores** o **>30 minutos sin altas** (incluyendo flujos de `Altas eSIM Prepago` y aprovisionamiento en `OCS`).

### 3.5 Provisión y Cobertura
* **Beneficios:** Indisponibilidad del **100% de renovaciones de beneficios**.
* **Órdenes de Móvil:** **>20% de errores** o el **100% de provisiones en error por >10 minutos** (incluyendo `PROVISIÓN MÓVIL`, `Cambio de eSIM`, `POMV` / `SOP_TEC_PROVISION`, `SIGMA` / `SOP_TMC_SIGMA`).
* **Órdenes de Fijo y Fibra:** **>30% de errores** o el **100% de provisiones en error por >30 minutos** (incluyendo `TEIDE` / `SOP_SMC_TEIDE`, `IP24`, `LUNA` / `Fijo Activacion LUNA`, `ALTAIR` / llamada `ALTAIR a BRÚJULA`, `MYADDRESS` / consulta de cobertura, `GIS FIBRA`, `SGA` / `SOP_TMC_HPE`, `Prerreserva Numeración Fijo` y `Provisión Fijo contra Adamo`).

### 3.6 Facturación, Mediación y Cobros
* **Fecha de Cobro / Tarificación Batch:** Desviación **>1 día en la fecha de cobro** o en la tarificación batch por marca.
* **Tarificación Online y Mediación:** Más de **3 horas sin tarificación online** por marca o caída/degradación crítica en `MEDIACIÓN` (`APL_FIJ_HP-IUM_OSP` / `HP-IUM`) u `OCS` (`SOP_TMC_OCS`).
* **Ciclo de Facturación y Sistemas de Cobro:** Indisponibilidad o degradación severa en la ventana de **±3 días de cada ciclo**, o bloqueo operativo en `BSCS` / `BSCS Online` (`SOP_TMC_BSCS_ONLINE`), `OPEN COBROS` (`COBROS Y RECOBROS - CONTROL`), `EXCALIBUR` (`SOP_TMC_EXCALIBUR`), `HPFMS` (`FRAUDE` - propagación de bloqueos/desbloqueos de líneas a red) y `SAP` facturación.

### 3.7 Capa de Integración / Middleware Transversal
* **Middleware / Bus de Servicios / Pasarelas API:** Indisponibilidad, errores masivos de integración (`HTTP 404/500`, rechazos de payload) o timeouts en `APIGEE` / `OPENAPI` (`SOP_TMC_APIGEE`), `TIBCO`, `GC MIDDLEWARE`, `Datapower`, conectores `OCCI`, procesos batch de integración (`SBL_EAI`), microservicios transversales (`DES_SOE_MICROSERVICIOS`) o sincronización entre `PeopleSoft` (`FIJO APL Soporte PS`) y `Siebel 8` que afecten la comunicación entre dos o más Procesos Críticos o frontales multicanal.
  * **Condición `SL1 / P1`:** Corte o fallo de integración sin redundancia que bloquea o corrompe operaciones en vivo hacia clientes o agentes (requiere **Escalado en Paralelo obligatorio**).
  * **Condición `SL2 / P2`:** Indisponibilidad parcial de nodos de middleware donde la **redundancia de infraestructura** mantiene activos los canales de negocio, o desincronización acotada de campos no bloqueantes.

### 3.8 Conectividad de Sedes, Call Centers (`MSC`) y Tiendas (`RTV-TECSE RED DATOS` / `GNOC`)
* **Condición de disparo `SL1 / P1` (Emergencia):**
  * **Aislamiento de Sede / Call Center / MSC:** Indisponibilidad total de conectividad de voz o datos en una o varias sedes operativas o plataformas de Call Center / `MSC` (ej. `Sede Málaga MSC`, `Sede Zaragoza Pilar`, `Bilbao Zamudio-MSC`, `Sedes Barcelona 1 / Mataró`, `La Finca`).
  * **Doble Caída de Circuitos:** Caída simultánea de ambos circuitos de comunicaciones de una sede (`Circuito Ulises + Meneses`).
* **Condición de disparo `SL2 / P2` (Mayor):**
  * **Pérdida de Redundancia de Circuito:** Caída o degradación de **un único circuito** de comunicaciones de sede (`Ulises`, `Meneses`, `Palos-Bogotá`, `Palos-ISGF Lezama`) manteniendo el servicio operativo a través del circuito de respaldo.
  * **Electrónica de Red Local o Tienda Física:** Degradación de firewall/switch de sede (`FW Torrejón`, `Switch central Yécora`) con camino alternativo, o **indisponibilidad completa de una Tienda física individual** (ej. `Tienda Calle Alcalá 149`, `Tienda Córdoba`).

### 3.9 Infraestructura Core IT, Hipervisores (`ESX`), Servidores (`PSeries`), Almacenamiento (`SAN`), BBDD (`Exadata`) y Cloud (`OCI`/`GCP`)
* **Condición de disparo `SL1 / P1` (Emergencia):**
  * **Interconexión Cloud (`OCI` / `GCP` / `ITX`):** Caída o flapeo severo de enlaces troncales `ITX` con `GCP` y `OCI` (`OPER_COE_CLOUD` / `Atlas_Soporte_CLOUD`, ej. `ITX OCI GCP ULI-MEN`, `Conectividad GCP`, `Flapeos OCI`).
  * **Cómputo y Virtualización sin HA efectiva (`PSeries Power9` / `ESX`):** Indisponibilidad de servidores críticos `PSeries Power9` (`Atlas_Soporte_Unix`) o hipervisores `ESX` (`Atlas_Soporte_Linux_Vmware`, ej. `ESX aotlxprvin...`) que provoque indisponibilidad de aplicativos o caída sin absorción por Alta Disponibilidad.
  * **Almacenamiento SAN, BBDD Críticas y Backups (`HWSAN` / `Exadata` / `Data Mart Fiscal` / `BACKUP OSP`):** Caída de switches troncales de almacenamiento (`ADM. HWSAN`), indisponibilidad de `DATA MART FISCAL` (`Atlas_Soporte_BBDD`) o fallo global en `BACKUP OSP` (`T.S. BYR`).
* **Condición de disparo `SL2 / P2` (Mayor):**
  * Caída, reinicio o degradación de un nodo individual `ESX`, un servidor `PSeries`, una cabina de discos (`SPAIN ALMACENAMIENTO`, `es3iba02fte`), un filesystem `SAP BASIS` o un nodo de clúster (`Cluster Exadata Yécora`) cuando la **Alta Disponibilidad (HA) o redundancia mantiene el servicio productivo arriba**, pero con pérdida de capacidad o respaldo.

### 3.10 Autenticación / Gestión de Identidad (`GDU` / `EVIDIAN`) y Automatización Operativa (`ROBOTFACTORY`)
* **Condición de disparo `SL1 / P1` (Emergencia):**
  * **Identidad y Control de Accesos (`GDU` / `EVIDIAN`):** Indisponibilidad global de `GDU` (`OPER_Soporte_GdU`) o del sistema de Single Sign-On `EVIDIAN` que impide el login o autenticación de operadores y usuarios en aplicaciones críticas.
  * **Automatización RPA (`ROBOTFACTORY`):** Indisponibilidad total de `ROBOTFACTORY` que paraliza los flujos automáticos de activación y provisión (`Fijo Activacion LUNA` / `Atlas_Soporte_BBDD`) sin alternativa inmediata.
* **Condición de disparo `SL2 / P2` (Mayor):**
  * Degradación parcial, lentitud de acceso o errores funcionales acotados en módulos de `GDU` (`GDU/ACM`) o `EVIDIAN`, o fallo parcial de robots en `ROBOTFACTORY` existiendo operativa manual de contingencia.

---

## 4. Matriz Determinista de Cruce y Regla de Desempate

Para incidencias no recogidas expresamente en los puntos clave anteriores, se aplica el cruce de **Impacto** y **Urgencia**:

| Impacto \ Urgencia | Urgencia Alta (`Crítica` / `Alta`) | Urgencia Media (`Media` / `Medio`) | Urgencia Baja (`Baja`) |
| :--- | :---: | :---: | :---: |
| **Alto (Proceso core / indisponibilidad / `Masiva` sin redundancia)** | **SL1 / P1** | **SL1 / P1** *(SL2 si hay workaround validado)* | **SL2 / P2** |
| **Medio (Infraestructura con HA / 1 circuito / 1 sede / degradación parcial)** | **SL2 / P2** | **SL2 / P2** *(SL3 si hay workaround validado)* | **SL3 / P3** |
| **Bajo (Fallo aislado o entorno no productivo)** | **SL3 / P3** | **SL3 / P3** | **SL4 / P4** |

* **Regla de Desempate:** Un *workaround* solo desescala 1 nivel si está **técnicamente verificado, operativo en minutos, autorizado por IM-CSO y no genera fricción severa de negocio**.
* **Información incompleta:** Si se desconoce el alcance o la viabilidad del workaround, aplica la **Regla de Oro** (mantener nivel superior).

---

## 5. Procedimiento de Gestión de Emergencias IT (SL1 / P1) y Escalados

El **Incident Manager (IM)** es el responsable de coordinar la resolución técnica, controlar los tiempos y activar los escalados.

### 5.1 Umbrales Temporales de Escalado
* **Primer Escalado (45 Minutos):**
  Si transcurridos como máximo **45 minutos** desde la apertura/identificación de la emergencia no existe ningún avance técnico por parte del grupo asignado, el IM ejecutará un **escalado telefónico** al siguiente nivel de los proveedores y grupos involucrados, convocando una reunión de seguimiento con los responsables.
* **Segundo Escalado (1 Hora Adicional - T+1h 45m):**
  Si tras **1 hora adicional** desde el primer escalado continúa la falta de avances significativos o los planes de acción aplicados no han mitigado el impacto, el IM realizará un **segundo escalado al siguiente escalón superior**.
* **Alarma por Estancamiento / Incidencia Bloqueada (>2 Horas sin Avance):**
  Si una incidencia catalogada como **SL1 / P1** (o **SL2 / P2** crítica de continuidad) acumula **>2 horas** en estado `PENDIENTE` o `ASIGNADO`, en diagnóstico o sin un plan de acción validado por el Incident Manager, se activará de forma automática el **Escalado de Dirección hacia Customer & Service Ops (IM-CSO)**, reconvocando con carácter ejecutivo de urgencia la mesa técnica de la War Room.

### 5.2 Canales y Reglas de Ejecución
* **Vía Telefónica Obligatoria:** Durante una Emergencia SL1, **todos los escalados se realizan exclusivamente vía telefónica**, independientemente de si ocurren en Horario Laboral (HL) o Fuera de Horario Laboral (FHL).
* **Coordinación con Customer & Service Ops (IM-CSO):**
  Cuando se requiera escalar a niveles directivos o superiores de proveedores y grupos internos, el IM debe contactar con el equipo de **IM-CSO** para gestionar dicho escalado. Ambos roles pueden acordar excepciones a la norma general según la evolución de la crisis.
* **Escalado en Paralelo (Casos Críticos):**
  Ante caídas de componentes estructurales críticos (**CRM, Middleware/TIBCO/APIGEE, enlaces Cloud OCI/GCP, bases de datos RAC/Exadata, Racks/ESX/PSeries de infraestructura**) o incidencias de impacto masivo desproporcionado, los escalados no se realizan de forma secuencial, sino **en paralelo a todos los posibles grupos resolutores**. Esta regla también aplica de inmediato si existen dudas sobre qué grupo técnico es el responsable.

### 5.3 Estructura de las Matrices de Contacto y Repositorios
Las matrices de contacto están organizadas por capas operativas y marcas:
* **Nivel 1 (N1):** Primer escalón de atención operativa (tanto interno de Orange como del proveedor de soporte).
* **Niveles N2 y N3 (Especialistas y Proveedores):** Matrices específicas asociadas a cada aplicativo o elemento de infraestructura:
  * **Entorno MasMóvil / KRT:** Documentadas y centralizadas en **Confluence**.
  * **Entorno Orange / Jazztel:** Documentadas y centralizadas en la plataforma **GRIAL**.

---

## 6. Formato de Justificación y Salida de la Skill

Al clasificar o auditar una incidencia con esta skill, emite el siguiente bloque normalizado:

- **Severidad / Prioridad:** `[SL1/P1 | SL2/P2 | SL3/P3 | SL4/P4] - [Emergencia / Mayor / Menor / Informativa]`
- **Proceso / Entorno Afectado:** `[3.1 ATC | 3.2 Ventas | 3.3 Portabilidad | 3.4 Prepago | 3.5 Provisión | 3.6 Facturación/Cobros | 3.7 Middleware/Integración | 3.8 Sedes/Circuitos/Tiendas | 3.9 Infraestructura Core/Cloud (ESX/PSeries/SAN/Exadata/OCI/GCP) | 3.10 Identidad/SSO y Automatización (GDU/EVIDIAN/ROBOTFACTORY)]`
- **Justificación del Criterio:** `[Umbral específico superado de la Sección 3 / Etiqueta explícita N1 (/SL1 o /SL2) / Cruce Matriz Sección 4 / Regla de Oro por información preliminar]`
- **Estado de Workaround:** `[No viable / En investigación / Redundancia HA activa / Operativo validado por IM-CSO]`
- **Protocolo Requerido:** `[War Room + Escalado telefónico IM (45 min) | Escalado en Paralelo | Escalado Dirección IM-CSO (>2h sin avance) | Guardia N2/N3 | Cola estándar]`
- **Matriz de Contacto de Referencia:** `[GRIAL (Orange/Jazztel) | Confluence (MasMóvil/KRT)]`
