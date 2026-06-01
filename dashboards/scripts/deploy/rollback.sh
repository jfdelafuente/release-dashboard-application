#!/bin/bash

################################################################################
# Rollback Script: Safe Rollback with Verification
################################################################################
#
# Usage:
#   ./rollback.sh [staging|production] [backup-dir]
#   ./rollback.sh staging backups/deployment-20260514-120000
#   ./rollback.sh production
#
# Features:
#   - Safely restores from backup
#   - Health checks after rollback
#   - Automatic abort if health fails
#   - Rollback logging and audit trail
#
################################################################################

set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================

ENVIRONMENT="${1:-staging}"
BACKUP_DIR="${2:-.}"  # If not specified, uses most recent
DEPLOYER="${DEPLOYER:-${USER}}"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
LOG_DIR="logs/rollback"
ROLLBACK_LOG="${LOG_DIR}/rollback-${ENVIRONMENT}-${TIMESTAMP}.log"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ============================================================================
# Functions
# ============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$ROLLBACK_LOG"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$ROLLBACK_LOG"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$ROLLBACK_LOG"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$ROLLBACK_LOG"
}

create_log_dir() {
    mkdir -p "$LOG_DIR"
}

print_header() {
    echo "===============================================================================" | tee -a "$ROLLBACK_LOG"
    echo "ROLLBACK LOG: $ENVIRONMENT" | tee -a "$ROLLBACK_LOG"
    echo "===============================================================================" | tee -a "$ROLLBACK_LOG"
    echo "Timestamp: $(date -u +'%Y-%m-%dT%H:%M:%SZ')" | tee -a "$ROLLBACK_LOG"
    echo "Environment: $ENVIRONMENT" | tee -a "$ROLLBACK_LOG"
    echo "Deployer: $DEPLOYER" | tee -a "$ROLLBACK_LOG"
    echo "===============================================================================" | tee -a "$ROLLBACK_LOG"
}

validate_environment() {
    log_info "Validating environment: $ENVIRONMENT"

    if [[ ! "$ENVIRONMENT" =~ ^(staging|production)$ ]]; then
        log_error "Invalid environment: $ENVIRONMENT (must be 'staging' or 'production')"
        exit 1
    fi

    log_success "Environment validated"
}

find_latest_backup() {
    log_info "Finding latest backup..."

    LATEST_BACKUP=$(find backups/ -maxdepth 1 -type d -name "deployment-*" \
        -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2- || echo "")

    if [[ -z "$LATEST_BACKUP" ]]; then
        log_error "No backup directories found"
        exit 1
    fi

    log_success "Latest backup found: $LATEST_BACKUP"
    BACKUP_DIR="$LATEST_BACKUP"
}

validate_backup() {
    log_info "Validating backup integrity..."

    if [[ ! -d "$BACKUP_DIR" ]]; then
        log_error "Backup directory not found: $BACKUP_DIR"
        exit 1
    fi

    # Check if backup has required files
    if [[ ! -d "$BACKUP_DIR/src" ]] && [[ ! -d "$BACKUP_DIR/data" ]]; then
        log_error "Backup missing required directories (src or data)"
        exit 1
    fi

    # Check backup is not too old (older than 30 days)
    BACKUP_AGE=$(find "$BACKUP_DIR" -type d -mtime +30 2>/dev/null | wc -l)
    if [[ $BACKUP_AGE -gt 0 ]]; then
        log_warning "Backup is older than 30 days - proceed with caution"
    fi

    log_success "Backup validated"
}

create_current_backup() {
    log_info "Creating backup of current (failed) deployment..."

    FAILED_BACKUP="backups/deployment-failed-${TIMESTAMP}"
    mkdir -p "$FAILED_BACKUP"

    if [[ -d "src" ]]; then
        cp -r src/ "$FAILED_BACKUP/src/" 2>/dev/null || true
    fi
    if [[ -d "data" ]]; then
        cp -r data/ "$FAILED_BACKUP/data/" 2>/dev/null || true
    fi

    log_success "Current state backed up: $FAILED_BACKUP"
}

restore_from_backup() {
    log_info "Restoring from backup: $BACKUP_DIR"

    # Restore src
    if [[ -d "$BACKUP_DIR/src" ]]; then
        log_info "Restoring source code..."
        rm -rf src/ 2>/dev/null || true
        cp -r "$BACKUP_DIR/src/" src/ >> "$ROLLBACK_LOG" 2>&1
        log_success "Source code restored"
    fi

    # Restore data (optional)
    if [[ -d "$BACKUP_DIR/data" ]]; then
        log_info "Restoring data..."
        rm -rf data/ 2>/dev/null || true
        cp -r "$BACKUP_DIR/data/" data/ >> "$ROLLBACK_LOG" 2>&1
        log_success "Data restored"
    fi

    log_success "Rollback to backup completed"
}

health_check_post_rollback() {
    log_info "Running post-rollback health checks..."

    # Verify Python environment
    log_info "Checking Python environment..."
    if ! python -m pytest --co -q >> "$ROLLBACK_LOG" 2>&1; then
        log_error "Python environment check failed after rollback"
        return 1
    fi
    log_success "Python environment OK"

    # Verify converter works
    log_info "Checking converter functionality..."
    if ! python src/converters/convert_incidents.py --help >> "$ROLLBACK_LOG" 2>&1; then
        log_error "Converter check failed after rollback"
        return 1
    fi
    log_success "Converter is functional"

    # Verify dashboard HTML exists
    if [[ ! -f "src/dashboards/dashboard-hub.html" ]]; then
        log_error "Dashboard file missing after rollback"
        return 1
    fi
    log_success "Dashboard file present"

    return 0
}

record_rollback() {
    log_info "Recording rollback in log..."

    ROLLBACK_RECORD=$(cat <<EOF

================================================================================
ROLLBACK RECORD
================================================================================
Environment:     $ENVIRONMENT
Timestamp:       $(date -u +'%Y-%m-%dT%H:%M:%SZ')
Deployer:        $DEPLOYER
Status:          SUCCESS
Rollback From:   $BACKUP_DIR
Failed Backup:   $FAILED_BACKUP
Log:             $ROLLBACK_LOG

Health Checks:   PASSED
Rollback:        COMPLETED
================================================================================
EOF
    )

    echo "$ROLLBACK_RECORD" | tee -a "$ROLLBACK_LOG"

    # Also save to main rollback record file
    echo "$ROLLBACK_RECORD" >> "logs/rollback/ROLLBACK-RECORDS.log"

    log_success "Rollback recorded"
}

abort_rollback() {
    log_error "Rollback failed - MANUAL INTERVENTION REQUIRED"
    log_error "Please review the failed deployment at: $FAILED_BACKUP"
    log_error "Rollback log: $ROLLBACK_LOG"
    exit 1
}

# ============================================================================
# Main Execution
# ============================================================================

main() {
    create_log_dir

    {
        print_header

        validate_environment

        # If backup not specified, find latest
        if [[ "$BACKUP_DIR" == "." ]]; then
            find_latest_backup
        fi

        validate_backup
        create_current_backup
        restore_from_backup

        if ! health_check_post_rollback; then
            abort_rollback
        fi

        record_rollback

        log_success "ROLLBACK COMPLETED SUCCESSFULLY"
        echo ""
        echo "✅ Rollback complete - system restored to previous state"
        echo "📋 Rollback Log: $ROLLBACK_LOG"
        echo "⚠️ Previous (failed) deployment backed up at: $FAILED_BACKUP"
        echo ""
        echo "Next steps:"
        echo "  1. Verify application is working correctly"
        echo "  2. Investigate root cause of deployment failure"
        echo "  3. Create a fix and re-deploy when ready"
        echo ""

        exit 0

    } 2>&1 | tee "$ROLLBACK_LOG"
}

# Trap errors
trap 'abort_rollback' ERR

main "$@"
