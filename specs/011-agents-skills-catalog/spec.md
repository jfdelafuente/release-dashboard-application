# Feature Specification: Catálogo y Dashboard de Agentes y Skills IA (011-agents-skills-catalog)

**Feature Branch**: `011-agents-skills-catalog`

**Created**: 2026-10-22

**Status**: Draft

**Input**: User description: "crear un nuevo dashboard que muestre la informacion de agentes/skill que tiene la biblioteca ubicada en C:\Users\jose.delafuente\Claude\Projects\biblioteca-agentes y que puede mostrarse con el comando ./deploy-agents.cmd -List"

---

## 🧭 Contexto y Origen de Datos

La organización cuenta con un repositorio central de agentes de Inteligencia Artificial ubicado en:
`C:\Users\jose.delafuente\Claude\Projects\biblioteca-agentes`

Dicha biblioteca contiene:
1. **Agentes declarativos en Markdown con frontmatter YAML**:
   - Ubicados en `agents/<dominio>/<nombre-agente>.md`.
   - Propiedades: `name`, `alias`, `description`, `domain`, `version`, `recommended_skills`, herramientas, reglas anti-alucinación e instrucciones operativas.
   - Dominios actuales:
     - `brand-content`: `orange-brand-generator` (v3.4.0-OE).
     - `it-incidents`: `incident-analyzer` (v1.2.0), `incident-describer` (v1.0.0), `incident-report-publisher` (v1.0.0), `incident-reporter` (v1.0.0).
2. **Skills y herramientas operativas**:
   - Ubicadas en `.agents/skills/<nombre-skill>/SKILL.md`.
   - Incluyen: `agent-deployer`, `agent-registrar`, `estilo-orange`, `it-severity-matrix`, `postmortem-pir-workflow`, `publicar-informe-incidencias`.
3. **Mecanismo CLI de listado**:
   - El script `.\deploy-agents.cmd -List` (orquestado por `.agents/skills/agent-deployer/scripts/deploy_agents.ps1`) parsea el frontmatter YAML y muestra en consola el catálogo con nombre, versión, alias, dominio, descripción y skills requeridas.

El objetivo de esta feature es dotar a la plataforma **Release Dashboard Application** de un nuevo dashboard visual, interactivo, alineado con la identidad corporativa Orange y accesible desde el Portal Hub, para consultar, buscar, explorar y desplegar rápidamente cualquier agente o skill del catálogo.

---

## 💡 Clarificaciones y Decisiones de Diseño

### Q1: Modelo de Ingesta y Compatibilidad VPS (Standalone Runtime)
- **Decisión**: **Arquitectura híbrida con contrato Envelope JSON (`_metadata` + `data`)**.
- **Detalle**:
  - Se creará un script de extracción y catálogo en Python (`converters/cli/build_agents_catalog.py` y/o endpoint `/api/agents-catalog` en `serve_app.py`).
  - El script lee la biblioteca (usando la ruta local configurada en `.env` o argumento `--library-path`), parsea los ficheros `.md` de agentes y skills y genera el fichero `data/output/agents_catalog.json`.
  - El formato de salida respeta el contrato estándar del proyecto:
    ```json
    {
      "_metadata": {
        "type": "agents_catalog",
        "generated_at": "2026-10-22T16:00:00Z",
        "library_path": "C:\\Users\\jose.delafuente\\Claude\\Projects\\biblioteca-agentes",
        "kpis": {
          "total_agents": 5,
          "total_domains": 2,
          "total_skills": 6
        }
      },
      "data": {
        "agents": [ ... ],
        "skills": [ ... ],
        "domains": [ ... ]
      }
    }
    ```
  - De este modo, en producción en el VPS (`10.132.26.96:8081`), el dashboard funciona como cliente estático desacoplado leyendo `data/output/agents_catalog.json` sin requerir acceso al disco local de la máquina de desarrollo.

### Q2: Alcance de Interactividad y Despliegue de Agentes
- **Decisión**: **Generador visual y copia con 1 clic de comandos de despliegue (`deploy-agents.cmd`)**.
- **Detalle**:
  - En la interfaz del dashboard, cada agente dispondrá de una acción "Copiar comando de despliegue" con sintaxis preconfigurada:
    `.\deploy-agents.cmd "<TargetRepo>" -Agents "<nombre-agente>"`
  - Existirá un asistente de despliegue por lotes que permite seleccionar múltiples agentes o un dominio completo (ej. `-Domain "it-incidents"`) y copiar el comando resultante.
  - Opcionalmente en local (`serve_app.py`), se podrá ofrecer una acción asistida si el entorno cuenta con permisos de ejecución.

### Q3: Ubicación del Dashboard y Navegación
- **Decisión**: **Dashboard independiente en `dashboards/agents-catalog/index.html` integrado en el Portal Hub**.
- **Detalle**:
  - Se añade como nueva tarjeta de acceso en el Portal Hub (`dashboards/portal/index.html`).
  - Se incorpora a la barra de navegación superior corporativa (`dashboards/assets/components/topbar.js`).
  - Aplica la paleta corporativa Orange y los tokens de diseño vigentes (`tokens.css`).

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Catálogo General y Vista por Dominios (Priority: P1) 🎯 MVP

Como usuario, responsable de proyectos o gestor de incidencias de Orange, quiero acceder al nuevo dashboard de Agentes y Skills para consultar el inventario visual de agentes IA clasificados por dominio, conociendo de un vistazo su versión, alias, descripción funcional y skills recomendadas.

**Why this priority**: Constituye el núcleo de valor imprescindible (MVP) para dar visibilidad centralizada a la biblioteca de agentes.

**Independent Test**: Abrir `/dashboards/agents-catalog/index.html`, verificar que cargan las tarjetas de agentes agrupadas por dominio (`brand-content`, `it-incidents`), mostrando nombre, versión, alias, skills y descripción equivalente a `.\deploy-agents.cmd -List`.

**Acceptance Scenarios**:
1. **Given** el catálogo de agentes generado en `data/output/agents_catalog.json`, **When** el usuario accede al dashboard, **Then** visualiza las tarjetas de agentes con sus etiquetas de dominio, alias, versión y lista de skills asociadas.
2. **Given** el panel de KPIs en la cabecera, **When** el dashboard carga, **Then** muestra métricas globales exactas (total de agentes, dominios activos, total de skills).

---

### User Story 2 - Búsqueda en Tiempo Real y Filtrado por Dominio / Skill (Priority: P2)

Como desarrollador o usuario de la biblioteca, quiero filtrar los agentes escribiendo palabras clave en una barra de búsqueda rápida o seleccionando chips de dominio y skill, para localizar de inmediato el agente adecuado para mi tarea.

**Why this priority**: Facilita la navegación rápida a medida que la biblioteca crezca con nuevos agentes y especialidades.

**Independent Test**: Escribir términos como "remedy", "postmortem", "pptx" o pulsar el chip de dominio `brand-content`, comprobando que la vista se filtra instantáneamente sin recargar la página.

**Acceptance Scenarios**:
1. **Given** el catálogo completo desplegado, **When** el usuario teclea "postmortem" en el buscador, **Then** solo se muestran los agentes que contengan esa palabra en su nombre, alias, skills o descripción (`incident-analyzer`, `incident-reporter`).
2. **Given** el selector de dominios, **When** el usuario selecciona `brand-content`, **Then** solo se muestra `orange-brand-generator`.

---

### User Story 3 - Asistente de Despliegue y Copia de Comandos CLI (Priority: P3)

Como desarrollador que desea incorporar agentes en su propio repositorio o proyecto, quiero disponer de un generador visual de comandos de despliegue donde indicar la ruta de mi repositorio destino y copiar el comando de `deploy-agents.cmd` listo para pegar en mi terminal.

**Why this priority**: Elimina la fricción manual de recordar la sintaxis y parámetros de `deploy-agents.cmd`.

**Independent Test**: Hacer clic en "Desplegar Agente" en la tarjeta de `incident-report-publisher`, ingresar o seleccionar una ruta de destino y hacer clic en "Copiar Comando", verificando que en el portapapeles queda `.\deploy-agents.cmd "..." -Agents "incident-report-publisher"`.

**Acceptance Scenarios**:
1. **Given** la tarjeta de un agente individual, **When** el usuario hace clic en el botón de copia rápida de despliegue, **Then** el sistema copia el comando al portapapeles y muestra una notificación flotante de confirmación.
2. **Given** el selector múltiple de agentes, **When** el usuario marca varios agentes y selecciona "Copiar comando por lotes", **Then** genera la instrucción combinada con la lista separada por comas.

---

### User Story 4 - Vista Detallada de Agente e Inventario de Skills (Priority: P4)

Como usuario avanzado, quiero abrir un modal o panel lateral para ver las directrices operativas completas de un agente (anti-alucinación, reglas de negocio, esquemas JSON vinculados) o consultar la pestaña dedicada al inventario de Skills para entender qué hace cada una (`estilo-orange`, `it-severity-matrix`, etc.).

**Why this priority**: Proporciona documentación técnica profunda sin salir de la plataforma.

**Independent Test**: Hacer clic en "Ver Ficha Completa" de un agente para abrir el modal con el contenido íntegro de su prompt e instrucciones, o cambiar a la pestaña "Skills" para revisar todas las habilidades disponibles.

**Acceptance Scenarios**:
1. **Given** una tarjeta de agente, **When** se pulsa "Ver detalles", **Then** se abre un modal con el desglose de instrucciones, requisitos de formato, herramientas requeridas y esquemas asociados.
2. **Given** la sección "Skills", **When** el usuario navega a ella, **Then** visualiza cada skill con su descripción oficial y qué agentes la utilizan.

---

## ⚡ Edge Cases

- **Biblioteca inaccesible o ruta no configurada**: Si el script conversor no encuentra la ruta local de la biblioteca, el dashboard debe cargar con gracia la última versión cacheada en `data/output/agents_catalog.json` indicando la fecha de la última extracción.
- **Agente con descripción multilínea en YAML**: El parser debe manejar adecuadamente bloques `>-`, `|` y texto entrecomillado preservando la legibilidad sin romper caracteres.
- **Caracteres UTF-8 y acentos en español**: Todos los textos, descripciones y alias con acentos (`gestión`, `análisis`, `catálogo`) deben visualizarse con codificación impecable.
- **Biblioteca vacía o sin agentes**: Si el JSON contiene un catálogo vacío, se debe mostrar un estado vacío informativo (*Empty State*) con indicaciones claras.

---

## 📋 Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE contar con un script conversor Python (`converters/cli/build_agents_catalog.py`) que parsee los ficheros Markdown de agentes (`agents/*/*.md`) y skills (`.agents/skills/*/SKILL.md`) en la biblioteca.
- **FR-002**: El script conversor DEBE generar el archivo `data/output/agents_catalog.json` siguiendo el formato estándar de *Envelope* con `_metadata` (KPIs, ruta de origen, fecha de generación) y `data` (agentes, skills, dominios).
- **FR-003**: El sistema DEBE proveer un nuevo dashboard web estático en `dashboards/agents-catalog/index.html` que cargue y renderice automáticamente los datos del catálogo.
- **FR-004**: El dashboard DEBE agrupar visualmente los agentes por su **Dominio** funcional (`brand-content`, `it-incidents`, etc.), indicando el número de agentes por grupo.
- **FR-005**: Cada tarjeta de agente DEBE mostrar: Nombre, Alias, Versión, Descripción resumida, Badges de skills recomendadas y ruta de fichero.
- **FR-006**: El dashboard DEBE incluir una cabecera con KPIs globales: Total de Agentes, Total de Dominios, Total de Skills y fecha de actualización.
- **FR-007**: El dashboard DEBE ofrecer un campo de búsqueda en tiempo real que filtre por nombre, alias, descripción o skill.
- **FR-008**: El dashboard DEBE permitir el filtrado mediante selectores/chips interactivos por Dominio y por Skill.
- **FR-009**: Cada tarjeta de agente DEBE incluir un botón de acción rápida para copiar al portapapeles el comando de despliegue `.\deploy-agents.cmd "<TargetRepo>" -Agents "<name>"`.
- **FR-010**: El dashboard DEBE contar con un modal o vista detallada para inspeccionar el contenido completo del agente, sus directrices de uso y sus esquemas asociados.
- **FR-011**: El dashboard DEBE incluir una sección o vista dedicada al inventario de **Skills**, explicando su propósito y qué agentes las requieren.
- **FR-012**: El dashboard DEBE integrarse estéticamente con el sistema de diseño corporativo Orange (`tokens.css`, `topbar.js`) y enlazarse desde el Portal Hub (`dashboards/portal/index.html`).

---

### Key Entities

- **`Agent`**:
  - `name`: Identificador único en formato kebab-case (ej. `incident-analyzer`).
  - `alias`: Nombre corto o identificador alternativo en español (ej. `analizador-incidencias-it`).
  - `version`: Versión semántica del agente (ej. `v1.2.0`).
  - `domain`: Categoría temática (`it-incidents`, `brand-content`, etc.).
  - `description`: Resumen del propósito y capacidades del agente.
  - `recommended_skills`: Lista de identificadores de skills necesarias.
  - `file_path`: Ruta relativa dentro de la biblioteca.
  - `instructions_markdown`: Contenido completo de las directrices e instrucciones operativas.
- **`Skill`**:
  - `name`: Identificador de la skill (ej. `it-severity-matrix`).
  - `description`: Descripción funcional y casos de uso.
  - `file_path`: Ruta del fichero `SKILL.md`.
  - `associated_agents`: Lista de agentes que referencian esta skill.
- **`Domain`**:
  - `id`: Identificador del dominio (ej. `it-incidents`).
  - `label`: Etiqueta descriptiva para visualización.
  - `agent_count`: Cantidad de agentes agrupados.
- **`CatalogEnvelope`**:
  - `_metadata`: Fecha de generación, ruta del repositorio fuente, versión del esquema y KPIs calculados.
  - `data`: Colecciones de `agents`, `skills` y `domains`.

---

## 🎯 Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El dashboard carga y renderiza el catálogo completo de 5 agentes y 6 skills en menos de 500 ms tras abrir la página.
- **SC-002**: La búsqueda y filtrado en tiempo real actualizan la vista en menos de 50 ms por pulsación de tecla.
- **SC-003**: El comando de despliegue copiado al portapapeles coincide al 100% con la sintaxis esperada por `deploy-agents.cmd`.
- **SC-004**: Los datos de agentes, alias, versiones y skills coinciden exactamente con la salida de `.\deploy-agents.cmd -List`.
- **SC-005**: El diseño cumple al 100% las directrices visuales oficiales de Orange (paleta de colores, tipografías y contrastes accesibles).

---

## 📌 Assumptions

1. La biblioteca ubicada en `C:\Users\jose.delafuente\Claude\Projects\biblioteca-agentes` mantiene la estructura canónica de frontmatter YAML en sus ficheros de agentes y skills.
2. Para el entorno de producción en el VPS (`10.132.26.96:8081`), la información se empaqueta estáticamente en `data/output/agents_catalog.json`, garantizando autonomía y zero-dependencies remotas.
3. El comando `deploy-agents.cmd` es ejecutado por el usuario en su estación de trabajo local apuntando a la ruta de su proyecto destino.
4. El servidor local `serve_app.py` expondrá una ruta o comando para regenerar el catálogo bajo demanda cuando se añadan nuevos agentes a la biblioteca.

