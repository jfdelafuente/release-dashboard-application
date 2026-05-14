# Deployment Guide: Safe Production Deployments

Complete step-by-step procedures for safe, auditable deployments with rollback capability.

---

## Quick Reference

**Staging** (automatic on main merge):
```bash
# No action needed - CI/CD handles it
```

**Production** (manual):
```bash
./scripts/deploy/deploy.sh production
```

**Rollback** (if needed):
```bash
./scripts/deploy/rollback.sh production
```

---

## Pre-Deployment Checklist

✅ **Code**:
- [ ] Tests pass: `pytest tests/ --cov --cov-fail-under=80`
- [ ] PR reviewed and approved
- [ ] Merged to `main` branch
- [ ] VERSION updated

✅ **Infrastructure**:
- [ ] SSH access verified
- [ ] Disk space available (> 5GB)
- [ ] Previous deployment stable

---

## Deployment Stages

### 1. Pre-Deployment Checks
- Runs full test suite
- Enforces 80%+ coverage
- Verifies git status
- Creates backup

### 2. Artifact Creation
```
dist/release-dashboard-{version}-{timestamp}.tar.gz
```

### 3. Deployment
- Upload to VPS via SSH
- Extract and deploy
- Install dependencies

### 4. Health Checks
- Python environment
- Converter functionality
- Dashboard files
- HTTP endpoints

---

## How to Deploy

### Staging (Automatic)

Merge PR to `main` → CI/CD runs tests → Auto-deploys to staging

Monitor:
- GitHub Actions tab
- logs/deployments/deployment-staging-*.log

### Production (Manual)

```bash
./scripts/deploy/deploy.sh production
```

Script will:
1. Run pre-checks (tests, coverage)
2. Create artifact
3. Backup current
4. Deploy to VPS
5. Run post-checks
6. Log everything

---

## Rollback

**Automatic**: Triggers if health checks fail post-deployment

**Manual**:
```bash
./scripts/deploy/rollback.sh production
```

Restores previous version from backup.

---

## Logs

Automatically created:

```
logs/deployments/
├── deployment-{env}-{timestamp}.log     # Detailed log
└── DEPLOYMENT-RECORDS.log               # Master audit trail
```

Query examples:
```bash
# All production deployments
grep "Environment:     production" logs/deployments/DEPLOYMENT-RECORDS.log

# Failed deployments
grep "Status:          FAILED" logs/deployments/DEPLOYMENT-RECORDS.log
```

---

## Production Readiness Checklist

**Use this checklist before your first production deployment to ensure all systems are configured correctly.**

### Infrastructure Setup
- [ ] VPS provisioned and accessible via SSH
- [ ] Nginx configured to serve static files from `/var/www/release-dashboard/static/`
- [ ] Python 3.6+ installed on VPS
- [ ] Firewall rules allow HTTP (80) and HTTPS (443)
- [ ] SSL certificate installed (if using HTTPS)
- [ ] SSH key authentication configured (no password login)
- [ ] Disk space available: ≥10GB for application and data

### Code & Configuration
- [ ] VERSION file created with semantic version (e.g., 0.2.0)
- [ ] Git repository initialized and main branch protected
- [ ] GitHub Secrets configured (SSH_PRIVATE_KEY, PRODUCTION_HOST, PRODUCTION_USER, PRODUCTION_PORT)
- [ ] .env.example created with all required variables
- [ ] .env protected in .gitignore (never commit secrets)
- [ ] requirements.txt and requirements-dev.txt up to date

### Testing & Quality Gates
- [ ] All unit tests pass: `pytest tests/ --cov --cov-fail-under=80`
- [ ] Code coverage ≥80%
- [ ] Linting passes: `flake8`, `black`, no syntax errors
- [ ] pre-commit hooks installed (optional but recommended)
- [ ] pytest.ini configured with coverage thresholds

### Deployment Scripts
- [ ] scripts/deploy/deploy.sh is executable and can be run from project root
- [ ] scripts/deploy/rollback.sh is executable
- [ ] scripts/health-check.sh is executable
- [ ] scripts/bin/convert_incidents.sh and convert_postmortems.sh are executable
- [ ] All scripts have correct file permissions (755)

### GitHub Actions CI/CD
- [ ] .github/workflows/tests.yml validates on every PR
- [ ] .github/workflows/lint.yml validates code style
- [ ] .github/workflows/deploy.yml can deploy to staging/production
- [ ] Branch protection enabled on `main` (requires 1+ approval)
- [ ] Status checks configured (test, lint required before merge)
- [ ] GitHub Actions logs accessible and comprehensible

### Documentation
- [ ] docs/QUICKSTART.md complete and tested (should take <30 min)
- [ ] docs/DEPLOYMENT.md complete with all procedures
- [ ] docs/VERSION-MANAGEMENT.md explains versioning policy
- [ ] SECURITY.md documents secret handling
- [ ] CONTRIBUTING.md explains development process
- [ ] README.md points to all key documentation

### Monitoring & Logging
- [ ] logs/deployments/ directory created and writable
- [ ] Deployment logs are being recorded (DEPLOYMENT-RECORDS.log)
- [ ] Health checks produce readable output
- [ ] Monitoring dashboard configured (optional but recommended)
- [ ] Alert system configured for failed deployments (optional)

### Data Management
- [ ] data/input/ directory exists and is writable
- [ ] data/output/ directory exists and is writable
- [ ] data/errors/ directory exists and is writable
- [ ] data/ is protected in .gitignore (no accidental commits)
- [ ] Dashboard can auto-load JSON from data/output/index.json
- [ ] Backup strategy documented (30-day retention in backups/)

### Rollback Capability
- [ ] Rollback script tested in staging
- [ ] Previous version backups are available and valid
- [ ] Rollback duration is <5 minutes
- [ ] Health checks verify rollback success
- [ ] Team knows how to initiate rollback if needed

### Post-Deployment
- [ ] All dashboards load correctly
- [ ] KPIs display real-time data
- [ ] CSV conversion works end-to-end
- [ ] Health checks show all green
- [ ] Logs are being written to deployment records
- [ ] Team notified of deployment completion

### Final Sign-Off
- [ ] All checklist items completed
- [ ] First production deployment executed successfully
- [ ] Rollback tested and working
- [ ] Team trained on deployment procedures
- [ ] Incident response procedure documented

**Sign-off date**: _________
**Signed by**: _________

---

**Last Updated**: 2026-05-14
