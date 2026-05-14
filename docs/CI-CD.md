# CI/CD Pipeline Documentation

Automated testing, linting, and deployment workflows for the Release Dashboard Application.

## Overview

The project uses **GitHub Actions** to automate:
- ✅ Test execution and coverage validation (80% minimum)
- ✅ Code quality and style checks
- ✅ Security vulnerability scanning
- ✅ Automated deployment to staging
- ✅ Manual approval for production deployments

---

## Prerequisitos Antes de Ejecutar CI/CD

### 1. Configurar GitHub Secrets

Para que el CI/CD funcione con VPS, debes configurar secrets en tu repositorio GitHub:

**Pasos**:
1. Ve a tu repositorio GitHub → **Settings** → **Secrets and variables** → **Actions**
2. Haz click en **"New repository secret"**
3. Añade los siguientes secrets:

| Secret | Descripción | Ejemplo |
|--------|-------------|---------|
| `SSH_PRIVATE_KEY` | Clave privada SSH para acceder a VPS | `-----BEGIN RSA PRIVATE KEY-----\nMII...` |
| `STAGING_HOST` | IP o dominio del servidor staging | `staging.example.com` o `192.168.1.10` |
| `STAGING_USER` | Usuario SSH en servidor staging | `root` o `app` |
| `STAGING_PORT` | Puerto SSH en staging | `22` (default) |
| `PRODUCTION_HOST` | IP o dominio del servidor producción | `prod.example.com` o `192.168.1.20` |
| `PRODUCTION_USER` | Usuario SSH en servidor producción | `root` o `app` |
| `PRODUCTION_PORT` | Puerto SSH en producción | `22` (default) |
| `STAGING_URL` | URL del ambiente de staging | `https://staging.dashboard.example.com` |
| `PRODUCTION_URL` | URL de producción | `https://dashboard.example.com` |

**⚠️ IMPORTANTE - SSH Key**:
1. Genera una clave SSH sin contraseña:
   ```bash
   ssh-keygen -t rsa -b 4096 -f deploy_key -N ""
   ```
2. Copia el contenido de `deploy_key` (privada) a `SSH_PRIVATE_KEY` secret
3. Añade `deploy_key.pub` (pública) a `~/.ssh/authorized_keys` en ambos servidores:
   ```bash
   cat deploy_key.pub >> ~/.ssh/authorized_keys
   chmod 600 ~/.ssh/authorized_keys
   ```

**Estructura de directorios en VPS** (ambos servidores):
```
/var/www/release-dashboard/          # Directorio de aplicación
/var/www/release-dashboard-staging/  # Directorio staging
/var/backups/release-dashboard/      # Backups automáticos
```

Crea estos directorios en ambos servidores:
```bash
sudo mkdir -p /var/www/release-dashboard
sudo mkdir -p /var/www/release-dashboard-staging
sudo mkdir -p /var/backups/release-dashboard
sudo chown app:app /var/www/release-dashboard*
sudo chown root:root /var/backups/release-dashboard
```

### 2. Configurar Branch Protection Rules

Para forzar que todos los PRs pasen los tests:

1. Ve a **Settings** → **Branches**
2. Selecciona `main` bajo "Branch protection rules"
3. Haz click **"Add rule"** si no existe
4. Configura:
   - ✅ **Require status checks to pass before merging**:
     - `test` (tests.yml)
     - `lint` (lint.yml)
   - ✅ **Require branches to be up to date before merging**
   - ✅ **Require code reviews before merging** (opcional)
   - ❌ **Allow force pushes**: desactivado

### 3. Verifica que pytest.ini existe

El archivo `pytest.ini` debe estar en la raíz del proyecto con configuración de coverage:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

[coverage:run]
source = src, csv_to_json
fail_under = 80
```

---

## Workflows

### 1. Tests & Coverage (`tests.yml`)

**Archivo**: `.github/workflows/tests.yml`
**Trigger**: Automático en cada push y pull request
**Propósito**: Ejecutar tests con validación de 80% coverage

**Características**:
- Matrix testing: Python 3.8, 3.9, 3.10, 3.11
- Coverage reporting (XML, HTML)
- Sube resultados a Codecov
- Comenta en el PR con % de coverage

**Requisito crítico**: Coverage >= 80% (bloquea merge si está por debajo)

**¿Qué hacer si falla?**:
- Lee el output del workflow en GitHub Actions
- Busca "FAILED" en los logs
- Ejecuta localmente: `pytest tests/ --cov --cov-fail-under=80`
- Aumenta coverage escribiendo más tests

### 2. Code Quality & Linting (`lint.yml`)

**Archivo**: `.github/workflows/lint.yml`
**Trigger**: Automático en cada push y pull request
**Propósito**: Validar estilo y seguridad del código

**Herramientas**:
- `flake8` - Estilo PEP 8
- `black` - Formateo de código
- `isort` - Organización de imports
- `pylint` - Análisis de código
- `bandit` - Escaneo de seguridad

⚠️ **Nota**: Este workflow es **non-blocking** (no bloquea merge si falla), pero verás advertencias.

**¿Qué hacer si ves advertencias?**:
```bash
# Auto-arreglar formateo y imports
black src/ csv_to_json/ tests/
isort src/ csv_to_json/ tests/

# Revisar flake8
flake8 src/ csv_to_json/ tests/

# Revisar pylint
pylint src/ csv_to_json/
```

### 3. Deployment Pipeline (`deploy.yml`)

**Archivo**: `.github/workflows/deploy.yml`
**Trigger**:
- ⚠️ Manual solamente (`workflow_dispatch`)
- No se ejecuta automáticamente hasta que staging esté configurado

**Propósito**: Deploy manual a VPS staging + aprobación manual para VPS producción

**⚠️ ESTADO**: Este workflow está **DESACTIVADO** por defecto. Se ejecutará únicamente cuando sea disparado manualmente desde GitHub Actions y se configure los secretos requeridos (SSH_PRIVATE_KEY, STAGING_HOST, STAGING_USER, STAGING_PORT, STAGING_URL, etc.)

**Infraestructura**:
- **Staging**: VPS via SSH (conectado automáticamente en cada push a main)
- **Production**: VPS via SSH (deploy manual después de validar staging)

**Flujo**:
```
PUSH a main
    ↓
[Build] - Crea artifact comprimido (tar.gz)
    ↓
[Deploy Staging] - Via SSH: scp + tar + pip install
    ↓
[Health Check] - Verifica HTTP 200 en STAGING_URL
    ↓
[Request Approval] - Comenta en PR para aprobar prod
    ↓
[Deploy Production] - Manual: scp + tar + pip install
                     + Backup automático antes de overwrite
    ↓
[Health Check Prod] - Verifica HTTP 200 en PRODUCTION_URL
    ↓
[Create Release] - Crea GitHub Release con v{{ version }}
```

---

## Cómo Ejecutar el CI/CD

### Ejecución Automática (Recomendado)

1. **Haz un commit y push a tu rama**:
```bash
git add .
git commit -m "Add feature X"
git push origin feature/X
```

2. **GitHub Actions se dispara automáticamente**:
   - Ve a tu repo → **Actions**
   - Verás "Tests & Coverage" y "Linting" corriendo
   - Espera a que terminen ✅

3. **Crea un Pull Request**:
   - Los workflows corren de nuevo
   - Si pasan, verás ✅ junto a "All checks passed"
   - Si fallan, verás ❌ y los errores en la sección de checks

4. **Merge a main**:
   - Una vez que PR es aprobado y checks pasan
   - ⚠️ El deployment NO se ejecuta automáticamente (requiere secretos configurados)
   - Para desplegar manualmente a staging/producción, usa la sección "Deployment Manual" abajo

### Ejecución Manual (Para Testing)

Para disparar workflows manualmente sin hacer push:

1. Ve a tu repo → **Actions**
2. Selecciona el workflow (e.g., "Tests & Coverage")
3. Haz click **"Run workflow"**
4. Selecciona rama y haz click **"Run"**

### Deployment Manual (Staging/Production)

⚠️ **PREREQUISITO**: Primero debes configurar los GitHub Secrets (ver sección "Configurar GitHub Secrets" arriba).

**Para desplegar a Staging**:

1. Ve a tu repositorio GitHub → **Actions**
2. Selecciona **"Deployment Pipeline"**
3. Haz click **"Run workflow"**
4. Selecciona:
   - **Branch**: `main` (o la rama que quieras desplegar)
   - **Environment**: `staging`
5. Haz click **"Run workflow"**
6. Espera a que se complete:
   - Build
   - Deploy Staging
   - Health Check
7. Si todo falla, revisa el log del workflow para ver el error

**Para desplegar a Production** (DESPUÉS de validar staging):

1. Ve a **Actions** → **Deployment Pipeline**
2. Haz click **"Run workflow"**
3. Selecciona:
   - **Branch**: `main`
   - **Environment**: `production` ← ⚠️ IMPORTANTE: Cambia a "production"
4. Haz click **"Run workflow"**
5. El flujo hará:
   - Build
   - Deploy a Production VPS
   - Crea backup automático antes de deploy
   - Health check
   - Crea GitHub Release con la versión

**⚠️ IMPORTANTE - Secretos requeridos**:

Si el workflow falla con errores de SSH o conexión:
1. Verifica que TODOS los secrets estén configurados en Settings → Secrets → Actions
2. Requeridos para staging: `SSH_PRIVATE_KEY`, `STAGING_HOST`, `STAGING_USER`, `STAGING_PORT`, `STAGING_URL`
3. Requeridos para production: `SSH_PRIVATE_KEY`, `PRODUCTION_HOST`, `PRODUCTION_USER`, `PRODUCTION_PORT`, `PRODUCTION_URL`

---

## Local Testing (Antes de hacer Push)

Ejecuta esto ANTES de hacer push para evitar fallos en CI:

```bash
# 1. Ejecutar todos los tests con coverage
pytest tests/ --cov=src --cov=csv_to_json --cov-fail-under=80 -v

# 2. Ejecutar linting (style)
flake8 src/ csv_to_json/ tests/ --max-line-length=120

# 3. Ejecutar black (formato)
black --check src/ csv_to_json/ tests/

# 4. Ejecutar isort (imports)
isort --check-only src/ csv_to_json/ tests/

# 5. Ejecutar pylint (análisis profundo)
pylint src/ csv_to_json/

# 6. Ejecutar bandit (seguridad)
bandit -r src/ csv_to_json/
```

### Auto-Fix Automático

Para arreglar automáticamente style y imports:

```bash
# Formatear código
black src/ csv_to_json/ tests/

# Organizar imports
isort src/ csv_to_json/ tests/
```

---

## Troubleshooting

### Tests Fallan con "Coverage below 80%"

**Causa**: Código nuevo sin tests

**Solución**:
```bash
# Ver qué líneas no tienen cobertura
pytest tests/ --cov --cov-report=html
# Abre htmlcov/index.html en navegador
# Escribe tests para las líneas rojas
```

### Lint Falla por "Black format issues"

**Causa**: Código no formateado

**Solución**:
```bash
black src/ csv_to_json/ tests/
git add .
git commit -m "Format code with black"
git push
```

### Deploy Workflow Falla Silenciosamente

**Causa**: Secrets SSH no configurados correctamente

**Solución**:
1. Ve a Settings → Secrets → Actions
2. Verifica que existen TODOS estos secrets:
   - `SSH_PRIVATE_KEY` (la clave privada completa, con saltos de línea)
   - `STAGING_HOST`, `STAGING_USER`, `STAGING_PORT`
   - `PRODUCTION_HOST`, `PRODUCTION_USER`, `PRODUCTION_PORT`
   - `STAGING_URL`, `PRODUCTION_URL`
3. Si faltan, añádelos
4. Re-dispara el workflow desde Actions tab

### Deploy Falla con "Permission denied (publickey)"

**Causa**: Clave SSH no autorizada en servidor

**Solución**:
1. En tu VPS, añade la clave pública a authorized_keys:
   ```bash
   cat deploy_key.pub >> ~/.ssh/authorized_keys
   chmod 600 ~/.ssh/authorized_keys
   chmod 700 ~/.ssh
   ```
2. Verifica que el usuario SSH puede conectar:
   ```bash
   ssh -i deploy_key -p 22 app@staging.example.com "echo test"
   ```
3. Si sigue fallando, revisa `/var/log/auth.log` en el VPS

### Deploy Falla con "No space left on device"

**Causa**: VPS sin espacio disco

**Solución**:
```bash
# En el VPS, limpia directorios temporales
rm -rf /tmp/release-dashboard-*.tar.gz
df -h  # Verifica espacio disponible
```

### Merge a main pero Deploy NO se ejecuta

**Causa**: Merge directo sin PR

**Solución**:
1. Siempre haz merge a través de GitHub UI (botón "Merge pull request")
2. No hagas `git push` directamente a main
3. Los workflows se disparan SOLO si el merge fue a través de GitHub

### Health Check Falla en VPS

**Causa**: Aplicación no está sirviendo HTTP correctamente

**Solución**:
1. SSH al servidor staging/production
2. Verifica que la aplicación está corriendo:
   ```bash
   ps aux | grep python
   curl -s http://localhost:8000  # o el puerto que uses
   ```
3. Revisa logs de la aplicación:
   ```bash
   tail -f /var/log/release-dashboard/*.log
   ```
4. Verifica que firewall permite tráfico HTTP:
   ```bash
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   ```

---

## Ejemplo Completo: Flujo de Desarrollo

```bash
# 1. Crear rama de feature
git checkout -b feature/add-validation

# 2. Escribir código + tests
# ... edita archivos ...

# 3. Verificar localmente ANTES de push
pytest tests/ --cov --cov-fail-under=80
black src/
isort src/

# 4. Commit y push
git add .
git commit -m "Add validation feature"
git push origin feature/add-validation

# 5. GitHub Actions automáticamente:
#    ✅ tests.yml corre
#    ✅ lint.yml corre
#    → Ve a GitHub Actions para ver progreso

# 6. Crear Pull Request en GitHub
#    → Workflows corren de nuevo
#    → Si pasan: verás ✅ "All checks passed"

# 7. Merge a main (desde GitHub UI)
#    → Tests y Linting se ejecutan de nuevo
#    → ⚠️ Deployment NO se ejecuta automáticamente
#    → Debes disparar deployment manualmente

# 8. Para desplegar a staging (manual):
#    → Ve a Actions → Deployment Pipeline
#    → Haz click "Run workflow"
#    → Selecciona environment: "staging"
#    → Verifica en STAGING_URL después del deploy

# 9. Para producción (después de validar staging):
#    → Ve a Actions → Deploy Pipeline
#    → Haz click "Run workflow"
#    → Selecciona environment: "production" ⚠️ IMPORTANTE
#    → Verifica en PRODUCTION_URL
```

---

## Archivos Importantes

| Archivo | Propósito |
|---------|-----------|
| `.github/workflows/tests.yml` | Ejecuta pytest y valida 80% coverage |
| `.github/workflows/lint.yml` | Ejecuta flake8, black, isort, pylint, bandit |
| `.github/workflows/deploy.yml` | Deploy a VPS via SSH (staging auto, prod manual) |
| `pytest.ini` | Configuración de pytest y coverage |
| `tests/` | Todos tus tests deben estar aquí |
| `requirements.txt` | Dependencias Python (se instala en VPS) |
| `VERSION` | Archivo con número de versión (se lee en build) |

---

## Dashboard: Monitoring CI/CD Status

En GitHub:
- **Actions** → Ver todos los workflows en tiempo real
- **Pull Requests** → Ver checks en cada PR
- **Commits** → Ver status de cada commit (✅ ❌)
- **Codecov** → Ver histórico de coverage (si conectas Codecov)

---

---

## Resumen: CI/CD en VPS

```
Desarrollo Local → GitHub Push
       ↓
tests.yml (Python 3.8-3.11, Coverage 80%)
       ↓
lint.yml (flake8, black, isort, pylint, bandit)
       ↓
PR Review & Merge a main
       ↓
⚠️ MANUAL: Actions → Deployment Pipeline → Run workflow
       ↓
deploy.yml (disparado manualmente) → SSH a Staging VPS
       ↓
Health Check Staging
       ↓
⚠️ MANUAL: Actions → Deploy to Production (después de validar staging)
       ↓
Backup automático + Deploy + Health Check
       ↓
GitHub Release creado
```

**IMPORTANTE**: El deployment NO es automático. Debes:
1. Hacer merge a `main` para ejecutar tests y linting
2. Una vez validado, disparar deployment manualmente desde Actions → Deployment Pipeline
3. Seleccionar environment (staging o production)

**Last Updated**: 2026-05-14
**Infrastructure**: VPS via SSH (no AWS)
