# CI/CD — Integración Continua y Despliegue

Este documento describe qué automatiza realmente GitHub Actions en este repositorio y cómo funciona el despliegue a producción, que **es manual**.

> ⚠️ **Aviso de precisión**: este documento sustituye a una versión anterior que describía un workflow `.github/workflows/deploy.yml` (staging/producción vía SSH, GitHub Secrets, health checks automáticos, backups automáticos y GitHub Releases). Ese workflow **fue eliminado del repositorio** (commit `Eliminar el workflow deploy.yml, sin uso`) porque no se usaba y estaba roto: empaquetaba una carpeta `src/` que ya no existe en el proyecto. Nada de eso existe hoy. Si buscas esa funcionalidad, no la vas a encontrar porque ya no está.

## Tabla de Contenidos

- [Resumen](#resumen)
- [Workflows de GitHub Actions](#workflows-de-github-actions)
  - [1. Tests \& Coverage (`tests.yml`)](#1-tests--coverage-testsyml)
  - [2. Code Quality \& Linting (`lint.yml`)](#2-code-quality--linting-lintyml)
- [Flujo de Ramas](#flujo-de-ramas)
- [Despliegue a Producción (Manual)](#despliegue-a-producción-manual)
  - [Arquitectura servida por nginx](#arquitectura-servida-por-nginx)
  - [Pasos del despliegue manual](#pasos-del-despliegue-manual)
- [Ejecutar los Checks en Local](#ejecutar-los-checks-en-local)
- [Troubleshooting de CI](#troubleshooting-de-ci)
- [Archivos Relevantes](#archivos-relevantes)

---

## Resumen

El repositorio usa **GitHub Actions** únicamente para dos cosas:

- ✅ Ejecutar la suite de tests con pytest y comprobar un umbral de cobertura (`tests.yml`)
- ✅ Ejecutar checks de estilo/formato/seguridad (`lint.yml`)

No hay más workflows. En concreto, **no existe**:

- ❌ Ningún workflow de despliegue automático (`deploy.yml` no existe)
- ❌ Ningún entorno de staging con su propia URL
- ❌ GitHub Secrets de SSH, ni GitHub Environments configurados en el repo
- ❌ Health checks automáticos, backups automáticos, ni GitHub Releases automáticos

El despliegue a producción se hace **a mano**, por SSH, tal como se describe en [Despliegue a Producción (Manual)](#despliegue-a-producción-manual).

---

## Workflows de GitHub Actions

`.github/workflows/` contiene exactamente dos archivos: `lint.yml` y `tests.yml`.

### 1. Tests & Coverage (`tests.yml`)

**Archivo**: `.github/workflows/tests.yml`

**Se dispara en**:
- `push` a las ramas `main` o `develop`
- `pull_request` contra `main` o `develop`

> Nota: en la práctica, el flujo de trabajo real del equipo usa ramas de feature numeradas (`009-nombre-feature`, etc.) con PR contra `production`, no contra `main`/`develop` (ver [Flujo de Ramas](#flujo-de-ramas)). Esto significa que este workflow, tal como está configurado con esos nombres de rama, puede no dispararse en el flujo habitual de trabajo — **no confirmado** si esto es intencional o un desajuste pendiente de corregir.

**Qué hace**:
- Matrix de Python: `3.8`, `3.9`, `3.10`, `3.11`
- Instala `requirements.txt` + `requirements-dev.txt`
- Ejecuta:
  ```bash
  pytest tests/ -v --cov=src.converters --cov=tests \
    --cov-report=xml --cov-report=html --cov-report=term-missing \
    --cov-fail-under=80 \
    --tb=short
  ```
- **Umbral de cobertura: 80%** — si la cobertura cae por debajo, el paso de pytest falla (`--cov-fail-under=80`)
- Sube el reporte a Codecov (`codecov/codecov-action@v4`, con `fail_ci_if_error: false`, es decir, si Codecov falla no bloquea el workflow)
- Escribe un resumen de cobertura en el Job Summary de GitHub Actions
- En pull requests, comenta en el PR el % de cobertura obtenido
- Job final `test-result`: comprueba explícitamente `needs.test.result` y hace `exit 1` si los tests no fueron exitosos — este es el job que realmente actúa como gate de "todo o nada" para este workflow

No hay `pytest.ini` ni configuración de coverage en `pyproject.toml`/`setup.cfg` en la raíz del repo — el umbral del 80% está definido únicamente como flag (`--cov-fail-under=80`) dentro del propio workflow, no en un archivo de configuración compartido.

### 2. Code Quality & Linting (`lint.yml`)

**Archivo**: `.github/workflows/lint.yml`

**Se dispara en**:
- `push` a `main`, `develop` o `005-project-organization`
- `pull_request` contra `main` o `develop`

(El nombre de rama `005-project-organization` es residual de una feature branch antigua; sigue en el archivo tal cual está hoy.)

**Contiene tres jobs**:

**a) `lint`** (Lint & Format Check)
- `flake8` en modo estricto solo para errores críticos (sin `exit-zero`): `E9,F63,F7,F82` (errores de sintaxis y bugs graves). **Este paso sí puede hacer fallar el job.**
- `flake8` en modo laxo (`--exit-zero`, complejidad y longitud de línea) — informativo, nunca falla
- `black --check ... || true` — informativo, nunca falla el step
- `isort --check-only ... || true` — informativo, nunca falla el step
- `pylint --exit-zero ...` sobre `src` y `tests` — informativo, nunca falla
- Verifica sintaxis con `py_compile` (con `|| true`, tampoco bloquea)
- Sube el reporte de pylint como artifact

**b) `security`** (Security Checks)
- `bandit -r src --skip B101,B601 ...` — ambas invocaciones llevan `|| true`, por lo que **nunca hace fallar el job**, solo genera un reporte JSON como artifact

**c) `result`** (Lint Result Summary)
- Solo imprime mensajes de "completado" (`echo`) independientemente de si `lint`/`security` tuvieron warnings — **no es un gate real**, no comprueba `needs.*.result` como sí hace `tests.yml`

**En resumen**: `lint.yml` es en la práctica **casi todo informativo**. El único punto donde puede fallar (y por tanto marcar el check en rojo en el PR) es la comprobación estricta de flake8 (`E9,F63,F7,F82`) o un fallo de infraestructura (checkout/instalación de dependencias). Formato (black/isort), pylint y bandit generan advertencias visibles en los logs pero no bloquean nada.

---

## Flujo de Ramas

Basado en el historial de commits observado en el repositorio:

- Se trabaja en ramas de feature numeradas (p. ej. `009-...`, `013-portal-usability`, `014-fix-generate-dashboards-double-convert`, `017-remove-unused-deploy-workflow`)
- Cada feature branch se integra mediante **Pull Request contra la rama `production`** (el historial de `production` muestra merges de PRs como `#9`, `#10`, `#11`, `#12`, `#13`)
- La rama `main` existe en el repositorio pero **su historial ha divergido significativamente del de `production`** (commits distintos en ambas direcciones) y no recibe los merges de las PRs recientes

**No confirmado**: la relación exacta entre `main` y `production` — es decir, si `main` es una rama legacy que se dejó de usar, si se sincroniza manualmente en algún punto del ciclo de release, o si tiene algún otro propósito. Tampoco está confirmado si existe algún hook o automatismo (por ejemplo, en el VPS o vía integración de git) que reaccione a un push/merge en `production`. A falta de evidencia de que exista tal automatismo, se asume que no lo hay y que todo despliegue posterior al merge es manual (ver siguiente sección).

Por lo observado, `production` es la rama que refleja el estado que efectivamente se despliega a mano en el VPS.

---

## Despliegue a Producción (Automatizado vía deploy-production.ps1)

El despliegue a producción **no se realiza mediante GitHub Actions ni mediante `git pull` en el servidor VPS**. Se ejecuta de forma automatizada y desatendida en 1 clic desde la máquina de desarrollo de Windows sobre la rama `production`:

```powershell
.\scripts\deploy-production.ps1
```

### Arquitectura de Despliegue: Standalone Runtime

1. **Empaquetado selectivo local**:
   - Genera el artefacto `dist/release-dashboard-runtime.tar.gz` (~2.3 MB) conteniendo únicamente el código productivo (`dashboards/`, `converters/`, `scripts/`, `nginx.conf`, `requirements.txt`, `VERSION`).
   - Se excluyen suites de test, specs de desarrollo, historial `.git/` y archivos binarios pesados.
2. **Cero Git en el VPS**:
   - No se realiza `git pull`, `git clone` ni `git stash` en el servidor de producción.
   - Sin dependencias de conectividad externa entre el VPS y GitHub.
3. **Persistencia estricta y desacoplamiento de datos**:
   - Los datos dinámicos están completamente desacoplados del código en `/infocodes/var/storage/release-dashboard/` (`input/`, `output/`, `reports/`, `errors/`, `archive/`).
   - Los informes ejecutivos PPTX se almacenan de manera unificada en `/infocodes/var/storage/executive_pptx`.
   - Los logs se guardan fuera del código en `/infocodes/var/log/release-dashboard/`.
   - El despliegue mantiene enlaces simbólicos retrocompatibles en el raíz del proyecto y en cada release, protegiendo al 100% los datos históricos y garantizando cero sobreescritura accidental.
4. **Copia preventiva y rollback automático**:
   - Antes de aplicar cambios, se genera una copia en `/infocodes/var/backups/release-dashboard-application/backup_YYYYMMDD_HHMMSS.tar.gz` (rotación automática de las últimas 5 copias).
   - `nginx.conf` (que **sí está versionado en Git** y forma parte del paquete) se valida sintácticamente (`nginx -t`) antes de recargar (`nginx -s reload`). Si la sintaxis falla, se restaura automáticamente la copia previa.
5. **Sondas de salud HTTP**:
   - Al finalizar, el script ejecuta sondas de salud HTTP automáticas hacia todos los dashboards y endpoints de proxy.

### Herramientas de Operación en el Servidor

En `/infocodes/project/release-dashboard-application`:
- `./status.sh`: Comprobación de versión, sintaxis Nginx, conteo de ficheros de datos y sondas HTTP locales.
- `./rollback.sh`: Reversión inmediata a la copia de seguridad más reciente o a una específica.
- `scripts/generate-dashboards.sh`: Conversión batch periódica de CSVs vía cron.

Ver [DEPLOYMENT.md](DEPLOYMENT.md) y [scripts/README.md](../scripts/README.md) para el manual completo de despliegue.

---

## Ejecutar los Checks en Local

Para reproducir lo que corre `tests.yml` y `lint.yml` antes de abrir un PR:

```bash
# Instalar dependencias de desarrollo (pytest, pytest-cov, black, flake8, pylint, etc.)
pip install -r requirements-dev.txt

# isort y bandit no están en requirements-dev.txt; el workflow los instala aparte
pip install isort bandit

# 1. Tests con el mismo umbral de cobertura que usa tests.yml
pytest tests/ -v --cov=src.converters --cov=tests --cov-report=term-missing --cov-fail-under=80

# 2. flake8 — el subconjunto que SÍ bloquea el job de lint
flake8 src tests --count --select=E9,F63,F7,F82 --show-source --statistics

# 3. flake8 informativo (no bloquea, pero conviene revisarlo)
flake8 src tests --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

# 4. Formato y orden de imports (informativos en CI, pero mantenerlos limpios evita ruido)
black --check src tests --diff
isort --check-only src tests --diff

# 5. Análisis estático informativo
pylint src tests --disable=missing-docstring,too-many-arguments,too-few-public-methods

# 6. Seguridad (informativo en CI)
bandit -r src --skip B101,B601
```

### Auto-fix de formato

```bash
black src tests
isort src tests
```

---

## Troubleshooting de CI

### `tests.yml` falla con "Coverage below 80%" (o el step de pytest falla)

**Causa**: código nuevo sin tests suficientes, o `--cov-fail-under=80` no se alcanza.

**Solución**:
```bash
pytest tests/ --cov=src.converters --cov=tests --cov-report=html
# Abrir htmlcov/index.html y añadir tests para las líneas sin cobertura
```

### `lint.yml` marca el check en rojo

**Causa más probable**: el paso estricto de flake8 (`E9,F63,F7,F82`) encontró un error de sintaxis o un bug grave (por ejemplo, uso de una variable no definida). Es el único paso de `lint.yml` que no tiene `|| true` ni `--exit-zero`.

**Solución**:
```bash
flake8 src tests --count --select=E9,F63,F7,F82 --show-source --statistics
```
Corrige lo que reporte ese comando. Las advertencias de black/isort/pylint/bandit en los logs de `lint.yml` son informativas y no son la causa de que el check falle.

### El PR no arranca ningún workflow

**Causa posible**: el PR va contra una rama distinta de `main`/`develop` (por ejemplo, contra `production`), que es justo el patrón real de trabajo descrito en [Flujo de Ramas](#flujo-de-ramas). Como ambos workflows solo escuchan `pull_request` contra `main`/`develop`, un PR contra `production` no los dispara.

**No confirmado**: si esto es un problema real detectado por el equipo o si en la práctica los PRs sí acaban disparando los workflows por algún otro motivo (por ejemplo, si la rama de feature también coincide en algún push a `main`). Se documenta la discrepancia de configuración tal como está en los archivos hoy.

### Dudas sobre el despliegue manual

No hay workflow que ayude a diagnosticar esto — al ser un procedimiento manual por SSH, cualquier problema (proceso caído, nginx mal configurado, permisos) se depura directamente en el VPS con las herramientas habituales (`journalctl`, `pm2 logs`, `nginx -t`, revisar `error_log`/`access_log` definidos en `nginx.conf`).

---

## Archivos Relevantes

| Archivo | Propósito |
|---------|-----------|
| `.github/workflows/tests.yml` | Ejecuta pytest con matrix de Python 3.8–3.11 y exige 80% de cobertura |
| `.github/workflows/lint.yml` | Ejecuta flake8 (estricto + informativo), black, isort, pylint y bandit (mayormente informativos) |
| `requirements.txt` | Dependencias de producción (mínimas: solo `python-dotenv`) |
| `requirements-dev.txt` | Dependencias de desarrollo/test (pytest, pytest-cov, black, flake8, pylint, pre-commit, python-dotenv) |
| `VERSION` | Número de versión del proyecto (actualmente `0.2.0`); no está ligado a ningún proceso de release automático |
| `nginx.conf` | Configuración real de nginx para este entorno (no versionada en git, solo presente en local/VPS) |

**Última actualización**: 2026-07-09
