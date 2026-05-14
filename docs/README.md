# Release Dashboard Application

A web-based application for analyzing and tracking incident management and post-mortem data through interactive dashboards.

## Features

- **Massive Incidents Dashboard**: Real-time analysis of incident data with temporal trends, KPI tracking, and filtering capabilities
- **Postmortem Dashboard**: Analysis of post-mortem reports with segmentation by deployment and urgency
- **CSV-to-JSON Converter**: Automated conversion of incident data from CSV to JSON format with auto-detection of encoding and delimiters
- **Multi-environment Support**: Separate configurations for development, staging, and production
- **Secure Configuration**: Environment-based credential management with no secrets in code

## Technology Stack

- **Backend**: Python 3.6+
- **Frontend**: HTML5, CSS3, JavaScript ES6+
- **Dashboard Visualization**: Plotly.js
- **Testing**: pytest with 80% coverage requirement
- **CI/CD**: GitHub Actions
- **Configuration**: python-dotenv for development, environment variables for production

## Quick Start

For complete setup instructions, see [docs/QUICKSTART.md](docs/QUICKSTART.md).

**Quick version (5 minutes)**:

```bash
# Clone repository
git clone <repository-url>
cd release-dashboard-application

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Configure development environment
cp config/.env.example .env

# Run tests
pytest tests/

# Start dashboard server
python -m http.server 8000

# Visit http://localhost:8000 in your browser
```

## Project Structure

```
release-dashboard-application/
├── src/                        # Source code
│   ├── converters/            # CSV-to-JSON converters
│   └── dashboards/            # HTML/CSS dashboards
│       └── assets/            # CSS and JS assets
├── scripts/                    # Executable scripts
│   ├── bin/                   # Wrapper scripts for converters
│   └── deploy/                # Deployment automation
├── data/                       # Data storage (git-ignored)
│   ├── input/                 # CSV input files
│   ├── output/                # Generated JSON files
│   ├── errors/                # Error reports
│   └── archive/               # Historical data
├── config/                     # Configuration templates
├── docs/                       # Documentation
├── tests/                      # Test suite
├── requirements.txt            # Production dependencies
├── requirements-dev.txt        # Development dependencies
├── VERSION                     # Semantic version
└── .gitignore                 # Git ignore patterns
```

See [DIRECTORY-STRUCTURE.md](DIRECTORY-STRUCTURE.md) for detailed documentation of each directory.

## Development

### Setup Development Environment

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for complete setup instructions.

### Running Tests

```bash
# Run all tests with coverage
pytest tests/ -v --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_converter.py -v

# Run tests matching pattern
pytest tests/ -k "converter" -v
```

### Code Standards

See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) for coding standards, commit message format, and PR process.

## Deployment

### Local Development

```bash
# Start development server
python -m http.server 8000
```

### Staging & Production

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for environment-specific deployment procedures.

### CI/CD Pipeline

GitHub Actions automatically:
- Runs tests and code quality checks on every pull request
- Generates coverage reports
- Auto-deploys to staging on merge to main
- Requires manual approval for production deployment

## Dashboards

### Massive Incidents Dashboard
- **File**: `src/dashboards/massive-incidents-dashboard.html`
- **Features**: Global time filter, KPI cards, temporal charts, incident table with sorting
- **Data Format**: JSON array of incidents (see docs/API.md)
- **Loading Data**: Drag-and-drop JSON file or select from `data/output/` directory

### Postmortem Dashboard
- **File**: `src/dashboards/postmortem-dashboard.html`
- **Features**: Post-mortem analysis, deployment segmentation, impact assessment

## CSV-to-JSON Converter

Converts CSV incident data to JSON format compatible with dashboards.

```bash
# Convert CSV file
python src/converters/convert_incidents.py data/input/incidents.csv

# Output
# ✅ JSON saved: data/output/incidents.json
# ✅ Index updated: data/output/index.json
# ✅ Errors (if any): data/errors/incidents_errors.json
```

See [docs/API.md](docs/API.md) for detailed converter documentation.

## Security

- Secrets are never committed to git (protected by pre-commit hooks)
- Development uses local `.env` file (git-ignored)
- Production uses GitHub Secrets (environment variables injected at deploy time)
- Sensitive files are automatically excluded from version control

See [SECURITY.md](SECURITY.md) for security practices and incident response procedures.

## Support

- **Documentation**: See [docs/](docs/) directory
- **Troubleshooting**: [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
- **Contributing**: [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md)
- **Architecture**: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## Version

Current version: 0.1.0 (see [VERSION](VERSION) file)

See [CHANGELOG.md](CHANGELOG.md) for release history.

## License

[Your License Here]

---

**Status**: Foundation infrastructure complete ✅
**Last Updated**: 2026-05-14
