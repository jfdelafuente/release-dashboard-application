/**
 * Consola de Triaje y Reclasificación Automática (SL1/P1 & SL2/P2)
 * Módulo 1: Motor de Inspección Continua, Umbrales Críticos y Alertas de Subescalación
 * Orange Tech Operations · Incident Management
 */

(function () {
  'use strict';

  // --- Estado Global de la Consola ---
  const state = {
    metadata: {
      source_file: '',
      generated_at: '',
      kpis: {
        total_scanned: 0,
        terminal_skipped_count: 0,
        active_evaluated_count: 0,
        total_high_priority: 0,
        p1_critical_count: 0,
        p2_high_count: 0,
        discrepancies_count: 0,
        discrepancias_delta1_moderada_count: 0,
        discrepancias_delta2_mayor_count: 0,
        discrepancias_delta3_critica_count: 0
      }
    },
    incidents: [],
    activeFilter: 'reclass_only', // 'all' | 'reclass_only' | 'correct_only'
    processFilter: 'all',
    severityFilter: 'all',
    searchQuery: '',
    expandedEpsilon: {}, // { [incId]: boolean }
    lastInspectionEpoch: 0,
    refreshIntervalMs: 30000,
    refreshTimer: null,
    relativeTimer: null
  };

  // --- Referencias del DOM ---
  const dom = {
    // Conexión y Control
    livePill: document.getElementById('live-pill'),
    liveStatusText: document.getElementById('live-status-text'),
    autoRefreshSelect: document.getElementById('auto-refresh-select'),
    btnRefreshNow: document.getElementById('btn-refresh-now'),
    btnHelpCriteria: document.getElementById('btn-help-criteria'),

    // Metadatos de Inspección
    sourceFileName: document.getElementById('source-file-name'),
    lastScanLabel: document.getElementById('last-scan-label'),
    kpiScanned: document.getElementById('kpi-scanned'),
    kpiSkipped: document.getElementById('kpi-skipped'),
    kpiActive: document.getElementById('kpi-active'),
    kpiEmergencies: document.getElementById('kpi-emergencies'),

    // Banner de Alerta Reclasificación
    reclassBanner: document.getElementById('reclass-banner'),
    reclassCountBadge: document.getElementById('reclass-count-badge'),
    reclassDelta2Badge: document.getElementById('reclass-delta2-badge'),
    reclassDelta1Badge: document.getElementById('reclass-delta1-badge'),

    // Controles de Filtrado
    tabAll: document.getElementById('tab-all'),
    tabReclassOnly: document.getElementById('tab-reclass-only'),
    tabCorrectOnly: document.getElementById('tab-correct-only'),
    countAll: document.getElementById('count-all'),
    countReclass: document.getElementById('count-reclass'),
    countCorrect: document.getElementById('count-correct'),
    filterProcessSelect: document.getElementById('filter-process'),
    filterSeveritySelect: document.getElementById('filter-severity'),
    searchInput: document.getElementById('search-input'),

    // Feed de Incidentes
    triageFeed: document.getElementById('triage-feed'),

    // Modal y Toast
    modalBackdrop: document.getElementById('modal-criteria'),
    btnModalClose: document.getElementById('btn-modal-close'),
    toastContainer: document.getElementById('toast-container'),
    srAnnouncements: document.getElementById('sr-announcements')
  };

  // --- Utilidades ---

  function escapeHtml(str) {
    if (typeof str !== 'string') return '';
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function announceSR(msg) {
    if (dom.srAnnouncements) {
      dom.srAnnouncements.textContent = msg;
    }
  }

  function showToast(message, type = 'info') {
    if (!dom.toastContainer) return;
    const toast = document.createElement('div');
    toast.className = `triage-toast ${type}`;
    const icon = type === 'success' ? '✅' : (type === 'error' ? '❌' : 'ℹ️');
    toast.innerHTML = `<span aria-hidden="true">${icon}</span><span>${escapeHtml(message)}</span>`;
    dom.toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(12px)';
      toast.style.transition = 'all 0.25s ease';
      setTimeout(() => toast.remove(), 250);
    }, 3500);
  }

  function copyToClipboard(text, successMsg) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(() => {
        showToast(successMsg, 'success');
        announceSR(successMsg);
      }).catch(err => {
        console.warn('Fallback copy due to clipboard writeText error:', err);
        fallbackCopy(text, successMsg);
      });
    } else {
      fallbackCopy(text, successMsg);
    }
  }

  function fallbackCopy(text, successMsg) {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.select();
    try {
      document.execCommand('copy');
      showToast(successMsg, 'success');
      announceSR(successMsg);
    } catch (_) {
      showToast('No se pudo copiar automáticamente. Por favor, selecciona y copia el texto manualmente.', 'error');
    }
    document.body.removeChild(textarea);
  }

  function formatRelativeTime(epochMs) {
    if (!epochMs) return 'Pendiente de escaneo';
    const seconds = Math.floor((Date.now() - epochMs) / 1000);
    if (seconds < 5) return 'Hace unos instantes';
    if (seconds < 60) return `Hace ${seconds}s`;
    const mins = Math.floor(seconds / 60);
    if (mins < 60) return `Hace ${mins}m ${seconds % 60}s`;
    const hours = Math.floor(mins / 60);
    return `Hace ${hours}h ${mins % 60}m`;
  }

  function formatAgingMinutes(mins) {
    if (mins == null || isNaN(mins)) return 'Reciente';
    if (mins < 60) return `${mins}m activa`;
    const h = Math.floor(mins / 60);
    const m = mins % 60;
    if (h < 24) return `${h}h ${m}m activa`;
    const d = Math.floor(h / 24);
    const remH = h % 24;
    return `${d}d ${remH}h activa`;
  }

  function setConnectionStatus(status, text) {
    if (!dom.livePill || !dom.liveStatusText) return;
    dom.livePill.className = `triage-live-pill ${status}`;
    dom.liveStatusText.textContent = text;
  }

  // --------------------------------------------------------------------------
  // Función 1: Ingesta e Inspección Continua
  // --------------------------------------------------------------------------

  async function performInspection(isManual = false) {
    if (isManual) {
      if (dom.btnRefreshNow) {
        dom.btnRefreshNow.disabled = true;
        dom.btnRefreshNow.innerHTML = `<span aria-hidden="true" style="display:inline-block; animation: spin 1s infinite linear;">🔄</span> Inspeccionando...`;
      }
    }
    setConnectionStatus('syncing', 'Inspeccionando...');

    const timestamp = Date.now();
    const candidateUrls = [
      '/data/output/high_priority_notifications.json?t=' + timestamp,
      '../../data/output/high_priority_notifications.json?t=' + timestamp,
      '/api/incident-manager/pending?t=' + timestamp,
      '/api/incident-manager/emergency-cockpit?t=' + timestamp
    ];

    let lastError = null;
    for (const url of candidateUrls) {
      try {
        const res = await fetch(url);
        if (!res.ok) continue;
        const data = await res.json();
        if (data && (data.data || data.incidents || data.all_active_incidents || data.pending_incidents)) {
          processInspectionData(data);
          setConnectionStatus('', 'Inspección Activa');
          state.lastInspectionEpoch = Date.now();
          updateRelativeTimeDisplay();
          if (isManual) {
            showToast('Inspección de catálogo completada exitosamente', 'success');
          }
          if (dom.btnRefreshNow) {
            dom.btnRefreshNow.disabled = false;
            dom.btnRefreshNow.innerHTML = `<span aria-hidden="true">🔄</span> Inspeccionar Ahora`;
          }
          return;
        }
      } catch (err) {
        lastError = err;
      }
    }

    setConnectionStatus('error', 'Error de conexión');
    showToast('Error al inspeccionar catálogo de incidencias: ' + (lastError ? lastError.message : 'No se encontraron datos'), 'error');
    if (dom.btnRefreshNow) {
      dom.btnRefreshNow.disabled = false;
      dom.btnRefreshNow.innerHTML = `<span aria-hidden="true">🔄</span> Inspeccionar Ahora`;
    }
  }

  // Estados terminales que no deben entrar al motor de triaje
  const TERMINAL_STATUSES = new Set([
    'cerrado', 'cerrada', 'cerrados', 'cerradas', 'closed', 'close',
    'resuelto', 'resuelta', 'resueltos', 'resueltas', 'resolved', 'resolve',
    'cancelado', 'cancelada', 'cancelados', 'canceladas', 'cancelled', 'canceled', 'cancel'
  ]);

  function isTerminalStatus(status) {
    if (!status) return false;
    const s = String(status).trim().toLowerCase();
    if (TERMINAL_STATUSES.has(s)) return true;
    return s.startsWith('cerrad') || s.startsWith('resuel') || s.startsWith('cancel') || s.startsWith('clos') || s.startsWith('resolv');
  }

  function processInspectionData(payload) {
    state.metadata = payload._metadata || {
      source_file: 'Desconocido',
      generated_at: new Date().toISOString(),
      kpis: {}
    };

    const rawList = payload.data || payload.incidents || payload.all_active_incidents || payload.pending_incidents || [];
    const list = Array.isArray(rawList) ? rawList : Object.values(rawList);
    // Filtrado estricto: las incidencias en estado Cerrado, Resuelto o Canceladas no entran al triaje
    state.incidents = list.filter(inc => !isTerminalStatus(inc.estatus || inc.estado || inc.status));

    // Actualizar KPIs superiores de Ingesta (Foco 100% en Incidencias Activas)
    const kpis = state.metadata.kpis || {};
    if (dom.sourceFileName) {
      dom.sourceFileName.textContent = state.metadata.source_file || 'high_priority_notifications.json';
    }

    const activeCount = (kpis.active_evaluated_count != null) ? kpis.active_evaluated_count : state.incidents.length;
    const discCount = (kpis.discrepancies_count != null) ? kpis.discrepancies_count : state.incidents.filter(i => i.es_discrepancia).length;
    const p1Count = (kpis.p1_critical_count != null) ? kpis.p1_critical_count : state.incidents.filter(i => i.prioridad_sugerida === 'P1').length;
    const p2Count = (kpis.p2_high_count != null) ? kpis.p2_high_count : state.incidents.filter(i => i.prioridad_sugerida === 'P2').length;

    if (dom.kpiScanned) dom.kpiScanned.textContent = activeCount;
    if (dom.kpiSkipped) dom.kpiSkipped.textContent = discCount;
    if (dom.kpiActive) dom.kpiActive.textContent = p1Count;
    if (dom.kpiEmergencies) dom.kpiEmergencies.textContent = p2Count;

    // Actualizar Panel de Alertas de Reclasificación Inmediata
    const delta2Count = (kpis.discrepancias_delta2_mayor_count != null) ? kpis.discrepancias_delta2_mayor_count : state.incidents.filter(i => i.discrepancia_delta === 2).length;
    const delta1Count = (kpis.discrepancias_delta1_moderada_count != null) ? kpis.discrepancias_delta1_moderada_count : state.incidents.filter(i => i.discrepancia_delta === 1).length;

    if (dom.reclassCountBadge) dom.reclassCountBadge.textContent = discCount;
    if (dom.reclassDelta2Badge) dom.reclassDelta2Badge.textContent = `${delta2Count} Mayor Severa (Delta +2)`;
    if (dom.reclassDelta1Badge) dom.reclassDelta1Badge.textContent = `${delta1Count} Moderada (Delta +1)`;

    // Contadores de pestañas de filtrado
    const totalCount = state.incidents.length;
    const correctCount = totalCount - discCount;
    if (dom.countAll) dom.countAll.textContent = totalCount;
    if (dom.countReclass) dom.countReclass.textContent = discCount;
    if (dom.countCorrect) dom.countCorrect.textContent = correctCount;

    // Renderizar Feed de Triaje
    renderFeed();
  }

  function updateRelativeTimeDisplay() {
    if (!dom.lastScanLabel) return;
    const dateFormatted = state.metadata.generated_at
      ? new Date(state.metadata.generated_at).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
      : '--:--';
    const relative = formatRelativeTime(state.lastInspectionEpoch);
    dom.lastScanLabel.textContent = `${relative} (${dateFormatted})`;
  }

  // --------------------------------------------------------------------------
  // Función 3: Generador de Texto Formal de Reclasificación Remedy
  // --------------------------------------------------------------------------

  function buildFormalReclassificationText(inc) {
    const incId = inc.id || 'INC000000000000';
    const titulo = inc.titulo || 'Sin título especificado';
    const sevNominal = inc.prioridad_original || 'Media';
    const sevSugerida = inc.prioridad_sugerida || 'P1';
    const delta = inc.discrepancia_delta || 2;
    const gravedad = inc.discrepancia_gravedad || (delta >= 2 ? 'Mayor Severa' : 'Moderada');

    const evaluacion = inc.evaluacion || {};
    const proceso = evaluacion.proceso || evaluacion.proceso_negocio || 'Procesos Críticos de Negocio';
    const umbral = evaluacion.criterio || 'Regla de Oro N1 (Principio de Precaución)';
    const justificacion = evaluacion.impacto_justificacion || inc.discrepancia_motivo || 'Impacto crítico en servicio y operativa de clientes.';
    const sistemas = Array.isArray(inc.sistemas) ? inc.sistemas.join(', ') : (inc.sistemas || 'Sistemas Core');

    return `[SOLICITUD URGENTE DE RECLASIFICACIÓN REMEDY - CRITERIO PROCESO OPERATIVO GESTIÓN EMERGENCIAS IT ORANGE]
--------------------------------------------------------------------------------
INCIDENCIA: ${incId}
TÍTULO: ${titulo}
PRIORIDAD REMEDY ACTUAL: ${sevNominal}
PRIORIDAD REQUERIDA: ${sevSugerida} (SL1 / P1 - Emergencia Crítica)
DESVÍO DETECTADO: Subescalación ${gravedad} (+${delta} nivel${delta > 1 ? 'es' : ''})

PROCESO CRÍTICO AFECTADO: ${proceso}
UMBRAL DE EMERGENCIA SUPERADO: ${umbral}
SISTEMAS INVOLUCRADOS: ${sistemas}

DICTAMEN Y JUSTIFICACIÓN TÉCNICA (EPSILON IA):
${justificacion}

ACCIÓN REQUERIDA A SERVICE DESK N1 / GRUPO RESOLUTOR:
Reclasificar inmediatamente este ticket a ${sevSugerida} en Remedy para aplicar los tiempos de respuesta de Emergencia, activar el protocolo de escalados con IM-CSO y coordinar la War Room.
--------------------------------------------------------------------------------
Generado por Consola de Emergencias IT Orange - Motor de Triaje (Módulo 1)`;
  }

  function build4BlockEmergencyReport(inc) {
    if (inc.reporte_emergencia) {
      return inc.reporte_emergencia;
    }
    const incId = inc.id || 'INC000000000000';
    const sev = inc.prioridad_sugerida === 'P1' ? 'SL1 (Emergencia Crítica)' : 'SL2 (Mayor)';
    const evaluacion = inc.evaluacion || {};
    const proceso = evaluacion.proceso || 'Atención al Cliente (ATC)';
    const criterio = evaluacion.criterio || 'Regla de Oro N1';
    const justificacion = evaluacion.impacto_justificacion || 'Afectación en proceso crítico.';
    const sistemas = Array.isArray(inc.sistemas) ? inc.sistemas.join(', ') : (inc.sistemas || 'Sistemas Core');

    return `🚨 REPORTE DE EMERGENCIA IT - ORANGE TECH OPERATIONS
────────────────────────────────────────────────────────────
[1] CLASIFICACIÓN DEL TICKET
• Incidencia: ${incId} (${sev})
• Proceso Crítico: ${proceso}
• Sistemas Involucrados: ${sistemas}
• Criterio / Umbral Superado: ${criterio}
• Impacto Justificado: ${justificacion}

[2] ESTADO DE COMUNICACIONES Y SLAS
• Tiempo desde Apertura: ${formatAgingMinutes(evaluacion.minutos_desde_apertura || 0)}
• SLA 1ª Notificación a Dirección: < 20 min
• Frecuencia de Actualizaciones: Cada 60 min (o <30m ante cambios críticos)

[3] PLAN DE ACCIÓN Y GOBERNANZA
• Diagnóstico Técnico: En curso de mitigación y erradicación
• Gobernanza de Workaround: Requiere validación explícita de Customer & Service Ops (IM-CSO)
• Prohibición de Desescalada Automática: Activa (Regla de Oro)

[4] PROTOCOLO DE ESCALADO TELEFÓNICO
• Canal: Vía Telefónica obligatoria (Regla de Oro en SL1)
• Hito: Convocatoria N2/N3 (45m) / Dirección IM-CSO (>105m)
────────────────────────────────────────────────────────────`;
  }

  // --------------------------------------------------------------------------
  // Función 2: Renderizado del Feed de Triaje y Evaluador de Umbrales
  // --------------------------------------------------------------------------

  function renderFeed() {
    if (!dom.triageFeed) return;

    let filtered = state.incidents.slice();

    // 1. Filtro de Pestaña Principal (Reclasificaciones vs Todas vs Correctas)
    if (state.activeFilter === 'reclass_only') {
      filtered = filtered.filter(i => i.es_discrepancia || (i.discrepancia_delta && i.discrepancia_delta > 0));
    } else if (state.activeFilter === 'correct_only') {
      filtered = filtered.filter(i => !i.es_discrepancia);
    }

    // 2. Filtro de Proceso Crítico
    if (state.processFilter !== 'all') {
      filtered = filtered.filter(i => {
        const proc = i.evaluacion?.proceso || i.evaluacion?.proceso_negocio || '';
        return proc.toLowerCase().includes(state.processFilter.toLowerCase());
      });
    }

    // 3. Filtro de Severidad ITIL
    if (state.severityFilter !== 'all') {
      filtered = filtered.filter(i => i.prioridad_sugerida === state.severityFilter);
    }

    // 4. Búsqueda por Texto
    if (state.searchQuery.trim()) {
      const q = state.searchQuery.toLowerCase();
      filtered = filtered.filter(i => {
        const idMatch = (i.id || '').toLowerCase().includes(q);
        const titleMatch = (i.titulo || '').toLowerCase().includes(q);
        const sysMatch = Array.isArray(i.sistemas) ? i.sistemas.some(s => s.toLowerCase().includes(q)) : (i.sistemas || '').toLowerCase().includes(q);
        const procMatch = (i.evaluacion?.proceso || '').toLowerCase().includes(q);
        const critMatch = (i.evaluacion?.criterio || '').toLowerCase().includes(q);
        const impactMatch = (i.evaluacion?.impacto_justificacion || '').toLowerCase().includes(q);
        return idMatch || titleMatch || sysMatch || procMatch || critMatch || impactMatch;
      });
    }

    if (filtered.length === 0) {
      dom.triageFeed.innerHTML = `
        <div class="triage-empty-state">
          <div class="triage-empty-icon" aria-hidden="true">🔍</div>
          <div class="triage-empty-title">No hay incidencias que coincidan con los filtros seleccionados</div>
          <p>Prueba a cambiar el filtro de proceso o la pestaña de reclasificaciones para ver más resultados.</p>
        </div>
      `;
      return;
    }

    dom.triageFeed.innerHTML = filtered.map(inc => renderTriageCard(inc)).join('');

    // Adjuntar escuchadores de eventos para los botones de las tarjetas
    attachCardEventListeners();
  }

  function renderTriageCard(inc) {
    const incId = inc.id || 'INC000000000000';
    const isDisc = Boolean(inc.es_discrepancia || (inc.discrepancia_delta && inc.discrepancia_delta > 0));
    const delta = inc.discrepancia_delta || 0;
    const isP1 = inc.prioridad_sugerida === 'P1';

    // Clases de estilo para borde de tarjeta
    let cardClass = 'triage-card';
    if (isDisc) {
      cardClass += delta === 1 ? ' is-discrepancy-delta1' : ' is-discrepancy';
    } else {
      cardClass += ' is-correct';
    }

    const evaluacion = inc.evaluacion || {};
    const minsElapsed = evaluacion.minutos_desde_apertura || 0;
    const proceso = evaluacion.proceso || evaluacion.proceso_negocio || 'Procesos Críticos de Negocio';
    const criterio = evaluacion.criterio || 'Regla de Oro N1';
    const impactText = evaluacion.impacto_justificacion || inc.discrepancia_motivo || 'Impacto activo evaluado por el motor de triaje.';
    const urgencyText = evaluacion.urgencia_justificacion || 'Restablecimiento operativo requerido con máxima celeridad.';

    // Métricas cuantitativas
    const metrics = evaluacion.metricas_cuantitativas || {};
    const metricChips = [];
    if (metrics.sedes != null) metricChips.push(`🏢 ${metrics.sedes} Sedes`);
    if (metrics.usuarios != null) metricChips.push(`👥 ${metrics.usuarios.toLocaleString('es-ES')} Usuarios`);
    if (metrics.desviacion_pct != null) metricChips.push(`📉 ${metrics.desviacion_pct}% Desviación`);
    if (metrics.detalles && Array.isArray(metrics.detalles)) {
      metrics.detalles.forEach(d => {
        if (!metricChips.some(c => c.includes(d))) metricChips.push(`📌 ${d}`);
      });
    }

    // Sistemas tags
    const sistemasList = Array.isArray(inc.sistemas) ? inc.sistemas : (inc.sistemas ? [inc.sistemas] : []);
    const sysTagsHtml = sistemasList.map(s => `<span class="triage-sys-tag">${escapeHtml(s)}</span>`).join('');

    // Estado del ticket
    const estatusRaw = (inc.estatus || 'Pendiente').toLowerCase();
    const statusPillClass = estatusRaw.includes('curso') ? 'status-en-curso' : 'status-pendiente';

    // Severidad Remedy original
    const sevNominal = inc.prioridad_original || 'Media';
    let remedyBadgeClass = 'badge-remedy-media';
    if (sevNominal.toLowerCase().includes('alta')) remedyBadgeClass = 'badge-remedy-alta';
    if (sevNominal.toLowerCase().includes('crítica') || sevNominal.toLowerCase().includes('critica')) remedyBadgeClass = 'badge-remedy-critica';

    // Severidad ITIL Evaluada
    const itilBadgeClass = isP1 ? 'badge-itil-sl1' : 'badge-itil-sl2';
    const itilLabel = isP1 ? 'SL1 / P1 (Emergencia Crítica)' : 'SL2 / P2 (Mayor)';

    // Detalle Epsilon IA colapsable
    const isEpsilonOpen = Boolean(state.expandedEpsilon[incId]);
    const resumenIa = inc.resumen_ia || {};

    return `
      <article class="${cardClass}" id="card-${escapeHtml(incId)}" data-inc="${escapeHtml(incId)}">
        
        <!-- Cabecera de la Tarjeta -->
        <div class="triage-card-header">
          <div>
            <div class="triage-ticket-meta">
              <span class="triage-ticket-id">${escapeHtml(incId)}</span>
              <span class="triage-status-pill ${statusPillClass}">${escapeHtml(inc.estatus || 'Pendiente')}</span>
              <span class="triage-time-badge" title="Tiempo acumulado desde apertura en Remedy">
                <span aria-hidden="true">⏱️</span> ${formatAgingMinutes(minsElapsed)}
              </span>
            </div>
            <h2 class="triage-ticket-title">${escapeHtml(inc.titulo || 'Sin título')}</h2>
            <div class="triage-systems-tags">
              <span style="font-size: 11px; color: var(--triage-text-subtle); font-weight: 600;">Sistemas:</span>
              ${sysTagsHtml || '<span class="triage-sys-tag">Sistemas Core</span>'}
            </div>
          </div>
        </div>

        <!-- Función 3: Alerta de Reclasificación Inmediata (Comparador Remedy vs ITIL) -->
        <div class="triage-reclass-box ${isDisc ? (delta === 1 ? 'is-delta1' : '') : 'is-nominal-ok'}">
          <div class="triage-comparison-header">
            ${isDisc ? `
              <span class="triage-reclass-flag ${delta === 1 ? 'delta-1' : ''}">
                <span aria-hidden="true">🚨</span> Subescalación N1 Detectada (+${delta} Nivel${delta > 1 ? 'es' : ''} - ${escapeHtml(inc.discrepancia_gravedad || 'Mayor')})
              </span>
            ` : `
              <span class="triage-reclass-flag nominal-ok">
                <span aria-hidden="true">✅</span> Severidad Nominal Correcta (Alineada con Criterio ITIL Orange)
              </span>
            `}
          </div>

          <div class="triage-sev-comparison-bar">
            <div class="triage-sev-side">
              <span class="triage-sev-side-label">Remedy Inicial:</span>
              <span class="triage-sev-badge ${remedyBadgeClass}">${escapeHtml(sevNominal)}</span>
            </div>
            <span class="triage-sev-arrow" aria-hidden="true">➔</span>
            <div class="triage-sev-side">
              <span class="triage-sev-side-label">Severidad Real ITIL:</span>
              <span class="triage-sev-badge ${itilBadgeClass}">${itilLabel}</span>
            </div>
          </div>

          ${isDisc ? `
            <div class="triage-reclass-reason">
              <strong>Motivo del Dictamen de Reclasificación:</strong> ${escapeHtml(inc.discrepancia_motivo || 'Ticket clasificado por debajo del umbral objetivo corporativo de emergencias.')}
            </div>
          ` : ''}
        </div>

        <!-- Función 2: Evaluador de Umbrales Críticos de Negocio -->
        <div class="triage-threshold-box">
          <div class="triage-threshold-header">
            <span class="triage-process-badge">
              <span aria-hidden="true">🏢</span> Proceso: ${escapeHtml(proceso)}
            </span>
            ${metricChips.length > 0 ? `
              <div class="triage-metrics-row">
                ${metricChips.map(m => `<span class="triage-metric-chip">${escapeHtml(m)}</span>`).join('')}
              </div>
            ` : ''}
          </div>

          <div class="triage-threshold-rule">
            <span style="color: var(--triage-orange); font-weight: 700;">Umbral Superado:</span> ${escapeHtml(criterio)}
          </div>

          <div class="triage-impact-text">
            <strong>Impacto Técnico y Operativo:</strong> ${escapeHtml(impactText)}
          </div>

          <div class="triage-impact-text" style="font-size: 12px; color: var(--triage-text-muted);">
            <strong>Urgencia Justificada:</strong> ${escapeHtml(urgencyText)}
          </div>
        </div>

        <!-- Acciones del Módulo 1 -->
        <div class="triage-card-actions">
          <div class="triage-actions-left">
            ${isDisc ? `
              <button type="button" class="triage-btn-action-reclass btn-copy-reclass" data-inc="${escapeHtml(incId)}" title="Copiar solicitud formal al portapapeles para pegar en el worklog de Remedy">
                <span aria-hidden="true">⚡</span> Copiar Solicitud Reclasificación Remedy
              </button>
            ` : ''}

            <button type="button" class="triage-btn-action-detail btn-toggle-epsilon" data-inc="${escapeHtml(incId)}">
              <span aria-hidden="true">${isEpsilonOpen ? '🔼' : '🔍'}</span>
              <span>${isEpsilonOpen ? 'Ocultar Epsilon IA' : 'Ver Detalle Epsilon IA'}</span>
            </button>

            <button type="button" class="triage-btn triage-btn-sm btn-copy-report" data-inc="${escapeHtml(incId)}" title="Copiar Reporte Oficial de Emergencias en 4 Bloques">
              <span aria-hidden="true">📋</span> Reporte 4 Bloques
            </button>
          </div>

          <div style="font-family: var(--font-mono); font-size: 11px; color: var(--triage-text-subtle);">
            Ref: ${escapeHtml(incId)} · Regla N1
          </div>
        </div>

        <!-- Panel Colapsable de Epsilon IA -->
        <div class="triage-epsilon-drawer ${isEpsilonOpen ? 'open' : ''}" id="epsilon-drawer-${escapeHtml(incId)}">
          <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--triage-border); padding-bottom: 8px;">
            <div style="font-size: 12px; font-weight: 700; color: var(--triage-text-main); display: flex; align-items: center; gap: 6px;">
              <span style="color: var(--triage-orange);">🤖</span> Diagnóstico Técnico Epsilon Resumen IA
            </div>
            <span style="font-size: 11px; color: var(--triage-text-muted); font-family: var(--font-mono);">Telemetría Oficial</span>
          </div>

          <div class="triage-epsilon-grid">
            <div class="triage-epsilon-item">
              <span class="triage-epsilon-label">Problema Detectado</span>
              <span class="triage-epsilon-val">${escapeHtml(resumenIa.problema || 'En análisis técnico.')}</span>
            </div>
            <div class="triage-epsilon-item">
              <span class="triage-epsilon-label">Impacto Operativo</span>
              <span class="triage-epsilon-val">${escapeHtml(resumenIa.impacto || impactText)}</span>
            </div>
            <div class="triage-epsilon-item">
              <span class="triage-epsilon-label">Causa Raíz / Solución</span>
              <span class="triage-epsilon-val">${escapeHtml(resumenIa.solucion || 'Pendiente de confirmación definitiva.')}</span>
            </div>
            <div class="triage-epsilon-item">
              <span class="triage-epsilon-label">Bloqueos / Siguiente Acción</span>
              <span class="triage-epsilon-val">${escapeHtml(resumenIa.siguiente_accion || resumenIa.bloqueos || 'Coordinación con soporte N2/N3.')}</span>
            </div>
          </div>
        </div>

      </article>
    `;
  }

  // --------------------------------------------------------------------------
  // Event Listeners y Delegación
  // --------------------------------------------------------------------------

  function attachCardEventListeners() {
    // 1. Botón Copiar Solicitud Reclasificación Remedy
    document.querySelectorAll('.btn-copy-reclass').forEach(btn => {
      btn.addEventListener('click', () => {
        const incId = btn.getAttribute('data-inc');
        const inc = state.incidents.find(i => i.id === incId);
        if (inc) {
          const text = buildFormalReclassificationText(inc);
          copyToClipboard(text, `¡Solicitud de reclasificación para ${incId} copiada! Pégala en el log de Remedy.`);
        }
      });
    });

    // 2. Botón Copiar Reporte de Emergencia en 4 Bloques
    document.querySelectorAll('.btn-copy-report').forEach(btn => {
      btn.addEventListener('click', () => {
        const incId = btn.getAttribute('data-inc');
        const inc = state.incidents.find(i => i.id === incId);
        if (inc) {
          const text = build4BlockEmergencyReport(inc);
          copyToClipboard(text, `Reporte oficial de emergencia en 4 bloques copiado para ${incId}`);
        }
      });
    });

    // 3. Botón Toggle Epsilon IA
    document.querySelectorAll('.btn-toggle-epsilon').forEach(btn => {
      btn.addEventListener('click', () => {
        const incId = btn.getAttribute('data-inc');
        state.expandedEpsilon[incId] = !state.expandedEpsilon[incId];
        renderFeed();
      });
    });
  }

  function setupGlobalListeners() {
    // Pestañas de filtrado principal
    if (dom.tabReclassOnly) {
      dom.tabReclassOnly.addEventListener('click', () => {
        state.activeFilter = 'reclass_only';
        updateTabStyles();
        renderFeed();
      });
    }

    if (dom.tabAll) {
      dom.tabAll.addEventListener('click', () => {
        state.activeFilter = 'all';
        updateTabStyles();
        renderFeed();
      });
    }

    if (dom.tabCorrectOnly) {
      dom.tabCorrectOnly.addEventListener('click', () => {
        state.activeFilter = 'correct_only';
        updateTabStyles();
        renderFeed();
      });
    }

    // Filtros de Proceso y Severidad
    if (dom.filterProcessSelect) {
      dom.filterProcessSelect.addEventListener('change', (e) => {
        state.processFilter = e.target.value;
        renderFeed();
      });
    }

    if (dom.filterSeveritySelect) {
      dom.filterSeveritySelect.addEventListener('change', (e) => {
        state.severityFilter = e.target.value;
        renderFeed();
      });
    }

    // Buscador
    if (dom.searchInput) {
      dom.searchInput.addEventListener('input', (e) => {
        state.searchQuery = e.target.value;
        renderFeed();
      });
    }

    // Botón Inspeccionar Ahora
    if (dom.btnRefreshNow) {
      dom.btnRefreshNow.addEventListener('click', () => performInspection(true));
    }

    // Selector de intervalo de refresco automático
    if (dom.autoRefreshSelect) {
      dom.autoRefreshSelect.addEventListener('change', (e) => {
        const val = parseInt(e.target.value, 10);
        state.refreshIntervalMs = val;
        resetAutoRefreshTimer();
        if (val > 0) {
          showToast(`Inspección continua programada cada ${val / 1000}s`, 'info');
        } else {
          showToast('Inspección automática pausada', 'info');
        }
      });
    }

    // Modal de Criterios y Umbrales Oficiales
    document.querySelectorAll('.btn-open-criteria, #btn-help-criteria').forEach(btn => {
      btn.addEventListener('click', () => {
        if (dom.modalBackdrop) dom.modalBackdrop.classList.add('open');
      });
    });

    if (dom.btnModalClose && dom.modalBackdrop) {
      dom.btnModalClose.addEventListener('click', () => {
        dom.modalBackdrop.classList.remove('open');
      });
      dom.modalBackdrop.addEventListener('click', (e) => {
        if (e.target === dom.modalBackdrop) dom.modalBackdrop.classList.remove('open');
      });
      window.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && dom.modalBackdrop.classList.contains('open')) {
          dom.modalBackdrop.classList.remove('open');
        }
      });
    }
  }

  function updateTabStyles() {
    [dom.tabReclassOnly, dom.tabAll, dom.tabCorrectOnly].forEach(btn => {
      if (btn) btn.classList.remove('active');
    });
    if (state.activeFilter === 'reclass_only' && dom.tabReclassOnly) dom.tabReclassOnly.classList.add('active');
    if (state.activeFilter === 'all' && dom.tabAll) dom.tabAll.classList.add('active');
    if (state.activeFilter === 'correct_only' && dom.tabCorrectOnly) dom.tabCorrectOnly.classList.add('active');
  }

  function resetAutoRefreshTimer() {
    if (state.refreshTimer) {
      clearInterval(state.refreshTimer);
      state.refreshTimer = null;
    }
    if (state.refreshIntervalMs > 0) {
      state.refreshTimer = setInterval(() => {
        performInspection(false);
      }, state.refreshIntervalMs);
    }
  }

  // --- Inicialización ---

  function init() {
    setupGlobalListeners();
    updateTabStyles();
    performInspection(false);
    resetAutoRefreshTimer();

    // Actualizar el reloj relativo de última inspección cada segundo
    state.relativeTimer = setInterval(() => {
      updateRelativeTimeDisplay();
    }, 1000);
  }

  // Disparar al cargar DOM
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();

