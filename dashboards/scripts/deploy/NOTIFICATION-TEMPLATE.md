# Deployment Notification Templates

Standardized notification templates for deployment events. Use these to communicate deployment status to team members and stakeholders.

---

## ✅ Successful Deployment

Use this template when deployment completes successfully.

### Slack/Email Subject
```
✅ Deployment Successful: {ENVIRONMENT} - v{VERSION}
```

### Message

```
🚀 DEPLOYMENT SUCCESSFUL

Environment: {ENVIRONMENT}
Version: {VERSION}
Timestamp: {TIMESTAMP}
Deployer: {DEPLOYER}
Duration: {DURATION} minutes

📊 Deployment Details:
  • Status: SUCCESS
  • Tests: PASSED (all {NUM_TESTS})
  • Coverage: {COVERAGE}%
  • Pre-Checks: PASSED
  • Health Checks: PASSED

🌐 URLs:
  • Staging: https://staging.example.com
  • Production: https://example.com
  • Health Check: https://example.com/health

📋 Changes in this Release:
  • New feature: Deployment automation
  • Bug fixes: 2
  • Documentation: Updated deployment guide
  • Breaking changes: None

📝 Full Details:
  • Logs: logs/deployments/deployment-{ENVIRONMENT}-{TIMESTAMP}.log
  • CHANGELOG: [CHANGELOG.md](../CHANGELOG.md)
  • Commits: [View on GitHub](https://github.com/.../{VERSION})

✅ Next Steps:
  1. Monitor application in [monitoring dashboard](https://monitoring.example.com)
  2. Review logs if any issues occur: `logs/deployments/`
  3. Rollback available at: [Rollback Procedure](../docs/DEPLOYMENT.md#rollback)

⚠️ Escalation:
  If issues detected, contact: DevOps Team @ #devops
```

---

## ❌ Failed Deployment - Auto Rollback

Use when deployment fails but automatic rollback succeeded.

### Slack/Email Subject
```
⚠️ Deployment Failed (Auto-Rollback): {ENVIRONMENT} - v{VERSION}
```

### Message

```
❌ DEPLOYMENT FAILED (AUTOMATIC ROLLBACK INITIATED)

Environment: {ENVIRONMENT}
Version: {VERSION} (attempted)
Timestamp: {TIMESTAMP}
Deployer: {DEPLOYER}

🔄 AUTO-ROLLBACK STATUS: ✅ SUCCESSFUL
  • Previous version: {PREVIOUS_VERSION}
  • Restored from: {BACKUP_DIR}
  • Health checks: PASSED
  • System status: OPERATIONAL

❌ Failure Reason:
  {FAILURE_REASON}

📋 Details:
  • Failed at stage: {STAGE} (e.g., health check, deployment)
  • Error message: {ERROR_MESSAGE}
  • Detailed logs: logs/deployments/deployment-{ENVIRONMENT}-{TIMESTAMP}.log

🔧 Immediate Actions:
  1. ✅ System rolled back to v{PREVIOUS_VERSION}
  2. 🔍 Investigate root cause
  3. 📝 Fix the issue in the codebase
  4. 🧪 Re-test locally: pytest tests/
  5. 🚀 Retry deployment when ready

📞 Support:
  • DevOps: #devops
  • On-Call: {ON_CALL_NUMBER}
  • Post-Mortem: Schedule review meeting

⏱️ Timeline:
  • Deployment started: {START_TIME}
  • Failure detected: {FAILURE_TIME}
  • Rollback completed: {ROLLBACK_TIME}
  • Duration: {TOTAL_DURATION} minutes
```

---

## 🔄 Manual Rollback Notification

Use when manual rollback is initiated.

### Slack/Email Subject
```
🔄 Manual Rollback: {ENVIRONMENT} - Reverting to v{PREVIOUS_VERSION}
```

### Message

```
🔄 MANUAL ROLLBACK IN PROGRESS

Environment: {ENVIRONMENT}
Rolling back from: v{FAILED_VERSION}
Rolling back to: v{PREVIOUS_VERSION}
Initiated by: {DEPLOYER}
Timestamp: {TIMESTAMP}

📦 Backup Used:
  • Directory: {BACKUP_DIR}
  • Created: {BACKUP_TIMESTAMP}
  • Size: {BACKUP_SIZE}

⏱️ Expected Duration: 2-5 minutes

📋 Rollback Checklist:
  [ ] Backup of failed version created: {FAILED_BACKUP_DIR}
  [ ] Previous version restored
  [ ] Dependencies installed
  [ ] Health checks run
  [ ] Application verified operational

✅ Post-Rollback:
  • Previous version now active: v{PREVIOUS_VERSION}
  • Health checks: PASSING
  • Application: OPERATIONAL
  • Full logs: logs/rollback/rollback-{ENVIRONMENT}-{TIMESTAMP}.log

🔧 Next Steps:
  1. Investigate why v{FAILED_VERSION} failed
  2. Create fix and re-test
  3. Update version to v{NEW_VERSION}
  4. Schedule re-deployment

📞 Contact:
  • Need urgent help? #devops-oncall
  • Post-mortem required
```

---

## ⚠️ Deployment Critical Issue

Use for critical issues that require immediate escalation.

### Slack/Email Subject
```
🚨 CRITICAL: Deployment Issue in {ENVIRONMENT} - v{VERSION}
```

### Message

```
🚨 CRITICAL DEPLOYMENT ISSUE

Environment: {ENVIRONMENT}
Version: {VERSION}
Severity: CRITICAL
Reported: {TIMESTAMP}
Reporter: {REPORTER_NAME}

🔴 Issue Description:
{ISSUE_DESCRIPTION}

💥 Impact:
  • Users affected: {AFFECTED_USERS}
  • Services down: {AFFECTED_SERVICES}
  • Data affected: {DATA_IMPACT}

⚡ Immediate Action Required:
  ☐ Escalate to on-call engineer
  ☐ Assess if rollback needed
  ☐ Notify stakeholders
  ☐ Create incident ticket

🔄 Rollback Decision:
  Status: {DECISION}
  Reason: {REASON}
  ETA: {ETA_MINUTES} minutes

📞 ESCALATION CHAIN:
  1. On-Call Engineer: {ONCALL_NUMBER}
  2. Engineering Lead: {LEAD_NUMBER}
  3. VP Engineering: {VP_NUMBER}

📋 Coordination:
  • War room: {ZOOM_LINK}
  • Incident channel: #incident-{DATE}
  • Tracking: {JIRA_LINK}

⏱️ Timeline:
  • Deployed: {DEPLOY_TIME}
  • Issue detected: {DETECT_TIME}
  • Escalation time: {TIME_SINCE_DEPLOY}
```

---

## 📊 Deployment Summary Report

Use this for a comprehensive weekly or monthly summary.

### Format

```
DEPLOYMENT SUMMARY: {PERIOD}

📈 Statistics:
  Total Deployments: {TOTAL}
  Successful: {SUCCESSFUL} ({SUCCESS_RATE}%)
  Failed: {FAILED}
  Rolled Back: {ROLLBACKS}

📊 By Environment:
  Staging: {STAGING_COUNT} deployments
  Production: {PRODUCTION_COUNT} deployments

⏱️ Performance:
  Avg deployment time: {AVG_TIME} minutes
  Fastest: {FASTEST_TIME} minutes
  Slowest: {SLOWEST_TIME} minutes

👥 Deployments by Team:
  {DEPLOYER1}: {COUNT}
  {DEPLOYER2}: {COUNT}
  {DEPLOYER3}: {COUNT}

🔧 Common Issues:
  1. {ISSUE1} ({FREQUENCY}%)
  2. {ISSUE2} ({FREQUENCY}%)
  3. {ISSUE3} ({FREQUENCY}%)

💡 Improvements Implemented:
  • {IMPROVEMENT1}
  • {IMPROVEMENT2}
  • {IMPROVEMENT3}

📋 Versions Deployed:
  v{VERSION1} → v{VERSION2} → v{VERSION3}

🎯 Next Month Goals:
  • Improve success rate to {TARGET}%
  • Reduce avg deployment time to {TARGET} minutes
  • Zero critical issues in deployments
```

---

## Template Variables Reference

| Variable | Example | Source |
|----------|---------|--------|
| `{ENVIRONMENT}` | staging / production | script argument |
| `{VERSION}` | 0.2.0 | VERSION file |
| `{TIMESTAMP}` | 2026-05-14T15:30:45Z | date command |
| `{DEPLOYER}` | jose.delafuente | $USER environment var |
| `{DURATION}` | 5 | calculated |
| `{NUM_TESTS}` | 258 | pytest output |
| `{COVERAGE}` | 86 | coverage report |
| `{FAILURE_REASON}` | Health check failed | deploy.sh log |
| `{STAGE}` | health-check-post | deploy.sh stage |
| `{ERROR_MESSAGE}` | Converter not responding | captured error |
| `{PREVIOUS_VERSION}` | 0.1.5 | VERSION file from backup |
| `{BACKUP_DIR}` | backups/deployment-20260514-150000 | created by script |
| `{ISSUE_DESCRIPTION}` | Users reporting 500 errors | incident report |

---

## Delivery Channels

### Slack

```
Use #deployments channel for:
  ✅ Successful deployments
  ❌ Failed deployments with rollback
  🔄 Manual rollbacks

Use #incident-response for:
  🚨 Critical issues
  💥 Escalations
```

### Email

Send to `{ENVIRONMENT}-deployments@company.com`:
  • All production deployments
  • Any critical issues
  • Monthly summaries

### Status Page

Post to status.example.com:
  • Critical issues affecting users
  • Extended outages
  • Rollbacks

### GitHub Release

Automatically created by CI/CD:
  • Title: Release v{VERSION}
  • Body: Auto-generated from logs
  • Tag: v{VERSION}

---

## Customization

Feel free to customize these templates to match your team's communication style:

1. Add team-specific contact info
2. Include relevant links (monitoring, docs, etc)
3. Add emoji preferences
4. Adjust detail level for audience
5. Include SLA/SLO information
6. Add post-mortem scheduling

---

**Last Updated**: 2026-05-14
**Version**: 1.0
