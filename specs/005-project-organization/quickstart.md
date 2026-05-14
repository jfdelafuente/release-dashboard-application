# Quick Start: Developer Setup (< 30 minutes)

This guide helps new developers set up a working development environment in under 30 minutes.

## Prerequisites

Verify you have these installed:
- Python 3.6 or higher: `python --version`
- Git: `git --version`
- Text editor (VS Code, Sublime, etc.)

**Time**: 2 minutes (or 10 minutes if installing)

## Step 1: Clone the Repository

```bash
git clone <repository-url>
cd release-dashboard-application
```

**Expected output**: Project files in current directory  
**Time**: 2 minutes

## Step 2: Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

**Expected output**: `(venv)` prompt prefix  
**Time**: 1 minute

## Step 3: Install Dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

**Expected output**: No error messages, dependencies installed  
**Time**: 3-5 minutes

## Step 4: Configure Development Environment

```bash
# Copy example configuration
cp config/.env.example .env

# Edit .env if needed (optional)
# Default values should work for local development
```

**Expected output**: `.env` file created  
**Note**: `.env` is git-ignored, never committed  
**Time**: 1 minute

## Step 5: Run Tests

```bash
pytest tests/
```

**Expected output**: 
```
tests/... PASSED                                     [100%]
============ 42 passed in 2.34s ============
```

**Success criteria**: All tests pass, coverage >= 80%  
**Time**: 2-3 minutes

## Step 6: Start Dashboard

For development, serve the dashboards locally:

```bash
# Using Python built-in server
python -m http.server 8000

# Or using better server (if Node.js available)
npx http-server
```

**Expected output**:
```
Serving HTTP on 0.0.0.0 port 8000 (http://localhost:8000/)
```

Open browser: http://localhost:8000

**Expected**: Dashboard Hub loads in < 2 seconds  
**Time**: 1 minute

## Step 7: Test a Converter

Try converting a test CSV file:

```bash
python convert_incidents.py data/input/CS_Masiva_20260514.csv
```

**Expected output**:
```
[OK] JSON guardado: data/output/CS_Masiva_20260514-massive.json
[OK] Index actualizado: data/output/index.json
```

**Success criteria**: JSON file created in `data/output/`  
**Time**: 1 minute

## Step 8: Load Data into Dashboard

1. Open Dashboard Hub in browser (from Step 6)
2. Click "Select JSON file" button
3. Navigate to `data/output/`
4. Choose any `.json` file
5. Click "Load"

**Expected**: Dashboard loads data and displays KPIs, charts, table  
**Time**: 1 minute

---

## Success! You're Ready to Develop

**Next steps**:
1. Read `CONTRIBUTING.md` for coding standards
2. Check `README.md` for feature overview
3. Explore `docs/ARCHITECTURE.md` for system design
4. Create a feature branch: `git checkout -b feature/your-feature-name`

## Troubleshooting

### Python not found
```bash
# Try python3 explicitly
python3 --version
python3 -m venv venv
```

### Permission denied on `venv/bin/activate`
```bash
# Make executable
chmod +x venv/bin/activate
```

### Tests fail
```bash
# Check Python version (need 3.6+)
python --version

# Check dependencies installed
pip list | grep pytest

# Run with verbose output
pytest tests/ -v
```

### Dashboard doesn't load
```bash
# Check port 8000 is free
netstat -an | grep 8000

# Try different port
python -m http.server 9000
```

### CSV conversion fails
```bash
# Check file exists
ls data/input/

# Check file encoding
file data/input/your-file.csv
```

## Getting Help

1. Check `docs/ARCHITECTURE.md` for system overview
2. Read `CONTRIBUTING.md` for development guidelines
3. Check test examples in `tests/` for code patterns
4. Open an issue in GitHub with error details

---

**Total Setup Time**: 15-30 minutes  
**Expected First Success**: Working dashboard loading data

Welcome to the team!
