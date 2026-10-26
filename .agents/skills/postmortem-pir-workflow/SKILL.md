---
name: postmortem-pir-workflow
alias: flujo-postmortem-pir
description: >-
  Guía paso a paso la elaboración de informes Post-Incident Review (PIR) o Post-Mortem
  sin culpa (Blameless), incluyendo cálculo de métricas operativas (MTTD, MTTA, MTTR),
  línea de tiempo verificada y plan de acciones CAPA. Úsese al documentar el cierre
  o análisis retrospectivo de una incidencia IT.
---

# Flujo de Trabajo para Post-Incident Review (PIR / Blameless Post-Mortem)

Esta skill establece el estándar para transformar los datos crudos de una incidencia resuelta en un documento de aprendizaje organizacional riguroso y libre de culpas (*Blameless*).

## 1. Principios de Cultura *Blameless* (Sin Culpa)
- **Prohibido señalar individuos:** Nunca escribas *"Juan ejecutó un script sin permisos"* o *"Error humano del operador X"*.
- **Enfoque sistémico:** Reemplaza nombres propios por roles (*"El ingeniero de guardia"*) y pregunta **por qué el sistema permitió el fallo** (ej. *"El entorno de producción carecía de bloqueo automático frente a borrados masivos sin flag de confirmación"*).

## 2. Cálculo de Métricas Clave (SLA / Tiempos)
A partir de las marcas de tiempo disponibles, calcula (o marca como `[PENDIENTE]` si faltan horas exactas):
1. **$T_0$ (Inicio real del fallo):** Momento en que comenzó la degradación o caída.
2. **$T_1$ (Detección / Alerta):** Momento en que la monitorización o un usuario reportó el fallo.
3. **$T_2$ (Reconocimiento / Intervención):** Momento en que el equipo técnico inició el diagnóstico.
4. **$T_3$ (Mitigación / Restauración del servicio):** Momento en que el servicio volvió a operar para los usuarios.
5. **$T_4$ (Resolución definitiva):** Momento en que se cerró el riesgo subyacente.

**Fórmulas operativas:**
- **MTTD (Mean Time To Detect):** $T_1 - T_0$
- **MTTA (Mean Time To Acknowledge):** $T_2 - T_1$
- **MTTR / Tiempo de Restauración:** $T_3 - T_0$ (Duración total del impacto)

## 3. Estructura de Acciones CAPA (Correctivas y Preventivas)
Toda acción derivada de una incidencia debe clasificarse en una de estas tres categorías y ser verificable:
- **Mitigación / Corrección Inmediata (Short-Term):** Qué se hizo para restaurar el servicio.
- **Detección (Observabilidad):** Qué alerta o test sintético faltó para haber detectado el fallo antes.
- **Prevención (Long-Term / Arquitectura):** Qué cambio técnico o de proceso impedirá que esta clase de fallo vuelva a ocurrir.

Cada acción debe tener: `[ID] | Tipo (Detección/Prevención/Mitigación) | Acción Concreta | Equipo/Rol Responsable | Prioridad`.

## 4. Checklist de Validación antes de Entregar el PIR
- [ ] ¿El resumen ejecutivo puede ser entendido por Dirección / Negocio sin leer jerga de bajo nivel?
- [ ] ¿La línea temporal distingue claramente entre eventos del sistema, alertas y acciones humanas?
- [ ] ¿Se explica por qué los controles existentes no detectaron ni evitaron el incidente?
- [ ] ¿Cada causa contribuyente tiene al menos una acción preventiva (CAPA) asociada?

