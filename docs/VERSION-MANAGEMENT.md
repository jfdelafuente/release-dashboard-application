# Version Management Policy

This document defines how versions are managed, incremented, and tagged in the Release Dashboard Application.

---

## Versioning Scheme: Semantic Versioning (SemVer)

Format: `MAJOR.MINOR.PATCH`

**Current Version**: Read from `VERSION` file in project root

**Example**: `0.2.0`

### Version Components

| Component | Increment When | Example |
|-----------|---|---------|
| **MAJOR** | Breaking API/UI changes, major refactoring | `1.0.0` (from 0.9.0) |
| **MINOR** | New features, non-breaking enhancements | `0.2.0` (from 0.1.0) |
| **PATCH** | Bug fixes, documentation, small improvements | `0.1.5` (from 0.1.4) |

### Examples

```
0.1.0 → First release (MVP)
0.1.1 → Bug fix
0.2.0 → Add new feature
0.2.1 → Fix bug in new feature
1.0.0 → Major rewrite, breaking changes
```

---

## VERSION File

**Location**: `VERSION` (root of project)

**Format**: Single line containing version number

**Content**:
```
0.2.0
```

### Updating VERSION

When to update:

1. **Before merge to main**: Update VERSION in PR
2. **Format**: Exactly as shown above (no `v` prefix, no extra text)
3. **Commit message**: Include version in message: `"Bump version to 0.2.0"`

**How to update**:

```bash
# Option 1: Manual edit
echo "0.2.0" > VERSION
git add VERSION
git commit -m "Bump version to 0.2.0"

# Option 2: Script (if available)
./scripts/bump-version.sh minor  # 0.1.0 → 0.2.0
./scripts/bump-version.sh patch  # 0.2.0 → 0.2.1
```

---

## Git Tags

Every version released to production MUST have a git tag.

### Tag Format

```
v{MAJOR}.{MINOR}.{PATCH}

Examples:
v0.1.0
v0.2.0
v1.0.0
```

### Creating Tags

```bash
# 1. Ensure VERSION file matches tag
cat VERSION
# Output: 0.2.0

# 2. Create annotated tag
git tag -a v0.2.0 -m "Release v0.2.0: Add deployment scripts and rollback"

# 3. Push tags to remote
git push origin v0.2.0

# 4. Verify
git tag -l v0.2.0
```

### Tag per Environment

- **Staging**: Optional (can use commits)
- **Production**: **MANDATORY** - Every production deployment must have a tag

---

## Deployment Version Locking

### How It Works

1. **Build Phase** (GitHub Actions)
   - Reads VERSION file
   - Creates artifact: `release-dashboard-{VERSION}-{timestamp}.tar.gz`
   - Stores version in build output

2. **Deployment Phase**
   - Deploys specific artifact with locked version
   - Cannot accidentally deploy different version

3. **Verification**
   - Deployment log records exact version deployed
   - Can verify running version matches tag: `ssh app@host "cat VERSION"`

### Example Deployment Flow

```bash
# 1. VERSION file shows
cat VERSION
# 0.2.0

# 2. Artifact created with version
ls dist/
# release-dashboard-0.2.0-20260514-153045.tar.gz

# 3. Artifact deployed with version baked in
./scripts/deploy/deploy.sh production

# 4. Deployment log records version
grep "Version:" logs/deployments/DEPLOYMENT-RECORDS.log
# Version: 0.2.0

# 5. Running system has same version
ssh app@prod.example.com "cat VERSION"
# 0.2.0

# 6. Git tag matches
git tag -l | grep 0.2.0
# v0.2.0
```

---

## Release Checklist

Before creating a release (bumping version):

### Code Quality

- [ ] All tests pass: `pytest tests/ --cov --cov-fail-under=80`
- [ ] Coverage >= 80%
- [ ] Linting clean: `flake8`, `black`, `pylint`, `bandit`
- [ ] No TODO comments (or tracked as issues)
- [ ] Security scan passed: `bandit`

### Documentation

- [ ] CHANGELOG.md updated with changes
- [ ] README.md reflects any new features
- [ ] API documentation updated
- [ ] Deployment guide current

### Testing

- [ ] Unit tests passing
- [ ] Integration tests passing
- [ ] Manual testing completed
- [ ] Staging deployment verified
- [ ] Health checks passing

### Version & Tags

- [ ] VERSION file updated
- [ ] Git tag created: `git tag -a v{VERSION}`
- [ ] Tag pushed: `git push origin v{VERSION}`
- [ ] CHANGELOG references new version

### Communication

- [ ] Release notes prepared
- [ ] Team notified
- [ ] Stakeholders informed
- [ ] Deployment scheduled

---

## CHANGELOG Format

File: `CHANGELOG.md` (in project root)

Format: Each version as section with dates and changes

```markdown
# Changelog

All notable changes to this project are documented here.

## [0.2.0] - 2026-05-14

### Added
- Deployment scripts (deploy.sh, rollback.sh)
- Health check monitoring
- Rollback capability

### Fixed
- Bug in CSV parser handling special characters
- Dashboard not loading with empty data

### Changed
- Updated deployment procedure
- Improved error messages

## [0.1.0] - 2026-04-01

### Added
- Initial project structure
- Massive Incidents Dashboard
- CSV to JSON converter
- Postmortem Dashboard
```

---

## Version History

Track all released versions:

```bash
# List all tags
git tag -l

# View commits for specific version
git show v0.2.0

# View log between versions
git log v0.1.0..v0.2.0 --oneline

# Generate release notes
git log v0.1.0..v0.2.0 --format="- %s" > release-notes.txt
```

---

## Handling Version Mismatches

If running version doesn't match deployed version:

```bash
# Check deployed version
ssh app@prod.example.com "cat VERSION"
# Output: 0.1.5

# Check git current version
cat VERSION
# Output: 0.2.0

# Check git tag vs running
git describe --tags  # Should show v0.1.5 if on that tag
# Output: v0.2.0

# Options:
# 1. Update VERSION to match running: `echo "0.2.0" > VERSION`
# 2. Or rollback: `./scripts/deploy/rollback.sh production`
```

---

## CI/CD Version Integration

### GitHub Actions (deploy.yml)

Automatically:
1. Reads VERSION file
2. Includes in artifact name
3. Passes to deployment script
4. Logs in deployment record

```yaml
- name: Get version
  id: version
  run: |
    VERSION=$(cat VERSION)
    echo "version=$VERSION" >> $GITHUB_OUTPUT

- name: Deploy artifact
  run: |
    echo "Deploying version: ${{ steps.version.outputs.version }}"
    # ... deployment steps ...
```

### GitHub Releases

Automatically created by deploy.yml on production deploy:

```bash
# GitHub automatically creates release:
# Title: "Release v0.2.0"
# Tag: "v0.2.0"
# Body: Deployment logs, changes, affected systems
```

---

## Best Practices

✅ **DO**:
- Update VERSION before merge to main
- Create git tag for every production deployment
- Document changes in CHANGELOG.md
- Use SemVer format consistently
- Include version in commit messages
- Test deployment with version bumped
- Verify running version matches tag

❌ **DON'T**:
- Commit VERSION without updating CHANGELOG
- Skip git tags for production
- Use non-SemVer format (e.g., `0.2a`, `v0.2.0-beta`)
- Deploy without creating release notes
- Update VERSION file only in hotfix branches

---

## Rollback Version Considerations

When rolling back to previous version:

```bash
# Automatic rollback restores previous VERSION
./scripts/deploy/rollback.sh production

# Verify version after rollback
ssh app@prod.example.com "cat VERSION"
# Should show previous version
```

---

## Frequently Asked Questions

**Q: How often should we bump MAJOR version?**
A: When making breaking changes to API/UI that require user action. Typically every 6-12 months.

**Q: Should patch releases get git tags?**
A: Only for production deployments. Staging patches can skip tags.

**Q: What if VERSION file is missing?**
A: Deploy will fail. Create it: `echo "0.1.0" > VERSION` and try again.

**Q: Can we skip version bumps for internal releases?**
A: No. Every deployment should increment at least PATCH version.

**Q: How do we handle pre-releases (beta, RC)?**
A: Currently not supported. Use stable versions only.

---

**Last Updated**: 2026-05-14
**Version**: 1.0
