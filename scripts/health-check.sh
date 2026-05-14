#!/bin/bash

################################################################################
# Health Check Script: Verify Application Health
################################################################################
#
# Usage:
#   ./health-check.sh [staging|production|local]
#   ./health-check.sh staging
#   ./health-check.sh local
#
# Exit Codes:
#   0 = All checks passed
#   1 = One or more checks failed
#
# Features:
#   - HTTP endpoint verification
#   - Python converter functionality
#   - Dashboard file availability
#   - Data directory structure
#   - Disk space monitoring
#
################################################################################

set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================

ENVIRONMENT="${1:-local}"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
LOG_DIR="logs/health-checks"
HEALTH_LOG="${LOG_DIR}/health-check-${ENVIRONMENT}-${TIMESTAMP}.log"

# URLs per environment
declare -A URLS=(
    [local]="http://localhost:8000"
    [staging]="${STAGING_URL:-https://staging.example.com}"
    [production]="${PRODUCTION_URL:-https://example.com}"
)

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Tracking
CHECKS_PASSED=0
CHECKS_FAILED=0

# ============================================================================
# Functions
# ============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$HEALTH_LOG"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1" | tee -a "$HEALTH_LOG"
    ((CHECKS_PASSED++))
}

log_error() {
    echo -e "${RED}[✗]${NC} $1" | tee -a "$HEALTH_LOG"
    ((CHECKS_FAILED++))
}

log_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1" | tee -a "$HEALTH_LOG"
}

create_log_dir() {
    mkdir -p "$LOG_DIR"
}

print_header() {
    echo "===============================================================================" | tee -a "$HEALTH_LOG"
    echo "HEALTH CHECK: $ENVIRONMENT" | tee -a "$HEALTH_LOG"
    echo "===============================================================================" | tee -a "$HEALTH_LOG"
    echo "Timestamp: $(date -u +'%Y-%m-%dT%H:%M:%SZ')" | tee -a "$HEALTH_LOG"
    echo "Environment: $ENVIRONMENT" | tee -a "$HEALTH_LOG"
    echo "===============================================================================" | tee -a "$HEALTH_LOG"
}

# ============================================================================
# Health Checks
# ============================================================================

check_http_endpoint() {
    local url="$1"
    log_info "Checking HTTP endpoint: $url"

    if curl -s -I -m 5 "$url" > /dev/null 2>&1; then
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$url")
        if [[ "$HTTP_CODE" == "200" ]]; then
            log_success "HTTP endpoint responding (HTTP $HTTP_CODE)"
            return 0
        else
            log_error "HTTP endpoint returned $HTTP_CODE (expected 200)"
            return 1
        fi
    else
        log_error "HTTP endpoint not reachable: $url"
        return 1
    fi
}

check_dashboard_files() {
    log_info "Checking dashboard files..."

    DASHBOARD_FILE="src/dashboards/dashboard-hub.html"

    if [[ -f "$DASHBOARD_FILE" ]]; then
        log_success "Dashboard file exists: $DASHBOARD_FILE"
    else
        log_error "Dashboard file missing: $DASHBOARD_FILE"
        return 1
    fi

    # Check CSS
    if [[ -f "src/dashboards/assets/css/dashboard-hub.css" ]]; then
        log_success "Dashboard CSS file exists"
    else
        log_warning "Dashboard CSS file missing (may use remote CDN)"
    fi

    # Check JS
    if [[ -f "src/dashboards/assets/js/dashboard-hub.js" ]]; then
        log_success "Dashboard JS file exists"
    else
        log_warning "Dashboard JS file missing"
    fi

    return 0
}

check_python_environment() {
    log_info "Checking Python environment..."

    if ! python --version > /dev/null 2>&1; then
        log_error "Python not installed"
        return 1
    fi

    PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
    log_success "Python installed: $PYTHON_VERSION"

    # Check if pytest available
    if ! python -m pytest --version > /dev/null 2>&1; then
        log_error "pytest not available"
        return 1
    fi

    PYTEST_VERSION=$(python -m pytest --version 2>&1 | head -1)
    log_success "pytest available: $PYTEST_VERSION"

    return 0
}

check_converter_functionality() {
    log_info "Checking converter functionality..."

    if [[ ! -f "src/converters/convert_incidents.py" ]]; then
        log_error "Converter script missing: src/converters/convert_incidents.py"
        return 1
    fi

    # Try to get help
    if python src/converters/convert_incidents.py --help > /dev/null 2>&1; then
        log_success "Converter is executable and responsive"
    else
        log_error "Converter command failed"
        return 1
    fi

    return 0
}

check_data_structure() {
    log_info "Checking data directory structure..."

    DIRS=(
        "data/input"
        "data/output"
        "data/errors"
        "data/archive"
    )

    local all_exist=true
    for dir in "${DIRS[@]}"; do
        if [[ -d "$dir" ]]; then
            log_success "Directory exists: $dir"
        else
            log_warning "Directory missing: $dir (will be created on first use)"
            all_exist=false
        fi
    done

    return 0
}

check_json_files() {
    log_info "Checking JSON data files..."

    if [[ -f "data/output/index.json" ]]; then
        FILE_SIZE=$(du -h "data/output/index.json" | cut -f1)
        log_success "index.json exists (${FILE_SIZE})"

        # Validate JSON syntax
        if python -m json.tool data/output/index.json > /dev/null 2>&1; then
            log_success "index.json is valid JSON"
        else
            log_error "index.json is invalid JSON"
            return 1
        fi
    else
        log_warning "index.json not found (run converters first)"
    fi

    return 0
}

check_disk_space() {
    log_info "Checking disk space..."

    USAGE=$(df . | awk 'NR==2 {print $5}' | sed 's/%//')
    AVAILABLE=$(df . | awk 'NR==2 {print $4}')

    if [[ $USAGE -lt 85 ]]; then
        log_success "Disk usage: ${USAGE}% (${AVAILABLE}K available)"
    else
        log_error "Disk usage: ${USAGE}% - LOW SPACE"
        return 1
    fi

    return 0
}

check_logs_directory() {
    log_info "Checking logs directory..."

    if [[ -d "logs" ]]; then
        LOG_SIZE=$(du -sh logs/ | cut -f1)
        log_success "Logs directory exists (${LOG_SIZE})"

        # Check log files not too large (> 500MB)
        MAX_LOG_SIZE=$(find logs/ -type f -size +500M | wc -l)
        if [[ $MAX_LOG_SIZE -gt 0 ]]; then
            log_warning "Some log files are very large (> 500MB)"
        fi
    else
        log_warning "Logs directory missing (will be created on first use)"
    fi

    return 0
}

check_requirements_met() {
    log_info "Checking requirements.txt..."

    if [[ -f "requirements.txt" ]]; then
        if python -m pip check > /dev/null 2>&1; then
            log_success "All Python requirements satisfied"
        else
            log_warning "Some Python requirements may not be installed"
        fi
    else
        log_error "requirements.txt not found"
        return 1
    fi

    return 0
}

check_git_status() {
    log_info "Checking git status..."

    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        log_warning "Not a git repository"
        return 0
    fi

    if [[ -z "$(git status --porcelain)" ]]; then
        log_success "Git working directory is clean"
    else
        log_warning "Git working directory has uncommitted changes"
    fi

    return 0
}

# ============================================================================
# Reporting
# ============================================================================

print_summary() {
    echo "" | tee -a "$HEALTH_LOG"
    echo "===============================================================================" | tee -a "$HEALTH_LOG"
    echo "HEALTH CHECK SUMMARY" | tee -a "$HEALTH_LOG"
    echo "===============================================================================" | tee -a "$HEALTH_LOG"
    echo -e "Passed: ${GREEN}${CHECKS_PASSED}${NC}" | tee -a "$HEALTH_LOG"
    echo -e "Failed: ${RED}${CHECKS_FAILED}${NC}" | tee -a "$HEALTH_LOG"
    echo "===============================================================================" | tee -a "$HEALTH_LOG"
    echo "" | tee -a "$HEALTH_LOG"

    if [[ $CHECKS_FAILED -eq 0 ]]; then
        echo -e "${GREEN}✅ ALL CHECKS PASSED${NC}" | tee -a "$HEALTH_LOG"
        return 0
    else
        echo -e "${RED}❌ SOME CHECKS FAILED${NC}" | tee -a "$HEALTH_LOG"
        return 1
    fi
}

# ============================================================================
# Main Execution
# ============================================================================

main() {
    create_log_dir

    {
        print_header

        # Environment-specific checks
        if [[ "$ENVIRONMENT" == "local" ]]; then
            log_info "Running local health checks..."
            check_dashboard_files
            check_python_environment
            check_converter_functionality
            check_data_structure
            check_json_files
            check_disk_space
            check_logs_directory
            check_requirements_met
            check_git_status

        elif [[ "$ENVIRONMENT" =~ ^(staging|production)$ ]]; then
            log_info "Running remote ($ENVIRONMENT) health checks..."
            check_http_endpoint "${URLS[$ENVIRONMENT]}"
            check_disk_space
            check_logs_directory

        else
            log_error "Unknown environment: $ENVIRONMENT"
            exit 1
        fi

        print_summary

    } 2>&1 | tee "$HEALTH_LOG"

    exit $?
}

main "$@"
