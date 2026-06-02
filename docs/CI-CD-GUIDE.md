# 🚀 Guía de CI/CD - Release Dashboard Application

## Descripción General

El proyecto utiliza **GitHub Actions** con **workflows modulares e independientes**. Cada componente (converters, dashboards) tiene su propio pipeline de validación que solo se ejecuta cuando sus archivos cambian.

### Características Principales

- ✅ **Path Filtering**: Los workflows solo corren cuando archivos relevantes cambian
- ✅ **Validación Específica**: Cada componente tiene tests y linting adaptado
- ✅ **E2E Integration**: Workflow que verifica que ambos componentes funcionan juntos
- ✅ **Deployment Selectivo**: Desplegar solo converters, solo dashboards, o ambos
- ✅ **Matriz Python**: Tests en Python 3.8, 3.9, 3.10, 3.11 (converters)

---

## 🏗️ Arquitectura de Workflows

### 1. converters-ci.yml
**Propósito:** Validar código Python de conversión de datos

```
Trigger: Push/PR con cambios en converters/**
├── test (matrix: Python 3.8-3.11)
│   ├── Pytest con coverage (>80% requerido)
│   ├── Upload a Codecov
│   └── Matriz de Python versions
├── lint
│   ├── flake8 (style checks)
│   ├── black (formatting)
│   ├── isort (imports)
│   ├── pylint (code analysis)
│   └── bandit (security)
└── performance (solo en main)
    └── Tests marcados con @pytest.mark.slow
```

**Archivos Vigilados:**
```yaml
paths:
  - 'converters/**'
  - '.github/workflows/converters-ci.yml'
```

### 2. dashboards-ci.yml
**Propósito:** Validar archivos HTML/frontend de dashboards

```
Trigger: Push/PR con cambios en dashboards/** o data/**
├── validate
│   ├── HTMLHint (validar sintaxis HTML5)
│   ├── File structure checks
│   ├── Link validation
│   └── Internal structure verification
├── data-validation
│   ├── Verificar data/output/index.json
│   └── Validar schema JSON
└── build-check
    └── Verificar no hay proceso de build necesario
```

**Archivos Vigilados:**
```yaml
paths:
  - 'dashboards/**'
  - 'data/**'
  - '.github/workflows/dashboards-ci.yml'
```

### 3. integration.yml
**Propósito:** Validar que converters y dashboards funcionan juntos

```
Trigger: Siempre (sin path filtering)
├── e2e-pipeline
│   ├── Busca/crea CSV de prueba
│   ├── Ejecuta converters
│   ├── Genera y valida JSON
│   ├── Crea index.json
│   └── Valida estructura completa
└── cross-component-validation
    └── Verifica que dashboards encuentran datos en ../data/output/
```

### 4. deploy.yml (Refactorizado)
**Propósito:** Deployment selectivo a staging/production

```
Trigger: Manual (workflow_dispatch)
Inputs:
  ├── environment: staging | production
  └── component: converters | dashboards | both

Pipeline:
├── build
│   └── Crea artefacto según componente
├── deploy-staging (condicional)
│   └── Despliega a servidor staging
├── request-production-approval
│   └── Pide aprobación en PR
└── deploy-production (condicional)
    └── Despliega a servidor production
```

---

## 📊 Path Filtering - Cómo Funciona

### Concepto

Los workflows **solo se ejecutan** cuando archivos en sus `paths` cambian.

### Ejemplo 1: Cambio en converters/

```
git add converters/src/converters/converter.py
git commit -m "fix: mejorar performance"
git push

→ ✅ converters-ci.yml corre
→ ✅ integration.yml corre (siempre)
→ ❌ dashboards-ci.yml NO corre
```

### Ejemplo 2: Cambio en dashboards/

```
git add dashboards/index.html
git commit -m "fix: actualizar link"
git push

→ ❌ converters-ci.yml NO corre
→ ✅ dashboards-ci.yml corre
→ ✅ integration.yml corre (siempre)
```

### Ejemplo 3: Cambio en ambos

```
git add converters/cli/convert_incidents.py
git add dashboards/massive-incidents-dashboard.html
git commit -m "feat: nueva feature completa"
git push

→ ✅ converters-ci.yml corre
→ ✅ dashboards-ci.yml corre
→ ✅ integration.yml corre
```

### Resultado: **Eficiencia**

- ❌ No ejecutas tests de converters si solo cambias dashboards
- ❌ No validas HTML si solo cambias Python
- ✅ Feedback más rápido (~2-5 minutos vs 10+)
- ✅ Menos recursos de CI/CD

---

## 🧪 Tests y Coverage

### Converters (unit + integration + e2e)

**Localización:** `converters/tests/`

**Ejecución Manual:**
```bash
cd converters
pytest -v                          # Todos los tests
pytest -m unit -v                  # Solo unit tests
pytest -m integration -v           # Solo integration tests
pytest -m e2e -v                   # Solo e2e tests
pytest -m slow -v                  # Tests de performance
pytest --cov=src --cov-report=html # Con coverage report
```

**Coverage Requerido:** `>80%` (verificado en CI)

**Donde Se Valida:**
- ✅ En local antes de push: `pytest`
- ✅ En CI al hacer push: converters-ci.yml → test job
- ✅ En CI en PRs: misma validación

### Dashboards

**Localización:** `dashboards/`

**Validaciones:**
- ✅ HTML5 syntax (htmlhint)
- ✅ Archivo structure checks
- ✅ Internal links (no links rotos)
- ✅ Data contract (index.json schema)

**Donde Se Valida:**
- ✅ En CI al hacer push: dashboards-ci.yml → validate job
- ✅ En CI en PRs: misma validación

---

## 🚀 Deployment Selectivo

### Escenario 1: Fix en Converters → Deploy solo converters

```
1. Hacer fix en converters/src/
2. git push a main
3. GitHub Actions → deploy (manual)
   - environment: production
   - component: converters ← AQUÍ
4. ✅ Se despliega solo converters
5. ✅ Dashboards no se tocan
```

**Beneficio:** No interrumpes dashboards si algo sale mal

### Escenario 2: Fix en Dashboard → Deploy solo dashboards

```
1. Hacer fix en dashboards/
2. git push a main
3. GitHub Actions → deploy (manual)
   - environment: production
   - component: dashboards ← AQUÍ
4. ✅ Se despliega solo HTML/CSS/JS
5. ✅ Converters no se reinstalan
```

**Beneficio:** Deploy ultra rápido (sin instalar dependencias Python)

### Escenario 3: Release nueva → Deploy ambos

```
1. Cambios en converters/ y dashboards/
2. git push a main
3. GitHub Actions → deploy (manual)
   - environment: production
   - component: both ← DEFAULT
4. ✅ Se despliega todo coordinadamente
5. ✅ Una sola release tag en GitHub
```

**Beneficio:** Versioning coherente para features completas

---

## 📋 Proceso de Deployment Paso a Paso

### 1. Trigger Manual (workflow_dispatch)

**Ubicación:** GitHub → Actions → Deployment Pipeline → Run workflow

```
┌─ environment (required)
│  ├── staging
│  └── production
│
└─ component (required)
   ├── converters
   ├── dashboards
   └── both (default)
```

### 2. Build Stage

El workflow crea artefactos específicos:

```
Si component = "converters":
  release-dashboard-converters-{commit-sha}.tar.gz
  ├── converters/
  ├── scripts/generate-dashboards.sh
  └── VERSION

Si component = "dashboards":
  release-dashboard-dashboards-{commit-sha}.tar.gz
  ├── dashboards/
  ├── data/
  └── VERSION

Si component = "both":
  release-dashboard-complete-{commit-sha}.tar.gz
  ├── converters/
  ├── dashboards/
  ├── data/
  ├── scripts/
  └── VERSION
```

### 3. Staging Deployment

- ✅ Sube artefacto al servidor staging
- ✅ Extrae archivos en `/var/www/release-dashboard-staging`
- ✅ Instala dependencias (solo si component es "converters" o "both")
- ✅ Ejecuta health checks

**Tiempo:** ~3-5 minutos

### 4. Production Deployment

- ✅ Hace backup de versión anterior
- ✅ Sube artefacto al servidor production
- ✅ Extrae archivos en `/var/www/release-dashboard`
- ✅ Instala dependencias (solo si es necesario)
- ✅ Ejecuta health checks
- ✅ Crea release tag en GitHub

**Tiempo:** ~5-8 minutos

### 5. Notificaciones

**En PR:**
- Comenta con estado de staging
- Pide aprobación para production
- Muestra URLs de staging/production

**En Release:**
- Crea release en GitHub con tag versionado
- Incluye información del componente deployado
- Referencia al commit y URLs

---

## 🔍 Validaciones en Cada Workflow

### converters-ci.yml

| Check | Herramienta | Falla? | Nota |
|-------|------------|--------|------|
| Tests + Coverage | pytest | ❌ SÍ | Coverage >80% requerido |
| Style (PEP8) | flake8 | ⚠️ NO | continue-on-error: true |
| Format | black | ⚠️ NO | continue-on-error: true |
| Imports | isort | ⚠️ NO | continue-on-error: true |
| Code quality | pylint | ⚠️ NO | continue-on-error: true |
| Security | bandit | ⚠️ NO | continue-on-error: true |

**Interpretación:**
- ❌ SÍ = Si falla, el workflow se marca rojo (fail)
- ⚠️ NO = Si falla, el workflow sigue verde (informativo)

### dashboards-ci.yml

| Check | Herramienta | Falla? | Nota |
|-------|------------|--------|------|
| HTML5 Syntax | htmlhint | ⚠️ NO | Informativo |
| File exists | bash test | ❌ SÍ | Crítico |
| Links structure | grep | ❌ SÍ | Crítico |
| JSON schema | validate_json_schema.py | ⚠️ NO | continue-on-error |

### integration.yml

| Check | Estado | Nota |
|-------|--------|------|
| CSV de prueba | busca o crea | no falla si no existe |
| Converters execution | ejecuta | continue-on-error |
| JSON generation | valida | continue-on-error |
| index.json schema | valida | continue-on-error |

---

## 🛠️ Troubleshooting

### Problema: converters-ci.yml falla con "coverage below 80%"

**Solución:**
```bash
cd converters
pytest --cov=src --cov-report=html
# Abre htmlcov/index.html en navegador
# Revisa qué código no está siendo cubierto
# Agrega tests para esas líneas
```

### Problema: dashboards-ci.yml reporta "link not found"

**Solución:**
```bash
# Verifica que el archivo existe
ls dashboards/dashboard-portal.html

# Verifica rutas relativas en HTML
grep "../data/output" dashboards/*.html

# Si falta data/output, crea estructura
mkdir -p data/output
```

### Problema: integration.yml falla porque no encuentra CSV de prueba

**Solución:** Es normal si no hay CSVs. El workflow crea uno de prueba automáticamente.
Si quieres usar un CSV específico:
```bash
cp test-data.csv converters/tests/test_data/sample.csv
git add converters/tests/test_data/sample.csv
git commit -m "test: add test CSV"
```

### Problema: deployment a staging falla con "SSH key not found"

**Verificación (requiere admin):**
- GitHub Settings → Secrets → Verificar SSH secrets existen
- Secrets necesarios:
  - `SSH_PRIVATE_KEY`
  - `STAGING_HOST`, `STAGING_PORT`, `STAGING_USER`, `STAGING_URL`
  - `PRODUCTION_HOST`, `PRODUCTION_PORT`, `PRODUCTION_USER`, `PRODUCTION_URL`

### Problema: Tests pasan en local pero fallan en CI

**Causas comunes:**
1. Diferencia en Python version
   ```bash
   python --version  # Verifica en local
   # En CI corre matrix: 3.8, 3.9, 3.10, 3.11
   ```

2. Diferencia en encoding
   ```bash
   # En Windows: UTF-8 con BOM
   # En GitHub Actions (Linux): UTF-8 sin BOM
   # Los converters manejan ambos automáticamente
   ```

3. Path separators
   ```bash
   # Usa siempre Path() de pathlib para portabilidad
   from pathlib import Path
   path = Path("converters") / "tests" / "test_data"
   ```

---

## 📚 Estructura de Directorios Relevantes

```
.github/workflows/
├── converters-ci.yml      ← Validación de converters
├── dashboards-ci.yml      ← Validación de dashboards
├── integration.yml        ← E2E testing
└── deploy.yml            ← Deployment selectivo

converters/
├── src/                   ← Código principal
├── cli/                   ← Scripts CLI
├── tests/                 ← Suite de tests
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   └── performance/
├── requirements.txt       ← Dependencies
└── pytest.ini            ← Configuración pytest

dashboards/
├── *.html                ← Dashboards principales
├── css/                  ← Estilos (si es necesario)
└── js/                   ← Scripts (si es necesario)

data/
├── input/                ← CSVs a procesar (git-ignored)
├── output/               ← JSON generados (git-ignored)
└── errors/               ← Reportes de error (git-ignored)

scripts/
├── generate-dashboards.sh  ← Automation script
└── validate_json_schema.py ← JSON validator
```

---

## 🔐 Secrets Necesarios para Deploy

**Para staging:**
- `SSH_PRIVATE_KEY` - Clave privada SSH
- `STAGING_HOST` - IP o hostname del servidor
- `STAGING_PORT` - Puerto SSH (ej: 22)
- `STAGING_USER` - Usuario SSH
- `STAGING_URL` - URL pública del staging

**Para production:**
- `SSH_PRIVATE_KEY` - Misma clave (o separada si prefieres)
- `PRODUCTION_HOST` - IP o hostname
- `PRODUCTION_PORT` - Puerto SSH
- `PRODUCTION_USER` - Usuario SSH
- `PRODUCTION_URL` - URL pública de production

**Setup:** GitHub → Settings → Secrets and variables → Actions

---

## 📞 Referencias Rápidas

### Comandos Locales Útiles

```bash
# Tests en converters
cd converters && pytest -v

# Coverage report
cd converters && pytest --cov=src --cov-report=html

# Linting
cd converters && flake8 src/ cli/
cd converters && black --check src/ cli/
cd converters && isort --check-only src/ cli/

# HTML validation (requiere npm)
npx htmlhint dashboards/*.html

# Validar JSON
python scripts/validate_json_schema.py data/output/index.json
```

### GitHub Actions URLs

```
https://github.com/jfdelafuente/release-dashboard-application/actions
  └── Converters CI
  └── Dashboards CI
  └── Integration Tests
  └── Deployment Pipeline
```

### Documentación Relacionada

- 📄 [specs/006-optimize-csv-converters/plan.md](../specs/006-optimize-csv-converters/plan.md) - Plan de implementación
- 📄 [CLAUDE.md](../CLAUDE.md) - Documentación del proyecto
- 📄 [converters/README.md](../converters/README.md) - Guía de converters
- 📄 [scripts/README.md](../scripts/README.md) - Guía de scripts

---

## ✅ Checklist para PRs

Antes de hacer push a una PR:

- [ ] Tests locales pasan: `pytest`
- [ ] Coverage OK: `pytest --cov=src`
- [ ] Linting OK: `flake8 src/` (si cambias converters)
- [ ] Archivos HTML validos: `htmlhint` (si cambias dashboards)
- [ ] Imports organizados: `isort`
- [ ] Código formateado: `black`

Ejemplo:
```bash
# Pre-push checks
cd converters
pytest --cov=src --cov-fail-under=80 -v
flake8 src/ cli/
black src/ cli/
isort src/ cli/

# Si todo OK
git push
```

---

## 🎓 Para Nuevos Miembros del Equipo

**Quick Start:**

1. **Clonar el repo**
   ```bash
   git clone https://github.com/jfdelafuente/release-dashboard-application.git
   cd release-dashboard-application
   ```

2. **Si trabajas con converters**
   ```bash
   cd converters
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   pytest -v  # Verificar tests pasan
   ```

3. **Si trabajas con dashboards**
   ```bash
   # No requiere setup, es HTML puro
   # Abre dashboards/*.html en navegador
   ```

4. **Antes de hacer push**
   ```bash
   # Si cambiaste converters
   cd converters && pytest

   # Si cambiaste dashboards
   # Solo verifica HTML sea válido en navegador
   ```

5. **Workflow CI/CD automático**
   - Push a feature branch o PR
   - GitHub Actions corre automáticamente
   - Revisa tab "Actions" para ver status

**Preguntas frecuentes:**
- "¿Cómo sé si mis cambios quebraron algo?" → Revisa GitHub Actions
- "¿Necesito hacer deployment?" → No, los PRs no despliegan (solo main)
- "¿Cómo despliego a production?" → Pide acceso a Actions → deploy workflow

---

**Última actualización:** 2 de Junio de 2026
**Versión:** 1.0
**Mantenedor:** DevOps Team
