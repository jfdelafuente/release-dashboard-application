# Guía de Despliegue

Procedimiento de despliegue de Release Dashboard Application en el VPS. Se cuenta con el script automatizado `./deploy.sh` que gestiona backups preventivos, stash seguro de datos locales, pull de `production`, sincronización y validación de `nginx.conf` con rollback automático, y pruebas de salud (smoke tests).

---

## Qué se despliega desde este repo

Este repositorio aporta **contenido estático** (dashboards HTML/CSS/JS) y **datos JSON**. Nginx los sirve directamente desde el checkout de la rama `production` en el VPS, sin build ni empaquetado:

| Ruta servida | Origen | Contenido |
|---|---|---|
| `/dashboards` | `dashboards/` del repo | Portal (`dashboards/portal/`), Incidencias Masivas, Postmortem/Release, KPIs Release |
| `/data` | `data/` del repo | JSONs generados por los conversores (`data/output/`) |
| `/api/epsilon/*` | Proxy en Nginx | Proxy reverso hacia `https://soptmc.si.orange.es/MonTMC/api/epsilon/` |

Lo que **no** se despliega desde este repo (corren aparte, en otros procesos/repos hermanos):

- **`/api`** → proxy a un backend FastAPI (`localhost:8000`), del repo hermano `cso-incident-masivas-report`.
- **`/reportes-incidencias`** → alias directo al checkout de `cso-incident-masivas-report/app`.
- **`/problemas`** → proxy a un backend Next.js (`localhost:3001`) gestionado con `pm2`, de un repo/backend de Gestión de Problemas.

Por tanto, desplegar este repo **no reinicia ni afecta** a esos otros servicios; son despliegues independientes que no están documentados aquí.

---

## ⚡ Despliegue Automatizado (Recomendado)

El script `./deploy.sh` realiza todo el proceso de forma desatendida y segura:

```bash
cd /infocodes/project/release-dashboard-application
./deploy.sh
```

### ¿Qué hace `./deploy.sh` automáticamente?
1. **Backup preventivo**: Guarda copia de seguridad de `data/output/` y del fichero activo `/infocodes/nginx/conf/nginx.conf` en `backups/deploy-YYYYMMDD_HHMMSS/`.
2. **Stash automático**: Si hay modificaciones locales en el servidor, las guarda con `git stash` y las restaura tras el pull para evitar bloqueos.
3. **Git pull**: Descarga y aplica los commits de `origin/production`.
4. **Sincronización inteligente de Nginx**:
   - Compara el `nginx.conf` del repo con el activo en `/infocodes/nginx/conf/nginx.conf`.
   - Si cambió, lo copia y ejecuta `nginx -t`.
   - Si la sintaxis es correcta, recarga en caliente con `nginx -s reload`.
   - **Rollback automático**: Si `nginx -t` detecta algún error de sintaxis, restaura inmediatamente la copia de seguridad previa para que el servidor nunca quede caído.
5. **Smoke tests**: Comprueba mediante `curl` interno que el portal y el proxy `/api/epsilon/` respondan `200 OK`.
6. **Mantenimiento**: Rota automáticamente las copias de seguridad conservando las últimas 5.
7. **Logging completo**: Registra la salida en `logs/deploy-YYYYMMDD.log`.

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

## Procedimiento Manual (Paso a paso alternativo)

Si por alguna razón prefieres realizar el despliegue manualmente paso a paso:

1. **Verificar antes de desplegar**:
   - Los tests pasan localmente/en CI (`tests.yml` en `.github/workflows/`).
   - El cambio está fusionado en `main` (o en la rama desde la que se promueve a `production`).
2. **Conectar al VPS por SSH.**
3. **Actualizar el checkout de la rama `production`**:
   ```bash
   cd /infocodes/project/release-dashboard-application
   git fetch origin
   git checkout production
   git pull origin production
   ```
   > 💡 **Si `git pull` da error por cambios sin commitear en `data/output/`** (p. ej. archivos JSON generados o eliminados localmente en el servidor):
   > ```bash
   > git stash
   > git pull origin production
   > git stash pop
   > ```
   > O si no necesitas conservar las modificaciones locales de esos JSONs:
   > ```bash
   > git restore data/output/
   > git pull origin production
   > ```

4. **Si cambió `nginx.conf`**:
   Nginx corre en espacio de usuario bajo `/infocodes/` (escuchando en el puerto 8081 y con PID en `/infocodes/var/run/nginx.pid`), por lo que **no se requiere `sudo` ni `systemctl`**.
   El fichero de configuración activo que Nginx lee en el VPS está ubicado en `/infocodes/nginx/conf/nginx.conf`. Por tanto, tras el `git pull`, se debe sincronizar el fichero y recargar:
   ```bash
   cp /infocodes/project/release-dashboard-application/nginx.conf /infocodes/nginx/conf/nginx.conf
   nginx -t               # Validar sintaxis
   nginx -s reload        # Recargar Nginx en caliente sin cortar conexiones
   ```
   *(Alternativa enviando señal directa: `kill -HUP $(cat /infocodes/var/run/nginx.pid)`).*

   > ℹ️ **Nota sobre cambios en Dashboards**: Los cambios en HTML, CSS y JS (`dashboards/` como `index.html`, `resumen-ia.css` o `resumen-ia.js`) se aplican **inmediatamente tras el `git pull`** sin necesidad de recargar Nginx, ya que se sirven por `alias` directo al sistema de archivos. La recarga con `nginx -s reload` solo es necesaria si se ha modificado `nginx.conf` (por ejemplo, para añadir bloques de proxy como `/api/epsilon/`).
5. **Si cambió algo en `converters/` o en dependencias Python**: reinstalar dependencias si aplica.
   ```bash
   pip install -r converters/requirements.txt
   ```
   **No confirmado**: si existe algún proceso Python de larga duración en el VPS para este repo que necesite reiniciarse tras el `pull` (los dashboards son estáticos y el cron de conversión se relanza solo en su próxima ejecución programada, así que en el caso normal no debería requerirse ningún reinicio).
6. **Verificar manualmente** que los dashboards cargan correctamente desde `http://<host>:8081/dashboards/` y que `/data` sirve los JSON esperados.

No hay artefacto empaquetado, ni subida por SSH de un `.tar.gz`, ni backup automático como parte de este proceso: es un `git pull` directo sobre el checkout que nginx ya está sirviendo.

---

## Conversión batch de CSV (cron)

La generación de los JSON que consumen los dashboards en producción se hace con `scripts/generate-dashboards.sh`, pensado para ejecutarse por cron en el VPS (ver cabecera del propio script):

```bash
0 2 * * * /infocodes/project/release-dashboard-application/scripts/generate-dashboards.sh
```

Qué hace:

1. Recorre todos los `.csv` en `data/input/`.
2. Despacha cada fichero al conversor que corresponde según el nombre: si contiene `postmortem` usa `converters/cli/convert_postmortems.py`; en caso contrario, `converters/cli/convert_incidents.py`.
3. Escribe los JSON resultantes en `data/output/` y los reportes de error en `data/errors/`.
4. Regenera `data/output/index.json` con `converters/cli/build_index.py`.
5. Registra todo en `logs/dashboards-generation-YYYYMMDD.log` dentro del propio repo.

Este proceso es independiente del despliegue de código: puede llevar horas de desfase respecto al último `git pull`, y viceversa — desplegar código nuevo no dispara una conversión inmediata (hay que esperar a la siguiente ejecución del cron, o lanzar `scripts/generate-dashboards.sh` a mano).

Más detalle de instalación/crontab en [`scripts/README.md`](../scripts/README.md).

---

## Rollback (manual)

No existe script de rollback. Si un despliegue introduce un problema:

```bash
cd /infocodes/project/release-dashboard-application
git log --oneline -10          # localizar el commit anterior estable
git checkout <commit-anterior>  # o: git revert <commit-problemático> && git pull
```

Tras volver a un commit anterior (o revertir), repetir el paso de nginx (`nginx -t` + reload) si el cambio afectaba a `nginx.conf`. No hay backups automáticos de código ni mecanismo de restauración distinto a `git`.

Los datos (`data/output/*.json`) no se versionan en git (`data/` está en `.gitignore`), por lo que un rollback de código no revierte los datos ya convertidos; si hace falta revertir datos, habría que regenerarlos desde los CSV originales en `data/input/` con `scripts/generate-dashboards.sh` o con los conversores individuales.

---

## Checklist pre-deploy

- [ ] Cambios fusionados en `main` y, si aplica, promovidos a `production`.
- [ ] Tests pasando (`tests.yml`) y linting sin errores (`lint.yml`).
- [ ] Si el cambio afecta a `nginx.conf`: validado con `nginx -t` antes de recargar.
- [ ] Si el cambio afecta a los conversores (`converters/`): probado localmente con un CSV de ejemplo.
- [ ] Acceso SSH al VPS verificado.
- [ ] Identificado el commit actual en `production` en el VPS, por si hace falta volver a él.

## Verificación post-deploy

- [ ] `git log -1` en el VPS muestra el commit esperado en la rama `production`.
- [ ] El portal carga en `/dashboards/portal/`.
- [ ] Los dashboards de Incidencias Masivas y Postmortem muestran datos (vía `/data/index.json`).
- [ ] Si se recargó nginx: `/reportes-incidencias` y `/problemas` siguen respondiendo (no deberían verse afectados por este despliegue, pero comparten el mismo nginx).

---

## Referencias

- [`scripts/README.md`](../scripts/README.md) — instalación y crontab de `generate-dashboards.sh`.
- [`README.md`](../README.md) — arranque local con `serve_app.py`, estructura del proyecto.
- `nginx.conf` (raíz del repo, no versionado) — configuración real servida en el VPS.
