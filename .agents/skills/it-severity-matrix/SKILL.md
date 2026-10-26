---
name: it-severity-matrix
alias: matriz-severidad-it
description: >-
  Calcula y justifica el nivel de Severidad/Prioridad (P1 a P4) de una incidencia IT
  cruzando el Impacto en el negocio con la Urgencia operativa según buenas prácticas ITIL/SRE.
  Úsese siempre que se describa, clasifique o haga triaje de una incidencia IT.
---

# Matriz de Severidad y Prioridad de Incidencias IT (ITIL / SRE)

Esta skill define el criterio estándar para clasificar cualquier incidencia técnica de forma objetiva, evitando tanto la sobre-escalación ("todo es urgente") como la subestimación de fallos críticos.

## 1. Evaluación de Impacto (Alcance del Daño)

| Nivel de Impacto | Criterios Objetivos |
| :--- | :--- |
| **Alto (Crítico)** | • Caída total de un servicio productivo crítico o de cara al cliente.<br>• Más del 50% de usuarios internos o clientes afectados.<br>• Riesgo de pérdida/corrupción de datos, brecha de seguridad o incumplimiento legal/financiero directo.<br>• No existe *workaround* (solución temporal) viable. |
| **Medio (Moderado)** | • Degradación severa de rendimiento o caída de una funcionalidad importante pero no bloqueante global.<br>• Entre el 10% y el 50% de usuarios afectados, o un departamento clave.<br>• Existe un *workaround* manual complejo o costoso. |
| **Bajo (Menor)** | • Fallo aislado que afecta a un grupo reducido (<10%) o a un único usuario.<br>• Entornos no productivos (`DEV`, `QA`, `STAGING`) salvo que bloqueen un despliegue crítico.<br>• Existe un *workaround* sencillo e inmediato. |

## 2. Evaluación de Urgencia (Sensibilidad al Tiempo)

| Nivel de Urgencia | Criterios Objetivos |
| :--- | :--- |
| **Alta** | El impacto crítico ya está ocurriendo en vivo o es inminente (ej. cierre contable, campaña activa, horario pico). Requiere intervención inmediata 24x7. |
| **Media** | El fallo afecta la operativa normal pero puede contenerse temporalmente durante unas horas sin daño irreversible. |
| **Baja** | El problema es cosmético, de consulta o planificable dentro del horario laboral estándar. |

## 3. Matriz de Cruce (Impacto × Urgencia = Prioridad)

| Impacto \ Urgencia | Urgencia Alta | Urgencia Media | Urgencia Baja |
| :--- | :---: | :---: | :---: |
| **Impacto Alto** | **P1 (Crítica)** | **P1 (Crítica)** o **P2** | **P2 (Alta)** |
| **Impacto Medio** | **P2 (Alta)** | **P2 (Alta)** o **P3** | **P3 (Media)** |
| **Impacto Bajo** | **P3 (Media)** | **P3 (Media)** | **P4 (Baja)** |

## 4. Niveles de Servicio (SLAs de Referencia) y Protocolo

- **P1 - Crítica (Major Incident):**
  - **Tiempo de Respuesta:** < 15 min.
  - **Frecuencia de Comunicación:** Cada 30-60 min.
  - **Acción:** Abrir puente de crisis (*War Room*), notificar a Incident Commander y dirección IT. Requiere informe PIR (*Post-Mortem*) obligatorio al cierre.
- **P2 - Alta:**
  - **Tiempo de Respuesta:** < 30-60 min.
  - **Frecuencia de Comunicación:** Cada 2-4 horas.
  - **Acción:** Escalado inmediato a equipo N2/N3 de guardia.
- **P3 - Media:**
  - **Tiempo de Respuesta:** < 4 horas laborales.
  - **Acción:** Gestión en cola estándar de soporte N2.
- **P4 - Baja:**
  - **Tiempo de Respuesta:** < 24 horas laborales.
  - **Acción:** Resolución estándar o conversión en petición evolutiva / bug de backlog.

## 5. Formato de Justificación Obligatorio

Siempre que asignes una prioridad usando esta skill, incluye este bloque resumido:

- **Prioridad Sugerida:** `P[1-4] - [Nombre]`
- **Impacto Evaluado:** `[Alto/Medio/Bajo]` — *[Justificación en 1 línea]*
- **Urgencia Evaluada:** `[Alta/Media/Baja]` — *[Justificación en 1 línea]*
- **Existencia de Workaround:** `[Sí / No / Desconocido]`
