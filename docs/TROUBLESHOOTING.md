# Troubleshooting Guide

Solutions for common issues when setting up and running the Release Dashboard Application.

## CSV Upload Issues

### "Failed to fetch" When Uploading a CSV

**Symptom**: Clicking "Seleccionar archivo" / dragging a CSV shows an alert `Error: Failed to fetch`.

**Cause**: The dashboard is being served by something that doesn't implement `POST` — usually `python -m http.server` or VS Code's Live Server. Both only serve static files, so the browser's request to `/api/upload` never gets a response at all.

**Solution**:
```bash
# Stop whatever is serving port 8000, then from the project root:
python serve_app.py
# Open: http://localhost:8000/dashboards/portal/
```

`serve_app.py` adds the `POST /api/upload` handler (saves the CSV to `data/input/`, runs the matching converter via `converters/cli/upload_csv.py`). If you only need to view already-generated JSON and don't need to upload anything, `http.server`/Live Server are fine.

### Upload Succeeds but Shows "Falló la conversión a JSON"

**Symptom**: The upload response has `"success": false` with a `details` field showing converter output.

**Cause**: The CSV itself failed validation (wrong columns, bad encoding, invalid enum values, etc.) — the `details` field is the converter's own stdout/stderr, truncated to 4000 characters.

**Solution**: Read the `details` text — it names the exact row/field that failed. Check [converters/docs/API.md](../converters/docs/API.md) for the expected column names and allowed values.

## Setup Issues

### Python Not Found

**Symptom**: "python: command not found" or "python is not recognized"

**Cause**: Python 3.8+ is not installed or not in system PATH

**Solution**:
```bash
# Check if Python is installed
python --version
python3 --version

# If neither works, install Python from: https://www.python.org/
# Windows: Download installer, check "Add Python to PATH" during installation
# Mac: brew install python3
# Linux: sudo apt install python3
```

### Virtual Environment Activation Failed

**Symptom**: "venv\Scripts\activate.bat" fails or "activate: command not found"

**Cause**: Virtual environment wasn't created properly

**Solution**:
```bash
# Delete old venv and recreate
rm -rf venv/  # Linux/Mac: rm -rf venv

# Create new virtual environment
python -m venv venv

# Activate properly
# Windows: venv\Scripts\activate
# Linux/Mac: source venv/bin/activate

# Verify
python --version  # Should show Python 3.6+
```

### "No module named 'csv_to_json'"

**Symptom**: ModuleNotFoundError when running converter

**Cause**: Running from wrong directory or Python path issue

**Solution**:
```bash
# Ensure you're in project root
cd /path/to/release-dashboard-application

# Verify you're in the right place
ls converters/src/csv_to_json/

# Try running from project root
python converters/cli/convert_incidents.py data/input/sample.csv
```

### Pip Install Fails

**Symptom**: "ERROR: Could not find a version that satisfies the requirement"

**Cause**: Internet connectivity or Python version mismatch

**Solution**:
```bash
# Update pip first
python -m pip install --upgrade pip

# Install with verbose output to see errors
pip install -r requirements.txt -v

# If specific package fails, install it individually
pip install python-dotenv

# Check Python version compatibility
python --version  # Should be 3.8+
```

## Converter Issues

### Converter Script Not Found

**Symptom**: "command not found: convert_incidents.sh" or ".bat file not found"

**Cause**: Scripts are in wrong location or permissions issue

**Solution**:

**Windows**:
```batch
REM Scripts are in converters\scripts\bin\
converters\scripts\bin\convert_incidents.bat data\input\sample.csv
```

**Linux/Mac**:
```bash
# Make scripts executable
chmod +x converters/scripts/bin/*.sh

# Run from project root
./converters/scripts/bin/convert_incidents.sh data/input/sample.csv
```

Cross-platform alternative, no wrapper script needed: `python converters/cli/convert_incidents.py data/input/sample.csv`.

### "Input file not found"

**Symptom**: Error when running converter, says input CSV not found

**Cause**: CSV file doesn't exist at specified path

**Solution**:
```bash
# List files in input directory
ls data/input/

# Create input directory if it doesn't exist
mkdir -p data/input/

# Place CSV file in data/input/
cp your-file.csv data/input/

# Run converter with correct path
convert_incidents.bat data/input/your-file.csv
```

### Encoding Error: "UnicodeDecodeError"

**Symptom**: "UnicodeDecodeError: 'utf-8' codec can't decode byte"

**Cause**: CSV file has unsupported encoding

**Solution**:
```bash
# The converter auto-detects encoding, but if it fails:
# 1. Open the CSV file in your editor
# 2. Save it as UTF-8 encoding:
#    - VS Code: Select "UTF-8" in bottom right
#    - Excel: File > Save As > CSV UTF-8
#    - LibreOffice: File > Save As > Character Set: UTF-8

# 3. Try conversion again
convert_incidents.bat data/input/your-file.csv -v
```

### "Invalid delimiter"

**Symptom**: JSON output looks wrong (columns merged or missing)

**Cause**: CSV uses unusual delimiter that auto-detector missed

**Solution**:
```bash
# The converter tries to auto-detect: comma, semicolon, tab
# If that doesn't work:
# 1. Open CSV in text editor (not Excel)
# 2. Look at first line to identify delimiter
# 3. Convert to use comma or semicolon
# 4. Re-run converter

# If using custom delimiter, report in docs/
convert_incidents.bat data/input/file.csv --verbose
```

### Validation Errors: "X records failed"

**Symptom**: Conversion completes but says "X records have validation errors"

**Cause**: CSV contains invalid data values

**Solution**:
```bash
# Check error report
cat data/errors/your-file_errors.json

# Or display error summary
convert_incidents.bat data/input/your-file.csv --show-errors

# Fix errors according to rules (see docs/API.md):
# - Urgencia: must be Baja, Media, Alta, or Crítica
# - Estatus: must be Abierto, Cerrado, Resuelto, or Pendiente
# - Fecha: must be dd/mm/yyyy HH:mm AM/PM

# Re-run after fixing CSV
convert_incidents.bat data/input/your-file.csv
```

## Dashboard Issues

### Dashboard Won't Load

**Symptom**: Blank page or "Cannot find file" in browser

**Cause**: JSON file not in correct location

**Solution**:
```bash
# Verify JSON was created
ls data/output/

# If no JSON files, run converter first
converters/scripts/bin/convert_incidents.sh data/input/sample.csv

# Serve the dashboards over HTTP — do NOT open the .html file directly
# (file://): fetch() calls to /data/output/index.json need a real server.
# `python -m http.server` works for read-only viewing (run it from the
# repo root, not from dashboards/), but only serve_app.py implements the
# /api/upload endpoint needed to upload a CSV from the browser.
python serve_app.py
# Then open: http://localhost:8000/dashboards/portal/
```

### Dashboard Showing Empty Data

**Symptom**: Dashboard loads but shows no incidents

**Cause**: JSON format mismatch or wrong file location

**Solution**:
```bash
# Verify JSON file is in data/output/
ls -la data/output/

# Check JSON format
cat data/output/your-file.json | head -20

# Should start with: [{ "ID de incidencia": "...", ...

# If JSON is invalid, check error report
cat data/errors/your-file_errors.json

# Re-generate if needed
convert_incidents.bat data/input/your-file.csv -v
```

## Testing Issues

### Tests Failing

**Symptom**: "FAILED tests/..." when running `pytest`

**Cause**: Missing dependencies or test data

**Solution**:
```bash
# Ensure dev dependencies are installed
pip install -r requirements-dev.txt

# Run tests with verbose output
python -m pytest tests/ -v

# Run specific test
python -m pytest tests/unit/test_encoding.py -v

# Check coverage
python -m pytest --cov=csv_to_json tests/
```

### Coverage Below 80%

**Symptom**: "Coverage failure: total of X% is less than fail-under=80%"

**Cause**: New code without tests

**Solution**:
```bash
# View coverage report
open htmlcov/index.html

# Write tests for uncovered code
# Place in tests/unit/test_<module>.py

# Run coverage again
python -m pytest --cov=csv_to_json --cov-report=html tests/
```

## Configuration Issues

### .env File Not Found

**Symptom**: "FileNotFoundError: [Errno 2] No such file or directory: '.env'"

**Cause**: .env file doesn't exist

**Solution**:
```bash
# Create .env from template
cp config/.env.example config/.env

# Or copy to root if needed
cp config/.env.example .env

# Edit with your settings
# nano config/.env  # or use your editor
```

### Environment Variables Not Loading

**Symptom**: Config values are None or default values

**Cause**: .env file not in right location or not loaded

**Solution**:
```bash
# .env should be in project root or config/ directory
ls config/.env
ls .env

# Check that python-dotenv is installed
pip list | grep python-dotenv

# If not installed
pip install python-dotenv
```

## Performance Issues

### Converter Very Slow

**Symptom**: Takes >5 seconds to convert 1000 records

**Cause**: Disk I/O or system resources

**Solution**:
```bash
# Use verbose mode to see progress
convert_incidents.bat data/input/large-file.csv -v

# Normal speed: ~1000 records/second
# If much slower, check:
# 1. Disk space (should have >100MB free)
# 2. System RAM (check Task Manager/Activity Monitor)
# 3. File size (if >1GB, may be slow)

# Split large files
# Convert smaller chunks instead of entire file
```

### Dashboard Very Slow with Large JSON

**Symptom**: Dashboard sluggish with 10,000+ incidents

**Cause**: Browser memory or rendering performance

**Solution**:
```bash
# Browser performance limits:
# Chrome/Firefox: ~50,000 incidents max
# Try splitting data:

# Option 1: Use filtering in dashboard
# Filter by Status, Urgency, etc.

# Option 2: Create multiple smaller JSON files
# Convert by month or team

# Option 3: Use index.json
# Dashboard can load from index for faster navigation
```

## Git & Version Control Issues

### Git Configuration Issues

**Symptom**: Can't commit or ".gitignore not working"

**Cause**: Git configuration problem

**Solution**:
```bash
# Verify .gitignore exists
ls -la .gitignore

# Check if data/ and .env are ignored
git status

# If still showing, clear git cache
git rm -r --cached data/
git rm -r --cached .env
git add .gitignore
git commit -m "fix: update gitignore"
```

## Getting Help

### Still Having Issues?

1. **Check the logs**:
   ```bash
   # Converter logs
   cat data/errors/your-file_errors.json

   # Test output
   python -m pytest -v
   ```

2. **Enable verbose mode**:
   ```bash
   convert_incidents.bat data/input/file.csv -v --show-errors
   ```

3. **Check documentation**:
   - [../converters/docs/API.md](../converters/docs/API.md) - Converter API reference
   - [DEVELOPMENT.md](DEVELOPMENT.md) - Setup guide
   - [docs/](.) - Complete documentation

4. **Create issue with details**:
   - Include error message
   - Show sample CSV (without sensitive data)
   - List Python version and OS
   - Attach error report JSON

---

**Last Updated**: 2026-05-14
