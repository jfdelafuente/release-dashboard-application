# Deployment Log Record Structure

This document defines the structure and format for deployment records in the Release Dashboard Application.

## Overview

Deployment logs are created automatically when running `scripts/deploy/deploy.sh` or `scripts/deploy/rollback.sh`. Each deployment creates:

1. **Timestamped Log File**: `logs/deployments/deployment-{env}-{timestamp}.log`
2. **Deployment Record**: Appended to `logs/deployments/DEPLOYMENT-RECORDS.log`

---

## Deployment Record Structure

### Record Header

```
================================================================================
DEPLOYMENT RECORD
================================================================================
```

### Required Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| **Environment** | String | Target environment (staging/production) | `staging` |
| **Version** | SemVer | Version being deployed | `0.2.0` |
| **Timestamp** | ISO-8601 | When deployment occurred (UTC) | `2026-05-14T15:30:45Z` |
| **Deployer** | String | Username of person who deployed | `jose.delafuente` |
| **Status** | Enum | SUCCESS / FAILED / ROLLED_BACK | `SUCCESS` |
| **Artifact** | Path | Path to deployment artifact (tarball) | `dist/release-dashboard-0.2.0-20260514-153045.tar.gz` |
| **Backup** | Path | Path to backup directory | `backups/deployment-20260514-153045` |
| **Log** | Path | Path to detailed log file | `logs/deployments/deployment-staging-20260514-153045.log` |

### Verification Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| **Pre-Checks** | Enum | PASSED / FAILED | `PASSED` |
| **Tests** | Enum | PASSED / FAILED | `PASSED` |
| **Coverage** | Percent | Code coverage % | `86%` |
| **Deployment** | Enum | COMPLETED / FAILED / ABORTED | `COMPLETED` |
| **Post-Checks** | Enum | PASSED / FAILED | `PASSED` |

### Example Deployment Record

```
================================================================================
DEPLOYMENT RECORD
================================================================================
Environment:     staging
Version:         0.2.0
Timestamp:       2026-05-14T15:30:45Z
Deployer:        jose.delafuente
Status:          SUCCESS
Artifact:        dist/release-dashboard-0.2.0-20260514-153045.tar.gz
Backup:          backups/deployment-20260514-153045
Log:             logs/deployments/deployment-staging-20260514-153045.log

Pre-Checks:      PASSED (tests, coverage, git status)
Tests:           PASSED (258/264 tests)
Coverage:        86%
Deployment:      COMPLETED
Post-Checks:     PASSED (converter, dashboard)
================================================================================
```

---

## Rollback Record Structure

### Record Header (for rollbacks)

```
================================================================================
ROLLBACK RECORD
================================================================================
```

### Rollback Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| **Environment** | String | Environment where rollback occurred | `staging` |
| **Timestamp** | ISO-8601 | When rollback occurred (UTC) | `2026-05-14T15:35:20Z` |
| **Deployer** | String | Username of person who executed rollback | `jose.delafuente` |
| **Status** | Enum | SUCCESS / FAILED | `SUCCESS` |
| **Rollback From** | Path | Backup directory used for rollback | `backups/deployment-20260514-150000` |
| **Failed Backup** | Path | Backup of the failed deployment | `backups/deployment-failed-20260514-153545` |
| **Log** | Path | Detailed rollback log | `logs/rollback/rollback-staging-20260514-153545.log` |

### Example Rollback Record

```
================================================================================
ROLLBACK RECORD
================================================================================
Environment:     staging
Timestamp:       2026-05-14T15:35:20Z
Deployer:        jose.delafuente
Status:          SUCCESS
Rollback From:   backups/deployment-20260514-150000
Failed Backup:   backups/deployment-failed-20260514-153545
Log:             logs/rollback/rollback-staging-20260514-153545.log

Health Checks:   PASSED
Rollback:        COMPLETED
================================================================================
```

---

## Log File Location Structure

```
logs/
├── deployments/
│   ├── deployment-staging-20260514-153045.log    # Detailed log for deploy
│   ├── deployment-production-20260515-090000.log
│   ├── DEPLOYMENT-RECORDS.log                    # All deployment records
│   └── ...
│
├── rollback/
│   ├── rollback-staging-20260514-153545.log      # Detailed log for rollback
│   ├── rollback-production-20260515-091500.log
│   ├── ROLLBACK-RECORDS.log                      # All rollback records
│   └── ...
│
└── health-checks/
    ├── health-check-staging-20260514-160000.log
    ├── health-check-production-20260515-092000.log
    └── ...
```

---

## Audit Trail

All deployments and rollbacks are recorded in master log files for audit purposes:

### DEPLOYMENT-RECORDS.log

Appended with each successful deployment. Contains all required fields for compliance and troubleshooting.

**Usage**:
```bash
# View all deployments
cat logs/deployments/DEPLOYMENT-RECORDS.log

# View staging deployments only
grep "Environment:     staging" logs/deployments/DEPLOYMENT-RECORDS.log

# View failed deployments
grep "Status:          FAILED" logs/deployments/DEPLOYMENT-RECORDS.log
```

### ROLLBACK-RECORDS.log

Appended with each rollback event (successful or failed).

**Usage**:
```bash
# View all rollbacks
cat logs/rollback/ROLLBACK-RECORDS.log

# View production rollbacks
grep "Environment:     production" logs/rollback/ROLLBACK-RECORDS.log
```

---

## Retention Policy

- **Detailed Logs** (`deployment-*.log`, `rollback-*.log`): Keep for 90 days
- **Master Records** (`DEPLOYMENT-RECORDS.log`, `ROLLBACK-RECORDS.log`): Keep indefinitely
- **Backup Directories**: Keep for 30 days
- **Archive**: Move logs older than 90 days to `logs/archive/YYYY/MM/`

**Cleanup Command**:
```bash
# Remove logs older than 90 days
find logs/deployments -name "*.log" -mtime +90 -delete
find logs/rollback -name "*.log" -mtime +90 -delete

# Remove backups older than 30 days
find backups/ -type d -mtime +30 -exec rm -rf {} \;
```

---

## Integration with Monitoring

Deployment logs can be integrated with monitoring systems:

### Key Metrics

Extract these from deployment records for monitoring dashboards:

```bash
# Deployment success rate (last 30 days)
grep "Status:          SUCCESS" logs/deployments/DEPLOYMENT-RECORDS.log | wc -l

# Average pre-check duration
grep "Pre-Checks:" logs/deployments/DEPLOYMENT-RECORDS.log | ...

# Deployments by version
grep "Version:" logs/deployments/DEPLOYMENT-RECORDS.log | sort | uniq -c

# Deployments by deployer
grep "Deployer:" logs/deployments/DEPLOYMENT-RECORDS.log | sort | uniq -c
```

### Alerts

Set up alerts for:

- **Failed Deployments**: Any record with `Status: FAILED`
- **Rollback Events**: Any entry in `ROLLBACK-RECORDS.log`
- **Disk Space**: During deployment if `<10% free`
- **Coverage Drop**: If coverage < 80%

---

## Compliance & Legal

- **Audit Trail**: All deployments logged with timestamp, actor, and status
- **Immutability**: Master records should not be edited (append-only)
- **Retention**: Keep records for compliance period (typically 7 years)
- **Privacy**: Deployer names are recorded (comply with data retention policies)

---

## Examples

### Query Recent Deployments

```bash
# Last 10 deployments
head -200 logs/deployments/DEPLOYMENT-RECORDS.log | tail -70

# Deployments from specific date
grep "2026-05-14" logs/deployments/DEPLOYMENT-RECORDS.log

# Production deployments
grep "Environment:     production" logs/deployments/DEPLOYMENT-RECORDS.log
```

### Generate Report

```bash
#!/bin/bash
# deployment-report.sh

echo "=== Deployment Summary (Last 30 days) ==="
echo "Total Deployments:"
grep "Status:" logs/deployments/DEPLOYMENT-RECORDS.log | wc -l

echo "Successful:"
grep "Status:          SUCCESS" logs/deployments/DEPLOYMENT-RECORDS.log | wc -l

echo "Failed:"
grep "Status:          FAILED" logs/deployments/DEPLOYMENT-RECORDS.log | wc -l

echo "By Environment:"
grep "Environment:" logs/deployments/DEPLOYMENT-RECORDS.log | sort | uniq -c

echo "By Deployer:"
grep "Deployer:" logs/deployments/DEPLOYMENT-RECORDS.log | sort | uniq -c
```

---

**Last Updated**: 2026-05-14
**Version**: 1.0
