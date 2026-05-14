# Documentation Index

📖 Complete documentation for the Release Dashboard Application.

**→ Start here**: [../README.md](../README.md) (project overview and quick start)

---

## 📚 Documentation Topics

### Getting Started
- **[QUICKSTART.md](QUICKSTART.md)** - 5-minute setup guide (recommended for first-time users)
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Development environment setup and workflows

### Using the Application
- **[API.md](API.md)** - Converter API reference and usage examples
- **[CONVERTER_USAGE.md](CONVERTER_USAGE.md)** - Detailed CSV-to-JSON converter guide
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common issues and solutions

### Architecture & Design
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture and component overview
- **[DATABASE.md](DATABASE.md)** - Data schema and storage (if applicable)

### Operations & Deployment
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Production deployment procedures
- **[SECURITY.md](../SECURITY.md)** - Security practices and incident response
- **[OPERATIONS.md](OPERATIONS.md)** - Monitoring, logging, and maintenance (if applicable)

### Contributing
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Code standards, commit conventions, PR process
- **[CHANGELOG.md](../CHANGELOG.md)** - Release history and version changes

---

## 🎯 Dashboards Overview

| Dashboard | File | Purpose |
|-----------|------|---------|
| **Dashboard Hub** (Principal) | `src/dashboards/dashboard-hub.html` | Unified access point with auto-loaded KPIs |
| **Massive Incidents** | `src/dashboards/massive-incidents-dashboard.html` | Detailed incident analysis with temporal trends |
| **Postmortem** | `src/dashboards/postmortem-dashboard.html` | Post-mortem analysis by deployments |

---

## 🔧 Data Workflow

```
CSV Files (data/input/)
    ↓
Converters (convert_incidents.bat, convert_postmortems.bat)
    ↓
JSON Output (data/output/*.json)
    ↓
Index Builder (build_index.py)
    ↓
Index (data/output/index.json)
    ↓
Dashboard Hub (Auto-loads all data)
    ↓
Specialized Dashboards (Incidents, Postmortems)
```

---

## 📊 Technology Stack

- **Backend**: Python 3.6+
- **Frontend**: HTML5, CSS3, JavaScript ES6+
- **Visualization**: Plotly.js
- **Testing**: pytest (80%+ coverage requirement)
- **Configuration**: Environment-based (.env files)

---

## ✅ Project Status

- **MVP**: Complete and validated ✅
- **Tests**: 264 passing (86.13% coverage) ✅
- **Dashboards**: All functional ✅
- **Converters**: Incidents + Postmortems ✅
- **Documentation**: Updated ✅

**Last Updated**: 2026-05-14
