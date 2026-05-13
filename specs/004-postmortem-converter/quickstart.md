# Quick Start: Postmortem CSV to JSON Converter Testing

## Overview

This guide provides step-by-step instructions for testing the Postmortem CSV to JSON Converter after implementation.

## Prerequisites

- Python 3.7+
- CSV file with postmortem data in 13 expected fields
- `data/input/` directory for CSV input
- `data/output/` directory for JSON output

## Installation & Setup

```bash
# Verify project structure
ls data/input/    # Should exist
ls data/output/   # Should exist
ls data/errors/   # Should exist

# Verify dependencies
pip install chardet  # For encoding detection
```

## Test Scenarios

### Test 1: Basic Conversion (Happy Path)

**Objective**: Verify converter processes valid CSV and produces correct JSON output

**Expected Output Structure**:
- All records in `data` array
- KPIs in `_metadata.kpis`
- Despliegue field added to each record
- File metadata includes timestamp and source filename

### Test 2: Encoding Detection

Verify converter auto-detects:
- UTF-8, UTF-8-sig, Windows-1252, Latin-1
- Spanish text with accented characters preserved

### Test 3: Delimiter Detection

Verify converter handles:
- Comma-delimited files
- Semicolon-delimited files
- Tab-delimited files

### Test 4: Error Handling

Expected behavior:
- Valid records converted and output
- Invalid records documented in error report
- No silent failures; all errors include row number and reason
- Error report is valid JSON

### Test 5: KPI Accuracy

Verify KPIs match expected distribution:
- Total record count
- Distribution by Estatus
- Distribution by Urgencia
- Distribution by Impacto

### Test 6: Auto-Load Discovery

Test Dashboard Hub integration:
1. Convert CSV: `python convert_postmortems.py data/input/test.csv`
2. Update index: `python build_index.py`
3. Verify `*-postmortem.json` files appear in `data/output/index.json`

### Test 7: Despliegue Derivation

Verify correct assignment:
- Record with oldest date gets Despliegue="PAP"
- All other records get Despliegue="MESA"
- Edge case: identical dates use first-seen rule

### Test 8: Performance

Expected: <5 seconds for 1000+ record CSV

## Dashboard Hub Integration

After converter implementation:

1. Generate postmortem JSON
2. Update index via `build_index.py`
3. Open `dashboard-hub.html`
4. Verify postmortem KPI cards display
5. Click postmortem dashboard link to verify data loads

## Troubleshooting

**Output JSON empty**: Check CSV header format and valid records exist

**All records fail**: Verify encoding, field names (case-sensitive), date formats

**Wrong Despliegue values**: Check date parsing (see error report)

**KPIs don't match dashboard**: Verify pre-calculated values in `_metadata.kpis`
