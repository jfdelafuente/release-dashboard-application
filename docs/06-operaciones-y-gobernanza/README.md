[← Volver al Índice General](../README.md)

# 06. Operaciones, Despliegue y Gobernanza

Procedimientos de entrega continua en el VPS de producción, control de versiones, auditoría técnica y políticas de protección de ramas.

---

## 📚 Documentos de la Sección

| Documento | Audiencia | Propósito |
| :--- | :--- | :--- |
| **[despliegue-vps.md](./despliegue-vps.md)** | DevOps y Sysadmins | Manual integral de despliegue Standalone Runtime mediante `deploy-production.ps1`, empaquetado selectivo, Zero Git en VPS y protocolo de Rollback Dual. |
| **[gestion-versiones.md](./gestion-versiones.md)** | Toda la Organización | Política oficial de versionado semántico (SemVer 2.0.0), trazabilidad en runtime atómico y etiquetado Git obligatorio. |
| **[logs-y-auditoria.md](./logs-y-auditoria.md)** | Operaciones y Soporte | Estándar unificado de bitácora técnica, estructura de logs persistentes en `/infocodes/var/log/` y políticas de retención y rotación. |
| **[integracion-continua-ci.md](./integracion-continua-ci.md)** | Desarrolladores y DevOps | Arquitectura de integración continua en GitHub Actions (`tests.yml` y `lint.yml`) ejecutada para las ramas `main` y `production`. |
| **[proteccion-ramas.md](./proteccion-ramas.md)** | Mantenedores del Repo | Reglas estrictas de protección de ramas en GitHub, requerimiento de PRs aprobados y status checks obligatorios de CI. |
| **[contributing.md](./contributing.md)** | Colaboradores | Guía de contribución para el equipo, flujo de trabajo con Git, convenciones de commit y buenas prácticas de desarrollo. |

---

## 🛡️ Reglas de Oro de Entrega en Producción

1. **Protección de Producción:** Jamás se realiza push directo a `production`. Todo cambio debe pasar por PR con revisión obligatoria y CI en verde.
2. **Despliegues Atómicos:** Todo despliegue en VPS se ejecuta mediante `deploy-production.ps1` creando una release fechada (`/releases/release_YYYYMMDD_HHMMSS/`) y conmutando el symlink `current` sin tiempo de inactividad.
3. **Rollback en 1-Clic:** Si se detecta una degradación post-despliegue, `rollback.sh` conmuta de inmediato a la release previa sin compilar ni transferir ficheros.
