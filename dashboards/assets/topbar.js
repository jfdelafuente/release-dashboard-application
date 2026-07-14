/* ============================================================
   Release Dashboard — barra superior MASORANGE (componente JS)
   ============================================================
   Fuente única de la navegación cruzada entre los 4 dashboards.
   Cada página incluye un <div id="mo-topbar-root" data-active="...">
   vacío; este script lo rellena con el markup .mo-topbar (estilos
   en assets/topbar.css) marcando la pestaña activa.

   Para páginas estáticas (portal, massive-incidents, postmortem):
   basta con incluir este script; se renderiza en DOMContentLoaded.

   Para release-kpis, que reconstruye su DOM en cada render() propio
   (ver app.js), este script se carga como <script> normal (sin
   defer) ANTES de app.js, y app.js llama a window.MoTopbar.render()
   explícitamente después de cada re-render suyo.
   ============================================================ */

(function () {
  var NAV_ITEMS = [
    { id: 'portal', label: 'Portal', href: '/dashboards/portal/' },
    { id: 'massive-incidents', label: 'Incidencias masivas', href: '/dashboards/massive-incidents/' },
    { id: 'postmortem', label: 'Release', href: '/dashboards/postmortem/' },
    { id: 'release-kpis', label: 'KPIs Release', href: '/dashboards/release-kpis/' },
    { id: 'reportes-incidencias', label: 'Reportes de Incidencias', href: '/reportes-incidencias/index.html' },
    { id: 'problemas', label: 'Gestión de Problemas', href: '/problemas' }
  ];

  function render() {
    var root = document.getElementById('mo-topbar-root');
    if (!root) return;
    var active = root.dataset.active;
    var navLinks = NAV_ITEMS.map(function (item) {
      var cls = item.id === active ? ' class="active"' : '';
      return '<a href="' + item.href + '"' + cls + '>' + item.label + '</a>';
    }).join('');
    root.innerHTML =
      '<div class="mo-topbar">' +
        '<img src="/dashboards/assets/masorange-logo-positive.svg" alt="MASORANGE">' +
        '<div class="mo-topbar-sep"></div>' +
        '<span class="mo-topbar-dept">Customer &amp; Service Operations</span>' +
        '<nav class="mo-topbar-nav">' + navLinks + '</nav>' +
      '</div>';
  }

  window.MoTopbar = { render: render };
  document.addEventListener('DOMContentLoaded', render);
})();
