# Contract: Severity Evaluation Rules (it-severity-matrix)

**Feature**: `012-high-priority-incident-notifications` | **Date**: 2026-10-26

Este documento formaliza la lógica de evaluación y cruce de impacto y urgencia conforme a la skill `it-severity-matrix`.

---

## 1. Reglas de Inferencia de Impacto

| Nivel de Impacto | Patrones en Epsilon IA (`impacto` / `problema`) y Ticket | Criterios Objetivos ITIL |
| :--- | :--- | :--- |
| **Alto** | `caída total`, `indisponibilidad masiva`, `bloqueo`, `pasarela`, `pérdida de datos`, `afectación a más del 50%`, `core`, `crítico`, `sin solución alternativa`, `Ticket.Impacto == 'Masiva'` con indisponibilidad | Caída total de servicio crítico o cara al cliente. >50% de usuarios. Riesgo financiero/datos. Sin workaround. |
| **Medio** | `degradación`, `latencia elevada`, `lentitud`, `10% a 50%`, `afectación parcial`, `workaround manual`, `reintentos` | Degradación severa o caída parcial importante no bloqueante global. Workaround manual existente. |
| **Bajo** | `incidencia aislada`, `usuario único`, `<10%`, `consulta`, `entorno no productivo`, `DEV`, `QA`, `workaround sencillo` | Fallo menor o aislado. Entornos de prueba. Workaround inmediato. |

---

## 2. Reglas de Inferencia de Urgencia

| Nivel de Urgencia | Patrones en Epsilon IA y Ticket | Criterios Operativos |
| :--- | :--- | :--- |
| **Alta** | `Estatus != 'Cerrado'`, `en vivo`, `horario pico`, `campaña activa`, `bloqueante 24x7`, `hitos sin resolución` | Fallo ocurriendo en tiempo real con impacto activo. Requiere intervención inmediata. |
| **Media** | `contenido temporalmente`, `mitigación provisional aplicada`, `incidencia en seguimiento` | Operativa degradada pero contenida durante unas horas. |
| **Baja** | `Estatus == 'Cerrado'`, `cosmético`, `resolución planificada` | Problema resuelto, cosmético o diferible. |

---

## 3. Matriz de Cruce de Prioridad

$$\text{Prioridad} = \text{Impacto} \times \text{Urgencia}$$

```
                URGENCIA ALTA        URGENCIA MEDIA       URGENCIA BAJA
IMPACTO ALTO    P1 (Crítica)         P1 / P2 (Alta)*      P2 (Alta)
IMPACTO MEDIO   P2 (Alta)            P2 / P3 (Media)*     P3 (Media)
IMPACTO BAJO    P3 (Media)           P3 (Media)           P4 (Baja)
```

*\*Nota de desempate*:
- `Impacto Alto × Urgencia Media`: Asigna **P1** si el sistema afectado es de cara directa a clientes o pasarela de pagos/core; en otro caso asigna **P2**.
- `Impacto Medio × Urgencia Media`: Asigna **P2** si afecta a un departamento operativo clave; en otro caso asigna **P3**.

---

## 4. Detección de Discrepancia de Prioridad

Se define una discrepancia como:
$$\text{es\_discrepancia} = \text{Severidad}(\text{Prioridad Calculada}) > \text{Severidad}(\text{Prioridad Ticket})$$

Donde la escala de severidad es:
$$\text{P1 (4)} > \text{P2 (3)} > \text{P3 (2)} > \text{P4 (1)}$$

**Ejemplos de Discrepancia**:
- Ticket dice `Media` (P3) pero la IA calcula `P1` $\rightarrow$ **⚠️ Discrepancia Crítica (Subescalación)**.
- Ticket dice `Baja` (P4) pero la IA calcula `P2` $\rightarrow$ **⚠️ Discrepancia Alta**.
- Ticket dice `Alta` (P2) y la IA calcula `P2` $\rightarrow$ Coincidencia normal (sin discrepancia).

