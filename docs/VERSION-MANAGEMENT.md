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

```

> There is no `bump-version.sh` script in the repo (yet). Manual editing,
> as shown above, is the only way to bump the version today.

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

## Deployment and Version Tracking

There is no build/artifact phase — this repo has no `deploy.yml` workflow
(it existed at one point but was removed: unused, and it packaged a `src/`
directory that no longer exists). Deployment is manual, and the `VERSION`
file travels with the git checkout, not with a separate build artifact.

### How It Works

1. Bump `VERSION` and tag the release commit locally (see above).
2. Push the commit and the tag.
3. On the VPS, SSH in and `git pull` the `production` branch — the
   checkout now has the new `VERSION` file automatically, since it's a
   tracked file in the repo.
4. Verify: `ssh <user>@<vps-host> "cat /infocodes/project/release-dashboard-application/VERSION"`
   should match the tag you just pushed.

There is no separate "deployment log" or automated record of what version
is running — the VPS checkout's `VERSION` file (and `git log -1`) is the
source of truth. **Not confirmed**: whether there's any process-level
restart needed after `git pull` for the checks to reflect the new code, or
if nginx serving static files means changes apply immediately.

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
- [ ] Manual testing completed (there is no staging environment or automated health check — verify manually against production after deploying)

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

If the version running on the VPS doesn't match what you expect:

```bash
# Check deployed version
ssh <user>@<vps-host> "cat /infocodes/project/release-dashboard-application/VERSION"

# Check local/repo version
cat VERSION

# If they differ, the VPS checkout is simply behind — pull the latest
# production branch on the VPS (see docs/DEPLOYMENT.md):
ssh <user>@<vps-host> "cd /infocodes/project/release-dashboard-application && git pull origin production"
```

Rollback is also manual: `git checkout <previous-tag-or-commit>` (or
`git revert`) on the VPS checkout, then `git pull`/`git reset` as needed.
There is no `rollback.sh` script.

---

## CI/CD Version Integration

There is no version-aware CI/CD integration. `.github/workflows/` only
has `lint.yml` and `tests.yml` (tests + coverage + style checks on push/PR)
— neither reads the `VERSION` file, builds an artifact, or creates a
GitHub Release. A `deploy.yml` workflow that did some of this existed at
one point but was removed (unused, and broken: it packaged a `src/`
directory that no longer exists in the repo). See
[CI-CD.md](CI-CD.md) for what actually runs today.

GitHub Releases, if you want them, currently have to be created manually
(`gh release create v0.2.0` or via the GitHub UI) after pushing the tag.

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

There is no automated rollback. To roll back on the VPS:

```bash
ssh <user>@<vps-host>
cd /infocodes/project/release-dashboard-application
git log --oneline -5          # find the commit/tag to roll back to
git checkout <previous-tag>   # or: git revert <bad-commit>

# Verify version after rollback
cat VERSION
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
