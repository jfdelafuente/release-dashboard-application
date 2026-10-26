/* ============================================================
   MASORANGE — Barra Superior Unificada (Portal Shell)
   ============================================================
   Fuente única y canónica de la navegación cruzada entre plataformas:
   - Portal (/dashboards/portal/)
   - Incidencias masivas (/dashboards/massive-incidents/)
   - Release (/dashboards/postmortem/)
   - KPIs Release (/dashboards/release-kpis/)
   - Reportes de Incidencias (/reportes-incidencias/index.html)
   - Gestión de Problemas (/problemas)
   ============================================================ */

(function () {
  var NAV_ITEMS = [
    { id: 'portal', label: 'Portal', href: '/dashboards/portal/' },
    { id: 'massive-incidents', label: 'Incidencias masivas', href: '/dashboards/massive-incidents/' },
    { id: 'postmortem', label: 'Release', href: '/dashboards/postmortem/' },
    { id: 'release-kpis', label: 'KPIs Release', href: '/dashboards/release-kpis/' },
    { id: 'reportes-incidencias', label: 'Reportes de Incidencias', href: '/dashboards/reportes-incidencias/' },
    { id: 'problemas', label: 'Gestión de Problemas', href: '/problemas' },
    { id: 'agents-catalog', label: 'Agentes IA', href: '/dashboards/agents-catalog/' }
  ];

  function render() {
    var root = document.getElementById('mo-topbar-root');
    if (!root) return;
    var active = root.dataset.active || '';

    var navLinks = NAV_ITEMS.map(function (item) {
      var isActive = item.id === active;
      var cls = isActive ? ' class="active" aria-current="page"' : '';
      return '<a href="' + item.href + '"' + cls + '>' + item.label + '</a>';
    }).join('');

    var logoSrc = root.dataset.logo || '/dashboards/assets/orange-logo.svg';

    root.innerHTML =
      '<div class="mo-topbar" role="banner">' +
        '<a href="/dashboards/portal/" class="mo-topbar-brand" aria-label="Ir al Portal de Fiabilidad">' +
          '<img src="' + logoSrc + '" onerror="if(this.src!=\'/dashboards/assets/orange-logo.svg\')this.src=\'/dashboards/assets/orange-logo.svg\'" alt="Orange">' +
        '</a>' +
        '<div class="mo-topbar-sep" aria-hidden="true"></div>' +
        '<span class="mo-topbar-dept">Customer &amp; Service Operations</span>' +
        '<nav class="mo-topbar-nav" aria-label="Navegación principal">' + navLinks + '</nav>' +
        '<div class="mo-topbar-right">' +
          '<div class="mo-status-badge" id="mo-api-status" title="Comprobando conexión con backend...">' +
            '<span class="mo-status-dot" id="mo-api-status-dot"></span>' +
            '<span class="mo-status-text" id="mo-api-status-text">API</span>' +
          '</div>' +
        '</div>' +
      '</div>';

    checkApiHealth();

    // Notificar y anclar Centro de Notificaciones de Incidencias si está disponible
    if (typeof window !== 'undefined' && window.IncidentNotifications && typeof window.IncidentNotifications.mountBell === 'function') {
      try {
        window.IncidentNotifications.mountBell();
      } catch (e) {
        console.warn('[MoTopbar] Error al anclar campana de notificaciones:', e);
      }
    }
    if (typeof document !== 'undefined') {
      document.dispatchEvent(new CustomEvent('mo-topbar-rendered'));
    }
  }

  function checkApiHealth() {
    var dot = document.getElementById('mo-api-status-dot');
    var text = document.getElementById('mo-api-status-text');
    var badge = document.getElementById('mo-api-status');
    if (!dot || !text) return;

    var controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
    var timer = setTimeout(function () {
      if (controller) controller.abort();
    }, 3500);

    fetch('/api/health', { signal: controller ? controller.signal : undefined })
      .then(function (r) {
        if (r.ok) return r.json();
        throw new Error('HTTP ' + r.status);
      })
      .then(function (data) {
        clearTimeout(timer);
        dot.className = 'mo-status-dot online';
        text.textContent = 'API OK';
        if (badge) badge.title = 'API Backend Operativa (' + (data.service || 'FastAPI') + ')';
      })
      .catch(function () {
        clearTimeout(timer);
        fetch('/healthz')
          .then(function (r) {
            if (r.ok) return r.json();
            throw new Error('HTTP ' + r.status);
          })
          .then(function (data) {
            dot.className = 'mo-status-dot online';
            text.textContent = 'API OK';
            if (badge) badge.title = 'API Backend Operativa';
          })
          .catch(function () {
            dot.className = 'mo-status-dot offline';
            text.textContent = 'API Offline';
            if (badge) badge.title = 'API Backend no accesible en puerto 8000';
          });
      });
  }

  // Carga automática del sistema central de feedback si no está presente
  if (typeof window !== 'undefined' && !window.Toast && !document.querySelector('script[src*="ui-feedback.js"]')) {
    var fbScript = document.createElement('script');
    fbScript.src = '/dashboards/assets/ui-feedback.js';
    fbScript.async = true;
    document.head.appendChild(fbScript);
  }

  // Carga automática de estilos y componente de notificaciones si no están presentes
  if (typeof window !== 'undefined') {
    if (!document.querySelector('link[href*="incident-notifications.css"]')) {
      var notifCss = document.createElement('link');
      notifCss.rel = 'stylesheet';
      notifCss.href = '/dashboards/assets/incident-notifications.css';
      document.head.appendChild(notifCss);
    }
    if (!window.IncidentNotifications && !document.querySelector('script[src*="incident-notifications.js"]')) {
      var notifScript = document.createElement('script');
      notifScript.src = '/dashboards/assets/incident-notifications.js';
      notifScript.defer = true;
      document.head.appendChild(notifScript);
    }
  }

  window.MoTopbar = { render: render, navItems: NAV_ITEMS, checkHealth: checkApiHealth };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', render);
  } else {
    render();
  }
})();
