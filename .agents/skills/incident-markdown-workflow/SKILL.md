---
name: incident-markdown-workflow
alias: flujo-informe-md
version: 1.1.1
description: >-
  Define la especificación técnica, reglas de extracción por tipo de fuente
  (URL de Confluence, HTML exportado o notas libres en Markdown), heurísticas
  de prioridad y exclusión, marcadores obligatorios de campos faltantes y la
  plantilla estándar del Informe Ejecutivo de Incidencia en Markdown (Etapa 1
  previa al PowerPoint). Úsese siempre que se invoque el agente
  incident-markdown-generator o se estructure un borrador Markdown de
  postmortem/incidencia.
---

# Especificación y Flujo del Informe Ejecutivo de Incidencia en Markdown (`incident-markdown-workflow`)

**Propósito en una frase:** convertir una fuente de entrada (URL de Confluence, archivo HTML exportado o notas libres `.md`) en un único archivo Markdown con la estructura exacta de la §4 ("Etapa 1"), sin inventar datos, dejando los campos no disponibles marcados explícitamente, como paso previo a la generación del PowerPoint ejecutivo ("Etapa 2").

Esta skill recoge las reglas técnicas de extracción, validación de fuentes, comandos de ejecución de `generate_report.py`, heurísticas de desambiguación y la estructura exacta de la plantilla Markdown para la **Etapa 1 (Revisión intermedia)** del pipeline de informes ejecutivos de incidencias.

---

## 0. Proceso Paso a Paso (resumen obligatorio de ejecución)

Sigue siempre este orden; no saltes pasos ni los reordenes:

1. **Identifica el tipo de fuente** (`<fuente>`) usando la tabla de la §1. Si no coincide con ninguna de las tres ramas (A/B/C), detén la ejecución y devuelve literalmente: `Error: Tipo de fuente no reconocido. Debe ser una URL http(s), un archivo .html/.htm o un archivo .md.`
2. **Valida la fuente** según la regla estricta de la §1 (existencia y tamaño `> 0 bytes` para Ramas B y C; disponibilidad de red/credenciales para Rama A).
3. **Determina la ruta de salida** según la regla de la §1 (parámetro explícito o valor por defecto).
4. **Extrae los datos** aplicando el método de procesamiento de la rama correspondiente (§2 para A/B, incluido el Modo Híbrido si Python no está disponible; §3 para C).
5. **Vuelca los datos en la plantilla exacta de la §4**, respetando encabezados, orden de secciones y formato de tablas carácter por carácter.
6. **Ejecuta la auditoría de calidad obligatoria** (§6.1) sobre el archivo generado y corrige cualquier incumplimiento antes de continuar.
7. **Presenta al usuario un resumen breve** (no el archivo completo) con: ID de incidencia, título, ruta del archivo generado y una lista de los campos que quedaron marcados como `[PENDIENTE DE COMPLETAR: ...]` o `—`.
8. **Ofrece el comando de transición a Etapa 2** (§6.2) solo después de que la auditoría del paso 6 haya pasado sin incidencias.

Consulta la §7 ("Prohibiciones Explícitas") antes de entregar cualquier resultado: recoge los errores más frecuentes que invalidan el informe.

---

## 1. Clasificación y Validación de Fuentes de Entrada

El flujo admite tres tipos de fuentes de entrada (`<fuente>`) y una ruta de salida opcional (`[ruta_salida_md]`):

| Caso | Tipo de Fuente | Criterio de Detección | Método de Procesamiento |
| :--- | :--- | :--- | :--- |
| **Rama A** | **URL de Confluence** | Comienza por `http://` o `https://` | Ejecución de `python ".agents/skills/incident-markdown-workflow/scripts/generate_report.py" --url "<URL>" --only-md --md-output "<RUTA_SALIDA>" --no-verify-ssl` |
| **Rama B** | **Archivo HTML local** | Ruta terminada en `.html` o `.htm` | Validación de existencia y tamaño `> 0 bytes` + `python ".agents/skills/incident-markdown-workflow/scripts/generate_report.py" --file "<RUTA_HTML>" --only-md --md-output "<RUTA_SALIDA>"` *(o Modo Híbrido IA si no hay Python, §2.C)* |
| **Rama C** | **Notas Markdown locales** | Ruta terminada en `.md` | Validación de existencia y tamaño `> 0 bytes` + extracción e interpretación directa hacia la plantilla estándar (§3) |

### Fuente no reconocida o ambigua

- Si `<fuente>` no cumple ninguno de los tres criterios de detección (por ejemplo, una ruta sin extensión, un fragmento de texto pegado directamente, o una URL `ftp://`), **no intentes adivinar la rama**: detén la ejecución y devuelve el error del paso 1 de la §0.
- Si el usuario proporciona más de un origen a la vez (ej. una URL y un archivo local), pide o usa únicamente el que se indicó explícitamente como `<fuente>` en la invocación; nunca combines datos de dos fuentes distintas en un mismo informe.
- Rama A no tiene modo sin Python: si no hay intérprete de Python disponible y la fuente es una URL, detén la ejecución e informa que la Rama A requiere Python (el Modo Híbrido del §2.C solo cubre Rama B).

### Regla estricta de validación para archivos locales (Ramas B y C)

1. Comprobar que el archivo existe físicamente en disco.
2. Comprobar que su tamaño es estrictamente **mayor que `0 bytes`**.
3. **Bloqueo inmediato ante archivo inexistente o vacío:** Si no existe o tiene `0 bytes`, detener la ejecución sin generar ningún archivo de salida y devolver literalmente:
   ```text
   Error: El archivo especificado no existe o está vacío: <ruta>
   ```

### Regla de ruta de salida por defecto

- Si el usuario especifica `[ruta_salida_md]`, utilizar esa ruta exactamente (crear los directorios intermedios que falten).
- Si no la especifica, utilizar `reports/informe_revisado.md` (o `reports/informe_<ID>.md` cuando el identificador de la incidencia o de la página sea conocido antes de escribir el archivo).
- Si el archivo de destino ya existe, **sobrescribirlo directamente** sin pedir confirmación ni crear copias con sufijos (`_v2`, `_final`, etc.).

---

## 2. Ejecución Portable mediante `scripts/generate_report.py` + Modo Híbrido (Ramas A y B)

Esta skill empaqueta de forma autocontenida el motor completo de extracción y renderizado en `.agents/skills/incident-markdown-workflow/scripts/`:

- `scripts/generate_report.py` y paquete modular `scripts/src/incident_report/` (Dominio, Extractores heurísticos HTML/Confluence, Serializador/Parser Markdown y Generador PowerPoint).
- `scripts/requirements.txt`: Dependencias de Python (`beautifulsoup4`, `requests`, `python-dotenv`, `python-pptx`).
- `scripts/.env.example`: Plantilla de configuración de credenciales de Confluence (`CONFLUENCE_URL`, `CONFLUENCE_USER`, `CONFLUENCE_TOKEN`, `CONFLUENCE_VERIFY_SSL`).
- `scripts/assets/templates/`: Plantillas corporativas `.pptx` para la Etapa 2 (`--from-md`).

### Instalación rápida de dependencias (si no están en el entorno Python)

```powershell
pip install -r .agents/skills/incident-markdown-workflow/scripts/requirements.txt
```

### A. Extracción desde URL de Confluence (Rama A)

```powershell
python ".agents/skills/incident-markdown-workflow/scripts/generate_report.py" --url "<URL>" --only-md --md-output "<RUTA_SALIDA>" --no-verify-ssl
```

*(Si se ejecuta dentro del repositorio original `executive-summary-report`, también puede invocarse directamente `python generate_report.py ...`).*

- **Red y seguridad corporativa:** El flag `--no-verify-ssl` es obligatorio para operar en entornos corporativos con proxy e inspección SSL sin bloqueos de certificados.
- **Manejo de errores `401`/`403` o de red:** Notificar el error al usuario y recordarle verificar las variables de entorno en el archivo `.env` de la raíz del proyecto (puede copiarse desde `.agents/skills/incident-markdown-workflow/scripts/.env.example`):
  - `CONFLUENCE_URL` (o `CONFLUENCE_BASE_URL`): URL base de la instancia de Confluence.
  - `CONFLUENCE_USER` (o `CONFLUENCE_EMAIL`): correo del usuario para Atlassian Cloud.
  - `CONFLUENCE_TOKEN` (o `CONFLUENCE_API_TOKEN`): API Token en Cloud o PAT en Data Center.
  - `CONFLUENCE_VERIFY_SSL=false` (opcional en redes con proxy corporativo).
- Nunca imprimas el valor de `CONFLUENCE_TOKEN`/`CONFLUENCE_API_TOKEN` en la salida ni en el archivo Markdown generado, ni siquiera en mensajes de error de depuración.

### B. Extracción desde Archivo HTML Exportado (Rama B)

```powershell
python ".agents/skills/incident-markdown-workflow/scripts/generate_report.py" --file "<RUTA_HTML>" --only-md --md-output "<RUTA_SALIDA>"
```

- Si en el HTML faltan secciones obligatorias (como `Impacto` o `Causa raíz`), el script inserta automáticamente los marcadores `[PENDIENTE DE COMPLETAR: ...]`.

### C. Modo Híbrido / Fallback IA (cuando Python no está disponible, solo Rama B)

Si en el proyecto destino no hay intérprete de Python disponible o falta alguna librería y no puede instalarse en ese momento:

1. Para **archivos `.html` locales (Rama B)**: Lee el archivo HTML directamente con la herramienta de lectura de archivos del agente, ignora tablas de checklist QA (`CHECK | RESULTADO | OK/KO`), y extrae los metadatos, impacto, impacto de negocio, causa raíz (priorizando `Detalle causa raíz` > `Causa raíz / RCA` > `Origen / detonante`), solución (priorizando `Solución / Explicar la solución` > `Mitigación / Workaround`), tabla de puntos de acción y tabla/sección `Time Log` de cronología aplicando las reglas de la §3 y la plantilla de la §4.
2. De este modo, la skill funciona **en el 100% de los proyectos** para Ramas B y C, tanto con ejecución determinista por script Python (Opción 1) como con extracción directa por el agente (Opción 2). La Rama A siempre requiere Python (ver §1).

---

## 3. Reglas de Extracción, Prioridad y Exclusión desde Notas Libres `.md` (Rama C)

Cuando la fuente es un archivo `.md` con apuntes, actas de war-room (reunión de crisis en tiempo real durante el incidente) o notas no estructuradas, lee el contenido completo y extrae cada campo aplicando estas reglas de prioridad y exclusión **sin inventar datos**: nunca completes una fecha, nombre, cifra o causa que no esté escrita literalmente (o de forma inequívocamente derivable, como una resta de horas) en la fuente.

| Campo / Sección | Regla de Extracción, Prioridad y Exclusión | Valor si no consta en la fuente |
| :--- | :--- | :--- |
| **ID Incidencia / TT** | Priorizar siempre el identificador de **Incidencia Masiva / TT** (`INC...`, `TT <ID>`) sobre códigos de problema (`PROB-<ID>`). **Ignorar** los tickets secundarios listados bajo *"Tickets relacionados"*. | Dejar en `—` |
| **Título** | Título sintético y descriptivo del incidente (máx. 120 caracteres, sin prefijos de plantilla redundantes como "Incidencia:" o "RCA:", sin punto final). Debe describir el síntoma observado por el usuario, no la causa técnica. | Sintetizar a partir de las notas; si no hay suficiente contexto para sintetizarlo, usar `[PENDIENTE DE COMPLETAR: Título no detectado en la fuente]` |
| **Inicio / Fin / Duración** | Fechas y horas en formato `DD/MM/YYYY HH:MM:SS` (o aproximado según conste). **Duración**: calcular `HH:MM` como la diferencia exacta entre Fin e Inicio solo si ambos constan explícitamente; si falta uno de los dos, o la fuente ya indica una duración distinta de forma literal, usar el valor literal de la fuente en vez de recalcular. | `—` en los datos no disponibles (Inicio, Fin o Duración de forma independiente) |
| **Impacto** | Resumen ejecutivo (2-4 frases) del impacto general en el servicio o clientes, incluyendo cifras si constan (nº de clientes, nº de transacciones). Separar de este bloque cualquier desglose por área de negocio. | `[PENDIENTE DE COMPLETAR: Impacto no detectado en la fuente]` *(literal)* |
| **Impacto de Negocio** | Formatear siempre como lista de viñetas `- **<Área>**: <detalle>` (ej. `- **Ventas**: ...`, `- **Provisión**: ...`, `- **Atención al Cliente**: ...`, `- **Operaciones**: ...`), separando claramente el nombre del área y su descripción. Incluir también las áreas marcadas explícitamente como "no afectado" si así constan en la fuente — no se descartan, solo se resumen. | `—` |
| **Causa Raíz** | Aplicar jerarquía: **1)** Detalle técnico de causa raíz (*"Cuál ha sido la causa raíz"*, *"Explicación técnica detallada"*) > **2)** Causa raíz / RCA > **3)** Factor desencadenante / origen. **Exclusión:** Ignorar textos sobre monitorización/falta de detección y descartar marcas de checklist (`X`, `OK`, `KO`, `Sí`, `No`). Si dos fuentes del mismo nivel de prioridad se contradicen, usa la que aparece primero en el documento y no mezcles ambas en la misma frase. | `[PENDIENTE DE COMPLETAR: Causa raíz no detectada en la fuente]` *(literal)* |
| **Solución** | Aplicar jerarquía: **1)** Solución / Solución técnica / Solución aplicada (*"Cómo se ha solucionado"*) > **2)** Mitigación / Workaround / Recuperación. **Exclusión:** Ignorar preguntas de tipo de cierre (*"¿Se resolvió mediante procedimiento documentado?"*, *"Solucionado con workaround: X"*, *"Autorrecuperación: X"*) y valores triviales (`X`, `OK`, `Sí`). | `—` |
| **Puntos de Acción** | Tabla Markdown con columnas `\| Pain Point \| Descripción \| Responsable \| Fecha Prevista \|`. Si hay referencias a tickets Jira (`PROB-XXXXX`), incluirlas limpias como `(PROB-XXXXX)` al final de la celda `Descripción`, sin volcar metadatos internos de macros (`key,summary,type...`). Una fila por cada acción encontrada; no fusionar varias acciones en una sola fila. | Al menos una fila con guiones (`\| — \| — \| — \| — \|`) |
| **Cronología** | Tabla Markdown con columnas `\| Hora \| Evento \|`, ordenada cronológicamente. Reconocer tanto horas con dos puntos (`HH:MM`, ej. `09:26`) como horas separadas por punto (`HH.MM`, ej. `08.00` o `15.46`), pero **normalizar siempre la salida al formato `HH:MM`** independientemente del separador de origen. Ignorar líneas que solo contengan una fecha suelta sin evento asociado. | Al menos una fila con guiones (`\| — \| — \|`) |

---

## 4. Plantilla Estándar Obligatoria del Archivo Markdown de Salida

El archivo generado debe respetar **exactamente** esta estructura de encabezados, metadatos y tablas — mismo texto de encabezado, mismo orden de secciones, mismas columnas de tabla. No añadas secciones adicionales, no cambies el nivel de los encabezados (`#`/`##`) y no agregues comentarios o explicaciones dentro del archivo:

```markdown
# Informe Ejecutivo de Incidencia

## Metadatos
- **ID Incidencia / TT**: <ID>
- **Título**: <TITULO>
- **Inicio**: <INICIO>
- **Fin**: <FIN>
- **Duración**: <DURACION>

## Impacto
<IMPACTO>

## Impacto de Negocio
<IMPACTO_NEGOCIO>

## Causa Raíz
<CAUSA_RAIZ>

## Solución
<SOLUCION>

## Puntos de Acción
| Pain Point | Descripción | Responsable | Fecha Prevista |
|---|---|---|---|
| <Pain Point> | <Descripción> | <Responsable> | <Fecha> |

## Cronología
| Hora | Evento |
|---|---|
| <Hora> | <Evento> |
```

### Formato del archivo

- Codificación **UTF-8 sin BOM**, saltos de línea `LF`.
- El archivo debe terminar con una única línea en blanco final.
- Todos los valores de marcador literal (`[PENDIENTE DE COMPLETAR: ...]`, `—`) deben copiarse carácter por carácter como aparecen en la §3, sin traducir, abreviar ni reformular.

---

## 5. Ejemplo Completo Trabajado (Rama C)

El siguiente ejemplo es **ficticio** (no corresponde a ningún incidente real de Orange) y sirve únicamente para ilustrar el resultado esperado de principio a fin.

### 5.1 Entrada: `notas-warroom-ejemplo.md` (notas libres sin estructurar)

```markdown
Notas War Room - Incidencia Facturación (EJEMPLO FICTICIO)

Incidencia Masiva: INC000009999999
Tickets relacionados: PROB-000111 (no usar este como ID principal)

Inicio: 14/03/2026 09:15:00
Fin: 14/03/2026 11:45:00

Qué ha pasado: Los clientes no podían descargar su factura PDF desde el
portal de autoservicio ficticio. Aproximadamente 12.000 clientes afectados
durante la incidencia.

Impacto en negocio:
- Ventas: no afectado
- Atención al Cliente: incremento del 300% en llamadas al CAU durante la
  franja horaria
- Provisión: sin incidencias

Cuál ha sido la causa raíz: Un despliegue de la versión 4.2.1 del
microservicio de facturación introdujo un bug en el generador de PDF que
lanzaba una excepción no controlada al renderizar facturas con más de 2
páginas.

¿Se resolvió mediante procedimiento documentado?: No
Solucionado con workaround: X
Cómo se ha solucionado: Se hizo rollback a la versión 4.2.0 del
microservicio y se desplegó un hotfix 4.2.2 dos días después con el fix
definitivo.

Puntos de acción:
- Añadir test de regresión para facturas >2 páginas. Responsable: Equipo
  Facturación. Fecha: 28/03/2026 (PROB-000111)
- Mejorar alertado de excepciones no controladas en el servicio.
  Responsable: SRE. Fecha: 04/04/2026

Time Log:
09.15 Detección de incremento de errores 500 en el endpoint de descarga de factura
09.26 Apertura de incidencia masiva INC000009999999
09.40 Escalado a equipo de Facturación
10.05 Confirmada causa raíz: bug en generador PDF
10.20 Decisión de rollback a versión 4.2.0
10.50 Rollback completado
11.45 Incidencia cerrada, servicio restablecido
```

### 5.2 Salida esperada: `reports/informe_INC000009999999.md`

```markdown
# Informe Ejecutivo de Incidencia

## Metadatos
- **ID Incidencia / TT**: INC000009999999
- **Título**: Fallo en la generación de PDF de facturas en el portal de autoservicio ficticio
- **Inicio**: 14/03/2026 09:15:00
- **Fin**: 14/03/2026 11:45:00
- **Duración**: 02:30

## Impacto
Los clientes no pudieron descargar su factura en PDF desde el portal de autoservicio ficticio durante aproximadamente 2 horas y 30 minutos, con un impacto estimado de 12.000 clientes afectados.

## Impacto de Negocio
- **Ventas**: No afectado.
- **Atención al Cliente**: Incremento del 300% en llamadas al CAU durante la franja horaria de la incidencia.
- **Provisión**: Sin incidencias.

## Causa Raíz
Un despliegue de la versión 4.2.1 del microservicio de facturación introdujo un bug en el generador de PDF que lanzaba una excepción no controlada al renderizar facturas con más de 2 páginas.

## Solución
Se hizo rollback a la versión 4.2.0 del microservicio y se desplegó un hotfix 4.2.2 dos días después con el fix definitivo.

## Puntos de Acción
| Pain Point | Descripción | Responsable | Fecha Prevista |
|---|---|---|---|
| Regresión no cubierta en facturas largas | Añadir test de regresión para facturas con más de 2 páginas (PROB-000111) | Equipo Facturación | 28/03/2026 |
| Alertado insuficiente de excepciones | Mejorar alertado de excepciones no controladas en el servicio | SRE | 04/04/2026 |

## Cronología
| Hora | Evento |
|---|---|
| 09:15 | Detección de incremento de errores 500 en el endpoint de descarga de factura |
| 09:26 | Apertura de incidencia masiva INC000009999999 |
| 09:40 | Escalado a equipo de Facturación |
| 10:05 | Confirmada causa raíz: bug en generador PDF |
| 10:20 | Decisión de rollback a versión 4.2.0 |
| 10:50 | Rollback completado |
| 11:45 | Incidencia cerrada, servicio restablecido |
```

Nótese en este ejemplo: el ticket secundario `PROB-000111` no se usó como ID principal (regla de la §3); las respuestas triviales de checklist (`¿Se resolvió mediante procedimiento documentado?: No`, `Solucionado con workaround: X`) se excluyeron de `Solución`; las horas `09.15`-style se normalizaron a `09:15`-style; y la columna `Pain Point` se sintetizó en pocas palabras a partir de la descripción completa de cada acción.

### 5.3 Resumen que se presenta al usuario tras generar el archivo (paso 7 de la §0)

```text
Informe generado: reports/informe_INC000009999999.md
- ID: INC000009999999
- Título: Fallo en la generación de PDF de facturas en el portal de autoservicio ficticio
- Campos pendientes de completar: ninguno
```

---

## 6. Auditoría de Calidad Post-Extracción y Transición a Etapa 2 (PowerPoint)

### 6.1 Auditoría obligatoria del archivo Markdown generado

Antes de presentar el resumen al usuario (tanto en Ramas A/B como en Rama C), verifica que el archivo generado cumple estos criterios de calidad. Si alguno falla, corrige el archivo y repite la auditoría antes de continuar — nunca entregues un archivo que no la supere:

1. **Sin valores triviales en secciones descriptivas:** `Impacto`, `Causa Raíz` y `Solución` nunca deben contener únicamente marcadores de casilla (`X`, `OK`, `KO`, `Sí`, `No`).
2. **Sin basura de macros de Confluence/Jira:** Ningún párrafo ni celda de tabla debe contener cadenas residuales de parámetros de macros como `key,summary,type,updated,assignee,status` o `Jira Next`.
3. **Impacto de Negocio legible:** Si existen áreas de negocio afectadas, deben figurar como lista de viñetas `- **<Área>**: <detalle>` y no pegadas en un único párrafo corrido.
4. **Estructura exacta de la plantilla:** Los 7 encabezados de la §4 están presentes, en ese orden y con ese texto literal; no faltan ni sobran secciones.
5. **Sin marcadores inventados:** Todo campo con `[PENDIENTE DE COMPLETAR: ...]` corresponde realmente a un dato ausente en la fuente, no a pereza de extracción (si el dato está en la fuente aunque sea en otra sección o formato, debe extraerse).

### 6.2 Comando hacia Etapa 2 (Renderizado PowerPoint)

Una vez generado y validado el archivo Markdown en la Etapa 1 (auditoría de §6.1 superada), el comando estándar para producir la presentación ejecutiva final es:

```powershell
python ".agents/skills/incident-markdown-workflow/scripts/generate_report.py" --from-md <RUTA_SALIDA> --output reports/informe_ejecutivo.pptx
```

*(Si se ejecuta dentro de `executive-summary-report`, basta con `python generate_report.py --from-md <RUTA_SALIDA> --output reports/informe_ejecutivo.pptx`).*

No ofrezcas ni ejecutes este comando si la auditoría de §6.1 no ha pasado: primero corrige el Markdown.

---

## 7. Prohibiciones Explícitas ("Nunca hagas esto")

- **Nunca inventes datos.** Si un campo no consta en la fuente (fecha, cifra, nombre de responsable, causa), usa el marcador literal definido en la §3 (`[PENDIENTE DE COMPLETAR: ...]` o `—`); no lo rellenes con una suposición razonable ni con un valor genérico.
- **Nunca mezcles el ID principal con tickets secundarios.** No promuevas un `PROB-<ID>` a `ID Incidencia / TT` solo porque aparezca primero en el texto; sigue la prioridad de la §3.
- **Nunca copies literalmente respuestas de checklist** (`X`, `OK`, `KO`, `Sí`, `No`, o preguntas de cierre tipo "¿Se resolvió mediante procedimiento documentado?") en `Impacto`, `Causa Raíz` o `Solución`.
- **Nunca vuelques metadatos crudos de macros de Confluence/Jira** (parámetros como `key,summary,type,updated,assignee,status`, bloques `Jira Next`, JSON de macro) en ninguna sección del Markdown de salida.
- **Nunca añadas, elimines o reordenes secciones** respecto a la plantilla exacta de la §4, ni cambies el texto o nivel de un encabezado.
- **Nunca generes el PPTX (Etapa 2) sin haber superado antes la auditoría de la §6.1** sobre el Markdown de la Etapa 1.
- **Nunca imprimas credenciales** (`CONFLUENCE_TOKEN`, `CONFLUENCE_API_TOKEN`, contraseñas) en la salida, en mensajes de error ni en el archivo Markdown generado.
- **Nunca generes un archivo de salida si la validación de fuente falló** (archivo inexistente, vacío, o tipo de fuente no reconocido): devuelve el error correspondiente y detente.
- **Nunca combines contenido de dos fuentes distintas** (p. ej. una URL y un archivo local) en un mismo informe sin que el usuario lo haya pedido explícitamente.
