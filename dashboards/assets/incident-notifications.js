/**
 * ============================================================
 * Centro de Notificaciones de Incidencias de Alta Prioridad
 * Orange - Customer & Service Operations
 * ============================================================
 * Gestión de alertas críticas P1/P2, discrepancias ITIL y
 * redacción ejecutiva para comités de dirección (incident-reporter).
 */

(function () {
  'use strict';

  const STORAGE_KEY = 'hp_incident_notifications_state_v1';
  const DATA_URL = '/data/output/high_priority_notifications.json';

  // ============================================================
  // 1. Gestor de Persistencia de Estados en Cliente (US4)
  // ============================================================
  const StateManager = {
    getAll() {
      try {
        const raw = localStorage.getItem(STORAGE_KEY);
        return raw ? JSON.parse(raw) : {};
      } catch (e) {
        console.warn('[IncidentNotifications] Error leyendo localStorage:', e);
        return {};
      }
    },

    getStatus(id) {
      const all = this.getAll();
      return (all[id] && all[id].status) || 'pendiente';
    },

    setStatus(id, status) {
      const all = this.getAll();
      all[id] = {
        status: status,
        updated_at: new Date().toISOString()
      };
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(all));
      } catch (e) {
        console.warn('[IncidentNotifications] Error escribiendo localStorage:', e);
      }
    }
  };

  // ============================================================
  // 2. Componente Principal
  // ============================================================
  class IncidentNotificationsManager {
    constructor() {
      this.catalog = null;
      this.items = [];
      this.activeFilterPriority = 'all'; // 'all', 'p1', 'p2', 'discrepancy'
      this.activeFilterState = 'pending'; // 'pending', 'all', 'managed'
      this.activeExecPhases = new Map(); // id -> 'apertura' | 'seguimiento' | 'cierre'
      this.openExecCards = new Set(); // ids con panel ejecutivo abierto

      this.init();
    }

    async init() {
      await this.loadData();
      this.mountBell();
      this.renderDrawer();
      this.updateBadge();
      this.bindGlobalKeys();
      this.startPolling();
    }

    startPolling() {
      // Polling periódico silencioso cada 2 minutos (120.000 ms)
      this.pollInterval = setInterval(async () => {
        if (document.hidden) return;
        await this.loadData();
        this.updateBadge();
        const drawer = document.getElementById('hp-drawer');
        if (drawer && drawer.classList.contains('active')) {
          this.renderCards();
        }
      }, 120000);

      // Refresco inmediato al reactivar o volver el foco a la pestaña
      document.addEventListener('visibilitychange', async () => {
        if (!document.hidden) {
          await this.loadData();
          this.updateBadge();
          const drawer = document.getElementById('hp-drawer');
          if (drawer && drawer.classList.contains('active')) {
            this.renderCards();
          }
        }
      });
    }

    async loadData() {
      try {
        const res = await fetch(DATA_URL, { cache: 'no-store' });
        if (!res.ok) {
          console.info('[IncidentNotifications] No se encontró el catálogo generado en ' + DATA_URL);
          return;
        }
        this.catalog = await res.json();
        this.items = Array.isArray(this.catalog.data) ? this.catalog.data : [];
      } catch (err) {
        console.info('[IncidentNotifications] Catálogo aún no disponible o fuera de línea:', err.message);
      }
    }

    // Montar la campana en el header o en la barra superior
    mountBell() {
      const topbarRight = document.querySelector('.mo-topbar-right');
      const existing = document.getElementById('hp-notifications-bell-btn');

      // Si ya está correctamente anclado dentro de .mo-topbar-right, salir
      if (topbarRight && existing && existing.parentElement === topbarRight) {
        return;
      }

      if (existing) {
        existing.remove();
      }

      const btn = document.createElement('button');
      btn.id = 'hp-notifications-bell-btn';
      btn.className = 'hp-bell-btn';
      btn.type = 'button';
      btn.setAttribute('aria-label', 'Centro de notificaciones de alta prioridad');
      btn.title = 'Incidencias de Alta Prioridad (P1 / P2)';
      btn.innerHTML = `
        <svg class="hp-bell-icon" viewBox="0 0 24 24">
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
          <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
        </svg>
        <span class="hp-bell-badge" id="hp-bell-badge" style="display: none;">0</span>
      `;

      btn.addEventListener('click', () => this.open());

      if (topbarRight) {
        topbarRight.insertBefore(btn, topbarRight.firstChild);
        return;
      }

      // Si no, intentar en la fila de controles del dashboard
      const controls = document.querySelector('.controls-row');
      if (controls) {
        const wrapper = document.createElement('div');
        wrapper.id = 'hp-controls-wrapper';
        wrapper.style.display = 'flex';
        wrapper.style.alignItems = 'center';
        wrapper.appendChild(btn);
        controls.appendChild(wrapper);
      } else {
        // Fallback flotante en esquina superior derecha
        btn.style.position = 'fixed';
        btn.style.top = '16px';
        btn.style.right = '24px';
        btn.style.zIndex = '999';
        document.body.appendChild(btn);
      }

      // Reintentar anclar en la topbar tras un breve retraso por si se carga después
      setTimeout(() => {
        const tr = document.querySelector('.mo-topbar-right');
        const b = document.getElementById('hp-notifications-bell-btn');
        if (tr && b && b.parentElement !== tr) {
          const wrapper = document.getElementById('hp-controls-wrapper');
          if (wrapper) wrapper.remove();
          b.style.position = '';
          b.style.top = '';
          b.style.right = '';
          b.style.zIndex = '';
          tr.insertBefore(b, tr.firstChild);
        }
      }, 300);
    }

    renderDrawer() {
      if (document.getElementById('hp-drawer-backdrop')) return;

      const backdrop = document.createElement('div');
      backdrop.id = 'hp-drawer-backdrop';
      backdrop.className = 'hp-drawer-backdrop';
      backdrop.addEventListener('click', () => this.close());

      const drawer = document.createElement('aside');
      drawer.id = 'hp-drawer';
      drawer.className = 'hp-drawer';
      drawer.setAttribute('role', 'dialog');
      drawer.setAttribute('aria-modal', 'true');
      drawer.setAttribute('aria-labelledby', 'hp-drawer-title');

      drawer.innerHTML = `
        <div class="hp-drawer-header">
          <div class="hp-drawer-top">
            <div class="hp-drawer-title-group">
              <span class="hp-drawer-eyebrow">Customer &amp; Service Operations · Orange</span>
              <h2 id="hp-drawer-title" class="hp-drawer-title">
                <span>Alertas de Alta Prioridad</span>
              </h2>
            </div>
            <button type="button" class="hp-drawer-close" id="hp-drawer-close-btn" aria-label="Cerrar panel">&times;</button>
          </div>

          <div class="hp-kpis-bar" id="hp-kpis-bar">
            <div class="hp-kpi-chip kpi-p1">
              <span class="hp-kpi-chip-label">P1 Críticas</span>
              <span class="hp-kpi-chip-val" id="hp-kpi-p1">0</span>
            </div>
            <div class="hp-kpi-chip">
              <span class="hp-kpi-chip-label">P2 Altas</span>
              <span class="hp-kpi-chip-val" id="hp-kpi-p2">0</span>
            </div>
            <div class="hp-kpi-chip kpi-disc">
              <span class="hp-kpi-chip-label">Discrepancias</span>
              <span class="hp-kpi-chip-val" id="hp-kpi-disc">0</span>
            </div>
          </div>

          <div class="hp-filters-row">
            <button type="button" class="hp-filter-btn active" data-prio="all">Todas</button>
            <button type="button" class="hp-filter-btn" data-prio="p1">🔴 Solo P1</button>
            <button type="button" class="hp-filter-btn" data-prio="p2">🟠 Solo P2</button>
            <button type="button" class="hp-filter-btn" data-prio="discrepancy">⚠️ Discrepancias</button>
          </div>

          <div class="hp-filters-row" style="margin-top: 6px;">
            <button type="button" class="hp-filter-btn active" data-state="pending">⚡ Pendientes</button>
            <button type="button" class="hp-filter-btn" data-state="all">Ver todas</button>
            <button type="button" class="hp-filter-btn" data-state="managed">✓ Gestionadas</button>
          </div>
        </div>

        <div class="hp-drawer-body" id="hp-drawer-body">
          <!-- Tarjetas renderizadas dinámicamente -->
        </div>
      `;

      document.body.appendChild(backdrop);
      document.body.appendChild(drawer);

      document.getElementById('hp-drawer-close-btn').addEventListener('click', () => this.close());

      // Handlers de filtros de prioridad
      drawer.querySelectorAll('.hp-filters-row button[data-prio]').forEach(b => {
        b.addEventListener('click', (e) => {
          drawer.querySelectorAll('.hp-filters-row button[data-prio]').forEach(x => x.classList.remove('active'));
          e.currentTarget.classList.add('active');
          this.activeFilterPriority = e.currentTarget.dataset.prio;
          this.renderCards();
        });
      });

      // Handlers de filtros de estado
      drawer.querySelectorAll('.hp-filters-row button[data-state]').forEach(b => {
        b.addEventListener('click', (e) => {
          drawer.querySelectorAll('.hp-filters-row button[data-state]').forEach(x => x.classList.remove('active'));
          e.currentTarget.classList.add('active');
          this.activeFilterState = e.currentTarget.dataset.state;
          this.renderCards();
        });
      });
    }

    open() {
      const backdrop = document.getElementById('hp-drawer-backdrop');
      const drawer = document.getElementById('hp-drawer');
      if (backdrop && drawer) {
        backdrop.classList.add('active');
        drawer.classList.add('active');
        this.renderCards();
        document.body.style.overflow = 'hidden';
      }
    }

    close() {
      const backdrop = document.getElementById('hp-drawer-backdrop');
      const drawer = document.getElementById('hp-drawer');
      if (backdrop && drawer) {
        backdrop.classList.remove('active');
        drawer.classList.remove('active');
        document.body.style.overflow = '';
      }
    }

    bindGlobalKeys() {
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
          this.close();
        }
      });
    }

    updateBadge() {
      const badge = document.getElementById('hp-bell-badge');
      const btn = document.getElementById('hp-notifications-bell-btn');
      if (!badge || !btn) return;

      const states = StateManager.getAll();
      const pendingItems = this.items.filter(item => {
        const s = (states[item.id] && states[item.id].status) || 'pendiente';
        return s === 'pendiente';
      });

      const count = pendingItems.length;
      if (count > 0) {
        badge.textContent = count > 99 ? '99+' : count;
        badge.style.display = 'block';
        btn.classList.add('has-alerts');

        const hasP1 = pendingItems.some(i => i.prioridad_sugerida === 'P1');
        if (!hasP1) {
          badge.classList.add('badge-p2-only');
        } else {
          badge.classList.remove('badge-p2-only');
        }
      } else {
        badge.style.display = 'none';
        btn.classList.remove('has-alerts');
      }

      // Actualizar KPIs del drawer
      const kpiP1 = document.getElementById('hp-kpi-p1');
      const kpiP2 = document.getElementById('hp-kpi-p2');
      const kpiDisc = document.getElementById('hp-kpi-disc');
      if (this.catalog && this.catalog._metadata && this.catalog._metadata.kpis) {
        const k = this.catalog._metadata.kpis;
        if (kpiP1) kpiP1.textContent = k.p1_critical_count || 0;
        if (kpiP2) kpiP2.textContent = k.p2_high_count || 0;
        if (kpiDisc) kpiDisc.textContent = k.discrepancies_count || 0;
      }
    }

    renderCards() {
      const body = document.getElementById('hp-drawer-body');
      if (!body) return;

      const filtered = this.items.filter(item => {
        // Filtro por Prioridad
        if (this.activeFilterPriority === 'p1' && item.prioridad_sugerida !== 'P1') return false;
        if (this.activeFilterPriority === 'p2' && item.prioridad_sugerida !== 'P2') return false;
        if (this.activeFilterPriority === 'discrepancy' && !item.es_discrepancia) return false;

        // Filtro por Estado Operativo
        const st = StateManager.getStatus(item.id);
        if (this.activeFilterState === 'pending' && st !== 'pendiente') return false;
        if (this.activeFilterState === 'managed' && st === 'pendiente') return false;

        return true;
      });

      if (filtered.length === 0) {
        body.innerHTML = `
          <div class="hp-empty-state">
            <div class="hp-empty-icon">🎉</div>
            <h3 style="margin:0 0 6px 0; font-size:16px;">Sin incidencias en esta vista</h3>
            <p style="margin:0; font-size:13px;">No hay alertas pendientes con los filtros seleccionados.</p>
          </div>
        `;
        return;
      }

      body.innerHTML = filtered.map(item => this.createCardHtml(item)).join('');
      this.attachCardEvents(body);
    }

    createCardHtml(item) {
      const currentStatus = StateManager.getStatus(item.id);
      const isManaged = currentStatus !== 'pendiente';
      const isP1 = item.prioridad_sugerida === 'P1';
      const prioClass = isP1 ? 'priority-p1' : 'priority-p2';
      const prioBadgeClass = isP1 ? 'hp-badge-p1' : 'hp-badge-p2';
      const isOpenExec = this.openExecCards.has(item.id);
      const activePhase = this.activeExecPhases.get(item.id) || 'apertura';

      const sistemas = Array.isArray(item.sistemas) ? item.sistemas.join(', ') : (item.sistemas || 'Sistemas Core');
      const evalData = item.evaluacion || {};
      const sla = evalData.sla_objetivo_minutos ? `${evalData.sla_objetivo_minutos} min` : '60 min';

      let discrepancyHtml = '';
      if (item.es_discrepancia) {
        discrepancyHtml = `<span class="hp-badge hp-badge-discrepancy" title="Subescalación detectada: en ticket figura como ${item.prioridad_original} pero la IA calculó ${item.prioridad_sugerida}">⚠️ Ticket: ${this.escape(item.prioridad_original)} → IA: ${item.prioridad_sugerida}</span>`;
      }

      // Panel Ejecutivo si está abierto
      let execPanelHtml = '';
      if (isOpenExec && item.mensajes_ejecutivos) {
        const msgs = item.mensajes_ejecutivos;
        const currentMsg = msgs[activePhase] || msgs.apertura || {};

        execPanelHtml = `
          <div class="hp-exec-panel">
            <div class="hp-exec-tabs">
              <button type="button" class="hp-exec-tab ${activePhase === 'apertura' ? 'active' : ''}" data-action="set-phase" data-id="${item.id}" data-phase="apertura">🟢 Apertura</button>
              <button type="button" class="hp-exec-tab ${activePhase === 'seguimiento' ? 'active' : ''}" data-action="set-phase" data-id="${item.id}" data-phase="seguimiento">🟡 Seguimiento</button>
              <button type="button" class="hp-exec-tab ${activePhase === 'cierre' ? 'active' : ''}" data-action="set-phase" data-id="${item.id}" data-phase="cierre">🔵 Cierre</button>
            </div>

            <div class="hp-exec-box">
              <div class="hp-exec-section-label">
                <span>Versión Completa Dirección (${currentMsg.conteo_palabras_completo || 0}/90 palabras)</span>
                <span>Monopárrafo</span>
              </div>
              <p class="hp-exec-text">${this.escape(currentMsg.completo || '')}</p>
              <div class="hp-copy-row">
                <button type="button" class="hp-copy-btn" data-action="copy-text" data-text="${this.escapeAttr(currentMsg.completo || '')}">
                  📋 Copiar Versión Completa
                </button>
              </div>
            </div>

            <div class="hp-exec-box">
              <div class="hp-exec-section-label">
                <span>Versión Breve (${currentMsg.conteo_palabras_breve || 0}/30 palabras)</span>
                <span>SMS / Asunto</span>
              </div>
              <p class="hp-exec-text"><strong>${this.escape(currentMsg.breve || '')}</strong></p>
              <div class="hp-copy-row">
                <button type="button" class="hp-copy-btn" data-action="copy-text" data-text="${this.escapeAttr(currentMsg.breve || '')}">
                  📋 Copiar Versión Breve
                </button>
              </div>
            </div>
          </div>
        `;
      }

      return `
        <article class="hp-card ${prioClass} ${isManaged ? 'is-managed' : ''}" data-id="${item.id}">
          <div class="hp-card-top">
            <div class="hp-badges-cluster">
              <span class="hp-badge ${prioBadgeClass}">${item.prioridad_sugerida} ${isP1 ? 'Crítica' : 'Alta'}</span>
              <span class="hp-badge hp-badge-code">${item.id}</span>
              ${discrepancyHtml}
            </div>
            <div>
              <select class="hp-status-select" data-action="change-status" data-id="${item.id}">
                <option value="pendiente" ${currentStatus === 'pendiente' ? 'selected' : ''}>⚡ Pendiente</option>
                <option value="comunicada" ${currentStatus === 'comunicada' ? 'selected' : ''}>📢 Comunicada</option>
                <option value="en_seguimiento" ${currentStatus === 'en_seguimiento' ? 'selected' : ''}>🔄 En seguimiento</option>
                <option value="descartada" ${currentStatus === 'descartada' ? 'selected' : ''}>✕ Descartada</option>
              </select>
            </div>
          </div>

          <h3 class="hp-card-title">${this.escape(item.titulo || 'Incidencia sin descripción')}</h3>

          <div class="hp-itil-meta">
            <div class="hp-itil-item">
              <span class="hp-itil-label">Sistemas:</span>
              <span class="hp-itil-val">${this.escape(sistemas)}</span>
            </div>
            <div class="hp-itil-item">
              <span class="hp-itil-label">Impacto:</span>
              <span class="hp-itil-val">${this.escape(evalData.impacto || '-')}</span>
            </div>
            <div class="hp-itil-item">
              <span class="hp-itil-label">Urgencia:</span>
              <span class="hp-itil-val">${this.escape(evalData.urgencia || '-')}</span>
            </div>
            <div class="hp-itil-item">
              <span class="hp-itil-label">SLA Obj.:</span>
              <span class="hp-itil-val">${sla}</span>
            </div>
          </div>

          <div class="hp-card-actions">
            <button type="button" class="hp-btn hp-btn-primary" data-action="toggle-exec" data-id="${item.id}">
              📢 ${isOpenExec ? 'Ocultar Notificación' : 'Mensaje Ejecutivo'}
            </button>
            <button type="button" class="hp-btn hp-btn-secondary" data-action="open-resumen-ia" data-id="${item.id}">
              ✨ Resumen IA
            </button>
          </div>

          ${execPanelHtml}
        </article>
      `;
    }

    attachCardEvents(container) {
      // Cambio de estado select
      container.querySelectorAll('select[data-action="change-status"]').forEach(sel => {
        sel.addEventListener('change', (e) => {
          const id = e.target.dataset.id;
          const newStatus = e.target.value;
          StateManager.setStatus(id, newStatus);
          this.updateBadge();
          this.renderCards();
        });
      });

      // Botón Toggle Mensaje Ejecutivo
      container.querySelectorAll('button[data-action="toggle-exec"]').forEach(btn => {
        btn.addEventListener('click', (e) => {
          const id = e.currentTarget.dataset.id;
          if (this.openExecCards.has(id)) {
            this.openExecCards.delete(id);
          } else {
            this.openExecCards.add(id);
          }
          this.renderCards();
        });
      });

      // Cambio de fase ejecutiva (apertura, seguimiento, cierre)
      container.querySelectorAll('button[data-action="set-phase"]').forEach(btn => {
        btn.addEventListener('click', (e) => {
          const id = e.currentTarget.dataset.id;
          const phase = e.currentTarget.dataset.phase;
          this.activeExecPhases.set(id, phase);
          this.renderCards();
        });
      });

      // Botón Resumen IA (modal nativo)
      container.querySelectorAll('button[data-action="open-resumen-ia"]').forEach(btn => {
        btn.addEventListener('click', (e) => {
          const id = e.currentTarget.dataset.id;
          if (typeof window.openResumenIA === 'function') {
            window.openResumenIA(id);
          } else if (window.ResumenIAModal && typeof window.ResumenIAModal.open === 'function') {
            window.ResumenIAModal.open(id);
          } else {
            alert(`Resumen IA para ${id}: Abre la incidencia directamente en Remedy o inicia el modal.`);
          }
        });
      });

      // Copiado en 1 clic al portapapeles
      container.querySelectorAll('button[data-action="copy-text"]').forEach(btn => {
        btn.addEventListener('click', async (e) => {
          const text = e.currentTarget.dataset.text;
          try {
            await navigator.clipboard.writeText(text);
            const origHtml = e.currentTarget.innerHTML;
            e.currentTarget.classList.add('copied');
            e.currentTarget.innerHTML = '✅ ¡Copiado!';
            setTimeout(() => {
              e.currentTarget.classList.remove('copied');
              e.currentTarget.innerHTML = origHtml;
            }, 1800);
          } catch (err) {
            console.error('Error al copiar:', err);
            prompt('Copia manualmente con Ctrl+C:', text);
          }
        });
      });
    }

    escape(str) {
      if (!str) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    }

    escapeAttr(str) {
      if (!str) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
    }
  }

  // Inicializar cuando el DOM esté disponible
  function initComponent() {
    window.IncidentNotifications = new IncidentNotificationsManager();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initComponent);
  } else {
    initComponent();
  }
})();
