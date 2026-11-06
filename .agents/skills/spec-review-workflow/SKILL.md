---
name: spec-review-workflow
alias: flujo-revision-spec
description: >-
  Audita y compara lo construido por spec-build-workflow contra la
  especificación guardada en specs/, evaluando requisito por requisito,
  restricción y caso límite, y emite un veredicto estricto (APROBADO o NO
  APROBADO) con correcciones accionables que reenvía a spec-build-workflow si
  hay brechas. Úsese cuando el usuario invoque /spec-review, flujo-revision-spec
  o pida verificar/auditar una implementación frente a su especificación.
---

# Flujo de Revisión y Auditoría de Especificación (`spec-review-workflow` / `/spec-review`)

Verifica que una construcción cumple exactamente con su especificación, ni más ni menos. El objetivo de esta skill es actuar como **última línea de control** antes de dar algo por terminado: no basta con que *"parezca que funciona"*, cada requisito escrito en la especificación tiene que quedar comprobado uno por uno contra lo que realmente existe.

Se activa cuando:
- El usuario invoca `/spec-review`, `flujo-revision-spec`, o pide verificar/auditar/revisar una construcción frente a su especificación (distinto de revisar un pull request general de GitHub).
- Finaliza una pasada de construcción de [`spec-build-workflow`](../spec-build-workflow/SKILL.md) (`/build`).

---

## Paso 1: Localizar Especificación y Construcción Real

1. Busca archivos Markdown (`.md`) dentro de la carpeta `specs/` en el directorio de trabajo actual:
   - **Si hay exactamente un archivo:** Úsalo.
   - **Si hay varios archivos:** Pregunta a la persona cuál de ellos corresponde a lo que se acaba de construir, en lugar de adivinar.
   - **Si la carpeta `specs/` no existe o está vacía:** Dilo con claridad y pregunta cómo proceder — **no inventes una especificación ni intentes revisar sin ella**.
2. Lee el archivo completo de especificación, prestando especial atención a las secciones **Requisitos**, **Restricciones**, **Casos límite** y **Definición de terminado**.
3. **Inspección directa de lo construido:** Identifica qué se construyó realmente mirando los archivos, el código, los documentos o el sistema que corresponda al alcance de la especificación (por el contexto de la conversación, por los archivos modificados recientemente, o preguntando a la persona dónde está la construcción si no es evidente).
   - **Prohibido confiar a ciegas en resúmenes:** No confíes en un resumen de lo que *"se supone"* que se hizo — inspecciona directamente el resultado (lee los archivos, ejecuta el código, corre las pruebas, abre el documento, lo que sea apropiado para el tipo de entregable).

---

## Paso 2: Comparar Requisito por Requisito

Recorre cada requisito obligatorio de la sección **Requisitos** de la especificación, uno a uno, y clasifícalo como:

- **Cumplido:** Existe y funciona tal como lo describe la especificación.
- **Parcialmente cumplido:** Existe pero le falta algo, se comporta distinto a lo especificado, o solo cubre parte del requisito.
- **Incumplido:** No existe o no funciona en absoluto.

Haz exactamente lo mismo con:
- Cada **Restricción** (¿se respetó?).
- Cada **Caso límite** listado (¿se maneja como se especificó, se ignoró, o se maneja de forma distinta a la pedida?).
- Cada criterio de la **Definición de terminado**.

> ⚠️ **Límite estricto de la auditoría:** No evalúes ni penalices nada que la especificación no pida — esta revisión no es una auditoría de calidad general subjetiva, es una comprobación de fidelidad a la especificación. Si ves algo que te parece mejorable pero no está en la especificación, **no lo marques como brecha**; como mucho anótalo aparte al final como sugerencia opcional, claramente separado de los resultados de la revisión.

Por cada requisito, restricción o caso límite que **no esté completamente cumplido**, registra obligatoriamente:
1. **Elemento exacto de la especificación que falla:** Cita el texto o el número/nombre del requisito tal como aparece en el archivo, no una paráfrasis vaga.
2. **Evidencia encontrada en la construcción real:** Qué existe, qué falta o qué se comporta distinto.
3. **Corrección específica y accionable:** Qué cambio concreto hay que realizar para cerrar esa brecha (nunca frases genéricas como *"arreglar esto"* o *"revisar validaciones"*; por ejemplo: *"el requisito 'debe rechazar archivos mayores a 10MB' no está implementado; añadir una validación de tamaño antes de procesar el archivo y devolver un error claro cuando se exceda"*).

---

## Paso 3: Veredicto Estricto

Solo declara la construcción **APROBADA** si **absolutamente todos** los requisitos obligatorios, restricciones y casos límite de la especificación quedaron completamente cumplidos, y todos los criterios de la Definición de terminado se verificaron con éxito. **Un solo punto incumplido o parcialmente cumplido significa que la construcción NO está aprobada todavía**, sin importar cuán menor parezca la brecha.

Presenta el resultado en dos partes claras:
1. **Veredicto explícito al principio:** `**APROBADO**` o `**NO APROBADO**`.
2. **Desglose completo requisito por requisito:** Incluye también los que sí se cumplieron (marcados como `Cumplido`) para que quede constancia de que se revisaron, junto con las correcciones específicas y accionables para cada punto que falló.

---

## Transición al Terminar

- **Si el veredicto es `NO APROBADO`:** Activa la skill [`spec-build-workflow`](../spec-build-workflow/SKILL.md) (`/build` / `flujo-construccion-spec`) pasándole la lista de correcciones específicas como su lista de trabajo para resolver a continuación — no reinicies la construcción desde cero, el objetivo es que `spec-build-workflow` cierre exactamente esas brechas. Si la skill no está disponible, entrega la lista de correcciones directamente a la persona para que decida cómo aplicarlas.
- **Si el veredicto es `APROBADO`:** Dilo con claridad y no actives ninguna otra skill — el ciclo **Especificación (`/spec`) → Construcción (`/build`) → Revisión (`/spec-review`)** termina aquí con éxito.

