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
      if (!all[id]) {
        all[id] = {};
      }
      all[id].status = status;
      all[id].updated_at = new Date().toISOString();
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(all));
      } catch (e) {
        console.warn('[IncidentNotifications] Error escribiendo localStorage:', e);
      }
    },

    getCustomMessage(id, phase) {
      const all = this.getAll();
      return (all[id] && all[id].custom_messages && all[id].custom_messages[phase]) || null;
    },

    setCustomMessage(id, phase, completo, breve) {
      const all = this.getAll();
      if (!all[id]) {
        all[id] = { status: 'pendiente' };
      }
      if (!all[id].custom_messages) {
        all[id].custom_messages = {};
      }
      const wordsComp = (completo || '').trim().split(/\s+/).filter(Boolean).length;
      const wordsBrev = (breve || '').trim().split(/\s+/).filter(Boolean).length;
      all[id].custom_messages[phase] = {
        completo: completo.trim(),
        breve: breve.trim(),
        conteo_palabras_completo: wordsComp,
        conteo_palabras_breve: wordsBrev,
        is_custom: true,
        saved_at: new Date().toISOString()
      };
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(all));
      } catch (e) {
        console.warn('[IncidentNotifications] Error guardando custom message:', e);
      }
    },

    removeCustomMessage(id, phase) {
      const all = this.getAll();
      if (all[id] && all[id].custom_messages && all[id].custom_messages[phase]) {
        delete all[id].custom_messages[phase];
        try {
          localStorage.setItem(STORAGE_KEY, JSON.stringify(all));
        } catch (e) {
          console.warn('[IncidentNotifications] Error eliminando custom message:', e);
        }
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
      this.mountBell();
      this.renderDrawer();
      await this.loadData();
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
      const candidates = [
        '/data/output/high_priority_notifications.json',
        '../../data/output/high_priority_notifications.json',
        '../data/output/high_priority_notifications.json',
        './data/output/high_priority_notifications.json',
        '/data/high_priority_notifications.json'
      ];

      for (const url of candidates) {
        try {
          const res = await fetch(url, { cache: 'no-store' });
          if (res.ok) {
            this.catalog = await res.json();
            this.items = Array.isArray(this.catalog.data) ? this.catalog.data : [];
            this.activeDataUrl = url;
            return;
          }
        } catch (err) {
          // Intentar con siguiente ruta candidata
        }
      }
      console.info('[IncidentNotifications] Catálogo aún no disponible o fuera de línea');
    }

    // Montar la campana en la barra superior unificada
    mountBell() {
      const topbarRight = document.querySelector('.mo-topbar-right');
      let btn = document.getElementById('hp-notifications-bell-btn');

      if (!btn) {
        btn = document.createElement('button');
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
      }

      if (topbarRight) {
        if (btn.parentElement !== topbarRight) {
          btn.style.position = '';
          btn.style.top = '';
          btn.style.right = '';
          btn.style.zIndex = '';
          topbarRight.insertBefore(btn, topbarRight.firstChild);
        }
        this.updateBadge();
        return;
      }

      // Si .mo-topbar-right aún no existe en el DOM, esperar activamente a que MoTopbar se monte
      if (!this._observerConfigured) {
        this._observerConfigured = true;
        const observer = new MutationObserver(() => {
          const target = document.querySelector('.mo-topbar-right');
          if (target) {
            this.mountBell();
            observer.disconnect();
          }
        });
        if (document.body) {
          observer.observe(document.body, { childList: true, subtree: true });
        } else {
          document.addEventListener('DOMContentLoaded', () => {
            observer.observe(document.body, { childList: true, subtree: true });
          });
        }

        document.addEventListener('mo-topbar-rendered', () => this.mountBell(), { once: true });
      }

      // Si tras 800ms sigue sin existir la barra superior, montar botón flotante de respaldo
      if (!this._fallbackTimer) {
        this._fallbackTimer = setTimeout(() => {
          const target = document.querySelector('.mo-topbar-right');
          if (!target && !document.getElementById('hp-notifications-bell-btn') && document.body) {
            btn.style.position = 'fixed';
            btn.style.top = '16px';
            btn.style.right = '24px';
            btn.style.zIndex = '999';
            document.body.appendChild(btn);
            this.updateBadge();
          }
        }, 800);
      }
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
      const hasEpsilon = Boolean(item.resumen_ia && (item.resumen_ia.problema || item.resumen_ia.impacto || item.resumen_ia.solucion));

      let discrepancyHtml = '';
      if (item.es_discrepancia) {
        discrepancyHtml = `<span class="hp-badge hp-badge-discrepancy" title="Subescalación detectada: en ticket figura como ${item.prioridad_original} pero la IA calculó ${item.prioridad_sugerida}">⚠️ Ticket: ${this.escape(item.prioridad_original)} → IA: ${item.prioridad_sugerida}</span>`;
      }

      // SLA y Escalados (orange-it-emergency-management)
      const mins = evalData.minutos_desde_apertura;
      const sla1aVencido = Boolean(evalData.sla_primera_notificacion_vencido);
      const reqEscaladoTel = Boolean(evalData.requiere_escalado_telefonico);
      const escSuperior = Boolean(evalData.escalado_estamentos_superiores);
      const workaroundGob = evalData.workaround_gobernanza;
      const hasWorkaround = evalData.workaround === 'Sí';

      let slaBadgeHtml = '';
      if (mins !== undefined && mins !== null) {
        if (sla1aVencido) {
          slaBadgeHtml = `<span class="hp-badge hp-badge-sla-overdue" title="SLA 1ª Notificación a Dirección (>20 min) VENCIDO (${mins} min)">🔴 1ª Notif. >20m (${mins}m)</span>`;
        } else {
          slaBadgeHtml = `<span class="hp-badge hp-badge-sla-ok" title="En tiempo para 1ª Notificación a Dirección (<20 min) (${mins} min)">🟢 1ª Notif. &lt;20m (${mins}m)</span>`;
        }
      }

      let escaladoBadgeHtml = '';
      if (escSuperior) {
        escaladoBadgeHtml = `<span class="hp-badge hp-badge-phone-escalation hp-badge-esc-superior" title="Superados 105 min sin resolución. Protocolo Orange: 2º escalado a Estamentos Superiores liderado por IM-CSO">🚨 &gt;1h45m: Escalado Estamentos Superiores</span>`;
      } else if (reqEscaladoTel) {
        escaladoBadgeHtml = `<span class="hp-badge hp-badge-phone-escalation" title="Superados 45 min sin avances. Regla de Oro: Incident Manager debe realizar escalado telefónico a N3 / Proveedor">📞 &gt;45m: Escalado Telefónico N3 / Proveedor</span>`;
      }

      let workaroundBadgeHtml = '';
      if (hasWorkaround) {
        workaroundBadgeHtml = `<span class="hp-badge hp-badge-workaround-cso" title="Reglas de Oro 2 y 3: Workaround aplicado. Requiere autorización de IM-CSO y NO reduce severidad mientras persista impacto.">⚠️ Workaround (Req. IM-CSO)</span>`;
      }

      let epsilonBadgeHtml = hasEpsilon
        ? `<span class="hp-badge hp-badge-epsilon" title="Contexto enriquecido con Epsilon Resumen IA">✨ Epsilon IA</span>`
        : `<span class="hp-badge hp-badge-no-epsilon" title="Datos basados en ticket Remedy. Pulsa 'Sincronizar' para enriquecer con Epsilon">ℹ️ Remedy Base</span>`;

      // Panel Ejecutivo si está abierto
      let execPanelHtml = '';
      if (isOpenExec) {
        const msgs = item.mensajes_ejecutivos || {};
        const customMsg = StateManager.getCustomMessage(item.id, activePhase);
        const currentMsg = customMsg || msgs[activePhase] || msgs.apertura || {};
        const isCustom = Boolean(customMsg);
        const hasAgentOutput = Boolean((currentMsg.completo && currentMsg.completo.trim()) || (currentMsg.breve && currentMsg.breve.trim()));
        const res = item.resumen_ia || {};

        let badgeTitle = '🤖 Salida de Agente incident-reporter';
        let badgeSub = hasEpsilon ? 'Síntesis ejecutiva con Epsilon IA' : 'Síntesis ejecutiva sobre Remedy Base';
        let badgeClass = 'hp-badge-official';

        if (isCustom) {
          badgeTitle = '✏️ Redacción Personalizada';
          badgeSub = 'Editado en cliente / pegado desde LLM';
          badgeClass = 'hp-badge-custom';
        } else if (!hasAgentOutput) {
          badgeTitle = '⏳ Redacción de Agente Pendiente';
          badgeSub = 'Listo para procesar prompt en Copilot/LLM';
          badgeClass = 'hp-badge-pending';
        }

        let epsilonContextBox = '';
        if (hasEpsilon) {
          epsilonContextBox = `
            <div class="hp-epsilon-summary-box">
              <div class="hp-epsilon-header">
                <span class="hp-epsilon-title">✨ Contexto Técnico Epsilon Resumen IA</span>
                <button type="button" class="hp-sync-btn" data-action="sync-epsilon" data-id="${item.id}" title="Reconsultar Epsilon en tiempo real">🔄 Actualizar</button>
              </div>
              <div class="hp-epsilon-grid">
                ${res.problema ? `<div class="hp-epsilon-field"><span class="hp-ep-label">Problema:</span> <span class="hp-ep-val">${this.escape(res.problema)}</span></div>` : ''}
                ${res.impacto ? `<div class="hp-epsilon-field"><span class="hp-ep-label">Impacto:</span> <span class="hp-ep-val">${this.escape(res.impacto)}</span></div>` : ''}
                ${res.solucion ? `<div class="hp-epsilon-field"><span class="hp-ep-label">Causa/Solución:</span> <span class="hp-ep-val">${this.escape(res.solucion)}</span></div>` : ''}
                ${res.siguiente_accion ? `<div class="hp-epsilon-field"><span class="hp-ep-label">Siguiente acción:</span> <span class="hp-ep-val">${this.escape(res.siguiente_accion)}</span></div>` : ''}
                ${res.bloqueos ? `<div class="hp-epsilon-field"><span class="hp-ep-label">Bloqueos:</span> <span class="hp-ep-val hp-ep-alert">${this.escape(res.bloqueos)}</span></div>` : ''}
              </div>
            </div>
          `;
        } else {
          epsilonContextBox = `
            <div class="hp-epsilon-summary-box hp-epsilon-missing">
              <span class="hp-ep-missing-text">ℹ️ Esta alerta usa metadatos base. Puedes sincronizar el Resumen IA de Epsilon para enriquecer el contexto.</span>
              <button type="button" class="hp-sync-btn hp-sync-btn-highlight" data-action="sync-epsilon" data-id="${item.id}">🔄 Sincronizar Epsilon IA</button>
            </div>
          `;
        }

        execPanelHtml = `
          <div class="hp-exec-panel">
            <div class="hp-exec-agent-banner">
              <div class="hp-exec-agent-badge-group">
                <span class="hp-exec-agent-badge ${badgeClass}">
                  ${badgeTitle}
                </span>
                <span class="hp-exec-agent-sub">
                  ${badgeSub}
                </span>
              </div>
              ${isCustom ? `
                <button type="button" class="hp-reset-agent-btn" data-action="reset-agent-output" data-id="${item.id}" data-phase="${activePhase}" title="Restaurar el mensaje oficial generado por el agente">
                  ↺ Restaurar original
                </button>
              ` : ''}
            </div>

            <div class="hp-exec-tabs">
              <button type="button" class="hp-exec-tab ${activePhase === 'apertura' ? 'active' : ''}" data-action="set-phase" data-id="${item.id}" data-phase="apertura">🟢 Apertura</button>
              <button type="button" class="hp-exec-tab ${activePhase === 'seguimiento' ? 'active' : ''}" data-action="set-phase" data-id="${item.id}" data-phase="seguimiento">🟡 Seguimiento</button>
              <button type="button" class="hp-exec-tab ${activePhase === 'cierre' ? 'active' : ''}" data-action="set-phase" data-id="${item.id}" data-phase="cierre">🔵 Cierre</button>
            </div>

            ${epsilonContextBox}

            ${hasAgentOutput ? `
              <div class="hp-exec-box">
                <div class="hp-exec-section-label">
                  <span>Versión Completa Dirección (${currentMsg.conteo_palabras_completo || 0}/90 palabras)</span>
                  <span>Monopárrafo</span>
                </div>
                <p class="hp-exec-text">${this.escape(currentMsg.completo || '')}</p>
                <div class="hp-copy-row">
                  <button type="button" class="hp-copy-btn" data-action="copy-text" data-text="${this.escapeAttr(currentMsg.completo || '')}">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                      <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                    </svg>
                    Copiar Versión Completa
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
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                      <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                    </svg>
                    Copiar Versión Breve
                  </button>
                </div>
              </div>
            ` : `
              <div class="hp-exec-pending-card">
                <div class="hp-exec-pending-header">
                  <span class="hp-exec-pending-icon">⏳</span>
                  <div>
                    <h4 class="hp-exec-pending-title">Redacción de Agente Pendiente</h4>
                    <p class="hp-exec-pending-desc">Esta incidencia no cuenta todavía con mensaje ejecutivo redactado por el agente <code>incident-reporter</code>. Copia el prompt preparado a continuación para procesarlo con tu LLM/Copilot y pulsa <strong>Pegar salida de Agente</strong> para guardarlo.</p>
                  </div>
                </div>
              </div>
            `}

            <div class="hp-agent-prompt-box">
              <div class="hp-exec-section-label">
                <span>🤖 Prompt para Agente incident-reporter</span>
                <span>${hasEpsilon ? 'Contexto Epsilon IA' : 'Metadatos Base'}</span>
              </div>
              <p class="hp-prompt-hint">Copia el prompt estructurado con todo el contexto técnico o pega directamente aquí la respuesta devuelta por el agente:</p>

              <div class="cmd-snippet-box hp-prompt-snippet-box">
                <span class="cmd-text hp-prompt-snippet-text" title="Haz clic o copia para usar en tu LLM">${this.escape(`Actúa como incident-reporter: ${item.id} (${activePhase.toUpperCase()} - ${item.prioridad_sugerida})`)}</span>
                <button type="button" class="cmd-copy-mini-btn hp-prompt-copy-mini-btn" data-action="copy-prompt" data-id="${item.id}" data-phase="${activePhase}" title="Copiar Prompt CLI/LLM" aria-label="Copiar prompt">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                  </svg>
                </button>
              </div>

              <div class="agent-card-actions hp-prompt-actions-row">
                <button type="button" class="btn-primary-action hp-btn-copy-prompt" data-action="copy-prompt" data-id="${item.id}" data-phase="${activePhase}">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                  </svg>
                  Copiar Prompt con Contexto
                </button>
                <button type="button" class="btn-secondary-action hp-btn-paste-agent" data-action="paste-agent-output" data-id="${item.id}" data-phase="${activePhase}">
                  ✏️ Pegar salida de Agente
                </button>
              </div>
            </div>

            <div class="hp-emergency-report-box">
              <div class="hp-exec-section-label">
                <span>🚨 Reporte Operativo de Emergencia (4 Bloques Orange)</span>
                <span>Protocolo IM-CSO</span>
              </div>
              <p class="hp-prompt-hint">Estructura normalizada para seguimiento técnico y escalados oficiales:</p>
              <pre class="hp-emergency-report-text">${this.escape(item.reporte_emergencia || this.buildEmergency4BlocksReport(item))}</pre>
              <div class="hp-copy-row">
                <button type="button" class="hp-copy-btn" data-action="copy-emergency-report" data-id="${item.id}">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                  </svg>
                  Copiar Reporte 4 Bloques
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
              ${slaBadgeHtml}
              ${escaladoBadgeHtml}
              ${workaroundBadgeHtml}
              ${epsilonBadgeHtml}
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
            <div class="hp-itil-item hp-itil-proceso">
              <span class="hp-itil-label">Proceso:</span>
              <span class="hp-itil-val hp-process-tag">${this.escape(evalData.proceso || 'Sistemas Core')}</span>
            </div>
            <div class="hp-itil-item hp-itil-criterio">
              <span class="hp-itil-label">Criterio:</span>
              <span class="hp-itil-val hp-criterio-text" title="${this.escape(evalData.criterio || '-')}">${this.escape(evalData.criterio || '-')}</span>
            </div>
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
            ${mins !== undefined && mins !== null ? `
            <div class="hp-itil-item">
              <span class="hp-itil-label">Transcurrido:</span>
              <span class="hp-itil-val hp-timer-val ${sla1aVencido ? 'sla-warn' : ''}">${mins} min</span>
            </div>` : ''}
            ${workaroundGob ? `
            <div class="hp-itil-item hp-itil-workaround">
              <span class="hp-itil-label">Gobernanza:</span>
              <span class="hp-itil-val hp-workaround-val">${this.escape(workaroundGob)}</span>
            </div>` : ''}
          </div>

          <div class="hp-card-actions">
            <button type="button" class="hp-btn hp-btn-primary" data-action="toggle-exec" data-id="${item.id}">
              📢 ${isOpenExec ? 'Ocultar Notificación' : 'Mensaje Ejecutivo'}
            </button>
            <button type="button" class="hp-btn hp-btn-secondary" data-action="open-resumen-ia" data-id="${item.id}">
              ✨ Resumen IA
            </button>
            <button type="button" class="hp-btn hp-btn-emergency" data-action="copy-emergency-report" data-id="${item.id}" title="Copiar reporte oficial de emergencia en 4 bloques según protocolo Orange">
              📋 Reporte Emergencia
            </button>
          </div>

          ${execPanelHtml}
        </article>
      `;
    }

    buildAgentPrompt(item, phase, forceRebuild = false) {
      const msgs = item.mensajes_ejecutivos || {};
      if (!forceRebuild && msgs[phase] && msgs[phase].prompt_agente) {
        return msgs[phase].prompt_agente;
      }

      const incId = item.id || 'INC';
      const prio = item.prioridad_sugerida || 'P2';
      const faseLabel = (phase || 'apertura').toUpperCase();
      const sistemas = Array.isArray(item.sistemas) ? item.sistemas.join(', ') : (item.sistemas || 'Sistemas Core');
      const res = item.resumen_ia;

      const lines = [
        'Actúa como el agente incident-reporter (comunicación ejecutiva para Dirección, versión completa de hasta 90 palabras y versión breve de hasta 30 palabras).',
        `Fase solicitada: ${faseLabel}`,
        `Incidencia: ${incId} - ${item.titulo || ''}`,
        `Criticidad sugerida: ${prio}`,
        `Sistemas involucrados: ${sistemas}`,
      ];

      const evalData = item.evaluacion || {};
      if (evalData.proceso) lines.push(`Proceso de Negocio: ${evalData.proceso}`);
      if (evalData.criterio) lines.push(`Criterio / Umbral: ${evalData.criterio}`);
      lines.push('');

      if (res && (res.problema || res.impacto || res.solucion)) {
        lines.push('--- Contexto extraído de Epsilon Resumen IA ---');
        if (res.problema) lines.push(`• Problema detectado: ${res.problema}`);
        if (res.impacto) lines.push(`• Impacto en servicio/negocio: ${res.impacto}`);
        if (res.solucion) lines.push(`• Causa raíz / Solución: ${res.solucion}`);
        if (res.siguiente_accion || res.siguienteAccion) lines.push(`• Siguiente acción: ${res.siguiente_accion || res.siguienteAccion}`);
        if (res.estadoActual) lines.push(`• Estado actual reportado: ${res.estadoActual}`);
        if (res.bloqueos) lines.push(`• Bloqueos identificados: ${Array.isArray(res.bloqueos) ? res.bloqueos.join('; ') : res.bloqueos}`);
      } else {
        lines.push('--- Metadatos del ticket (Epsilon IA pendiente) ---');
        lines.push(`• Descripción: ${item.titulo || ''}`);
        const evalData = item.evaluacion || {};
        lines.push(`• Impacto ticket: ${evalData.impacto || 'N/D'}`);
        lines.push(`• Urgencia ticket: ${evalData.urgencia || 'N/D'}`);
      }

      lines.push('');
      lines.push('Redacta el mensaje en los dos niveles obligatorios:');
      lines.push('**Mensaje para Dirección (versión completa):** (único párrafo, máx 90 palabras)');
      lines.push('**Versión aún más breve:** (máx 30 palabras)');

      return lines.join('\n');
    }

    refreshMessagesForEpsilon(item) {
      if (!item.mensajes_ejecutivos) {
        item.mensajes_ejecutivos = {};
      }
      // Actualizar el prompt estructurado para cada fase sin alterar mensajes oficiales o personalizados
      ['apertura', 'seguimiento', 'cierre'].forEach(phase => {
        const prev = item.mensajes_ejecutivos[phase] || {};
        item.mensajes_ejecutivos[phase] = {
          ...prev,
          prompt_agente: this.buildAgentPrompt(item, phase, true)
        };
      });
    }

    buildEmergency4BlocksReport(item) {
      if (item.reporte_emergencia) return item.reporte_emergencia;

      const evalData = item.evaluacion || {};
      const res = item.resumen_ia || {};
      const sistemas = Array.isArray(item.sistemas) ? item.sistemas.join(', ') : (item.sistemas || 'Sistemas Core');
      const mins = evalData.minutos_desde_apertura !== undefined && evalData.minutos_desde_apertura !== null
        ? `${evalData.minutos_desde_apertura} min`
        : 'Desconocido';

      const esc = evalData.escalado_estamentos_superiores
        ? 'Superados 105 min. Requiere 2º escalado a Estamentos Superiores liderado por IM-CSO.'
        : (evalData.requiere_escalado_telefonico
          ? 'Superados 45 min sin avances. Regla de Oro: Requiere escalado telefónico a N3 / Proveedor.'
          : 'Dentro de ventana normal de trabajo.');

      return [
        '================================================================================',
        'REPORTE OPERATIVO DE EMERGENCIA IT - ORANGE',
        `Incidencia: ${item.id} | Severidad: ${item.prioridad_sugerida} | Proceso: ${evalData.proceso || 'Core'}`,
        '================================================================================',
        '',
        '1. RESUMEN EJECUTIVO',
        `  - Incidencia: ${item.id}`,
        `  - Severidad: ${item.prioridad_sugerida} (Original: ${item.prioridad_original || 'N/A'})`,
        `  - Proceso Crítico: ${evalData.proceso || 'Core'} (Criterio: ${evalData.criterio || 'Operación'})`,
        `  - Estado Operativo: ${item.estado || 'Activo'}`,
        `  - Impacto de Negocio: ${res.impacto || evalData.impacto || item.titulo || 'Impacto en servicio'}`,
        '',
        '2. DETALLE TÉCNICO Y CAUSA',
        `  - Síntomas y Causa: ${res.problema || res.solucion || item.titulo || 'En investigación'}`,
        `  - Sistemas Afectados: ${sistemas}`,
        `  - Workaround / Mitigación: ${evalData.workaround_gobernanza || (evalData.workaround === 'Sí' ? 'Workaround activo (Pendiente IM-CSO)' : 'Sin workaround aplicable')}`,
        '',
        '3. CRONOLOGÍA Y GOBERNANZA',
        `  - Apertura / Detección: ${item.fecha_inicio || 'N/A'}`,
        `  - Tiempo Transcurrido: ${mins}`,
        `  - 1ª Notificación a Dirección: ${evalData.sla_primera_notificacion_vencido ? 'VENCIDA (>20 min)' : 'En plazo (<20 min)'}`,
        `  - Próxima Ventana de Actualización: ${evalData.proxima_ventana_update_minutos || 60} min`,
        `  - Estado de Escalado: ${esc}`,
        '',
        '4. ACCIONES EN CURSO Y EQUIPOS',
        `  - Asignatario / Grupo: ${item.grupo_asignado || 'N3 / Operaciones'}`,
        `  - Acciones Inmediatas: ${res.siguiente_accion || 'Monitorización técnica y diagnóstico continuo con equipos de soporte.'}`,
        `  - Bloqueos Activos: ${res.bloqueos || 'Sin bloqueos declarados.'}`,
        '================================================================================'
      ].join('\n');
    }

    async syncEpsilon(id, buttonEl) {
      if (!id) return;
      const originalText = buttonEl ? buttonEl.innerHTML : '';
      if (buttonEl) {
        buttonEl.disabled = true;
        buttonEl.innerHTML = '⏳ Consultando Epsilon...';
      }

      try {
        const res = await fetch(`/api/epsilon/resumenIA/${encodeURIComponent(id)}`, {
          headers: { 'Accept': 'application/json', 'Cache-Control': 'no-cache' }
        });
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        const payload = await res.json();
        const data = (payload && payload.data) ? payload.data : payload;
        if (!data || (!data.problema && !data.impacto && !data.solucion)) {
          throw new Error('Epsilon no devolvió resumen para esta incidencia');
        }

        const item = this.items.find(x => x.id === id);
        if (item) {
          item.resumen_ia = {
            problema: data.problema || '',
            impacto: data.impacto || '',
            solucion: data.solucion || '',
            bloqueos: Array.isArray(data.bloqueos) ? data.bloqueos.join('; ') : (data.bloqueos || ''),
            siguiente_accion: data.siguienteAccion || data.siguiente_accion || '',
            estadoActual: data.estadoActual || ''
          };
          if (Array.isArray(data.sistemas) && data.sistemas.length > 0) {
            item.sistemas = data.sistemas;
          }
          this.refreshMessagesForEpsilon(item);
          this.renderCards();
        }
      } catch (err) {
        console.warn(`[IncidentNotifications] Error al sincronizar con Epsilon para ${id}:`, err);
        if (buttonEl) {
          buttonEl.innerHTML = '⚠️ No disponible';
          setTimeout(() => {
            buttonEl.disabled = false;
            buttonEl.innerHTML = originalText;
          }, 2000);
        }
      }
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
        btn.addEventListener('click', (e) => {
          const text = e.currentTarget.dataset.text;
          this.copyToClipboard(text, e.currentTarget, 'Mensaje copiado al portapapeles');
        });
      });

      // Copiado de Prompt estructurado para Agente IA
      container.querySelectorAll('button[data-action="copy-prompt"]').forEach(btn => {
        btn.addEventListener('click', (e) => {
          const id = e.currentTarget.dataset.id;
          const phase = e.currentTarget.dataset.phase || 'apertura';
          const item = this.items.find(x => x.id === id);
          if (!item) return;

          const promptText = this.buildAgentPrompt(item, phase);
          this.copyToClipboard(promptText, e.currentTarget, 'Prompt con contexto copiado');
        });
      });

      // Clic directo en el snippet de texto del prompt para copiar
      container.querySelectorAll('.hp-prompt-snippet-text').forEach(el => {
        el.addEventListener('click', (e) => {
          const box = e.currentTarget.closest('.hp-prompt-snippet-box');
          const btn = box ? box.querySelector('button[data-action="copy-prompt"]') : null;
          if (btn) btn.click();
        });
      });

      // Sincronización en vivo con Epsilon Resumen IA
      container.querySelectorAll('button[data-action="sync-epsilon"]').forEach(btn => {
        btn.addEventListener('click', (e) => {
          const id = e.currentTarget.dataset.id;
          this.syncEpsilon(id, e.currentTarget);
        });
      });

      // Pegar salida personalizada de Agente LLM
      container.querySelectorAll('button[data-action="paste-agent-output"]').forEach(btn => {
        btn.addEventListener('click', (e) => {
          const id = e.currentTarget.dataset.id;
          const phase = e.currentTarget.dataset.phase || 'apertura';
          this.openPasteModal(id, phase);
        });
      });

      // Restaurar salida original del Agente
      container.querySelectorAll('button[data-action="reset-agent-output"]').forEach(btn => {
        btn.addEventListener('click', (e) => {
          const id = e.currentTarget.dataset.id;
          const phase = e.currentTarget.dataset.phase || 'apertura';
          StateManager.removeCustomMessage(id, phase);
          this.renderCards();
        });
      });

      // Copiar Reporte de Emergencia oficial en 4 bloques
      container.querySelectorAll('button[data-action="copy-emergency-report"]').forEach(btn => {
        btn.addEventListener('click', (e) => {
          const id = e.currentTarget.dataset.id;
          const item = this.items.find(x => x.id === id);
          if (!item) return;

          const reportText = item.reporte_emergencia || this.buildEmergency4BlocksReport(item);
          this.copyToClipboard(reportText, e.currentTarget, 'Reporte de emergencia en 4 bloques copiado');
        });
      });
    }

    parseAgentOutput(raw) {
      let completo = '';
      let breve = '';
      if (!raw || typeof raw !== 'string') return { completo, breve };

      const clean = raw.trim();

      // Buscar versión completa
      const compRegex = /\*\*(?:Mensaje para Dirección|Versión Completa)[^\*]*\*\*[:\s]*([\s\S]*?)(?=\*\*(?:Versión aún más breve|Versión breve)[^\*]*\*\*|$)/i;
      const compMatch = clean.match(compRegex);
      if (compMatch && compMatch[1]) {
        completo = compMatch[1].trim();
      }

      // Buscar versión breve
      const brevRegex = /\*\*(?:Versión aún más breve|Versión breve)[^\*]*\*\*[:\s]*([\s\S]*?)$/i;
      const brevMatch = clean.match(brevRegex);
      if (brevMatch && brevMatch[1]) {
        breve = brevMatch[1].trim();
      }

      // Si no se usó el formato exacto de doble asterisco
      if (!completo && !breve) {
        const paras = clean.split(/\n\s*\n/).map(p => p.trim()).filter(Boolean);
        if (paras.length >= 2) {
          completo = paras[0];
          breve = paras[1];
        } else {
          completo = clean;
          breve = clean.split('.')[0] || clean.substring(0, 100);
        }
      } else if (!breve && completo) {
        breve = completo.split('.')[0] || completo.substring(0, 100);
      }

      // Limpiar prefijos de instrucciones entre paréntesis que pudieran haberse capturado
      completo = completo.replace(/^\([^)]*\)\s*/, '').replace(/^["'`]+|["'`]+$/g, '').trim();
      breve = breve.replace(/^\([^)]*\)\s*/, '').replace(/^["'`]+|["'`]+$/g, '').trim();

      return { completo, breve };
    }

    openPasteModal(id, phase) {
      const item = this.items.find(x => x.id === id);
      if (!item) return;

      const msgs = item.mensajes_ejecutivos || {};
      const customMsg = StateManager.getCustomMessage(id, phase);
      const current = customMsg || msgs[phase] || msgs.apertura || {};

      let modalBackdrop = document.getElementById('hp-paste-modal');
      if (!modalBackdrop) {
        modalBackdrop = document.createElement('div');
        modalBackdrop.id = 'hp-paste-modal';
        modalBackdrop.className = 'hp-paste-backdrop';
        document.body.appendChild(modalBackdrop);
      }

      const phaseName = (phase || 'apertura').toUpperCase();
      const defaultComp = current.completo || '';
      const defaultBrev = current.breve || '';
      const wordsComp = defaultComp ? defaultComp.split(/\s+/).filter(Boolean).length : 0;
      const wordsBrev = defaultBrev ? defaultBrev.split(/\s+/).filter(Boolean).length : 0;

      modalBackdrop.innerHTML = `
        <div class="hp-paste-dialog" role="dialog" aria-modal="true" aria-labelledby="hp-paste-title">
          <div class="hp-paste-header">
            <div>
              <span class="hp-paste-eyebrow">Agente incident-reporter</span>
              <h3 id="hp-paste-title" class="hp-paste-title">✏️ Salida del Agente (${this.escape(id)} - ${phaseName})</h3>
            </div>
            <button type="button" class="hp-paste-close" id="hp-paste-close-btn" aria-label="Cerrar">&times;</button>
          </div>

          <div class="hp-paste-body">
            <p class="hp-paste-desc">
              Pega aquí el texto devuelto por el LLM al ejecutar el Prompt. Se autocompletarán la Versión Completa (máx 90 palabras) y la Versión Breve (máx 30 palabras).
            </p>

            <div class="hp-paste-field">
              <label for="hp-paste-raw" class="hp-paste-label">📋 Pegar respuesta completa del LLM / Agente:</label>
              <textarea id="hp-paste-raw" class="hp-paste-textarea" rows="3" placeholder="Pega aquí la salida del agente..."></textarea>
            </div>

            <div class="hp-paste-field">
              <div class="hp-paste-field-header">
                <label for="hp-paste-comp" class="hp-paste-label">Versión Completa Dirección (Monopárrafo):</label>
                <span id="hp-paste-comp-count" class="hp-word-count-badge ${wordsComp > 90 ? 'count-overflow' : ''}">${wordsComp} / 90 palabras</span>
              </div>
              <textarea id="hp-paste-comp" class="hp-paste-textarea" rows="4">${this.escape(defaultComp)}</textarea>
            </div>

            <div class="hp-paste-field">
              <div class="hp-paste-field-header">
                <label for="hp-paste-brev" class="hp-paste-label">Versión Aún Más Breve (SMS / Asunto):</label>
                <span id="hp-paste-brev-count" class="hp-word-count-badge ${wordsBrev > 30 ? 'count-overflow' : ''}">${wordsBrev} / 30 palabras</span>
              </div>
              <textarea id="hp-paste-brev" class="hp-paste-textarea" rows="2">${this.escape(defaultBrev)}</textarea>
            </div>
          </div>

          <div class="hp-paste-footer">
            <button type="button" class="hp-btn hp-btn-secondary" id="hp-paste-cancel-btn">Cancelar</button>
            <button type="button" class="hp-btn hp-btn-primary" id="hp-paste-save-btn">💾 Guardar Mensaje Ejecutivo</button>
          </div>
        </div>
      `;

      modalBackdrop.classList.add('active');

      const rawInput = document.getElementById('hp-paste-raw');
      const compInput = document.getElementById('hp-paste-comp');
      const brevInput = document.getElementById('hp-paste-brev');
      const compCount = document.getElementById('hp-paste-comp-count');
      const brevCount = document.getElementById('hp-paste-brev-count');

      const updateWordCounts = () => {
        const cVal = compInput.value.trim();
        const bVal = brevInput.value.trim();
        const cLen = cVal ? cVal.split(/\s+/).filter(Boolean).length : 0;
        const bLen = bVal ? bVal.split(/\s+/).filter(Boolean).length : 0;

        compCount.textContent = `${cLen} / 90 palabras`;
        compCount.className = `hp-word-count-badge ${cLen > 90 ? 'count-overflow' : ''}`;

        brevCount.textContent = `${bLen} / 30 palabras`;
        brevCount.className = `hp-word-count-badge ${bLen > 30 ? 'count-overflow' : ''}`;
      };

      rawInput.addEventListener('input', () => {
        const parsed = this.parseAgentOutput(rawInput.value);
        if (parsed.completo) compInput.value = parsed.completo;
        if (parsed.breve) brevInput.value = parsed.breve;
        updateWordCounts();
      });

      compInput.addEventListener('input', updateWordCounts);
      brevInput.addEventListener('input', updateWordCounts);

      const closeModal = () => {
        modalBackdrop.classList.remove('active');
      };

      document.getElementById('hp-paste-close-btn').addEventListener('click', closeModal);
      document.getElementById('hp-paste-cancel-btn').addEventListener('click', closeModal);
      modalBackdrop.addEventListener('click', (e) => {
        if (e.target === modalBackdrop) closeModal();
      });

      document.getElementById('hp-paste-save-btn').addEventListener('click', () => {
        const finalComp = compInput.value.trim();
        const finalBrev = brevInput.value.trim();
        if (!finalComp && !finalBrev) {
          this.notify('Por favor, introduce al menos una de las versiones del mensaje.', 'warning');
          return;
        }
        StateManager.setCustomMessage(id, phase, finalComp, finalBrev);
        closeModal();
        this.renderCards();
      });

      setTimeout(() => rawInput.focus(), 80);
    }

    copyToClipboard(text, triggerBtn, successMessage) {
      if (!text) return;

      if (navigator.clipboard && navigator.clipboard.writeText && window.isSecureContext) {
        navigator.clipboard.writeText(text)
          .then(() => {
            this.handleCopySuccess(triggerBtn, successMessage);
          })
          .catch(() => {
            this.fallbackExecCommand(text, triggerBtn, successMessage);
          });
      } else {
        this.fallbackExecCommand(text, triggerBtn, successMessage);
      }
    }

    fallbackExecCommand(text, triggerBtn, successMessage) {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.setAttribute('readonly', '');
      ta.style.position = 'fixed';
      ta.style.left = '-9999px';
      ta.style.top = '-9999px';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      try {
        const ok = document.execCommand('copy');
        if (ok) {
          this.handleCopySuccess(triggerBtn, successMessage);
        } else {
          this.notify('No se pudo copiar automáticamente', 'warning');
        }
      } catch (err) {
        console.warn('[IncidentNotifications] Error al copiar con execCommand:', err);
        this.notify('No se pudo copiar automáticamente', 'error');
      } finally {
        if (document.body.contains(ta)) {
          document.body.removeChild(ta);
        }
      }
    }

    handleCopySuccess(triggerBtn, successMessage) {
      this.notify(successMessage || 'Copiado al portapapeles', 'success');

      if (triggerBtn) {
        const origHtml = triggerBtn.innerHTML;
        triggerBtn.classList.add('copied');
        const hasSvg = origHtml.indexOf('<svg') !== -1;
        const isMini = triggerBtn.classList.contains('cmd-copy-mini-btn') || triggerBtn.classList.contains('hp-prompt-copy-mini-btn');

        if (isMini) {
          triggerBtn.innerHTML = `
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#16A34A" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
          `;
        } else {
          triggerBtn.innerHTML = `
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
            <span>✓ Copiado</span>
          `;
        }

        setTimeout(() => {
          triggerBtn.classList.remove('copied');
          triggerBtn.innerHTML = origHtml;
        }, 2000);
      }
    }

    notify(message, type = 'info') {
      if (window.Toast && typeof window.Toast.show === 'function') {
        window.Toast.show(message, type);
      } else if (window.UIFeedback && typeof window.UIFeedback.toast === 'function') {
        window.UIFeedback.toast(message, type);
      } else {
        this.showFloatingToast(message, type);
      }
    }

    showFloatingToast(message, type = 'info') {
      let toast = document.getElementById('hp-global-toast');
      if (!toast) {
        toast = document.createElement('div');
        toast.id = 'hp-global-toast';
        toast.className = 'hp-global-toast';
        document.body.appendChild(toast);
      }

      const icon = type === 'success' ? '✓' : (type === 'warning' ? '⚠️' : 'ℹ️');
      toast.className = `hp-global-toast hp-toast-${type} active`;
      toast.innerHTML = `<span class="hp-toast-icon">${icon}</span> <span class="hp-toast-text">${this.escape(message)}</span>`;

      clearTimeout(this._toastTimer);
      this._toastTimer = setTimeout(() => {
        toast.classList.remove('active');
      }, 2500);
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
