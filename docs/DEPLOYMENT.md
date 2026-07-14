# Guía de Despliegue

Procedimiento real de despliegue de Release Dashboard Application. El despliegue es **manual**: no existe script de deploy, ni de rollback, ni de health-check, ni un workflow de GitHub Actions que despliegue automáticamente.

---

## Qué se despliega desde este repo

Este repositorio aporta **contenido estático** (dashboards HTML/CSS/JS) y **datos JSON**. Nginx los sirve directamente desde el checkout de la rama `production` en el VPS, sin build ni empaquetado:

| Ruta servida | Origen | Contenido |
|---|---|---|
| `/dashboards` | `dashboards/` del repo | Portal (`dashboards/portal/`), Incidencias Masivas, Postmortem/Release, KPIs Release |
| `/data` | `data/` del repo | JSONs generados por los conversores (`data/output/`) |

Lo que **no** se despliega desde este repo (corren aparte, en otros procesos/repos hermanos):

- **`/api`** → proxy a un backend FastAPI (`localhost:8000`), del repo hermano `cso-incident-masivas-report`.
- **`/reportes-incidencias`** → alias directo al checkout de `cso-incident-masivas-report/app`.
- **`/problemas`** → proxy a un backend Next.js (`localhost:3001`) gestionado con `pm2`, de un repo/backend de Gestión de Problemas.

Por tanto, desplegar este repo **no reinicia ni afecta** a esos otros servicios; son despliegues independientes que no están documentados aquí.

> `serve_app.py` (servidor HTTP con endpoint `POST /api/upload` para subir CSV desde el navegador) es una utilidad de **desarrollo local** (ver README.md, sección "Inicio Rápido"). En producción, `/api` lo gestiona el nginx del VPS apuntando al backend FastAPI del repo hermano, no a `serve_app.py`. **No confirmado**: si en producción existe alguna forma equivalente de subir un CSV desde el navegador para este repo, o si la única vía de entrada de datos en producción es el cron de conversión batch descrito más abajo.

---

## Arquitectura de despliegue (VPS)

Configuración real, ver `nginx.conf` en la raíz del repo (fichero local, no versionado — está en `.gitignore`, pero existe una copia igual en el VPS):

```nginx
server {
    listen 8081 default_server;
    server_name 10.132.68.85 infocodes.si.orange.es;

    location /dashboards {
        alias /infocodes/project/release-dashboard-application/dashboards;
        index index.html index.htm;
        try_files $uri $uri/ /index.html;
    }

    location /data {
        alias /infocodes/project/release-dashboard-application/data;
        autoindex off;
    }

    location /reportes-incidencias {
        alias /infocodes/project/cso-incident-masivas-report/app;
        index index.html index.htm;
        try_files $uri $uri/ /index.html;
    }

    location /problemas {
        proxy_pass http://gestion_problemas_backend;   # localhost:3001, vía pm2
        ...
    }

    location /api {
        proxy_pass http://fastapi_backend;              # localhost:8000
        ...
    }
}
```

Puntos clave:

- El checkout del repo en el VPS vive en `/infocodes/project/release-dashboard-application`. Nginx sirve `dashboards/` y `data/` **directamente desde ahí** vía `alias` — no hay una carpeta `static/` separada ni un paso de copiado/build.
- El puerto expuesto es **8081**, no 80/443 directamente (`server_name 10.132.68.85 infocodes.si.orange.es`).
- No hay entorno de "staging" con URL propia: solo existe esta configuración de producción.

---

## Requisitos previos

- Acceso SSH al VPS con el usuario que tiene permisos sobre `/infocodes/project/release-dashboard-application`.
- El checkout en el VPS debe estar en la rama `production` (rama existente en el repo, separada de `main`).
- Python instalado en el VPS (usado por los conversores CSV→JSON y por el cron de `generate-dashboards.sh`; ver `converters/requirements.txt`).

**No confirmado**: la versión exacta de Python requerida en el VPS, y si el entorno usa un virtualenv específico o el intérprete de sistema.

---

## Procedimiento de despliegue (manual)

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
4. **Si cambió `nginx.conf`**: copiar/aplicar los cambios a la configuración real de nginx en el VPS y recargar:
   ```bash
   sudo nginx -t          # validar sintaxis antes de recargar
   sudo systemctl reload nginx
   ```
   (o el comando equivalente según cómo esté gestionado nginx en ese servidor — **no confirmado** si es un servicio `systemd` estándar o un nginx compilado a medida bajo `/infocodes`).
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
