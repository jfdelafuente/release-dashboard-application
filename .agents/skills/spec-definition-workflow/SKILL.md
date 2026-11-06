---
name: spec-definition-workflow
alias: flujo-especificacion
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

---

## 2. Cómo Entrevistar al Usuario

1. **Una sola pregunta por turno:** Espera siempre la respuesta del usuario antes de formular la siguiente pregunta. No agrupes varias preguntas en un mismo mensaje, incluso si parecen relacionadas — la persona responde mejor y con más precisión a una pregunta concreta que a una lista.
2. **Elección del canal de pregunta:**
   - Usa la herramienta de preguntas interactivas (`ask_question` / `AskUserQuestion`) cuando la pregunta tenga respuestas naturalmente acotadas (por ejemplo, elegir entre un puñado de enfoques o alcances).
   - Usa una pregunta abierta en texto plano cuando la respuesta requiera explicación libre (por ejemplo, describir el objetivo o un caso de uso).
3. **Áreas obligatorias a cubrir (sin guion rígido):**
   Cubre estas cinco áreas en el orden que tenga más sentido según lo que la persona ya te haya contado, profundizando donde haya ambigüedad:
   1. **Objetivo:** Qué problema resuelve esto y para quién. Qué pasa hoy sin esta función o aplicación.
   2. **Alcance y requisitos obligatorios:** Qué tiene que hacer sí o sí para considerarse útil. Distingue esto de *"estaría bien tenerlo"* — pregunta explícitamente qué es imprescindible frente a qué es opcional o para más adelante (Fase 2).
   3. **Restricciones:** Tecnología o stack si ya está decidido, integraciones existentes con las que debe convivir, límites de tiempo/presupuesto, requisitos de seguridad o cumplimiento, usuarios o volúmenes esperados.
   4. **Casos límite:** Qué debe pasar con entradas vacías, datos erróneos, permisos insuficientes, fallos de red, concurrencia, valores extremos, etc. Si la persona no ha pensado en esto, propón 2-3 casos límite plausibles para ese tipo de función y pregúntale cómo quiere que se manejen — no los inventes tú solo y los des por buenos.
   5. **Definición de "terminado":** Cómo sabrá la persona (o un tercero que no tuvo esta conversación) que la construcción cumple la especificación. Busca criterios verificables: comportamientos concretos, entradas/salidas de ejemplo o pasos de prueba, no frases vagas como *"que funcione bien"*.
4. **Cero respuestas vagas:** Sigue preguntando hasta que puedas escribir cada una de estas cinco secciones con contenido concreto, no genérico. Si una respuesta es vaga (*"que sea rápido"*, *"que sea intuitivo"*), repregunta para convertirla en algo verificable (*"¿rápido comparado con qué? ¿cuánto tiempo es aceptable?"*).
5. **Confirmación previa a escribir:** Antes de pasar a escribir la especificación, haz un **resumen breve** de lo que has entendido y pregúntale a la persona si es correcto o si falta algo. Esto evita escribir una especificación basada en un malentendido.

---

## 3. Escribir la Especificación (`specs/<slug>.md`)

Cuando la persona confirme que el resumen es correcto y no queda nada importante por aclarar, escribe la especificación como archivo Markdown:

- **Ubicación y nombre:** Guárdalo en la carpeta `specs/`, en un archivo cuyo nombre sea un slug corto en `kebab-case` derivado del nombre del proyecto o función, con extensión `.md` (por ejemplo, `specs/exportador-facturas-pdf.md`). Si la carpeta `specs/` no existe en el directorio de trabajo actual, créala.
- **Prohibición de diseño técnico prematuro:** No añadas secciones de diseño técnico, elección de librerías no solicitadas o plan de implementación — eso es trabajo de construcción, no de especificación, y le corresponde a la siguiente fase.
- **Estructura obligatoria (usa exactamente estas secciones):**

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

---

## 4. Transición al Terminar

Una vez guardada la especificación en `specs/<slug>.md`:
1. Avisa brevemente de dónde quedó guardado el archivo.
2. Activa la skill [`spec-build-workflow`](../spec-build-workflow/SKILL.md) (alias: `flujo-construccion-spec` / comando `/build`) para que continúe con la construcción a partir de esa especificación.
3. Si la skill de construcción no está disponible en el entorno actual, dilo con claridad en vez de intentar construir tú mismo sin avisar — pregunta a la persona cómo quiere proceder (por ejemplo, que construyas siguiendo la especificación o que instale/active primero `spec-build-workflow`).

