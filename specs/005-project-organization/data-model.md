# Data Model: Project Organization & Architecture Foundation

**Date**: 2026-05-14

## Entities

### Configuration Entity

Represents environment-specific settings.

```
Configuration:
  - environment_name: enum [development, staging, production]
  - database_url: string (reference or connection string)
  - api_key: string (secret, never logged)
  - log_level: enum [debug, info, warning, error]
  - cache_ttl: integer (seconds, default 300)
  - debug_mode: boolean (true in dev, false in prod)
  - features_enabled: dict (feature flags)
  
  Constraints:
    - database_url must be non-empty
    - log_level must be one of [debug, info, warning, error]
    - cache_ttl must be >= 0
    - Secrets (api_key) never logged, only masked in outputs
```

### EnvironmentProfile Entity

Represents a deployment target environment.

```
EnvironmentProfile:
  - name: string [development, staging, production]
  - config: Configuration (reference)
  - overrides: dict (environment-specific overrides)
  - status: enum [healthy, degraded, failed]
  - last_deployment: timestamp
  - version_deployed: string (semantic version)
  - secrets_source: enum [local_env, external_vault, none]
  
  Relationships:
    - has-one: Configuration
    - has-many: DeploymentLogs
    
  Constraints:
    - Each name is unique (only one production environment)
    - version_deployed must match semantic versioning pattern
```

### DeploymentLog Entity

Tracks deployment history for audit trails.

```
DeploymentLog:
  - timestamp: datetime
  - environment: string (dev/staging/prod)
  - version: string (semantic version)
  - deployer: string (who performed deployment)
  - status: enum [success, rolled_back, failed]
  - previous_version: string (for rollback tracking)
  - changes_summary: string (commit range deployed)
  - error_message: string (if failed, null if success)
  
  Constraints:
    - timestamp must be ISO8601 format
    - deployer must be non-empty
    - All production deployments must have approval log
```

### ProjectMetadata Entity

Represents project-wide information.

```
ProjectMetadata:
  - version: string (semantic version, from VERSION file)
  - team_size: integer (expected 2-6)
  - last_deployment: timestamp
  - current_environment_status: EnvironmentProfile
  - test_coverage: float (percentage, 0-100)
  - is_production_ready: boolean (all gating criteria met)
  
  Constraints:
    - version must match semantic versioning pattern
    - team_size must be between 1 and 50
    - test_coverage >= 80% for prod readiness
```

## Relationships

```
ProjectMetadata
  ├── has-one: EnvironmentProfile (current production)
  ├── has-many: EnvironmentProfile (all environments)
  └── has-many: DeploymentLog (history)

EnvironmentProfile
  ├── has-one: Configuration (settings)
  └── has-many: DeploymentLog (deployment history)

Configuration
  └── belongs-to: EnvironmentProfile
```

## Data Flow

```
1. Developer makes changes
2. Git pre-commit hook checks for secrets
3. PR created -> CI/CD runs tests, linting, coverage
4. PR approved -> merges to main
5. Main deployment process:
   - Read VERSION file
   - Create DeploymentLog entry
   - Load Configuration for target environment
   - Deploy code
   - Update EnvironmentProfile.status
   - Log deployment timestamp and version
```

## Validation Rules

**Configuration Validation**:
- All required fields populated
- No secrets in database_url (use environment variables)
- log_level is valid
- cache_ttl >= 0

**EnvironmentProfile Validation**:
- name is unique within project
- config is valid Configuration
- version_deployed matches semver pattern

**DeploymentLog Validation**:
- timestamp is ISO8601
- version matches semver pattern
- status is valid enum
- For production: previous_version must be non-null (rollback capability)

## Storage & State Management

**Local Development**:
- Configuration stored in `.env` file
- Not committed to git (in .gitignore)
- Loaded by python-dotenv at startup

**Production**:
- Configuration from environment variables
- Injected by deployment platform (GitHub Actions, Kubernetes, etc.)
- Never committed to git
- Audit-logged by deployment system

**Project State**:
- VERSION file stores semantic version
- Deployment logs stored in external system (GitHub Actions logs, CloudWatch, etc.)
- No state persisted in application

## Example: Development Configuration

```
FILE: config/.env
---
APP_ENV=development
DATABASE_URL=sqlite:///incidents.db
LOG_LEVEL=debug
DEBUG=True
CACHE_TTL=60
FEATURE_FLAGS={"advanced_filters": true}
```

## Example: Production Configuration (via environment variables)

```
Environment variables injected by CI/CD:
---
APP_ENV=production
DATABASE_URL=postgresql://user:encrypted_pass@prod.db.cloud/incidents
LOG_LEVEL=warning
DEBUG=False
CACHE_TTL=3600
API_KEY=<secret from vault>
FEATURE_FLAGS={"advanced_filters": false}
```

## Success Criteria

- Configuration can be changed without code modification
- Secrets never appear in logs, git history, or backups
- Deployment log provides complete audit trail
- Rollback can restore previous version in < 5 minutes
- New environment can be added by setting environment variables only
