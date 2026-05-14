# CI/CD Pipeline

Continuous Integration and Continuous Deployment documentation for the Release Dashboard Application.

## Overview

The CI/CD pipeline automates testing, linting, and deployment using GitHub Actions. Every pull request automatically runs tests and code quality checks before merging to main.

## Pipeline Workflow

```
Developer Push
    ↓
GitHub Actions Triggered
    ├─ Run pytest (80% coverage required)
    ├─ Run flake8 linting
    ├─ Run pylint checks
    └─ Run code formatting (black)
    ↓
All Checks Pass?
    ├─ YES → Allow PR merge
    └─ NO → Block PR, require fixes
    ↓
PR Merged to Main
    ├─ Auto-deploy to staging
    └─ Run health checks
    ↓
Manual Approval for Production?
    ├─ YES → Deploy to production
    └─ NO → Stop (staging only)
    ↓
Post-Deployment
    ├─ Run smoke tests
    ├─ Log deployment
    └─ Notify team
```

## GitHub Actions Workflows

### 1. tests.yml - Testing & Coverage

**Trigger**: Every push to any branch, every PR

**Actions**:
- Run `pytest` with minimum 80% coverage requirement
- Generate coverage report (HTML)
- Fail if coverage drops below 80%

**Command**:
```bash
python -m pytest tests/ --cov=csv_to_json --cov-fail-under=80
```

**Status Badge**:
```markdown
![Tests](https://github.com/YOUR_ORG/release-dashboard/actions/workflows/tests.yml/badge.svg)
```

### 2. lint.yml - Code Quality

**Trigger**: Every push to any branch, every PR

**Actions**:
- Run `flake8` for style validation
- Run `pylint` for code analysis
- Run `black` to check code formatting

**Commands**:
```bash
flake8 src/ tests/
pylint src/
black --check src/ tests/
```

**Status Badge**:
```markdown
![Lint](https://github.com/YOUR_ORG/release-dashboard/actions/workflows/lint.yml/badge.svg)
```

### 3. deploy.yml - Automated Deployment

**Trigger**: Merge to main branch

**Actions**:
1. Auto-deploy to staging environment
2. Run health checks on staging
3. Wait for manual approval for production
4. Deploy to production (if approved)
5. Log deployment with timestamp

**Status Badge**:
```markdown
![Deploy](https://github.com/YOUR_ORG/release-dashboard/actions/workflows/deploy.yml/badge.svg)
```

## Configuration Files

### .github/workflows/tests.yml

```yaml
name: Tests & Coverage

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - run: pip install -r requirements-dev.txt
      - run: python -m pytest --cov=csv_to_json --cov-fail-under=80
```

### .github/workflows/lint.yml

```yaml
name: Lint & Format

on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - run: pip install -r requirements-dev.txt
      - run: flake8 src/ tests/
      - run: pylint src/
      - run: black --check src/ tests/
```

## Requirements for PR Merge

For a PR to be merged to main, all of the following must pass:

1. ✅ All tests pass (pytest)
2. ✅ Code coverage ≥ 80%
3. ✅ No style violations (flake8)
4. ✅ No linting errors (pylint)
5. ✅ Code is properly formatted (black)
6. ✅ At least 1 approving review
7. ✅ Branch is up to date with main

## Deployment Process

### Staging Deployment

Automatically triggered when code is merged to main:

1. Create staging artifact from main branch
2. Deploy to staging environment
3. Run health checks:
   - HTTP 200 on dashboard endpoints
   - Converter can execute test CSV
   - All database migrations pass
4. Post result in PR

### Production Deployment

Manual approval required. Only available after staging passes:

1. Create production artifact
2. Request approval from team lead
3. Wait for approval (timeout: 24 hours)
4. If approved:
   - Pre-deployment checks (disk space, backups)
   - Deploy new version
   - Run health checks
   - Log deployment with timestamp, version, deployer
5. If not approved:
   - Cancel deployment
   - Document reason

### Rollback

In case of issues in production:

```bash
./scripts/deploy/rollback.sh <previous-version>
```

Rollback checks:
- Verify previous version exists
- Stop current application
- Restore previous version
- Run health checks
- Verify application is responding
- Log rollback with timestamp and reason

## Local Testing

Before pushing, run checks locally:

```bash
# Run all tests
python -m pytest tests/

# Check coverage
python -m pytest --cov=csv_to_json tests/

# Check style
flake8 src/ tests/
pylint src/
black --check src/ tests/

# Auto-format code
black src/ tests/
```

## GitHub Secrets

The following secrets must be configured in GitHub repository settings:

- `DEPLOY_KEY`: Private key for deployment server access
- `STAGING_SERVER_URL`: Staging environment URL
- `PRODUCTION_SERVER_URL`: Production environment URL
- `LOG_WEBHOOK_URL`: Slack webhook for deployment notifications (optional)

## Troubleshooting

### Tests Failing Locally but Passing in CI

**Cause**: Different Python version or missing dependencies

**Solution**:
```bash
# Update dependencies
pip install -r requirements-dev.txt

# Check Python version
python --version  # Should be 3.10+

# Run pytest verbose
python -m pytest -v tests/
```

### Coverage Drops Below 80%

**Cause**: New code without tests

**Solution**:
1. Write tests for new functionality in `tests/`
2. Ensure tests cover all code paths
3. Verify coverage locally: `python -m pytest --cov=csv_to_json --cov-report=html`
4. Run coverage report: `open htmlcov/index.html`

### Linting Errors

**Cause**: Code style violations

**Solution**:
```bash
# Auto-fix formatting
black src/ tests/

# Fix simple style issues
flake8 --select=E501 --show-source  # Line too long

# Run pylint for detailed analysis
pylint src/
```

### Deployment Fails

**Check logs**:
1. Go to GitHub Actions tab
2. Click on failed workflow
3. Expand "Deploy" step
4. Review logs for error details

**Common issues**:
- Missing environment variables (check GitHub Secrets)
- Database migration failure (check SQL scripts)
- Health check timeout (check server connectivity)

## References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [pytest Documentation](https://docs.pytest.org/)
- [flake8 Documentation](https://flake8.pycqa.org/)
- [pylint Documentation](https://pylint.pycqa.org/)
- [black Documentation](https://black.readthedocs.io/)

---

**Last Updated**: 2026-05-14
