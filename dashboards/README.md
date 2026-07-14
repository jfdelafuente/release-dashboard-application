# Release Dashboards

Dashboards web interactivos para análisis y visualización de incidencias masivas y postmortems de release, con la identidad visual de MASORANGE.

## 📂 Estructura

```
dashboards/
├── index.html                           # Redirige a dashboard-portal.html
├── dashboard-portal.html                # Portal principal (punto de entrada)
├── massive-incidents-dashboard.html     # Dashboard de incidencias masivas
├── postmortem-dashboard.html            # Dashboard de postmortem / release
├── release-kpis-dashboard/              # Dashboard de KPIs históricos de release
│   ├── index.html
│   ├── app.js
│   ├── releases-data.js                 # Dataset estático mantenido a mano
│   ├── colors_and_type.css              # Tokens de diseño propios de este dashboard
│   └── style.css
├── assets/                              # Compartido por TODOS los dashboards
│   ├── masorange-logo-positive.svg      # Logo (fondo oscuro)
│   ├── masorange-logo-negative.svg      # Logo (fondo claro)
│   ├── masorange-mark.svg               # Isotipo reducido
│   ├── topbar.css                       # Barra superior MASORANGE (usada por los 4 dashboards)
│   └── shared.css                       # Resto del framework de los 3 dashboards "clásicos"
└── README.md                            # Este archivo
```

**Sin build step**: HTML, CSS y JavaScript servidos directos, sin bundler. Los 3 dashboards "clásicos" (portal, incidencias masivas, postmortem) tienen su CSS/JS específico en línea en el propio `.html`, y enlazan `assets/shared.css` para lo común (barra superior, pantalla de subida, tarjetas KPI, tabla, badges de estado). `release-kpis-dashboard/` sigue un patrón distinto — archivos separados en su propia carpeta — porque tiene bastante más CSS/JS propio y un modelo de datos diferente (ver más abajo); solo enlaza `assets/topbar.css` de lo compartido, ya que no usa el resto del framework (no tiene pantalla de subida ni tabla con badges de estado).

## 🚀 Características

- 🧭 **Portal**: punto de acceso único, con tarjetas clicables a cada dashboard (incluye enlaces a Reportes de Incidencias y Gestión de Problemas, que son apps de los repos hermanos, no de este repositorio)
- 📈 **Incidencias Masivas**: filtro de tiempo global, KPIs con tendencias, gráficas temporales (entradas/solucionadas/backlog), incidencias abiertas por estado, tabla filtrable y ordenable con enlaces a Remedy
- 🔍 **Postmortem / Release**: análisis por despliegue (PAP/MESA), KPIs de resolución, distribución por sistema y por estado, tabla filtrable y ordenable
- 📤 **Subida de CSV desde el navegador**: arrastra o selecciona un CSV y se convierte automáticamente (requiere `serve_app.py`, ver más abajo)
- 🎨 **Identidad MASORANGE**: barra superior negra con logo, acento naranja `#FF7900` sobre neutros cálidos, tipografía Inter (interfaz) + IBM Plex Mono (cifras/datos)
- 📱 **Responsive**: funciona en desktop, tablet y móvil
- ⚡ **Sin dependencias propias**: HTML5, CSS3 y JavaScript vanilla (Plotly.js vía CDN)

## 📦 Prerequisitos

### Datos

Los dashboards consumen JSON de `../data/output/`, generados por los [converters](../converters/README.md) — automáticamente al subir un CSV desde el navegador, o manualmente con los scripts de `converters/scripts/bin/`.

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
# Abre: http://localhost:8000/dashboards/dashboard-portal.html
```

`serve_app.py` sirve los archivos estáticos **y** el endpoint `POST /api/upload`, que guarda el CSV en `data/input/`, ejecuta el conversor correspondiente y deja el JSON listo en `data/output/`.

### Solo lectura (datos ya generados, sin subida desde el navegador)

Si solo quieres ver datos que ya están en `data/output/`, sirve sin más:

```bash
# Con Live Server (VSCode): clic derecho en dashboard-portal.html → "Open with Live Server"
# o con Python, desde la raíz del repo:
python -m http.server 8000
```

> ⚠️ Ninguna de estas dos opciones implementa `POST`: si intentas subir un
> CSV desde el navegador con alguna de ellas, fallará con "Failed to
> fetch". Para subir CSVs, usa siempre `serve_app.py`.

### Producción (Nginx)

En producción, `dashboards/` se sirve como alias estático y `/api` se enruta al backend FastAPI que ejecuta los conversores (ver `nginx.conf` en la raíz del repo para la configuración completa, incluida la de los paneles hermanos `/reportes-incidencias` y `/problemas`).

## 📊 Dashboards Disponibles

### Portal (`dashboard-portal.html`)

**Punto de entrada.** Tarjetas clicables a cada dashboard, con contador de registros e índice de datasets cargados (`../data/output/index.json`).

### Incidencias Masivas (`massive-incidents-dashboard.html`)

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

### Postmortem / Release (`postmortem-dashboard.html`)

**Análisis detallado de postmortems por despliegue.**

- KPIs: total, % cerradas, % resueltas PaP, % resueltas Mesa
- Gráfica temporal de entradas/resoluciones/backlog
- Distribución por sistema y por estado
- Filtros de tabla (Estado, Despliegue, Impacto) y tabla ordenable

### KPIs Release — Histórico (`release-kpis-dashboard/index.html`)

**Vista histórica de KPIs de release (volumen y % de resolución PaP/1ª semana), con indicador de umbral del 75%.**

- ⚠️ **No usa la tubería CSV/converters.** A diferencia de los otros 3, consume un dataset estático mantenido a mano en `releases-data.js` (48 releases desde 2020 en adelante) — no hace `fetch` de `data/output/`, ni se actualiza subiendo un CSV. Para añadir un release nuevo, edita `releases-data.js` directamente.
- Filtros por año y por número de gráficas a mostrar
- Panel de detalle por release con incidencias asociadas

## 🎨 Convención para futuros dashboards

- **Un dashboard nuevo con CSS/JS propio sustancial** (como `release-kpis-dashboard`) va en su propia subcarpeta con su propio `index.html`, en vez de sumar otro archivo `.html` suelto en la raíz de `dashboards/`.
- Enlaza siempre `assets/topbar.css` para la barra superior (así se mantiene la navegación cruzada entre todos los dashboards). Si además necesitas el resto del framework compartido (pantalla de subida de CSV, tarjetas KPI, tabla, badges de estado), enlaza `assets/shared.css` en su lugar — ya incluye `topbar.css` internamente vía `@import`.
- No dupliques los SVG de marca: referencia siempre `assets/masorange-*.svg`, nunca una copia local.
- Los 3 dashboards "clásicos" (portal, incidencias masivas, postmortem) se quedan como archivos sueltos por continuidad histórica — no es la norma a replicar para dashboards nuevos.
- Añade el enlace del dashboard nuevo a la `.mo-topbar-nav` de **todas** las páginas existentes (incluida la propia, marcando su pestaña como `active`) y a las tarjetas del portal.

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

Para añadir o modificar un dashboard, edita directamente el `.html` correspondiente (estilos y lógica viven en el mismo archivo) y pruébalo con `python serve_app.py` desde la raíz del repo.

## 📞 Soporte

Para problemas:
1. Verificar que el JSON en `data/output/` cumple el formato esperado (ver [converters/docs/API.md](../converters/docs/API.md))
2. Revisar la consola del navegador (DevTools)
3. Si la subida de CSV falla con "Failed to fetch", confirmar que el servidor es `serve_app.py` y no `python -m http.server` / Live Server
4. Consultar [docs/TROUBLESHOOTING.md](../docs/TROUBLESHOOTING.md)

---

**Última actualización**: 2026-07-14
