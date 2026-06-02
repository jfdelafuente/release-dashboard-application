# 🚀 CI/CD - Quick Reference

## Workflows en Un Vistazo

| Workflow | Trigger | Tiempo | Status |
|----------|---------|--------|--------|
| **converters-ci** | Push/PR en `converters/` | ~3-5 min | 🔴 Falla si <80% coverage |
| **dashboards-ci** | Push/PR en `dashboards/` | ~2-3 min | 🟡 Informativo |
| **integration** | Siempre | ~5-10 min | 🟡 Informativo |
| **deploy** | Manual (workflow_dispatch) | ~8-15 min | 🔴 Falla si deployment fail |

---

## Cambio Local → Push → CI/CD

### Cambio solo en Converters
```
git add converters/
git commit -m "fix: mejorar parser"
git push
    ↓
✅ converters-ci corre (tests + linting)
✅ integration corre (E2E)
❌ dashboards-ci NO corre
```

### Cambio solo en Dashboards
```
git add dashboards/
git commit -m "fix: actualizar CSS"
git push
    ↓
❌ converters-ci NO corre
✅ dashboards-ci corre (HTML validation)
✅ integration corre (E2E)
```

### Cambio en Ambos
```
git add converters/ dashboards/
git commit -m "feat: nueva feature"
git push
    ↓
✅ converters-ci corre
✅ dashboards-ci corre
✅ integration corre
```

---

## Pre-Push Checks

```bash
# Solo converters
cd converters
pytest -v                        # Tests
pytest --cov=src                # Coverage
flake8 src/ cli/                # Style
black --check src/              # Format
isort --check-only src/         # Imports

# Si TODO OK
git push
```

---

## Deployment Selectivo

### Opción 1: Solo Converters
```
GitHub Actions → Deployment Pipeline → Run workflow
  environment: production
  component: converters ✓
```
→ Despliega `converters/` + scripts

### Opción 2: Solo Dashboards
```
GitHub Actions → Deployment Pipeline → Run workflow
  environment: production
  component: dashboards ✓
```
→ Despliega `dashboards/` + data/

### Opción 3: Ambos (Default)
```
GitHub Actions → Deployment Pipeline → Run workflow
  environment: production
  component: both ✓
```
→ Despliega todo

---

## Status Badges en GitHub Actions

| Símbolo | Significado |
|---------|------------|
| 🟢 Checkmark | Workflow pasó |
| 🔴 X Red | Workflow falló |
| 🟡 Yellow | Workflow en progreso |
| ⏭️ Skip | Workflow skipped (path filtering) |

**Dónde ver:**
- PR checks (automático debajo del descripción)
- Tab "Actions" en repo
- Commit status en history

---

## Coverage Requirement

```
Tests:   ❌ Falla si < 80%
Linting: ⚠️ Informativo (no falla)
```

### Aumentar Coverage

```bash
cd converters
pytest --cov=src --cov-report=html
# Abre htmlcov/index.html
# Agrega tests para líneas rojas
pytest --cov=src  # Verifica %
```

---

## Archivos Vigilados

### converters-ci.yml
```
✅ paths:
  - converters/**
  - .github/workflows/converters-ci.yml
```

### dashboards-ci.yml
```
✅ paths:
  - dashboards/**
  - data/**
  - .github/workflows/dashboards-ci.yml
```

### integration.yml
```
❌ Sin path filtering (siempre corre)
```

### deploy.yml
```
❌ Manual (workflow_dispatch)
```

---

## Error Común: "Tests < 80%"

```
Solución:
cd converters
pytest --cov=src --cov-report=html
# Abre htmlcov/index.html
# Revisa qué código NO está cubierto (rojo)
# Agrega @pytest.mark.unit tests para eso
pytest --cov=src  # Verifica nuevamente
```

---

## Error Común: "Linting Fail"

```
converters-ci → lint → flake8 / black / isort FAIL

Solución rápida:
cd converters
black src/ cli/          # Auto-fix format
isort src/ cli/          # Auto-fix imports
flake8 src/ cli/         # Solo reporta (no auto-fix)
git add src/ cli/
git commit -m "style: auto-format"
git push
```

---

## Environment Variables & Secrets

### Staging Secrets
- SSH_PRIVATE_KEY
- STAGING_HOST
- STAGING_PORT
- STAGING_USER
- STAGING_URL

### Production Secrets
- PRODUCTION_HOST
- PRODUCTION_PORT
- PRODUCTION_USER
- PRODUCTION_URL

**Setup:** GitHub Repo → Settings → Secrets and variables → Actions

---

## Links Importantes

```
GitHub Actions:
  https://github.com/jfdelafuente/release-dashboard-application/actions

Codecov:
  https://codecov.io/gh/jfdelafuente/release-dashboard-application

Docs:
  - Full Guide: docs/CI-CD-GUIDE.md
  - Project Info: CLAUDE.md
  - Converters: converters/README.md
```

---

## Matriz Python (converters-ci)

Converters se testa en:
- Python 3.8
- Python 3.9
- Python 3.10
- Python 3.11

Si algo falla en una versión:
```bash
pyenv install 3.10
pyenv local 3.10
cd converters
pytest -v
# Debug
```

---

## Artifacts Generados

### coverters-ci
- lint-reports/ (flake8, pylint reports)
- (coverage.xml en Codecov)

### dashboards-ci
- (ninguno, solo reporta)

### integration
- (ninguno, solo reporta)

### deploy
- build-artifact/ (tarball)
  - release-dashboard-converters-{sha}.tar.gz
  - release-dashboard-dashboards-{sha}.tar.gz
  - release-dashboard-complete-{sha}.tar.gz

---

## Workflow Execution Times

```
converters-ci:     ~3-5 min
  ├── test matrix  ~2-3 min (paralelo)
  ├── lint         ~1 min
  └── performance  ~1 min

dashboards-ci:     ~2-3 min
  ├── validate     ~1 min
  ├── data-val     ~30s
  └── build-check  ~30s

integration:       ~5-10 min
  ├── e2e-pipeline ~3-5 min
  └── cross-comp   ~1-2 min

deploy (full):     ~10-15 min
  ├── build        ~2 min
  ├── staging      ~5 min
  ├── approval     ~5 min (manual)
  └── production   ~5-8 min
```

---

## VS Code Extensions Recomendadas

```json
{
  "recommendations": [
    "ms-python.python",          // Python
    "ms-python.vscode-pylance",  // Linting
    "GitHub.copilot",            // AI assist
    "redhat.vscode-yaml",        // YAML syntax (workflows)
    "ms-vscode.makefile-tools"   // Makefiles
  ]
}
```

---

## Cheat Sheet de Comandos

```bash
# Tests
pytest
pytest -v
pytest -m unit
pytest --cov=src

# Linting
flake8 src/ cli/
black src/ cli/
isort src/ cli/
pylint src/
bandit -r src/

# Git
git add .
git commit -m "feat: description"
git push

# Local server (dashboards)
python -m http.server 8000 -d dashboards/
# http://localhost:8000
```

---

## Troubleshooting Quick Links

| Problema | Causa | Solución |
|----------|-------|----------|
| Coverage <80% | Tests insuficientes | Agregar @pytest.mark tests |
| Flake8 fail | Style violation | `black` auto-format |
| Import wrong | isort | `isort` auto-sort |
| SSH key fail | Secret no set | Setup en GitHub Settings |
| HTML invalid | Syntax error | Validar en navegador |
| JSON fail | Schema mismatch | Ver integration.yml logs |

---

**Última actualización:** 2 de Junio de 2026 | **v1.0**
