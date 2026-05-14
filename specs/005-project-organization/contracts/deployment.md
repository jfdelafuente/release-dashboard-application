# Contract: Deployment Process

**Type**: Operational Contract  
**Version**: 1.0  
**Owner**: Operations Team

## Purpose

Define safe, auditable, and reversible deployments to production.

## Inputs

- Merged PR on main branch with semantic version bump
- CI/CD pipeline passed (all tests, linting, coverage >= 80%)
- Deployment approval (manual approval step)

## Deployment Process

### Pre-Deployment

1. ✅ Read VERSION file for version number
2. ✅ Verify CI/CD passed for commit being deployed
3. ✅ Get approval from team lead or designated reviewer
4. ✅ Create backup of current production state
5. ✅ Prepare rollback procedure

### Deployment

1. Execute deployment script: `./scripts/deploy.sh <environment> <version>`
2. Script performs:
   - Check environment variables are set
   - Load configuration for target environment
   - Run health checks (DB connection, API endpoints)
   - Deploy code (update files or containers)
   - Run smoke tests (basic functionality)
   - Update VERSION in production
3. Record deployment in log:
   - Timestamp
   - Version deployed
   - Deployer name
   - Duration
   - Previous version

### Post-Deployment

1. ✅ Verify application is responding (HTTP 200 on health endpoint)
2. ✅ Check key functionality (can load incidents, filters work)
3. ✅ Monitor error rates (Sentry, CloudWatch, logs)
4. ✅ Send notification to team

## Outputs

### Success
- ✅ Application running in production
- ✅ Deployment log entry created
- ✅ Version updated
- ✅ Notification sent to team

**Information Logged**:
- Timestamp (ISO8601)
- Version deployed (semantic version)
- Previous version (for rollback)
- Deployer ID
- Deployment duration
- Commit hash deployed

### Failure
- ❌ Deployment halted
- ❌ Rollback to previous version initiated
- ❌ Error details logged
- ❌ Alert sent to team

**Recovery**:
- Automatic or manual rollback to previous version
- Health checks verify rollback success
- Root cause analysis required before retry

## Rollback Procedure

**Rollback Time**: < 5 minutes from decision to previous version running

```
./scripts/rollback.sh <version>
```

1. Verify previous version is available
2. Stop current application
3. Restore previous version code
4. Restore previous version database (if needed)
5. Start application
6. Run health checks
7. Log rollback event with reason

## Timeline

| Phase | Expected Duration |
|-------|-------------------|
| Pre-deployment checks | 5-10 min |
| Deployment execution | 10-15 min |
| Health checks | 5 min |
| Team notification | 1 min |
| **Total** | **25-30 min** |

## Approval & Audit

**Approval Required For**:
- All production deployments (no auto-deploy)
- Any rollback
- Emergency patches (expedited, but still logged)

**Audit Trail**:
- All deployments logged to deployment log
- Log includes timestamp, version, deployer, result
- Logs retained for 1 year (compliance)
- Inaccessible to developers (audit integrity)

## Environment-Specific Details

### Development
- Auto-deploy on commit to dev branch
- No approval required
- Health checks optional

### Staging
- Manual deploy trigger
- Approval by QA lead
- Full health checks required

### Production
- Manual deploy trigger
- Approval by team lead + one other reviewer
- All health checks + smoke tests required
- Rollback procedure tested weekly

## Safety Rails

- ❌ Cannot deploy without passing CI/CD
- ❌ Cannot deploy without approval
- ❌ Cannot rollback without logging reason
- ❌ Cannot change VERSION in code (use semantic versioning)
- ❌ Cannot deploy from feature branches (only main)

## Responsible Systems

- **Trigger**: GitHub (deployment action)
- **Executor**: GitHub Actions or equivalent CI/CD
- **Approval**: GitHub required review
- **Logging**: Deployment log (external service or GitHub logs)
- **Notification**: Slack, email, or GitHub notification
