# Release Dashboards

Dashboards web interactivos para análisis y visualización de incidencias masivas y postmortems de release, con la identidad visual de MASORANGE.

## 📂 Estructura

```
dashboards/
├── index.html                           # Redirige a /dashboards/portal/
├── portal/
│   └── index.html                       # Portal principal (punto de entrada)
├── massive-incidents/
│   └── index.html                       # Dashboard de incidencias masivas
├── postmortem/
│   └── index.html                       # Dashboard de postmortem / release
├── release-kpis/                        # Dashboard de KPIs históricos de release
│   ├── index.html
│   ├── app.js
│   ├── releases-data.js                 # Dataset estático mantenido a mano
│   ├── colors_and_type.css              # Tipografía global propia de este dashboard
│   └── style.css
├── assets/                               # Compartido por TODOS los dashboards
│   ├── masorange-logo-positive.svg      # Logo (fondo oscuro)
│   ├── masorange-logo-negative.svg      # Logo (fondo claro)
│   ├── masorange-mark.svg               # Isotipo reducido
│   ├── tokens.css                       # Variables de diseño MASORANGE — fuente única de tokens
│   ├── topbar.css                       # Barra superior MASORANGE (usada por los 4 dashboards)
│   ├── topbar.js                        # Inyecta la barra superior con la pestaña activa marcada
│   └── shared.css                       # Resto del framework de los 3 dashboards "clásicos"
└── README.md                            # Este archivo
```

**Sin build step**: HTML, CSS y JavaScript servidos directos, sin bundler. **Todos los dashboards viven en su propia subcarpeta** con un `index.html` como punto de entrada, y usan URLs limpias (`/dashboards/massive-incidents/` en vez de un archivo `.html` suelto). Los 3 dashboards "clásicos" (portal, incidencias masivas, postmortem) tienen su CSS/JS específico en línea en el propio `index.html`, y enlazan `/dashboards/assets/shared.css` para lo común (pantalla de subida, tarjetas KPI, tabla, badges de estado) — `shared.css` importa a su vez `topbar.css` y `tokens.css`. `release-kpis/` tiene bastante más CSS/JS propio y un modelo de datos diferente (ver más abajo), así que solo enlaza `assets/topbar.css` y `assets/tokens.css` directamente, sin cargar el resto del framework (no tiene pantalla de subida ni tabla).

**Rutas root-absolutas**: todas las referencias a datos (`/data/output/...`) y a assets compartidos (`/dashboards/assets/...`) usan rutas absolutas desde la raíz del sitio, no relativas. Esto es lo que hace posible mover cualquier dashboard de carpeta sin romper nada — la ruta no depende de la profundidad del archivo que la usa. Funciona igual en local (`serve_app.py`, `python -m http.server` desde la raíz del repo) y en producción (nginx, donde `/dashboards` y `/data` son alias hermanos del mismo origen).

**Barra superior compartida vía componente JS**: en vez de duplicar el HTML de la navegación en cada página, cada dashboard incluye un `<div id="mo-topbar-root" data-active="...">` vacío y carga `assets/topbar.js`, que rellena ese contenedor con el markup `.mo-topbar` y marca la pestaña activa según el atributo `data-active`. Así la lista de destinos vive en un único sitio (`NAV_ITEMS` en `topbar.js`).

## 🚀 Características

- 🧭 **Portal**: punto de acceso único, con tarjetas clicables a cada dashboard (incluye enlaces a Reportes de Incidencias y Gestión de Problemas, que son apps de los repos hermanos, no de este repositorio)
- 📈 **Incidencias Masivas**: filtro de tiempo global, KPIs con tendencias, gráficas temporales (entradas/solucionadas/backlog), incidencias abiertas por estado, tabla filtrable y ordenable con enlaces a Remedy
- 🔍 **Postmortem / Release**: un dashboard por release (identificado por su nombre), con análisis por despliegue (PAP/MESA), KPIs de resolución, distribución por sistema y por estado, tabla filtrable y ordenable — se accede desde la tabla de KPIs de Release, no como vista combinada
- 🎯 **KPIs de Release (Histórico)**: serie histórica de KPIs de release (volumen y % de resolución PaP/1ª semana) con indicador de umbral del 75%, sobre un dataset estático mantenido a mano
- 📤 **Subida de CSV desde el navegador**: arrastra o selecciona un CSV y se convierte automáticamente (requiere `serve_app.py`, ver más abajo)
- 🎨 **Identidad MASORANGE**: barra superior negra con logo, acento naranja `#FF7900` sobre neutros cálidos, tipografía Inter (interfaz) + IBM Plex Mono (cifras/datos)
- 📱 **Responsive**: funciona en desktop, tablet y móvil
- ⚡ **Sin dependencias propias**: HTML5, CSS3 y JavaScript vanilla (Plotly.js vía CDN)

## 📦 Prerequisitos

### Datos

Los dashboards consumen JSON de `/data/output/` (ruta root-absoluta), generados por los [converters](../converters/README.md) — automáticamente al subir un CSV desde el navegador, o manualmente con los scripts de `converters/scripts/bin/`.

**Formato esperado:**
- `*-massive.json`: datos de incidencias masivas
- `*-postmortem.json`: datos de postmortem (opcional)
- `index.json`: índice de datasets disponibles (auto-generado por `build_index.py`)

Ver [Contrato JSON](../converters/docs/API.md) para la estructura detallada.

### Navegador

- Chrome/Edge/Firefox/Safari moderno (ES6+)
- Conexión a internet (Plotly.js y Google Fonts vía CDN)

## 🎯 Uso

### Con subida de CSV desde el navegador (recomendado)

Desde la **raíz del repositorio** (no desde `dashboards/`):

```bash
python serve_app.py
# Abre: http://localhost:8000/dashboards/portal/
```

`serve_app.py` sirve los archivos estáticos **y** el endpoint `POST /api/upload`, que guarda el CSV en `data/input/`, ejecuta el conversor correspondiente y deja el JSON listo en `data/output/`.

### Solo lectura (datos ya generados, sin subida desde el navegador)

Si solo quieres ver datos que ya están en `data/output/`, sirve sin más **desde la raíz del repositorio** (las rutas root-absolutas necesitan que el servidor arranque ahí, no dentro de `dashboards/`):

```bash
# Con Live Server (VSCode): clic derecho en dashboards/index.html → "Open with Live Server"
# o con Python, desde la raíz del repo:
python -m http.server 8000
```

> ⚠️ Ninguna de estas dos opciones implementa `POST`: si intentas subir un
> CSV desde el navegador con alguna de ellas, fallará con "Failed to
> fetch". Para subir CSVs, usa siempre `serve_app.py`.

### Producción (Nginx)

En producción, `dashboards/` se sirve como alias estático y `/api` se enruta al backend FastAPI que ejecuta los conversores (ver `nginx.conf` en la raíz del repo para la configuración completa, incluida la de los paneles hermanos `/reportes-incidencias` y `/problemas`).

## 📊 Dashboards Disponibles

### Portal (`portal/index.html`)

**Punto de entrada.** Tarjetas clicables a cada dashboard, con contador de registros e índice de datasets cargados (`/data/output/index.json`).

### Incidencias Masivas (`massive-incidents/index.html`)

**Análisis temporal de incidencias masivas.**

- Filtro de tiempo global (7d, 15d, 30d, 90d, 6m, año, año en curso, todo)
- KPI cards con tendencias (7d/15d/30d, color-coded)
- Gráficas temporales: entradas/solucionadas/backlog, incidencias abiertas por estado
- Filtros de tabla (Estado, Grupo asignado, Urgencia)
- Tabla ordenable con enlaces a Remedy

**Entrada:** JSON con estructura de incidencias masivas, p. ej.:
```json
{
  "ID de incidencia": "INC000003884945",
  "Descripción": "...",
  "Estatus": "Cerrado",
  "Fecha de envío": "02/01/2026 8:14 a",
  "Grupo asignado": "...",
  "Urgencia": "Baja",
  "Impacto": "Masiva"
}
```

### Postmortem / Release (`postmortem/index.html`)

**Un dashboard por release, no una vista combinada.** Se accede mediante `/dashboards/postmortem/?release=<nombre>` — el nombre coincide con el que aparece en la columna "RELEASE" de la tabla de `dashboards/release-kpis/`, cuyas filas enlazan directamente aquí. No existe ya un dashboard con todas las releases mezcladas.

- KPIs: total, % cerradas, % resueltas PaP, % resueltas Mesa (de la release cargada)
- Gráfica temporal de entradas/resoluciones/backlog
- Gráfica de evolución de incidencias PAP en intervalos de 30 minutos (usa la hora de "Fecha de envío"/"Fecha de última resolución", preservada por el conversor junto con la fecha)
- Distribución por sistema y por estado
- Filtros de tabla (Estado, Despliegue, Urgencia, Sistema) y tabla ordenable
- **Tres estados según el parámetro `release`**: sin parámetro → mensaje pidiendo acceder desde KPIs de Release; con parámetro y datos ya cargados → dashboard normal con el nombre de la release en la cabecera; con parámetro pero sin datos todavía → pantalla de subida de CSV con el nombre de la release ya asociado (no hay que escribirlo a mano)
- El nombre de release se asocia al subir el CSV: `data/output/index.json` guarda `release_name` por archivo (leído de `_metadata.release_name`), y el JS de este dashboard busca ahí el archivo que corresponde al `?release=` de la URL

### KPIs Release — Histórico (`release-kpis/index.html`)

**Vista histórica de KPIs de release (volumen y % de resolución PaP/1ª semana), con indicador de umbral del 75%.**

- ⚠️ **No usa la tubería CSV/converters.** A diferencia de los otros 3, consume un dataset estático mantenido a mano en `releases-data.js` (48 releases desde 2020 en adelante) — no hace `fetch` de `data/output/`, ni se actualiza subiendo un CSV. Para añadir un release nuevo, edita `releases-data.js` directamente.
- Filtros por año y por número de gráficas a mostrar
- Panel de detalle por release con incidencias asociadas
- El nombre de cada release en la columna "RELEASE" de la tabla enlaza a `/dashboards/postmortem/?release=<nombre>` — es el único punto de acceso a los dashboards de postmortem por release (ver más abajo)
- Su barra superior se inyecta igual que en los otros 3 (vía `assets/topbar.js`), pero como este dashboard reconstruye todo su DOM en cada `render()` propio (`app.js`), llama explícitamente a `window.MoTopbar.render()` después de cada re-render, en vez de depender solo del evento `DOMContentLoaded`.

## 🎨 Convención para dashboards

- **Todo dashboard vive en su propia subcarpeta** (`portal/`, `massive-incidents/`, `postmortem/`, `release-kpis/`) con un `index.html` como punto de entrada, para tener una URL limpia (`/dashboards/<nombre>/`).
- Usa siempre **rutas root-absolutas** para datos y assets compartidos (`/data/output/...`, `/dashboards/assets/...`), nunca relativas — así el dashboard puede moverse de carpeta sin que se rompa nada.
- Enlaza siempre `assets/topbar.css` para los estilos de la barra superior, e incluye `assets/topbar.js` junto con un `<div id="mo-topbar-root" data-active="tu-id"></div>` vacío donde debe ir — no dupliques el HTML de la navegación a mano. Si además necesitas el resto del framework compartido (pantalla de subida de CSV, tarjetas KPI, tabla, badges de estado), enlaza `assets/shared.css` en su lugar — ya incluye `topbar.css` y `tokens.css` internamente vía `@import`.
- Usa las variables de `assets/tokens.css` para colores, tipografía, espaciado y sombras en vez de hardcodear valores nuevos — es la única fuente de tokens de diseño compartida entre los 4 dashboards.
- No dupliques los SVG de marca: referencia siempre `/dashboards/assets/masorange-*.svg`, nunca una copia local.
- Añade el destino del dashboard nuevo al array `NAV_ITEMS` de `assets/topbar.js` (una sola vez, no hace falta tocar cada página) y a las tarjetas del portal.

## 🐛 Debugging

### Ver logs del navegador

1. Abrir DevTools (F12) → pestaña "Console"
2. Los dashboards registran ahí los fallos de carga de datos (p. ej. si `index.json` no existe todavía porque no se ha subido ningún CSV)

### Verificar datos cargados

En la consola del navegador:
```javascript
console.log(allIncidents);      // Todos los datos cargados
console.log(filteredIncidents); // Datos después de aplicar filtros
```

## 🔐 Seguridad

- Sin autenticación propia (asume acceso controlado en red/VPN)
- Sin llamadas a APIs externas salvo CDN (Plotly.js, Google Fonts)
- Los datos se procesan en el navegador; la subida de CSV pasa por el backend, que valida la extensión antes de guardar

## 🤝 Desarrollo

- **HTML5 + CSS3 + JavaScript (ES6+)**, sin framework ni build step
- **Plotly.js** para las gráficas interactivas
- **Google Fonts**: Inter (interfaz) e IBM Plex Mono (cifras)

Para añadir o modificar un dashboard, edita directamente los archivos de su subcarpeta y pruébalo con `python serve_app.py` desde la raíz del repo.

## 📞 Soporte

Para problemas:
1. Verificar que el JSON en `data/output/` cumple el formato esperado (ver [converters/docs/API.md](../converters/docs/API.md))
2. Revisar la consola del navegador (DevTools)
3. Si la subida de CSV falla con "Failed to fetch", confirmar que el servidor es `serve_app.py` y no `python -m http.server` / Live Server
4. Consultar [docs/TROUBLESHOOTING.md](../docs/TROUBLESHOOTING.md)

---

**Última actualización**: 2026-07-14
