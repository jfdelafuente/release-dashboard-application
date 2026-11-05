[← Volver a Gestión de Emergencias](02-gestion-emergencias/README.md) · [Protocolo General IM-CSO](02-gestion-emergencias/protocolo-im-cso-escenarios-triaje.md)

# Catálogo Operativo de Escenarios Post-Triaje (IM-CSO)

Directorio oficial de guías procedimentales modulares por escenario post-triaje para la actuación coordinada entre el **Operador de Consola NOC/CCO**, el **Incident Manager (IM)** y la Jefatura de **Customer & Service Operations (IM-CSO)** en Orange Tech Operations.

---

## 🚦 Matriz de Acceso Directo por Escenario

| Escenario | Nombre Oficial | Código Operativo | Severidad ITIL | Llamada IM-CSO | Traza Remedy | Documento Detallado |
| :---: | :--- | :---: | :---: | :---: | :---: | :--- |
| **1** | **Emergencia Viva Crítica** | `EMERGENCIA_VIVA` | `SL1 / P1` | **OBLIGATORIA** | `WL-01`, `WL-02` | [**Ver Guía Escenario 1**](02-gestion-emergencias/escenarios/escenario-1-emergencia-viva.md) |
| **2** | **Resolución Planificada** | `RESOLUCION_PLANIFICADA` | `SL2 / P2` | **NO REQUERIDA** | `WL-04`, `JIRA-02` | [**Ver Guía Escenario 2**](02-gestion-emergencias/escenarios/escenario-2-resolucion-planificada.md) |
| **3** | **Ticket Zombi en Remedy** | `TICKET_ZOMBI_REMEDY` | `P3 Admin` | **NO REQUERIDA** | `WL-06`, `JIRA-03` | [**Ver Guía Escenario 3**](02-gestion-emergencias/escenarios/escenario-3-ticket-zombi-remedy.md) |
| **4** | **Estancamiento Local** | `ESTANCAMIENTO_LOCAL` | `SL2 / P2` | **NO REQUERIDA** | `WL-07` | [**Ver Guía Escenario 4**](02-gestion-emergencias/escenarios/escenario-4-estancamiento-local.md) |
| **5** | **Infratriaje en Remedy** | `INFRATRIAJE_REMEDY` | `SL1` o `SL2` | **OBLIGATORIA** (si P1) | `WL-03` | [**Ver Guía Escenario 5**](02-gestion-emergencias/escenarios/escenario-5-infratriaje-remedy.md) |
| **6** | **Afectación Multisede Parcial** | `AFECTACION_MULTISEDE_PARCIAL` | `SL1` o `SL2` | **INFORMATIVA** | `WL-08` | [**Ver Guía Escenario 6**](02-gestion-emergencias/escenarios/escenario-6-afectacion-multisede-parcial.md) |
| **7** | **Workarounds y Candado 🔒** | `WORKAROUND_AUTORIZADO` | `SL1` o `SL2` | **OBLIGATORIA** | `WL-05` | [**Ver Guía Escenario 7**](02-gestion-emergencias/escenarios/escenario-7-workaround-autorizado.md) |
| **8** | **Reapertura / Recurrencia Activa** | `REAPERTURA_ACTIVA` | `SL1` o `SL2` | **OBLIGATORIA** (<5m) | `WL-09` | [**Ver Guía Escenario 8**](02-gestion-emergencias/escenarios/escenario-8-reapertura-activa.md) |

---

## 🖥️ Integración con las Consolas Operativas

Desde la [Consola de Triaje y Emergencias IT ↗](/dashboards/emergency-triage-console/ ':ignore :target=_blank') y el [Cockpit del Incident Manager ↗](/dashboards/incident-manager-monitor/ ':ignore :target=_blank'), el operador puede acceder en un solo clic a la guía correspondiente al escenario en el que se encuentra clasificada la incidencia mediante:
1. **Botón Directo en la Tarjeta:** `📖 Ver Procedimiento Escenario X ↗` que abre directamente la guía específica en Docsify.
2. **Ventana Modal Interactiva:** `⚡ Guía Rápida & Trazas` que permite consultar en pantalla los pasos inmediatos y copiar al portapapeles la traza oficial de Remedy correspondiente sin salir de la consola.

---

## 📚 Recursos Complementarios

* [Protocolo Integral IM-CSO Post-Triaje](02-gestion-emergencias/protocolo-im-cso-escenarios-triaje.md): Marco metodológico global, diagrama de secuencia de escalados y estándar de worklogs.
* [Manual de la Consola Operativa](02-gestion-emergencias/manual-consola-operativa.md): Instrucciones de manejo del Cockpit de guardia.
* [Matriz de Severidad ITIL](02-gestion-emergencias/triaje-itil-automatizado.md): Algoritmo de clasificación y umbrales cuantitativos.
* Skill `orange-it-emergency-management` (`.agents/skills/orange-it-emergency-management/SKILL.md`): Gobernanza de crisis y escalados.

