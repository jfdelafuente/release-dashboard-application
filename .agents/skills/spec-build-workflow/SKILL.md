---
name: spec-build-workflow
alias: flujo-construccion-spec
description: >-
  Lee una especificación guardada en la carpeta specs/ (creada por
  spec-definition-workflow) y construye exactamente lo que describe sin añadir
  funciones no pedidas ni inventar requisitos, verificando la Definición de
  terminado, reportando cobertura requisito por requisito y activando
  spec-review-workflow al finalizar. Úsese cuando el usuario invoque /build,
  flujo-construccion-spec o pida implementar una especificación existente o
  cerrar brechas devueltas por spec-review-workflow.
---

# Flujo de Construcción desde Especificación (`spec-build-workflow` / `/build`)

Construye exactamente lo que describe una especificación ya escrita, sin ampliarla ni recortarla. El valor de esta skill depende de que la construcción sea una **traducción fiel de la especificación a algo funcionando** — no una interpretación creativa de ella. Si tienes una buena idea que no está en la especificación, no la implementes aquí: anótala al final como sugerencia separada para que la persona decida, pero no la construyas sin que lo pida.

Se activa cuando:
- El usuario invoca `/build`, `flujo-construccion-spec`, o pide construir/implementar algo a partir de una especificación que ya existe como archivo en `specs/`.
- Finaliza la fase [`spec-definition-workflow`](../spec-definition-workflow/SKILL.md) (`/spec`).
- La skill [`spec-review-workflow`](../spec-review-workflow/SKILL.md) (`/spec-review`) devuelve un veredicto **NO APROBADO** junto con una lista de correcciones específicas: en ese caso, el trabajo consiste en **cerrar exactamente esas brechas**, no en reconstruir desde cero.

---

## Paso 1: Localizar la Especificación

Busca archivos Markdown (`.md`) dentro de la carpeta `specs/` en el directorio de trabajo actual:

1. **Si hay exactamente un archivo:** Úsalo.
2. **Si hay varios archivos:** Pregunta a la persona cuál de ellos quiere construir (muéstrale los nombres) en lugar de adivinar.
3. **Si la carpeta `specs/` no existe o está vacía:** Dilo con claridad y sugiere ejecutar primero `/spec` ([`spec-definition-workflow`](../spec-definition-workflow/SKILL.md)) para generar una especificación. **No improvises una especificación tú mismo ni construyas sin ella.**

Lee el archivo completo antes de empezar a construir. Presta especial atención a las secciones **Objetivo**, **Requisitos**, **Restricciones**, **Casos límite** y **Definición de terminado** — son el contrato que vas a cumplir.

Si llegas aquí porque `spec-review-workflow` encontró brechas, además de la especificación ten a mano la lista de correcciones específicas que devolvió: esa lista es tu lista de trabajo para esta pasada.

---

## Paso 2: Construir Dentro de los Límites de la Especificación

Reglas estrictas mientras construyes:

- **Requisitos obligatorios vs. opcionales:** Implementa todos los requisitos marcados como obligatorios. Si la especificación distingue requisitos obligatorios de opcionales/Fase 2, implementa los obligatorios y deja los opcionales sin construir salvo que la persona indique lo contrario en este momento.
- **Fidelidad a las restricciones:** Respeta las restricciones tal cual están escritas (stack técnico, integraciones, límites de recursos, requisitos de seguridad). No sustituyas una restricción por lo que te resulte más cómodo de implementar.
- **Manejo explícito de casos límite:** Maneja explícitamente cada caso límite listado en la especificación. Si al construir descubres que un caso límite no está claro o es contradictorio, resuélvelo de la forma más conservadora y anótalo para mencionarlo al final — no lo omitas en silencio.
- **Cero *Scope Creep* (prohibido añadir extras):** No añadas funciones, pantallas, opciones de configuración, validaciones extra ni "mejoras" que no estén pedidas. Si algo no aparece en la especificación, no lo construyas aunque te parezca una buena práctica — es responsabilidad de una especificación nueva o una revisión, no de esta construcción.
- **Detención ante bloqueo o ambigüedad:** Si durante la construcción descubres que un requisito es ambiguo, técnicamente imposible tal como está escrito, o que faltan datos imprescindibles para continuar, **detente y pregunta a la persona** en lugar de rellenar el hueco con una suposición. Una especificación mal interpretada en silencio es peor que una pregunta de más.

---

## Paso 3: Verificación contra la Definición de Terminado

Antes de dar la construcción por finalizada, repasa uno por uno los criterios de la sección **"Definición de terminado"** de la especificación y comprueba cada uno contra lo que realmente construiste (ejecuta pruebas, abre el archivo generado, corre el script o haz la comprobación real que corresponda al tipo de entregable). No te limites a asumir que algo quedó cubierto porque escribiste código para ello.

---

## Paso 4: Reportar Cobertura de Requisitos

Cuando termines, entrega un listado explícito, **requisito por requisito** (usando el texto o numeración de la sección `Requisitos` de la especificación), indicando:

- **Requisitos cubiertos:** Qué requisitos quedaron cubiertos y cómo (una frase concreta y verificable, nunca un simple *"hecho"*).
- **Casos límite manejados:** Qué casos límite se manejaron y de qué forma.
- **Definición de terminado:** Qué criterios de la Definición de terminado se verificaron y con qué resultado.
- **Pendientes o bloqueos (si los hubiera):** Cualquier requisito o caso límite que no se haya podido cubrir, con el motivo.

Este listado existe para que el siguiente paso (`spec-review-workflow`) pueda verificar cada punto contra la especificación sin tener que releer todo el proceso de construcción — sé concreto y verificable, no genérico.

---

## Transición al Terminar

Una vez entregado el listado de cobertura:
1. Activa la skill [`spec-review-workflow`](../spec-review-workflow/SKILL.md) (alias: `flujo-revision-spec` / comando `/spec-review`) para que continúe con la verificación independiente de lo construido.
2. Si `spec-review-workflow` no está disponible en el entorno actual, dilo con claridad a la persona en vez de intentar auto-aprobarlo en silencio, y pregúntale cómo quiere proceder.

