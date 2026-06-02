# 👋 Onboarding - Nuevos Miembros del Equipo

Bienvenido al equipo de Release Dashboard Application. Esta guía te pone al día en 15 minutos.

## ⚡ Lo Más Importante

1. **El proyecto tiene 2 partes independientes:**
   - `converters/` - Herramientas Python (CSV → JSON)
   - `dashboards/` - Frontend HTML (visualización)

2. **CI/CD automático:**
   - Haces push → GitHub Actions corre tests automáticamente
   - Si todo OK → puedes mergear
   - Si falla → revisa logs y arregla

3. **Qué usar:**
   - Para converters: Python 3.11+, pytest, git
   - Para dashboards: navegador, git
   - Para ambos: GitHub Actions (automático)

---

## 🏃 Setup Rápido (5 minutos)

### 1. Clonar Repo
```bash
git clone https://github.com/jfdelafuente/release-dashboard-application.git
cd release-dashboard-application
```

### 2. Si Trabajas con Converters
```bash
cd converters
python -m venv venv          # crear virtualenv
source venv/bin/activate     # en Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
pytest -v                    # verificar que funciona
```

### 3. Si Trabajas con Dashboards
```bash
# No necesita setup especial, es HTML puro
# Abre en navegador: dashboards/index.html
# O levanta servidor:
cd dashboards
python -m http.server 8000
# http://localhost:8000
```

---

## 📝 Workflow Típico

### Escenario: Arreglar Bug en Converters

```bash
# 1. Crear rama
git checkout -b fix/parser-bug

# 2. Hacer cambios
# Editar converters/src/converters/parser.py

# 3. Tests locales
cd converters
pytest -v                    # ¿pasan los tests?
pytest --cov=src            # ¿coverage OK? (>80%)

# 4. Commit
git add converters/
git commit -m "fix: parser error handling"

# 5. Push
git push origin fix/parser-bug

# 6. GitHub Actions automático
# Espera 3-5 minutos
# Revisa tab "Actions" en GitHub
# ✅ Si verde: todo bien
# ❌ Si rojo: lee logs y arregla

# 7. Pull Request
# GitHub te permite hacer PR automáticamente
# Revisa que todos los checks sean ✅
# Pide review a un colega
# Merge cuando esté aprobado
```

### Escenario: Cambio en Dashboard

```bash
# 1. Rama
git checkout -b feat/dashboard-update

# 2. Cambios
# Editar dashboards/index.html

# 3. Test local
# Abre en navegador, verifica que funciona

# 4. Commit
git add dashboards/
git commit -m "feat: add new KPI card"

# 5. Push
git push origin feat/dashboard-update

# 6. CI/CD automático (2-3 min)
# dashboards-ci.yml valida HTML
# integration.yml verifica E2E

# 7. PR y merge igual que arriba
```

---

## 🚨 Errores Comunes (y cómo arreglarlos)

### Error: "pytest: command not found"
```bash
# Olvidaste instalar dependencias
cd converters
pip install -r requirements-dev.txt
pytest
```

### Error: "Coverage is below 80%"
```bash
# Tus cambios no tienen tests suficientes
cd converters

# Ver qué código no está cubierto
pytest --cov=src --cov-report=html
# Abre htmlcov/index.html

# Agregar tests para código rojo
# En converters/tests/unit/ agrega test_*.py
pytest --cov=src  # Verifica de nuevo
```

### Error: "flake8: style issues"
```bash
# Tu código tiene estilo inconsistente
cd converters

# Auto-fix
black src/ cli/        # formato
isort src/ cli/        # imports

# Verifica
flake8 src/ cli/       # solo reporta (no auto-fix)

# Commit
git add src/ cli/
git commit -m "style: auto-format code"
```

### Error en GitHub Actions: "SSH key error"
```
Contacta a un admin, necesita:
- SSH_PRIVATE_KEY (secret)
- STAGING_HOST, STAGING_PORT, etc (secrets)
```

---

## 📚 Documentación Completa

Si necesitas más detalles:

1. **CI/CD Completo:** [CI-CD-GUIDE.md](CI-CD-GUIDE.md)
2. **Quick Reference:** [CI-CD-QUICKREF.md](CI-CD-QUICKREF.md)
3. **Arquitectura:** [CI-CD-ARCHITECTURE.md](CI-CD-ARCHITECTURE.md)
4. **Info del Proyecto:** [CLAUDE.md](../CLAUDE.md)
5. **Converters:** [converters/README.md](../converters/README.md)

---

## 🔑 Conceptos Clave (3 minutos)

### Path Filtering
```
Cambio solo en converters/
  → solo converters-ci corre

Cambio solo en dashboards/
  → solo dashboards-ci corre

Cambio en ambos
  → ambas corren

integration.yml SIEMPRE corre
  → valida que ambas partes funcionan juntas
```

### Coverage
```
>80% requerido en converters

Si escribes código nuevo, necesita tests

Si cambias código viejo:
  nueva_líneas_código / (nueva_líneas_código + líneas_sin_test)

Herramienta: pytest --cov=src --cov-report=html
```

### Deployment
```
manual: GitHub Actions → Deploy → Run workflow

Inputs:
  - environment: staging o production
  - component: converters, dashboards, o both

Ejemplo:
  environment = production
  component = converters
  → solo converters se despliega
```

---

## 🎯 Checklist Antes de Hacer Push

- [ ] Cambios locales funcionan
- [ ] Tests pasan: `pytest -v`
- [ ] Coverage OK: `pytest --cov=src` (>80%)
- [ ] Sin conflictos: `git pull origin main`
- [ ] Commit message descriptivo
- [ ] Branch name descriptivo: `fix/`, `feat/`, `docs/`

```bash
# Quick check
cd converters
pytest --cov=src --cov-fail-under=80 -v
flake8 src/ cli/
black --check src/ cli/

# Si TODO OK
git push
```

---

## 🤝 Pedir Ayuda

**Slack/Teams:**
- Problema de setup → @DevOps
- Bug en converters → @Backend
- Bug en dashboards → @Frontend

**GitHub Issues:**
1. Busca issue existente
2. Si no existe, crea una nueva
3. Describe: qué esperabas vs qué pasó
4. Incluye: logs, steps para reproducir

**Documentación:**
- Preguntas sobre CI/CD → CI-CD-GUIDE.md
- Preguntas sobre código → CLAUDE.md
- Preguntas sobre converters → converters/README.md

---

## 📋 Ramas y Naming

```
✅ BIEN:
  fix/parser-bug
  feat/new-dashboard
  docs/update-guide
  refactor/simplify-validation

❌ MAL:
  bugfix
  feature-test
  stuff
  temporal-branch
```

---

## 🔄 Merge Workflow

```
1. Feature branch
   └─ git checkout -b feat/new-feature

2. Cambios + commits
   └─ git push origin feat/new-feature

3. GitHub: Create PR
   └─ Espera que CI/CD corra

4. Review
   └─ Un colega revisa código

5. Merge
   └─ Si ✅ checks + ✅ review
   └─ Delete branch después de merge

6. Sync local
   └─ git checkout main
   └─ git pull origin main
```

---

## 🎓 Próximos Pasos

**Después de este onboarding:**

1. Lee [CI-CD-GUIDE.md](CI-CD-GUIDE.md) (completo)
2. Haz un cambio de prueba (fix cosmético en dashboard)
3. Crea un PR
4. Observa CI/CD ejecutándose
5. Mergea cuando esté OK
6. ¡Bienvenido al equipo! 🚀

---

## ☎️ Contactos Importantes

| Rol | Contacto | Para... |
|-----|----------|---------|
| Lead | @jfdelafuente | Decisiones arquitectura |
| DevOps | @devops-team | CI/CD, deployment |
| QA | @qa-team | Testing, coverage |

---

**Última actualización:** 2 de Junio de 2026
**Versión:** 1.0 - Inicio del proyecto
