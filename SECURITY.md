# Security Guide

Security practices and incident response procedures for Release Dashboard Application.

## Overview

This application handles sensitive incident data and requires strict security practices to prevent:
- Accidental disclosure of credentials
- Exposure of sensitive incident data
- Unauthorized access to production systems
- Data breaches

## Secret Management

### What Are Secrets?

Secrets are sensitive information that must never be committed to git:
- API keys and tokens
- Database passwords
- Encryption keys
- Authentication credentials
- Private configuration

### Development (Local)

**File**: `.env` (git-ignored)

```bash
# Create .env from template
cp config/.env.example .env

# Edit with local values (safe - not committed)
APP_ENV=development
DATABASE_URL=sqlite:///incidents.db
API_KEY=<local-test-key>
```

**Safe practices**:
- ✅ Use `.env` for development
- ✅ `.env` is automatically git-ignored
- ✅ Reset `.env` between sessions
- ❌ Never commit `.env` to git
- ❌ Never use production secrets locally

### Production

**Location**: GitHub Secrets (never in code)

**Setup**:
1. Go to GitHub repository settings
2. Navigate to "Secrets" section
3. Create secret for each environment variable:
   - `APP_ENV`
   - `DATABASE_URL`
   - `API_KEY`
   - `LOG_LEVEL`

**Injected at deployment**:
```bash
# GitHub Actions automatically injects secrets as environment variables
# Code reads: os.getenv('DATABASE_URL')  # Gets from GitHub Secret
```

**Access Control**:
- Only repository admins can create/modify secrets
- Only deployment workflows can read secrets
- Developers cannot access production credentials
- All secret access is logged

### Staging

**Configuration**: `config/.env.staging` (git-ignored)

For staging deployments, use subset of production credentials:
- Test database (not production)
- Test API keys
- Reduced sensitive data scope

## Prevention Systems

### Layer 1: .gitignore

Prevents files from being committed:

```gitignore
# Environment variables
.env
.env.local
.env.*.local

# Sensitive files
credentials.json
secrets.yml
*.key
*.pem

# Data directory (contains incident data)
data/
```

**Verify**:
```bash
cat .gitignore | grep "^\.env"  # Should match .env patterns
```

### Layer 2: Pre-commit Hook

Blocks commits if secrets are detected:

```bash
# Install hook (one-time setup)
./scripts/deploy/install-hooks.sh

# Or manually:
bash config/pre-commit-hook.sh

# Runs automatically on: git commit
```

**What it checks**:
- Detects files named `.env*`
- Detects common patterns: `password=`, `api_key=`, `secret=`
- Blocks commit if secrets found
- Suggests correct handling

**Example**:
```bash
$ git commit -m "Add feature"
# Pre-commit hook detects .env file
❌ BLOCKED: .env files not allowed in commits
✅ Fix: Remove .env from staging area (it's git-ignored)
$ git reset .env
$ git commit -m "Add feature"  # Now succeeds
```

### Layer 3: GitHub Secret Scanning

Automatic scanning of all pushes:

**Detects**:
- AWS keys, tokens
- GitHub tokens
- Slack tokens
- Database connection strings

**Actions**:
- Alerts repository admins
- Blocks risky commits (configurable)
- Suggests remediation

**Enable**:
- Go to repository settings
- Enable "Push protection" for secret scanning
- GitHub scans all future pushes

### Layer 4: Principle of Least Privilege

**For developers**:
- Read access to development secrets only
- No access to production credentials
- Cannot approve own deployments
- Cannot modify security settings

**For deployment**:
- Automation has minimal required permissions
- Staging deployments have limited privileges
- Production deployments require approval
- All actions are logged

## Data Protection

### Incident Data Security

The `data/` directory contains sensitive incident information:
- Customer names and details
- System vulnerabilities
- Incident timelines
- Response procedures

**Protection**:
- ✅ Git-ignored: never committed to repository
- ✅ Access controlled: only authorized team members
- ✅ Encrypted: at rest (if on cloud storage)
- ✅ Encrypted: in transit (HTTPS only)
- ❌ Never shared in unencrypted channels
- ❌ Never stored in version control

### Log Security

**Secure logging**:
```python
# ✅ GOOD: Don't log secrets
logger.info(f"Authenticated as {user}")  # OK

# ❌ BAD: Don't log API keys
logger.info(f"Using API key: {api_key}")  # DANGER

# ✅ GOOD: Log masked version
masked_key = api_key[:4] + "..." + api_key[-4:]
logger.info(f"Using API key: {masked_key}")  # Better
```

**Log cleanup**:
- Don't include secrets in error messages
- Sanitize stack traces before sharing
- Rotate sensitive values regularly
- Delete old logs containing sensitive data

## Credential Rotation

### When to Rotate

- Monthly (best practice)
- When employee leaves
- If compromise is suspected
- After any security incident
- On schedule (quarterly minimum)

### How to Rotate

1. **Create new credentials** in secure system (GitHub Secrets, vault)
2. **Update all locations** where old credential is used:
   - GitHub Secrets
   - Production configuration
   - Environment variables
3. **Test** that new credentials work
4. **Delete old credentials** from all systems
5. **Log rotation** for audit trail:
   ```
   [2026-05-14 10:00:00] Rotated API_KEY secret
   [2026-05-14 10:05:00] Verified production deployment with new key
   [2026-05-14 10:10:00] Deleted old API_KEY from all systems
   ```

## Incident Response

### If a Secret is Committed

**Immediate actions**:

1. **Don't panic** - you have time to fix this
2. **Identify what was exposed** - API key? Password? Token?
3. **Revoke the credential immediately**:
   - GitHub Secrets: delete and recreate
   - API provider: revoke token
   - Database: change password
4. **Remove from git history**:
   ```bash
   # Option 1: Rewrite history (if not yet pushed to GitHub)
   git reset HEAD~1
   # OR
   # Option 2: Use git filter (if pushed)
   git filter-branch --tree-filter 'rm -f .env' HEAD
   git push --force
   ```
5. **Create new commit** with removed secret:
   ```bash
   # Remove .env from git (stays on disk, git-ignored)
   git rm --cached .env
   git commit -m "fix: remove exposed secrets"
   ```
6. **Notify team** - explain what happened, assure them it's revoked
7. **Review logs** - check if revoked credential was used for unauthorized access
8. **Update pre-commit hook** - ensure this can't happen again

### If Credentials Are Compromised

**Incident response steps**:

1. **Assess impact**:
   - What credential was compromised?
   - What systems can it access?
   - Any unauthorized access detected?
   - How long was credential exposed?

2. **Contain the threat**:
   - Immediately revoke compromised credential
   - Rotate all related credentials
   - Check logs for unauthorized use
   - Disable user account if employee-related

3. **Remediate**:
   - Change all affected passwords/keys
   - Update all systems with new credentials
   - Force password resets for affected users
   - Check for data exfiltration

4. **Communicate**:
   - Notify affected teams
   - Update incident tracking system
   - Brief leadership on remediation
   - Document lessons learned

5. **Prevent future incidents**:
   - Review security training
   - Strengthen pre-commit hooks
   - Audit access logs
   - Update security policies

### Incident Tracking

Document all security incidents:

```markdown
**Incident**: [INC-2026-001] Accidentally committed .env to feature branch

**Date**: 2026-05-14 14:30
**Severity**: Low (caught before merge, no production impact)
**Credential**: development API_KEY only

**Timeline**:
- 14:30: Committed .env by mistake to feature/new-feature
- 14:35: Caught by pre-commit hook on next commit attempt
- 14:40: Revoked development API key
- 14:45: Removed commit with git revert
- 15:00: Verified no unauthorized access in logs

**Resolution**: New API key generated, .env regenerated, team trained

**Follow-up**: Enable push protection on GitHub
```

## Security Checklist

### Before Every Deployment

- [ ] No secrets in code or configuration
- [ ] All credentials in GitHub Secrets (production)
- [ ] Credentials are not hardcoded anywhere
- [ ] `.env` file is git-ignored
- [ ] No API keys in logs or error messages
- [ ] Database passwords are stored securely
- [ ] Access logs show no unauthorized attempts

### Weekly

- [ ] Review access logs for suspicious activity
- [ ] Verify all team members still need their access
- [ ] Check GitHub Secret scanning alerts
- [ ] Review pre-commit hook logs

### Monthly

- [ ] Rotate production credentials
- [ ] Review security audit logs
- [ ] Update security documentation
- [ ] Test disaster recovery procedures
- [ ] Review access control policies

### Quarterly

- [ ] Security audit of all systems
- [ ] Penetration testing (if applicable)
- [ ] Security training for team
- [ ] Review and update security policies
- [ ] Incident response drill

## Best Practices

### Do's ✅

- ✅ Use environment variables for configuration
- ✅ Store secrets in GitHub Secrets (production)
- ✅ Use `.env` files for development (git-ignored)
- ✅ Rotate credentials regularly
- ✅ Log security events
- ✅ Review access logs
- ✅ Use strong passwords
- ✅ Enable two-factor authentication
- ✅ Keep dependencies updated
- ✅ Test security regularly

### Don'ts ❌

- ❌ Commit `.env` files to git
- ❌ Hardcode API keys in code
- ❌ Share credentials in chat/email
- ❌ Use production credentials locally
- ❌ Log sensitive data
- ❌ Use weak passwords
- ❌ Reuse credentials across systems
- ❌ Leave unused credentials active
- ❌ Ignore security warnings
- ❌ Disable security checks

## Tools & Resources

### Built-in Security

- **Git hooks**: Prevent secret commits
- **GitHub Secrets**: Secure credential storage
- **GitHub Secret scanning**: Detect leaked credentials
- **Environment variables**: Externalize configuration

### Recommended Tools

- **Vault** (HashiCorp): Secrets management
- **1Password**: Team password management
- **git-secrets**: Additional git hook checking
- **TruffleHog**: Find secrets in git history

### Learning Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [GitHub Security Docs](https://docs.github.com/en/code-security)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)

## Questions?

1. **How do I know if my secret was exposed?**
   - GitHub Secret scanning will alert you
   - Check git log for accidental commits
   - Review pre-commit hook logs

2. **Can I use production secrets locally?**
   - No. Never use production credentials in development.
   - Create test/development versions instead.
   - This prevents accidental damage to production.

3. **What if I accidentally put a secret in a PR?**
   - Don't panic - immediately revoke the credential
   - Remove from git history before merging
   - Use `git revert` if already merged
   - Notify team and security lead

4. **Who should have access to production credentials?**
   - Only deployment automation and authorized ops staff
   - Never developers (except as needed for debugging)
   - Access should be logged and audited
   - Use principle of least privilege

5. **How often should I rotate credentials?**
   - Monthly at minimum
   - More frequently for high-risk systems
   - Immediately if compromise suspected
   - Document all rotations

---

**Last Updated**: 2026-05-14
