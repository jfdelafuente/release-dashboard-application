/**
 * Monitor de Incidencias de Alta Prioridad - Cockpit Incident Manager
 * Feature: 013-incident-manager-monitor
 * 
 * Gestiona la carga híbrida de incidencias activas, cálculo de KPIs en vivo,
 * copia de prompts para incident-reporter en 1 clic y validación reactiva de palabras
 * para la persistencia de mensajes ejecutivos oficiales.
 */

(function () {
  'use strict';

  // --- Estado de la Aplicación ---
  const state = {
    kpis: {
      total_active: 0,
      completed_count: 0,
      pending_count: 0,
      p1_count: 0,
      p2_count: 0,
      discrepancies_count: 0,
      generated_at: '',
      source_file: ''
    },
    pendingIncidents: [],
    completedIncidents: [],
    allIncidents: [],
    activeView: 'pending', // 'pending' | 'all'
    filters: {
      severity: 'all',
      process: 'all',
      onlyDiscrepancies: false,
      search: ''
    },
    // Guarda la fase seleccionada por cada incidencia { [incId]: 'apertura' | 'seguimiento' | 'cierre' }
    activePhases: {},
    // Textos temporales ingresados en el asistente de ingesta { [incId]: { completo: '', breve: '' } }
    ingestaDrafts: {},
    refreshIntervalMs: 30000,
    refreshTimer: null,
    searchDebounceTimer: null
  };

  // --- Elementos del DOM ---
  const dom = {
    connStatusPill: document.getElementById('conn-status-pill'),
    connStatusText: document.getElementById('conn-status-text'),
    autoRefreshSelect: document.getElementById('auto-refresh-select'),
    btnManualRefresh: document.getElementById('btn-manual-refresh'),
    lastSyncTimestamp: document.getElementById('last-sync-timestamp'),

    // KPIs
    kpiCardPending: document.getElementById('kpi-card-pending'),
    kpiPendingCount: document.getElementById('kpi-pending-count'),
    kpiPendingFooter: document.getElementById('kpi-pending-footer'),
    kpiCompletedCount: document.getElementById('kpi-completed-count'),
    kpiTotalActive: document.getElementById('kpi-total-active'),
    kpiSourceFile: document.getElementById('kpi-source-file'),
    kpiP1Count: document.getElementById('kpi-p1-count'),
    kpiP2Count: document.getElementById('kpi-p2-count'),
    kpiDiscrepanciesCount: document.getElementById('kpi-discrepancies-count'),

    // Tabs y Badges
    tabViewPending: document.getElementById('tab-view-pending'),
    tabViewAll: document.getElementById('tab-view-all'),
    badgeCountPending: document.getElementById('badge-count-pending'),
    badgeCountAll: document.getElementById('badge-count-all'),

    // Filtros
    filterSearchInput: document.getElementById('filter-search-input'),
    filterSeveritySelect: document.getElementById('filter-severity-select'),
    filterProcessSelect: document.getElementById('filter-process-select'),
    filterOnlyDiscrepancies: document.getElementById('filter-only-discrepancies'),

    // Contenedores
    queueContainer: document.getElementById('queue-container'),
    emptyStateContainer: document.getElementById('empty-state-container'),
    emptyStateTitle: document.getElementById('empty-state-title'),
    emptyStateDesc: document.getElementById('empty-state-desc'),
    toastContainer: document.getElementById('im-toast-container'),
    srAnnouncements: document.getElementById('sr-announcements')
  };

  // --- Utilidades de Accesibilidad y Notificaciones ---

  function announceSR(message) {
    if (dom.srAnnouncements) {
      dom.srAnnouncements.textContent = '';
      setTimeout(() => {
        dom.srAnnouncements.textContent = message;
      }, 50);
    }
  }

  function showToast(message, type = 'info') {
    if (!dom.toastContainer) return;
    const toast = document.createElement('div');
    toast.className = `im-toast toast-${type}`;
    toast.setAttribute('role', 'alert');

    const icon = type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️';
    toast.innerHTML = `<span aria-hidden="true">${icon}</span><span>${escapeHtml(message)}</span>`;

    dom.toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      setTimeout(() => toast.remove(), 250);
    }, 3500);
  }

  function escapeHtml(str) {
    if (typeof str !== 'string') return '';
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function setConnectionStatus(status, text) {
    if (!dom.connStatusPill || !dom.connStatusText) return;
    dom.connStatusPill.className = `im-status-pill status-${status}`;
    dom.connStatusText.textContent = text;
  }

  function countWords(str) {
    if (!str || typeof str !== 'string') return 0;
    const clean = str.trim();
    if (!clean) return 0;
    return clean.split(/\s+/).length;
  }

  // --- Carga de Datos (Híbrida: API con Fallback Estático) ---

  async function loadData(showLoadingIndicator = true) {
    if (showLoadingIndicator) {
      setConnectionStatus('syncing', 'Sincronizando...');
    }

    try {
      // 1. Intentar endpoint API oficial
      const res = await fetch('/api/incident-manager/pending?t=' + Date.now());
      if (res.ok) {
        const payload = await res.json();
        processApiPayload(payload);
        setConnectionStatus('connected', 'Conectado');
        updateLastSyncTime();
        return;
      }
    } catch (_) {
      // Fallback a archivos estáticos
    }

    // 2. Fallback estático directo si la API no está disponible (ej. Nginx puro sin proxy Python)
    try {
      const [catRes, storeRes] = await Promise.all([
        fetch('/data/output/high_priority_notifications.json?t=' + Date.now()),
        fetch('/data/agent_executive_messages.json?t=' + Date.now()).catch(() => null)
      ]);

      if (!catRes.ok) {
        throw new Error(`No se pudo cargar el catálogo de notificaciones (${catRes.status})`);
      }

      const catalogData = await catRes.json();
      let storeData = { incidents: {} };
      if (storeRes && storeRes.ok) {
        storeData = await storeRes.json();
      }

      processStaticFiles(catalogData, storeData);
      setConnectionStatus('connected', 'Conectado (Estático)');
      updateLastSyncTime();
    } catch (err) {
      console.error('Error cargando incidencias:', err);
      setConnectionStatus('error', 'Sin conexión');
      showToast('Error al conectar con el almacén de datos: ' + err.message, 'error');
    }
  }

  function processApiPayload(payload) {
    state.kpis = payload.kpis || state.kpis;
    state.pendingIncidents = payload.pending_incidents || [];
    state.completedIncidents = payload.completed_incidents || [];
    state.allIncidents = payload.all_active_incidents || [
      ...state.pendingIncidents,
      ...state.completedIncidents
    ];

    renderAll();
  }

  function processStaticFiles(catalogData, storeData) {
    const rawIncidents = catalogData.data || catalogData.incidents || [];
    const storeIncidents = storeData.incidents || {};

    const pending = [];
    const completed = [];
    const all = [];

    let p1 = 0;
    let p2 = 0;
    let discrepancies = 0;

    rawIncidents.forEach((raw) => {
      const inc = { ...raw };
      const incId = inc.id;
      const prio = inc.prioridad_sugerida || 'P2';

      if (prio === 'P1') p1++;
      else if (prio === 'P2') p2++;

      if (inc.es_discrepancia) discrepancies++;

      const mensajes = inc.mensajes_ejecutivos || {};
      const apertura = mensajes.apertura || {};
      const storeEntry = storeIncidents[incId]?.apertura || {};
      const inStore = !!(storeEntry.completo && storeEntry.generado_por_agente !== false);

      const isPending = (
        apertura.estado === 'pendiente' ||
        !apertura.completo ||
        !inStore
      );

      inc.is_pending = isPending;
      all.push(inc);

      if (isPending) {
        pending.push(inc);
      } else {
        completed.push(inc);
      }
    });

    state.kpis = {
      total_active: all.length,
      completed_count: completed.length,
      pending_count: pending.length,
      p1_count: p1,
      p2_count: p2,
      discrepancies_count: discrepancies,
      generated_at: catalogData._metadata?.generated_at || '',
      source_file: catalogData._metadata?.source_file || ''
    };

    state.pendingIncidents = pending;
    state.completedIncidents = completed;
    state.allIncidents = all;

    renderAll();
  }

  function updateLastSyncTime() {
    const now = new Date();
    const timeStr = now.toLocaleTimeString('es-ES', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
    if (dom.lastSyncTimestamp) {
      dom.lastSyncTimestamp.textContent = timeStr;
    }
  }

  // --- Renderizado Completo ---

  function renderAll() {
    renderKPIs();
    renderToolbarCounts();
    renderQueue();
  }

  function renderKPIs() {
    const k = state.kpis;
    if (dom.kpiPendingCount) dom.kpiPendingCount.textContent = k.pending_count;
    if (dom.kpiCompletedCount) dom.kpiCompletedCount.textContent = k.completed_count;
    if (dom.kpiTotalActive) dom.kpiTotalActive.textContent = k.total_active;
    if (dom.kpiP1Count) dom.kpiP1Count.textContent = k.p1_count;
    if (dom.kpiP2Count) dom.kpiP2Count.textContent = k.p2_count;
    if (dom.kpiDiscrepanciesCount) dom.kpiDiscrepanciesCount.textContent = k.discrepancies_count;

    if (dom.kpiCardPending) {
      if (k.pending_count > 0) {
        dom.kpiCardPending.className = 'kpi-card kpi-pending-active';
        if (dom.kpiPendingFooter) {
          dom.kpiPendingFooter.textContent = `🚨 ${k.pending_count} ${k.pending_count === 1 ? 'incidencia requiere' : 'incidencias requieren'} redacción de agente`;
        }
      } else {
        dom.kpiCardPending.className = 'kpi-card kpi-pending-clean';
        if (dom.kpiPendingFooter) {
          dom.kpiPendingFooter.textContent = '✅ Sin redacciones pendientes';
        }
      }
    }

    if (dom.kpiSourceFile && k.source_file) {
      dom.kpiSourceFile.textContent = k.source_file.split('-massive.json')[0] || k.source_file;
      dom.kpiSourceFile.title = k.source_file;
    }
  }

  function renderToolbarCounts() {
    if (dom.badgeCountPending) {
      dom.badgeCountPending.textContent = state.pendingIncidents.length;
    }
    if (dom.badgeCountAll) {
      dom.badgeCountAll.textContent = state.allIncidents.length;
    }
  }

  function getFilteredIncidents() {
    const sourceList = state.activeView === 'pending'
      ? state.pendingIncidents
      : state.allIncidents;

    const { severity, process, onlyDiscrepancies, search } = state.filters;
    const q = search.trim().toLowerCase();

    return sourceList.filter((inc) => {
      // 1. Filtro de Severidad
      if (severity !== 'all' && inc.prioridad_sugerida !== severity) {
        return false;
      }

      // 2. Filtro de Proceso de Negocio
      const proc = inc.evaluacion?.proceso || '';
      if (process !== 'all' && proc !== process) {
        return false;
      }

      // 3. Filtro Solo Discrepancias
      if (onlyDiscrepancies && !inc.es_discrepancia) {
        return false;
      }

      // 4. Búsqueda libre
      if (q) {
        const id = (inc.id || '').toLowerCase();
        const titulo = (inc.titulo || '').toLowerCase();
        const sistemas = (inc.sistemas || []).join(' ').toLowerCase();
        if (!id.includes(q) && !titulo.includes(q) && !sistemas.includes(q)) {
          return false;
        }
      }

      return true;
    });
  }

  function renderQueue() {
    if (!dom.queueContainer || !dom.emptyStateContainer) return;

    const incidents = getFilteredIncidents();

    if (incidents.length === 0) {
      dom.queueContainer.innerHTML = '';
      dom.emptyStateContainer.style.display = 'flex';

      if (state.activeView === 'pending' && state.pendingIncidents.length === 0) {
        dom.emptyStateTitle.textContent = '✅ Sin redacciones pendientes';
        dom.emptyStateDesc.textContent =
          'Todas las incidencias de alta prioridad activas cuentan con mensajes ejecutivos oficiales generados.';
      } else {
        dom.emptyStateTitle.textContent = '🔍 No se encontraron incidencias';
        dom.emptyStateDesc.textContent =
          'Ninguna incidencia coincide con los filtros aplicados en esta vista.';
      }
      return;
    }

    dom.emptyStateContainer.style.display = 'none';

    const frag = document.createDocumentFragment();
    incidents.forEach((inc) => {
      const card = createIncidentCardElement(inc);
      frag.appendChild(card);
    });

    dom.queueContainer.innerHTML = '';
    dom.queueContainer.appendChild(frag);
  }

  // --- Creación de Tarjeta de Incidencia ---

  function createIncidentCardElement(inc) {
    const isP1 = inc.prioridad_sugerida === 'P1';
    const borderClass = isP1 ? 'border-p1' : 'border-p2';
    const badgeClass = isP1 ? 'badge-p1' : 'badge-p2';
    const badgeText = isP1 ? 'P1 · Crítica' : 'P2 · Alta';

    const incId = inc.id || 'INC000000000000';
    const activePhase = state.activePhases[incId] || 'apertura';

    const card = document.createElement('article');
    card.className = `incident-card ${borderClass}`;
    card.id = `card-${incId}`;
    card.setAttribute('aria-labelledby', `title-${incId}`);

    // Contexto evaluado
    const evaluacion = inc.evaluacion || {};
    const proceso = evaluacion.proceso || 'No clasificado';
    const criterio = evaluacion.criterio || 'Sin criterio asignado';
    const sla = evaluacion.sla_objetivo_minutos ? `${evaluacion.sla_objetivo_minutos} min` : '60 min';
    const sistemas = (inc.sistemas && inc.sistemas.length > 0)
      ? inc.sistemas.map((s) => `<span class="context-systems">${escapeHtml(s)}</span>`).join(' ')
      : '<span class="context-systems">N/A</span>';

    // Discrepancia badge
    let discrepancyHtml = '';
    if (inc.es_discrepancia) {
      const nom = inc.prioridad_original || 'P3';
      discrepancyHtml = `<span class="badge badge-discrepancy" title="Regla de Oro N1: Ticket nominalmente ${escapeHtml(nom)} elevado a ${inc.prioridad_sugerida}">⚠️ Subescalación (${escapeHtml(nom)} → ${inc.prioridad_sugerida})</span>`;
    }

    // Epsilon IA status & button
    const hasEpsilon = Boolean(inc.tiene_epsilon && inc.resumen_ia);
    const epsilonBtnHtml = hasEpsilon
      ? `<button type="button" class="im-btn im-btn-secondary im-btn-sm btn-open-epsilon" data-inc="${escapeHtml(incId)}">
           <span aria-hidden="true">🤖</span> Ver Resumen Epsilon
         </button>`
      : `<span style="font-size: 11px; color: var(--im-text-muted); font-style: italic;">ℹ️ Solo metadatos Remedy</span>`;

    // Prompt actual de la fase
    const promptText = getPromptForPhase(inc, activePhase);

    // Contenido HTML de la tarjeta
    card.innerHTML = `
      <div class="incident-card-header">
        <div class="incident-card-badges">
          <span class="badge ${badgeClass}">${badgeText}</span>
          ${discrepancyHtml}
          <span class="badge badge-status">Remedy: ${escapeHtml(inc.estatus || 'En curso')}</span>
          <span class="badge" style="background:#F1F5F9; color:#0F172A; font-family:var(--im-font-mono);">SLA: ${sla}</span>
        </div>
        <div style="display:flex; align-items:center; gap:12px;">
          <a href="#" class="incident-id-link" title="Abrir en BMC Remedy">${escapeHtml(incId)}</a>
          <span class="incident-timing" title="Fecha de envío">${escapeHtml(inc.fecha_envio || 'Reciente')}</span>
        </div>
      </div>

      <h2 id="title-${escapeHtml(incId)}" class="incident-title">${escapeHtml(inc.titulo || 'Sin título registrado')}</h2>

      <div class="incident-context-block">
        <div class="context-row">
          <span class="context-label">Proceso Crítico:</span>
          <span class="context-tag-process">${escapeHtml(proceso)}</span>
          <span class="context-label" style="min-width:auto; margin-left:10px;">Sistemas:</span>
          ${sistemas}
        </div>
        <div class="context-row">
          <span class="context-label">Criterio ITIL:</span>
          <span class="context-criterion">${escapeHtml(criterio)}</span>
        </div>
      </div>

      <div class="incident-actions-row">
        <div>${epsilonBtnHtml}</div>
        <div style="font-size:11px; color:var(--im-text-muted);">
          ${inc.is_pending ? '⚠️ <strong style="color:var(--im-p1-red);">Pendiente de redacción de agente</strong>' : '✅ <strong style="color:var(--im-green-success);">Mensaje oficial aprobado</strong>'}
        </div>
      </div>

      <!-- Panel de Redacción de Agente -->
      <section class="agent-panel" aria-label="Espacio de Redacción para ${escapeHtml(incId)}">
        <div class="agent-panel-header">
          <div class="phase-tabs" role="tablist" aria-label="Fases de comunicación">
            <button type="button" class="phase-tab-btn ${activePhase === 'apertura' ? 'active' : ''}" data-phase="apertura" data-inc="${escapeHtml(incId)}">Apertura</button>
            <button type="button" class="phase-tab-btn ${activePhase === 'seguimiento' ? 'active' : ''}" data-phase="seguimiento" data-inc="${escapeHtml(incId)}">Seguimiento</button>
            <button type="button" class="phase-tab-btn ${activePhase === 'cierre' ? 'active' : ''}" data-phase="cierre" data-inc="${escapeHtml(incId)}">Cierre</button>
          </div>
          <span style="font-size:11px; color:var(--im-text-muted);">Agente: <strong>incident-reporter</strong> (≤90 y ≤30 palabras)</span>
        </div>

        <div class="prompt-box-container">
          <pre class="prompt-code-block" id="prompt-block-${escapeHtml(incId)}">${escapeHtml(promptText)}</pre>
          <div class="prompt-copy-bar">
            <button type="button" class="im-btn im-btn-primary im-btn-sm btn-copy-prompt" data-inc="${escapeHtml(incId)}">
              <span aria-hidden="true">📋</span> Copiar Prompt para el Agente
            </button>
          </div>
        </div>

        <!-- Asistente de Ingesta Oficial -->
        <div class="ingesta-assistant" id="ingesta-${escapeHtml(incId)}">
          <div class="ingesta-title-row" id="toggle-ingesta-${escapeHtml(incId)}" data-inc="${escapeHtml(incId)}">
            <span>✍️ Asistente de Ingesta Oficial (Fase: <span class="active-phase-label">${escapeHtml(capitalize(activePhase))}</span>)</span>
            <span class="ingesta-toggle-icon" aria-hidden="true">▼</span>
          </div>

          <div class="ingesta-body" id="ingesta-body-${escapeHtml(incId)}">
            <div class="ingesta-field-group">
              <div class="ingesta-field-header">
                <label for="comp-input-${escapeHtml(incId)}">Versión Completa para Dirección (Único párrafo):</label>
                <span class="word-counter-chip valid" id="counter-comp-${escapeHtml(incId)}">0/90 palabras</span>
              </div>
              <textarea id="comp-input-${escapeHtml(incId)}" class="ingesta-textarea" rows="3" placeholder="Pega la versión completa devuelta por el agente (máximo 90 palabras en un solo párrafo)..." data-inc="${escapeHtml(incId)}" data-type="completo"></textarea>
            </div>

            <div class="ingesta-field-group">
              <div class="ingesta-field-header">
                <label for="brev-input-${escapeHtml(incId)}">Versión Breve para Alertas:</label>
                <span class="word-counter-chip valid" id="counter-brev-${escapeHtml(incId)}">0/30 palabras</span>
              </div>
              <textarea id="brev-input-${escapeHtml(incId)}" class="ingesta-textarea" rows="2" placeholder="Pega la versión breve devuelta por el agente (máximo 30 palabras)..." data-inc="${escapeHtml(incId)}" data-type="breve"></textarea>
            </div>

            <div class="ingesta-actions-bar">
              <button type="button" class="im-btn im-btn-secondary im-btn-sm btn-copy-cli" data-inc="${escapeHtml(incId)}" title="Generar sintaxis CLI de update_agent_message.py">
                <span aria-hidden="true">💻</span> Copiar Comando CLI
              </button>
              <button type="button" class="im-btn im-btn-primary im-btn-sm btn-save-official" data-inc="${escapeHtml(incId)}">
                <span aria-hidden="true">💾</span> Guardar en Almacén Oficial
              </button>
            </div>
          </div>
        </div>
      </section>
    `;

    // Vincular listeners en esta tarjeta
    bindCardEvents(card, inc);

    return card;
  }

  function capitalize(str) {
    if (!str) return '';
    return str.charAt(0).toUpperCase() + str.slice(1);
  }

  function getPromptForPhase(inc, phase) {
    if (inc.mensajes_ejecutivos && inc.mensajes_ejecutivos[phase] && inc.mensajes_ejecutivos[phase].prompt_agente) {
      return inc.mensajes_ejecutivos[phase].prompt_agente;
    }
    if (inc.prompts_agente && inc.prompts_agente[phase]) {
      return inc.prompts_agente[phase];
    }

    // Generador dinámico en cliente si no venía precalculado
    const evaluacion = inc.evaluacion || {};
    const proceso = evaluacion.proceso || 'Sistemas Core';
    const criterio = evaluacion.criterio || 'SL2 Mayor';
    const sistemas = (inc.sistemas || []).join(', ') || 'Sistemas';

    return `Actúa como el agente incident-reporter de MasOrange para la fase de ${phase.toUpperCase()}.
Redacta la comunicación ejecutiva para Dirección sobre la incidencia ${inc.id} (${inc.prioridad_sugerida}).
Proceso Crítico: ${proceso} | Criterio: ${criterio} | Sistemas: ${sistemas}
Título/Afectación: ${inc.titulo}
Instrucciones estrictas:
1. Versión Completa: máximo 90 palabras en un ÚNICO párrafo cohesionado.
2. Versión Breve: máximo 30 palabras para canal de alertas.
3. No inventes causas raíz ni métricas ausentes.`;
  }

  // --- Asignación de Eventos en Tarjeta ---

  function bindCardEvents(card, inc) {
    const incId = inc.id;

    // 1. Selector de Pestañas de Fase
    const phaseBtns = card.querySelectorAll('.phase-tab-btn');
    phaseBtns.forEach((btn) => {
      btn.addEventListener('click', () => {
        const selectedPhase = btn.getAttribute('data-phase');
        state.activePhases[incId] = selectedPhase;

        phaseBtns.forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');

        // Actualizar bloque de prompt
        const promptBlock = card.querySelector(`#prompt-block-${incId}`);
        if (promptBlock) {
          promptBlock.textContent = getPromptForPhase(inc, selectedPhase);
        }

        // Actualizar etiqueta en asistente de ingesta
        const phaseLabel = card.querySelector('.active-phase-label');
        if (phaseLabel) {
          phaseLabel.textContent = capitalize(selectedPhase);
        }
      });
    });

    // 2. Botón Copiar Prompt
    const copyPromptBtn = card.querySelector('.btn-copy-prompt');
    if (copyPromptBtn) {
      copyPromptBtn.addEventListener('click', async () => {
        const currentPhase = state.activePhases[incId] || 'apertura';
        const promptText = getPromptForPhase(inc, currentPhase);

        try {
          await navigator.clipboard.writeText(promptText);
          const origText = copyPromptBtn.innerHTML;
          copyPromptBtn.innerHTML = '✅ ¡Prompt copiado!';
          copyPromptBtn.style.background = 'var(--im-green-success)';
          copyPromptBtn.style.borderColor = 'var(--im-green-success)';

          announceSR(`Prompt de ${currentPhase} para ${incId} copiado al portapapeles.`);
          showToast(`¡Prompt de ${currentPhase} copiado! Pégalo en tu sesión de Agente.`);

          setTimeout(() => {
            copyPromptBtn.innerHTML = origText;
            copyPromptBtn.style.background = '';
            copyPromptBtn.style.borderColor = '';
          }, 2000);
        } catch (err) {
          showToast('No se pudo copiar automáticamente: ' + err.message, 'error');
        }
      });
    }

    // 3. Botón Modal Epsilon IA
    const epsilonBtn = card.querySelector('.btn-open-epsilon');
    if (epsilonBtn) {
      epsilonBtn.addEventListener('click', () => {
        if (typeof window.openResumenIA === 'function') {
          window.openResumenIA(incId);
        } else {
          showToast('El visor de Epsilon IA no está disponible en este momento.', 'error');
        }
      });
    }

    // 4. Validación Reactiva de Palabras en Ingesta
    const compTextarea = card.querySelector(`#comp-input-${incId}`);
    const brevTextarea = card.querySelector(`#brev-input-${incId}`);
    const counterComp = card.querySelector(`#counter-comp-${incId}`);
    const counterBrev = card.querySelector(`#counter-brev-${incId}`);

    function updateWordCounters() {
      const compText = compTextarea ? compTextarea.value : '';
      const brevText = brevTextarea ? brevTextarea.value : '';

      const compWords = countWords(compText);
      const brevWords = countWords(brevText);

      if (counterComp) {
        if (compWords > 90) {
          counterComp.className = 'word-counter-chip invalid';
          counterComp.textContent = `${compWords}/90 palabras (Excede límite)`;
        } else {
          counterComp.className = 'word-counter-chip valid';
          counterComp.textContent = `${compWords}/90 palabras`;
        }
      }

      if (counterBrev) {
        if (brevWords > 30) {
          counterBrev.className = 'word-counter-chip invalid';
          counterBrev.textContent = `${brevWords}/30 palabras (Excede límite)`;
        } else {
          counterBrev.className = 'word-counter-chip valid';
          counterBrev.textContent = `${brevWords}/30 palabras`;
        }
      }

      // Guardar borrador en memoria
      state.ingestaDrafts[incId] = {
        completo: compText,
        breve: brevText
      };
    }

    if (compTextarea) compTextarea.addEventListener('input', updateWordCounters);
    if (brevTextarea) brevTextarea.addEventListener('input', updateWordCounters);

    // Restaurar borrador si existía
    if (state.ingestaDrafts[incId]) {
      if (compTextarea) compTextarea.value = state.ingestaDrafts[incId].completo || '';
      if (brevTextarea) brevTextarea.value = state.ingestaDrafts[incId].breve || '';
      updateWordCounters();
    }

    // 5. Botón Copiar Comando CLI (Mecanismo de contingencia)
    const copyCliBtn = card.querySelector('.btn-copy-cli');
    if (copyCliBtn) {
      copyCliBtn.addEventListener('click', async () => {
        const currentPhase = state.activePhases[incId] || 'apertura';
        const compVal = compTextarea ? compTextarea.value.trim() : '';
        const brevVal = brevTextarea ? brevTextarea.value.trim() : '';

        // Normalizar comillas para CLI
        const cleanComp = compVal.replace(/"/g, '\\"');
        const cleanBrev = brevVal.replace(/"/g, '\\"');

        const cliCmd = `python converters/cli/update_agent_message.py --id ${incId} --phase ${currentPhase} --completo "${cleanComp}" --breve "${cleanBrev}"`;

        try {
          await navigator.clipboard.writeText(cliCmd);
          announceSR(`Comando CLI para ${incId} copiado al portapapeles.`);
          showToast('¡Comando CLI copiado! Puedes ejecutarlo directamente en PowerShell/Terminal.');
        } catch (err) {
          showToast('Error al copiar comando CLI: ' + err.message, 'error');
        }
      });
    }

    // 6. Botón Guardar en Almacén Oficial
    const saveOfficialBtn = card.querySelector('.btn-save-official');
    if (saveOfficialBtn) {
      saveOfficialBtn.addEventListener('click', async () => {
        const currentPhase = state.activePhases[incId] || 'apertura';
        const compVal = compTextarea ? compTextarea.value.trim() : '';
        const brevVal = brevTextarea ? brevTextarea.value.trim() : '';

        if (!compVal) {
          showToast('Debes ingresar la versión completa para Dirección.', 'error');
          if (compTextarea) compTextarea.focus();
          return;
        }

        if (!brevVal) {
          showToast('Debes ingresar la versión breve para alertas.', 'error');
          if (brevTextarea) brevTextarea.focus();
          return;
        }

        const compWords = countWords(compVal);
        const brevWords = countWords(brevVal);

        if (compWords > 90) {
          showToast(`La versión completa excede el límite permitido: ${compWords}/90 palabras.`, 'error');
          return;
        }

        if (brevWords > 30) {
          showToast(`La versión breve excede el límite permitido: ${brevWords}/30 palabras.`, 'error');
          return;
        }

        // Enviar POST a la API
        const origBtnText = saveOfficialBtn.innerHTML;
        saveOfficialBtn.disabled = true;
        saveOfficialBtn.innerHTML = '⏳ Guardando...';

        try {
          const res = await fetch('/api/incident-manager/save-message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json; charset=utf-8' },
            body: JSON.stringify({
              incident_id: incId,
              phase: currentPhase,
              completo: compVal,
              breve: brevVal,
              origen: 'incident-reporter'
            })
          });

          const data = await res.json();
          if (res.ok && data.success) {
            showToast(`¡Mensaje oficial de ${currentPhase} guardado con éxito para ${incId}!`, 'success');
            announceSR(`Mensaje oficial guardado con éxito.`);
            // Limpiar borrador y refrescar
            delete state.ingestaDrafts[incId];
            await loadData(false);
          } else {
            throw new Error(data.error || 'Respuesta insatisfactoria del servidor.');
          }
        } catch (err) {
          console.error('Error guardando mensaje:', err);
          showToast(`Fallo al guardar vía API: ${err.message}. Usa el botón "Copiar Comando CLI" como contingencia.`, 'error');
        } finally {
          saveOfficialBtn.disabled = false;
          saveOfficialBtn.innerHTML = origBtnText;
        }
      });
    }
  }

  // --- Manejo de Filtros y Vistas ---

  function setupEventListeners() {
    // 1. Selector de Vistas: Solo Pendientes vs Todas
    if (dom.tabViewPending) {
      dom.tabViewPending.addEventListener('click', () => {
        state.activeView = 'pending';
        dom.tabViewPending.classList.add('active');
        dom.tabViewPending.setAttribute('aria-selected', 'true');
        dom.tabViewAll.classList.remove('active');
        dom.tabViewAll.setAttribute('aria-selected', 'false');
        renderQueue();
      });
    }

    if (dom.tabViewAll) {
      dom.tabViewAll.addEventListener('click', () => {
        state.activeView = 'all';
        dom.tabViewAll.classList.add('active');
        dom.tabViewAll.setAttribute('aria-selected', 'true');
        dom.tabViewPending.classList.remove('active');
        dom.tabViewPending.setAttribute('aria-selected', 'false');
        renderQueue();
      });
    }

    // 2. Buscador en tiempo real con Debounce
    if (dom.filterSearchInput) {
      dom.filterSearchInput.addEventListener('input', (e) => {
        clearTimeout(state.searchDebounceTimer);
        state.searchDebounceTimer = setTimeout(() => {
          state.filters.search = e.target.value;
          renderQueue();
        }, 150);
      });
    }

    // 3. Filtro Severidad
    if (dom.filterSeveritySelect) {
      dom.filterSeveritySelect.addEventListener('change', (e) => {
        state.filters.severity = e.target.value;
        renderQueue();
      });
    }

    // 4. Filtro Proceso
    if (dom.filterProcessSelect) {
      dom.filterProcessSelect.addEventListener('change', (e) => {
        state.filters.process = e.target.value;
        renderQueue();
      });
    }

    // 5. Filtro Solo Discrepancias
    if (dom.filterOnlyDiscrepancies) {
      dom.filterOnlyDiscrepancies.addEventListener('change', (e) => {
        state.filters.onlyDiscrepancies = e.target.checked;
        renderQueue();
      });
    }

    // 6. Refresco Manual
    if (dom.btnManualRefresh) {
      dom.btnManualRefresh.addEventListener('click', () => {
        loadData(true);
        showToast('Sincronizando catálogo con almacén oficial...');
      });
    }

    // 7. Auto-Refresco
    if (dom.autoRefreshSelect) {
      dom.autoRefreshSelect.addEventListener('change', (e) => {
        const interval = parseInt(e.target.value, 10);
        state.refreshIntervalMs = interval;
        setupAutoRefresh();
      });
    }
  }

  function setupAutoRefresh() {
    if (state.refreshTimer) {
      clearInterval(state.refreshTimer);
      state.refreshTimer = null;
    }

    if (state.refreshIntervalMs > 0) {
      state.refreshTimer = setInterval(() => {
        loadData(false);
      }, state.refreshIntervalMs);
    }
  }

  // --- Inicialización ---

  function init() {
    setupEventListeners();
    setupAutoRefresh();
    loadData(true);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();

