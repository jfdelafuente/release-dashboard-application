# Deployment Guide

Complete guide for deploying Release Dashboard Application to different environments.

## Deployment Architecture

```
Development (Local)
  └─ .env file (git-ignored)
     └─ Python venv + local dependencies

Staging (GitHub Actions)
  └─ GitHub Secrets (environment variables)
     └─ Auto-deploy on main merge
     └─ Full health checks

Production (GitHub Actions)
  └─ GitHub Secrets (environment variables)
     └─ Manual approval required
     └─ Audit logging
     └─ Rollback capability
```

## Environment Variables

### Development (.env file)

Copy template and configure:
```bash
cp config/.env.example .env
```

See [config/.env.development](../config/.env.development) for development defaults.

### Staging & Production (GitHub Secrets)

Set in GitHub repository settings → Secrets:
- `APP_ENV`: `staging` or `production`
- `DATABASE_URL`: Connection string (if using database)
- `LOG_LEVEL`: `warning` (production) or `info` (staging)
- `DEBUG`: `False` (never `True` in prod)

**WARNING**: Never hardcode production secrets in repository. Use GitHub Secrets exclusively.

## Local Deployment (Development)

### Step 1: Configure Environment

```bash
cp config/.env.example .env
# Edit .env with your development settings
```

### Step 2: Install Dependencies

```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate
pip install -r requirements.txt
```

### Step 3: Start Application

```bash
python -m http.server 8000
```

Visit: http://localhost:8000

## Staging Deployment

Staging deploys **automatically** on every merge to `main`:

1. **Create pull request** with your changes
2. **Pass CI/CD checks**:
   - All tests pass (pytest)
   - Code quality (flake8, pylint)
   - Coverage ≥ 80%
3. **Get approved** and merge to main
4. **GitHub Actions** automatically deploys to staging

Monitor staging deployment:
- GitHub Actions tab → see workflow execution
- Check staging environment (URL provided in deployment logs)

## Production Deployment

Production requires **manual approval**:

### Pre-Deployment Checklist

- [ ] Code merged to main
- [ ] All tests passing (≥80% coverage)
- [ ] Code reviewed and approved
- [ ] CHANGELOG.md updated
- [ ] VERSION file updated with new semantic version
- [ ] Release notes prepared

### Deployment Steps

1. **Navigate to GitHub Actions**:
   - Go to "Actions" tab
   - Select "Deploy" workflow
   - Click "Run workflow"

2. **Select deployment parameters**:
   - Environment: `production`
   - Version: (should match VERSION file)

3. **Review pre-deployment checks**:
   - Database migrations (if needed)
   - Configuration compatibility
   - Backup creation

4. **Approve deployment**:
   - Wait for approval prompt
   - Review changes and impact
   - Approve if everything looks good

5. **Monitor deployment**:
   - GitHub Actions shows real-time progress
   - Deployment logs display start/end time
   - Health checks verify success

6. **Post-deployment validation**:
   - Verify application responding (HTTP 200)
   - Test critical features
   - Monitor error rates
   - Notify team of completion

### Rollback Procedure

If deployment fails or causes issues:

```bash
# Automatic rollback (if health checks fail)
# System automatically reverts to previous version

# Manual rollback (if issue detected post-deployment)
./scripts/deploy/rollback.sh <previous-version>
```

Examples:
```bash
./scripts/deploy/rollback.sh 0.1.0  # Rollback to v0.1.0
./scripts/deploy/rollback.sh        # Rollback to previous version
```

**Rollback time**: < 5 minutes from decision to previous version running

## Version Management

### Semantic Versioning

Format: `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes (e.g., 1.0.0 → 2.0.0)
- **MINOR**: New features, backward compatible (e.g., 0.1.0 → 0.2.0)
- **PATCH**: Bug fixes only (e.g., 0.1.0 → 0.1.1)

### Updating Version

1. Edit [VERSION](../VERSION) file:
   ```
   0.2.0
   ```

2. Update [CHANGELOG.md](../CHANGELOG.md) with release notes

3. Commit changes:
   ```bash
   git commit -m "chore: bump version to 0.2.0"
   ```

4. Create git tag:
   ```bash
   git tag v0.2.0
   git push origin v0.2.0
   ```

## Deployment Logging

All deployments are logged with:
- Timestamp (ISO8601 format)
- Version deployed
- Deployer (GitHub Actions automation or user)
- Status (success, rolled_back, failed)
- Duration
- Error details (if failed)

Access logs:
- GitHub Actions artifacts
- CloudWatch (if using AWS)
- Sentry (if configured for error tracking)

## Health Checks

Post-deployment health checks verify:

1. **Application responding**:
   - HTTP 200 on main endpoint
   - Response time < 2 seconds

2. **Core functionality**:
   - CSV converter can execute
   - Dashboard loads with sample data
   - API endpoints respond correctly

3. **Environment configuration**:
   - All required environment variables set
   - Database connections working (if applicable)
   - External services reachable

## Monitoring & Alerts

After deployment, monitor:

- **Error rate**: Should return to baseline within 5 minutes
- **Performance**: Response times should be < 2 seconds
- **Availability**: All critical endpoints should respond
- **Logs**: Check for errors or warnings in deployment logs

Configure alerts for:
- Deployment failures
- High error rates post-deployment
- Performance degradation
- Health check failures

## Troubleshooting

### Deployment Fails

1. Check GitHub Actions logs for error details
2. Verify all tests pass locally: `pytest tests/ -v --cov=src`
3. Verify environment variables are set in GitHub Secrets
4. Check database migrations completed (if applicable)
5. Manual rollback if necessary: `./scripts/deploy/rollback.sh`

### Health Checks Failing

1. Verify application logs: `docker logs <container>` (if using Docker)
2. Check connectivity to external services
3. Verify environment variables are correct
4. Test locally with production config (using GitHub Secrets values locally)

### Rollback Not Working

1. Verify previous version is still available
2. Check permissions for running rollback script
3. Verify database rollback procedures (if data migrations occurred)
4. Contact infrastructure team if issue persists

## Security

### Secrets Management

- **Development**: Use local `.env` file (git-ignored)
- **Production**: Use GitHub Secrets (never in code)
- **Rotation**: Rotate secrets regularly (at least quarterly)
- **Access**: Limit who can approve production deployments

### Deployment Approval

- Minimum 1 reviewer for production deployments
- Require green CI/CD pipeline
- Block auto-merge until approval granted
- Log all deployments for audit trail

## Configuration by Environment

| Setting | Development | Staging | Production |
|---------|-------------|---------|------------|
| DEBUG | True | False | False |
| LOG_LEVEL | debug | info | warning |
| CACHE_TTL | 60 | 300 | 3600 |
| DATABASE | SQLite | PostgreSQL | PostgreSQL |
| Secrets | .env file | GitHub Secrets | GitHub Secrets |
| Health Checks | Optional | Required | Required |
| Approval Required | No | No | Yes |

## Deployment Calendar

- **Staging**: Auto-deploys on every merge to main (continuous deployment)
- **Production**: Manual deployments, business hours recommended
- **Hotfixes**: Can deploy outside hours if critical, but still requires approval

Suggested production deployment times:
- During business hours (9am-5pm)
- Off-peak times to minimize user impact
- Never during critical business periods

## Related Documentation

- [CI-CD.md](CI-CD.md) - GitHub Actions workflow documentation
- [SECURITY.md](../SECURITY.md) - Security practices
- [CHANGELOG.md](../CHANGELOG.md) - Release history
- [contracts/deployment.md](../specs/005-project-organization/contracts/deployment.md) - Detailed deployment contract

---

**Last Updated**: 2026-05-14
