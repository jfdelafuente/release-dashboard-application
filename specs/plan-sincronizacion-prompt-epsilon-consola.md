# Plan de Evolución: Sincronización del Prompt Epsilon IA con la Consola Operativa

> **Estado:** Planificado (próxima iteración posterior al cierre de `feat/internal-epsilon-ia`)  
> **Documento de Prompt objetivo:** [`data/resumen_incidencia_epsilon.md`](../../data/resumen_incidencia_epsilon.md)  
> **Motor y validador:** [`converters/src/epsilon_service.py`](../../converters/src/epsilon_service.py)  
> **Consumidores principales:** [`converters/cli/evaluate_incident_notifications.py`](../../converters/cli/evaluate_incident_notifications.py) y [`dashboards/emergency-triage-console/triage.js`](../../dashboards/emergency-triage-console/triage.js)

---

## 1. Objetivo

Alinear el contenido y la estructura del JSON generado por el **Motor Interno Epsilon IA** con las señales heurísticas y reglas ITIL que utiliza la **Consola de Emergencias IT (`emergency-triage-console`)** para clasificar escenarios, calcular estancamiento, activar el candado de *workaround* y detectar infratriajes o cierres en falso (*tickets zombi*).

Gracias al **Smart Fingerprint Cache** implementado en `feat/internal-epsilon-ia`, cualquier mejora aplicada a las secciones 1–4 de `data/resumen_incidencia_epsilon.md` cambia automáticamente el `prompt_hash` y regenera los resúmenes afectados sin necesidad de purgas manuales ni despliegues externos.

---

## 2. Arquitectura en Dos Fases

Para minimizar riesgos en producción y mantener 100% compatible el contrato actual, el plan se divide en **2 fases independientes**:

- **Fase 1 (Ajustes de Prompt compatibles hacia atrás — Riesgo bajo):** Refinamiento de reglas textuales sobre los campos existentes (`impacto`, `solucion`, `hitosTecnicos`, `bloqueos`) sin alterar el esquema JSON ni la consola.
- **Fase 2 (Vía 2 Estructurada — Campo opcional `triaje`):** Activación del bloque JSON estructurado `triaje` para que la consola consuma señales deterministas en lugar de depender únicamente de expresiones regulares sobre texto libre.

---

## 3. Detalle de la Fase 1: Refinamiento del Prompt Actual (Sin cambios de esquema)

### 3.1 Último hito sustantivo garantizado (`hitosTecnicos`)
- **Problema actual:** `compute_worklog_stagnation()` en `evaluate_incident_notifications.py` inspecciona las marcas temporales de `hitosTecnicos` para calcular si un ticket supera los umbrales de estancamiento (`>6h`, `>12h`, `>24h`). Si el LLM prioriza eventos iniciales y omite el último comentario sustantivo del resolutor, la consola puede marcar un falso estancamiento.
- **Cambio en Regla 5 (`hitosTecnicos`):** Exigir que el último elemento del array (`hitosTecnicos[-1]`) corresponda **obligatoriamente al apunte técnico sustantivo más reciente** de Remedy (excluyendo ruido automático de cambios de asignación/prioridad), con su marca exacta en `Europe/Madrid`.
- **Criterio de aceptación:** En tickets con worklogs recientes (`< 6h`), `hitosTecnicos[-1]` refleja la fecha/hora del último apunte técnico real.

### 3.2 Fórmulas normalizadas de *Workaround* (`impacto`)
- **Problema actual:** La consola busca expresiones regulares en `impacto` y `bloqueos` para decidir si activa el **candado de gobernanza de workaround (Escenario 7)** y calibrar la urgencia operativa. Redacciones ambiguas pueden omitir la activación del candado.
- **Cambio en Regla 1 (`impacto`):** Exigir cerrar el campo `impacto` (manteniendo el límite de $\le 30$ palabras) con una de estas tres fórmulas inequívocas:
  1. `Sin método alternativo disponible.` *(bloqueo total)*
  2. `Workaround activo (pendiente de erradicación definitiva / visado CSO).` *(activa candado CSO)*
  3. `Existe método alternativo operativo (<descripción breve>).`
- **Criterio de aceptación:** 100% de los resúmenes pasan `WORKAROUND_REGEX` en `EpsilonResumenModel` y activan correctamente `workaround_pendiente_cso` cuando hay mitigación temporal.

### 3.3 Deduplicación multisede en tickets `OE-03` (`problema` e `impacto`)
- **Problema actual:** En incidencias masivas multisede, Remedy recibe notas `OE-03 · NUEVA SEDE AFECTADA` que en ocasiones duplican una misma sede (ej. doble envío desde un mismo centro).
- **Cambio en Reglas 1 y 8:** Instruir explícitamente al modelo para **deduplicar sedes repetidas** por nombre de centro antes de sumar agentes/usuarios afectados o enumerar sedes impactadas.
- **Criterio de aceptación:** El conteo de sedes y usuarios en `impacto` coincide con el conjunto único de sedes presentes en el ticket + worklogs `OE-03`.

### 3.4 Señalización obligatoria de ventanas `PaP / Release / CRQ` (`bloqueos`)
- **Problema actual:** La clasificación automática de **Escenario 2 (`RESOLUCION_PLANIFICADA`)** se apoya en detectar `[Ventana Release]` dentro de `bloqueos`, además de `solucion` y `siguienteAccion`. Si el modelo solo menciona la release en `solucion`, la señal en `bloqueos` queda vacía.
- **Cambio en Regla 6 (`bloqueos`):** Indicar que siempre que exista un parche comprometido, despliegue planificado (`PaP`, `CRQ`, ventana nocturna) o fecha objetivo documentada, se incluya obligatoriamente en `bloqueos` con prefijo `[Ventana Release]: <detalle y fecha si consta>`.
- **Criterio de aceptación:** Todo ticket con fecha de release/parche en worklogs genera entrada `[Ventana Release]: ...` en `bloqueos`.

### 3.5 Visibilidad explícita de *Tickets Zombi* y *Reaperturas* (`Escenarios 3 y 8`)
- **Problema actual:** La consola cruza `estadoActual`, `solucion`, `bloqueos` e `hitosTecnicos` para diferenciar una emergencia viva de un **Ticket Zombi** (resuelto técnicamente pero esperando confirmación de sede/usuario) o de una **Reapertura**.
- **Cambio en Reglas 6 y 7:**
  - Si un grupo resolutor reporta resolución o solicita validación al peticionario sin confirmación final aún, exigir añadir `[Validación Negocio]: Pendiente de confirmación por sede/peticionario` en `bloqueos`.
  - Si el peticionario rechazó el cierre o reabrió el ticket, exigir documentar el motivo en `solucion` y en el último hito de `hitosTecnicos`.
- **Criterio de aceptación:** Los casos de prueba de Escenario 3 y Escenario 8 quedan reflejados de forma inequívoca sin necesidad de inferencias externas.

---

## 4. Detalle de la Fase 2: Bloque Estructurado Opcional `triaje` (Vía 2)

Una vez validada y estabilizada la Fase 1 en producción, se activará la evolución ya esbozada en la Sección 6 de `data/resumen_incidencia_epsilon.md`:

### 4.1 Cambios en el Prompt y Esquema JSON
Añadir al esquema solicitado en `data/resumen_incidencia_epsilon.md` el objeto opcional `triaje`:
- `escenario`: `"EMERGENCIA_ACTIVA" | "RESOLUCION_PLANIFICADA" | "RESOLUCION_PARCIAL" | "REAPERTURA" | "ESTANCAMIENTO"`
- `workaround`: `boolean`
- `multisede`: `boolean`
- `alertaInfratriaje`: `boolean`
- `desgloseSedes`: `[{ "sede": string, "estado": "OK_CONFIRMADO" | "FALLO_ACTIVO" }]`

### 4.2 Cambios en Backend y Consola
1. **`converters/src/epsilon_service.py`**:
   - Añadir `EpsilonTriajeModel` (opcional, `triaje: Optional[EpsilonTriajeModel] = None`) dentro de `EpsilonResumenModel` para validar tipos sin romper compatibilidad con caches o consumidores antiguos.
   - Incorporar una comprobación informativa en `evaluate_contract()` para auditar el bloque `triaje` en `scripts/test_epsilon_prompt.py`.
2. **`converters/cli/evaluate_incident_notifications.py`**:
   - Consumir `epsilon_data.get("triaje")` con prioridad sobre las heurísticas por regex cuando esté presente, manteniendo el motor heurístico actual como fallback determinista.
   - Exponer `desgloseSedes` en el catálogo para que el modal de triaje en `triage.js` muestre directamente qué sedes ya confirmaron OK y cuáles siguen en fallo activo.

---

## 5. Plan de Pruebas y Criterios de Validación

1. **Calibración empírica con CLI (`scripts/test_epsilon_prompt.py --url ... --strict`):**
   - Probar contra al menos 1 ticket real representativo de cada escenario crítico (Multisede, Workaround, Resolución Planificada, Zombi/Reapertura y Diagnóstico inicial).
   - Confirmar `10/10` reglas `[OK]` y `0` alucinaciones de fechas/métricas frente a los worklogs crudos de Remedy.
2. **Batería de tests unitarios (`pytest`):**
   - Añadir casos en `converters/tests/unit/test_epsilon_service.py` y `converters/tests/unit/test_epsilon_prompt_cli.py` para validar deduplicación multisede, fórmulas de workaround y, en Fase 2, el submodelo `EpsilonTriajeModel`.
3. **Verificación de invalidación automática:**
   - Comprobar en un ticket cacheado previamente que al modificar `data/resumen_incidencia_epsilon.md` cambia `meta.prompt_hash` y `resolve_or_generate_epsilon_summary()` regenera sin requerir `--force`.

---

## 6. Riesgos y Mitigación

| Riesgo | Impacto | Mitigación |
| :--- | :--- | :--- |
| El bloque `triaje` aumenta tokens o provoca fallos Pydantic en Fase 2 | Medio | Mantener `triaje` como campo opcional en Fase 2 y apoyarse en `max_retries=1` (autocorrección). |
| Regeneración masiva simultánea al cambiar `prompt_hash` en producción | Bajo | La pre-generación en `sync_montmc_incidents.py` procesa únicamente incidencias activas (excluye terminales) con concurrencia acotada (3 hilos). |
| Regresión puntual en calidad de resúmenes | Bajo | Conmutador inmediato vía `EPSILON_PROVIDER_MODE=soptmc` o `git revert` sobre `data/resumen_incidencia_epsilon.md`. |
