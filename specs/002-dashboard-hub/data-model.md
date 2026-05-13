# Data Model: Dashboard Hub

## Entities

### DashboardHub
**Purpose**: Main page container that aggregates data from both dashboards

**Structure**:
```javascript
{
  title: "Dashboard Hub",
  lastUpdated: "2026-05-13T15:45:00Z",
  dataSource: "data/output/[latest-filename].json",
  navigation: [NavigationItem],
  kpiSummary: {
    massiveIncidents: [KPICard],
    postmortem: [KPICard]
  }
}
```

---

### KPICard
**Purpose**: Individual metric display component

**Fields**:
- `id` (String): Unique identifier (e.g., "total-incidents")
- `label` (String): Display name (e.g., "Total Incidents")
- `value` (Number): Current metric value
- `unit` (String, optional): Unit of measurement (e.g., "incidents")
- `trend` (Object, optional):
  - `percentage` (Number): Percent change (-100 to +100)
  - `direction` ("up" | "down" | "neutral")
  - `period` (String): Time period compared (e.g., "7-day")
- `icon` (String, optional): CSS class or icon name
- `color` (String, optional): CSS class for styling
- `link` (String, optional): URL to target dashboard

**Relationships**:
- Belongs to: DashboardHub (under massiveIncidents or postmortem array)

**Validation**:
- `value` must be >= 0
- `percentage` must be between -100 and 100
- `direction` must be one of allowed values

---

### NavigationItem
**Purpose**: Link to access individual dashboards

**Fields**:
- `id` (String): Unique identifier
- `label` (String): Display name (e.g., "Massive Incidents Dashboard")
- `url` (String): Relative path (e.g., "massive-incidents-dashboard.html")
- `description` (String, optional): Brief description of dashboard
- `icon` (String, optional): Icon identifier

**Relationships**:
- Belongs to: DashboardHub (navigation array)

---

### IncidentRecord
**Purpose**: Raw incident data loaded from JSON

**Fields** (extracted from JSON):
- `ID de incidencia` (String): Incident ID
- `Descripción` (String): Incident description
- `Estatus` (String): Status value
- `Fecha de envío` (String): Date/time incident reported
- `Urgencia` (String): Urgency level
- `Impacto` (String): Impact level
- `Grupo asignado` (String): Assigned group

**Validation**:
- All required fields must be present
- Date format must be parseable
- Known enum values for Estatus, Urgencia, Impacto

---

## Data Transformations

### JSON Input → KPI Metrics

**Massive Incidents KPIs** (from incident JSON):
```
Total Incidents = COUNT(all records)
Pending Incidents = COUNT(Estatus not in ['Cerrado', 'Resuelto', 'Cancelado'])
7-Day Trend = (Pending Count Today - Pending Count 7 days ago) / Pending Count 7 days ago * 100
```

**Postmortem KPIs** (to be extracted from postmortem data):
```
Total Postmortems = COUNT(all postmortem records)
Unresolved Items = COUNT(items with status != completed)
Status Distribution = GROUPBY(status)
```

---

## File Locations

- **Input**: `data/output/*.json` (latest file by modification timestamp)
- **Processing**: Browser memory (no persistence)
- **Output**: Rendered HTML in Dashboard Hub page

---

## Schema Versioning

**Current Version**: 1.0

**Compatibility**:
- Supports JSON from CSV-to-JSON converter (v1.0+)
- Backward compatible with existing dashboard data format

