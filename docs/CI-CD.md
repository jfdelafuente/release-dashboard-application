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

## Workflows

### 1. Tests & Coverage (`tests.yml`)

**Trigger**: Every push and pull request  
**Purpose**: Run automated tests with 80% coverage enforcement

**Features**:
- Matrix testing: Python 3.8, 3.9, 3.10, 3.11
- Coverage reporting (XML, HTML)
- Uploads to Codecov
- Comments on PR with coverage %

**Requirement**: Coverage >= 80% (blocks merge if below)

### 2. Code Quality & Linting (`lint.yml`)

**Trigger**: Every push and pull request  
**Purpose**: Enforce code style and security standards

**Checks**:
- flake8 (PEP 8 style)
- black (code formatting)
- isort (import organization)
- pylint (code analysis)
- bandit (security scanning)

### 3. Deployment Pipeline (`deploy.yml`)

**Trigger**: Auto on merge to main, manual for production  
**Purpose**: Automated staging deployment + manual production approval

**Flow**:
1. Build & create artifact
2. Auto-deploy to staging
3. Run health checks
4. Request production approval
5. Manual deploy to production (requires approval)

---

## Local Testing

```bash
# Run tests with coverage
pytest tests/ --cov --cov-fail-under=80

# Run linting
flake8 src tests
black --check src tests
isort --check-only src tests

# Auto-fix formatting
black src tests
isort src tests
```

---

**Last Updated**: 2026-05-14
