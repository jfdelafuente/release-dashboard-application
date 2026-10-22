# Tasks: Catálogo y Dashboard de Agentes y Skills IA (011-agents-skills-catalog)

**Input**: Design documents from `specs/011-agents-skills-catalog/`
- Spec: [spec.md](spec.md)
- Plan: [plan.md](plan.md)
- Research: [research.md](research.md)
- Data Model: [data-model.md](data-model.md)
- Contracts: [contracts/](contracts/)
- Quickstart: [quickstart.md](quickstart.md)

**Prerequisites**: Python 3.10+ con `PyYAML`, biblioteca de agentes en `C:\Users\jose.delafuente\Claude\Projects\biblioteca-agentes`.

**Organization**: Tareas agrupadas por fases y por historias de usuario con criterios de verificación independientes.

---

## Phase 1: Setup & Foundational (Data Extractor & Schema Contract)

**Purpose**: Construir la infraestructura de extracción y generación del catálogo desacoplado en formato Envelope (`_metadata` + `data`).

- [x] T001 [P] Crear el script extractor `converters/cli/build_agents_catalog.py` para parsear el frontmatter YAML y directrices Markdown de agentes (`agents/*/*.md`) y skills (`.agents/skills/*/SKILL.md`)
- [x] T002 Implementar en `build_agents_catalog.py` la lógica de correlación bidireccional entre skills y agentes (`used_by_agents`), cálculo de KPIs (`total_agents`, `total_domains`, `total_skills`) y generación del archivo `data/output/agents_catalog.json` bajo el contrato Envelope
- [x] T003 [P] Crear la suite de pruebas unitarias en `converters/tests/unit/test_build_agents_catalog.py` validando la extracción, parsing seguro de YAML, resiliencia ante caracteres UTF-8/acentos y validez del schema JSON
- [x] T004 Implementar el endpoint `GET /api/agents-catalog` (con fallback de lectura directa de `data/output/agents_catalog.json`) en `serve_app.py`

**Checkpoint**: Extractor operativo, pruebas unitarias ejecutadas con éxito y catálogo `data/output/agents_catalog.json` generado y validado.

---

## Phase 2: User Story 1 - Catálogo General y Vista por Dominios (Priority: P1) 🎯 MVP

**Goal**: Disponer de la estructura base del dashboard en `dashboards/agents-catalog/` que cargue el catálogo y muestre las tarjetas de agentes agrupadas por dominio con métricas de cabecera.

**Independent Test**: Abrir `/dashboards/agents-catalog/index.html` en el navegador y verificar que cargan las 5 tarjetas de agentes agrupadas en sus 2 dominios (`brand-content` y `it-incidents`) junto con los 3 KPIs de cabecera.

- [x] T005 [US1] Crear el archivo HTML base `dashboards/agents-catalog/index.html` con estructura corporativa Orange: topbar root, hero header con KPIs globales, contenedor de toolbar y rejilla de catálogo
- [x] T006 [P] [US1] Crear la hoja de estilos `dashboards/agents-catalog/agents-catalog.css` consumiendo `tokens.css` y `shared.css`, definiendo la disposición de tarjetas, insignias semánticas de dominio, tipografía Arial y contrastes accesibles
- [x] T007 [US1] Implementar en `dashboards/agents-catalog/agents-catalog.js` la carga asíncrona de datos desde `/api/agents-catalog` con fallback automático a `/data/output/agents_catalog.json`, y el renderizado dinámico de tarjetas agrupadas por dominio

**Checkpoint**: User Story 1 (MVP) completamente operativa e independientemente verificable.

---

## Phase 3: User Story 2 - Búsqueda en Tiempo Real y Filtrado por Dominio / Skill (Priority: P2)

**Goal**: Permitir al usuario filtrar al instante los agentes mediante buscador textual y chips interactivos de Dominio y Skill.

**Independent Test**: Teclear "postmortem" en el buscador y verificar que solo permanecen visibles `incident-analyzer` e `incident-reporter`. Pulsar el chip `Contenido y Marca` y verificar que solo se muestra `orange-brand-generator`.

- [x] T008 [US2] Implementar en `agents-catalog.html` y `agents-catalog.css` la barra de herramientas interactiva (input de búsqueda con icono SVG, contador reactivo de resultados y barra de chips de filtro)
- [x] T009 [US2] Desarrollar en `dashboards/agents-catalog/agents-catalog.js` el motor de filtrado en tiempo real multi-criterio (búsqueda debounced por texto, filtro activo por chip de dominio y filtro por skill recomendada)

**Checkpoint**: Búsqueda instantánea y filtros combinables verificados en navegador.

---

## Phase 4: User Story 3 - Asistente de Despliegue y Copia de Comandos CLI (Priority: P3)

**Goal**: Incorporar un generador visual de comandos de despliegue con copia en 1 clic de la sintaxis exacta de `.\deploy-agents.cmd`.

**Independent Test**: Hacer clic en el botón de copia en la tarjeta de `incident-report-publisher`, comprobar que el texto en portapapeles es `.\deploy-agents.cmd "<TargetRepo>" -Agents "incident-report-publisher"` y que la interfaz muestra un toast corporativo de confirmación.

- [x] T010 [US3] Implementar en `agents-catalog.js` la lógica de formateo y copia de comandos según el contrato `deployment-command-contract.md` (`navigator.clipboard` con fallback a `document.execCommand`)
- [x] T011 [US3] Agregar feedback visual accesible en el botón de copia (estado temporal "✓ Copiado") y notificación flotante (toast) mediante integración con `ui-feedback.js`
- [x] T012 [US3] Diseñar modal/drawer de configuración de ruta destino (`TargetRepo`) que almacena la preferencia en `localStorage` para personalizar los comandos generados en futuras visitas

**Checkpoint**: Generador y copia de comandos CLI validado con la sintaxis de `deploy-agents.cmd`.

---

## Phase 5: User Story 4 - Vista Detallada de Agente e Inventario de Skills (Priority: P4)

**Goal**: Permitir abrir una ficha técnica completa de cada agente (instrucciones y reglas en Markdown) y consultar la pestaña dedicada al inventario de Skills con sus agentes asociados.

**Independent Test**: Hacer clic en "Ver Ficha Completa" de un agente para abrir el modal con el texto de sus instrucciones, o cambiar a la vista "Skills" y comprobar que aparecen las 6 habilidades y los agentes que las utilizan.

- [x] T013 [US4] Implementar el modal/drawer de detalle técnico de agente en `index.html` y `agents-catalog.js` con visualización de instrucciones, herramientas autorizadas y directrices operativas
- [x] T014 [US4] Crear la vista o pestaña alternativa "Inventario de Skills" en el dashboard, mostrando cada skill con su descripción oficial y lista interactiva de agentes que la emplean

**Checkpoint**: Vista detallada de directrices operativas e inventario de skills verificado.

---

## Phase 6: Integración Corporativa & Verificación Final

**Purpose**: Conectar el nuevo dashboard en el Portal Hub y en la navegación unificada, verificando la suite completa de pruebas.

- [x] T015 Actualizar `dashboards/assets/topbar.js` añadiendo el elemento `{ id: 'agents-catalog', label: 'Agentes IA', href: '/dashboards/agents-catalog/' }`
- [x] T016 Actualizar `dashboards/portal/index.html` añadiendo una nueva tarjeta destacada "Catálogo de Agentes IA" dentro de la parrilla de plataformas operativas
- [x] T017 Ejecutar la suite de pruebas unitarias `pytest converters/tests/unit/test_build_agents_catalog.py` y verificar que todos los tests pasen al 100%
- [x] T018 Ejecutar `python converters/cli/build_agents_catalog.py` para generar la versión definitiva de `data/output/agents_catalog.json` y comprobar paridad exacta con `deploy-agents.cmd -List`

