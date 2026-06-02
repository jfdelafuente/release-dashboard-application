# 📚 Índice de Documentación CI/CD

Guía de navegación para toda la documentación del sistema de CI/CD.

---

## 🚀 Empieza Aquí

### Para Nuevos Miembros
👉 **[ONBOARDING.md](ONBOARDING.md)** (15 minutos)
- Setup rápido
- Workflow típico
- Errores comunes
- Checklist antes de push

---

## 📖 Documentación Completa

### 1. **[CI-CD-GUIDE.md](CI-CD-GUIDE.md)** - Guía Completa ⭐
**Para:** Entender cómo funcionan todos los workflows
**Contiene:**
- Descripción de cada workflow (converters-ci, dashboards-ci, integration, deploy)
- Path filtering explicado
- Tests y coverage
- Proceso de deployment paso a paso
- Troubleshooting detallado
- Estructura de directorios

**Tiempo de lectura:** ~30 minutos
**Cuando leer:** Antes de trabajar en cambios importantes

---

### 2. **[CI-CD-QUICKREF.md](CI-CD-QUICKREF.md)** - Referencia Rápida
**Para:** Búsquedas rápidas mientras trabajas
**Contiene:**
- Tabla de workflows
- Ejemplos de cambios (converters, dashboards, ambos)
- Comandos útiles
- Errores comunes y soluciones
- Cheat sheet de comandos

**Tiempo de lectura:** ~10 minutos (consulta según necesites)
**Cuando consultar:** Mientras haces cambios, necesitas un comando, o tienes error

---

### 3. **[CI-CD-ARCHITECTURE.md](CI-CD-ARCHITECTURE.md)** - Arquitectura y Diagramas
**Para:** Entender visualmente cómo todo se conecta
**Contiene:**
- 11 diagramas de flujo y arquitectura
- Flujo general de cambios
- Arquitectura de workflows
- Path filtering logic
- Dependencias entre workflows
- Deployment flow
- Data flow: CSV → JSON → Dashboard
- Status checks en PR
- Timelines
- Decision trees

**Tiempo de lectura:** ~15 minutos
**Cuando leer:** Si eres visual o necesitas entender interacciones complejas

---

### 4. **[ONBOARDING.md](ONBOARDING.md)** - Para Nuevos Miembros
**Para:** Integración rápida al equipo
**Contiene:**
- Lo más importante (resumen)
- Setup rápido (5 minutos)
- Workflow típico
- Errores comunes y soluciones
- Conceptos clave explicados
- Checklist antes de push

**Tiempo de lectura:** ~15 minutos
**Cuando leer:** Primer día en el equipo

---

## 🎯 Guías por Rol

### 👨‍💻 Desarrollador (converters)
1. Lee [ONBOARDING.md](ONBOARDING.md) - 15 min
2. Consulta [CI-CD-QUICKREF.md](CI-CD-QUICKREF.md) mientras trabajas - as needed
3. Lee [CI-CD-GUIDE.md](CI-CD-GUIDE.md) → sección "Tests y Coverage" - 10 min
4. Referencia: `cd converters && pytest --cov=src`

### 🎨 Desarrollador (dashboards)
1. Lee [ONBOARDING.md](ONBOARDING.md) - 15 min
2. Consulta [CI-CD-QUICKREF.md](CI-CD-QUICKREF.md) para errores - as needed
3. Lee [CI-CD-GUIDE.md](CI-CD-GUIDE.md) → sección "Validaciones en dashboards-ci.yml" - 5 min
4. Referencia: navega a `dashboards/` en navegador

### 🚀 DevOps / Release Manager
1. Lee [CI-CD-GUIDE.md](CI-CD-GUIDE.md) - 30 min (completo)
2. Lee [CI-CD-ARCHITECTURE.md](CI-CD-ARCHITECTURE.md) - 15 min
3. Lee [CI-CD-GUIDE.md](CI-CD-GUIDE.md) → sección "Deployment Selectivo" - 10 min
4. Referencia: [CI-CD-QUICKREF.md](CI-CD-QUICKREF.md) para deployment commands

### 🔍 QA / Tester
1. Lee [ONBOARDING.md](ONBOARDING.md) - 15 min
2. Lee [CI-CD-GUIDE.md](CI-CD-GUIDE.md) → sección "Tests y Coverage" - 10 min
3. Lee [CI-CD-GUIDE.md](CI-CD-GUIDE.md) → sección "Validaciones" - 10 min
4. Referencia: [CI-CD-QUICKREF.md](CI-CD-QUICKREF.md) para test commands

---

## 🔍 Búsqueda Rápida por Tema

### ¿Cómo...?

**...ejecuto tests?**
- → [CI-CD-QUICKREF.md](CI-CD-QUICKREF.md) - Cheat Sheet de Comandos
- → [CI-CD-GUIDE.md](CI-CD-GUIDE.md) - Sección "Tests y Coverage"

**...hago coverage report?**
- → [CI-CD-QUICKREF.md](CI-CD-QUICKREF.md) - Comandos
- → [ONBOARDING.md](ONBOARDING.md) - Error "Coverage is below 80%"

**...valido HTML?**
- → [CI-CD-GUIDE.md](CI-CD-GUIDE.md) - Sección "dashboards-ci.yml"
- → [CI-CD-QUICKREF.md](CI-CD-QUICKREF.md) - Cheat Sheet

**...despliego solo converters?**
- → [CI-CD-GUIDE.md](CI-CD-GUIDE.md) - Sección "Deployment Selectivo"
- → [CI-CD-QUICKREF.md](CI-CD-QUICKREF.md) - Deployment Selectivo
- → [CI-CD-ARCHITECTURE.md](CI-CD-ARCHITECTURE.md) - Diagrama #5

**...entiendo path filtering?**
- → [CI-CD-GUIDE.md](CI-CD-GUIDE.md) - Sección "Path Filtering"
- → [CI-CD-ARCHITECTURE.md](CI-CD-ARCHITECTURE.md) - Diagrama #3

**...veo logs del workflow?**
- → GitHub → Actions → [workflow name] → [run number]

**...arreglo un error de coverage?**
- → [ONBOARDING.md](ONBOARDING.md) - Error "Coverage is below 80%"
- → [CI-CD-GUIDE.md](CI-CD-GUIDE.md) - Troubleshooting

### Problemas Específicos

**Tests fallan locally pero pasan en CI (o vice versa)**
- → [CI-CD-GUIDE.md](CI-CD-GUIDE.md) - Troubleshooting - "Tests pasan en local"

**SSH key error en deployment**
- → [ONBOARDING.md](ONBOARDING.md) - Error "SSH key error"
- → [CI-CD-GUIDE.md](CI-CD-GUIDE.md) - Secrets Necesarios

**Coverage below 80%**
- → [ONBOARDING.md](ONBOARDING.md) - Error específico
- → [CI-CD-GUIDE.md](CI-CD-GUIDE.md) - Sección "Tests y Coverage"

**Flake8/Black/Isort errors**
- → [ONBOARDING.md](ONBOARDING.md) - Error "flake8: style issues"
- → [CI-CD-QUICKREF.md](CI-CD-QUICKREF.md) - Comandos

---

## 📊 Información Técnica

### GitHub Actions Workflows
- Ubicación: `.github/workflows/`
- Workflows:
  - `converters-ci.yml` - Tests, linting, performance
  - `dashboards-ci.yml` - HTML validation, data validation
  - `integration.yml` - E2E testing
  - `deploy.yml` - Deployment selectivo

### Test Framework
- Framework: pytest
- Coverage tool: pytest-cov
- Coverage requirement: >80%
- Localización: `converters/tests/`
- Markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.e2e`, `@pytest.mark.slow`

### Validation Tools
- Python linting: flake8, pylint
- Format: black
- Imports: isort
- Security: bandit
- HTML: htmlhint
- JSON Schema: validate_json_schema.py

---

## 🔗 Enlaces Relacionados

### En el Proyecto
- [CLAUDE.md](../CLAUDE.md) - Documentación general del proyecto
- [converters/README.md](../converters/README.md) - Guía de converters
- [scripts/README.md](../scripts/README.md) - Guía de scripts
- [specs/006-optimize-csv-converters/](../specs/006-optimize-csv-converters/) - Especificaciones de converters

### Externos
- GitHub: https://github.com/jfdelafuente/release-dashboard-application
- GitHub Actions Docs: https://docs.github.com/en/actions
- Pytest Docs: https://docs.pytest.org/

---

## 📈 Versiones de Documentación

| Versión | Fecha | Cambios |
|---------|-------|---------|
| 1.0 | 2 Jun 2026 | Creación inicial con 4 documentos |

---

## 💡 Tips de Lectura

### Primer Contacto (15 minutos)
1. [ONBOARDING.md](ONBOARDING.md) - Empieza aquí
2. Haz un cambio de prueba en una rama
3. Observa CI/CD ejecutándose
4. Mergea

### Profundizar (45 minutos)
1. [CI-CD-GUIDE.md](CI-CD-GUIDE.md) - Guía completa
2. [CI-CD-ARCHITECTURE.md](CI-CD-ARCHITECTURE.md) - Visualización
3. Experimenta con cambios locales

### Referencia Diaria
- [CI-CD-QUICKREF.md](CI-CD-QUICKREF.md) - Guarda en favoritos
- Busca por tema en esta página (CI-CD-INDEX.md)

---

## ✅ Checklist para "Listo para Trabajar"

- [ ] Leí [ONBOARDING.md](ONBOARDING.md)
- [ ] Cloné el repo
- [ ] Setup local funciona (pytest o navegador)
- [ ] Hice un cambio de prueba
- [ ] Observé CI/CD ejecutándose
- [ ] Entiendo qué es path filtering
- [ ] Sé cómo ver logs en GitHub Actions
- [ ] Tengo [CI-CD-QUICKREF.md](CI-CD-QUICKREF.md) guardado para consulta rápida

---

**Última actualización:** 2 de Junio de 2026
**Versión:** 1.0
**Mantenedor:** DevOps Team
