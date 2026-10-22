# Implementation Plan: Catálogo y Dashboard de Agentes y Skills IA (011-agents-skills-catalog)

**Branch**: `011-agents-skills-catalog` | **Date**: 2026-10-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification en `specs/011-agents-skills-catalog/spec.md` y biblioteca externa en `C:\Users\jose.delafuente\Claude\Projects\biblioteca-agentes`.

---

## Summary

Implementar un nuevo dashboard corporativo e interactivo en `dashboards/agents-catalog/index.html` que visualice, categorice y permita explorar el catálogo de agentes IA y skills operativas de la organización (equivalente visual al comando `.\deploy-agents.cmd -List`). Para desacoplar el frontend y posibilitar la ejecución estática en el servidor VPS de producción (`10.132.26.96:8081`), se desarrolla un conversor en Python (`converters/cli/build_agents_catalog.py`) que extrae el frontmatter YAML y las directrices Markdown de la biblioteca, produciendo `data/output/agents_catalog.json` bajo el contrato Envelope (`_metadata` + `data`). La interfaz incluye KPIs ejecutivos, búsqueda y filtrado en tiempo real, generador/asistente de comandos de despliegue con copia en 1 clic, modal de instrucciones completas, inventario de skills e integración en el Portal Hub y navegación topbar.

---

## Technical Context

**Language/Version**: Python 3.10+ (extractor/conversor) + HTML5 / CSS3 / Vanilla JavaScript ES6+ (dashboard cliente).

**Primary Dependencies**: `PyYAML` (parseo seguro de frontmatter), `pathlib` (recorrido de sistema de ficheros), tokens corporativos Orange (`dashboards/assets/tokens.css`, `shared.css`, `topbar.js`).

**Storage**: Archivo JSON estático en disco (`data/output/agents_catalog.json`) consumido vía fetch por el cliente web.

**Testing**: `pytest` con tests unitarios en `converters/tests/unit/test_build_agents_catalog.py` (validación de frontmatter, tolerancias a fallos, estructura de envelope y cálculo de KPIs). Pruebas de integración frontend en navegador.

**Target Platform**: Linux VPS (producción `10.132.26.96:8081` bajo Nginx estático) y Windows (desarrollo local con PowerShell y `serve_app.py`).

**Performance Goals**:
- Carga y renderizado inicial del dashboard en < 200 ms.
- Filtrado reactivo en tiempo real en < 20 ms.
- Extracción y compilación de catálogo CLI en < 1 segundo.

**Constraints**:
- Respeto absoluto a la identidad de marca de **Orange** (`#FF7900`, tipografías y contrastes accesibles). Ningún uso de "MASORANGE".
- Zero-dependencies de servicios externos en producción.
- Compatibilidad estricta con la sintaxis de `deploy-agents.cmd`.

---

## Constitution Check

*GATE: Must pass before implementation.*

- **Principio I (Calidad de Código)**: ✅ Cumple. Separación nítida entre extracción de datos (`build_agents_catalog.py`), presentación (`agents-catalog.js`, `agents-catalog.css`) y componentes globales (`topbar.js`).
- **Principio II (Estándares de Testing)**: ✅ Cumple. Pruebas unitarias para el script extractor verificando agentes, dominios, skills asociadas y Envelope contract.
- **Principio III (Consistencia de UX)**: ✅ Cumple. Paleta de diseño corporativa Orange oficial, tipografías estándar, estados accesibles de foco y toasts de confirmación.
- **Principio IV (Rendimiento)**: ✅ Cumple. Modelo desacoplado estático que evita peticiones pesadas y proporciona respuestas en 0 ms en producción.
- **Principio V (Seguridad e Integridad)**: ✅ Cumple. Validación segura con `yaml.safe_load`, sin ejecución de código dinámico. Copia al portapapeles segura con sanitización de rutas.
- **Principio VI (Documentación y Mantenibilidad)**: ✅ Cumple. Documentación completa en `specs/011-agents-skills-catalog/` (`spec.md`, `plan.md`, `research.md`, `data-model.md`, `quickstart.md`, `contracts/`).

---

## Project Structure

### Documentation (this feature)

```text
specs/011-agents-skills-catalog/
├── spec.md                     # Especificación funcional
├── checklists/
│   └── requirements.md         # Checklist de requisitos validado
├── research.md                 # Decisiones de arquitectura y UX
├── data-model.md               # Entidades y esquema Envelope
├── quickstart.md               # Guía rápida de uso y pruebas
├── contracts/
│   ├── agents-catalog-schema.md
│   ├── deployment-command-contract.md
│   └── catalog-api-contract.md
└── plan.md                     # Este plan de implementación
```

### Source Code

```text
# Extractor y Conversor en Python
converters/
├── cli/
│   └── build_agents_catalog.py                 # Extractor CLI y generador de JSON Envelope
└── tests/
    └── unit/
        └── test_build_agents_catalog.py        # Suite de pruebas unitarias pytest

# Backend HTTP
serve_app.py                                    # Soporte para /api/agents-catalog y fallback /data/

# Dashboard y Frontend
dashboards/
├── agents-catalog/
│   ├── index.html                              # Estructura principal y layout corporativo
│   ├── agents-catalog.css                      # Estilos propios alineados con tokens Orange
│   └── agents-catalog.js                       # Lógica de renderizado, búsqueda, filtros y portapapeles
├── portal/
│   └── index.html                              # Nueva tarjeta destacada de Catálogo IA
└── assets/
    └── topbar.js                               # Inclusión de pestaña 'Agentes IA' en navegación global
```

---

## Complexity Tracking

| Componente | Nivel de Riesgo | Mitigación |
| :--- | :---: | :--- |
| **Acceso a ruta local en Windows** | Bajo | Parametrización en CLI (`--library-path`) y fallback gracioso a catálogo cacheado. |
| **Frontmatter multilínea y caracteres UTF-8** | Bajo | Uso de `PyYAML` con `encoding='utf-8'` y normalización de saltos de línea. |
| **Copia al portapapeles en navegadores restrictivos** | Bajo | Detección de `navigator.clipboard` con fallback clásico `document.execCommand('copy')`. |
| **Integración visual con Orange tokens** | Muy Bajo | Reutilización de `tokens.css` y `shared.css`. |

---

## Implementation Phases

### Phase 1: Extractor & Contrato de Datos (Python Backend)
- **T1.1**: Desarrollar `converters/cli/build_agents_catalog.py` para parsear `agents/*/*.md` y `.agents/skills/*/SKILL.md`.
- **T1.2**: Implementar el cálculo de KPIs agregados y la generación del envelope `data/output/agents_catalog.json`.
- **T1.3**: Crear la suite de pruebas unitarias en `converters/tests/unit/test_build_agents_catalog.py`.
- **T1.4**: Añadir el endpoint `GET /api/agents-catalog` en `serve_app.py`.

### Phase 2: Construcción del Dashboard Web (Frontend)
- **T2.1**: Crear `dashboards/agents-catalog/index.html` con estructura semántica (hero, KPIs, toolbar de búsqueda/chips, grid de agentes, vista de skills y modal/drawer de detalle).
- **T2.2**: Crear `dashboards/agents-catalog/agents-catalog.css` con estilos refinados Orange, badges de dominio/versión y microinteracciones de tarjetas.
- **T2.3**: Crear `dashboards/agents-catalog/agents-catalog.js`:
  - Carga de datos asíncrona (con fallback estático).
  - Renderizado dinámico de tarjetas agrupadas por dominio.
  - Motor de búsqueda reactivo y chips de filtro.
  - Asistente de despliegue con copia de comando al portapapeles y toasts de feedback.
  - Modal para visualización de fichas completas y vista alternativa de Skills.

### Phase 3: Integración Corporativa y Navegación
- **T3.1**: Actualizar `dashboards/assets/topbar.js` para registrar el ítem `Agentes IA` en la barra superior.
- **T3.2**: Actualizar `dashboards/portal/index.html` añadiendo la tarjeta de acceso directo al Catálogo IA en la sección correspondiente.

### Phase 4: Verificación, Pruebas y Cierre
- **T4.1**: Ejecutar la suite de tests unitarios de Python con `pytest`.
- **T4.2**: Probar la generación de `agents_catalog.json` y verificar paridad exacta con `deploy-agents.cmd -List`.
- **T4.3**: Verificar la interacción completa en navegador con `serve_app.py`.

