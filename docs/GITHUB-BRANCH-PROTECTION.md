# GitHub Branch Protection Configuration

Instructions for configuring branch protection rules to enforce required reviews for production deployments.

---

## Quick Setup

1. Go to **GitHub Repository Settings**
2. Navigate to **Branches** → **Branch protection rules**
3. Click **Add rule** or edit existing `main` rule
4. Configure as shown below

---

## Required Configuration for `main` Branch

### Basic Settings

**Branch name pattern**: `main`

### Protect matching branches

✅ **Require a pull request before merging**:
- [x] Require approvals
- [x] Number of required approvals: **1** (minimum for production)
  - *Recommended: 2 for critical projects*
- [x] Dismiss stale pull request approvals when new commits are pushed
- [x] Require review from code owners (if CODEOWNERS file exists)

✅ **Require status checks to pass before merging**:
- [x] Require branches to be up to date before merging
- [x] Required checks:
  - `test` (from tests.yml workflow)
  - `lint` (from lint.yml workflow)
  - *Add other required checks as needed*

✅ **Require conversation resolution before merging**:
- [x] Enable (requires all conversations resolved)

✅ **Require signed commits**:
- [x] Enable (optional, for high-security environments)

### Rules for administrators

- [ ] Do NOT allow admins to bypass these rules
  - *If unchecked, admins must follow rules too (recommended)*

### Dismissal restrictions

- [x] Restrict who can dismiss pull request reviews
  - *Recommended: Only maintainers/leads*

---

## Configuration for `develop` Branch (Optional)

If you have a develop branch for testing:

**Branch name pattern**: `develop`

✅ **Require a pull request before merging**:
- [x] Require approvals: **1**
- [x] Dismiss stale approvals on new commits

✅ **Require status checks to pass**:
- [x] Required checks:
  - `test` (tests.yml)
  - `lint` (lint.yml)

*Less strict than `main` - allows faster iteration*

---

## Applying Settings

### Step-by-Step in GitHub UI

1. **Go to Repository**:
   - https://github.com/yourusername/release-dashboard-application
   - Click **Settings** tab

2. **Navigate to Branches**:
   - Left sidebar: **Code and automation** → **Branches**
   - Or: https://github.com/.../settings/branches

3. **Add or Edit Rule**:
   - Click **Add rule** (new) or edit existing
   - Enter branch pattern: `main`

4. **Configure Protection**:
   - ✅ Require a pull request before merging
   - ✅ Number of approvals: `1`
   - ✅ Require status checks to pass
   - ✅ Select required checks: `test`, `lint`
   - ✅ Require conversation resolution

5. **Review and Save**:
   - Scroll down
   - Click **Create** (or **Update** if editing)

---

## Enforcement: What Happens

### After Configuration

**When code is pushed to non-main branch**:
1. ✅ GitHub Actions workflows run automatically
2. ✅ Tests must pass (tests.yml)
3. ✅ Linting must pass (lint.yml)

**When PR is created**:
1. ✅ Workflow status checks visible in PR
2. ✅ Merge button disabled until checks pass
3. ✅ At least 1 approval required to merge

**Attempting to merge without meeting requirements**:
```
❌ CANNOT MERGE
Reason: Required status checks did not complete successfully:
  ○ test (pending)
  ○ lint (pending)

Reason: This branch has 0 of 1 required approval
```

---

## Special Cases

### Dismissing Reviews

Reviews can be dismissed IF configured:
- Only by designated users (maintainers/leads)
- Requires reason
- Creates audit log entry

### Bypassing Rules

Branch protection cannot be bypassed except by:
- Repository admins (if allowed in settings)
- GitHub Enterprise admins

### Emergency Override

If CRITICAL issue requires bypass:
1. Temporarily disable branch protection
2. Deploy hotfix
3. Re-enable branch protection
4. Document in incident ticket

---

## Verification

### Check Current Settings

```bash
# View branch protection rules via GitHub API
gh api repos/{owner}/{repo}/branches/main/protection

# Example output:
{
  "url": "https://api.github.com/repos/.../protection",
  "required_pull_request_reviews": {
    "require_code_owner_reviews": false,
    "required_approving_review_count": 1
  },
  "required_status_checks": {
    "strict": true,
    "contexts": ["test", "lint"]
  }
}
```

### Test Configuration

Create a test PR to verify:

1. Create branch from `main`
2. Make small change (README.md)
3. Push and create PR
4. Verify:
   - Workflows run automatically
   - Merge button is disabled
   - Shows: "1 approval required"
   - Shows: "Status checks pending"
5. Merge button enabled only after:
   - Workflows pass ✅
   - PR has 1+ approvals ✅
   - Conversations resolved ✅

---

## Troubleshooting

### "Required status checks did not complete successfully"

**Cause**: Workflow did not run or failed

**Solution**:
1. Check **Actions** tab for workflow status
2. Fix code issues (tests/linting)
3. Push fix
4. Workflow runs automatically

### "This branch has 0 of 1 required approval"

**Cause**: PR needs approval from repository maintainer

**Solution**:
1. Ask maintainer to review PR
2. Click **Add approval** on PR
3. Comment: "Looks good to merge"
4. Once approved, merge button enables

### "Merge button still disabled after checks pass"

**Cause**: Branch may be out of date with `main`

**Solution**:
1. Pull latest `main`: `git pull origin main`
2. Merge into your branch: `git merge main`
3. Push: `git push`
4. Workflow runs again
5. After passing, merge should be enabled

---

## Best Practices

✅ **DO**:
- Require at least 1 review for all branches
- Enable status checks (test + lint)
- Require conversation resolution
- Keep rules consistent across branches
- Document exceptions
- Review branch protection settings quarterly

❌ **DON'T**:
- Allow admins to bypass rules
- Require excessive approvals (blocks velocity)
- Dismiss reviews without code changes
- Merge without resolving conversations
- Disable branch protection for convenience

---

## Audit Trail

GitHub automatically logs:
- Who dismissed reviews
- Who merged PRs
- When branch protection rules changed
- All approvals and reviews

**View at**: GitHub → **Settings** → **Audit log**

---

## For Production Deployments

Additional considerations:

1. **Required Code Owners Review**:
   - Create `CODEOWNERS` file
   - Require approval from code owners
   - Ensures domain experts review changes

2. **Require Signed Commits**:
   - All commits must be signed
   - Verifies commit authenticity
   - Prevents impersonation

3. **Require Deployments**:
   - Deployment must succeed in test environment first
   - Before allowing merge to production branch

Example advanced config:
```
✅ Require 2 approvals (not 1)
✅ Require code owner review
✅ Require signed commits
✅ Require status checks to pass
✅ Require conversation resolution
✅ Require branches to be up to date
```

---

**Last Updated**: 2026-05-14
**Version**: 1.0
