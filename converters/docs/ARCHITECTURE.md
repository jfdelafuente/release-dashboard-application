# System Architecture

High-level overview of Release Dashboard Application system design, data flow, and component relationships.

## System Overview

```
┌─────────────────────────────────────────────────────┐
│            Release Dashboard Application             │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────────────┐        ┌──────────────────┐  │
│  │  CSV Converters  │        │   Dashboards     │  │
│  ├──────────────────┤        ├──────────────────┤  │
│  │ convert_         │        │ massive-         │  │
│  │ incidents.py     │        │ incidents-       │  │
│  │                  │        │ dashboard.html   │  │
│  │ convert_         │        │                  │  │
│  │ postmortems.py   │        │ postmortem-      │  │
│  │                  │        │ dashboard.html   │  │
│  └────────┬─────────┘        └────────┬─────────┘  │
│           │                            │             │
│           ▼                            ▼             │
│  ┌─────────────────────────────────────────────┐   │
│  │         Data Processing Layer               │   │
│  │  (Encoding detection, delimiter detection, │   │
│  │   field normalization, validation)          │   │
│  └────────┬───────────────────────────────────┘   │
│           │                                        │
│           ▼                                        │
│  ┌─────────────────────────────────────────────┐   │
│  │      File-Based Storage (data/)             │   │
│  │ ┌──────────┬──────────┬──────────┐          │   │
│  │ │  input/  │ output/  │ errors/  │          │   │
│  │ │ (CSV)    │ (JSON)   │(errors)  │          │   │
│  │ └──────────┴──────────┴──────────┘          │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │    Configuration Management                 │   │
│  │ ┌─────────────────────────────────────────┐ │   │
│  │ │ Environment Variables (dev/staging/prod)│ │   │
│  │ │ .env (dev, git-ignored)                 │ │   │
│  │ │ GitHub Secrets (prod)                   │ │   │
│  │ └─────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
└─────────────────────────────────────────────────────┘
```

## Component Architecture

### 1. CSV Converters (`src/converters/`)

**Purpose**: Convert incident data from CSV format to JSON format

**Components**:
- `convert_incidents.py`: Massive incidents converter
- `convert_postmortems.py`: Post-mortem incidents converter
- `csv_to_json/`: Shared converter module

**Responsibilities**:
- Auto-detect file encoding (UTF-8, UTF-8-sig, Windows-1252, Latin-1, ISO-8859-15)
- Auto-detect CSV delimiter (comma, semicolon, tab)
- Normalize field values (urgency levels, status codes)
- Validate required fields and allowed values
- Generate comprehensive error reports for invalid records
- Create searchable JSON index

**Data Flow**:
```
CSV Input
   ↓
Encoding Detection (read first 4KB, check for BOM)
   ↓
Delimiter Detection (csv.Sniffer with fallback)
   ↓
CSV Parsing (DictReader with detected settings)
   ↓
Field Normalization (Urgency "4-Baja" → "Baja", Status → title case)
   ↓
Validation (required fields, allowed values)
   ↓
JSON Output (valid records) + Error Report (invalid records)
```

### 2. Dashboards (`src/dashboards/`)

**Purpose**: Provide interactive visualizations of incident data

**Components**:
- `massive-incidents-dashboard.html`: Real-time incident analysis
- `postmortem-dashboard.html`: Post-mortem analysis
- `assets/css/`: Shared stylesheets
- `assets/js/`: Shared JavaScript utilities (future)

**Dashboards Features**:

#### Massive Incidents Dashboard
- **Global Time Filter**: Period selection (all, 7d, 15d, 30d, 90d, 6m, 1y, current year)
- **KPI Cards**: Total incidents, pending, trend indicators
- **Temporal Charts**: Daily evolution, backlog tracking
- **Interactive Table**: Sortable incidents with status badges
- **Filter System**: Status, system, urgency filters

#### Postmortem Dashboard
- **Analysis by Deployment**: PAP vs MESA segmentation
- **Impact Assessment**: By urgency, system, deployment phase
- **Timeline View**: Chronological incident progression

**Data Format Expected**:
```json
[
  {
    "ID de incidencia": "INC000004002774",
    "Descripción": "Problem description",
    "Estatus": "Cerrado",
    "Fecha de envío": "26/04/2026 8:40 a",
    "Grupo asignado": "TEAM_NAME",
    "Urgencia": "Alta",
    "Impacto": "Masiva",
    "Fecha de última resolución": "26/04/2026 10:00 p"
  }
]
```

### 3. Data Storage (`data/`)

**File-based storage with directory organization**:

```
data/
├── input/      # CSV input files (user uploads here)
├── output/     # Generated JSON files (dashboards load from here)
├── errors/     # Error reports from conversions
└── archive/    # Historical data (YYYY/MM/ subdirs)
```

**All data/ directory contents are git-ignored** for security (contains sensitive incident data).

**Storage Strategy**:
- **Input**: CSV files from incident management systems
- **Output**: Processed JSON ready for dashboard consumption
- **Errors**: Validation error reports with record-level details
- **Archive**: Historical snapshots organized by year/month

### 4. Configuration Management (`config/`)

**Multi-environment configuration**:

```
config/
├── .env.example         # Template (committed to git)
├── .env.development     # Dev defaults (committed)
├── .env.staging         # Staging (git-ignored)
├── .env.production      # Production (git-ignored)
└── pre-commit-hook.sh   # Prevents secret commits
```

**Environment Isolation**:
- **Development**: Local `.env` file with sensible defaults
- **Staging**: GitHub Secrets injected at deployment
- **Production**: GitHub Secrets with production credentials

**Configuration Loading**:
```python
from dotenv import load_dotenv
load_dotenv('config/.env.development')  # Or load from environment variables
```

### 5. Testing Infrastructure (`tests/`)

**Test organization**:
```
tests/
├── unit/           # Unit tests for converters
├── integration/    # End-to-end workflow tests
├── fixtures/       # Test data (sample CSV, JSON files)
└── __init__.py
```

**Testing Strategy**:
- Minimum 80% code coverage (enforced by CI/CD)
- Unit tests for converter logic
- Integration tests for complete workflows
- Fixture-based test data

## Data Flow

### Complete Incident Processing Pipeline

```
User uploads CSV to data/input/
   ↓
Converter runs (python src/converters/convert_incidents.py)
   ↓
  ┌─────────────────────────────────────┐
  │   Encoding Detection                │
  │   ↓ BOM check → try UTF-8-sig first │
  │   ↓ Read first 4KB                  │
  │   ↓ Fallback: UTF-8, Windows-1252   │
  └─────────────────────────────────────┘
   ↓
  ┌─────────────────────────────────────┐
  │   Delimiter Detection               │
  │   ↓ csv.Sniffer (3 samples)         │
  │   ↓ Fallback: count columns         │
  │   ↓ Detected: comma, semicolon, tab │
  └─────────────────────────────────────┘
   ↓
  ┌─────────────────────────────────────┐
  │   CSV Parsing                       │
  │   ↓ DictReader with detected config │
  │   ↓ Read each row                   │
  │   ↓ Build record dict               │
  └─────────────────────────────────────┘
   ↓
  ┌─────────────────────────────────────┐
  │   Field Normalization               │
  │   ↓ Urgencia: "4-Baja" → "Baja"     │
  │   ↓ Estatus: "cerrado" → "Cerrado"  │
  │   ↓ Trim whitespace                 │
  │   ↓ Parse dates                     │
  └─────────────────────────────────────┘
   ↓
  ┌─────────────────────────────────────┐
  │   Validation                        │
  │   ✅ Required fields present        │
  │   ✅ Values in allowed set          │
  │   ✅ Date formats correct           │
  │   ❌ Invalid records logged         │
  └─────────────────────────────────────┘
   ↓
Output Files:
├── data/output/[filename].json         (valid records)
├── data/errors/[filename]_errors.json  (invalid records with details)
└── data/output/index.json              (searchable index)
   ↓
User loads JSON in Dashboard
   ↓
Dashboard parses JSON
   ↓
  ┌─────────────────────────────────────┐
  │   Dashboard Processing              │
  │   ↓ Parse dates from "Fecha de..."  │
  │   ↓ Apply global time filter        │
  │   ↓ Calculate KPIs                  │
  │   ↓ Build temporal charts           │
  │   ↓ Generate filterable table       │
  └─────────────────────────────────────┘
   ↓
User sees incidents visualized and filtered
```

## Deployment Architecture

### CI/CD Pipeline (GitHub Actions)

```
Developer pushes to feature branch
   ↓
GitHub Actions triggers:
├─ Run pytest (80% coverage minimum)
├─ Run flake8 linting
├─ Run pylint style checks
└─ Run code formatting check (black)
   ↓
All checks pass?
├─ Yes → Create deployment artifact
└─ No → Block PR, require fixes
   ↓
PR approved by reviewer?
├─ Yes → Merge to main
└─ No → Wait for approval
   ↓
Merge triggers:
├─ Auto-deploy to staging
└─ Run health checks
   ↓
Manual approval required?
├─ Yes → Wait for prod approval
└─ No → Deploy complete
   ↓
Production deployment:
├─ Pre-deployment checks
├─ Deploy new version
├─ Run health checks
├─ Log deployment with timestamp
└─ Notify team
```

### Environment Architecture

```
┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│  Development   │  │    Staging     │  │  Production    │
├────────────────┤  ├────────────────┤  ├────────────────┤
│ Local machine  │  │  GitHub Infra  │  │  GitHub Infra  │
│                │  │  (or server)   │  │  (or server)   │
│ Python venv    │  │ Containerized  │  │ Containerized  │
│ .env file      │  │ Env vars       │  │ GitHub Secrets │
│                │  │                │  │                │
│ Manual testing │  │ Auto-deployed  │  │ Approval req'd │
│ Unlimited data │  │ Limited data   │  │ Full datasets  │
│ Loose rules    │  │ Staging checks │  │ Strict rules   │
└────────────────┘  └────────────────┘  └────────────────┘
```

## Security Architecture

```
┌─────────────────────────────────────────────┐
│         Secrets Prevention Layers            │
├─────────────────────────────────────────────┤
│ Layer 1: .gitignore                         │
│ ├─ Prevents .env file commits              │
│ ├─ Prevents credentials files              │
│ └─ Prevents sensitive data in data/        │
├─────────────────────────────────────────────┤
│ Layer 2: Pre-commit Hook                    │
│ ├─ Detects secret patterns                 │
│ ├─ Blocks commit if secrets found          │
│ └─ Runs before push to remote              │
├─────────────────────────────────────────────┤
│ Layer 3: GitHub Secret Scanning             │
│ ├─ Scans all pushes for known patterns     │
│ ├─ Alerts on detected credentials          │
│ └─ Blocks risky commits                    │
├─────────────────────────────────────────────┤
│ Layer 4: GitHub Secrets for Production      │
│ ├─ Credentials never in code               │
│ ├─ Injected as environment variables       │
│ └─ Rotated regularly                       │
└─────────────────────────────────────────────┘
```

## Performance Characteristics

### Converter Performance

- **Target**: 1000+ records/second
- **Typical**: CSV parsing ~2000 records/sec
- **Bottleneck**: Validation, not parsing

### Dashboard Performance

- **Load Time**: < 2 seconds with 10,000 incidents
- **Filter Response**: < 200ms
- **Chart Rendering**: < 500ms

### Memory Usage

- **Typical**: < 100MB for 10,000 incidents
- **Peak**: During filtering/sorting operations
- **Limit**: Support up to 100,000 incidents (backend limit TBD)

## Dependencies

### Production Dependencies

- `python-dotenv`: Environment variable loading
- Python 3.6+ standard library (csv, json, datetime, etc.)

### Development Dependencies

- `pytest`: Testing framework
- `pytest-cov`: Coverage reporting
- `black`: Code formatter
- `flake8`: Style linter
- `pylint`: Code analyzer
- `pre-commit`: Git hook management

### Frontend Dependencies

- `Plotly.js`: Dashboard charting (CDN, not npm)
- HTML5 File API: File upload
- CSS3: Styling

## Technology Decisions

See [specs/005-project-organization/research.md](../specs/005-project-organization/research.md) for detailed technical decisions:

1. **GitHub Actions** for CI/CD (native, free, minimal config)
2. **pytest** with 80% coverage (simple, effective)
3. **python-dotenv** for dev config (standard practice)
4. **Plain Markdown docs** (no build tool needed)
5. **Optional Docker** (consistency, not required locally)

## Scaling Considerations

For future scaling:

1. **More Incidents**: Database instead of file-based storage
2. **More Dashboards**: Frontend framework (React, Vue)
3. **Microservices**: Separate converter service
4. **Caching**: Redis for frequently accessed data
5. **Async Processing**: Celery for long-running conversions

---

**Last Updated**: 2026-05-14
