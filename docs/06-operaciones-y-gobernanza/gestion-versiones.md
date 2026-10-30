# Política de Gestión de Versiones

Este documento define la política oficial de versionado semántico, incremento, etiquetado y trazabilidad en producción para Release Dashboard Application.

---

## 📌 Esquema de Versionado: Semantic Versioning (SemVer 2.0.0)

La aplicación sigue el estándar [SemVer 2.0.0](https://semver.org/lang/es/):

$$\text{MAJOR}.\text{MINOR}.\text{PATCH}$$

- **Versión actual**: Se consulta en el archivo [VERSION](../../VERSION) ubicado en la raíz del repositorio.
- **Ejemplo**: `0.2.0`

### Reglas de Incremento

| Componente | Criterio de Incremento | Ejemplo |
|---|---|---|
| **MAJOR** | Cambios incompatibles en contratos de datos (JSON), reestructuración radical del frontend o cambios de arquitectura mayores. | `1.0.0` (desde `0.2.0`) |
| **MINOR** | Nuevas funcionalidades, conversores adicionales, nuevos dashboards o mejoras compatibles hacia atrás. | `0.3.0` (desde `0.2.0`) |
| **PATCH** | Correcciones de errores (bugfixes), optimizaciones de rendimiento, ajustes de estilos o documentación. | `0.2.1` (desde `0.2.0`) |

---

## 📄 El Archivo `VERSION`

- **Ubicación**: Archivo `VERSION` en la raíz del repositorio.
- **Formato**: Texto plano de una única línea sin prefijos ni saltos extra (ejemplo: `0.2.0`).

### Procedimiento de Actualización

1. **Momento**: Antes de fusionar un Pull Request hacia la rama `production` o `main`.
2. **Actualización simultánea**: Debe actualizarse al mismo tiempo que la sección correspondiente en [CHANGELOG.md](../../CHANGELOG.md).
3. **Comando de actualización**:
   ```bash
   echo 0.2.1 > VERSION
   git add VERSION CHANGELOG.md
   git commit -m "chore: bump version to 0.2.1"
   ```

> **Garantía en el Despliegue**: El script [scripts/deploy-production.ps1](../../scripts/deploy-production.ps1) comprueba la existencia de `VERSION` y lo empaqueta automáticamente dentro del artefacto runtime (`dist/release-dashboard-runtime.tar.gz`). Si el archivo no existiera localmente, genera automáticamente una versión basada en timestamp (`0.2.0-YYYYMMDD`).

---

## 🏷️ Etiquetado Git (Git Tags)

Todo despliegue a producción **debe contar con una etiqueta Git anotada** asociada al commit exacto desplegado.

### Formato de Etiquetas

$$\text{v}\text{MAJOR}.\text{MINOR}.\text{PATCH}$$

*Ejemplos*: `v0.1.0`, `v0.2.0`, `v1.0.0`.

### Procedimiento de Creación y Publicación

```bash
# 1. Asegurar que VERSION coincide con la versión objetivo
cat VERSION
# Salida esperada: 0.2.0

# 2. Crear etiqueta anotada con descripción del release
git tag -a v0.2.0 -m "Release v0.2.0: Despliegue seguro Standalone Runtime y Storage Desacoplado"

# 3. Publicar la etiqueta en el repositorio remoto
git push origin v0.2.0

# 4. Verificar la etiqueta creada
git tag -n1 -l "v0.2.0"
```

---

## 🌐 Trazabilidad en Producción (VPS 10.132.26.96)

El modelo de producción implementa una arquitectura **Standalone Runtime sin Git en el servidor**:

```text
/infocodes/project/release-dashboard-application/
├── releases/
│   ├── 20261015_120000/ (contiene VERSION: 0.1.9)
│   └── 20261020_164500/ (contiene VERSION: 0.2.0)
└── current ──► releases/20261020_164500/
```

### Comprobación de la Versión Desplegada

Para auditar en tiempo real qué versión está activa en el VPS:

- **Vía comando SSH**:
  ```bash
  ssh infocodes@10.132.26.96 "cat /infocodes/project/release-dashboard-application/current/VERSION"
  ```
- **Vía script de estado en el servidor**:
  ```bash
  ssh infocodes@10.132.26.96 "/infocodes/project/release-dashboard-application/scripts/status.sh"
  ```
- **Desde PowerShell en local**:
  ```powershell
  .\scripts\deploy-production.ps1 -VerifyOnly
  ```

---

## 🔄 Política de Rollback y Versionado

En caso de contingencia o detección de regresiones en producción, el sistema soporta dos modalidades inmediatas de rollback sin recompilar código:

1. **Rollback Rápido por Symlink (`scripts/rollback.sh`)**:
   Conmuta el enlace simbólico `current` a la release precedente en el directorio `releases/` y recarga Nginx sin caída de servicio.
   ```bash
   ssh infocodes@10.132.26.96 "/infocodes/project/release-dashboard-application/scripts/rollback.sh"
   ```
2. **Rollback Preventivo por Copia de Seguridad (`deploy-production.ps1 -Rollback`)**:
   Restaura el archivo `backup_<TIMESTAMP>.tar.gz` generado inmediatamente antes del último despliegue en `/infocodes/var/backups/release-dashboard-application/`.
   ```powershell
   .\scripts\deploy-production.ps1 -Rollback
   ```

Tras cualquier rollback, `scripts/status.sh` confirmará la versión restaurada en pantalla.

---

## ✅ Checklist de Calidad Pre-Release

Antes de incrementar la versión y empaquetar para producción, deben superarse los siguientes controles:

### 1. Calidad de Código y Pruebas
- [ ] Suite de pruebas completa aprobada (516+ tests):
  ```bash
  cd converters
  pytest tests/ -v --cov=src --cov-fail-under=80
  cd ..
  ```
- [ ] Cobertura de código superior o igual al **80%**.
- [ ] Validación de estilo y análisis estático sin errores:
  ```bash
  cd converters
  flake8 src cli tests
  black --check src cli tests
  isort --check-only src cli tests
  cd ..
  ```

### 2. Documentación y Trazabilidad
- [ ] Archivo `VERSION` actualizado.
- [ ] Archivo [CHANGELOG.md](../../CHANGELOG.md) actualizado con la fecha, versión y resumen de cambios categorizados (`Added`, `Changed`, `Fixed`, `Security`).
- [ ] Manuales técnicos en `docs/` sincronizados si hubo modificaciones en arquitectura o endpoints.
- [ ] Cumplimiento de marca corporativa estricto: **Orange** (prohibido MASORANGE u otras marcas).

### 3. Etiquetado y Despliegue
- [ ] Commit de versión fusionado en la rama `production`.
- [ ] Etiqueta Git `vX.Y.Z` creada y enviada a `origin`.
- [ ] Despliegue ejecutado exitosamente con `.\scripts\deploy-production.ps1`.
- [ ] Verificación post-despliegue mediante sondas HTTP (`-VerifyOnly` o `status.sh`).

---

## 📋 Estructura de Registro en `CHANGELOG.md`

Las entradas deben seguir el estándar [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/):

```markdown
## [0.2.0] - 2026-10-20

### Added
- Despliegue atómico Standalone Runtime sin Git en el VPS.
- Almacenamiento persistente desacoplado en `/infocodes/var/storage/`.
- Soporte para generación de informes ejecutivos PowerPoint con motor CSO.

### Changed
- Puerto local por defecto reubicado a 8080 para evitar colisiones con FastAPI.
- Normalización integral de documentación técnica al español.

### Fixed
- Corrección de rutas de ejecución de pruebas en workflows de GitHub Actions.
```

---

## ❓ Preguntas Frecuentes (FAQ)

**¿Con qué frecuencia se debe incrementar la versión MAJOR?**  
Únicamente ante cambios drásticos en los contratos JSON que rompan los dashboards existentes o reestructuraciones completas del sistema.

**¿Las correcciones menores (hotfixes) requieren tag Git?**  
Sí. Cualquier modificación que se despliegue en producción debe contar con un tag semántico `vX.Y.Z` para mantener una trazabilidad total entre Git y el VPS.

**¿Qué ocurre si se despliega sin actualizar el archivo `VERSION`?**  
El script `deploy-production.ps1` utilizará la versión existente en el archivo `VERSION`. Es una buena práctica actualizarlo siempre para que `status.sh` y las auditorías reflejen con fidelidad el código en ejecución.

---

## Documentación Relacionada

- [DEPLOYMENT.md](despliegue-vps.md) — Manual integral de despliegue Standalone Runtime.
- [DEVELOPMENT.md](../01-primeros-pasos/desarrollo.md) — Flujos de trabajo y directrices de desarrollo local.
- [GITHUB-BRANCH-PROTECTION.md](proteccion-ramas.md) — Reglas de ramas protegidas para `main` y `production`.
- [PROJECT-STRUCTURE.md](../03-arquitectura-y-datos/estructura-proyecto.md) — Arquitectura y mapa exhaustivo de directorios.
- [LOGS.md](logs-y-auditoria.md) — Estándar de bitácora técnica e intervenciones de producción.

---

**Última actualización**: 2026-10-20  
**Versión de política**: 2.0
