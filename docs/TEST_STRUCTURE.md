# Test Structure Organization

## Overview

Tests are organized in a hybrid structure that combines **functionality** (what is being tested) with **converter type** (which converter it's testing). This provides clear navigation and makes it easy to find and run related tests.

```
tests/
├── conftest.py              # Shared pytest fixtures
├── test_data/               # Test input fixtures (CSV files)
├── utils/                   # Test utilities and helpers
├── unit/                    # Unit tests (pure logic, no I/O)
├── integration/             # Integration tests (with I/O)
└── e2e/                     # End-to-end tests (complete workflows)
```

## Directory Structure

### Unit Tests (`tests/unit/`)

Pure logic tests with no file I/O. Tests are grouped by functionality:

#### `unit/encoding/` - Encoding Detection
- `test_encoding.py` - General encoding detection
- `test_postmortem_encoding_detection.py` - Postmortem-specific encoding

Tests verify:
- UTF-8, UTF-8-sig, Windows-1252, Latin-1, ISO-8859-15 detection
- BOM (Byte Order Mark) handling
- Special character preservation

#### `unit/delimiter/` - Delimiter Detection
- `test_delimiter.py` - General delimiter detection
- `test_postmortem_delimiter_detection.py` - Postmortem-specific delimiter

Tests verify:
- Comma (,), semicolon (;), tab (\t) detection
- CSV parsing with detected delimiters
- Auto-detection accuracy

#### `unit/normalizers/` - Data Normalization
- `test_normalizers.py` - Core normalization functions
- `test_estatus_normalization.py` - Estatus field normalization (title case)
- `test_record_normalization.py` - Complete record normalization
- `test_date_parser.py` - Date parsing and normalization

Tests verify:
- Text case normalization (title case, lowercase)
- Urgencia extraction (remove prefixes like "4-Baja" → "Baja")
- Date format parsing (DD/MM/YYYY HH:mm a/p)
- Whitespace trimming
- Special character handling

#### `unit/validators/` - Data Validation
- `test_validators.py` - Core validation logic
- `test_validation_rules.py` - Specific validation rules
- `test_field_mapping.py` - Field mapping and requirement verification

Tests verify:
- Required field validation
- Enum value validation (allowed values)
- Date format validation
- Field mapping and presence
- Error message formatting

#### `unit/schemas/` - Data Structures
- `test_postmortem_schemas.py` - Postmortem record schema
- `test_kpi_calculation.py` - KPI aggregation logic
- `test_kpi_metrics.py` - KPI metrics data structure
- `test_metadata_generation.py` - Metadata creation

Tests verify:
- Record structure initialization
- KPI aggregation (by Estatus, Urgencia, Impacto)
- Metadata generation (timestamps, filenames)
- Data structure serialization

#### `unit/derivation/` - Derived Logic
- `test_despliegue_derivation.py` - Despliegue field derivation (PAP/MESA)

Tests verify:
- PAP assignment (earliest date)
- MESA assignment (other records)
- Deterministic tie-breaking

### Integration Tests (`tests/integration/`)

Tests that involve file I/O and converter pipelines. Use `pytest tmp_path` fixture for isolation.

#### `integration/converters/` - CSV→JSON Conversion
- `test_converter_e2e.py` - General converter end-to-end tests
- `test_csv_reader.py` - CSV reading with encoding/delimiter detection

Tests verify:
- Complete conversion pipeline (read → validate → normalize → write)
- Encoding auto-detection in real files
- Delimiter auto-detection in real files
- Field mapping and data preservation
- Large file handling (1000+ records)
- Special characters preservation

#### `integration/postmortem/` - Postmortem Converter
- `test_postmortem_e2e_conversion.py` - Postmortem conversion pipeline
- `test_postmortem_e2e_full.py` - Full postmortem workflow
- `test_postmortem_normalization_integration.py` - Normalization integration
- `test_error_handling.py` - Error reporting and handling

Tests verify:
- Complete postmortem conversion workflow
- Metadata and KPI inclusion in output
- Error record tracking and reporting
- Zero silent failures (all records processed)
- JSON output structure validity
- Field normalization in context

### E2E Tests (`tests/e2e/`)

End-to-end tests covering complete workflows and performance.

#### `e2e/performance/` - Performance Benchmarks
- `test_performance.py` - Performance and scalability tests

Tests verify:
- Conversion speed (< 5 seconds for 1000+ records)
- Per-record processing time (< 5ms per record)
- Memory efficiency
- JSON generation speed
- Error report generation speed

## Running Tests

### Run All Tests
```bash
pytest tests/
pytest tests/ -v                    # Verbose output
pytest tests/ --tb=short            # Short traceback format
```

### Run Tests by Category

```bash
# Unit tests only
pytest tests/unit/

# Specific functionality
pytest tests/unit/encoding/         # Encoding tests
pytest tests/unit/delimiter/        # Delimiter tests
pytest tests/unit/validators/       # Validation tests

# Integration tests
pytest tests/integration/

# Postmortem converter tests
pytest tests/integration/postmortem/

# CSV conversion tests
pytest tests/integration/converters/

# E2E and performance tests
pytest tests/e2e/
pytest tests/e2e/performance/
```

### Run Tests with Filters

```bash
# Run only tests matching a pattern
pytest tests/ -k "normalization"    # Run normalization tests
pytest tests/ -k "encoding"         # Run encoding tests
pytest tests/ -k "postmortem"       # Run postmortem-specific tests

# Run with markers
pytest tests/ -m "slow"             # Run only slow tests (if marked)
pytest tests/ -v --durations=10     # Show 10 slowest tests
```

### Parallel Test Execution

```bash
# Install pytest-xdist first
pip install pytest-xdist

# Run tests in parallel (auto-detect CPU cores)
pytest tests/ -n auto

# Run with 4 workers
pytest tests/ -n 4
```

### Coverage Analysis

```bash
pip install pytest-cov

# Generate coverage report
pytest tests/ --cov=src --cov-report=html

# View specific module coverage
pytest tests/ --cov=csv_to_json --cov-report=term-missing
```

## Adding New Tests

When adding a new test, place it in the appropriate directory:

1. **Logic test (no file I/O)** → `tests/unit/{functionality}/`
2. **File I/O test** → `tests/integration/{converter}/`
3. **Complete workflow test** → `tests/e2e/{purpose}/`
4. **Use `pytest tmp_path`** for temporary output files

Example structure for a new feature:

```python
# tests/unit/newfeature/test_myfeature.py
import pytest

class TestMyFeature:
    def test_basic_functionality(self):
        """Test core logic."""
        # Pure logic testing, no I/O
        result = my_function(input_data)
        assert result == expected

# tests/integration/converters/test_myfeature_converter.py
import pytest
from pathlib import Path

class TestMyFeatureConverter:
    def test_conversion_workflow(self, tmp_path):
        """Test complete conversion workflow."""
        # Create input in tmp_path
        input_file = tmp_path / "input.csv"
        input_file.write_text("header\ndata\n")

        # Run conversion
        output_file = tmp_path / "output.json"
        converter.convert_file(str(input_file), str(output_file))

        # Verify output
        assert output_file.exists()
```

## Test Statistics

Current test suite (as of 2026-06-01):

| Category | Count | Location |
|----------|-------|----------|
| Unit Tests | 178 | `tests/unit/` |
| Integration Tests | 85 | `tests/integration/` |
| E2E Tests | 1 | `tests/e2e/` |
| **Total** | **264** | |

**Execution Time**: ~1.3 seconds
**Code Coverage**: 86% (exceeds 80% requirement)

## Benefits of This Structure

✅ **Clarity** - Tests organized by functionality (what) and converter (which)
✅ **Scalability** - Easy to add new tests in appropriate directories
✅ **Maintainability** - Related tests grouped together
✅ **Navigation** - `grep -r` searches are more targeted
✅ **CI/CD** - Can run test categories independently
✅ **Parallelization** - Full pytest-xdist support (all tests isolated)
✅ **Documentation** - Directory names are self-documenting

## Troubleshooting

### Import Errors
If tests fail with import errors after reorganization:
- Ensure `conftest.py` is in `tests/` root
- Check that all `__init__.py` files exist in directories
- Run `pytest --collect-only` to verify test discovery

### Path Issues in Tests
If tests fail due to relative paths:
- Use `pytest tmp_path` fixture for output files
- Use `tests/test_data/` for input fixtures (already on import path)
- Test files can import from `csv_to_json` directly (installed in editable mode)

### Performance Tests Failing
If performance tests fail with "took too long":
- Check system load (run tests in isolation)
- Update timeout thresholds in test file if hardware is slower
- Use `pytest tests/e2e/performance/ -v` to see exact times

## References

- [pytest Documentation](https://docs.pytest.org/en/stable/)
- [Test Structure Best Practices](https://docs.pytest.org/en/latest/goodpractices.html)
- [pytest tmp_path Fixture](https://docs.pytest.org/en/stable/how-to/tmp_path.html)
- [Code Coverage Best Practices](https://coverage.readthedocs.io/)
