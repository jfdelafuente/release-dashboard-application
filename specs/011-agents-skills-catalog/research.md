# Research & Technical Decisions: Catálogo y Dashboard de Agentes y Skills IA (011-agents-skills-catalog)

**Feature**: `011-agents-skills-catalog`
**Date**: 2026-10-22

---

## 1. Estrategia de Extracción y Desacoplamiento (Standalone Architecture)

### Contexto
La organización mantiene la biblioteca canónica de agentes en la ruta local de desarrollo:
`C:\Users\jose.delafuente\Claude\Projects\biblioteca-agentes`
En el entorno de producción en el VPS (`10.132.26.96:8081`), la aplicación corre sobre Debian/Nginx sin acceso directo al disco local de la máquina del desarrollador.

### Decisión
Implementar un CLI conversor en Python (`converters/cli/build_agents_catalog.py`) que:
1. Inspecciona la biblioteca local (ruta configurable vía `--library-path` o variable `AGENTS_LIBRARY_PATH`, con valor por defecto la ruta canónica del usuario).
2. Lee y analiza recursivamente todos los ficheros de agentes (`agents/<domain>/*.md`) y de skills (`.agents/skills/*/SKILL.md`).
3. Compila y valida un dataset estructurado bajo el patrón de **Envelope Estándar** (`_metadata` + `data`).
4. Genera el archivo estático `data/output/agents_catalog.json` (versionable o transferible en despliegues al VPS).
5. Opcionalmente, expone un endpoint `/api/agents-catalog` en `serve_app.py` que lee `data/output/agents_catalog.json` o regenera los datos bajo demanda en local si se invoca con `?refresh=true`.

### Rationale
- **Zero-runtime-dependencies en producción**: El VPS sirve un fichero JSON estático y ligero (< 50 KB), garantizando un tiempo de carga inferior a 50 ms en producción.
- **Resiliencia**: Si la ruta externa no está disponible, el conversor emite un aviso controlado sin corromper el catálogo previamente generado.

---

## 2. Parseo de Frontmatter YAML y Contenido Markdown

### Decisión
Utilizar la librería estándar `PyYAML` (`yaml.safe_load`) combinada con división controlada por delimitadores `---` y fallback de expresiones regulares para máxima tolerancia a fallos.

### Mapeo de Campos de Agentes:
- Delimitador inicial de Frontmatter: `^---\s*$`
- Campos del Frontmatter:
  - `name`: Identificador kebab-case (ej. `incident-analyzer`).
  - `alias`: Alias corto en español o nombre alternativo (ej. `analizador-incidencias-it`, `estilo-orange`).
  - `domain`: Subcarpeta dentro de `agents/` (`brand-content`, `it-incidents`).
  - `version`: String semántico (ej. `3.4.0-OE`, `1.2.0`, `1.0.0`).
  - `description`: Texto explicativo, normalizando bloques multilínea (`>-` o `|`).
  - `recommended_skills`: Lista de identificadores de skills.
  - `tools`: Herramientas declaradas en el frontmatter (si existen).
- Cuerpo Markdown:
  - Instrucciones del sistema, reglas anti-alucinación, esquemas de entrada/salida y tablas de correspondencias.

### Mapeo de Campos de Skills:
- Carpeta: `.agents/skills/<skill-name>/SKILL.md`
- Campos del Frontmatter:
  - `name`: Nombre de la skill (ej. `it-severity-matrix`, `estilo-orange`).
  - `description`: Resumen del rol y disparador ("Úsese siempre que...").
- Contenido Markdown:
  - Directrices operativas, tablas de decisión, scripts y referencias.

### Relación Bidireccional:
El conversor mapea automáticamente para cada Skill la lista de agentes que la tienen en su `recommended_skills`, permitiendo al usuario ver en el catálogo: *"Skill utilizada por: incident-analyzer, incident-reporter"*.

---

## 3. Diseño Visual y Experiencia de Usuario (Orange Design System)

### Decisión
Crear una interfaz web dedicada en `dashboards/agents-catalog/index.html` con soporte nativo para los tokens corporativos de Orange (`dashboards/assets/tokens.css` y `shared.css`), complementada con `agents-catalog.css` y `agents-catalog.js`.

### Elementos de Diseño Clave:
1. **Firma Visual Única (Signature Element)**:
   - Panel de agentes en tarjetas con acentos en `#FF7900`, insignias semánticas de dominio con bordes discretos, y visor interactivo de instrucciones con renderizado Markdown legible y tipografía limpia.
2. **Hero & KPIs**:
   - Cabecera sobria y ejecutiva con métricas clave:
     - Total Agentes (5)
     - Dominios Activos (2: `brand-content`, `it-incidents`)
     - Total Skills (6)
     - Última sincronización con biblioteca.
3. **Barra de Herramientas Operativa**:
   - Buscador en tiempo real con filtrado instantáneo por texto (`nombre`, `alias`, `descripción`, `skills`).
   - Filtros por chips de Dominio (`Todos`, `Contenido y Marca`, `Incidencias IT`).
   - Selector de vistas: *Vista Catálogo de Agentes* vs *Vista Inventario de Skills*.
4. **Tarjeta de Agente (`Agent Card`)**:
   - Cabecera con Dominio y Versión destacada.
   - Nombre principal y Alias con tipografía monoespaciada suave.
   - Descripción clara y directa.
   - Lista interactiva de Badges de Skills recomendadas (al hacer clic filtra por esa skill).
   - Acciones principales:
     - 📋 Botón "Copiar Comando de Despliegue".
     - 👁️ Botón "Ver Ficha Completa" (abre Drawer / Modal con prompt completo y directrices).

---

## 4. Generador de Comandos de Despliegue (`deploy-agents.cmd`)

### Sintaxis Analizada en `biblioteca-agentes`:
1. **Despliegue de un agente individual**:
   ```cmd
   .\deploy-agents.cmd "<TargetRepo>" -Agents "<agent-name>"
   ```
2. **Despliegue por Dominio completo**:
   ```cmd
   .\deploy-agents.cmd "<TargetRepo>" -Domain "<domain-name>"
   ```
3. **Despliegue múltiple por lotes**:
   ```cmd
   .\deploy-agents.cmd "<TargetRepo>" -Agents "agent1,agent2"
   ```
4. **Simulación sin cambios**:
   ```cmd
   .\deploy-agents.cmd "<TargetRepo>" -Agents "<agent-name>" -WhatIf
   ```

### Decisión de UX:
- En cada tarjeta de agente habrá un botón rápido "Copiar comando", que copia al portapapeles:
  `.\deploy-agents.cmd "<RutaDestino>" -Agents "<nombre-agente>"`
- Un modal/asistente de despliegue configurable permitirá al usuario especificar su ruta de proyecto local (ej. `C:\Users\jose.delafuente\proyectos\release-dashboard-application` o `..\mi-proyecto`) y recordar dicha ruta en `localStorage` para que todos los comandos copiados salgan con su ruta ya rellenada.

---

## 5. Integración con el Portal Hub y Navegación

### Decisión
1. **Portal Hub (`dashboards/portal/index.html`)**:
   - Crear una nueva sección destacada: **"Inteligencia Artificial y Automatización"** o integrar una tarjeta dedicada en la parrilla operativa.
   - Título: **Catálogo de Agentes IA**.
   - Subtítulo: *Biblioteca de agentes especializados y skills para operaciones*.
   - Descripción: *Inventario de agentes declarativos para soporte a incidencias IT, postmortems, reportes y generación de contenido Orange con generador de comandos de despliegue.*
   - Tag: `Catálogo IA · 5 Agentes`.
2. **Topbar Global (`dashboards/assets/topbar.js`)**:
   - Agregar el elemento al array `NAV_ITEMS`:
     ```javascript
     { id: 'agents-catalog', label: 'Agentes IA', href: '/dashboards/agents-catalog/' }
     ```
   - Asegura navegación directa desde cualquiera de los otros dashboards del ecosistema.

