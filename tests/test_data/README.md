# Test Data Files

This directory contains CSV files for testing the upload and validation pipeline.

## Files

### valid_sample.csv
A valid CSV file with all required headers and sample incident data.
- Headers: ID de incidencia, Descripción, Estatus, Fecha de envío, Grupo asignado, Urgencia, Impacto, Fecha de última resolución
- Encoding: UTF-8
- Delimiter: Comma (,)
- Rows: 5 sample records
- Use case: Test successful upload and validation

### missing_headers.csv
CSV file missing required headers (Estatus, Grupo asignado, Urgencia, Impacto missing).
- Headers: ID de incidencia, Descripción, Fecha de envío (incomplete)
- Encoding: UTF-8
- Use case: Test header validation error handling

### empty.csv
CSV file with headers but no data rows.
- Headers: Complete set of required headers
- Rows: 0 (header only)
- Use case: Test empty file handling

## Adding New Test Files

When adding new test files, follow these naming conventions:

- **Valid files**: `valid_*.csv`
- **Invalid encoding**: `encoding_*.csv`
- **Invalid delimiter**: `delimiter_*.csv`
- **Missing data**: `incomplete_*.csv`
- **Edge cases**: `edge_*.csv`
- **Large files**: `large_*.csv` (for performance testing)

## Test Data Structure

All valid test files should follow this structure:

```csv
ID de incidencia,Descripción,Estatus,Fecha de envío,Grupo asignado,Urgencia,Impacto,Fecha de última resolución
INC000000000001,Description text,Cerrado,02/01/2026 8:14 AM,Equipo Name,Baja,Masiva,12/01/2026 8:24 AM
```

## Notes

- Keep test files small (<1MB) for quick test execution
- Test files are NOT committed to production deployments
- Use `valid_sample.csv` as the baseline for other test variations
