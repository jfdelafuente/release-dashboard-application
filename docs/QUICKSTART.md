# Quick Start Guide

Get started with the Release Dashboard Application in 5 minutes.

## 5-Minute Setup

### Prerequisites
- Python 3.6+ installed
- git installed (optional, for cloning)

### Step 1: Clone or Download Project
```bash
# Option A: Clone from git
git clone <repository-url> release-dashboard
cd release-dashboard

# Option B: Download and extract ZIP
# Extract the project folder and navigate to it
cd release-dashboard
```

### Step 2: Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Step 4: Configure Environment
```bash
# Copy template to local config
cp config/.env.example config/.env

# Edit .env with your settings (optional for development)
# cat config/.env  # View current settings
```

### Step 5: Run Tests
```bash
# Run test suite to verify installation
python -m pytest tests/ -v

# Should output: 258 passed (or similar count)
```

### Step 6: Convert Your First CSV
```bash
# Windows - Incidencias Masivas
scripts\bin\convert_incidents.bat data/input/sample.csv

# Windows - Postmortems
scripts\bin\convert_postmortems.bat data/input/postmortem.csv

# Linux/Mac - Incidencias Masivas
./scripts/bin/convert_incidents.sh data/input/sample.csv

# Linux/Mac - Postmortems
./scripts/bin/convert_postmortems.sh data/input/postmortem.csv
```

**✅ Done!** Your JSON files are now in `data/output/`

### Step 7: View Dashboard Hub (Principal)
```bash
# Option 1: Using Live Server in VSCode (RECOMMENDED)
# Right-click on: src/dashboards/dashboard-hub.html → "Open with Live Server"

# Option 2: Using Python HTTP server
python -m http.server 8000
# Then open: http://localhost:8000/src/dashboards/dashboard-hub.html
```

**Dashboard Hub mostrará automáticamente:**
- 📊 Secciones: Massive Incidents Dashboard y Postmortem Dashboard
- ⚡ KPIs en tiempo real cargados automáticamente
- 🔗 Enlaces a dashboards especializados

## Next Steps

### Option A: Explore Specialized Dashboards
```bash
# From Dashboard Hub, click on:
# - "Massive Incidents Dashboard" para análisis detallado con gráficas temporales
# - "Postmortem Dashboard" para análisis por despliegues
```

### Option B: Processing Your Own Data
```bash
# Place your CSV file in data/input/
cp your-file.csv data/input/

# Convert it
scripts\bin\convert_incidents.bat data/input/your-file.csv

# Check results in data/output/
```

### Option C: Development
```bash
# Read development guide
cat docs/DEVELOPMENT.md

# Or jump to contributing guide
cat CONTRIBUTING.md
```

## Common Tasks

### Convert All CSV Files in a Directory
```bash
scripts\bin\convert_incidents.bat data/input/ -o data/output/
```

### Show Conversion Errors
```bash
scripts\bin\convert_incidents.bat data/input/file.csv --show-errors
```

### Verbose Output
```bash
scripts\bin\convert_incidents.bat data/input/file.csv -v
```

### Get Help
```bash
# Display converter help
scripts\bin\convert_incidents.bat --help

# Read API documentation
cat docs/API.md
```

## Troubleshooting

### "Python not found"
```bash
# Verify Python is installed
python --version

# If not found, install from: https://www.python.org/
```

### "Module not found"
```bash
# Ensure virtual environment is activated
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### "Permission denied" (Linux/Mac)
```bash
# Make scripts executable
chmod +x scripts/bin/*.sh
```

### Conversion Errors
```bash
# Check error report
cat data/errors/your-file_errors.json

# For detailed troubleshooting
cat docs/TROUBLESHOOTING.md
```

### Dashboard Hub Not Loading Data
```bash
# Issue: Dashboard shows "Loading..." or error message

# Solution 1: Make sure you're using HTTP server, not file://
# ✅ Correct: http://localhost:8000/src/dashboards/dashboard-hub.html
# ❌ Wrong: file:///C:/Users/.../dashboard-hub.html (blocks CORS)

# Solution 2: Verify data/output/ has JSON files
ls data/output/
# Should show: *.json files and index.json

# Solution 3: Check browser console (F12) for errors
# - Open DevTools → Console
# - Look for fetch errors or 404s
# - Verify: GET http://127.0.0.1:5500/data/output/index.json (should be 200)
```

## Documentation

- **Full Setup**: [DEVELOPMENT.md](DEVELOPMENT.md)
- **API Reference**: [API.md](API.md)
- **Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **Deployment**: [DEPLOYMENT.md](DEPLOYMENT.md)
- **Troubleshooting**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Contributing**: [../CONTRIBUTING.md](../CONTRIBUTING.md)

## Project Structure

```
release-dashboard-application/
├── src/
│   ├── converters/          # Python CSV→JSON converters
│   └── dashboards/          # HTML/CSS dashboards
├── scripts/bin/             # Converter wrapper scripts
├── data/
│   ├── input/               # Place your CSV files here
│   ├── output/              # Generated JSON files
│   └── errors/              # Validation error reports
├── config/                  # Configuration templates
├── docs/                    # Documentation
└── tests/                   # Test suite
```

## Key Files

| File | Purpose |
|------|---------|
| `src/dashboards/dashboard-hub.html` | **Principal dashboard** - Unified access point |
| `scripts/bin/convert_incidents.bat` | Windows converter for massive incidents |
| `scripts/bin/convert_incidents.sh` | Linux/Mac converter for massive incidents |
| `scripts/bin/convert_postmortems.bat` | Windows converter for postmortems |
| `scripts/bin/convert_postmortems.sh` | Linux/Mac converter for postmortems |
| `config/.env` | Environment configuration |
| `data/input/` | CSV input folder |
| `data/output/` | Generated JSON output |
| `src/dashboards/massive-incidents-dashboard.html` | Specialized dashboard - massive incidents analysis |
| `src/dashboards/postmortem-dashboard.html` | Specialized dashboard - postmortem analysis |

## Next: Deploy to Production

Once you're comfortable with local usage:

1. Read [DEPLOYMENT.md](DEPLOYMENT.md) for deployment procedures
2. Configure [GitHub Secrets](../SECURITY.md) for production
3. Review [CONTRIBUTING.md](../CONTRIBUTING.md) for code standards
4. Start contributing!

---

**Estimated Time**: 5 minutes
**Difficulty**: Beginner
**Last Updated**: 2026-05-14
