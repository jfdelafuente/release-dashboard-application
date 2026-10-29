# Reglas del Proyecto (`AGENTS.md`)

<!-- BEGIN BIBLIOTECA-AGENTES -->
## Agentes y Skills Desplegados (`biblioteca-agentes`)

Este repositorio cuenta con agentes declarativos y skills sincronizados desde `biblioteca-agentes`. Adopta las siguientes reglas cuando el usuario solicite alguna de estas tareas:

- **incident-reporter** (`it-incidents`): Experto en comunicación ejecutiva de incidencias de sistemas para Dirección en grandes organizaciones de servicios/telecomunicaciones. Redacta mensajes de apertura, seguimiento o cierre en dos niveles estrictos (versión completa de hasta 90 palabras y versión breve de hasta 30 palabras), integrando el contexto de Epsilon Resumen IA.
  - Lee y sigue íntegramente las instrucciones de [`agents/it-incidents/incident-reporter.md`](./agents/it-incidents/incident-reporter.md). Apóyate obligatoriamente en la skill `it-severity-matrix` ([`.agents/skills/it-severity-matrix/SKILL.md`](./.agents/skills/it-severity-matrix/SKILL.md)), `orange-it-emergency-management` ([`.agents/skills/orange-it-emergency-management/SKILL.md`](./.agents/skills/orange-it-emergency-management/SKILL.md)), `incident-executive-notifications` ([`.agents/skills/incident-executive-notifications/SKILL.md`](./.agents/skills/incident-executive-notifications/SKILL.md)), `postmortem-pir-workflow` ([`.agents/skills/postmortem-pir-workflow/SKILL.md`](./.agents/skills/postmortem-pir-workflow/SKILL.md)).

- **Regla Anti-Alucinación (Incidencias IT):** Nunca inventes horas, métricas, IPs, usuarios ni causas raíz no respaldadas por la evidencia proporcionada. Todo dato ausente debe marcarse o consultarse según indique el agente.
<!-- END BIBLIOTECA-AGENTES -->
