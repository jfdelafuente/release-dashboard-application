# Development Setup Guide

Complete guide for setting up a development environment.

## Prerequisites

- Python 3.8 or higher: `python --version`
- Git: `git --version`
- Text editor or IDE (VS Code, PyCharm, Sublime, etc.)

## Step 1: Clone Repository

```bash
git clone <repository-url>
cd release-dashboard-application
```

## Step 2: Create Virtual Environment

### Windows
```bash
python -m venv venv
venv\Scripts\activate
```

### macOS / Linux
```bash
python3 -m venv venv
source venv/bin/activate
```

Expected prompt: `(venv) $ `

## Step 3: Install Dependencies

```bash
# Install production dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt
```

Verify installation:
```bash
pip list | grep pytest
pip list | grep black
```

## Step 4: Configure Development Environment

```bash
# Copy example environment file
cp config/.env.example .env

# Edit .env if needed (most defaults are good for development)
# .env is git-ignored, never committed
```

## Step 5: Verify Installation

Run tests:
```bash
pytest tests/ -v
```

Expected output:
```
tests/... PASSED                           [100%]
============ X passed in Xs ============
```

## Running the Application

### Start Dashboard Server

```bash
python serve_app.py
# Then visit: http://localhost:8000/dashboards/portal/
```

> ⚠️ Don't use `python -m http.server` or Live Server: they only serve
> static files and don't implement `POST`, so uploading a CSV from the
> browser fails with "Failed to fetch". `serve_app.py` adds the
> `/api/upload` endpoint that the dashboards need.

### Convert CSV to JSON

```bash
# Convert incidents CSV
python converters/cli/convert_incidents.py data/input/sample.csv

# Output location: data/output/sample-massive.json
```

See [converters/docs/API.md](../converters/docs/API.md) for detailed converter documentation.

## Development Workflow

### 1. Create Feature Branch

```bash
git checkout -b feature/your-feature-name
```

Branch naming: `feature/`, `bugfix/`, `docs/`, `refactor/`, `test/`

### 2. Make Changes

Edit code in your favorite editor.

### 3. Run Tests

```bash
cd converters

# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/unit/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

### 4. Format Code

```bash
# Auto-format code
black src/ tests/

# Check formatting
flake8 src/ tests/

# Check style
pylint src/ tests/
```

### 5. Commit Changes

```bash
git add src/your_file.py tests/test_your_file.py
git commit -m "feat: describe your change"
```

### 6. Push and Create PR

```bash
git push origin feature/your-feature-name

# Then create pull request on GitHub
```

## Code Organization

See [PROJECT-STRUCTURE.md](PROJECT-STRUCTURE.md) for the full layout. In short:
- Python converters: `converters/cli/` (entry points) + `converters/src/csv_to_json/` (logic)
- Dashboards (HTML/CSS/JS, inline per file, no shared assets folder): `dashboards/`
- Converter tests: `converters/tests/` (there's no top-level `tests/`)
- Batch/cron script: `scripts/generate-dashboards.sh` (there's no `scripts/bin/` or `scripts/deploy/`)

## Common Tasks

### Adding a New Converter

1. Create file: `converters/cli/convert_new_data.py`
2. Implement converter function
3. Add tests: `converters/tests/unit/test_convert_new_data.py`
4. Update [converters/docs/API.md](../converters/docs/API.md) with usage

### Modifying a Dashboard

1. Edit the dashboard's `.html` directly (styles and JS live inline in the same file): `dashboards/dashboard-name.html`
2. Test with `python serve_app.py` (not `http.server`/Live Server — see the warning above): http://localhost:8000/dashboards/dashboard-name.html
3. Update [docs/](.) with any new features

### Running Specific Tests

Run these from `converters/` (that's where `pytest.ini` lives):

```bash
cd converters

# Test file
pytest tests/unit/test_csv_reader.py -v

# Test function
pytest tests/unit/encoding/test_encoding.py::TestEncodingDetection::test_detect_utf8 -v

# By pattern
pytest tests/ -k "csv" -v
```

## Git Hooks (Pre-commit)

The repository includes pre-commit hooks to prevent committing secrets:

```bash
# Install the hook (one-time setup)
cp config/pre-commit-hook.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

# Runs automatically on: git commit

# To run manually:
bash config/pre-commit-hook.sh
```

The hook prevents committing:
- `.env` files
- Files containing API keys or passwords
- Secrets or credentials

## Troubleshooting

### Python Version Error

```bash
# If python command not found, try python3
python3 --version
python3 -m venv venv

# Or set alias
alias python=python3
```

### Virtual Environment Not Activating

```bash
# Windows - try different activation method
venv\Scripts\activate.bat    # Command Prompt
venv\Scripts\Activate.ps1    # PowerShell

# macOS / Linux
source venv/bin/activate
```

### Permission Denied

```bash
# Make scripts executable
chmod +x converters/scripts/bin/*.sh
chmod +x scripts/generate-dashboards.sh
```

### Pytest Not Found

```bash
# Make sure venv is activated
which python  # Should be in venv directory
pip install -r requirements-dev.txt
```

### Port Already in Use

```bash
# Use different port
python -m http.server 9000

# Visit http://localhost:9000
```

## IDE Setup

### VS Code

Install extensions:
- Python
- Pylance
- Python Docstring Generator
- Black Formatter
- Flake8

Create `.vscode/settings.json`:
```json
{
  "python.formatting.provider": "black",
  "python.linting.flake8Enabled": true,
  "python.linting.pylintEnabled": true,
  "[python]": {
    "editor.formatOnSave": true
  }
}
```

### PyCharm

- Automatically configures Python venv
- Configure code formatter: Settings → Code Style → Python
- Configure linting: Settings → Tools → Python Integrated Tools

## Performance Testing

### Check Converter Speed

```bash
import time
start = time.time()
# run converter
end = time.time()
print(f"Conversion took {end - start:.2f}s")

# Target: < 5 seconds for 1000+ records
```

### Profile Code

```bash
python -m cProfile -s cumulative src/converters/convert_incidents.py data/input/sample.csv
```

## Learning Resources

- [Python Official Docs](https://docs.python.org/3/)
- [Pytest Documentation](https://docs.pytest.org/)
- [Git Documentation](https://git-scm.com/doc)
- [Markdown Guide](https://www.markdownguide.org/)

## Next Steps

1. Read [CONTRIBUTING.md](CONTRIBUTING.md) for coding standards
2. Review [DIRECTORY-STRUCTURE.md](../DIRECTORY-STRUCTURE.md) for file organization
3. Check [converters/docs/API.md](../converters/docs/API.md) for API documentation
4. Explore existing code in `src/` for patterns

---

**Setup Time**: 15-30 minutes
**Last Updated**: 2026-05-14
