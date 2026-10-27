---
name: it-severity-matrix
alias: matriz-severidad-it
description: >-
  Calcula y justifica el nivel de Severidad y Prioridad (SL1/P1 a SL4/P4) de incidencias IT
  en MasOrange, aplicando los umbrales de los 6 Procesos Críticos de Negocio, la Regla de Oro
  del triaje N1 y el protocolo oficial de escalados de Emergencias (45 min / +1 hora) con IM-CSO.
---

# Matriz de Severidad, Prioridad y Protocolo de Escalados IT (MasOrange)

Esta skill establece el criterio estándar, objetivo y determinista para la detección, clasificación, asignación de severidad y protocolo de escalado técnico en la gestión de incidencias de MasOrange.

---

## 1. Principios Generales del Triaje

* **Responsable del Triaje Inicial:**
  La detección y clasificación inicial la realiza el nivel **N1** mediante la monitorización directa de alarmas, análisis de tickets reiterativos, alertas de clientes o escalados procedentes de Negocio y Atención al Cliente (ATC).

* **La "Regla de Oro" (Principio de Precaución):**
  > En caso de duda o información incompleta sobre el impacto real de una incidencia, **debe clasificarse inicialmente como Emergencia (SL1 / P1 / Crítica)**, gestionarse y comunicarse como tal. Únicamente se reducirá la severidad si se confirma de forma explícita y verificada que el impacto es menor.

---

## 2. Niveles Generales de Severidad en IT (SL1 a SL4 / P1 a P4)

| Nivel de Severidad | Denominación | Criterio de Afectación Operativa | SLAs Objetivos y Protocolo |
| :---: | :--- | :--- | :--- |
| **SL1 / P1** | **Emergencia (Crítica)** | Alto impacto o alto riesgo de generarlo en Procesos Críticos de Negocio, infraestructura crítica, ciberseguridad o herramientas esenciales de O&M (monitorización/ticketing). | • **Respuesta:** < 15 min.<br>• **Comunicación:** Cada 30-60 min.<br>• **Puente:** War Room activa con Incident Manager.<br>• **Cierre:** Informe PIR (*Post-Mortem*) obligatorio. |
| **SL2 / P2** | **Mayor** | Incidencias que afectan a equipos o infraestructuras (p. ej., degradación parcial o pérdida de capacidad en entornos redundados), pero donde **el servicio o proceso sigue siendo funcional sin causar indisponibilidad**. | • **Respuesta:** < 30-60 min.<br>• **Comunicación:** Cada 2-4 horas.<br>• **Acción:** Escalado inmediato a guardia N2/N3. |
| **SL3 / P3** | **Menor** | Bajo o nulo impacto en procesos de negocio (p. ej., fallo parcial en procesos no críticos, alarmas menores o fallos en backups). | • **Respuesta:** < 4 horas laborales.<br>• **Acción:** Gestión en cola estándar de soporte N2. |
| **SL4 / P4** | **Informativa** | Sin impacto directo en los servicios; incidencias o problemas de software que solo requieren registro y seguimiento. | • **Respuesta:** < 24 horas laborales.<br>• **Acción:** Registro en backlog evolutivo o seguimiento. |

---

## 3. Criterios de Emergencia (SL1 / P1) por Procesos Críticos de Negocio

Cualquier incidencia que supere al menos uno de los siguientes umbrales en los 6 procesos clave se cataloga **de forma automática como Emergencia (SL1 / P1)**:

### 1. Atención al Cliente (ATC)
* **IVR:** Indisponibilidad o degradación que colapse o impida atender a **>20% de las llamadas** para cualquier marca/segmento, o cualquier IVR **descartando >20% de llamadas durante 1 hora**.
* **Frontales / CRM:** Indisponibilidad o degradación en Frontales/CRM con una desviación de **>20% en 30 minutos** en volumen o errores.

### 2. Ventas
* **Volumen de Operaciones:** Afectación en cualquier canal, segmento o marca que suponga un impacto en **más del 30% del volumen de operaciones**.
* **Caída Diaria:** Registrar **menos del 15% de ventas diarias** respecto al promedio de los 4 días equivalentes anteriores.

### 3. Portabilidad
* **Flujo Nocturno:** Imposibilidad de iniciar el flujo de portabilidad a las **2:00 AM**.
* **Entidad de Referencia:** Fallos de comunicación con la entidad de referencia entre las **8:00 AM y las 8:00 PM** (indisponibilidad total o degradación con **>2 horas de retraso**).

### 4. Prepago
* **Recargas:** **>10% de errores** o **>30 minutos sin actividad** por marca o canal.
* **Alta de Líneas:** **>10% de errores** o **>30 minutos sin altas**.

### 5. Provisión
* **Beneficios:** Indisponibilidad del **100% de renovaciones de beneficios**.
* **Órdenes de Móvil:** **>20% de errores** o el **100% de provisiones en error por >10 minutos**.
* **Órdenes de Fijo:** **>30% de errores** o el **100% de provisiones en error por >30 minutos**.

### 6. Facturación y Cobros
* **Fecha de Cobro / Tarificación Batch:** Desviación **>1 día en la fecha de cobro** o en la tarificación batch por marca.
* **Tarificación Online:** Más de **3 horas sin tarificación online** por marca.
* **Ciclo de Facturación:** Indisponibilidad o degradación severa en facturación en la ventana de **±3 días de cada ciclo**.

---

## 4. Matriz Determinista de Cruce y Regla de Desempate

Para incidencias no recogidas expresamente en los 6 procesos clave, se aplica el cruce de **Impacto** y **Urgencia**:

| Impacto \ Urgencia | Urgencia Alta | Urgencia Media | Urgencia Baja |
| :--- | :---: | :---: | :---: |
| **Alto (Proceso core / indisponibilidad)** | **SL1 / P1** | **SL1 / P1** *(SL2 si hay workaround validado)* | **SL2 / P2** |
| **Medio (Infraestructura / redundancia / degradación parcial)** | **SL2 / P2** | **SL2 / P2** *(SL3 si hay workaround validado)* | **SL3 / P3** |
| **Bajo (Fallo aislado o entorno no productivo)** | **SL3 / P3** | **SL3 / P3** | **SL4 / P4** |

* **Regla de Desempate:** Un *workaround* solo desescala 1 nivel si está **técnicamente verificado, operativo en minutos y no genera fricción severa de negocio**.
* **Información incompleta:** Si se desconoce el alcance o la viabilidad del workaround, aplica la **Regla de Oro** (mantener nivel superior).

---

## 5. Procedimiento de Gestión de Emergencias IT (SL1 / P1) y Escalados

El **Incident Manager (IM)** es el responsable de coordinar la resolución técnica, controlar los tiempos y activar los escalados.

### 5.1 Umbrales Temporales de Escalado
* **Primer Escalado (45 Minutos):**
  Si transcurridos como máximo **45 minutos** desde la apertura/identificación de la emergencia no existe ningún avance técnico por parte del grupo asignado, el IM ejecutará un **escalado telefónico** al siguiente nivel de los proveedores y grupos involucrados, convocando una reunión de seguimiento con los responsables.
* **Segundo Escalado (1 Hora Adicional - T+1h 45m):**
  Si tras **1 hora adicional** desde el primer escalado continúa la falta de avances significativos o los planes de acción aplicados no han mitigado el impacto, el IM realizará un **segundo escalado al siguiente escalón superior**.

### 5.2 Canales y Reglas de Ejecución
* **Vía Telefónica Obligatoria:** Durante una Emergencia SL1, **todos los escalados se realizan exclusivamente vía telefónica**, independientemente de si ocurren en Horario Laboral (HL) o Fuera de Horario Laboral (FHL).
* **Coordinación con Customer & Service Ops (IM-CSO):**
  Cuando se requiera escalar a niveles directivos o superiores de proveedores y grupos internos, el IM debe contactar con el equipo de **IM-CSO** para gestionar dicho escalado. Ambos roles pueden acordar excepciones a la norma general según la evolución de la crisis.
* **Escalado en Paralelo (Casos Críticos):**
  Ante caídas de componentes estructurales críticos (**CRM, bases de datos RAC, Racks de infraestructura**) o incidencias de impacto masivo desproporcionado, los escalados no se realizan de forma secuencial, sino **en paralelo a todos los posibles grupos resolutores**. Esta regla también aplica de inmediato si existen dudas sobre qué grupo técnico es el responsable.

### 5.3 Estructura de las Matrices de Contacto y Repositorios
Las matrices de contacto están organizadas por capas operativas y marcas:
* **Nivel 1 (N1):** Primer escalón de atención operativa (tanto interno de MasOrange como del proveedor de soporte).
* **Niveles N2 y N3 (Especialistas y Proveedores):** Matrices específicas asociadas a cada aplicativo o elemento de infraestructura:
  * **Entorno MasMóvil / KRT:** Documentadas y centralizadas en **Confluence**.
  * **Entorno Orange / Jazztel:** Documentadas y centralizadas en la plataforma **GRIAL**.

---

## 6. Formato de Justificación y Salida de la Skill

Al clasificar o auditar una incidencia con esta skill, emite el siguiente bloque normalizado:

- **Severidad / Prioridad:** `[SL1/P1 | SL2/P2 | SL3/P3 | SL4/P4] - [Emergencia / Mayor / Menor / Informativa]`
- **Proceso / Entorno Afectado:** `[ATC | Ventas | Portabilidad | Prepago | Provisión | Facturación/Cobros | Infraestructura Core]`
- **Justificación del Criterio:** `[Umbral específico superado de la Sección 3 / Regla de Oro por información preliminar]`
- **Estado de Workaround:** `[No viable / En investigación / Operativo validado]`
- **Protocolo Requerido:** `[War Room + Escalado telefónico IM (45 min) | Guardia N2/N3 | Cola estándar]`
- **Matriz de Contacto de Referencia:** `[GRIAL (Orange/Jazztel) | Confluence (MasMóvil/KRT)]`
