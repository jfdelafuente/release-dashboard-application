# Quickstart: CSV-to-JSON Converters Testing & Integration

**Date**: 2026-05-14 | **Audience**: QA Engineers, Integration Testers, Developers

## Overview

This quickstart covers how to test the optimized CSV-to-JSON converters after implementation. Both converters (massive incidents and postmortem) follow the same API and produce JSON compatible with their respective dashboards.

---

## Setup

### Prerequisites
- Python 3.8+
- `pytest` and `coverage` installed
- Test CSV files in `tests/test_data/`
- Access to development branch `006-optimize-csv-converters`

### Installation
```bash
# Clone/checkout the branch
git checkout 006-optimize-csv-converters

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For testing
```

---

## Basic Usage

### Python API

```python
from src.converters import CsvToJsonConverter

# Initialize converter
converter = CsvToJsonConverter()

# Convert a CSV file
success, report = converter.convert_file(
    input_path='data/input/CS_Masiva_20260514.csv',
    output_path='data/output/CS_Masiva_20260514-massive.json',
    error_report_path='data/errors/CS_Masiva_20260514_errors.json'
)

# Check results
print(f"Success: {success}")
print(f"Valid records: {report['stats']['successful']}")
print(f"Invalid records: {report['stats']['failed']}")
print(f"Encoding detected: {report['encoding_detected']}")
```

### CLI Usage

```bash
# Massive incidents converter
python -m src.converters.csv_to_json.converter \
  --input data/input/CS_Masiva_20260514.csv \
  --output data/output/CS_Masiva_20260514-massive.json \
  --errors data/errors/CS_Masiva_20260514_errors.json

# Postmortem converter
python -m src.converters.csv_to_json.postmortem_converter \
  --input data/input/2026R4MESAPOST.csv \
  --output data/output/2026R4MESAPOST-postmortem.json \
  --errors data/errors/2026R4MESAPOST_errors.json
```

---

## Test Scenarios

### Scenario 1: Valid File with Mixed Encoding

**Test Data**: `tests/test_data/valid-100.csv` (100 valid records, UTF-8 with BOM)

**Expected Result**:
- ✅ 100 records in JSON output
- ✅ success_rate = 100%
- ✅ All fields normalized (e.g., Urgencia "4-Baja" → "Baja")
- ✅ Processing < 1 second
- ✅ Memory < 50MB

**Test Steps**:
```python
import json
import time
import psutil

converter = CsvToJsonConverter()
start_time = time.time()
start_memory = psutil.Process().memory_info().rss

success, report = converter.convert_file(
    input_path='tests/test_data/valid-100.csv',
    output_path='test_output.json',
    error_report_path='test_errors.json'
)

elapsed = time.time() - start_time
memory_used = (psutil.Process().memory_info().rss - start_memory) / (1024 * 1024)

# Assertions
assert success == True
assert report['stats']['successful'] == 100
assert report['stats']['failed'] == 0
assert report['stats']['success_rate'] == 100.0
assert elapsed < 1.0, f"Processing took {elapsed}s (expected <1s)"
assert memory_used < 50, f"Memory used {memory_used}MB (expected <50MB)"

# Verify JSON structure
with open('test_output.json') as f:
    data = json.load(f)
    assert '_metadata' in data
    assert 'data' in data
    assert len(data['data']) == 100
    assert data['_metadata']['record_count'] == 100
    assert data['_metadata']['encoding_detected'] in ['UTF-8', 'utf-8', 'UTF-8-sig']
```

---

### Scenario 2: File with Invalid Records

**Test Data**: `tests/test_data/invalid-mixed.csv` (mix of valid and invalid records)

**Expected Result**:
- ✅ Valid records in JSON output
- ✅ Invalid records NOT in JSON, but listed in error report
- ✅ success_rate < 100%
- ✅ Each error includes row number, record ID, field name, and error message

**Test Steps**:
```python
converter = CsvToJsonConverter()
success, report = converter.convert_file(
    input_path='tests/test_data/invalid-mixed.csv',
    output_path='test_output.json',
    error_report_path='test_errors.json'
)

# Assertions
assert success == False  # Has errors
assert report['stats']['failed'] > 0
assert report['stats']['success_rate'] < 100.0

# Verify error report structure
with open('test_errors.json') as f:
    errors = json.load(f)
    assert 'summary' in errors
    assert 'errors' in errors
    for error in errors['errors']:
        assert 'row' in error
        assert 'record_id' in error
        assert 'issues' in error
        for issue in error['issues']:
            assert 'field' in issue
            assert 'error' in issue
            assert issue['error'] not in [None, '']  # Error message must be specific

# Verify invalid records NOT in JSON
with open('test_output.json') as f:
    data = json.load(f)
    output_ids = {r.get('ID de incidencia') for r in data['data']}

    # Check that invalid record IDs are not in output
    for error in errors['errors']:
        if error['record_id']:
            assert error['record_id'] not in output_ids
```

---

### Scenario 3: Performance - Large File

**Test Data**: Generated CSV with 50,000 records

**Expected Result**:
- ✅ Processing completes in < 30 seconds
- ✅ Memory usage < 500MB
- ✅ Consistent processing rate (linear time complexity)

**Test Steps**:
```python
import time
import psutil

converter = CsvToJsonConverter()

# Generate or use large test file
large_csv = 'tests/test_data/large-50k.csv'

start_time = time.time()
start_memory = psutil.Process().memory_info().rss / (1024 * 1024)

success, report = converter.convert_file(
    input_path=large_csv,
    output_path='test_output_large.json',
    error_report_path='test_errors_large.json'
)

elapsed = time.time() - start_time
peak_memory = psutil.Process().memory_info().rss / (1024 * 1024)
memory_used = peak_memory - start_memory

print(f"Time: {elapsed:.2f}s, Memory: {memory_used:.2f}MB")

# Assertions
assert elapsed < 30, f"Processing took {elapsed:.2f}s (expected <30s)"
assert memory_used < 500, f"Memory used {memory_used:.2f}MB (expected <500MB)"

# Verify record count
with open('test_output_large.json') as f:
    data = json.load(f)
    assert len(data['data']) == report['stats']['successful']
```

---

### Scenario 4: Postmortem Despliegue Derivation

**Test Data**: CSV with postmortem records spanning multiple dates

**Expected Result**:
- ✅ Exactly one record has `Despliegue="PAP"` (earliest date)
- ✅ All other records have `Despliegue="MESA"`
- ✅ On tie (identical dates), first occurrence gets PAP
- ✅ KPI calculations correct

**Test Steps**:
```python
converter = CsvToJsonConverter()
success, report = converter.convert_file(
    input_path='tests/test_data/postmortem-dates.csv',
    output_path='test_postmortem.json',
    error_report_path='test_postmortem_errors.json'
)

with open('test_postmortem.json') as f:
    data = json.load(f)
    records = data['data']

    # Count Despliegue values
    pap_count = sum(1 for r in records if r.get('Despliegue') == 'PAP')
    mesa_count = sum(1 for r in records if r.get('Despliegue') == 'MESA')

    # Assertions
    assert pap_count == 1, f"Expected 1 PAP record, got {pap_count}"
    assert mesa_count == len(records) - 1

    # Verify KPI calculations
    kpis = data['_metadata']['kpis']
    assert 'dashboard_hub' in kpis
    assert 'cerradas_percent' in kpis['dashboard_hub']
    assert 'pap_resueltas_percent' in kpis['dashboard_hub']
    assert 'mesa_resueltas_percent' in kpis['dashboard_hub']

    # Manual KPI check: spot-check one aggregation
    by_estatus = kpis.get('by_estatus', {})
    total_in_data = len(records)
    total_in_kpi = sum(by_estatus.values())
    assert total_in_kpi == total_in_data, "KPI aggregation mismatch"
```

---

### Scenario 5: Edge Cases

**Test Case 5a: Empty File**
```python
# File with header only, no data rows
success, report = converter.convert_file('tests/test_data/empty.csv', ...)
assert report['stats']['successful'] == 0
assert report['stats']['failed'] == 0
assert report['stats']['success_rate'] == 100.0
```

**Test Case 5b: BOM Handling**
```python
# File with UTF-8 BOM
success, report = converter.convert_file('tests/test_data/utf8-bom.csv', ...)
assert 'UTF' in report['encoding_detected']
# Verify no BOM artifacts in JSON
with open(output_path) as f:
    content = f.read()
    assert not content.startswith('\ufeff')
```

**Test Case 5c: Mixed Line Endings**
```python
# CSV with both CRLF and LF
success, report = converter.convert_file('tests/test_data/mixed-endings.csv', ...)
assert success == True
assert report['stats']['successful'] > 0
```

**Test Case 5d: Normalization Verification**
```python
# Verify field normalization
with open(output_path) as f:
    data = json.load(f)
    for record in data['data']:
        urgencia = record.get('Urgencia', '')
        # Should be normalized without numeric prefix
        assert not urgencia[0].isdigit(), f"Urgencia not normalized: {urgencia}"
        # Should be title case
        assert urgencia == urgencia.title(), f"Urgencia not title case: {urgencia}"
```

---

## Dashboard Integration Testing

### Integration Test: Massive Incidents Dashboard

After conversion, verify the Massive Incidents Dashboard can:

1. **Load the JSON file**:
   ```javascript
   // In browser console or test
   fetch('data/output/CS_Masiva_20260514-massive.json')
     .then(r => r.json())
     .then(data => {
       console.log('Records:', data.data.length);
       console.log('KPIs:', data._metadata.kpis);
     });
   ```

2. **Display KPIs correctly**:
   - Total Incidencias matches `_metadata.kpis.total_incidencias`
   - Pendientes matches `_metadata.kpis.total_pendientes`
   - Trends (7d, 15d, 30d) populated
   - By_estatus, by_urgencia, by_impacto populated

3. **Filter and display records**:
   - All records in data array match expected format
   - No null or undefined values in required fields

### Integration Test: Postmortem Dashboard + Dashboard Hub

After conversion, verify:

1. **Dashboard Hub can auto-load**:
   - File in `data/output/` with `-postmortem` suffix recognized
   - KPI cards display: cerradas%, pap_resueltas%, mesa_resueltas%
   - Despliegue field visible in dashboard

2. **Postmortem Dashboard displays**:
   - All 13 fields present
   - Despliegue derivation visible and correct
   - Aggregations (by_estatus, by_urgencia, by_impacto) match manual checks

---

## Running Full Test Suite

### Unit Tests
```bash
# Run all tests with coverage
pytest tests/ --cov=src.converters --cov-report=html --cov-fail-under=80

# Run specific test file
pytest tests/test_normalizers.py -v

# Run specific test
pytest tests/test_converter.py::test_valid_massive_incidents -v
```

### Performance Tests
```bash
# Run only performance/scaling tests
pytest tests/test_performance.py -v -m performance

# Benchmark with timing output
pytest tests/test_performance.py -v -s
```

### Edge Case Tests
```bash
# Run only edge case tests
pytest tests/test_edge_cases.py -v
```

---

## Troubleshooting

### Problem: Encoding Detection Fails

**Symptom**: `encoding_detected` doesn't match actual encoding, garbled characters in output

**Solution**:
1. Check file has valid BOM or common encoding signature
2. Verify with `file` command: `file input.csv`
3. If necessary, explicitly convert: `iconv -f WINDOWS-1252 -t UTF-8 input.csv > output.csv`

### Problem: Despliegue Always "MESA"

**Symptom**: No record gets `Despliegue="PAP"` in postmortem output

**Solution**:
1. Verify date fields have values
2. Check date format matches expected format (DD-MMM or DD/MM/YYYY)
3. Ensure Despliegue derivation logic scans all date fields (Fecha de envío, notificación, última resolución)

### Problem: KPI Counts Don't Match

**Symptom**: Sum of by_estatus != total_incidencias

**Solution**:
1. Check if records have null/empty status values (may be excluded)
2. Verify validation didn't exclude partial records
3. Manually count records with status in JSON to debug

### Problem: Performance Degradation

**Symptom**: Processing 10K records takes >5 seconds

**Solution**:
1. Check available memory: `ps aux | grep python`
2. Profile with cProfile: `python -m cProfile -s cumtime converter.py`
3. Look for: excessive field lookups, redundant normalization, nested loops

---

## Success Criteria Checklist

Use this checklist to verify all success criteria are met after implementation:

- [ ] SC-001: 100% of valid records converted correctly
- [ ] SC-002: ≥95% success rate on real-world CSV files
- [ ] SC-003: Error report identifies 100% of invalid records
- [ ] SC-004: Processing time for 10K records < 5 seconds
- [ ] SC-005: Peak memory for 50K records < 500MB
- [ ] SC-006: Postmortem Despliegue derivation 100% correct
- [ ] SC-007: KPI calculations match manual spot-checks
- [ ] SC-008: JSON validates against dashboard schema
- [ ] SC-009: Encoding detection accurate in 99%+ of cases
- [ ] SC-010: Delimiter detection accurate in 100% of cases

---

**Last Updated**: 2026-05-14
