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
- **[INFORME-PPT-POSTMORTEM.md](INFORME-PPT-POSTMORTEM.md)** - Cómo generar el informe PPT de postmortem por release (navegador y línea de comandos)
- **[INFORME-EJECUTIVO-POSTMORTEM.md](INFORME-EJECUTIVO-POSTMORTEM.md)** - Cómo generar el informe ejecutivo PPT de una incidencia (navegador y CLI)
- **[../converters/docs/API.md](../converters/docs/API.md)** - Referencia de la API de los conversores CSV→JSON
- **[../converters/docs/CSV-TO-JSON-WORKFLOW.md](../converters/docs/CSV-TO-JSON-WORKFLOW.md)** - Flujo detallado de conversión

### Arquitectura y diseño
- **[PROJECT-STRUCTURE.md](PROJECT-STRUCTURE.md)** - Estructura del proyecto y de producción
- **[DASHBOARDS-API.md](DASHBOARDS-API.md)** - Catálogo de APIs e integraciones de los dashboards
- **[../converters/docs/ARCHITECTURE.md](../converters/docs/ARCHITECTURE.md)** - Arquitectura del módulo de conversión

### Operaciones y despliegue
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Procedimiento de despliegue automatizado (Standalone Runtime vía `deploy-production.ps1`)
- **[LOGS.md](LOGS.md)** - Gestión de logs, auditoría y trazabilidad en servidor y desarrollo
- **[../scripts/README.md](../scripts/README.md)** - Referencia de scripts de despliegue, status, rollback y cron
- **[CI.md](CI.md)** - Integración continua (tests unitarios, cobertura y linters en GitHub Actions)
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
| **Portal** (entrada principal) | `dashboards/portal/index.html` | Punto de acceso único, con buscador Remedy y Resumen IA |
| **Incidencias Masivas** | `dashboards/massive-incidents/index.html` | Análisis temporal y evolutivo de incidencias masivas |
| **Postmortem / Release** | `dashboards/postmortem/index.html` | Análisis por despliegue (PAP/MESA) y KPIs |
| **KPIs Release (Histórico)** | `dashboards/release-kpis/index.html` | Serie histórica de KPIs por release y exportación PPT |
| **Reportes de Incidencias** | `dashboards/reportes-incidencias/index.html` | Gestión tabular, reportes de impacto y exportación PDF/PPTX |
| **Informes Específicos** | `dashboards/informes/incidencias-pdtes-r9-2026/` | Informe ejecutivo de incidencias pendientes R9 |

`dashboards/index.html` redirige automáticamente al Portal.

---

## 🔧 Flujo de Datos

```
CSV (subido desde el navegador, o en data/input/)
    ↓
serve_app.py [/api/upload]  o  converters/cli/convert_incidents.py / convert_postmortems.py
    ↓
JSON estructurado (data/output/) + build_index.py → index.json
    ↓
Portal Hub (dashboards/portal/)  <-- [Consultas en tiempo real a Epsilon IA]
    ↓
Incidencias Masivas · Postmortem/Release · KPIs · Reportes de Incidencias
    ↓
Generación de Informes PPTX / PDF (report_generator / python-pptx)
```

---

## 📊 Stack Tecnológico

- **Conversores y Backend**: Python 3.8+ (FastAPI en `:8000`, `serve_app.py` en local)
- **Dashboards**: HTML5, CSS3, JavaScript ES6+ (sin framework pesado, sin build step)
- **Visualización**: Plotly.js (vía CDN), tokens oficiales Orange
- **Testing**: pytest (ver [converters/docs/TEST_STRUCTURE.md](../converters/docs/TEST_STRUCTURE.md))

---

## ✅ Estado del Proyecto

- **Dashboards**: ✅ Suite completa de portales, incidencias masivas, postmortems y reportes operativos
- **Subida de CSV desde el navegador**: ✅ vía `serve_app.py` (`/api/upload`) y CLI
- **Conversores**: ✅ Incidencias masivas, Postmortems e informes ejecutivos PPTX
- **CI**: ✅ tests y linting automatizados en cada PR (ver [CI.md](CI.md))
- **Despliegue**: ✅ Automatizado en 1 clic vía `deploy-production.ps1` con backup rotativo y rollback automático (ver [DEPLOYMENT.md](DEPLOYMENT.md))
- **Logs y Auditoría**: ✅ Desacoplados en /infocodes/var/log/ y rotación de backups (ver [LOGS.md](LOGS.md))

---

**Última actualización**: 2026-10-20
