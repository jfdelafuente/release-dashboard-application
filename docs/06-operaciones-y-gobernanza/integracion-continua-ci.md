# CI — Integración Continua y Pipeline de Calidad

Este documento describe la automatización de **Integración Continua (CI)** mediante GitHub Actions en este repositorio, los controles de calidad exigidos para fusionar cambios y cómo ejecutar estas validaciones en local.

> ℹ️ **Sobre el Despliegue (CD)**:
> Este repositorio **no realiza despliegues continuos automáticos desde GitHub Actions** hacia el VPS.
> El despliegue a producción se realiza en 1 clic desde la estación de desarrollo con el script automatizado [`scripts/deploy-production.ps1`](../../scripts/deploy-production.ps1). Consulta la arquitectura y operativa completa en [**`DEPLOYMENT.md`**](despliegue-vps.md).

---

## 1. Resumen de GitHub Actions

El repositorio ejecuta automáticamente dos workflows en GitHub Actions ante cada `push` o `pull_request` sobre las ramas principales (`production` y `main`):

| Workflow | Archivo | Triggers | Entorno | Qué valida | Gate bloqueante |
|---|---|---|---|---|---|
| **Tests & Coverage** | `.github/workflows/tests.yml` | `push`, `pull_request` a `main`, `production` | Ubuntu / Python 3.11 | Tests unitarios e integración con pytest + cobertura de código | **SÍ**: falla si algún test falla o si la cobertura cae por debajo del 80% (`fail_under = 80`) |
| **Code Quality & Linting** | `.github/workflows/lint.yml` | `push`, `pull_request` a `main`, `production` | Ubuntu / Python 3.10 | Estilo (flake8), formato (black), imports (isort), análisis estático (pylint), seguridad (bandit) | **SÍ**: falla ante errores críticos de sintaxis o bugs severos (`flake8 E9,F63,F7,F82`) |

---

## 2. Detalle de Workflows

### 2.1 Tests & Coverage (`tests.yml`)
- **Directorio de trabajo**: `converters/`
- **Entorno**: Ubuntu Latest con Python 3.11 y caché de paquetes `pip`.
- **Pasos**:
  1. Instala dependencias desde `converters/requirements.txt` y `converters/requirements-dev.txt`.
  2. Ejecuta `pytest tests/ -v --cov=src` respetando la configuración centralizada en [`converters/pytest.ini`](../../converters/pytest.ini).
  3. **Umbral de cobertura (80%)**: Exige un mínimo del **80%** de cobertura en el código productivo de conversores. Si no se alcanza, el job falla (`exit 1`).
  4. Genera informe en el Job Summary y publica un comentario automático en el Pull Request con el porcentaje de cobertura obtenido.
  5. Sube métricas a Codecov (`codecov-action@v4`).

### 2.2 Code Quality & Linting (`lint.yml`)
- **Directorio de trabajo**: `converters/` sobre los módulos `src`, `cli` y `tests`.
- **Jobs**:
  - **`lint`**:
    - **Paso bloqueante**: `flake8 src cli tests --select=E9,F63,F7,F82` (falla si hay errores de sintaxis, variables no definidas o excepciones mal estructuradas).
    - **Pasos informativos**: `flake8` laxo (complejidad ciclomática y longitud de línea), `black --check`, `isort --check-only`, `pylint` y comprobación de sintaxis con `py_compile`. Sube el reporte `pylint-report.txt` como artefacto.
  - **`security`**:
    - Análisis estático de vulnerabilidades con `bandit -r src cli --skip B101,B601`. Sube `bandit-report.json` como artefacto.
  - **`result`**:
    - Resumen final informativo de validaciones.

---

## 3. Flujo de Ramas y Promoción

- **Desarrollo**: Se trabaja en ramas de feature numeradas (p. ej. `018-feature-name`, etc.).
- **Pull Requests**: Se abren contra la rama **`production`**.
- Al abrir o actualizar el PR, GitHub Actions ejecuta automáticamente `tests.yml` y `lint.yml`.
- **Condición para Merge**:
  1. Todos los tests deben pasar exitosamente (cero fallos).
  2. Cobertura $\ge$ 80%.
  3. Flake8 estricto sin violaciones de sintaxis ni bugs.
- **Despliegue tras Merge**: Una vez integrado el PR en `production`, el despliegue al VPS se realiza ejecutando `.\scripts\deploy-production.ps1` desde Windows (ver [`DEPLOYMENT.md`](despliegue-vps.md)).

---

## 4. Ejecutar las Validaciones en Local (Antes del PR)

Para evitar rechazos en el CI, ejecuta los mismos checks en tu máquina antes de hacer push:

```powershell
# 1. Situarse en la carpeta converters
cd converters

# 2. Instalar dependencias de desarrollo
pip install -r requirements-dev.txt
pip install isort bandit

# 3. Ejecutar la suite completa de tests y cobertura
pytest

# 4. Comprobación estricta de flake8 (lo que bloquea el CI)
flake8 src cli tests --count --select=E9,F63,F7,F82 --show-source --statistics

# 5. Formateo y orden de imports automático
black src cli tests
isort src cli tests

# 6. Análisis de seguridad
bandit -r src cli --skip B101,B601
```

---

## 5. Troubleshooting de Fallos en CI

### ❌ `tests.yml` falla con "Coverage below 80%" o error en tests
- **Causa**: Se ha añadido o modificado código en `converters/src/` sin sus correspondientes tests unitarios, o la cobertura global descendió del 80%.
- **Solución**:
  ```powershell
  cd converters
  pytest --cov-report=html
  # Abre htmlcov/index.html en el navegador para localizar las líneas sin cobertura
  ```

### ❌ `lint.yml` falla en el paso estricto de flake8
- **Causa**: El paso estricto detectó un error de sintaxis, variable no definida (`F821`), import circular o error estructural severo.
- **Solución**:
  ```powershell
  cd converters
  flake8 src cli tests --select=E9,F63,F7,F82 --show-source
  ```
  Corrige los avisos reportados y vuelve a subir los cambios.

### ❓ ¿Por qué mi PR no realiza el despliegue automático en el VPS?
- Como se indica arriba, el despliegue a producción **no es automático por GitHub Actions**. Se realiza mediante el comando operativo local:
  ```powershell
  .\scripts\deploy-production.ps1
  ```
  Consulta [`DEPLOYMENT.md`](despliegue-vps.md) para más detalles.

---

## 6. Archivos Relevantes de CI

| Archivo | Propósito |
|---|---|
| [`.github/workflows/tests.yml`](../../.github/workflows/tests.yml) | Workflow de ejecución de tests unitarios y validación de cobertura 80% |
| [`.github/workflows/lint.yml`](../../.github/workflows/lint.yml) | Workflow de linter, formato, análisis de seguridad y calidad de código |
| [`converters/pytest.ini`](../../converters/pytest.ini) | Configuración de pytest, marcadores y umbral de cobertura (`fail_under = 80`) |
| [`converters/requirements.txt`](../../converters/requirements.txt) | Dependencias de producción del entorno de conversores |
| [`converters/requirements-dev.txt`](../../converters/requirements-dev.txt) | Herramientas de test y linter (pytest, pytest-cov, black, flake8, pylint) |
| [`docs/DEPLOYMENT.md`](despliegue-vps.md) | Guía oficial del despliegue a producción |
| [`nginx.conf`](../../nginx.conf) | Configuración de Nginx versionada y sincronizada al VPS |
