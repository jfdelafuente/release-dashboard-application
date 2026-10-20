# Guía de Despliegue de Release Dashboard Application

Procedimiento de despliegue moderno de Release Dashboard Application en el VPS de producción (`infocodes@10.132.26.96`).

El despliegue está basado en un **artefacto empaquetado selectivo (Standalone Runtime)** generado en local, transferido por SCP y desplegado de forma segura en el servidor, eliminando por completo operaciones de `git pull`, `git stash` o clonación en el servidor de producción.

---

## 🏛️ Principios de la Arquitectura de Despliegue

1. **Standalone Runtime (Empaquetado Selectivo)**:
   - Solo se sube a producción lo estrictamente necesario para la ejecución (`dashboards/`, `converters/`, `scripts/`, `nginx.conf`, `requirements.txt`, `VERSION`).
   - Se excluyen suites de test (`tests/`), especificaciones (`specs/`), historias de git (`.git/`), archivos `.md` de desarrollo y archivos binarios de prueba (`*.pptx` locales).
   - El artefacto pasa de ocupar cientos de megas a solo **~2.3 MB**.
2. **Cero Git en Producción**:
   - Sin dependencias de conectividad de red externa desde el VPS a GitHub.
   - Sin riesgo de conflictos de merge, `git stash`, o sobreescritura accidental de datos dinámicos.
3. **Persistencia Estricta de Datos**:
   - El directorio `data/` (`data/input/`, `data/output/`, `data/reports/`, `data/errors/`, `data/archive/`) es **estrictamente persistente** y **nunca** se sobreescribe ni se incluye en el artefacto.
4. **Copia Preventiva y Rollback Instantáneo**:
   - Cada despliegue genera automáticamente una copia de seguridad comprimida en `/infocodes/var/backups/release-dashboard-application/backup_YYYYMMDD_HHMMSS.tar.gz`.
   - Se mantiene una política de rotación automática conservando los últimos 5 backups.
   - Posibilidad de rollback inmediato en 1 clic si se detecta cualquier anomalía.
5. **Sincronización y Validación Segura de Nginx**:
   - `nginx.conf` se valida sintácticamente (`nginx -t`) antes de recargar.
   - Si la configuración es válida, se recarga en caliente (`nginx -s reload`) sin cortar conexiones ni requerir permisos de `root`.
   - Si `nginx -t` detecta algún error de sintaxis, se aborta y se revierte automáticamente a la configuración previa.

---

## 📦 Qué se despliega desde este repositorio

| Ruta servida | Origen | Contenido |
|---|---|---|
| `/dashboards/portal/` | `dashboards/portal/` | Portal central de accesos y buscador global |
| `/dashboards/massive-incidents/` | `dashboards/massive-incidents/` | Dashboard de Incidencias Masivas |
| `/dashboards/postmortem/` | `dashboards/postmortem/` | Dashboard de Informes Postmortem / Releases |
| `/dashboards/release-kpis/` | `dashboards/release-kpis/` | Dashboard de KPIs por Release |
| `/dashboards/reportes-incidencias/` | `dashboards/reportes-incidencias/` | Frontend de gestión y análisis de reportes de incidencias |
| `/dashboards/informes/` | `dashboards/informes/` | Informes específicos (p. ej. incidencias pendientes R9) |
| `/data/` | `data/` del servidor | JSONs de incidencias/postmortems y reportes PPTX |
| `/api/epsilon/*` | Proxy en Nginx | Proxy reverso con caché a la API de Epsilon IA |

Servicios hermanos en el mismo Nginx (despliegues independientes):
- **`/api`** → Proxy al backend FastAPI (`localhost:8000`), del repositorio hermano `cso-incident-masivas-report`.
- **`/problemas`** → Proxy al backend Next.js (`localhost:3001`) de Gestión de Problemas.

---

## ⚡ Despliegue en 1 Clic desde Windows (Recomendado)

Desde tu terminal de PowerShell en la máquina local (rama operativa `production`):

```powershell
.\scripts\deploy-production.ps1
```

### Opciones y Parámetros del Script

| Parámetro | Descripción |
|---|---|
| *(sin parámetros)* | Proceso completo: valida git local, push a GitHub, empaqueta artefacto, sube por SCP, aplica en el VPS, valida Nginx y comprueba sondas de salud. |
| `-VerifyOnly` | Solo consulta el estado de Nginx, estadísticas de datos y sondas HTTP remotas sin tocar ningún archivo ni recargar. |
| `-Rollback` | Restaura instantáneamente la copia de seguridad más reciente en `/infocodes/var/backups/release-dashboard-application/` y recarga Nginx. |
| `-SkipPush` | Salta el `git push origin production` y empaqueta/despliega directamente el estado local. |
| `-SkipBuild` | Salta la generación del tarball local y sube el `dist/release-dashboard-runtime.tar.gz` existente. |
| `-SkipUpload` | Utiliza el tarball ya presente en `/tmp/release-dashboard-runtime.tar.gz` en el VPS. |
| `-DryRun` | Muestra los pasos y el script bash remoto que se ejecutaría sin aplicar ningún cambio. |

---

## 🛠️ Herramientas de Control en el VPS

En el propio servidor (`/infocodes/project/release-dashboard-application`), se dispone de scripts directos de administración:

### 1. Comprobación de Estado (`./status.sh`)
```bash
./status.sh
```
Muestra:
- Versión desplegada (`VERSION`).
- Estado de configuración del proceso Nginx (puerto 8081).
- Volúmenes de datos (`CSV` en input, `JSON` en output, `PPTX` en reports).
- Sondas de salud HTTP para todos los dashboards y endpoints de proxy.

### 2. Rollback Inmediato (`./rollback.sh`)
```bash
# Restaurar la última copia preventiva:
./rollback.sh

# Restaurar una copia específica:
./rollback.sh backup_20261015_145000.tar.gz
```

---

## 🛡️ Proxy y Caché de Epsilon IA (Nginx)

Nginx actúa como proxy seguro y protector de la API de Epsilon IA mediante una caché compartida (`keys_zone=my_cache:10m`):

```nginx
location /api/epsilon/ {
    proxy_pass https://soptmc.si.orange.es/MonTMC/api/epsilon/;
    proxy_ssl_verify off;
    proxy_ssl_server_name on;
    proxy_set_header Host soptmc.si.orange.es;
    proxy_connect_timeout 15s;
    proxy_read_timeout 30s;

    # Caché compartida para no saturar la API de Epsilon IA
    proxy_cache my_cache;
    proxy_cache_valid 200 15m;
    proxy_cache_valid 404 1m;
    proxy_cache_use_stale error timeout updating http_500 http_502 http_503 http_504;
    proxy_cache_lock on;
    proxy_cache_lock_timeout 5s;
    proxy_ignore_headers Cache-Control Expires Set-Cookie;
    proxy_cache_bypass $http_cache_control;
    add_header X-Cache-Status $upstream_cache_status always;
}
```

- **TTL de 15 minutos (`proxy_cache_valid 200 15m`)**: Nginx responde en milisegundos directamente sin saturar Epsilon.
- **`proxy_cache_lock on`**: Evita avalanchas concurrentes agrupando peticiones en vuelo.
- **`proxy_cache_use_stale`**: Resiliencia total ante caídas o lentitud de la API externa (sirve caché en lugar de error).
- **`add_header X-Cache-Status`**: Inspeccionable en DevTools (`HIT` o `MISS`).

---

## 🔄 Conversión Batch de CSV (Cron en el VPS)

La generación periódica de los JSONs que consumen los dashboards se realiza con `scripts/generate-dashboards.sh`, configurado en el crontab del usuario `infocodes`:

```bash
# Ejecución diaria a las 2 AM:
0 2 * * * /infocodes/project/release-dashboard-application/scripts/generate-dashboards.sh >> /infocodes/project/release-dashboard-application/logs/dashboards-cron.log 2>&1
```
