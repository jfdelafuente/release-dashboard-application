---
name: spec-review-workflow
alias: flujo-revision-spec
version: 1
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

El veredicto es **binario y sin matices**: no existen aprobaciones parciales, condicionales, "aprobado con observaciones" ni porcentajes de cumplimiento mínimo. No hay umbral de tolerancia.

- **APROBADO:** únicamente si el desglose del Paso 2 no contiene ni un solo ítem marcado `Parcialmente cumplido` o `Incumplido`, en ninguna de las cuatro categorías (Requisitos, Restricciones, Casos límite, Definición de terminado), y cada ítem fue efectivamente inspeccionado (ninguno quedó como `No verificado`).
- **NO APROBADO:** basta con **un solo ítem** `Parcialmente cumplido`, `Incumplido` o `No verificado` en cualquiera de las cuatro categorías, sin importar cuán menor parezca la brecha o cuántos otros ítems sí se cumplieron.

Si durante el Paso 1 o 2 no fue posible inspeccionar directamente algún requisito, restricción o caso límite (por ejemplo, porque no se pudo ejecutar el código, no se pudo acceder a un entorno, o la evidencia es ambigua), clasifícalo como **`No verificado`** — nunca lo asumas `Cumplido` por omisión ni lo ignores en el conteo. Un ítem `No verificado` siempre fuerza el veredicto a `NO APROBADO`.

### Formato de salida obligatorio

Presenta el resultado exactamente en este orden y estructura:

1. **Veredicto explícito al principio**, en su propia línea: `**APROBADO**` o `**NO APROBADO**`.
2. **Desglose completo requisito por requisito**, en una tabla o lista con, por cada ítem: identificador/cita del elemento de la especificación, categoría (Requisito / Restricción / Caso límite / Definición de terminado), estado (`Cumplido` / `Parcialmente cumplido` / `Incumplido` / `No verificado`), evidencia encontrada, y — solo si el estado no es `Cumplido` — la corrección específica y accionable. Incluye **todos** los ítems, incluso los `Cumplido`, para dejar constancia de que se revisaron.
3. **Sugerencias opcionales** (si las hay): lista aparte, claramente separada, de mejoras que no están en la especificación y que por tanto no afectan el veredicto.

#### Ejemplo relleno — Veredicto APROBADO

> **APROBADO**
>
> | # | Categoría | Elemento de la especificación | Estado | Evidencia |
> | --- | --- | --- | --- | --- |
> | R1 | Requisito | "El endpoint `/upload` debe rechazar archivos mayores a 10MB con error 413" | Cumplido | Se probó subiendo un archivo de 12MB a `/upload`; el servidor respondió `413 Payload Too Large` tal como especifica el requisito. |
> | C1 | Caso límite | "Archivo de exactamente 10MB debe aceptarse" | Cumplido | Se probó con un archivo de 10.00MB exacto; el servidor lo procesó correctamente (200 OK). |
> | DT1 | Definición de terminado | "Pruebas automatizadas del endpoint pasan en CI" | Cumplido | Se ejecutó `pytest tests/test_upload.py`; 14/14 pruebas pasaron. |
>
> Sugerencias opcionales (no afectan el veredicto): considerar loggear el tamaño del archivo rechazado para facilitar soporte.

#### Ejemplo relleno — Veredicto NO APROBADO

> **NO APROBADO**
>
> | # | Categoría | Elemento de la especificación | Estado | Evidencia | Corrección |
> | --- | --- | --- | --- | --- | --- |
> | R1 | Requisito | "El endpoint `/upload` debe rechazar archivos mayores a 10MB con error 413" | Incumplido | Se probó subiendo un archivo de 12MB a `/upload`; el servidor lo aceptó con `200 OK` y lo procesó igual que uno válido. No existe ninguna validación de tamaño en `handlers/upload.py`. | Añadir en `handlers/upload.py`, antes de procesar el archivo, una comprobación de `content-length` (o tamaño real del stream) que devuelva `413 Payload Too Large` cuando supere 10MB, con un mensaje de error indicando el límite. |
> | C1 | Caso límite | "Archivo de exactamente 10MB debe aceptarse" | No verificado | No se pudo generar un archivo de prueba de exactamente 10MB en este entorno; el caso límite no fue ejercitado. | Repetir la verificación una vez disponible un archivo de prueba de 10.00MB exacto; no asumir que pasa porque el caso de 12MB falló. |
>
> Sugerencias opcionales (no afectan el veredicto): ninguna.

---

## Prohibiciones (nunca hacer esto)

- **Nunca** declares `APROBADO` si queda al menos un ítem `Parcialmente cumplido`, `Incumplido` o `No verificado` en el desglose.
- **Nunca** marques un ítem como `Cumplido` sin haberlo inspeccionado directamente (leyendo el archivo, ejecutando el código o las pruebas, abriendo el documento). Si no pudiste verificarlo, usa `No verificado`, nunca `Cumplido` por defecto ni por "parece razonable que funcione".
- **Nunca** afirmes en el reporte que se ejecutó una prueba, comando o inspección que no se ejecutó realmente. Si no se corrió, dilo explícitamente (`No verificado`) en vez de inventar evidencia.
- **Nunca** promedies, pondérés o calcules un "porcentaje de cumplimiento" para decidir el veredicto — es binario, un solo fallo basta para `NO APROBADO`.
- **Nunca** marques como brecha algo que la especificación no pide explícitamente; eso va solo en "Sugerencias opcionales", separado del veredicto.
- **Nunca** inventes una especificación ni proceses una revisión si `specs/` no existe o está vacía — detente y pregunta.
- **Nunca** omitas del desglose los ítems que sí se cumplieron; el reporte debe listar todos los ítems evaluados, no solo los que fallaron.

---

## Transición al Terminar

- **Si el veredicto es `NO APROBADO`:** Activa la skill [`spec-build-workflow`](../spec-build-workflow/SKILL.md) (`/build` / `flujo-construccion-spec`) pasándole la lista de correcciones específicas (incluyendo los ítems `No verificado`, que deben re-chequearse, no asumirse) como su lista de trabajo para resolver a continuación — no reinicies la construcción desde cero, el objetivo es que `spec-build-workflow` cierre exactamente esas brechas. Si la skill no está disponible, entrega la lista de correcciones directamente a la persona para que decida cómo aplicarlas.
- **Si el veredicto es `APROBADO`:** Dilo con claridad y no actives ninguna otra skill — el ciclo **Especificación (`/spec`) → Construcción (`/build`) → Revisión (`/spec-review`)** termina aquí con éxito.

