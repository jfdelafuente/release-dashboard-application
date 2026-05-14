# Secret Management Documentation

Guide to managing secrets in development, staging, and production environments.

## Overview

Secrets (API keys, passwords, tokens) are managed differently per environment to balance security and developer convenience.

## Development

### Storage: `.env` file (git-ignored)

**Location**: `${PROJECT_ROOT}/.env` (not in code repository)

**Example**:
```bash
APP_ENV=development
DEBUG=True
DATABASE_URL=sqlite:///incidents.db
API_KEY=test-key-12345
LOG_LEVEL=debug
```

### Setup

```bash
# Copy template
cp config/.env.example .env

# Edit with your local values
# editor .env

# Load into shell session
source .env  # or: export $(cat .env | xargs)
```

### Safety

- ✅ Automatically git-ignored (in .gitignore)
- ✅ Pre-commit hook prevents accidental commits
- ✅ Safe to store test credentials
- ✅ Can be easily reset or shared within team
- ❌ Never use production values here

### Rotation

- Change values as needed for testing
- No coordination required (local only)
- Can be different per developer

## Staging

### Storage: GitHub Secrets + `config/.env.staging` (git-ignored)

**Location**: GitHub repository settings → Secrets

**Setup**:
1. Go to repository settings
2. Click "Secrets" in sidebar
3. Create secrets for staging environment:
   - `STAGING_DATABASE_URL`
   - `STAGING_API_KEY`
   - `STAGING_LOG_LEVEL`

**Automatic Injection**:
```yaml
# In GitHub Actions workflow
- name: Deploy to Staging
  env:
    DATABASE_URL: ${{ secrets.STAGING_DATABASE_URL }}
    API_KEY: ${{ secrets.STAGING_API_KEY }}
  run: ./scripts/deploy/deploy.sh staging
```

### Local Testing with Staging Config

If needed locally (not recommended):
```bash
# Copy staging config (git-ignored)
cp config/.env.example config/.env.staging

# Edit with staging values (careful!)
# editor config/.env.staging

# Load for testing:
source config/.env.staging
```

### Rotation

- Rotate monthly (staging test keys)
- Use different values than production
- Smaller blast radius if compromised

## Production

### Storage: GitHub Secrets (ONLY - never elsewhere)

**Location**: GitHub repository settings → Secrets

**Critical**: Production secrets ONLY in GitHub Secrets. Nowhere else.

### Setup

1. Go to repository settings
2. Click "Secrets" in sidebar
3. Create secrets for production:
   - `PROD_DATABASE_URL` (production database)
   - `PROD_API_KEY` (production API credentials)
   - `PROD_LOG_LEVEL` (warning level in prod)
   - Any other production-specific variables

### Access Control

Only authorized deployment workflows can read these secrets:

```yaml
# .github/workflows/deploy.yml
- name: Deploy to Production
  if: github.event_name == 'workflow_dispatch'  # Manual trigger only
  env:
    DATABASE_URL: ${{ secrets.PROD_DATABASE_URL }}
    API_KEY: ${{ secrets.PROD_API_KEY }}
  run: ./scripts/deploy/deploy.sh production
```

### Security Rules

- ❌ Never use production secrets locally
- ❌ Never commit to git (GitHub Secrets prevents this)
- ❌ Never share in chat, email, or non-secure channels
- ❌ Never log or display values
- ✅ Rotate regularly (monthly minimum)
- ✅ Restrict access (admins only)
- ✅ Audit access logs
- ✅ Document all rotations

### Rotation Procedure

**Monthly or as needed**:

1. **Generate new credentials**:
   - Create new API key (if applicable)
   - Reset database password
   - Generate new tokens

2. **Update in GitHub Secrets**:
   ```bash
   # Go to Settings → Secrets
   # Edit existing secret
   # Paste new value
   # Save
   ```

3. **Test new credentials**:
   ```bash
   # Deploy to staging with new secret (testing)
   # Verify deployment succeeds
   # Verify application works correctly
   ```

4. **Deploy to production**:
   ```bash
   # Trigger manual production deployment
   # GitHub Actions uses new secret
   # Application should work with new credential
   ```

5. **Verify and clean up**:
   - Check logs for any failures
   - Monitor error rates
   - Delete old credential from provider
   - Document rotation in security log

6. **Log the rotation**:
   ```
   [2026-05-14 10:00:00] Rotated PROD_API_KEY secret
   [2026-05-14 10:05:00] Tested on staging
   [2026-05-14 10:10:00] Deployed to production
   [2026-05-14 10:15:00] Verified production health
   [2026-05-14 10:20:00] Deleted old API key from provider
   ```

## Secret Types

### API Keys

**Storage**: GitHub Secrets (production), .env (development)

**Rotation**: Every 90 days or on compromise

**Best Practices**:
- Use service accounts, not personal accounts
- Restrict permissions to minimum required
- Use separate keys for dev/staging/prod
- Revoke immediately if compromised

### Database Passwords

**Storage**: GitHub Secrets (production), .env (development)

**Rotation**: Every 30 days

**Best Practices**:
- Strong passwords (20+ characters)
- Unique per environment
- Use managed database services when possible
- Test password change before deploying

### Tokens (GitHub, Slack, etc.)

**Storage**: GitHub Secrets (production), .env (development)

**Rotation**: Every 30-90 days

**Best Practices**:
- Use workflow-specific tokens when available
- Minimal required scopes
- Automatic expiration if supported
- Monitor token usage in logs

## Environment Variable Mapping

### Development (.env)

```bash
APP_ENV=development
DATABASE_URL=sqlite:///incidents.db
LOG_LEVEL=debug
API_KEY=<test-key>
```

### Staging (GitHub Secrets)

```bash
STAGING_DATABASE_URL=<staging-db>
STAGING_API_KEY=<staging-key>
STAGING_LOG_LEVEL=info
```

### Production (GitHub Secrets)

```bash
PROD_DATABASE_URL=<prod-db>
PROD_API_KEY=<prod-key>
PROD_LOG_LEVEL=warning
```

## Audit Trail

All secret access is logged:

- GitHub Actions: Workflow logs show secret usage
- Deployment logs: Record which secrets were injected
- Provider logs: API calls using the credentials

**Check logs**:
```bash
# GitHub Actions logs (view in Actions tab)
# Look for successful deployments using secrets

# Application logs (from deployed system)
# Verify correct credentials were loaded

# Provider logs (API provider, database, etc.)
# Check for unusual activity patterns
```

## If a Secret Is Compromised

**Immediate**:
1. Revoke the credential immediately
2. Create new credential
3. Update in GitHub Secrets
4. Re-deploy with new credential
5. Notify team and security

**Investigation**:
1. Check logs for unauthorized access
2. Determine blast radius
3. Verify data integrity
4. Document incident

**Prevention**:
1. Review how compromise happened
2. Strengthen safeguards
3. Update documentation
4. Train team on prevention

## Verification

### .env Files are Git-Ignored

```bash
# Verify .env is in .gitignore
grep "^\.env" .gitignore

# Verify .env is not tracked
git status .env
# Should show: ".env" (untracked)

# If already committed, remove it:
git rm --cached .env
git commit -m "fix: remove .env from tracking"
```

### GitHub Secrets are Set

```bash
# Go to repository settings → Secrets
# Verify all required secrets are present:
# - STAGING_* (if using staging)
# - PROD_* (for production)

# Cannot view secret values (GitHub hides them)
# But can verify existence and last updated date
```

### Pre-commit Hook is Working

```bash
# Try to commit a .env file
touch .env.test
git add .env.test
git commit -m "test"

# Hook should block with message:
# ERROR: .env files not allowed in commits

# Clean up
git reset .env.test
rm .env.test
```

## Related Documentation

- [SECURITY.md](../SECURITY.md) - Full security guide
- [docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md) - Deployment procedures
- [config/.env.example](.env.example) - Environment variables template

---

**Last Updated**: 2026-05-14
