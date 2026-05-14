# Migration Guide: Data Directory Reorganization

This guide documents the migration from the old directory structure (`datos/`, `csv/`, `incidencias/`) to the new unified structure (`data/input/`, `data/output/`, `data/errors/`).

## Old Structure vs. New Structure

### Old Structure (Deprecated)
```
datos/
├── csv/              # CSV input files
├── json/             # Generated JSON files
└── errors/           # Error reports
```

### New Structure (Current)
```
data/
├── input/            # CSV input files (replace: datos/csv/)
├── output/           # Generated JSON files (replace: datos/json/)
├── errors/           # Error reports (replace: datos/errors/)
└── archive/          # Historical data (optional)
```

## Benefits

✅ Clarity: `data/input/` and `data/output/` are self-documenting
✅ Security: `data/` in `.gitignore` prevents accidental commits  
✅ Consistency: Aligns with industry standards
✅ Scalability: Supports archiving without clogging active directories

## Migration Steps

### Phase 1: Directory Creation (✅ Done)
New directories created in `data/` hierarchy.

### Phase 2: Migrate Existing Data
```bash
cp datos/csv/* data/input/
cp datos/json/* data/output/
cp datos/errors/* data/errors/
```

### Phase 3: Update Converters
Old paths still work during transition (30-day period).

New preferred usage:
```bash
python src/converters/convert_incidents.py data/input/sample.csv
# Output: data/output/sample.json
```

## File Naming Conventions

### CSV Files (Input)
Pattern: `<type>-<identifier>-<date>.csv`
- `cs-masiva-202605.csv` (Customer Service, massive, June 2026)
- `2026r4-postmortem.csv` (Release 2026 R4, post-mortem)

### JSON Files (Output)
Same base name as CSV, with `.json` extension:
- `data/input/cs-masiva-202605.csv` → `data/output/cs-masiva-202605.json`

### Error Reports
Pattern: `<base>_errors.json`
- `data/errors/cs-masiva-202605_errors.json`

## Backward Compatibility

### Transition Period (30 days)

Both paths work:
✅ `python src/converters/convert_incidents.py data/input/sample.csv` (new, preferred)
✅ `python src/converters/convert_incidents.py datos/csv/sample.csv` (old, fallback)

After 2026-06-14: Only new paths supported.

## Dashboard Integration

1. Start server: `python -m http.server 8000`
2. Open dashboard: `http://localhost:8000/src/dashboards/massive-incidents-dashboard.html`
3. Load JSON: Click "Select JSON File" → navigate to `data/output/` → select `.json`

## Verification Checklist

- [ ] `data/input/`, `data/output/`, `data/errors/` exist
- [ ] `.gitignore` contains `data/` pattern
- [ ] Converter works: `python src/converters/convert_incidents.py data/input/test.csv`
- [ ] Output appears in `data/output/`
- [ ] Dashboard can load JSON from `data/output/`
- [ ] `.env` files are git-ignored

## Related Documentation

- [DIRECTORY-STRUCTURE.md](DIRECTORY-STRUCTURE.md) - Detailed directory organization
- [docs/API.md](docs/API.md) - Converter API
- [README.md](README.md) - Quick start
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) - Development setup

---

**Migration Deadline**: 2026-06-14  
**Status**: Backward compatible until deadline  
**Last Updated**: 2026-05-14
