---
name: spec-build-workflow
alias: flujo-construccion-spec
version: 1
description: >-
  Lee una especificación guardada en la carpeta specs/ (creada por
  spec-definition-workflow) y construye exactamente lo que describe sin añadir
  funciones no pedidas ni inventar requisitos, verificando la Definición de
  terminado, reportando cobertura requisito por requisito en un formato fijo
  y activando spec-review-workflow al finalizar. Úsese cuando el usuario
  invoque /build, flujo-construccion-spec o pida implementar una
  especificación existente o cerrar brechas devueltas por
  spec-review-workflow.
---

# Flujo de Construcción desde Especificación (`spec-build-workflow` / `/build`)

**Qué hace esta skill en una frase:** toma una especificación ya escrita en `specs/` y la traduce fielmente en una implementación funcionando, sin añadir ni recortar alcance, reportando al final la cobertura requisito por requisito en un formato fijo y entregando el control a `spec-review-workflow`.

El valor de esta skill depende de que la construcción sea una **traducción fiel de la especificación a algo funcionando** — no una interpretación creativa de ella. Si tienes una buena idea que no está en la especificación, no la implementes aquí: anótala al final como sugerencia separada para que la persona decida, pero no la construyas sin que lo pida.

Se activa cuando:
- El usuario invoca `/build`, `flujo-construccion-spec`, o pide construir/implementar algo a partir de una especificación que ya existe como archivo en `specs/`.
- Finaliza la fase [`spec-definition-workflow`](../spec-definition-workflow/SKILL.md) (`/spec`).
- La skill [`spec-review-workflow`](../spec-review-workflow/SKILL.md) (`/spec-review`) devuelve un veredicto **NO APROBADO** junto con una lista de correcciones específicas: en ese caso, el trabajo consiste en **cerrar exactamente esas brechas**, no en reconstruir desde cero.

---

## Proceso Paso a Paso

### Paso 1: Localizar y leer la especificación

1. Busca archivos Markdown (`.md`) dentro de la carpeta `specs/` en el directorio de trabajo actual.
2. **Si hay exactamente un archivo:** Úsalo.
3. **Si hay varios archivos:** Pregunta a la persona cuál de ellos quiere construir (muéstrale los nombres) en lugar de adivinar.
4. **Si la carpeta `specs/` no existe o está vacía:** Dilo con claridad y sugiere ejecutar primero `/spec` ([`spec-definition-workflow`](../spec-definition-workflow/SKILL.md)) para generar una especificación. **No improvises una especificación tú mismo ni construyas sin ella.**
5. Lee el archivo completo antes de escribir una sola línea. Presta especial atención a las secciones **Objetivo**, **Requisitos**, **Restricciones**, **Casos límite** y **Definición de terminado** — son el contrato que vas a cumplir.
6. Numera mentalmente (o anota) cada requisito de la sección **Requisitos** tal como aparece en la especificación (p. ej. R1, R2, R3…) — esa numeración es la que usarás literalmente en el Paso 4. Si la especificación ya numera los requisitos, usa esa numeración; si no, numéralos tú en el orden en que aparecen y dilo explícitamente en el reporte final.
7. Si llegas aquí porque `spec-review-workflow` encontró brechas, además de la especificación ten a mano la lista de correcciones específicas que devolvió: esa lista es tu lista de trabajo para esta pasada, no la especificación completa de nuevo.

### Paso 2: Construir dentro de los límites de la especificación

Reglas estrictas mientras construyes:

- **Requisitos obligatorios vs. opcionales:** Implementa todos los requisitos marcados como obligatorios. Si la especificación distingue requisitos obligatorios de opcionales/Fase 2, implementa los obligatorios y deja los opcionales sin construir salvo que la persona indique lo contrario en este momento.
- **Fidelidad a las restricciones:** Respeta las restricciones tal cual están escritas (stack técnico, integraciones, límites de recursos, requisitos de seguridad). No sustituyas una restricción por lo que te resulte más cómodo de implementar.
- **Manejo explícito de casos límite:** Maneja explícitamente cada caso límite listado en la especificación. Si al construir descubres que un caso límite no está claro o es contradictorio, resuélvelo de la forma más conservadora y anótalo para mencionarlo al final — no lo omitas en silencio.
- **Cero *Scope Creep* (prohibido añadir extras):** No añadas funciones, pantallas, opciones de configuración, validaciones extra ni "mejoras" que no estén pedidas. Si algo no aparece en la especificación, no lo construyas aunque te parezca una buena práctica — es responsabilidad de una especificación nueva o una revisión, no de esta construcción.
- **Detención ante bloqueo o ambigüedad:** Si durante la construcción descubres que un requisito es ambiguo, técnicamente imposible tal como está escrito, o que faltan datos imprescindibles para continuar, **detente y pregunta a la persona** en lugar de rellenar el hueco con una suposición. Una especificación mal interpretada en silencio es peor que una pregunta de más.

### Paso 3: Verificación contra la Definición de terminado

Antes de dar la construcción por finalizada, repasa uno por uno los criterios de la sección **"Definición de terminado"** de la especificación y comprueba cada uno contra lo que realmente construiste: ejecuta las pruebas, abre el archivo generado, corre el script o haz la comprobación real que corresponda al tipo de entregable. **Nunca marques un criterio como verificado sin haber ejecutado esa comprobación real** — no basta con haber escrito código que debería cumplirlo.

### Paso 4: Reportar cobertura de requisitos (formato exacto)

Cuando termines, entrega el reporte de cobertura usando **exactamente** esta plantilla, con una entrada por cada requisito numerado en el Paso 1 (ningún requisito puede quedar fuera del listado, ni siquiera los no cubiertos):

```markdown
## Reporte de Cobertura — spec-build-workflow

**Especificación:** <ruta del archivo, ej. specs/003-ejemplo/spec.md>

### Requisitos

- [x] R1 — <texto o resumen del requisito>: <frase concreta y verificable de cómo quedó cubierto, ej. "implementado en src/auth/login.py:42, cubierto por test_login_success">
- [x] R2 — <texto o resumen del requisito>: <frase concreta y verificable>
- [ ] R3 — <texto o resumen del requisito>: PENDIENTE — <motivo concreto del bloqueo>

### Casos límite
- <caso límite 1>: <cómo se manejó, con referencia a archivo/función>
- <caso límite 2>: <cómo se manejó>

### Definición de terminado
- <criterio 1>: ✅ verificado — <cómo se comprobó, ej. "pytest tests/test_login.py: 8 passed">
- <criterio 2>: ❌ no verificado — <motivo>

### Pendientes o bloqueos
- <requisito o caso límite no cubierto, con motivo> (o "Ninguno" si no hay pendientes)
```

**Ejemplo relleno** (especificación ficticia `specs/003-ejemplo/spec.md` con 3 requisitos — R1 y R2 obligatorios, R3 opcional marcado como no incluido en esta pasada):

```markdown
## Reporte de Cobertura — spec-build-workflow

**Especificación:** specs/003-ejemplo/spec.md

### Requisitos

- [x] R1 — El formulario de login debe rechazar contraseñas de menos de 8 caracteres: implementado en src/auth/validators.py:15 (`validate_password_length`), cubierto por test_validators.py::test_password_too_short (pasa).
- [x] R2 — Tras 5 intentos fallidos, la cuenta se bloquea 15 minutos: implementado en src/auth/lockout.py:30 (`check_lockout_window`), cubierto por test_lockout.py::test_lockout_after_five_failures (pasa).
- [ ] R3 — (Opcional/Fase 2) Soporte de login con proveedor externo (OAuth): NO CONSTRUIDO — requisito marcado como opcional en la especificación, se deja sin implementar según el Paso 2 de esta skill; no hubo indicación de la persona para incluirlo ahora.

### Casos límite
- Contraseña vacía: rechazada con el mismo mensaje que "menos de 8 caracteres" (src/auth/validators.py:12).
- Usuario inexistente en el intento de login: responde con mensaje genérico "credenciales inválidas" para no filtrar qué cuentas existen (src/auth/login.py:50).

### Definición de terminado
- "Todos los tests de auth pasan": ✅ verificado — `pytest tests/auth/ -v`: 14 passed.
- "El endpoint /login responde en menos de 300ms": ✅ verificado — medido con `curl -w "%{time_total}"`, 180ms promedio sobre 10 llamadas.

### Pendientes o bloqueos
- R3 (OAuth externo) queda sin construir por ser opcional; requiere decisión explícita de la persona para incluirse en una pasada futura.
```

Este reporte existe para que el siguiente paso (`spec-review-workflow`) pueda verificar cada punto contra la especificación sin tener que releer todo el proceso de construcción — cada línea debe ser concreta y verificable (archivo, función, comando ejecutado, resultado de test), nunca un simple *"hecho"* o *"funciona"*.

---

## Prohibiciones (nunca hagas esto)

- **Nunca** construyas sin una especificación real en `specs/` — ni la improvises, ni la infieras de una conversación anterior.
- **Nunca** añadas funciones, validaciones, pantallas o "mejoras" que no estén explícitamente pedidas en la especificación (cero *scope creep*), aunque te parezcan buenas prácticas obvias.
- **Nunca** implementes un requisito opcional/Fase 2 sin que la persona lo pida explícitamente en el momento de construir.
- **Nunca** marques un requisito, caso límite o criterio de la Definición de terminado como cubierto/verificado sin haber comprobado realmente el resultado (ejecutar el test, correr el script, abrir el archivo generado). Si no lo verificaste, repórtalo como pendiente, no como hecho.
- **Nunca** rellenes en silencio un requisito ambiguo, contradictorio o técnicamente imposible con una suposición propia — detente y pregunta a la persona.
- **Nunca** entregues el reporte de cobertura omitiendo requisitos de la lista, usando frases genéricas como "hecho" o "completado" sin detalle verificable, o con un formato distinto al definido en el Paso 4.
- **Nunca** omitas la transición final a `spec-review-workflow`, ni te auto-apruebes como si esa revisión ya hubiera ocurrido.

---

## Transición al Terminar

Una vez entregado el reporte de cobertura con el formato exacto del Paso 4:
1. Activa la skill [`spec-review-workflow`](../spec-review-workflow/SKILL.md) (alias: `flujo-revision-spec` / comando `/spec-review`) para que continúe con la verificación independiente de lo construido.
2. Si `spec-review-workflow` no está disponible en el entorno actual, dilo con claridad a la persona en vez de intentar auto-aprobarlo en silencio, y pregúntale cómo quiere proceder. En ningún caso des el trabajo por "aprobado" sin que esa revisión se haya ejecutado.

