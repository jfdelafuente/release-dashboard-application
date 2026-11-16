---
name: spec-definition-workflow
alias: flujo-especificacion
version: 1.1
description: >-
  Entrevista al usuario una pregunta a la vez sobre una función o aplicación
  que quiere construir hasta definir Objetivo, Requisitos obligatorios,
  Restricciones, Casos límite y Definición de terminado, escribe la
  especificación en specs/<slug>.md sin tocar código y activa la fase de
  construcción (spec-build-workflow). Úsese cuando el usuario invoque /spec,
  flujo-especificacion o pida especificar algo antes de construirlo.
---

# Flujo de Definición de Especificación (`spec-definition-workflow` / `/spec`)

Entrevista al usuario sobre una función o aplicación que quiere construir y produce una especificación escrita antes de que se toque una sola línea de código. El objetivo de esta skill es separar **"entender qué hay que construir"** de **"construirlo"**: muchas veces se empieza a programar con una idea a medias, y el resultado no coincide con lo que la persona tenía en la cabeza. Esta skill evita eso forzando una conversación completa primero.

Se activa cuando el usuario invoca `/spec`, `flujo-especificacion`, o pide explícitamente "especificar" una función, aplicación o feature antes de construirla.

---

## 1. Regla Principal: No Construir Todavía

Mientras dure la entrevista:
- **No crees archivos de código**, no propongas arquitectura y no generes esqueletos de proyecto.
- La **única escritura permitida** antes de terminar la entrevista es el propio archivo de especificación al final (`specs/<slug>.md`).
- Si en algún momento tienes la tentación de *"ya sé cómo hacer esto, lo empiezo mientras pregunto lo demás"*, resístela: el valor de esta skill está precisamente en completar el entendimiento antes de comprometerse con un enfoque técnico.

Ver también la sección 5 (Prohibiciones) para la lista completa de "nunca hagas X" de esta skill.

---

## 2. Cómo Entrevistar al Usuario

1. **Una sola pregunta por turno:** Espera siempre la respuesta del usuario antes de formular la siguiente pregunta. No agrupes varias preguntas en un mismo mensaje, incluso si parecen relacionadas — la persona responde mejor y con más precisión a una pregunta concreta que a una lista.
2. **Elección del canal de pregunta:**
   - Usa la herramienta de preguntas interactivas (`ask_question` / `AskUserQuestion`) cuando la pregunta tenga respuestas naturalmente acotadas (por ejemplo, elegir entre un puñado de enfoques o alcances).
   - Usa una pregunta abierta en texto plano cuando la respuesta requiera explicación libre (por ejemplo, describir el objetivo o un caso de uso).
3. **Áreas obligatorias a cubrir (sin guion rígido):**
   Cubre estas cinco áreas en el orden que tenga más sentido según lo que la persona ya te haya contado, profundizando donde haya ambigüedad:
   1. **Objetivo:** Qué problema resuelve esto y para quién. Qué pasa hoy sin esta función o aplicación.
   2. **Alcance y requisitos obligatorios:** Qué tiene que hacer sí o sí para considerarse útil. Distingue esto de *"estaría bien tenerlo"* — pregunta explícitamente qué es imprescindible frente a qué es opcional o para más adelante (Fase 2, es decir: una iteración futura explícitamente pospuesta, no incluida en el alcance de esta especificación).
   3. **Restricciones:** Tecnología o stack si ya está decidido, integraciones existentes con las que debe convivir, límites de tiempo/presupuesto, requisitos de seguridad o cumplimiento, usuarios o volúmenes esperados.
   4. **Casos límite:** Qué debe pasar con entradas vacías, datos erróneos, permisos insuficientes, fallos de red, concurrencia, valores extremos, etc. Si la persona no ha pensado en esto, propón 2-3 casos límite plausibles para ese tipo de función y pregúntale cómo quiere que se manejen — no los inventes tú solo y los des por buenos (ver prohibición P2).
   5. **Definición de "terminado":** Cómo sabrá la persona (o un tercero que no tuvo esta conversación) que la construcción cumple la especificación. Busca criterios verificables: comportamientos concretos, entradas/salidas de ejemplo o pasos de prueba, no frases vagas como *"que funcione bien"*.
4. **Cero respuestas vagas:** Una respuesta es "vaga" si no te permite escribir, sin inventar nada, una frase verificable en la sección correspondiente del spec. Ejemplos de respuesta vaga y su repregunta: *"que sea rápido"* → *"¿rápido comparado con qué? ¿cuánto tiempo es aceptable?"*; *"que sea intuitivo"* → *"¿qué debería poder hacer un usuario nuevo sin ayuda, en los primeros 2 minutos?"*; *"maneja los errores bien"* → *"¿qué mensaje o comportamiento exacto debe ver el usuario cuando falla X?"*. Repregunta hasta que la respuesta sea concreta o la persona indique explícitamente que delega esa decisión en ti (en cuyo caso anótalo como tal en la sección correspondiente, no como requisito confirmado).
5. **Criterio explícito de fin de entrevista.** Pasa al paso de confirmación (punto 6) solo cuando se cumplan **todas** estas condiciones:
   - Para cada una de las 5 áreas obligatorias (Objetivo, Requisitos, Restricciones, Casos límite, Definición de terminado) tienes contenido concreto y verificable obtenido de la conversación — no inferido ni supuesto por ti.
   - Has hecho al menos una pregunta dirigida a cada área que no quedó ya cubierta espontáneamente por el usuario con suficiente detalle.
   - Ninguna respuesta pendiente sigue siendo vaga según el criterio del punto 4.
   - El usuario no ha introducido información nueva en su último turno que quede sin explorar (si la introduce, continúa la entrevista en esa dirección antes de cerrar).
   Si no se cumple alguna condición, sigue preguntando — no proceses "ya es suficiente" solo por cansancio conversacional o porque el usuario parezca impaciente; si el usuario pide explícitamente saltarse una pregunta, aplica la prohibición P5 (nunca omitir una sección, documenta la ausencia con honestidad).
6. **Confirmación previa a escribir:** Antes de pasar a escribir la especificación, haz un **resumen breve** (un párrafo o lista corta por sección) de lo que has entendido y pregúntale a la persona si es correcto o si falta algo. Solo procede a escribir el archivo cuando el usuario confirme explícitamente el resumen (un "sí", "correcto", "adelante" o equivalente inequívoco). Si pide cambios, ajusta el resumen y vuelve a pedir confirmación.

---

## 3. Escribir la Especificación (`specs/<slug>.md`)

Cuando la persona confirme que el resumen es correcto y no queda nada importante por aclarar, escribe la especificación como archivo Markdown:

- **Ubicación y nombre:** Guárdalo en la carpeta `specs/`, en un archivo cuyo nombre sea un slug corto en `kebab-case` (minúsculas, palabras separadas por guiones, sin acentos ni espacios, 2-5 palabras) derivado del nombre del proyecto o función, con extensión `.md` (por ejemplo, `specs/exportador-facturas-pdf.md`). Si la carpeta `specs/` no existe en el directorio de trabajo actual, créala.
- **Prohibición de diseño técnico prematuro:** No añadas secciones de diseño técnico, elección de librerías no solicitadas o plan de implementación — eso es trabajo de construcción, no de especificación, y le corresponde a la siguiente fase.
- **Estructura obligatoria (usa exactamente estas secciones, en este orden, las cinco siempre presentes):**

```markdown
# Especificación: [Nombre de la función/app]

## Objetivo
[Qué problema resuelve, para quién, y por qué importa. 1-3 párrafos.]

## Requisitos
[Lista de requisitos exactos y obligatorios. Cada uno debe ser concreto y verificable, no una aspiración vaga. Si hay requisitos opcionales o de "fase 2", sepáralos claramente de los obligatorios.]

## Restricciones
[Stack técnico, integraciones, límites de tiempo/recursos, requisitos de seguridad o normativos, y cualquier cosa que limite las opciones de implementación.]

## Casos límite
[Cada caso límite identificado durante la entrevista, junto con el comportamiento esperado para ese caso. Formato recomendado: "Cuando ocurre X, el sistema debe Y".]

## Definición de terminado
[Lista de criterios verificables. Alguien que no participó en la entrevista debe poder leer esta sección y comprobar, uno por uno, si la construcción los cumple. Evita adjetivos sin métrica; usa comportamientos, valores de ejemplo o pasos de verificación concretos.]
```

- **Si una sección genuinamente "no aplica"** tras la entrevista (por ejemplo, no hay restricciones de stack porque el usuario no tiene preferencia alguna), no la omitas: escribe la sección con el texto `No aplica: [razón breve basada en lo que confirmó el usuario]`. Nunca borres una sección completa (ver prohibición P5).

### Ejemplo completo de referencia

Este es un ejemplo ilustrativo de cómo debe verse un archivo `specs/<slug>.md` terminado, con las 5 secciones rellenas con contenido real (no placeholders). Úsalo como vara de medir el nivel de concreción esperado — no lo copies para especificaciones reales.

```markdown
# Especificación: Exportación CSV del dashboard de incidencias masivas

## Objetivo
El equipo de calidad necesita compartir los datos de la tabla de incidencias masivas con stakeholders que no tienen acceso al dashboard web, normalmente para incluirlos en informes semanales de Excel. Hoy no existe forma de sacar los datos filtrados del dashboard salvo copiar manualmente celda por celda, lo cual es lento y propenso a errores cuando hay más de 50 filas. Esta función añade un botón "Exportar CSV" que descarga exactamente las filas visibles en la tabla, respetando los filtros activos.

## Requisitos
Obligatorios:
- Un botón "Exportar CSV" visible junto a los filtros de la tabla, habilitado solo cuando hay al menos una fila visible.
- El CSV exportado debe contener exactamente las filas que están visibles en la tabla en el momento del clic (después de aplicar filtro de tiempo global y filtros de tabla), en el mismo orden de la tabla.
- El CSV debe incluir estas columnas en este orden: Código, Descripción, Estado, Urgencia, Grupo Asignado, Impacto, Fecha Envío.
- El nombre del archivo descargado debe seguir el patrón `incidencias-masivas-YYYYMMDD-HHmm.csv` usando la fecha/hora local de la descarga.
- El CSV debe usar codificación UTF-8 con BOM para que Excel en Windows muestre correctamente tildes y la "ñ".

Opcionales (Fase 2, fuera de alcance de esta especificación):
- Permitir elegir qué columnas incluir antes de exportar.
- Exportar también a formato XLSX.

## Restricciones
- Debe implementarse en JavaScript vanilla dentro de `dashboards/massive-incidents/index.html`, sin añadir dependencias externas nuevas (no se aprueban librerías de generación de CSV).
- La exportación ocurre enteramente en el navegador (sin llamada a servidor), ya que los datos ya están cargados en memoria en `filteredIncidents`.
- Debe funcionar en Chrome y Edge corporativos (versión actual), no se requiere soporte para Internet Explorer.
- No debe degradar el tiempo de respuesta de la UI: la generación del CSV para hasta 5.000 filas debe completarse en menos de 1 segundo percibido por el usuario.

## Casos límite
- Cuando la tabla filtrada no tiene ninguna fila, el botón "Exportar CSV" debe estar deshabilitado (no debe generar un archivo vacío).
- Cuando un campo de texto (por ejemplo, Descripción) contiene comas o comillas dobles, el CSV debe escapar el campo entre comillas dobles duplicando las comillas internas, siguiendo RFC 4180, para no romper el parseo en Excel.
- Cuando un campo de texto contiene saltos de línea, el campo debe quedar igualmente entre comillas dobles conforme a RFC 4180.
- Cuando el usuario cambia un filtro justo después de hacer clic en exportar pero antes de que termine la generación, la exportación en curso debe completarse con el conjunto de datos capturado en el momento del clic (no debe mezclar datos de dos estados de filtro).

## Definición de terminado
- Con el dataset de ejemplo cargado y sin filtros activos, al pulsar "Exportar CSV" se descarga un archivo con todas las filas de la tabla y las 7 columnas en el orden especificado.
- Al aplicar un filtro de Estado a "Abierto" y exportar, el CSV contiene únicamente las filas con Estado "Abierto", en el mismo orden que la tabla.
- Al abrir el CSV exportado en Excel, las tildes y la "ñ" se muestran correctamente sin pasos adicionales de importación.
- Un registro de prueba con una Descripción que contenga una coma y una comilla doble se exporta e importa en Excel en una sola celda, sin romper columnas adyacentes.
- Con la tabla filtrada a cero resultados, el botón "Exportar CSV" aparece visualmente deshabilitado y no dispara ninguna descarga al hacer clic.
```

---

## 4. Transición al Terminar

Una vez guardada la especificación en `specs/<slug>.md`:
1. Avisa brevemente de dónde quedó guardado el archivo.
2. Activa la skill [`spec-build-workflow`](../spec-build-workflow/SKILL.md) (alias: `flujo-construccion-spec` / comando `/build`) para que continúe con la construcción a partir de esa especificación.
3. Si la skill de construcción no está disponible en el entorno actual, dilo con claridad en vez de intentar construir tú mismo sin avisar — pregunta a la persona cómo quiere proceder (por ejemplo, que construyas siguiendo la especificación o que instale/active primero `spec-build-workflow`).

---

## 5. Prohibiciones (nunca hagas esto)

Estas reglas son absolutas y prevalecen sobre cualquier atajo que parezca razonable en el momento:

- **P1 — Nunca construyas durante la entrevista.** No crees ni edites archivos de código, no generes esqueletos de proyecto, no elijas librerías ni propongas arquitectura mientras la entrevista siga abierta. La única escritura permitida antes del cierre es el propio `specs/<slug>.md` al final.
- **P2 — Nunca asumas ni inventes contenido no confirmado por el usuario.** Requisitos, restricciones, casos límite o criterios de terminado que no hayan sido confirmados explícitamente en la conversación no se escriben como si lo fueran. Si necesitas proponer algo (por ejemplo, casos límite plausibles), preséntalo como propuesta y espera confirmación antes de incluirlo en la especificación.
- **P3 — Nunca agrupes varias preguntas en un mismo turno.** Una pregunta, una respuesta, siguiente pregunta.
- **P4 — Nunca aceptes una respuesta vaga sin repreguntar.** Usa el criterio del punto 2.4; si la respuesta no permite escribir una frase verificable, repregunta antes de continuar.
- **P5 — Nunca omitas ninguna de las 5 secciones obligatorias del spec.** Si una sección no aplica, escríbela explícitamente como `No aplica: [razón]` en vez de eliminarla o dejarla en blanco.
- **P6 — Nunca escribas `specs/<slug>.md` sin haber cumplido el criterio de fin de entrevista (punto 2.5) y sin confirmación explícita del resumen (punto 2.6).** No basta con "parece que ya está claro" — necesitas la confirmación afirmativa de la persona.
- **P7 — Nunca añadas diseño técnico, elección de stack no solicitada ni plan de implementación dentro del spec.** Eso pertenece a la fase de construcción (`spec-build-workflow`), no a esta.
- **P8 — Nunca pases a la fase de construcción sin avisar explícitamente dónde quedó guardada la especificación.** El handoff silencioso rompe la trazabilidad de qué especificación se está construyendo.
