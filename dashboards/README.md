# Release Dashboards

Dashboards web interactivos para análisis y visualización de incidencias masivas y postmortems.

## 🚀 Características

- 📊 **Dashboard Hub**: Punto de acceso unificado con KPIs en tiempo real
- 📈 **Massive Incidents Dashboard**: Análisis temporal con tendencias, filtros y backlog
- 🔍 **Postmortem Dashboard**: Análisis detallado por despliegues (PAP/MESA)
- ⚡ **Sin dependencias**: Puro HTML5, CSS3 y JavaScript (Plotly.js vía CDN)
- 📱 **Responsive**: Funciona en desktop, tablet y móvil
- 🔄 **Auto-carga**: Dashboard Hub carga datos automáticamente desde `index.json`

## 📦 Prerequisitos

### Datos

Los dashboards requieren archivos JSON en `../data/output/` generados por los [converters](../converters/README.md).

**Formato esperado:**
- `*-massive.json`: Datos de incidencias masivas
- `*-postmortem.json`: Datos de postmortem (opcional)
- `index.json`: Índice de datasets disponibles (auto-generado)

Ver [Contrato JSON](../converters/docs/API.md) para estructura detallada.

### Navegador

- Chrome/Edge/Firefox/Safari moderno (soporta ES6+)
- Conexión a internet (para Plotly.js y Google Fonts vía CDN)

## 🎯 Uso

### Opción A: Live Server (VSCode) - Recomendado

1. Instalar extensión "Live Server"
2. Click derecho en `index.html`
3. Seleccionar "Open with Live Server"
4. Abre automáticamente en `http://localhost:5500/`

### Opción B: Python HTTP Server

```bash
# Desde el directorio dashboards
python -m http.server 8000

# Abre en navegador: http://localhost:8000/
```

### Opción C: Nginx (Producción)

```nginx
server {
    listen 80;
    server_name dashboards.example.com;
    root /var/www/dashboards;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|woff|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

## 📊 Dashboards Disponibles

### Dashboard Hub (`index.html`)

**Punto de entrada principal** - Carga automáticamente los datos.

**Características:**
- KPIs resumidas (total, pendientes, tendencias)
- Auto-detección de datasets disponibles
- Navegación a dashboards especializados
- Breadcrumbs para volver

**Flujo:**
1. Carga `../data/output/index.json`
2. Extrae KPIs del `_metadata`
3. Muestra links a dashboards con datos disponibles

### Massive Incidents Dashboard (`src/massive-incidents-dashboard.html`)

**Análisis temporal de incidencias masivas.**

**Características:**
- Filtro de tiempo global (7d, 15d, 30d, 90d, 6m, año, custom)
- KPI cards dinámicas con tendencias (color-coded)
- Gráficas temporales:
  - Evolución diaria de entradas/solucionadas
  - Backlog acumulado
  - Incidencias abiertas por estado
- Filtros de tabla (Estado, Sistema, Urgencia)
- Tabla ordenable con links a Remedy
- Debug table con cálculos diarios

**Entrada:** JSON con estructura masivas
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

### Postmortem Dashboard (`src/postmortem-dashboard.html`)

**Análisis detallado de postmortems.**

**Características:**
- Análisis por despliegue (PAP/MESA)
- KPI desglosadas por tipo de despliegue
- Visualizaciones por estado de resolución
- Filtros avanzados
- Detalles de cada postmortem

**Entrada:** JSON con estructura postmortem

## 🎨 Personalización

### Cambiar colores

En `src/assets/css/dashboard-hub.css`:

```css
/* Colores primarios */
:root {
  --primary-color: #f97316;      /* Naranja principal */
  --secondary-color: #fb923c;    /* Naranja claro */
  --dark-color: #c2410c;         /* Naranja oscuro */
  --success-color: #22c55e;      /* Verde (tendencia positiva) */
  --danger-color: #ef4444;       /* Rojo (tendencia negativa) */
  --neutral-color: #6b7280;      /* Gris (estable) */
}
```

### Cambiar KPIs mostradas

En `src/dashboard-hub.html` y `src/massive-incidents-dashboard.html`:
- Buscar sección "KPI Cards"
- Modificar campos extraídos del `_metadata.kpis`
- Ajustar cálculos según necesidad

### Agregar nuevas gráficas

1. Copiar estructura HTML de gráfica existente
2. Crear función JavaScript en `assets/js/dashboard-hub.js`
3. Usar Plotly.newPlot() para renderizar
4. Conectar con datos filtrados

Ejemplo:
```javascript
function createMyChart(filteredData) {
  const trace = {
    x: filteredData.map(r => r['Fecha de envío']),
    y: filteredData.map(r => r['Impacto']),
    type: 'scatter'
  };
  Plotly.newPlot('myChartDiv', [trace]);
}
```

## 📱 Responsividad

Los dashboards usan CSS Grid y Flexbox. Para optimizar para móvil:

```css
@media (max-width: 768px) {
  .kpi-container {
    grid-template-columns: 1fr; /* Una columna en móvil */
  }

  .chart-container {
    height: 300px; /* Reducir altura */
  }
}
```

## 🔌 Integración con Otros Sistemas

Los dashboards pueden consumir datos de **cualquier fuente** que genere JSON compatible:

```javascript
// Ejemplo: Cargar desde API externa
fetch('https://api.example.com/incidencias')
  .then(r => r.json())
  .then(data => {
    // Asegurar que cumple formato esperado
    allIncidents = data.data || data;
    renderDashboard();
  });
```

No es necesario usar los converters de este repositorio.

## 🚀 Despliegue

### Staging

```bash
./scripts/deploy/deploy.sh staging
```

### Production

```bash
./scripts/deploy/deploy.sh production
```

Ver [DEPLOYMENT.md](docs/DEPLOYMENT.md) para configuración detallada.

## 🐛 Debugging

### Ver logs del navegador

1. Abrir DevTools (F12)
2. Tab "Console"
3. Buscar mensajes de error

### Verificar datos cargados

En console:
```javascript
console.log(allIncidents);      // Todos los datos
console.log(filteredIncidents); // Datos después de filtros
console.log(globalBacklogData); // Datos de backlog por fecha
```

### Probar con datos de ejemplo

1. Crear archivo JSON de prueba en `../data/output/test.json`
2. Actualizar `index.json` manualmente
3. Recargar dashboard

## 📊 Estructura de Archivos

```
dashboards/
├── src/
│   ├── dashboard-hub.html              # Punto de entrada principal
│   ├── massive-incidents-dashboard.html # Dashboard masivas
│   ├── postmortem-dashboard.html       # Dashboard postmortems
│   └── assets/
│       ├── css/dashboard-hub.css       # Estilos globales
│       └── js/dashboard-hub.js         # Lógica Dashboard Hub
├── scripts/deploy/                     # Scripts de despliegue
├── specs/002-dashboard-hub/            # Especificación
├── docs/                               # Documentación
└── index.html                          # Redirect a Dashboard Hub
```

## 📈 Performance

- Gráficas actualizadas en <500ms para 1000 registros
- Memory footprint: <50MB con 10K registros
- CDN caching para assets (Plotly.js, Google Fonts)

## 🔐 Seguridad

- Sin autenticación requerida (asume acceso controlado en red)
- Sin llamadas a APIs externas (excepto CDN)
- Datos procesados localmente en navegador
- XSS protection a través de sanitización de strings

## 🤝 Desarrollo

### Stack

- **HTML5**: Estructura semántica
- **CSS3**: Flexbox, Grid, Media queries
- **JavaScript (ES6+)**: Manipulación DOM, filtrado, cálculos
- **Plotly.js**: Gráficas interactivas
- **Google Fonts**: Tipografía (Poppins)

### Agregar nueva funcionalidad

1. Crear rama: `git checkout -b feature/nuevo-dashboard`
2. Editar archivos en `src/`
3. Probar localmente con `python -m http.server 8000`
4. Commit y push
5. CI/CD desplegará automáticamente

## 📚 Referencias

- [Dashboard Hub Spec](specs/002-dashboard-hub/spec.md)
- [Plotly.js Docs](https://plotly.com/javascript/)
- [MDN Web Docs](https://developer.mozilla.org/)

## 📞 Soporte

Para problemas:
1. Verificar que JSON de entrada cumple el formato esperado
2. Revisar logs del navegador (DevTools)
3. Consultar documentación en `docs/`
4. Verificar que converters generaron datos correctamente

## 📝 Licencia

Parte del proyecto Release Dashboard Application.

---

**Última actualización**: 2026-06-01
