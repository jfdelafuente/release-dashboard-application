# Project Directory Structure Guide

Complete guide to the Release Dashboard Application directory organization.

## Directory Tree

```
release-dashboard-application/
│
├── src/                                 # Source code (organized by type)
│   │
│   ├── converters/                     # CSV-to-JSON converter modules
│   │   ├── __init__.py
│   │   ├── convert_incidents.py        # Massive incidents converter
│   │   ├── convert_postmortems.py      # Post-mortem incidents converter
│   │   └── csv_to_json/                # Shared converter module
│   │       ├── __init__.py
│   │       ├── converter.py            # Main converter logic
│   │       ├── encoding.py             # Encoding detection
│   │       ├── delimiter.py            # Delimiter detection
│   │       ├── normalizers.py          # Field normalization
│   │       ├── validators.py           # Data validation
│   │       └── schemas.py              # Field definitions
│   │
│   └── dashboards/                     # Frontend dashboards (HTML + CSS)
│       ├── massive-incidents-dashboard.html
│       ├── postmortem-dashboard.html
│       ├── dashboard-hub.html
│       └── assets/
│           ├── css/
│           │   ├── dashboard-hub.css
│           │   └── [dashboard-specific styles]
│           └── js/                     # JavaScript utilities (future)
│
├── scripts/                             # Executable scripts (organized by function)
│   │
│   ├── bin/                            # Converter wrapper scripts
│   │   ├── convert_incidents.bat       # Windows wrapper
│   │   ├── convert_incidents.sh        # Unix wrapper
│   │   ├── convert_postmortems.bat     # Windows wrapper
│   │   └── convert_postmortems.sh      # Unix wrapper
│   │
│   └── deploy/                         # Deployment automation scripts
│       ├── deploy.sh                   # Production deployment
│       ├── rollback.sh                 # Rollback procedure
│       ├── install-hooks.sh            # Git hook setup
│       └── health-check.sh             # Health verification
│
├── data/                                # Data storage (git-ignored) ⚠️
│   │
│   ├── input/                          # CSV input files (place files here)
│   │   └── .gitkeep                    # Ensures directory persists in git
│   │
│   ├── output/                         # Generated JSON files (dashboards load from here)
│   │   ├── index.json                  # Searchable index of converted files
│   │   └── .gitkeep
│   │
│   ├── errors/                         # Error reports from conversions
│   │   └── .gitkeep
│   │
│   └── archive/                        # Historical data (optional archiving)
│       └── YYYY/MM/                    # Organized by year/month
│           └── .gitkeep
│
├── config/                             # Configuration templates
│   ├── .env.example                    # Environment variable template (committed)
│   ├── .env.development                # Development defaults (committed)
│   ├── .env.staging                    # Staging config (git-ignored)
│   ├── .env.production                 # Production config (git-ignored)
│   ├── pre-commit-hook.sh              # Git hook to prevent secret commits
│   └── SECRET-MANAGEMENT.md            # Secret handling documentation
│
├── docs/                               # Project documentation
│   ├── README.md                       # Project overview (this is in root, symlinked)
│   ├── CONTRIBUTING.md                 # Development guidelines
│   ├── DEVELOPMENT.md                  # Local setup guide
│   ├── DEPLOYMENT.md                   # Deployment procedures
│   ├── ARCHITECTURE.md                 # System design
│   ├── API.md                          # API documentation
│   ├── CI-CD.md                        # GitHub Actions workflows
│   ├── TROUBLESHOOTING.md              # Common issues & solutions
│   └── QUICKSTART.md                   # 8-step setup guide
│
├── tests/                              # Test suite
│   ├── __init__.py
│   ├── unit/                           # Unit tests for modules
│   │   ├── __init__.py
│   │   ├── test_converter.py
│   │   ├── test_encoding.py
│   │   ├── test_validation.py
│   │   └── test_normalizers.py
│   ├── integration/                    # End-to-end integration tests
│   │   ├── __init__.py
│   │   └── test_conversion_workflow.py
│   └── fixtures/                       # Test data
│       ├── sample_utf8.csv
│       ├── sample_windows1252.csv
│       └── sample_output.json
│
├── .github/                            # GitHub configuration
│   ├── workflows/                      # CI/CD pipelines
│   │   ├── tests.yml                   # Run tests & coverage
│   │   ├── lint.yml                    # Code quality checks
│   │   └── deploy.yml                  # Deployment automation
│   └── ISSUE_TEMPLATE/                 # Issue templates
│       ├── bug.md
│       └── feature.md
│
├── .gitignore                          # Git ignore patterns
├── CLAUDE.md                           # Development guidance for Claude AI
├── CONTRIBUTING.md                     # Contributing guidelines
├── DIRECTORY-STRUCTURE.md              # This file
├── SECURITY.md                         # Security practices
├── CHANGELOG.md                        # Release history
├── README.md                           # Project overview
├── VERSION                             # Semantic version (0.1.0)
├── requirements.txt                    # Production dependencies
├── requirements-dev.txt                # Development dependencies
└── pytest.ini                          # Pytest configuration
```

## Directory Purposes

### src/ - Source Code (Organized by Type)

**Purpose**: All production code, organized by functionality

**Key Directories**:
- `src/converters/`: CSV-to-JSON conversion logic
- `src/dashboards/`: Interactive visualizations (HTML/CSS)
- `src/dashboards/assets/`: Shared resources (CSS, JS)

**When to add files here**:
- Python converters, utilities, modules
- HTML dashboards and visualization code
- Asset files (stylesheets, images)

**Convention**: Group by type (converters, dashboards), not by project

### scripts/ - Executable Scripts (Organized by Function)

**Purpose**: Executable scripts and automation tools, organized by purpose

**Key Directories**:
- `scripts/bin/`: Wrapper scripts that call converter modules
- `scripts/deploy/`: Deployment, rollback, and health-check scripts

**When to add files here**:
- Shell scripts (.sh for Unix, .bat for Windows)
- Deployment automation
- System administration tools
- Convenience wrappers around Python modules

**Convention**: Use bash/batch, not Python (unless system-level script)

### data/ - Data Storage (⚠️ Git-Ignored for Security)

**Purpose**: Input/output data directories (NEVER committed to git)

**Key Directories**:
- `data/input/`: User uploads CSV files here
- `data/output/`: Converted JSON files (dashboards load from here)
- `data/errors/`: Error reports with validation details
- `data/archive/`: Historical data organized by YYYY/MM/

**CRITICAL**: All contents are git-ignored:
```gitignore
data/              # Entire directory git-ignored
```

**When to add files here**:
- User uploads CSV data
- Converter generates JSON
- Validation errors are reported
- Historical archives (30+ days old)

**NOT here**:
- ❌ Configuration files (use config/)
- ❌ Source code (use src/)
- ❌ Scripts (use scripts/)
- ❌ Tests (use tests/)

### config/ - Configuration Templates

**Purpose**: Environment configuration files and documentation

**Key Files**:
- `.env.example`: Template for all environment variables
- `.env.development`: Development defaults (safe to commit)
- `.env.staging`: Staging secrets (git-ignored)
- `.env.production`: Production secrets (git-ignored)
- `pre-commit-hook.sh`: Prevents secret commits
- `SECRET-MANAGEMENT.md`: Documentation on secret handling

**When to add files here**:
- Environment variable templates
- Configuration examples
- Setup documentation
- Hook scripts

**Convention**: `.env` files follow: `.env.{environment-name}`

### docs/ - Project Documentation

**Purpose**: User-facing and developer documentation

**Key Files**:
- `README.md`: Project overview and quick start
- `CONTRIBUTING.md`: Coding standards and PR process
- `DEVELOPMENT.md`: Local development setup
- `DEPLOYMENT.md`: Deployment procedures
- `ARCHITECTURE.md`: System design and data flow
- `API.md`: API documentation for converters
- `TROUBLESHOOTING.md`: Common issues and solutions
- `QUICKSTART.md`: 8-step setup guide

**When to add files here**:
- User-facing documentation
- API reference
- Guides and tutorials
- Troubleshooting information

**Root-level Documentation Files**:
- `README.md` (also in root for GitHub)
- `CONTRIBUTING.md` (root for GitHub recognition)
- `MIGRATION.md` (root for visibility)
- `SECURITY.md` (root for security)
- `CHANGELOG.md` (root for releases)

### tests/ - Test Suite

**Purpose**: Automated tests organized by type

**Key Directories**:
- `tests/unit/`: Unit tests for individual functions/modules
- `tests/integration/`: End-to-end workflow tests
- `tests/fixtures/`: Test data (sample CSV, expected JSON)

**When to add files here**:
- Unit tests for Python modules (mirrors src/ structure)
- Integration tests for complete workflows
- Test fixtures and sample data
- Pytest configuration

**Convention**: Mirror src/ directory structure for unit tests:
```
src/converters/converter.py     → tests/unit/test_converter.py
src/converters/encoding.py      → tests/unit/test_encoding.py
```

### .github/ - GitHub Configuration

**Purpose**: GitHub-specific configuration

**Key Directories**:
- `.github/workflows/`: CI/CD pipeline definitions (YAML)
- `.github/ISSUE_TEMPLATE/`: Templates for issues and PRs

**Key Files**:
- `tests.yml`: Run pytest, check coverage ≥80%
- `lint.yml`: Run flake8, pylint, black
- `deploy.yml`: Auto-deploy to staging, manual approval for production

**Convention**: Workflows are triggered automatically by GitHub events

---

## Quick Navigation

### "Where do I put...?"

| What? | Where? | Example |
|-------|--------|---------|
| Python converter module | `src/converters/` | `src/converters/convert_incidents.py` |
| HTML dashboard | `src/dashboards/` | `src/dashboards/massive-incidents-dashboard.html` |
| Dashboard CSS | `src/dashboards/assets/css/` | `src/dashboards/assets/css/dashboard-hub.css` |
| Shell script wrapper | `scripts/bin/` | `scripts/bin/convert_incidents.sh` |
| Deployment script | `scripts/deploy/` | `scripts/deploy/deploy.sh` |
| User CSV input | `data/input/` | `data/input/cs-masiva-202605.csv` |
| Generated JSON | `data/output/` | `data/output/cs-masiva-202605.json` |
| Conversion errors | `data/errors/` | `data/errors/cs-masiva-202605_errors.json` |
| Config template | `config/` | `config/.env.example` |
| Setup guide | `docs/` | `docs/DEVELOPMENT.md` |
| Unit tests | `tests/unit/` | `tests/unit/test_converter.py` |
| Integration tests | `tests/integration/` | `tests/integration/test_conversion_workflow.py` |
| Test data | `tests/fixtures/` | `tests/fixtures/sample.csv` |
| CI/CD workflows | `.github/workflows/` | `.github/workflows/tests.yml` |

### "Find me a ..."

| Looking for | Start at | Command |
|-------------|----------|---------|
| CSV converter | `src/converters/` | `ls src/converters/` |
| Dashboard | `src/dashboards/` | `ls src/dashboards/` |
| Documentation | `docs/` | `ls docs/` |
| Test | `tests/` | `ls tests/` |
| Your CSV input | `data/input/` | `ls data/input/` |
| Generated JSON | `data/output/` | `ls data/output/` |
| Conversion errors | `data/errors/` | `ls data/errors/` |

---

## Important Notes

### Git-Ignored Directories ⚠️

**Never committed** (protected by .gitignore):
- `data/` (all subdirectories)
- `.env*` (configuration files)
- `venv/` (Python virtual environment)
- `__pycache__/` (Python cache)
- `.coverage`, `htmlcov/` (test coverage reports)
- `.vscode/`, `.idea/` (IDE configuration)

### Persistent Empty Directories

Empty directories don't persist in git. To preserve them:
- `.gitkeep` files added to each data/ subdirectory
- `.gitkeep` is ignored by git but ensures directory exists
- Remove `.gitkeep` when adding actual files

### Naming Conventions

**Python Files**: snake_case
- `convert_incidents.py`
- `test_encoding.py`

**Directories**: lowercase with hyphens (scripts) or underscores (Python)
- `src/converters/` (package)
- `scripts/bin/` (shell scripts)
- `data/input/` (data directory)

**Documentation Files**: UPPER_CASE.md
- `README.md`
- `CONTRIBUTING.md`
- `DIRECTORY-STRUCTURE.md`

**Configuration Files**: lowercase with dots
- `.env.example`
- `.env.development`
- `pytest.ini`

### Directory Size Limits

**data/ directory** can grow large with CSV/JSON files:
- Typical incident: 500 bytes JSON
- 10,000 incidents = 5MB
- 100,000 incidents = 50MB

**Management**:
- Archive old files to `data/archive/`
- Use naming convention to identify dates
- Clean up regularly to prevent disk issues

---

## Related Documentation

- [README.md](README.md) - Project overview
- [CONTRIBUTING.md](CONTRIBUTING.md) - Development standards
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) - Setup guide
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - System design
- [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) - Common issues and solutions

---

**Last Updated**: 2026-05-14
