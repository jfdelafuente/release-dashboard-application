[← Volver al Índice General](../README.md)

# 02. Gestión de Emergencias IT y Triaje

Manuales operacionales, arquitectura de triaje determinista ITIL y gobernanza de incidencias críticas para Orange Tech Operations.

---

## 📚 Documentos de la Sección

| Documento | Audiencia | Propósito |
| :--- | :--- | :--- |
| **[triaje-itil-automatizado.md](./triaje-itil-automatizado.md)** | Incident Managers / N1 | Manual técnico del motor algorítmico de 5 fases, cálculo de Severidad (SL1-SL4), Reglas de Oro, discrepancias N1 y SLAs de crisis. |
| **[manual-consola-operativa.md](./manual-consola-operativa.md)** | Incident Managers | Manual táctico de uso de la Consola `/dashboards/incident-manager-monitor/`: acciones en 1 clic (Remedy/War Room/IA), cronómetros anti-drift y cockpit de crisis. |
| **[casos-de-uso-evaluacion-modulo-1-triaje.md](./casos-de-uso-evaluacion-modulo-1-triaje.md)** | Incident Managers / QA Ops | Casos de uso operacionales, criterios de aceptación, detección de Gaps Funcionales y Operativos y matriz MoSCoW para el Módulo 1. |
| **[flujo-gestion-incidencias.md](./flujo-gestion-incidencias.md)** | Equipos de Operaciones | Ciclo de vida integral de incidencias, estados operativos, escalados telefónicos (45m / 105m) y gobernanza de workarounds autorizados por IM-CSO. |
| **[notificaciones-ejecutivas.md](./notificaciones-ejecutivas.md)** | Incident Managers / IA | Flujo oficial de redacción ejecutiva para Dirección ($\le 90$ palabras completo, $\le 30$ palabras breve) mediante el agente `incident-reporter`. |
| **[catalogo-alta-prioridad.md](./catalogo-alta-prioridad.md)** | Arquitectura y Backend | Especificación técnica del catálogo unificado `high_priority_notifications.json` (`_metadata` + `data`), campos y reglas de validación. |

---

## 🧭 Mapa Rápido para Incident Managers en Guardia

* **Durante una crisis activa:** Accede a la Consola en `/dashboards/incident-manager-monitor/` y sigue el **[manual-consola-operativa.md](./manual-consola-operativa.md)**.
* **Para justificar una subescalación N1:** Consulta la matriz y criterios en **[triaje-itil-automatizado.md](./triaje-itil-automatizado.md)**.
* **Para emitir una comunicación a Dirección:** Revisa el estándar en **[notificaciones-ejecutivas.md](./notificaciones-ejecutivas.md)**.

