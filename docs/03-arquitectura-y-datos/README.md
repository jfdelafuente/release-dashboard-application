[← Volver al Índice General](../README.md)

# 03. Arquitectura del Sistema y Contratos de Datos

Diseño arquitectónico, infraestructura de servidores, endpoints de integración y modelo de persistencia desacoplada.

---

## 📚 Documentos de la Sección

| Documento | Audiencia | Propósito |
| :--- | :--- | :--- |
| **[estructura-proyecto.md](./estructura-proyecto.md)** | Arquitectos y DevOps | Organización detallada del repositorio, arquitectura atómica en VPS (`releases/` + symlink `current`), persistencia externa y matriz "quién sirve qué". |
| **[vps-infraestructura.md](./vps-infraestructura.md)** | Sysadmins y DevOps | Requisitos de servidor, topología de red (`10.132.26.96:8081`), directivas Nginx y coexistencia en el entorno VPS. |
| **[dashboards-api.md](./dashboards-api.md)** | Desarrolladores | Catálogo de endpoints, contratos de datos, proxy local con Epsilon Resumen IA y backend CSO (`:8000`). |
| **[migracion-esquemas.md](./migracion-esquemas.md)** | Desarrolladores | Historial de evolución de los esquemas JSON (`massive`, `postmortem`, `high_priority`) y estrategias de retrocompatibilidad en JavaScript. |

---

## 🏛️ Principio de Diseño Fundamental

El sistema implementa una arquitectura **desacoplada**:
1. **Frontend Estático:** Dashboards ligeros HTML/JS vanilla servidos vía Nginx o `serve_app.py`.
2. **Capa de Datos Externa:** Los ficheros procesados residen fuera del repositorio de código (en `/infocodes/var/storage/release-dashboard/` en producción y en `data/` en local).
3. **Microservicios Satélite:** Conexión semántica delegada al microservicio Epsilon IA y generación de presentaciones PPTX al backend FastAPI CSO.

