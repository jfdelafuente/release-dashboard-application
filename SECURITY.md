# Guía y Política de Seguridad - Release Dashboard Application

Este documento describe las prácticas de seguridad, gestión de datos sensibles, protección de secretos y procedimientos de respuesta ante incidentes para el ecosistema **Release Dashboard Application** en el entorno corporativo de **Orange**.

---

## 🛡️ Principios Generales de Seguridad

La aplicación procesa métricas e información operativa de incidencias técnicas procedentes de Remedy y Confluence. Para garantizar la confidencialidad, integridad y disponibilidad del servicio, se aplican los siguientes principios:

1. **Defensa en profundidad**: Múltiples capas independientes de validación y control (gitignore, hooks locales, secret scanning y permisos en servidor).
2. **Mínimo privilegio**: El despliegue en producción opera como *Standalone Runtime* (sin acceso Git en el VPS) y bajo la cuenta de servicio específica del entorno (`infocodes`).
3. **Desacoplamiento y persistencia segura**: Los datos sensibles no viajan en el código ni en los paquetes de release; residen en rutas desacopladas del sistema de ficheros del VPS con permisos restringidos.
4. **Cero credenciales en repositorio**: Ninguna clave, contraseña o token corporativo puede almacenarse en el control de versiones.

---

## 🔒 Gestión de Datos y Almacenamiento

### Clasificación de Datos

- **Datos de Incidencias Operativas (Remedy)**: CSVs de entrada y JSONs procesados que contienen referencias de tickets, descripciones de problemas y tiempos de resolución.
- **Informes Ejecutivos (PowerPoint / PDF)**: Presentaciones generadas que consolidan análisis de impacto, causas raíz y cronologías técnicas.
- **Configuración y Entorno**: Parámetros de red, puertos y rutas de almacenamiento.

### Almacenamiento en Entorno Local (Desarrollo)

- Directorios temporales ignorados por Git:
  - `data/input/`: Ficheros CSV cargados para conversión.
  - `data/output/`: JSONs resultantes y catálogo `index.json`.
  - `data/errors/`: Reportes de validación de campos.
- Archivo local de variables de entorno: `.env` (ignorado en `.gitignore`).

### Almacenamiento en Producción (VPS `10.132.26.96`)

Los datos en producción están estrictamente desacoplados del directorio del código (`/infocodes/project/release-dashboard-application`):
- **Almacenamiento analítico**: `/infocodes/var/storage/release-dashboard/`
- **Almacenamiento de informes ejecutivos**: `/infocodes/var/storage/executive_pptx/`

Estos directorios:
- Pertenecen al usuario/grupo de servicio `infocodes:infocodes`.
- Cuentan con permisos `750` (lectura/escritura exclusiva para la cuenta de servicio y Nginx).
- Se preservan intactos durante cualquier despliegue, actualización o rollback ejecutado por [`deploy-production.ps1`](scripts/deploy-production.ps1).

---

## 🔑 Gestión de Secretos y Variables de Entorno

### Configuración Local (`.env`)

Para configurar el entorno local de desarrollo:

```bash
# Copiar plantilla base
cp config/.env.example .env

# Editar parámetros según necesidad local
PORT=8080
STORAGE_PATH=./data
```

**Reglas obligatorias**:
- ✅ `.env` está expresamente incluido en `.gitignore`.
- ❌ **Prohibido** commitear `.env` o archivos `.env.*` al repositorio.
- ❌ **Prohibido** utilizar credenciales de producción en máquinas locales de desarrollo.

### Producción (GitHub Secrets y Entorno del Servidor)

- Cualquier token o secreto requerido en pipelines de CI/CD se gestiona a través de **GitHub Secrets** con acceso restringido a administradores.
- Los scripts de despliegue y servidores utilizan variables inyectadas por el sistema operativo o cargadas desde ubicaciones protegidas del VPS.

---

## 🛑 Sistemas de Prevención Multi-Capa

```
[ Desarrollador ]
       │
       ▼
[ Capa 1: .gitignore ]  ──▶ Bloquea .env, data/, logs/, temporales
       │
       ▼
[ Capa 2: Pre-commit Hook ]  ──▶ Intercepta tokens, passwords y archivos de entorno
       │ (git commit)
       ▼
[ Capa 3: GitHub Push Protection ]  ──▶ Bloquea secretos conocidos en el push remoto
       │ (git push)
       ▼
[ Capa 4: Standalone Runtime en VPS ]  ──▶ Sin Git en servidor, persistencia desacoplada
```

### Capa 1: Reglas de `.gitignore`

El archivo [`.gitignore`](.gitignore) previene el rastreo accidental de:
- Ficheros de entorno: `.env`, `.env.*`.
- Carpetas de datos de incidencias: `data/`, `datos/`.
- Claves privadas y certificados: `*.key`, `*.pem`, `*.crt`.
- Archivos generados y cachés de testing (`.pytest_cache`, `.coverage`, `__pycache__`).

### Capa 2: Hook de Pre-commit

El repositorio proporciona el script [`config/pre-commit-hook.sh`](config/pre-commit-hook.sh) para validar los cambios antes de consolidar cualquier commit:

```bash
# Instalación del hook (ejecución única por desarrollador)
cp config/pre-commit-hook.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

# Ejecución manual de prueba
bash config/pre-commit-hook.sh
```

**Comprobaciones efectuadas**:
- Detección de archivos con nomenclatura sensible (`.env`, `.key`, `id_rsa`, etc.).
- Búsqueda de patrones de credenciales (`password=`, `token=`, `api_key=`, `secret=`).
- Bloqueo inmediato del commit si se detecta cualquier anomalía.

### Capa 3: GitHub Secret Scanning y Protección de Ramas

- **Push Protection**: Bloqueo automático en GitHub ante cualquier intento de publicar tokens o claves reconocidas.
- **Rama `production` protegida**: Requiere aprobaciones obligatorias de PR y paso exitoso de la suite de pruebas (516+ tests) antes de fusionar cualquier cambio (ver [`docs/06-operaciones-y-gobernanza/proteccion-ramas.md`](docs/06-operaciones-y-gobernanza/proteccion-ramas.md)).

---

## 🌐 Seguridad en Red y Pasarelas API

### Proxy Inverso y CORS

1. **Epsilon IA**:
   - Las consultas a `https://soptmc.si.orange.es/MonTMC/api/epsilon/resumenIA/{ID}` se canalizan a través del proxy local de [`serve_app.py`](serve_app.py) o las directivas de [`nginx.conf`](nginx.conf).
   - Evita la exposición de cabeceras sensibles en el cliente y neutraliza problemas de CORS.
2. **Backend FastAPI (`cso-incident-masivas-report`)**:
   - Integración mediante endpoints específicos en localhost (`:8000`) o a través del enrutador de Nginx en producción (`:8081`).
   - Los datos viajan cifrados o aislados en la red interna corporativa.

### Tránsito de Despliegue

- Las transferencias entre la máquina local y el VPS se ejecutan exclusivamente mediante canales seguros: **SSH** y **SCP**.
- La clave privada SSH nunca reside en el repositorio y requiere permisos locales restrictivos en el puesto del operador.

---

## 📋 Registro Seguro de Logs

Para evitar la fuga de información confidencial en los ficheros de log:
- **Enmascaramiento**: Si es necesario registrar tokens o identificadores sensibles, se deben enmascarar (ej. `tok_1234...abcd`).
- **Trazas de error**: Las excepciones y *stack traces* mostradas al usuario final en los dashboards no deben exponer rutas internas completas ni datos de conexión.
- **Rotación**: Los logs generados por el servidor y los scripts de despliegue (`logs/deployments/`) se rotan y custodian conforme a los estándares de retención corporativos.

---

## 🚨 Plan de Respuesta ante Incidentes de Seguridad

### Si se commitea un secreto o dato confidencial accidentalmente:

1. **Contención inmediata**:
   - Si no se ha hecho push remoto:
     ```bash
     # Revertir el commit preservando los cambios en local
     git reset HEAD~1
     # Desmarcar el fichero confidencial
     git reset ruta/al/fichero-sensible
     ```
   - Si ya se ha realizado push a GitHub:
     - Invalidar o revocar la credencial **inmediatamente** en el proveedor o sistema correspondiente (Remedy, Confluence, etc.).
     - Notificar al responsable técnico para evaluar el reescrito del histórico o aplicar `git filter-repo`.
     - Generar un nuevo commit que elimine la referencia del árbol de ficheros.
2. **Evaluación de impacto**:
   - Revisar logs de auditoría para verificar si la credencial revocada registró actividad no autorizada.
3. **Registro y lecciones aprendidas**:
   - Documentar la incidencia, verificar la causa y asegurar que el hook de pre-commit impida recurrencias futuras.

---

## ✅ Lista de Verificación (Checklist)

### Antes de cada Despliegue a Producción

- [ ] La rama actual es `production` y está sincronizada con `origin/production`.
- [ ] No existen ficheros `.env` ni claves privadas en el área de preparación (*staging*).
- [ ] La suite de pruebas de `converters/` supera el 100% de éxito (516+ tests pasando).
- [ ] Las rutas de almacenamiento apuntan al directorio desacoplado `/infocodes/var/storage/`.
- [ ] El script de despliegue [`deploy-production.ps1`](scripts/deploy-production.ps1) finaliza con sondeo HTTP 200/302 OK.

---

## 📞 Contacto y Soporte de Seguridad

Para reportar vulnerabilidades o incidencias de seguridad en este proyecto:
- Contactar directamente con el equipo de soporte técnico y operaciones del proyecto (*Release Dashboard Application - Orange*).
- No divulgar detalles de vulnerabilidades en incidencias públicas o canales abiertos sin resolver.

---

**Última actualización**: 2026-10-21
