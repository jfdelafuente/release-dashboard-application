---
name: incident-markdown-workflow
alias: flujo-informe-md
version: 1.1.0
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

Esta skill recoge las reglas técnicas de extracción, validación de fuentes, comandos de ejecución de `generate_report.py`, heurísticas de desambiguación y la estructura exacta de la plantilla Markdown para la **Etapa 1 (Revisión intermedia)** del pipeline de informes ejecutivos de incidencias.

---

## 1. Clasificación y Validación de Fuentes de Entrada

El flujo admite tres tipos de fuentes de entrada (`<fuente>`) y una ruta de salida opcional (`[ruta_salida_md]`):

| Caso | Tipo de Fuente | Criterio de Detección | Método de Procesamiento |
| :--- | :--- | :--- | :--- |
| **Rama A** | **URL de Confluence** | Comienza por `http://` o `https://` | Ejecución de `python ".agents/skills/incident-markdown-workflow/scripts/generate_report.py" --url "<URL>" --only-md --md-output "<RUTA_SALIDA>" --no-verify-ssl` |
| **Rama B** | **Archivo HTML local** | Ruta terminada en `.html` o `.htm` | Validación de existencia y tamaño `> 0 bytes` + `python ".agents/skills/incident-markdown-workflow/scripts/generate_report.py" --file "<RUTA_HTML>" --only-md --md-output "<RUTA_SALIDA>"` *(o Modo Híbrido IA si no hay Python)* |
| **Rama C** | **Notas Markdown locales** | Ruta terminada en `.md` | Validación de existencia y tamaño `> 0 bytes` + extracción e interpretación directa hacia la plantilla estándar (§3) |

### Regla estricta de validación para archivos locales (Ramas B y C)
1. Comprobar que el archivo existe físicamente en disco.
2. Comprobar que su tamaño es estrictamente **mayor que `0 bytes`**.
3. **Bloqueo inmediato ante archivo inexistente o vacío:** Si no existe o tiene `0 bytes`, detener la ejecución sin generar ningún archivo de salida y devolver literalmente:
   ```text
   Error: El archivo especificado no existe o está vacío: <ruta>
   ```

### Regla de ruta de salida por defecto
- Si el usuario especifica `[ruta_salida_md]`, utilizar esa ruta.
- Si no la especifica, utilizar `reports/informe_revisado.md` (o `reports/informe_<ID>.md` cuando el identificador de la incidencia o de la página sea conocido).
- Si el archivo de destino ya existe, **sobrescribirlo directamente**.

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

### B. Extracción desde Archivo HTML Exportado (Rama B)
```powershell
python ".agents/skills/incident-markdown-workflow/scripts/generate_report.py" --file "<RUTA_HTML>" --only-md --md-output "<RUTA_SALIDA>"
```
- Si en el HTML faltan secciones obligatorias (como `Impacto` o `Causa raíz`), el script inserta automáticamente los marcadores `[PENDIENTE DE COMPLETAR: ...]`.

### C. Modo Híbrido / Fallback IA (cuando Python no está disponible)
Si en el proyecto destino no hay intérprete de Python disponible o falta alguna librería y no puede instalarse en ese momento:
1. Para **archivos `.html` locales (Rama B)**: Lee el archivo HTML directamente con la herramienta de lectura de archivos del agente, ignora tablas de checklist QA (`CHECK | RESULTADO | OK/KO`), y extrae los metadatos, impacto, impacto de negocio, causa raíz (priorizando `Detalle causa raíz` > `Causa raíz / RCA` > `Origen / detonante`), solución (priorizando `Solución / Explicar la solución` > `Mitigación / Workaround`), tabla de puntos de acción y tabla/sección `Time Log` de cronología aplicando las reglas de la §3 y la plantilla de la §4.
2. De este modo, la skill funciona **en el 100% de los proyectos**, tanto con ejecución determinista por script Python (Opción 1) como con extracción directa por el agente (Opción 2).

---

## 3. Reglas de Extracción, Prioridad y Exclusión desde Notas Libres `.md` (Rama C)

Cuando la fuente es un archivo `.md` con apuntes, actas de war-room o notas no estructuradas, lee el contenido completo y extrae cada campo aplicando estas reglas de prioridad y exclusión **sin inventar datos**:

| Campo / Sección | Regla de Extracción, Prioridad y Exclusión | Valor si no consta en la fuente |
| :--- | :--- | :--- |
| **ID Incidencia / TT** | Priorizar siempre el identificador de **Incidencia Masiva / TT** (`INC...`, `TT <ID>`) sobre códigos de problema (`PROB-<ID>`). **Ignorar** los tickets secundarios listados bajo *"Tickets relacionados"*. | Dejar en `—` |
| **Título** | Título sintético y descriptivo del incidente (sin prefijos de plantilla redundantes). | Sintetizar a partir de las notas |
| **Inicio / Fin / Duración** | Fechas y horas en formato `DD/MM/YYYY HH:MM:SS` (o aproximado según conste) y duración calculada (`HH:MM`). | `—` en los datos no disponibles |
| **Impacto** | Resumen ejecutivo del impacto general en el servicio o clientes. Separar de este bloque cualquier desglose por área de negocio. | `[PENDIENTE DE COMPLETAR: Impacto no detectado en la fuente]` *(literal)* |
| **Impacto de Negocio** | Formatear siempre como lista de viñetas `- **<Área>**: <detalle>` (ej. `- **Ventas**: ...`, `- **Provisión**: ...`, `- **Atención al Cliente**: ...`, `- **Operaciones**: ...`), separando claramente el nombre del área y su descripción. | `—` |
| **Causa Raíz** | Aplicar jerarquía: **1)** Detalle técnico de causa raíz (*"Cuál ha sido la causa raíz"*, *"Explicación técnica detallada"*) > **2)** Causa raíz / RCA > **3)** Factor desencadenante / origen. **Exclusión:** Ignorar textos sobre monitorización/falta de detección y descartar marcas de checklist (`X`, `OK`, `KO`, `Sí`, `No`). | `[PENDIENTE DE COMPLETAR: Causa raíz no detectada en la fuente]` *(literal)* |
| **Solución** | Aplicar jerarquía: **1)** Solución / Solución técnica / Solución aplicada (*"Cómo se ha solucionado"*) > **2)** Mitigación / Workaround / Recuperación. **Exclusión:** Ignorar preguntas de tipo de cierre (*"¿Se resolvió mediante procedimiento documentado?"*, *"Solucionado con workaround: X"*, *"Autorrecuperación: X"*) y valores triviales (`X`, `OK`, `Sí`). | `—` |
| **Puntos de Acción** | Tabla Markdown con columnas `\| Pain Point \| Descripción \| Responsable \| Fecha Prevista \|`. Si hay referencias a tickets Jira (`PROB-XXXXX`), incluirlas limpias como `(PROB-XXXXX)` sin volcar metadatos internos de macros (`key,summary,type...`). | Al menos una fila con guiones (`\| — \| — \| — \| — \|`) |
| **Cronología** | Tabla Markdown con columnas `\| Hora \| Evento \|`, ordenada cronológicamente. Reconocer tanto horas con dos puntos (`HH:MM`, ej. `09:26`) como horas separadas por punto (`HH.MM`, ej. `08.00` o `15.46`). Ignorar líneas que solo contengan una fecha suelta. | Al menos una fila con guiones (`\| — \| — \|`) |

---

## 4. Plantilla Estándar Obligatoria del Archivo Markdown de Salida

El archivo generado debe respetar exactamente esta estructura de encabezados, metadatos y tablas:

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

---

## 5. Auditoría de Calidad Post-Extracción y Transición a Etapa 2 (PowerPoint)

### 5.1 Auditoría obligatoria del archivo Markdown generado
Antes de presentar el resumen al usuario (tanto en Ramas A/B como en Rama C), verifica que el archivo generado cumple estos criterios de calidad:
1. **Sin valores triviales en secciones descriptivas:** `Impacto`, `Causa Raíz` y `Solución` nunca deben contener únicamente marcadores de casilla (`X`, `OK`, `KO`, `Sí`, `No`).
2. **Sin basura de macros de Confluence/Jira:** Ningún párrafo ni celda de tabla debe contener cadenas residuales de parámetros de macros como `key,summary,type,updated,assignee,status` o `Jira Next`.
3. **Impacto de Negocio legible:** Si existen áreas de negocio afectadas, deben figurar como lista de viñetas `- **<Área>**: <detalle>` y no pegadas en un único párrafo corrido.

### 5.2 Comando hacia Etapa 2 (Renderizado PowerPoint)
Una vez generado y validado el archivo Markdown en la Etapa 1, el comando estándar para producir la presentación ejecutiva final es:

```powershell
python ".agents/skills/incident-markdown-workflow/scripts/generate_report.py" --from-md <RUTA_SALIDA> --output reports/informe_ejecutivo.pptx
```
*(Si se ejecuta dentro de `executive-summary-report`, basta con `python generate_report.py --from-md <RUTA_SALIDA> --output reports/informe_ejecutivo.pptx`).*
