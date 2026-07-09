# Índice de Documentación

📖 Documentación completa de Release Dashboard Application.

**→ Empieza aquí**: [../README.md](../README.md) (visión general y arranque rápido)

---

## 📚 Temas

### Primeros pasos
- **[QUICKSTART.md](QUICKSTART.md)** - Guía de instalación y primer uso
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Entorno de desarrollo y flujo de trabajo

### Usar la aplicación
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Problemas comunes y soluciones
- **[../converters/docs/API.md](../converters/docs/API.md)** - Referencia de la API de los conversores CSV→JSON
- **[../converters/docs/CSV-TO-JSON-WORKFLOW.md](../converters/docs/CSV-TO-JSON-WORKFLOW.md)** - Flujo detallado de conversión

### Arquitectura y diseño
- **[PROJECT-STRUCTURE.md](PROJECT-STRUCTURE.md)** - Estructura del proyecto y de producción
- **[../converters/docs/ARCHITECTURE.md](../converters/docs/ARCHITECTURE.md)** - Arquitectura del módulo de conversión

### Operaciones y despliegue
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Procedimiento de despliegue (manual, vía SSH)
- **[CI-CD.md](CI-CD.md)** - Qué automatiza CI (tests y linting) y qué no (el despliegue)
- **[VERSION-MANAGEMENT.md](VERSION-MANAGEMENT.md)** - Versionado semántico
- **[VPS-REQUIREMENTS.md](VPS-REQUIREMENTS.md)** - Requisitos del servidor
- **[../SECURITY.md](../SECURITY.md)** - Prácticas de seguridad

### Contribuir
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Estándares de código, commits, proceso de PR
- **[GITHUB-BRANCH-PROTECTION.md](GITHUB-BRANCH-PROTECTION.md)** - Reglas de protección de ramas
- **[../CHANGELOG.md](../CHANGELOG.md)** - Historial de versiones
- **[MIGRATION.md](MIGRATION.md)** - Cambios de formato entre versiones del conversor

---

## 🎯 Dashboards

| Dashboard | Archivo | Propósito |
|-----------|------|---------|
| **Portal** (entrada principal) | `dashboards/dashboard-portal.html` | Punto de acceso único, con tarjetas a cada dashboard |
| **Incidencias Masivas** | `dashboards/massive-incidents-dashboard.html` | Análisis temporal de incidencias masivas |
| **Postmortem / Release** | `dashboards/postmortem-dashboard.html` | Análisis por despliegue (PAP/MESA) |

`dashboards/index.html` redirige automáticamente al Portal.

---

## 🔧 Flujo de Datos

```
CSV (subido desde el navegador, o en data/input/)
    ↓
serve_app.py [/api/upload]  o  converters/cli/convert_incidents.py / convert_postmortems.py
    ↓
JSON (data/output/) + build_index.py → index.json
    ↓
Portal (dashboard-portal.html)
    ↓
Incidencias Masivas · Postmortem/Release
```

---

## 📊 Stack Tecnológico

- **Conversores**: Python 3.8+
- **Dashboards**: HTML5, CSS3, JavaScript ES6+ (sin framework, sin build step)
- **Visualización**: Plotly.js (vía CDN)
- **Testing**: pytest (ver [converters/docs/TEST_STRUCTURE.md](../converters/docs/TEST_STRUCTURE.md))

---

## ✅ Estado del Proyecto

- **Dashboards**: ✅ Portal, Incidencias Masivas y Postmortem/Release funcionales
- **Subida de CSV desde el navegador**: ✅ vía `serve_app.py` (`/api/upload`)
- **Conversores**: ✅ Incidencias masivas + Postmortems
- **CI**: ✅ tests y linting automatizados en cada PR (ver [CI-CD.md](CI-CD.md))
- **Despliegue**: manual (SSH + git pull), ver [DEPLOYMENT.md](DEPLOYMENT.md)

---

**Última actualización**: 2026-07-09
