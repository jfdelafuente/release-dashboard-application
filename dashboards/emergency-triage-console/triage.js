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
    activeFilter: 'reclass_only', // 'all' | 'reclass_only' | 'correct_only' | 'orchestrator_only'
    processFilter: 'all',
    severityFilter: 'all',
    searchQuery: '',
    expandedRows: {}, // { [incId]: boolean }
    allExpanded: false,
    lastInspectionEpoch: 0,
    refreshIntervalMs: 30000,
    refreshTimer: null,
    relativeTimer: null,

    // --- Estado Módulo 2: Orquestador Operativo de Emergencias ---
    paps: [], // Trabajos Programados (CRQ) recientes
    activeOrchIncId: null, // Incidencia abierta en el Orquestador
    orchestratorLogs: {}, // Bitácora interactiva por ticket { [incId]: Array }
    orchestratorRollbacks: {}, // Estado de Rollback por ticket { [incId]: boolean }
    orchestratorEscalations: {}, // Estado de confirmaciones de escalado { [incId]: Object }
    orchestratorActivations: {}, // Timestamp de activación del Orquestador (Dual Clock) { [incId]: number }
    clockTimeBase: 'crisis', // 'crisis' (T0 Activación SL1) | 'remedy' (T0 Apertura Remedy)
    clocksTicker: null, // Timer de actualización de relojes
    defaultIncidentManager: 'Carlos Morales · Incident Manager de Guardia (Turno Activo CSO)',
    remedyWorklogData: {}, // Datos de worklog de Remedy con filtro y estado { [incId]: Object }

    // --- Estado Módulo 3: Centro de Comunicaciones y Matrices ---
    activeCommsIncId: null,
    activeCommsTab: 'tab-templates',
    activeCommsPhase: 'inicial',
    activeContactsBrand: 'orange',
    activeContactsDomain: 'ALL',
    commsDispatchHistory: {} // { [incId]: Array }
  };

  // --- Referencias del DOM ---
  const dom = {
    // Conexión y Control
    livePill: document.getElementById('live-pill'),
    liveStatusText: document.getElementById('live-status-text'),
    autoRefreshSelect: document.getElementById('auto-refresh-select'),
    btnRefreshNow: document.getElementById('btn-refresh-now'),
    btnSyncRemedy: document.getElementById('btn-sync-remedy'),
    btnHelpCriteria: document.getElementById('btn-help-criteria'),

    // Metadatos de Canal de Datos y Vigilancia
    sourceChannelBadge: document.getElementById('source-channel-badge'),
    sourceChannelText: document.getElementById('source-channel-text'),
    sourceChannelIcon: document.getElementById('source-channel-icon'),
    sourceFileName: document.getElementById('source-file-name'),
    lastScanLabel: document.getElementById('last-scan-label'),
    kpiScanned: document.getElementById('kpi-scanned'),
    kpiSkipped: document.getElementById('kpi-skipped'),
    kpiActive: document.getElementById('kpi-active'),
    kpiEmergencies: document.getElementById('kpi-emergencies'),

    // Controles de Filtrado
    tabAll: document.getElementById('tab-all'),
    tabReclassOnly: document.getElementById('tab-reclass-only'),
    tabCorrectOnly: document.getElementById('tab-correct-only'),
    tabOrchestrator: document.getElementById('tab-orchestrator'),
    countAll: document.getElementById('count-all'),
    countReclass: document.getElementById('count-reclass'),
    countCorrect: document.getElementById('count-correct'),
    countOrchestrator: document.getElementById('count-orchestrator'),
    filterProcessSelect: document.getElementById('filter-process'),
    filterSeveritySelect: document.getElementById('filter-severity'),
    searchInput: document.getElementById('search-input'),

    // Feed de Incidentes
    triageFeed: document.getElementById('triage-feed'),

    // Modal Criterios y Toast
    modalBackdrop: document.getElementById('modal-criteria'),
    btnModalClose: document.getElementById('btn-modal-close'),
    toastContainer: document.getElementById('toast-container'),
    srAnnouncements: document.getElementById('sr-announcements'),

    // --- Referencias DOM Módulo 2: Orquestador Operativo ---
    modalOrchestrator: document.getElementById('modal-orchestrator'),
    btnOrchClose: document.getElementById('btn-orch-close'),
    orchIncId: document.getElementById('orch-inc-id'),
    orchSevBadge: document.getElementById('orch-sev-badge'),
    orchStatusPill: document.getElementById('orch-status-pill'),
    orchImName: document.getElementById('orch-im-name'),
    orchAgingTag: document.getElementById('orch-global-aging-tag'),
    orchCrisisTimeTag: document.getElementById('orch-crisis-time-tag'),
    btnModeCrisis: document.getElementById('btn-mode-crisis'),
    btnModeRemedy: document.getElementById('btn-mode-remedy'),

    // Relojes de Escalado
    clock20mCard: document.getElementById('orch-clock-20m'),
    clock20mTimer: document.getElementById('clock-20m-timer'),
    clock20mFill: document.getElementById('clock-20m-fill'),
    clock20mStatusText: document.getElementById('clock-20m-status-text'),
    popup20m: document.getElementById('popup-clock-20m'),
    btnAction20m: document.getElementById('btn-action-20m'),

    clock45mCard: document.getElementById('orch-clock-45m'),
    clock45mTimer: document.getElementById('clock-45m-timer'),
    clock45mFill: document.getElementById('clock-45m-fill'),
    clock45mStatusText: document.getElementById('clock-45m-status-text'),
    popup45m: document.getElementById('popup-clock-45m'),
    btnAction45m: document.getElementById('btn-action-45m'),

    clock105mCard: document.getElementById('orch-clock-105m'),
    clock105mTimer: document.getElementById('clock-105m-timer'),
    clock105mFill: document.getElementById('clock-105m-fill'),
    clock105mStatusText: document.getElementById('clock-105m-status-text'),
    popup105m: document.getElementById('popup-clock-105m'),
    btnAction105m: document.getElementById('btn-action-105m'),

    clock120mCard: document.getElementById('orch-clock-120m'),
    clock120mTimer: document.getElementById('clock-120m-timer'),
    clock120mFill: document.getElementById('clock-120m-fill'),
    clock120mStatusText: document.getElementById('clock-120m-status-text'),
    popup120m: document.getElementById('popup-clock-120m'),
    btnAction120m: document.getElementById('btn-action-120m'),

    // War Room Teams
    orchWarroomState: document.getElementById('orch-warroom-state'),
    orchTeamsUrlPreview: document.getElementById('orch-teams-url-preview'),
    orchBtnJoinTeams: document.getElementById('orch-btn-join-teams'),
    orchBtnCopyTeams: document.getElementById('orch-btn-copy-teams'),

    // Monitor PaP
    orchPapBadge: document.getElementById('orch-pap-status-badge'),
    orchPapContainer: document.getElementById('orch-pap-container'),

    // Bitácora / Live Incident Log
    orchTimelineContainer: document.getElementById('orch-timeline-container'),
    orchLogForm: document.getElementById('orch-log-form'),
    orchLogRole: document.getElementById('orch-log-role'),
    orchLogText: document.getElementById('orch-log-text'),
    btnCopyFullLog: document.getElementById('btn-copy-full-log'),
    btnClearLog: document.getElementById('btn-clear-log'),

    // Secciones Plegables del Módulo 2
    orchWarRoomSection: document.getElementById('orch-war-room-section'),
    orchWarRoomHeader: document.getElementById('orch-war-room-header'),
    btnToggleWarRoom: document.getElementById('btn-toggle-war-room'),
    orchPapSection: document.getElementById('orch-pap-section'),
    orchPapHeader: document.getElementById('orch-pap-header'),
    btnTogglePap: document.getElementById('btn-toggle-pap'),
    orchLogSection: document.getElementById('orch-log-section'),
    orchLogHeader: document.getElementById('orch-log-header'),
    btnToggleLog: document.getElementById('btn-toggle-log'),
    orchRemedySection: document.getElementById('orch-remedy-section'),
    orchRemedyHeader: document.getElementById('orch-remedy-header'),
    btnToggleRemedyWorklog: document.getElementById('btn-toggle-remedy-worklog'),
    btnRefreshRemedyWorklog: document.getElementById('btn-refresh-remedy-worklog'),
    orchRemedyBody: document.getElementById('orch-remedy-body'),
    orchRemedyWorklogContent: document.getElementById('orch-remedy-worklog-content'),

    // Modales Secundarios
    modalRollback: document.getElementById('modal-rollback-order'),
    btnModalRollbackClose: document.getElementById('btn-modal-rollback-close'),
    rollbackOrderText: document.getElementById('rollback-order-text'),
    btnRollbackCancel: document.getElementById('btn-rollback-cancel'),
    btnRollbackConfirmCopy: document.getElementById('btn-rollback-confirm-copy'),

    modalExecutiveComm: document.getElementById('modal-executive-comm'),
    btnModalExecClose: document.getElementById('btn-modal-exec-close'),
    execCommCompleto: document.getElementById('exec-comm-completo'),
    execCommBreve: document.getElementById('exec-comm-breve'),
    btnCopyExecBreve: document.getElementById('btn-copy-exec-breve'),
    btnCopyExecCompleto: document.getElementById('btn-copy-exec-completo'),

    // --- Referencias DOM Módulo 3: Centro de Comunicaciones y Matrices ---
    btnOpenCommsCenter: document.getElementById('btn-open-comms-center'),
    modalCommsCenter: document.getElementById('modal-comms-center'),
    btnCommsClose: document.getElementById('btn-comms-close'),
    commsLinkedTicketBadge: document.getElementById('comms-linked-ticket-badge'),
    commsLinkedTicketIcon: document.getElementById('comms-linked-ticket-icon'),
    commsLinkedTicketText: document.getElementById('comms-linked-ticket-text'),
    commsBrandIndicator: document.getElementById('comms-brand-indicator'),
    commsBrandIcon: document.getElementById('comms-brand-icon'),
    commsBrandText: document.getElementById('comms-brand-text'),
    commsBrandPlatform: document.getElementById('comms-brand-platform'),

    // Tabs Módulo 3
    tabBtnGateway: document.getElementById('tab-btn-gateway'),
    tabBtnContacts: document.getElementById('tab-btn-contacts'),
    tabGateway: document.getElementById('tab-gateway'),
    tabContacts: document.getElementById('tab-contacts'),

    // Generador de Plantillas
    tplPhaseSla: document.getElementById('tpl-phase-sla'),
    tplMetaSistemas: document.getElementById('tpl-meta-sistemas'),
    tplMetaImpacto: document.getElementById('tpl-meta-impacto'),
    tplMetaProveedor: document.getElementById('tpl-meta-proveedor'),
    tplMetaWorkaround: document.getElementById('tpl-meta-workaround'),
    tplMetaDuracion: document.getElementById('tpl-meta-duracion'),
    tplTextCompleto: document.getElementById('tpl-text-completo'),
    tplTextBreve: document.getElementById('tpl-text-breve'),
    counterCompleto: document.getElementById('counter-completo'),
    counterBreve: document.getElementById('counter-breve'),
    btnCopyTplCompleto: document.getElementById('btn-copy-tpl-completo'),
    btnCopyTplBreve: document.getElementById('btn-copy-tpl-breve'),
    btnTplRegenerate: document.getElementById('btn-tpl-regenerate'),
    btnTplLoadGateway: document.getElementById('btn-tpl-load-gateway'),

    // Gateway Web de Explotación
    gwSubject: document.getElementById('gw-subject'),
    gwBody: document.getElementById('gw-body'),
    btnGwCopyPayload: document.getElementById('btn-gw-copy-payload'),
    btnGwDispatch: document.getElementById('btn-gw-dispatch'),
    gwHistoryList: document.getElementById('gw-history-list'),

    // Buscador de Contactos y Matrices
    btnBrandOrange: document.getElementById('btn-brand-orange'),
    btnBrandMasmovil: document.getElementById('btn-brand-masmovil'),
    commsPlatformDirectLink: document.getElementById('comms-platform-direct-link'),
    contactsSearchInput: document.getElementById('contacts-search-input'),
    contactsDomainPills: document.getElementById('contacts-domain-pills'),
    contactsCardsGrid: document.getElementById('contacts-cards-grid'),

    // Traspaso de Guardia en 1 Clic (US-04 Usabilidad)
    btnShiftHandover: document.getElementById('btn-shift-handover'),
    footerBtnHandover: document.getElementById('footer-btn-handover'),
    modalShiftHandover: document.getElementById('modal-shift-handover'),
    btnModalHandoverClose: document.getElementById('btn-modal-handover-close'),
    btnModalHandoverCloseBottom: document.getElementById('btn-modal-handover-close-bottom'),
    btnHandoverCopy: document.getElementById('btn-handover-copy'),
    btnHandoverCopyBottom: document.getElementById('btn-handover-copy-bottom'),
    handoverReportText: document.getElementById('handover-report-text'),
    handoverMetaSummary: document.getElementById('handover-meta-summary'),

    // Banners de Borrador Recuperado (US-03 Continuidad Operativa)
    orchLogDraftAlert: document.getElementById('orch-log-draft-alert'),
    btnDiscardLogDraft: document.getElementById('btn-discard-log-draft'),
    btnOrchLogClear: document.getElementById('btn-orch-log-clear'),
    tplDraftAlert: document.getElementById('tpl-draft-alert'),
    btnDiscardTplDraft: document.getElementById('btn-discard-tpl-draft'),

    // Consola de Auditoría de Carga & Telemetría IA (Atajo Shift+I)
    modalIngestionAudit: document.getElementById('modal-ingestion-audit'),
    btnModalAuditClose: document.getElementById('btn-modal-audit-close'),
    btnModalAuditCloseBottom: document.getElementById('btn-modal-audit-close-bottom'),
    btnAuditForceAll: document.getElementById('btn-audit-force-all'),
    btnAuditRetryMissing: document.getElementById('btn-audit-retry-missing'),
    btnAuditRefresh: document.getElementById('btn-audit-refresh'),
    auditMetaSource: document.getElementById('audit-meta-source'),
    auditActionStatus: document.getElementById('audit-action-status'),
    auditKpiTotal: document.getElementById('audit-kpi-total'),
    auditKpiSubTotal: document.getElementById('audit-kpi-sub-total'),
    auditKpiIa: document.getElementById('audit-kpi-ia'),
    auditKpiSubIa: document.getElementById('audit-kpi-sub-ia'),
    auditKpiCompletas: document.getElementById('audit-kpi-completas'),
    auditKpiParciales: document.getElementById('audit-kpi-parciales'),
    auditKpiIncompletas: document.getElementById('audit-kpi-incompletas'),
    auditKpiDiscrepancias: document.getElementById('audit-kpi-discrepancias'),
    auditTabTickets: document.getElementById('audit-tab-tickets'),
    auditTabLogs: document.getElementById('audit-tab-logs'),
    auditTabTicketsCount: document.getElementById('audit-tab-tickets-count'),
    auditViewTickets: document.getElementById('audit-view-tickets'),
    auditViewLogs: document.getElementById('audit-view-logs'),
    auditFilterSearch: document.getElementById('audit-filter-search'),
    auditFilterState: document.getElementById('audit-filter-state'),
    auditTicketsTbody: document.getElementById('audit-tickets-tbody'),
    auditLogTerminal: document.getElementById('audit-log-terminal'),
    btnAuditCopyLog: document.getElementById('btn-audit-copy-log'),
    btnAuditScrollLog: document.getElementById('btn-audit-scroll-log'),

    // Footer Colapsable / Desplegable (Gobernanza y Consola)
    triageFooter: document.getElementById('triage-footer'),
    triageFooterHeader: document.getElementById('triage-footer-header'),
    footerBtnToggle: document.getElementById('footer-btn-toggle'),
    footerExpandable: document.getElementById('triage-footer-expandable')
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
    if (dom.livePill && dom.liveStatusText) {
      dom.livePill.className = `triage-live-pill ${status}`;
      dom.liveStatusText.textContent = text;
    }
    const footerLiveStatus = document.getElementById('footer-live-status-text');
    if (footerLiveStatus) {
      footerLiveStatus.textContent = text;
    }
  }

  // --------------------------------------------------------------------------
  // Función 1: Canal de Datos y Vigilancia Continua
  // --------------------------------------------------------------------------

  async function performInspection(isManual = false) {
    if (isManual) {
      if (dom.btnRefreshNow) {
        dom.btnRefreshNow.disabled = true;
        dom.btnRefreshNow.innerHTML = `<span aria-hidden="true" style="display:inline-block; animation: spin 1s infinite linear;">🔄</span> Auditando...`;
      }
    }
    setConnectionStatus('syncing', 'Auditando SLAs...');

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
          const isPaused = dom.autoRefreshSelect && parseInt(dom.autoRefreshSelect.value, 10) === 0;
          if (isPaused) {
            setConnectionStatus('paused', 'Vigilancia Pausada');
          } else {
            setConnectionStatus('', 'Vigilancia SLA Activa');
          }
          state.lastInspectionEpoch = Date.now();
          updateRelativeTimeDisplay();
          if (isManual) {
            showToast('Auditoría de alarmas y SLAs completada exitosamente', 'success');
          }
          if (dom.btnRefreshNow) {
            dom.btnRefreshNow.disabled = false;
            dom.btnRefreshNow.innerHTML = `<span aria-hidden="true">🔄</span> Auditar Ahora`;
          }
          return;
        }
      } catch (err) {
        lastError = err;
      }
    }

    setConnectionStatus('error', 'Error de conexión');
    showToast('Error al auditar catálogo de incidencias: ' + (lastError ? lastError.message : 'No se encontraron datos'), 'error');
    if (dom.btnRefreshNow) {
      dom.btnRefreshNow.disabled = false;
      dom.btnRefreshNow.innerHTML = `<span aria-hidden="true">🔄</span> Auditar Ahora`;
    }
  }

  async function triggerRemedySync() {
    if (!dom.btnSyncRemedy) return;
    const origHtml = dom.btnSyncRemedy.innerHTML;
    dom.btnSyncRemedy.disabled = true;
    dom.btnSyncRemedy.innerHTML = `<span aria-hidden="true" style="display:inline-block; animation: spin 1s infinite linear;">⚡</span> Sincronizando...`;

    try {
      const res = await fetch('/api/sync-remedy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dias: 3 }),
      });
      const data = await res.json();
      if (res.ok && data.success) {
        state.metadata.last_sync_source = 'montmc_api';
        const total = data.total_consultadas ?? data.count ?? 0;
        const nuevas = data.nuevas ?? data.stats?.inserted ?? 0;
        const actualizadas = data.actualizadas ?? data.stats?.updated ?? 0;
        const msg = `Sincronización Remedy OK: ${total} incidencias procesadas (+${nuevas} nuevas, ${actualizadas} actualizadas).`;
        showToast(msg, 'success');
        await performInspection(true);
      } else {
        const err = data.error || (data.details ? JSON.stringify(data.details) : 'Error desconocido');
        showToast(`Error al sincronizar con MonTMC Remedy: ${err}`, 'error');
      }
    } catch (e) {
      showToast(`Fallo de red al invocar /api/sync-remedy: ${e.message}`, 'error');
    } finally {
      dom.btnSyncRemedy.disabled = false;
      dom.btnSyncRemedy.innerHTML = origHtml;
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
    // Filtrado estricto y deduplicación defensiva por ID de incidencia
    const seenIds = new Set();
    state.incidents = list.filter(inc => {
      const id = String(inc.id || inc['ID de incidencia'] || '').trim();
      if (id) {
        if (seenIds.has(id)) return false;
        seenIds.add(id);
      }
      return !isTerminalStatus(inc.estatus || inc.estado || inc.status);
    });

    // Actualizar KPIs superiores y Canal de Datos (Foco 100% en Incidencias Activas)
    const kpis = state.metadata.kpis || {};
    if (dom.sourceFileName) {
      dom.sourceFileName.textContent = state.metadata.source_file || 'high_priority_notifications.json';
    }

    // Actualizar Canal / Origen de Datos (API MonTMC vs Snapshot Local)
    if (dom.sourceChannelBadge && dom.sourceChannelText) {
      const isApi = state.metadata.last_sync_source === 'montmc_api' ||
                    (state.metadata.source_file && /montmc|remedy/i.test(state.metadata.source_file));
      if (isApi) {
        dom.sourceChannelBadge.className = 'triage-source-badge triage-source-badge-api';
        if (dom.sourceChannelIcon) dom.sourceChannelIcon.textContent = '⚡';
        dom.sourceChannelText.textContent = 'Canal MonTMC Remedy (Online)';
      } else {
        dom.sourceChannelBadge.className = 'triage-source-badge triage-source-badge-snapshot';
        if (dom.sourceChannelIcon) dom.sourceChannelIcon.textContent = '📄';
        dom.sourceChannelText.textContent = 'Snapshot Local';
      }
    }

    const activeCount = (kpis.active_evaluated_count != null) ? kpis.active_evaluated_count : state.incidents.length;
    const discCount = (kpis.discrepancies_count != null) ? kpis.discrepancies_count : state.incidents.filter(i => i.es_discrepancia).length;
    const p1Count = (kpis.p1_critical_count != null) ? kpis.p1_critical_count : state.incidents.filter(i => i.prioridad_sugerida === 'P1').length;
    const p2Count = (kpis.p2_high_count != null) ? kpis.p2_high_count : state.incidents.filter(i => i.prioridad_sugerida === 'P2').length;

    if (dom.kpiScanned) dom.kpiScanned.textContent = activeCount;
    if (dom.kpiSkipped) dom.kpiSkipped.textContent = discCount;
    if (dom.kpiActive) dom.kpiActive.textContent = p1Count;
    if (dom.kpiEmergencies) dom.kpiEmergencies.textContent = p2Count;

    // Contadores de pestañas de filtrado
    const totalCount = state.incidents.length;
    const correctCount = state.incidents.filter(i => !i.es_discrepancia && (!i.discrepancia_delta || i.discrepancia_delta === 0)).length;
    if (dom.countAll) dom.countAll.textContent = totalCount;
    if (dom.countReclass) dom.countReclass.textContent = discCount;
    if (dom.countCorrect) dom.countCorrect.textContent = correctCount;
    if (dom.countOrchestrator) dom.countOrchestrator.textContent = p1Count;

    // Renderizar Feed de Triaje (Vista Tabular con Filas Plegables)
    renderFeed();
    updateBrowserTitleAndFavicon();
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

  // ==========================================================================
  // MÓDULO 2: ORQUESTADOR DEL PROCESO OPERATIVO DE EMERGENCIAS (SL1/P1)
  // Activación de Emergencia, War Room Teams, Monitor PaP, Relojes y Bitácora
  // ==========================================================================

  async function loadScheduledChangesPaP() {
    const candidateUrls = [
      '/data/scheduled_changes_pap.json',
      '../../data/scheduled_changes_pap.json',
      './data/scheduled_changes_pap.json'
    ];
    for (const url of candidateUrls) {
      try {
        const res = await fetch(url);
        if (res.ok) {
          const data = await res.json();
          if (data && data.changes && Array.isArray(data.changes)) {
            state.paps = data.changes;
            return;
          }
        }
      } catch (_) {}
    }
    // Fallback integrado si no se alcanza el archivo por la red (Marcados explícitamente como SIMULATED MOCK)
    state.paps = [
      {
        crq: 'CRQ000000190422',
        titulo: 'Despliegue parche v24.8 catálogo terminales y microservicios CRM4TELCO',
        sistemas: ['CRM4TELCO', 'Ficha multimarca'],
        proceso_relacionado: 'Atención al Cliente (ATC)',
        fecha_ejecucion: '2026-10-30T17:15:00+01:00',
        ventana: 'Ventana Ordinaria (17:00 - 18:00)',
        horas_desde_ejecucion: 2.5,
        estado: 'Ejecutado / En Observación',
        responsable: 'Laura Menéndez (DevOps CRM Digital)',
        equipo: 'Sistemas Comerciales y Frontales',
        riesgo: 'Medio',
        rollback_plan: 'Revertir despliegue de pods Kubernetes a la imagen v24.7 y reiniciar endpoints de sincronización con Ficha multimarca.',
        tiempo_rollback_estimado: '12 minutos',
        contacto_guardia: 'Guardia CRM Frontales (+34 91 222 3401)',
        is_mock: true,
        data_source: 'SIMULATED_MOCK',
        mock_tag: '[MOCK / PENDIENTE API CMDB]'
      },
      {
        crq: 'CRQ000000190311',
        titulo: 'Actualización release bffclientdashboard v3.12 y cache customerAgreement',
        sistemas: ['bffclientdashboard', 'Ficha Cliente Orange', 'InteractionClient'],
        proceso_relacionado: 'Atención al Cliente (ATC)',
        fecha_ejecucion: '2026-10-30T16:45:00+01:00',
        ventana: 'Ventana de Tarde (16:30 - 17:30)',
        horas_desde_ejecucion: 3.0,
        estado: 'Ejecutado / En Observación',
        responsable: 'Sergio Morales (Arquitectura BFF & Fronts)',
        equipo: 'Frontales y Experiencia Digital',
        riesgo: 'Alto',
        rollback_plan: 'Detener réplicas v3.12 en APIGEE/Istio, restablecer enrutado del ingress hacia backend v3.11 y purgar caché Redis de customerAgreement.',
        tiempo_rollback_estimado: '8 minutos',
        contacto_guardia: 'Guardia BFF Digital (+34 91 222 3402)',
        is_mock: true,
        data_source: 'SIMULATED_MOCK',
        mock_tag: '[MOCK / PENDIENTE API CMDB]'
      },
      {
        crq: 'CRQ000000189914',
        titulo: 'Parche hotfix adaptadores JMS TIBCO BusinessWorks hacia Siebel IP24',
        sistemas: ['TIBCO', 'BW', 'Siebel IP24', 'Siebel 8', 'CRM'],
        proceso_relacionado: 'Middleware Transversal',
        fecha_ejecucion: '2026-10-30T15:30:00+01:00',
        ventana: 'Ventana de Mantenimiento Middleware (15:00 - 16:30)',
        horas_desde_ejecucion: 4.2,
        estado: 'Ejecutado / En Observación',
        responsable: 'Martín Quintana (Middleware Operations)',
        equipo: 'Infraestructura & Middleware Core',
        riesgo: 'Alto',
        rollback_plan: 'Conmutar el conector EMS JMS al bus de colas pasivo anterior y ejecutar reinicio escalonado de engines TIBCO BW en cluster.',
        tiempo_rollback_estimado: '15 minutos',
        contacto_guardia: 'Guardia Middleware TIBCO (+34 91 222 3403)',
        is_mock: true,
        data_source: 'SIMULATED_MOCK',
        mock_tag: '[MOCK / PENDIENTE API CMDB]'
      },
      {
        crq: 'CRQ000000188550',
        titulo: 'Migración endpoint xpldocumentlist en API Gateway Apigee y balanceo Ficha',
        sistemas: ['xpldocumentlist API', 'Ficha Cliente Orange'],
        proceso_relacionado: 'Atención al Cliente (ATC)',
        fecha_ejecucion: '2026-10-30T18:00:00+01:00',
        ventana: 'Ventana Express (18:00 - 18:30)',
        horas_desde_ejecucion: 1.7,
        estado: 'Ejecutado / En Observación',
        responsable: 'Elena Casado (API Core Gateway)',
        equipo: 'Comunicaciones y Gateway',
        riesgo: 'Medio',
        rollback_plan: 'Reactivar la directiva TargetServer hacia el cluster legacy en Apigee y vaciar la tabla de rutas temporales.',
        tiempo_rollback_estimado: '5 minutos',
        contacto_guardia: 'Guardia Apigee (+34 91 222 3404)',
        is_mock: true,
        data_source: 'SIMULATED_MOCK',
        mock_tag: '[MOCK / PENDIENTE API CMDB]'
      },
      {
        crq: 'CRQ000000187640',
        titulo: 'Recarga de parámetros de tarificación CAS e interfaces de mediación HPFMS',
        sistemas: ['HPFMS', 'CAS', 'BSCS', 'SEDNA_PREPAGO', 'HPSPI', 'Middleware'],
        proceso_relacionado: 'Facturación, Mediación y Cobros',
        fecha_ejecucion: '2026-10-30T14:00:00+01:00',
        ventana: 'Ventana Batch (14:00 - 15:30)',
        horas_desde_ejecucion: 5.8,
        estado: 'Ejecutado / En Observación',
        responsable: 'David Salgado (Billing & Mediation Lead)',
        equipo: 'Sistemas de Facturación y Mediación',
        riesgo: 'Crítico',
        rollback_plan: 'Restaurar snapshot de tablas de parámetros CAS y relanzar el demonio colector HPFMS con las colas previas.',
        tiempo_rollback_estimado: '20 minutos',
        contacto_guardia: 'Guardia Facturación/Mediación (+34 91 222 3405)',
        is_mock: true,
        data_source: 'SIMULATED_MOCK',
        mock_tag: '[MOCK / PENDIENTE API CMDB]'
      }
    ];
  }

  function findMatchingPaP(inc) {
    if (!inc || !state.paps || state.paps.length === 0) return null;
    const rawSistemas = inc.sistemas || [];
    const incSystems = (Array.isArray(rawSistemas) ? rawSistemas : [rawSistemas])
      .map(s => String(s).toLowerCase().trim())
      .filter(Boolean);

    if (incSystems.length === 0) return null;

    for (const pap of state.paps) {
      const papSystems = (pap.sistemas || []).map(s => String(s).toLowerCase().trim());
      const hasMatch = incSystems.some(isys =>
        papSystems.some(psys => psys.includes(isys) || isys.includes(psys))
      );
      if (hasMatch) {
        return pap;
      }
    }
    return null;
  }

  function generateTeamsWarRoomUrl(incId) {
    const cleanId = String(incId).toLowerCase().replace(/[^a-z0-9]/g, '');
    return `https://teams.microsoft.com/l/meetup-join/19%3ameeting_${cleanId}_orange_warroom%40thread.v2/0?context=%7b%22Tid%22%3a%22orange-spain-tenant%22%2c%22Oid%22%3a%22im-cso-coordinator%22%7d`;
  }

  function buildTeamsWarRoomCallText(inc, teamsUrl) {
    const incId = inc.id || 'INC000000000000';
    const titulo = inc.titulo || 'Sin título';
    const evaluacion = inc.evaluacion || {};
    const proceso = evaluacion.proceso || evaluacion.proceso_negocio || 'Procesos Críticos';
    const sistemas = Array.isArray(inc.sistemas) ? inc.sistemas.join(', ') : (inc.sistemas || 'Sistemas Core');
    const imName = state.defaultIncidentManager;
    const confId = '948' + (Math.abs(incId.split('').reduce((acc, c) => acc + c.charCodeAt(0), 1000)) % 9000);

    return `🚨 CONVOCATORIA URGENTE WAR ROOM · INCIDENCIA CRÍTICA SL1 / P1 🚨
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Código Incidencia: ${incId}
Título: ${titulo}
Severidad Declarada: SL1 / P1 (Emergencia Crítica ITIL)
Proceso Afectado: ${proceso}
Sistemas Impactados: ${sistemas}
Incident Manager Asignado: ${imName}

🔗 Puente Microsoft Teams War Room:
${teamsUrl}

📞 Conexión Telefónica de Respaldo: +34 91 123 4567 | Conf ID: ${confId}#
👥 Asistencia Obligatoria: IM-CSO, SMC Operations Bridge, Soporte Resolutor N2/N3, Responsable de Aplicación.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Convocado por Orange Tech Operations · IT Incident Management`;
  }

  function getOrInitLog(incId, inc) {
    const storageKey = 'emergency_log_' + incId;
    let entries = [];
    try {
      const stored = localStorage.getItem(storageKey);
      if (stored) {
        entries = JSON.parse(stored);
      }
    } catch (_) {}

    if (!entries || entries.length === 0) {
      const nowStr = new Date().toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      const remedyMins = inc?.evaluacion?.minutos_desde_apertura || 0;
      entries = [
        {
          id: 'log-1',
          time: nowStr,
          role: 'TRIAGE',
          roleLabel: '🤖 Motor de Triaje',
          text: `Incidencia evaluada y clasificada como SL1 / P1 por superación de umbrales críticos. Apertura formal de proceso de emergencia.`,
          extraClass: 'role-warroom'
        },
        {
          id: 'log-dualclock',
          time: nowStr,
          role: 'CRISIS_CLOCK',
          roleLabel: '⏱️ Dual Clock (ITIL)',
          text: `Inicializados temporizadores tácticos de War Room (T0_crisis: ${nowStr}). Envejecimiento Remedy acumulado en N1: ${formatAgingMinutes(remedyMins)}.`,
          extraClass: 'role-im'
        },
        {
          id: 'log-2',
          time: nowStr,
          role: 'IM',
          roleLabel: '👤 Incident Manager',
          text: `Asignación automática de Incident Manager en Turno Activo CSO: ${state.defaultIncidentManager}.`,
          extraClass: 'role-im'
        },
        {
          id: 'log-3',
          time: nowStr,
          role: 'WARROOM',
          roleLabel: '📡 War Room Teams',
          text: `Puente Microsoft Teams generado y convocado con SMC Operations Bridge y grupos resolutores.`,
          extraClass: 'role-warroom'
        }
      ];

      const pap = findMatchingPaP(inc);
      if (pap) {
        entries.push({
          id: 'log-pap',
          time: nowStr,
          role: 'PAP',
          roleLabel: '🔍 Monitor PaP',
          text: `[DATOS SIMULADOS / MOCK] Coincidencia detectada con cambio reciente ${pap.crq}: "${pap.titulo}". Procedimiento de Rollback verificado disponible (${pap.tiempo_rollback_estimado}).`,
          extraClass: 'role-rollback'
        });
      }

      saveLog(incId, entries);
    }

    state.orchestratorLogs[incId] = entries;
    return entries;
  }

  function saveLog(incId, entries) {
    state.orchestratorLogs[incId] = entries;
    try {
      localStorage.setItem('emergency_log_' + incId, JSON.stringify(entries));
    } catch (_) {}
  }

  function addLogEntry(incId, role, roleLabel, text, extraClass = '') {
    const entries = state.orchestratorLogs[incId] || [];
    const nowStr = new Date().toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    entries.push({
      id: 'log-' + Date.now(),
      time: nowStr,
      role,
      roleLabel,
      text,
      extraClass
    });
    saveLog(incId, entries);
    renderTimelineEntries(incId);
  }

  function renderTimelineEntries(incId) {
    if (!dom.orchTimelineContainer) return;
    const entries = state.orchestratorLogs[incId] || [];
    if (entries.length === 0) {
      dom.orchTimelineContainer.innerHTML = `<div style="text-align: center; color: var(--triage-text-subtle); padding: 16px; font-size: 12px;">No hay hitos registrados en la bitácora todavía.</div>`;
      return;
    }

    const html = entries.map(item => `
      <div class="orch-timeline-entry ${item.extraClass || ''}">
        <div class="orch-entry-top">
          <span class="orch-entry-role-badge">${escapeHtml(item.roleLabel || item.role)}</span>
          <span class="orch-entry-time">${escapeHtml(item.time)}</span>
        </div>
        <div class="orch-entry-text">${escapeHtml(item.text)}</div>
      </div>
    `).join('');

    dom.orchTimelineContainer.innerHTML = html;
    dom.orchTimelineContainer.scrollTop = dom.orchTimelineContainer.scrollHeight;
  }

  function renderPapSection(inc) {
    if (!dom.orchPapContainer || !dom.orchPapBadge) return;
    const incId = inc.id || 'INC000000000000';
    const isRollbackOrdered = Boolean(state.orchestratorRollbacks[incId]);
    const pap = findMatchingPaP(inc);

    if (isRollbackOrdered && pap) {
      dom.orchPapBadge.className = 'orch-pap-badge';
      dom.orchPapBadge.style.background = '#EFF6FF';
      dom.orchPapBadge.style.color = '#1D4ED8';
      dom.orchPapBadge.style.border = '1px solid #93C5FD';
      dom.orchPapBadge.textContent = '⏪ Rollback en Curso';

      dom.orchPapContainer.innerHTML = `
        <div class="orch-pap-rollback-in-progress">
          <div style="display: flex; align-items: center; gap: 8px; font-size: 13px; font-weight: 700; color: #1E40AF;">
            <span>⏪</span> <span>Orden de Rollback Inmediato Ejecutada por IM</span>
          </div>
          <p style="margin: 0; font-size: 12px; color: var(--triage-text-muted);">
            Se ha transmitido la orden obligatoria de revertir el cambio <strong>${escapeHtml(pap.crq)}</strong>. SMC Bridge y el equipo de guardia están ejecutando el plan de reversión.
          </p>
          <div style="background: #FFFFFF; border: 1px solid #BFDBFE; border-radius: 4px; padding: 8px 10px; font-size: 11.5px;">
            <strong>Plan en ejecución:</strong> ${escapeHtml(pap.rollback_plan)} (Tiempo est: ${escapeHtml(pap.tiempo_rollback_estimado)})
          </div>
        </div>
      `;
      return;
    }

    if (pap) {
      dom.orchPapBadge.className = 'orch-pap-badge is-matched';
      dom.orchPapBadge.textContent = `⚠️ Coincidencia: ${pap.crq}`;

      const mockNoticeHtml = pap.is_mock ? `
        <div class="triage-mock-banner" style="margin-bottom: 8px;">
          <span aria-hidden="true">🧪</span>
          <div>
            <strong>DATOS SIMULADOS (MOCK · PENDIENTE API CMDB):</strong>
            <div>Registro sintético para pruebas de cruce y reversión. Endpoint planificado: <code>GET /api/v1/cmdb/scheduled-changes</code>.</div>
          </div>
        </div>
      ` : '';

      dom.orchPapContainer.innerHTML = `
        <div class="orch-pap-alert-card">
          ${mockNoticeHtml}
          <div class="orch-pap-top-alert">
            <span aria-hidden="true">⚠️</span>
            <span>Trabajo Programado (PaP) reciente coincide con los sistemas afectados:</span>
          </div>
          <div class="orch-pap-details-grid">
            <div class="orch-pap-field">
              <strong>Código de Cambio</strong>
              <span>${escapeHtml(pap.crq)} ${pap.is_mock ? '<span class="triage-mock-badge">🧪 MOCK</span>' : ''}</span>
            </div>
            <div class="orch-pap-field">
              <strong>Ventana de Ejecución</strong>
              <span>${escapeHtml(pap.ventana)} (hace ${pap.horas_desde_ejecucion}h)</span>
            </div>
            <div class="orch-pap-field" style="grid-column: span 2;">
              <strong>Título del Cambio</strong>
              <span>${escapeHtml(pap.titulo)}</span>
            </div>
            <div class="orch-pap-field">
              <strong>Responsable</strong>
              <span>${escapeHtml(pap.responsable)}</span>
            </div>
            <div class="orch-pap-field">
              <strong>Contacto de Guardia</strong>
              <span>${escapeHtml(pap.contacto_guardia)}</span>
            </div>
          </div>
          <div class="orch-pap-rollback-plan-box">
            <strong>Plan de Rollback Documentado:</strong> ${escapeHtml(pap.rollback_plan)}
            <div style="font-weight: 700; margin-top: 4px;">⏱️ Tiempo estimado de ejecución del Rollback: ${escapeHtml(pap.tiempo_rollback_estimado)}</div>
          </div>
          <button type="button" class="orch-btn-rollback" id="btn-orch-trigger-rollback" data-inc="${escapeHtml(incId)}">
            <span aria-hidden="true">⏪</span>
            <span>Ordenar Rollback Inmediato (IM)</span>
          </button>
        </div>
      `;

      const btnRollback = document.getElementById('btn-orch-trigger-rollback');
      if (btnRollback) {
        btnRollback.addEventListener('click', () => {
          openRollbackOrderModal(inc, pap);
        });
      }
    } else {
      dom.orchPapBadge.className = 'orch-pap-badge is-none';
      dom.orchPapBadge.textContent = '✅ Sin PaP Reciente';
      dom.orchPapContainer.innerHTML = `
        <div class="orch-pap-no-match-box">
          <span style="font-size: 20px;" aria-hidden="true">🛡️</span>
          <div>
            <strong>No se detectaron Trabajos Programados (PaP) en las últimas horas</strong>
            <p style="margin: 2px 0 0; font-size: 11.5px; color: var(--triage-text-muted);">
              Los sistemas involucrados (${escapeHtml(Array.isArray(inc.sistemas) ? inc.sistemas.join(', ') : (inc.sistemas || 'Sistemas Core'))}) no registran cambios de producción en la ventana reciente.
            </p>
          </div>
        </div>
      `;
    }
  }

  function openRollbackOrderModal(inc, pap) {
    if (!dom.modalRollback || !dom.rollbackOrderText) return;
    const incId = inc.id || 'INC000000000000';
    const imName = state.defaultIncidentManager;
    const nowStr = new Date().toLocaleString('es-ES');
    const mockDisclaimer = pap && pap.is_mock ? '⚠️ [DATOS DE PRUEBA / SIMULACRO OPERATIVO MOCK · PENDIENTE API REMEDY CMDB]\n' : '';
    const orderText = `⏪ ORDEN FORMAL DE ROLLBACK INMEDIATO (IM-CSO) ⏪
${mockDisclaimer}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Ordenante: ${imName}
Motivo: Indisponibilidad crítica ${incId} tras despliegue de cambio.
Código de Cambio (PaP): ${pap.crq}${pap.is_mock ? ' [MOCK]' : ''}
Título PaP: ${pap.titulo}
Sistemas Impactados: ${(pap.sistemas || []).join(', ')}
Plan de Rollback: ${pap.rollback_plan}
Tiempo Estimado de Ejecución: ${pap.tiempo_rollback_estimado}
Contacto de Guardia: ${pap.contacto_guardia}
Hora Oficial de la Orden: ${nowStr}
Destinatarios: SMC Operations Bridge / Centro de Control / Equipo de Guardia PaP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INSTRUCCIÓN OPERATIVA OBLIGATORIA:
Proceder con la ejecución inmediata del procedimiento de Rollback. Confirmar inicio y progreso a través del puente de la War Room.`;

    dom.rollbackOrderText.textContent = orderText;
    dom.modalRollback.classList.add('open');

    if (dom.btnRollbackConfirmCopy) {
      dom.btnRollbackConfirmCopy.onclick = () => {
        copyToClipboard(orderText, '¡Orden formal de Rollback copiada al portapapeles!');
        state.orchestratorRollbacks[incId] = true;
        addLogEntry(
          incId,
          'ROLLBACK',
          '⏪ Rollback PaP',
          `IM ${imName} ha ordenado el Rollback inmediato del PaP ${pap.crq} (${pap.titulo}). Tiempo estimado: ${pap.tiempo_rollback_estimado}. Notificado SMC Bridge.`,
          'role-rollback'
        );
        renderPapSection(inc);
        dom.modalRollback.classList.remove('open');
        showToast(`Rollback ordenado para el PaP ${pap.crq}. Notificado a SMC.`, 'success');
      };
    }

    if (dom.btnRollbackCancel) {
      dom.btnRollbackCancel.onclick = () => {
        dom.modalRollback.classList.remove('open');
      };
    }
    if (dom.btnModalRollbackClose) {
      dom.btnModalRollbackClose.onclick = () => {
        dom.modalRollback.classList.remove('open');
      };
    }
  }

  // =========================================================================
  // MÓDULO 3: CENTRO DE COMUNICACIONES Y MATRICES DE CONTACTO
  // =========================================================================

  // Catálogo Oficial de Contactos Técnicos y Matrices N2/N3 (GRIAL / Confluence)
  const CONTACTS_DIRECTORY = [
    // --- ORANGE / JAZZTEL (GRIAL: https://grial.orange.es) ---
    {
      id: 'cont-ora-01',
      brand: 'orange',
      domain: 'FRONT',
      system: 'CRM4TELCO & Ficha de Cliente',
      name: 'Guardia Frontales Comerciales (ATC / Distribuidores)',
      provider: 'Indra Sistemas · Front Operations',
      level: 'N2 / N3',
      role: 'Soporte Frontales & Transaccional CRM',
      phone: '+34 91 222 3401',
      ext: '43401',
      email: 'guardia.frontales.crm@orange.com',
      sdm: 'Alfonso Ruiz · SDM Indra (+34 600 111 201)',
      hours: '24x7 Turno Continuo',
      platformUrl: 'https://grial.orange.es/sistemas/crm4telco'
    },
    {
      id: 'cont-ora-02',
      brand: 'orange',
      domain: 'MIDDLE',
      system: 'TIBCO EMS & Bus de Integración Transversal',
      name: 'Guardia Middleware TIBCO & Bus Corporativo',
      provider: 'Sopra Steria · Middleware Engineering',
      level: 'N3',
      role: 'Arquitectura & Broker de Mensajería TIBCO',
      phone: '+34 91 222 3403',
      ext: '43403',
      email: 'guardia.tibco.integration@orange.com',
      sdm: 'Elena Santamaría · Lead Architect (+34 600 111 203)',
      hours: '24x7 Convocatoria Directa War Room',
      platformUrl: 'https://grial.orange.es/sistemas/tibco-ems'
    },
    {
      id: 'cont-ora-03',
      brand: 'orange',
      domain: 'MIDDLE',
      system: 'Apigee API Gateway & Microservicios',
      name: 'Guardia Pasarela de APIs Apigee',
      provider: 'Minsait / Google Cloud Services',
      level: 'N2 / N3',
      role: 'Tráfico de APIs & Pasarelas B2B/B2C',
      phone: '+34 91 222 3404',
      ext: '43404',
      email: 'guardia.apigee.core@orange.com',
      sdm: 'David Garrido · API Platform Manager (+34 600 111 204)',
      hours: '24x7 On-Call',
      platformUrl: 'https://grial.orange.es/sistemas/apigee-gateway'
    },
    {
      id: 'cont-ora-04',
      brand: 'orange',
      domain: 'BILLING',
      system: 'HPFMS / BSCS / SEDNA (Facturación & Cobros)',
      name: 'Guardia Tasación & Facturación Core',
      provider: 'Ericsson España / DXC Technology',
      level: 'N2 / N3',
      role: 'Tarificación, Ciclos de Cobro y Mediación',
      phone: '+34 91 222 3405',
      ext: '43405',
      email: 'guardia.billing.hpfms@orange.com',
      sdm: 'Beatriz Morales · Billing Ops Lead (+34 600 111 205)',
      hours: '24x7 Guardia Crítica',
      platformUrl: 'https://grial.orange.es/sistemas/hpfms-billing'
    },
    {
      id: 'cont-ora-05',
      brand: 'orange',
      domain: 'INFRA',
      system: 'Infraestructura Core IT (VMware ESX / PSeries / Exadata / OCI)',
      name: 'Guardia Datacenter, Servidores & Cloud Core',
      provider: 'Kyndryl / Oracle Cloud España',
      level: 'N3',
      role: 'SRE Virtualización, Hypervisores & BBDD Críticas',
      phone: '+34 91 222 3406',
      ext: '43406',
      email: 'guardia.infra.cloud@orange.com',
      sdm: 'Marcos Vega · Principal SRE (+34 600 111 206)',
      hours: '24x7 Intervención Inmediata',
      platformUrl: 'https://grial.orange.es/sistemas/core-infra'
    },
    {
      id: 'cont-ora-06',
      brand: 'orange',
      domain: 'IAM',
      system: 'EVIDIAN / GDU / RobotFactory (Identidad & SSO)',
      name: 'Guardia Autenticación Corporativa, Directorio & SSO',
      provider: 'Evidian IAM Ops / Atos',
      level: 'N2 / N3',
      role: 'Gestión de Credenciales, MFA & Token Services',
      phone: '+34 91 222 3407',
      ext: '43407',
      email: 'guardia.iam.evidian@orange.com',
      sdm: 'Silvia Navarro · IAM Service Manager (+34 600 111 207)',
      hours: '24x7 On-Call',
      platformUrl: 'https://grial.orange.es/sistemas/iam-evidian'
    },
    {
      id: 'cont-ora-07',
      brand: 'orange',
      domain: 'NETWORK',
      system: 'Redes WAN Sedes & Conectividad CGRED',
      name: 'Guardia Redes WAN Sedes, Tiendas & Datacenter',
      provider: 'Orange Wholesale & Data Networks',
      level: 'N2 / N3',
      role: 'Circuitos Macro-LAN, SD-WAN & CGRED',
      phone: '+34 91 222 3408',
      ext: '43408',
      email: 'guardia.cgred.redes@orange.com',
      sdm: 'Ignacio Campos · NOC Operations Lead (+34 600 111 208)',
      hours: '24x7 Turno Continuo NOC',
      platformUrl: 'https://grial.orange.es/sistemas/redes-cgred'
    },
    {
      id: 'cont-ora-08',
      brand: 'orange',
      domain: 'INFRA',
      system: 'Customer & Service Operations (IM-CSO)',
      name: 'Incident Management CSO (Gestión Emergencias)',
      provider: 'Orange España Interno · Dirección de Operaciones',
      level: 'Jefatura',
      role: 'Orquestación de Emergencias, War Rooms & C-Level',
      phone: '+34 91 222 3900',
      ext: '43900',
      email: 'im-cso-guardia@orange.com',
      sdm: 'Carlos Morales · IM CSO Turno Activo (+34 600 111 900)',
      hours: '24x7 Presencial / Remoto Activo',
      platformUrl: 'https://grial.orange.es/escalados/im-cso'
    },

    // --- MASMOVIL / KRT (CONFLUENCE: https://confluence.masmovil.com) ---
    {
      id: 'cont-mm-01',
      brand: 'masmovil',
      domain: 'FRONT',
      system: 'CRM KRT / Salesforce MM / Yoigo / Euskaltel',
      name: 'Guardia Operaciones Front CRM MasMóvil',
      provider: 'Accenture Interactive / Salesforce',
      level: 'N2 / N3',
      role: 'Atención Tiendas, Call Centers y Portabilidad MM',
      phone: '+34 91 333 4501',
      ext: '54501',
      email: 'guardia.krt.salesforce@masmovil.com',
      sdm: 'Javier Serrano · Service Lead Accenture (+34 611 222 301)',
      hours: '24x7 On-Call Turno Rotativo',
      platformUrl: 'https://confluence.masmovil.com/display/OPS/KRT+CRM+OnCall'
    },
    {
      id: 'cont-mm-02',
      brand: 'masmovil',
      domain: 'MIDDLE',
      system: 'Kong API Gateway & EventBus Matrix (Kafka)',
      name: 'Guardia Integración Transversal & Streaming MM',
      provider: 'Thoughtworks / DevOps SRE MasMóvil',
      level: 'N3',
      role: 'Event Streaming Kafka & Pasarelas Kong',
      phone: '+34 91 333 4503',
      ext: '54503',
      email: 'guardia.eventbus.kong@masmovil.com',
      sdm: 'Marta Gil · SRE Platform Manager (+34 611 222 303)',
      hours: '24x7 War Room Directa',
      platformUrl: 'https://confluence.masmovil.com/display/OPS/Kong+Matrix+Matrix'
    },
    {
      id: 'cont-mm-03',
      brand: 'masmovil',
      domain: 'BILLING',
      system: 'Netcracker Billing Core & Mediación MasMóvil',
      name: 'Guardia Facturación & Recargas MasMóvil / Yoigo',
      provider: 'Netcracker Technology / NTT Data',
      level: 'N2 / N3',
      role: 'Rating Online, Billing Cycles & Tasación Prepago/Pospago',
      phone: '+34 91 333 4505',
      ext: '54505',
      email: 'guardia.netcracker.billing@masmovil.com',
      sdm: 'Pablo Domínguez · Billing Lead (+34 611 222 305)',
      hours: '24x7 Guardia Crítica',
      platformUrl: 'https://confluence.masmovil.com/display/OPS/Netcracker+Billing'
    },
    {
      id: 'cont-mm-04',
      brand: 'masmovil',
      domain: 'INFRA',
      system: 'Cloud AWS Platform & Kubernetes EKS MM',
      name: 'Guardia SRE Cloud & Infraestructura MasMóvil',
      provider: 'AWS Enterprise Support / MM Cloud Ops',
      level: 'N3',
      role: 'Clústeres Kubernetes, Contenedores & Cloud VPC',
      phone: '+34 91 333 4506',
      ext: '54506',
      email: 'guardia.aws.eks@masmovil.com',
      sdm: 'Rodrigo Méndez · Head of Cloud Platform (+34 611 222 306)',
      hours: '24x7 Incident Support',
      platformUrl: 'https://confluence.masmovil.com/display/OPS/AWS+EKS+OnCall'
    },
    {
      id: 'cont-mm-05',
      brand: 'masmovil',
      domain: 'IAM',
      system: 'Keycloak SSO & Okta Identity MasMóvil',
      name: 'Guardia Identidad & Gestión de Accesos MM',
      provider: 'MM Cyber & Identity Operations',
      level: 'N2 / N3',
      role: 'Tokens OAuth2, Autenticación y Single Sign-On',
      phone: '+34 91 333 4507',
      ext: '54507',
      email: 'guardia.iam.keycloak@masmovil.com',
      sdm: 'Lucía Ramos · IAM Tech Lead (+34 611 222 307)',
      hours: '24x7 On-Call',
      platformUrl: 'https://confluence.masmovil.com/display/OPS/Keycloak+SSO'
    },
    {
      id: 'cont-mm-06',
      brand: 'masmovil',
      domain: 'NETWORK',
      system: 'NOC MasMóvil / Red de Transmisión & Fibra',
      name: 'Guardia Red Transporte IP & Fibra MasMóvil',
      provider: 'MM Network Operations / ZTE Support',
      level: 'N2 / N3',
      role: 'Troncales de Fibra, BGP & Enrutamiento Core',
      phone: '+34 91 333 4508',
      ext: '54508',
      email: 'guardia.noc.transmision@masmovil.com',
      sdm: 'Gonzalo Pardo · NOC Lead (+34 611 222 308)',
      hours: '24x7 Turno Continuo NOC',
      platformUrl: 'https://confluence.masmovil.com/display/OPS/NOC+Network+OnCall'
    }
  ];

  function detectIncidentBrand(inc) {
    if (!inc) return 'orange';
    const textToScan = [
      inc.id || '',
      inc.titulo || '',
      inc.descripcion || '',
      Array.isArray(inc.sistemas) ? inc.sistemas.join(' ') : (inc.sistemas || ''),
      inc.evaluacion?.proceso || '',
      inc.evaluacion?.impacto_justificacion || '',
      inc.evaluacion?.criterio || ''
    ].join(' ').toLowerCase();

    const mmKeywords = ['masmovil', 'másmóvil', 'krt', 'yoigo', 'euskaltel', 'telecable', 'r cable', 'matrix', 'kong', 'netcracker', 'salesforce mm', 'aws eks', 'keycloak'];
    const isMasmovil = mmKeywords.some(kw => textToScan.includes(kw));
    return isMasmovil ? 'masmovil' : 'orange';
  }

  function updateCommsBrandBadge(brand) {
    const isOrange = brand === 'orange';
    if (dom.commsBrandIndicator) {
      dom.commsBrandIndicator.className = 'comms-brand-badge brand-' + brand;
    }
    if (dom.commsBrandIcon) {
      dom.commsBrandIcon.textContent = isOrange ? '🟠' : '🟡';
    }
    if (dom.commsBrandText) {
      dom.commsBrandText.innerHTML = isOrange ? 'Entorno: <strong>Orange / Jazztel</strong>' : 'Entorno: <strong>MasMóvil / KRT</strong>';
    }
    if (dom.commsBrandPlatform) {
      dom.commsBrandPlatform.textContent = isOrange ? 'Directorio GRIAL' : 'Directorio Confluence';
    }

    // Actualizar botón enlace a plataforma oficial
    if (dom.commsPlatformDirectLink) {
      if (isOrange) {
        dom.commsPlatformDirectLink.href = 'https://grial.orange.es';
        dom.commsPlatformDirectLink.innerHTML = '<span>Abrir GRIAL Orange</span> <span aria-hidden="true">↗</span>';
        dom.commsPlatformDirectLink.title = 'Abrir directorio oficial GRIAL Orange en pestaña nueva';
      } else {
        dom.commsPlatformDirectLink.href = 'https://confluence.masmovil.com';
        dom.commsPlatformDirectLink.innerHTML = '<span>Abrir Confluence MM</span> <span aria-hidden="true">↗</span>';
        dom.commsPlatformDirectLink.title = 'Abrir directorio oficial Confluence MasMóvil en pestaña nueva';
      }
    }

    // Sincronizar botones de marca en pestaña de contactos
    if (dom.btnBrandOrange && dom.btnBrandMasmovil) {
      if (isOrange) {
        dom.btnBrandOrange.classList.add('is-active');
        dom.btnBrandMasmovil.classList.remove('is-active');
      } else {
        dom.btnBrandOrange.classList.remove('is-active');
        dom.btnBrandMasmovil.classList.add('is-active');
      }
    }
  }

  function updateCommsLinkedTicketBadge(inc) {
    if (!dom.commsLinkedTicketBadge) return;
    if (inc && inc.id) {
      dom.commsLinkedTicketBadge.className = 'comms-linked-ticket-badge is-linked';
      if (dom.commsLinkedTicketIcon) dom.commsLinkedTicketIcon.textContent = '📌';
      if (dom.commsLinkedTicketText) {
        const sev = inc.prioridad_sugerida || 'SL1';
        dom.commsLinkedTicketText.textContent = `Ticket Vinculado: ${inc.id} (${sev})`;
      }
    } else {
      dom.commsLinkedTicketBadge.className = 'comms-linked-ticket-badge is-general';
      if (dom.commsLinkedTicketIcon) dom.commsLinkedTicketIcon.textContent = '🌐';
      if (dom.commsLinkedTicketText) {
        dom.commsLinkedTicketText.textContent = 'Despacho General · Sin ticket vinculado';
      }
    }
  }

  function countWords(str) {
    if (!str || typeof str !== 'string') return 0;
    const tokens = str.trim().split(/\s+/).filter(Boolean);
    return tokens.length;
  }

  function updateWordCounters() {
    // 1. Versión Completa (hasta 90 palabras)
    if (dom.tplTextCompleto && dom.counterCompleto) {
      const words = countWords(dom.tplTextCompleto.value);
      if (words > 90) {
        dom.counterCompleto.textContent = `${words} / 90 palabras ⚠️ (Excede el límite normativo)`;
        dom.counterCompleto.className = 'comms-word-counter is-warning';
      } else {
        dom.counterCompleto.textContent = `${words} / 90 palabras`;
        dom.counterCompleto.className = 'comms-word-counter is-valid';
      }
    }

    // 2. Versión Breve (hasta 30 palabras)
    if (dom.tplTextBreve && dom.counterBreve) {
      const words = countWords(dom.tplTextBreve.value);
      if (words > 30) {
        dom.counterBreve.textContent = `${words} / 30 palabras ⚠️ (Excede el límite normativo)`;
        dom.counterBreve.className = 'comms-word-counter is-warning';
      } else {
        dom.counterBreve.textContent = `${words} / 30 palabras`;
        dom.counterBreve.className = 'comms-word-counter is-valid';
      }
    }
  }

  function generateDynamicTemplates(inc, phase = 'inicial') {
    if (!inc) {
      return {
        completo: '',
        breve: '',
        meta: { sistemas: '-', impacto: '-', inicio: '-', proveedor: '-', workaround: '-', duracion: '-' }
      };
    }

    const brand = detectIncidentBrand(inc);
    const evaluacion = inc.evaluacion || {};
    const sistemas = Array.isArray(inc.sistemas) ? inc.sistemas.join(', ') : (inc.sistemas || 'Sistemas Core');
    const proceso = evaluacion.proceso || evaluacion.proceso_negocio || 'Atención al Cliente (ATC)';
    const criterio = evaluacion.criterio || 'Regla de Oro N1';
    const resumenIa = inc.resumen_ia || {};

    const minsElapsed = evaluacion.minutos_desde_apertura || 25;
    const totalDurationText = formatAgingMinutes(minsElapsed);
    const inicioStr = evaluacion.fecha_apertura ? evaluacion.fecha_apertura.slice(11, 16) + 'h' : '14:15h';

    // Métricas cuantitativas resumidas
    const metrics = evaluacion.metricas_cuantitativas || {};
    const mParts = [];
    if (metrics.sedes != null) mParts.push(`${metrics.sedes} sedes`);
    if (metrics.usuarios != null) mParts.push(`${metrics.usuarios.toLocaleString('es-ES')} usuarios`);
    if (metrics.desviacion_pct != null) mParts.push(`${metrics.desviacion_pct}% desviación`);
    const metricsLabel = mParts.length > 0 ? mParts.join(', ') : 'afectación transaccional activa';

    // Proveedores según sistema y marca
    let proveedores = brand === 'masmovil' ? 'Accenture Interactive, DevOps MM y SRE' : 'Indra Sistemas y Kyndryl';
    if (sistemas.toLowerCase().includes('tibco')) proveedores = 'Sopra Steria Middleware y Arquitectura';
    if (sistemas.toLowerCase().includes('facturación') || sistemas.toLowerCase().includes('hpfms')) proveedores = 'Ericsson España y DXC Technology';

    // Workaround
    const workaroundVal = evaluacion.workaround || 'Mitigación técnica en evaluación con IM-CSO';
    const workaroundSentence = evaluacion.workaround
      ? `Workaround activo autorizado por IM-CSO: ${evaluacion.workaround}.`
      : 'Workaround operativo en validación coordinado con IM-CSO.';
    const workaroundShort = evaluacion.workaround ? 'Workaround IM-CSO activo' : 'Mitigación en curso';

    // Causa raíz / Diagnóstico
    const diagRaw = resumenIa.problema || 'degradación en pool de hilos y saturación de conexiones';
    const diagShort = diagRaw.length > 55 ? diagRaw.slice(0, 52) + '...' : diagRaw;
    const causaRaw = resumenIa.solucion || resumenIa.problema || 'bloqueo transaccional por saturación de hilos en servidor';
    const causaShort = causaRaw.length > 60 ? causaRaw.slice(0, 57) + '...' : causaRaw;

    let completo = '';
    let breve = '';

    if (phase === 'inicial') {
      completo = `[NOTIFICACIÓN INICIAL SL1] Declarada emergencia crítica en ${sistemas} afectando ${proceso} desde las ${inicioStr}. Umbral superado: ${criterio} (${metricsLabel}). War Room activa con Incident Management CSO (IM-CSO) y resolutores técnicos (${proveedores}) coordinando diagnóstico y mitigación inmediata. Servicios alternativos en evaluación operativa. Próxima actualización formal a Dirección en 60 minutos o de forma inmediata ante cualquier cambio de criticidad.`;
      breve = `[SL1 INICIAL] Emergencia en ${sistemas} (${proceso}). Impacto: ${metricsLabel}. War Room activa con IM-CSO y soporte. Mitigación en curso.`;
    } else if (phase === 'actualizacion') {
      completo = `[ACTUALIZACIÓN SL1 - T+${minsElapsed}m] Continúa la gestión de la emergencia en ${sistemas} (${proceso}). Diagnóstico técnico en curso: ${diagShort}. ${workaroundSentence} Equipos resolutores (${proveedores}) ejecutan acciones de mitigación coordinadas por Incident Management CSO en War Room. Se monitorizan indicadores de recuperación. Próxima actualización formal en 60 minutos o ante variación significativa del impacto.`;
      breve = `[SL1 UPDATE T+${minsElapsed}m] ${sistemas}: Diagnóstico en curso. ${workaroundShort}. War Room activa con IM-CSO. Próximo checkpoint en 60m.`;
    } else {
      // Cierre / Resolución
      completo = `[RESOLUCIÓN Y CIERRE SL1] Restablecido al 100% el servicio en ${sistemas} tras ${totalDurationText} de afectación en ${proceso}. Causa técnica identificada y corregida: ${causaShort}. Pruebas de validación del servicio satisfactorias con canales de atención y monitorización estable con IM-CSO. Se convoca formalmente la sesión de Post-Incident Review (PIR) blameless dentro de las próximas 48 horas.`;
      breve = `[SL1 RESUELTO] Normalizado el servicio en ${sistemas} (${proceso}) tras ${totalDurationText}. Validación satisfactoria. Post-Mortem (PIR) programado en 48h con IM-CSO.`;
    }

    // Si la incidencia ya cuenta con mensaje oficial pre-redactado por el agente incident-reporter, priorizarlo
    const phaseKey = phase === 'inicial' ? 'apertura' : (phase === 'actualizacion' ? 'seguimiento' : 'cierre');
    const msgPre = inc.mensajes_ejecutivos && inc.mensajes_ejecutivos[phaseKey];
    if (msgPre && msgPre.completo && msgPre.estado !== 'pendiente') {
      completo = msgPre.completo;
      if (msgPre.breve) breve = msgPre.breve;
    }

    return {
      completo,
      breve,
      meta: {
        sistemas,
        impacto: `${criterio} (${metricsLabel})`,
        inicio: inicioStr,
        proveedor: proveedores,
        workaround: workaroundVal,
        duracion: totalDurationText
      }
    };
  }

  function renderCommsTemplateTab(inc, phase = 'inicial') {
    state.activeCommsPhase = phase;

    // Actualizar botones de fase
    document.querySelectorAll('.comms-phase-btn').forEach(btn => {
      const p = btn.getAttribute('data-phase');
      if (p === phase) {
        btn.classList.add('is-active');
      } else {
        btn.classList.remove('is-active');
      }
    });

    // Actualizar SLA etiqueta
    if (dom.tplPhaseSla) {
      if (phase === 'inicial') {
        dom.tplPhaseSla.textContent = '⏱️ SLA: ≤ 20 min desde apertura';
      } else if (phase === 'actualizacion') {
        dom.tplPhaseSla.textContent = '⏱️ Frecuencia: Cada 60 min (o <30m ante cambio de impacto)';
      } else {
        dom.tplPhaseSla.textContent = '⏱️ SLA: Inmediato tras validación de estabilidad';
      }
    }

    if (!inc) return;

    const data = generateDynamicTemplates(inc, phase);

    // Actualizar grid de metadatos (con tooltips accesibles)
    if (dom.tplMetaSistemas) {
      dom.tplMetaSistemas.textContent = data.meta.sistemas;
      dom.tplMetaSistemas.title = data.meta.sistemas;
    }
    if (dom.tplMetaImpacto) {
      dom.tplMetaImpacto.textContent = data.meta.impacto;
      dom.tplMetaImpacto.title = data.meta.impacto;
    }
    if (dom.tplMetaProveedor) {
      dom.tplMetaProveedor.textContent = data.meta.proveedor;
      dom.tplMetaProveedor.title = data.meta.proveedor;
    }
    if (dom.tplMetaWorkaround) {
      dom.tplMetaWorkaround.textContent = data.meta.workaround;
      dom.tplMetaWorkaround.title = data.meta.workaround;
    }
    if (dom.tplMetaDuracion) {
      dom.tplMetaDuracion.textContent = data.meta.duracion;
      dom.tplMetaDuracion.title = data.meta.duracion;
    }

    // Comprobar si existe borrador guardado en LocalStorage (US-03 Zero-Data-Loss)
    let hasDraft = false;
    let textCompleto = data.completo;
    let textBreve = data.breve;

    try {
      const draftComp = localStorage.getItem(`triage_draft_tpl_comp_${inc.id}_${phase}`);
      const draftBrev = localStorage.getItem(`triage_draft_tpl_brev_${inc.id}_${phase}`);
      if (draftComp !== null && draftComp.trim() !== '' && draftComp !== data.completo) {
        textCompleto = draftComp;
        hasDraft = true;
      }
      if (draftBrev !== null && draftBrev.trim() !== '' && draftBrev !== data.breve) {
        textBreve = draftBrev;
        hasDraft = true;
      }
    } catch (_) {}

    if (dom.tplDraftAlert) {
      dom.tplDraftAlert.style.display = hasDraft ? 'flex' : 'none';
    }

    // Actualizar textareas
    if (dom.tplTextCompleto) dom.tplTextCompleto.value = textCompleto;
    if (dom.tplTextBreve) dom.tplTextBreve.value = textBreve;

    updateWordCounters();
  }

  function transferTemplateToGateway() {
    if (!state.activeCommsIncId) return;
    const inc = state.incidents.find(i => i.id === state.activeCommsIncId);
    if (!inc) return;

    const brand = detectIncidentBrand(inc);
    const brandTag = brand === 'masmovil' ? 'MASMÓVIL' : 'ORANGE';
    const sistemas = Array.isArray(inc.sistemas) ? inc.sistemas.join(', ') : (inc.sistemas || 'Sistemas Core');

    let phaseTitle = 'Notificación Inicial';
    if (state.activeCommsPhase === 'actualizacion') phaseTitle = 'Actualización de Seguimiento';
    if (state.activeCommsPhase === 'cierre') phaseTitle = 'Resolución y Cierre Definitivo';

    const subject = `[EMERGENCIA SL1][${brandTag}] ${inc.id} - ${sistemas} - ${phaseTitle}`;

    // Determinar qué cuerpo usar según canal seleccionado en gateway
    const selectedChannel = document.querySelector('input[name="gw-channel"]:checked')?.value || 'dual';
    let body = dom.tplTextCompleto ? dom.tplTextCompleto.value.trim() : '';
    if (selectedChannel === 'sms' && dom.tplTextBreve) {
      body = dom.tplTextBreve.value.trim();
    }

    if (dom.gwSubject) dom.gwSubject.value = subject;
    if (dom.gwBody) dom.gwBody.value = body;

    // Cerrar modal del Generador de Plantillas (Módulo 2)
    if (dom.modalExecutiveComm) {
      dom.modalExecutiveComm.classList.remove('open');
    }

    // Abrir Centro de Comunicaciones (Módulo 3) directamente en la pestaña del Gateway
    openCommsCenterModal(inc.id, 'tab-gateway');
    showToast('Plantilla cargada en el Gateway de la Web de Explotación (Módulo 3)', 'info');
  }

  function getCommsHistory(incId) {
    if (!state.commsDispatchHistory) state.commsDispatchHistory = {};
    if (!state.commsDispatchHistory[incId]) {
      try {
        const stored = localStorage.getItem('comms_history_' + incId);
        if (stored) {
          state.commsDispatchHistory[incId] = JSON.parse(stored);
        } else {
          state.commsDispatchHistory[incId] = [];
        }
      } catch (_) {
        state.commsDispatchHistory[incId] = [];
      }
    }
    return state.commsDispatchHistory[incId];
  }

  function saveCommsHistory(incId, list) {
    if (!state.commsDispatchHistory) state.commsDispatchHistory = {};
    state.commsDispatchHistory[incId] = list;
    try {
      localStorage.setItem('comms_history_' + incId, JSON.stringify(list));
    } catch (_) {}
  }

  function renderGatewayHistory(incId) {
    if (!dom.gwHistoryList) return;
    const list = getCommsHistory(incId);
    if (!list || list.length === 0) {
      const emptyNote = incId && incId !== 'GENERAL'
        ? `No hay despachos registrados para la incidencia ${escapeHtml(incId)} en la Web de Explotación.`
        : 'No hay despachos registrados en la Web de Explotación.';
      dom.gwHistoryList.innerHTML = `
        <div style="text-align: center; color: #6B7280; font-size: 12px; padding: 12px 0;">
          ${emptyNote}
        </div>
      `;
      return;
    }

    const html = list.map(item => `
      <div class="comms-gw-history-entry">
        <div style="display: flex; flex-direction: column; gap: 2px;">
          <div style="display: flex; align-items: center; gap: 8px;">
            <strong style="color: #111827;">${escapeHtml(item.asunto)}</strong>
            <span style="background: #D1FAE5; color: #065F46; padding: 1px 6px; border-radius: 3px; font-weight: 700; font-size: 10.5px;">${escapeHtml(item.estado)}</span>
          </div>
          <div style="font-size: 11.5px; color: #4B5563;">${escapeHtml(item.cuerpo)}</div>
          <div style="font-size: 10.5px; color: #6B7280; margin-top: 2px;">
            Canal: <strong>${escapeHtml((item.canal || 'dual').toUpperCase())}</strong> · Colectivos: ${escapeHtml((item.colectivos || []).join(', '))} · Emisor: ${escapeHtml(item.autor)}
          </div>
        </div>
        <div style="font-family: var(--font-mono); font-size: 11px; color: #6B7280; white-space: nowrap; margin-left: 12px;">
          ⏱️ ${escapeHtml(item.timestamp)}
        </div>
      </div>
    `).join('');

    dom.gwHistoryList.innerHTML = html;
  }

  function dispatchGatewayMessage() {
    const incId = state.activeCommsIncId || 'GENERAL';

    const subject = dom.gwSubject ? dom.gwSubject.value.trim() : '';
    const body = dom.gwBody ? dom.gwBody.value.trim() : '';

    if (!subject) {
      showToast('El asunto de la notificación no puede estar vacío', 'warning');
      if (dom.gwSubject) dom.gwSubject.focus();
      return;
    }

    if (!body) {
      showToast('El cuerpo de la notificación no puede estar vacío', 'warning');
      if (dom.gwBody) dom.gwBody.focus();
      return;
    }

    const selectedChannel = document.querySelector('input[name="gw-channel"]:checked')?.value || 'dual';
    const checkedGroups = Array.from(document.querySelectorAll('input[name="gw-group"]:checked')).map(cb => cb.value);

    if (checkedGroups.length === 0) {
      showToast('Debes marcar al menos un colectivo de distribución', 'warning');
      return;
    }

    const groupNamesMap = {
      direccion: 'Dirección (C-Level / Jefaturas)',
      resolutores: 'Resolutores N2/N3 & Proveedores',
      cso: 'Customer & Service Ops (IM-CSO)',
      atc: 'Atención al Cliente (ATC/Tiendas)'
    };
    const collectiveLabels = checkedGroups.map(k => groupNamesMap[k] || k);

    const nowStr = new Date().toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    const record = {
      id: 'EXP-' + Date.now().toString(36).toUpperCase(),
      incId,
      timestamp: nowStr,
      canal: selectedChannel,
      colectivos: collectiveLabels,
      asunto: subject,
      cuerpo: body,
      autor: state.defaultIncidentManager,
      estado: 'Despachado OK (Web de Explotación)'
    };

    const history = getCommsHistory(incId);
    history.unshift(record);
    saveCommsHistory(incId, history);

    // Si es notificación inicial (<20 min) o no se había marcado, completar reloj de 20 min
    const escState = state.orchestratorEscalations[incId] || {};
    if (state.activeCommsPhase === 'inicial' || !escState.commDone) {
      escState.commDone = true;
      state.orchestratorEscalations[incId] = escState;
      try {
        localStorage.setItem('emergency_esc_' + incId, JSON.stringify(escState));
      } catch (_) {}
      updateOrchestratorClocks();
    }

    // Registrar en la bitácora auditable del ticket
    addLogEntry(
      incId,
      'NOTIFICACION',
      '📡 Despacho Web de Explotación',
      `Notificación oficial emitida vía canal [${selectedChannel.toUpperCase()}] a ${collectiveLabels.length} colectivos: "${subject}". Despachado por ${state.defaultIncidentManager}.`,
      'role-notificacion'
    );

    // Limpiar borrador guardado tras despacho exitoso (US-03)
    try {
      localStorage.removeItem('triage_draft_gw_subj_' + incId);
      localStorage.removeItem('triage_draft_gw_body_' + incId);
    } catch (_) {}

    renderGatewayHistory(incId);
    showToast('Notificación despachada con éxito a través de Web de Explotación Orange', 'success');
  }

  function renderContactMatrices(brandFilter, searchQuery, domainFilter) {
    if (!dom.contactsCardsGrid) return;
    const brand = brandFilter || state.activeContactsBrand || 'orange';
    const query = (searchQuery || '').trim().toLowerCase();
    const domain = domainFilter || state.activeContactsDomain || 'ALL';

    let filtered = CONTACTS_DIRECTORY.filter(c => c.brand === brand);

    if (domain !== 'ALL') {
      filtered = filtered.filter(c => c.domain === domain);
    }

    if (query) {
      filtered = filtered.filter(c => {
        const haystack = [
          c.system,
          c.name,
          c.provider,
          c.role,
          c.phone,
          c.ext,
          c.sdm,
          c.email,
          c.domain
        ].join(' ').toLowerCase();
        return haystack.includes(query);
      });
    }

    if (filtered.length === 0) {
      dom.contactsCardsGrid.innerHTML = `
        <div style="grid-column: 1 / -1; text-align: center; padding: 32px 16px; background: #FFFFFF; border: 1px dashed #CBD5E1; border-radius: 8px;">
          <span style="font-size: 28px;" aria-hidden="true">🔍</span>
          <h4 style="margin: 8px 0 4px 0; color: #1E293B; font-size: 14px;">No se encontraron contactos de guardia</h4>
          <p style="margin: 0; font-size: 12px; color: #64748B;">Intenta con otros términos de búsqueda o cambia el filtro de dominio funcional.</p>
        </div>
      `;
      return;
    }

    const isOrange = brand === 'orange';
    const platformName = isOrange ? 'GRIAL Orange' : 'Confluence MM';

    const cardsHtml = filtered.map(c => {
      let levelClass = 'comms-level-n2';
      if (c.level.includes('N3')) levelClass = 'comms-level-n3';
      if (c.level.toLowerCase().includes('jefatura')) levelClass = 'comms-level-sdm';

      return `
        <div class="comms-contact-card" data-contact-id="${escapeHtml(c.id)}">
          <div class="comms-card-top">
            <div>
              <div class="comms-card-team">${escapeHtml(c.name)}</div>
              <div class="comms-card-domain">Dominio: <strong>${escapeHtml(c.domain)}</strong> · ${escapeHtml(c.provider)}</div>
            </div>
            <div class="comms-card-badges">
              <span class="comms-badge-level ${levelClass}">${escapeHtml(c.level)}</span>
            </div>
          </div>

          <div class="comms-card-systems">
            <div style="font-weight: 700; color: #1F2937; margin-bottom: 2px;">🖥️ ${escapeHtml(c.system)}</div>
            <div>👔 <strong>SDM / Lead:</strong> ${escapeHtml(c.sdm)}</div>
            <div>⏰ <strong>Disponibilidad:</strong> ${escapeHtml(c.hours)}</div>
            <div>✉️ <strong>Email:</strong> ${escapeHtml(c.email)}</div>
          </div>

          <div class="comms-card-actions">
            <div style="display: flex; align-items: center; gap: 6px;">
              <a href="tel:${escapeHtml(c.phone.replace(/\s+/g, ''))}" class="comms-phone-btn" title="Llamar directamente al teléfono de guardia">
                <span aria-hidden="true">📞</span> <span>${escapeHtml(c.phone)}</span>
              </a>
              <span style="font-family: var(--font-mono); font-size: 11px; color: #6B7280;">(Ext: ${escapeHtml(c.ext)})</span>
            </div>

            <div style="display: flex; align-items: center; gap: 6px;">
              <button type="button" class="triage-btn triage-btn-sm contact-btn-copy-phone" data-phone="${escapeHtml(c.phone)}" title="Copiar teléfono al portapapeles">
                <span aria-hidden="true">📋</span> <span>Copiar</span>
              </button>
              <button type="button" class="triage-btn triage-btn-sm contact-btn-log-call" data-contact-id="${escapeHtml(c.id)}" style="background: #FF7900; color: #FFFFFF; border-color: #FF7900; font-weight: 600;" title="Registrar llamada de guardia en la bitácora del ticket">
                <span aria-hidden="true">📝</span> <span>Registrar</span>
              </button>
              <a href="${escapeHtml(c.platformUrl)}" target="_blank" rel="noopener noreferrer" class="triage-btn triage-btn-sm" style="border: 1px solid #D1D5DB; font-weight: 600;" title="Abrir ficha en ${platformName}">
                <span>${platformName}</span> <span aria-hidden="true">↗</span>
              </a>
            </div>
          </div>
        </div>
      `;
    }).join('');

    dom.contactsCardsGrid.innerHTML = cardsHtml;

    // Vincular eventos internos de las tarjetas
    dom.contactsCardsGrid.querySelectorAll('.contact-btn-copy-phone').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const phone = btn.getAttribute('data-phone');
        if (phone) copyToClipboard(phone, `Teléfono ${phone} copiado al portapapeles`);
      });
    });

    dom.contactsCardsGrid.querySelectorAll('.contact-btn-log-call').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const contactId = btn.getAttribute('data-contact-id');
        const contact = CONTACTS_DIRECTORY.find(c => c.id === contactId);
        if (!contact) return;
        const targetIncId = state.activeCommsIncId || state.activeOrchIncId;
        if (!targetIncId) {
          showToast('Selecciona primero un ticket para registrar la llamada en su bitácora', 'warning');
          return;
        }
        addLogEntry(
          targetIncId,
          'ESCALADO',
          '📞 Contacto Telefónico de Guardia',
          `Llamada de guardia registrada a ${contact.system} (${contact.level}). Contacto: ${contact.sdm} · Tel: ${contact.phone} (Ext: ${contact.ext}). Soporte: ${contact.provider}.`,
          'role-resolutor'
        );
        showToast(`Llamada a guardia de ${contact.system} registrada en la bitácora`, 'success');
      });
    });
  }

  function switchCommsTab(tabId) {
    const validTab = (tabId === 'tab-contacts') ? 'tab-contacts' : 'tab-gateway';
    state.activeCommsTab = validTab;

    // Pestañas botones
    [dom.tabBtnGateway, dom.tabBtnContacts].forEach(btn => {
      if (!btn) return;
      const target = btn.getAttribute('data-tab');
      if (target === validTab) {
        btn.classList.add('is-active');
        btn.setAttribute('aria-selected', 'true');
      } else {
        btn.classList.remove('is-active');
        btn.setAttribute('aria-selected', 'false');
      }
    });

    // Paneles
    [dom.tabGateway, dom.tabContacts].forEach(panel => {
      if (!panel) return;
      if (panel.id === validTab) {
        panel.classList.add('is-active');
      } else {
        panel.classList.remove('is-active');
      }
    });
  }

  function openCommsCenterModal(incId, targetTab = 'tab-gateway') {
    if (!dom.modalCommsCenter) return;

    let inc = null;
    if (incId) {
      inc = state.incidents.find(i => i.id === incId);
    }

    const effectiveIncId = inc ? inc.id : null;
    state.activeCommsIncId = effectiveIncId;

    // Actualizar badge pasivo de contexto operativo (Opción B)
    updateCommsLinkedTicketBadge(inc);

    // Detectar marca corporativa
    const brand = inc ? detectIncidentBrand(inc) : (state.activeContactsBrand || 'orange');
    state.activeContactsBrand = brand;
    updateCommsBrandBadge(brand);

    // Renderizar historial de despachos del gateway para este ticket o general
    renderGatewayHistory(effectiveIncId || 'GENERAL');

    // Restaurar borrador de Gateway si existe (US-03 Zero-Data-Loss)
    try {
      const draftSubj = localStorage.getItem('triage_draft_gw_subj_' + (effectiveIncId || 'GENERAL'));
      const draftBody = localStorage.getItem('triage_draft_gw_body_' + (effectiveIncId || 'GENERAL'));
      if (draftSubj && dom.gwSubject) dom.gwSubject.value = draftSubj;
      if (draftBody && dom.gwBody) dom.gwBody.value = draftBody;
    } catch (_) {}

    // Renderizar directorio de contactos
    renderContactMatrices(state.activeContactsBrand, dom.contactsSearchInput ? dom.contactsSearchInput.value : '', state.activeContactsDomain);

    // Activar pestaña solicitada
    switchCommsTab(targetTab || 'tab-gateway');

    // Abrir modal
    dom.modalCommsCenter.classList.add('open');
  }

  function closeCommsCenterModal() {
    if (dom.modalCommsCenter) {
      dom.modalCommsCenter.classList.remove('open');
    }
  }

  // Módulo 2: Generador de Plantillas Dinámicas de Emergencia
  function openExecutiveCommModal(incId, phase = 'inicial') {
    if (!dom.modalExecutiveComm) return;

    let inc = state.incidents.find(i => i.id === incId);
    if (!inc && state.activeOrchIncId) {
      inc = state.incidents.find(i => i.id === state.activeOrchIncId);
    }
    if (!inc) {
      inc = state.incidents.find(i => i.prioridad_sugerida === 'P1') || state.incidents[0];
    }
    if (!inc) return;

    state.activeCommsIncId = inc.id;
    state.activeCommsPhase = phase || 'inicial';

    const execModalIncId = document.getElementById('exec-modal-inc-id');
    if (execModalIncId) {
      execModalIncId.textContent = inc.id;
    }

    // Renderizar plantilla para la fase seleccionada
    renderCommsTemplateTab(inc, state.activeCommsPhase);

    // Abrir modal del Generador de Plantillas (Módulo 2)
    dom.modalExecutiveComm.classList.add('open');
  }

  function startOrchestratorClocks(inc) {
    if (state.clocksTicker) {
      clearInterval(state.clocksTicker);
      state.clocksTicker = null;
    }
    updateOrchestratorClocks();
    state.clocksTicker = setInterval(updateOrchestratorClocks, 1000);
  }

  function updateOrchestratorClocks() {
    if (!state.activeOrchIncId) return;
    const inc = state.incidents.find(i => i.id === state.activeOrchIncId);
    if (!inc) return;

    const evaluacion = inc.evaluacion || {};
    const baseMinutes = evaluacion.minutos_desde_apertura || 0;

    // 1. Reloj Global Remedy (envejecimiento acumulado del ticket en N1/Remedy)
    const remedyElapsedSeconds = Math.max(0, Math.floor(baseMinutes * 60) + Math.floor((Date.now() - (state.lastInspectionEpoch || Date.now())) / 1000));
    const remedyElapsedMinutes = Math.floor(remedyElapsedSeconds / 60);

    // 2. Reloj Táctico de Crisis (T0 = momento de activación formal SL1 en el Orquestador)
    const activationEpoch = state.orchestratorActivations[state.activeOrchIncId] || Date.now();
    const crisisElapsedSeconds = Math.max(0, Math.floor((Date.now() - activationEpoch) / 1000));
    const crisisElapsedMinutes = Math.floor(crisisElapsedSeconds / 60);
    const crisisElapsedSec = crisisElapsedSeconds % 60;
    const crisisPadSec = crisisElapsedSec < 10 ? '0' + crisisElapsedSec : crisisElapsedSec;

    // Actualizar badges en la cabecera del orquestador
    if (dom.orchAgingTag) {
      dom.orchAgingTag.textContent = `📋 Global Remedy: ${formatAgingMinutes(remedyElapsedMinutes)}`;
    }
    if (dom.orchCrisisTimeTag) {
      dom.orchCrisisTimeTag.textContent = `🚨 Crisis SL1: ${crisisElapsedMinutes}m ${crisisPadSec}s`;
    }

    // Sincronizar botones de modo de tiempo
    const isCrisisMode = state.clockTimeBase === 'crisis';
    if (dom.btnModeCrisis && dom.btnModeRemedy) {
      if (isCrisisMode) {
        dom.btnModeCrisis.classList.add('is-active');
        dom.btnModeRemedy.classList.remove('is-active');
      } else {
        dom.btnModeCrisis.classList.remove('is-active');
        dom.btnModeRemedy.classList.add('is-active');
      }
    }

    // Tiempo activo para evaluar los 4 relojes de escalado
    const elapsedSeconds = isCrisisMode ? crisisElapsedSeconds : remedyElapsedSeconds;
    const escState = state.orchestratorEscalations[state.activeOrchIncId] || {};

    // 1. Reloj 20 min: SLA 1ª Notificación a Dirección
    if (dom.clock20mCard && dom.clock20mTimer && dom.clock20mFill && dom.clock20mStatusText) {
      const limit = 20 * 60; // 1200 seg
      const pct = Math.min(100, Math.round((elapsedSeconds / limit) * 100));
      dom.clock20mFill.style.width = pct + '%';

      if (escState.commDone) {
        dom.clock20mCard.className = 'orch-clock-card is-completed';
        dom.clock20mTimer.textContent = 'Enviada';
        dom.clock20mStatusText.textContent = '1ª Notificación Emitida';
        if (dom.btnAction20m) {
          dom.btnAction20m.innerHTML = '<span>✅ Ver Notificación</span>';
        }
      } else if (elapsedSeconds >= limit) {
        dom.clock20mCard.className = 'orch-clock-card is-alarm';
        const overdue = Math.floor((elapsedSeconds - limit) / 60);
        dom.clock20mTimer.textContent = `+${overdue}m SLA`;
        dom.clock20mStatusText.textContent = isCrisisMode ? '🚨 SLA 20m War Room Excedido' : '🚨 SLA 20m Remedy Excedido';
        if (dom.btnAction20m) {
          dom.btnAction20m.innerHTML = '<span>⚠️ Emitir Notificación Ya</span>';
        }
      } else {
        const remaining = limit - elapsedSeconds;
        const remM = Math.floor(remaining / 60);
        const remS = remaining % 60;
        dom.clock20mTimer.textContent = `${remM}:${remS < 10 ? '0' : ''}${remS}`;
        if (elapsedSeconds >= 15 * 60) {
          dom.clock20mCard.className = 'orch-clock-card is-warning';
          dom.clock20mStatusText.textContent = '⚠️ Alerta Próxima SLA';
        } else {
          dom.clock20mCard.className = 'orch-clock-card is-ok';
          dom.clock20mStatusText.textContent = isCrisisMode ? 'Cuenta atrás (T0 SL1)' : 'Cuenta atrás (Remedy)';
        }
        if (dom.btnAction20m) {
          dom.btnAction20m.innerHTML = '<span>⚠️ Emitir Notificación Ya</span>';
        }
      }
    }

    // 2. Reloj 45 min: 1er Escalado Telefónico N2/N3
    if (dom.clock45mCard && dom.clock45mTimer && dom.clock45mFill && dom.clock45mStatusText) {
      const limit = 45 * 60; // 2700 seg
      const pct = Math.min(100, Math.round((elapsedSeconds / limit) * 100));
      dom.clock45mFill.style.width = pct + '%';

      if (escState.esc45Done) {
        dom.clock45mCard.className = 'orch-clock-card is-completed';
        dom.clock45mTimer.textContent = 'Confirmado';
        dom.clock45mStatusText.textContent = 'Escalado N2/N3 Registrado';
      } else if (elapsedSeconds >= limit) {
        dom.clock45mCard.className = 'orch-clock-card is-alarm';
        const overdue = Math.floor((elapsedSeconds - limit) / 60);
        dom.clock45mTimer.textContent = `+${overdue}m Alarma`;
        dom.clock45mStatusText.textContent = '🚨 Alarma Escalado Telefónico';
      } else {
        const remaining = limit - elapsedSeconds;
        const remM = Math.floor(remaining / 60);
        const remS = remaining % 60;
        dom.clock45mTimer.textContent = `${remM}:${remS < 10 ? '0' : ''}${remS}`;
        if (elapsedSeconds >= 35 * 60) {
          dom.clock45mCard.className = 'orch-clock-card is-warning';
          dom.clock45mStatusText.textContent = '⚠️ Requiere avance técnico';
        } else {
          dom.clock45mCard.className = 'orch-clock-card is-ok';
          dom.clock45mStatusText.textContent = 'En tiempo de respuesta';
        }
      }
    }

    // 3. Reloj T+1h 45m (105 min): 2º Escalado Jerárquico
    if (dom.clock105mCard && dom.clock105mTimer && dom.clock105mFill && dom.clock105mStatusText) {
      const limit = 105 * 60; // 6300 seg
      const pct = Math.min(100, Math.round((elapsedSeconds / limit) * 100));
      dom.clock105mFill.style.width = pct + '%';

      if (escState.esc105Done) {
        dom.clock105mCard.className = 'orch-clock-card is-completed';
        dom.clock105mTimer.textContent = 'Notificado';
        dom.clock105mStatusText.textContent = '2º Escalado Jerárquico Ejecutado';
      } else if (elapsedSeconds >= limit) {
        dom.clock105mCard.className = 'orch-clock-card is-alarm';
        const overdue = Math.floor((elapsedSeconds - limit) / 60);
        dom.clock105mTimer.textContent = `+${overdue}m Jerárquico`;
        dom.clock105mStatusText.textContent = '🚨 Alarma Escalado Superior';
      } else {
        const remaining = limit - elapsedSeconds;
        const remH = Math.floor(remaining / 3600);
        const remM = Math.floor((remaining % 3600) / 60);
        dom.clock105mTimer.textContent = `${remH}h ${remM}m`;
        if (elapsedSeconds >= 90 * 60) {
          dom.clock105mCard.className = 'orch-clock-card is-warning';
          dom.clock105mStatusText.textContent = '⚠️ Alerta de escalado a Jefatura';
        } else {
          dom.clock105mCard.className = 'orch-clock-card is-ok';
          dom.clock105mStatusText.textContent = 'En monitorización';
        }
      }
    }

    // 4. Reloj >2 horas (120 min - Alarma Estancamiento IM-CSO)
    if (dom.clock120mCard && dom.clock120mTimer && dom.clock120mFill && dom.clock120mStatusText) {
      const limit = 120 * 60; // 7200 seg
      const pct = Math.min(100, Math.round((elapsedSeconds / limit) * 100));
      dom.clock120mFill.style.width = pct + '%';

      if (escState.esc120Done) {
        dom.clock120mCard.className = 'orch-clock-card is-completed';
        dom.clock120mTimer.textContent = 'Convocada';
        dom.clock120mStatusText.textContent = 'War Room Ejecutiva CSO Re-convocada';
      } else if (elapsedSeconds >= limit) {
        dom.clock120mCard.className = 'orch-clock-card orch-clock-alarm-zone is-alarm';
        const overdue = Math.floor((elapsedSeconds - limit) / 60);
        dom.clock120mTimer.textContent = `🚨 +${overdue}m Estancada`;
        dom.clock120mStatusText.textContent = '🚨 ALARMA ESTANCAMIENTO IM-CSO';
      } else {
        const remaining = limit - elapsedSeconds;
        const remH = Math.floor(remaining / 3600);
        const remM = Math.floor((remaining % 3600) / 60);
        dom.clock120mCard.className = 'orch-clock-card is-ok';
        dom.clock120mTimer.textContent = `${remH}h ${remM}m`;
        dom.clock120mStatusText.textContent = 'Monitorización IM-CSO';
      }
    }
  }

  function openEmergencyOrchestrator(incId) {
    const inc = state.incidents.find(i => i.id === incId);
    if (!inc || !dom.modalOrchestrator) return;

    state.activeOrchIncId = incId;

    // Cargar o inicializar timestamp de activación táctica de crisis (Dual Clock)
    if (!state.orchestratorActivations[incId]) {
      try {
        const storedActivation = localStorage.getItem('emergency_activation_' + incId);
        if (storedActivation) {
          state.orchestratorActivations[incId] = parseInt(storedActivation, 10);
        }
      } catch (_) {}
    }
    if (!state.orchestratorActivations[incId] || isNaN(state.orchestratorActivations[incId])) {
      state.orchestratorActivations[incId] = Date.now();
      try {
        localStorage.setItem('emergency_activation_' + incId, String(state.orchestratorActivations[incId]));
      } catch (_) {}
    }

    // Cargar estado de rollback previo si existe en localStorage
    if (state.orchestratorRollbacks[incId] === undefined) {
      try {
        const storedRollback = localStorage.getItem('emergency_rollback_' + incId);
        if (storedRollback) state.orchestratorRollbacks[incId] = JSON.parse(storedRollback);
      } catch (_) {}
    }

    // Cargar estado de escalados previo si existe en localStorage
    if (!state.orchestratorEscalations[incId]) {
      try {
        const storedEsc = localStorage.getItem('emergency_esc_' + incId);
        if (storedEsc) state.orchestratorEscalations[incId] = JSON.parse(storedEsc);
      } catch (_) {}
    }

    // 1. Cabecera del Orquestador
    if (dom.orchIncId) dom.orchIncId.textContent = incId;
    if (dom.orchSevBadge) {
      const isP1 = inc.prioridad_sugerida === 'P1';
      dom.orchSevBadge.textContent = isP1 ? 'SL1 / P1 · Crítica' : 'SL2 / P2 · Mayor';
      dom.orchSevBadge.style.background = isP1 ? '#EF4444' : '#F59E0B';
    }
    if (dom.orchStatusPill) {
      dom.orchStatusPill.textContent = inc.estatus || 'Asignado';
    }
    if (dom.orchImName) {
      dom.orchImName.textContent = state.defaultIncidentManager;
    }

    // 2. War Room Teams
    const teamsUrl = generateTeamsWarRoomUrl(incId);
    if (dom.orchTeamsUrlPreview) dom.orchTeamsUrlPreview.textContent = teamsUrl;
    if (dom.orchBtnJoinTeams) dom.orchBtnJoinTeams.href = teamsUrl;

    if (dom.orchBtnCopyTeams) {
      dom.orchBtnCopyTeams.onclick = () => {
        const text = buildTeamsWarRoomCallText(inc, teamsUrl);
        copyToClipboard(text, '¡Convocatoria oficial para Teams copiada al portapapeles!');
      };
    }

    // 3. Monitor PaP
    renderPapSection(inc);

    // 4. Bitácora / Live Incident Log
    getOrInitLog(incId, inc);
    renderTimelineEntries(incId);

    // Restaurar borrador de bitácora no guardado (US-03 Zero-Data-Loss)
    try {
      const draftLog = localStorage.getItem('triage_draft_log_' + incId);
      const draftRole = localStorage.getItem('triage_draft_role_' + incId);
      if (draftLog && draftLog.trim()) {
        if (dom.orchLogText) dom.orchLogText.value = draftLog;
        if (dom.orchLogRole && draftRole) dom.orchLogRole.value = draftRole;
        if (dom.orchLogDraftAlert) dom.orchLogDraftAlert.style.display = 'flex';
      } else {
        if (dom.orchLogText) dom.orchLogText.value = '';
        if (dom.orchLogRole) dom.orchLogRole.value = 'IM';
        if (dom.orchLogDraftAlert) dom.orchLogDraftAlert.style.display = 'none';
      }
    } catch (_) {}

    // 5. Iniciar Relojes de Escalado
    startOrchestratorClocks(inc);

    // 5.5 Plegar por defecto las secciones en Módulo 2 (Fase 1: Bitácora, War Room y Monitor de Trabajos)
    setOrchSectionCollapsed('warroom', true);
    setOrchSectionCollapsed('pap', true);
    setOrchSectionCollapsed('log', true);
    setOrchSectionCollapsed('remedy', true);
    if (dom.orchRemedyWorklogContent) {
      dom.orchRemedyWorklogContent.innerHTML = '<p style="color: var(--triage-text-muted); font-size: 13px;">Haz clic en desplegar o actualizar para consultar las notas técnicas de Remedy.</p>';
      dom.orchRemedyWorklogContent.dataset.loadedInc = '';
    }

    // 6. Abrir Modal
    dom.modalOrchestrator.classList.add('open');
    showToast(`Orquestador Operativo activado para ${incId}`, 'info');
  }

  function closeEmergencyOrchestrator() {
    if (state.clocksTicker) {
      clearInterval(state.clocksTicker);
      state.clocksTicker = null;
    }
    state.activeOrchIncId = null;
    document.querySelectorAll('.orch-clock-info-wrap.is-open').forEach(w => w.classList.remove('is-open'));
    if (dom.modalOrchestrator) {
      dom.modalOrchestrator.classList.remove('open');
    }
  }

  function setOrchSectionCollapsed(sectionName, isCollapsed) {
    let sectionEl, btnEl, headerEl;
    if (sectionName === 'warroom') {
      sectionEl = dom.orchWarRoomSection || document.getElementById('orch-war-room-section');
      btnEl = dom.btnToggleWarRoom || document.getElementById('btn-toggle-war-room');
      headerEl = dom.orchWarRoomHeader || document.getElementById('orch-war-room-header');
    } else if (sectionName === 'pap') {
      sectionEl = dom.orchPapSection || document.getElementById('orch-pap-section');
      btnEl = dom.btnTogglePap || document.getElementById('btn-toggle-pap');
      headerEl = dom.orchPapHeader || document.getElementById('orch-pap-header');
    } else if (sectionName === 'log') {
      sectionEl = dom.orchLogSection || document.getElementById('orch-log-section');
      btnEl = dom.btnToggleLog || document.getElementById('btn-toggle-log');
      headerEl = dom.orchLogHeader || document.getElementById('orch-log-header');
    } else if (sectionName === 'remedy') {
      sectionEl = dom.orchRemedySection || document.getElementById('orch-remedy-section');
      btnEl = dom.btnToggleRemedyWorklog || document.getElementById('btn-toggle-remedy-worklog');
      headerEl = dom.orchRemedyHeader || document.getElementById('orch-remedy-header');
    }
    if (!sectionEl) return;

    if (isCollapsed) {
      sectionEl.classList.add('is-collapsed');
      if (btnEl) btnEl.setAttribute('aria-expanded', 'false');
      if (headerEl) headerEl.setAttribute('aria-expanded', 'false');
    } else {
      sectionEl.classList.remove('is-collapsed');
      if (btnEl) btnEl.setAttribute('aria-expanded', 'true');
      if (headerEl) headerEl.setAttribute('aria-expanded', 'true');
    }
  }

  function toggleOrchSection(sectionName) {
    let sectionEl;
    if (sectionName === 'warroom') sectionEl = dom.orchWarRoomSection || document.getElementById('orch-war-room-section');
    else if (sectionName === 'pap') sectionEl = dom.orchPapSection || document.getElementById('orch-pap-section');
    else if (sectionName === 'log') sectionEl = dom.orchLogSection || document.getElementById('orch-log-section');
    else if (sectionName === 'remedy') sectionEl = dom.orchRemedySection || document.getElementById('orch-remedy-section');
    if (!sectionEl) return;
    const isCurrentlyCollapsed = sectionEl.classList.contains('is-collapsed');
    setOrchSectionCollapsed(sectionName, !isCurrentlyCollapsed);
    if (isCurrentlyCollapsed && sectionName === 'remedy') {
      if (state.activeOrchIncId) {
        if (!dom.orchRemedyWorklogContent || dom.orchRemedyWorklogContent.dataset.loadedInc !== state.activeOrchIncId) {
          loadRemedyWorklog(state.activeOrchIncId);
        }
      }
    }
  }

  function initOrchestratorCollapsibleSections() {
    const sections = [
      { key: 'warroom', headerId: 'orch-war-room-header', btnId: 'btn-toggle-war-room' },
      { key: 'pap', headerId: 'orch-pap-header', btnId: 'btn-toggle-pap' },
      { key: 'log', headerId: 'orch-log-header', btnId: 'btn-toggle-log' },
      { key: 'remedy', headerId: 'orch-remedy-header', btnId: 'btn-toggle-remedy-worklog' }
    ];

    sections.forEach(({ key, headerId, btnId }) => {
      const header = document.getElementById(headerId);
      const btn = document.getElementById(btnId);

      if (btn) {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          toggleOrchSection(key);
        });
      }

      if (header) {
        header.addEventListener('click', (e) => {
          if (e.target.closest('#btn-copy-full-log, #btn-clear-log, #orch-btn-join-teams, #orch-btn-copy-teams, a, button:not(.orch-box-toggle-btn)')) return;
          toggleOrchSection(key);
        });

        header.addEventListener('keydown', (e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            if (e.target.closest('#btn-copy-full-log, #btn-clear-log, #orch-btn-join-teams, #orch-btn-copy-teams, a, button:not(.orch-box-toggle-btn)')) return;
            e.preventDefault();
            toggleOrchSection(key);
          }
        });
      }

      // Por defecto en Fase 1: dejarlas plegadas
      setOrchSectionCollapsed(key, true);
    });
  }

  // --- Módulo 2: Worklog Remedy & Inteligencia Operativa MonTMC ---
  function isSystemNoiseWorklog(text) {
    if (!text) return true;
    const t = text.trim();
    if (t === '' || t === '.' || t === '-' || t === '..' || t === '...') return true;
    if (/^(revisando|en curso)\.?$/i.test(t)) return true;
    if (/^(el estado ha sido cambiado a|la asignaci[oó]n ha sido cambiada a|la prioridad ha sido cambiada a|la urgencia ha sido cambiada a)\b/i.test(t)) return true;
    if (/^\[SCA360-OTRS.*\]\s*Adjunto\(s\)\s*\(\d+\):/i.test(t) && !t.includes('\n\n') && t.length < 100) return true;
    if (/\(Sin cambios de datos en el ticket OTRS desde el ultimo envio a EPSILON\.\)/i.test(t)) return true;
    return false;
  }

  function formatRemedyDate(dateStr) {
    if (!dateStr) return 'Fecha no informada';
    try {
      const d = new Date(dateStr);
      if (isNaN(d.getTime())) return dateStr;
      const pad = n => String(n).padStart(2, '0');
      return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
    } catch (_) {
      return dateStr;
    }
  }

  function getRelativeTimeSpan(dateStr) {
    if (!dateStr) return '';
    try {
      const d = new Date(dateStr);
      if (isNaN(d.getTime())) return '';
      const diffMs = Date.now() - d.getTime();
      if (diffMs < 0) return '';
      const diffMins = Math.floor(diffMs / 60000);
      if (diffMins < 1) return 'hace unos instantes';
      if (diffMins < 60) return `hace ${diffMins} min`;
      const diffHours = Math.floor(diffMins / 60);
      if (diffHours < 24) return `hace ${diffHours} h`;
      const diffDays = Math.floor(diffHours / 24);
      return `hace ${diffDays} día${diffDays > 1 ? 's' : ''}`;
    } catch (_) {
      return '';
    }
  }

  function renderRemedyWorklogView(cleanId) {
    if (!dom.orchRemedyWorklogContent) return;
    const item = state.remedyWorklogData && state.remedyWorklogData[cleanId];
    if (!item) return;

    const { solucion, isCached, isDisk, substantiveList, allList, filterMode } = item;
    const currentList = filterMode === 'all' ? allList : substantiveList;
    const lastSubstantive = (substantiveList && substantiveList.length > 0) ? substantiveList[0] : (allList[0] || null);

    let html = '';

    if (isCached) {
      html += `
        <div style="font-size: 11px; color: var(--triage-text-muted); margin-bottom: 8px; font-style: italic;">
          ⚡ Datos servidos desde caché ${isDisk ? 'en disco (contingencia)' : 'en memoria'}.
        </div>
      `;
    }

    // 1. Tarjeta destacada: Última Acción Técnica / Estado de Gestión
    if (lastSubstantive) {
      const relTime = getRelativeTimeSpan(lastSubstantive.fecha);
      html += `
        <div class="remedy-highlight-card">
          <div class="remedy-highlight-header">
            <div class="remedy-highlight-title-wrap">
              <span class="remedy-highlight-badge">⚡ Última Acción Técnica</span>
              ${relTime ? `<span class="remedy-highlight-relative">(${escapeHtml(relTime)})</span>` : ''}
            </div>
            <div class="remedy-highlight-meta">
              <span class="remedy-worklog-author">👤 ${escapeHtml(lastSubstantive.autor)}</span>
              ${lastSubstantive.grupo ? `<span class="remedy-worklog-group-pill">${escapeHtml(lastSubstantive.grupo)}</span>` : ''}
              <span class="remedy-worklog-date">🕒 ${formatRemedyDate(lastSubstantive.fecha)}</span>
            </div>
          </div>
          <div class="remedy-highlight-body">${escapeHtml(lastSubstantive.texto)}</div>
        </div>
      `;
    }

    // 2. Banner de Solución Oficial Remedy SOLO si el ticket está en estado terminal (Resuelto, Cerrado o Cancelado)
    const isTerminalStatus = (st) => {
      if (!st) return false;
      const s = String(st).toLowerCase().trim();
      return s.includes('resuelt') || s.includes('resolv') || s.includes('cerrad') || s.includes('clos') || s.includes('cancel');
    };
    if (solucion && isTerminalStatus(item.estado)) {
      html += `
        <div class="remedy-detail-banner">
          <strong>💡 Detalle de Solución / Cierre en Remedy:</strong>
          <div style="margin-top: 4px; white-space: pre-wrap;">${escapeHtml(solucion)}</div>
        </div>
      `;
    }

    // 3. Controles de Filtro (Pills)
    html += `
      <div class="remedy-worklog-controls">
        <div class="remedy-filter-pills" role="tablist" aria-label="Filtro de notas de Remedy">
          <button type="button" class="remedy-filter-pill ${filterMode === 'substantive' ? 'is-active' : ''}" onclick="window.__setRemedyWorklogFilter('${escapeHtml(cleanId)}', 'substantive')">
            📝 Notas Técnicas Clave (${substantiveList.length})
          </button>
          <button type="button" class="remedy-filter-pill ${filterMode === 'all' ? 'is-active' : ''}" onclick="window.__setRemedyWorklogFilter('${escapeHtml(cleanId)}', 'all')">
            📋 Auditoría Completa (${allList.length})
          </button>
        </div>
        <div class="remedy-worklog-order-hint">
          <span>⬇️ Más recientes primero</span>
        </div>
      </div>
    `;

    // 4. Lista de notas cronológica inversa
    if (currentList.length === 0) {
      html += `
        <p style="color: var(--triage-text-muted); font-size: 13px; font-style: italic; margin: 12px 0; padding: 12px; background: #F8FAFC; border-radius: 6px; border: 1px dashed #CBD5E1;">
          ${filterMode === 'substantive' 
            ? 'No se detectaron notas técnicas manuales en este ticket. Consulta la pestaña "Auditoría Completa" para revisar los cambios de estado y asignación.' 
            : 'No constan anotaciones en el worklog de esta incidencia en Remedy.'}
        </p>
      `;
    } else {
      html += `<div class="remedy-worklog-list">`;
      currentList.forEach(entry => {
        if (entry.isSystem) {
          html += `
            <div class="remedy-worklog-item remedy-worklog-system">
              <div class="remedy-worklog-meta">
                <div class="remedy-worklog-meta-left">
                  <span class="remedy-worklog-author-muted">⚙️ ${escapeHtml(entry.autor)}</span>
                  <span class="remedy-worklog-system-tag">Sistema / Auditoría</span>
                </div>
                <div class="remedy-worklog-meta-right">
                  <span class="remedy-worklog-date">🕒 ${formatRemedyDate(entry.fecha)}</span>
                </div>
              </div>
              <div class="remedy-worklog-text-muted">${escapeHtml(entry.texto)}</div>
            </div>
          `;
        } else {
          html += `
            <div class="remedy-worklog-item remedy-worklog-substantive">
              <div class="remedy-worklog-meta">
                <div class="remedy-worklog-meta-left">
                  <span class="remedy-worklog-author">👤 ${escapeHtml(entry.autor)}</span>
                  ${entry.grupo ? `<span class="remedy-worklog-group-pill">${escapeHtml(entry.grupo)}</span>` : ''}
                </div>
                <div class="remedy-worklog-meta-right">
                  ${entry.adjuntos > 0 ? `<span class="remedy-worklog-att-pill">📎 ${entry.adjuntos} adjunto${entry.adjuntos > 1 ? 's' : ''}</span>` : ''}
                  <span class="remedy-worklog-date">🕒 ${formatRemedyDate(entry.fecha)}</span>
                </div>
              </div>
              <div class="remedy-worklog-text">${escapeHtml(entry.texto)}</div>
            </div>
          `;
        }
      });
      html += `</div>`;
    }

    dom.orchRemedyWorklogContent.innerHTML = html;
  }

  function setRemedyWorklogFilter(cleanId, mode) {
    if (state.remedyWorklogData && state.remedyWorklogData[cleanId]) {
      state.remedyWorklogData[cleanId].filterMode = mode;
      renderRemedyWorklogView(cleanId);
    }
  }
  window.__setRemedyWorklogFilter = setRemedyWorklogFilter;

  async function loadRemedyWorklog(incId, forceRefresh = false) {
    if (!dom.orchRemedyWorklogContent) return;
    const cleanId = (incId || '').trim();
    if (!cleanId) return;

    if (!forceRefresh && state.remedyWorklogData && state.remedyWorklogData[cleanId]) {
      dom.orchRemedyWorklogContent.dataset.loadedInc = cleanId;
      renderRemedyWorklogView(cleanId);
      return;
    }

    dom.orchRemedyWorklogContent.innerHTML = `
      <div style="display: flex; align-items: center; gap: 8px; padding: 12px; color: var(--triage-text-muted); font-size: 13px;">
        <span aria-hidden="true" style="display: inline-block; animation: spin 1s infinite linear;">🔄</span>
        <span>Consultando notas técnicas de ${escapeHtml(cleanId)} en API MonTMC Remedy...</span>
      </div>
    `;

    try {
      const url = `/api/remedy/detail/${encodeURIComponent(cleanId)}${forceRefresh ? '?force=1' : ''}`;
      const res = await fetch(url);
      const data = await res.json();

      if (!res.ok || !data.success) {
        const errorMsg = data.error || `HTTP ${res.status}`;
        dom.orchRemedyWorklogContent.innerHTML = `
          <div style="background: #FEF2F2; border: 1px solid #FCA5A5; border-radius: 6px; padding: 12px; font-size: 13px; color: #991B1B;">
            <p style="margin: 0 0 6px 0; font-weight: 600;">⚠️ No se pudo recuperar el worklog de Remedy:</p>
            <p style="margin: 0 0 8px 0; font-family: var(--font-mono); font-size: 12px;">${escapeHtml(errorMsg)}</p>
            <button type="button" class="triage-btn triage-btn-sm" onclick="window.__loadRemedyWorklog('${escapeHtml(cleanId)}', true)">
              🔄 Reintentar consulta
            </button>
          </div>
        `;
        return;
      }

      dom.orchRemedyWorklogContent.dataset.loadedInc = cleanId;
      const rawWorklogs = data.worklogs || [];
      const normalized = rawWorklogs.map(entry => {
        const fecha = entry.fecha || entry.submit_date || entry.date || entry.timestamp || '';
        const autor = entry.autor || entry.submitter || entry.usuario || entry.user || 'Sistema';
        const texto = (entry.detalle || entry.texto || entry.notes || entry.description || entry.log || '').trim();
        const grupo = entry.grupoAsignado || entry.grupoResolutor || entry.grupo || '';
        const adjuntos = entry.numeroAdjuntos || (Array.isArray(entry.adjuntos) ? entry.adjuntos.length : 0) || 0;
        const isSystem = isSystemNoiseWorklog(texto);
        return { fecha, autor, texto, grupo, adjuntos, isSystem };
      });

      // Orden cronológico inverso (más recientes arriba)
      normalized.sort((a, b) => {
        const tA = a.fecha ? new Date(a.fecha).getTime() : 0;
        const tB = b.fecha ? new Date(b.fecha).getTime() : 0;
        return tB - tA;
      });

      const substantiveList = normalized.filter(e => !e.isSystem);
      const allList = normalized;

      const inc = state.incidents && state.incidents.find(i => (i.id || i['ID de incidencia']) === cleanId);
      const ticketEstado = (data.estado || (data.remedy && data.remedy.estadoDesc) || (inc && (inc.estatus || inc.estado || inc.Estatus)) || '').trim();

      if (!state.remedyWorklogData) state.remedyWorklogData = {};
      state.remedyWorklogData[cleanId] = {
        cleanId,
        solucion: (data.solucion || '').trim(),
        detalle: (data.detalle || '').trim(),
        estado: ticketEstado,
        isCached: Boolean(data._cached),
        isDisk: data._source === 'disk_fallback',
        substantiveList,
        allList,
        filterMode: (state.remedyWorklogData[cleanId] && state.remedyWorklogData[cleanId].filterMode) || 'substantive'
      };

      renderRemedyWorklogView(cleanId);
    } catch (err) {
      dom.orchRemedyWorklogContent.innerHTML = `
        <div style="background: #FEF2F2; border: 1px solid #FCA5A5; border-radius: 6px; padding: 12px; font-size: 13px; color: #991B1B;">
          <p style="margin: 0 0 6px 0; font-weight: 600;">⚠️ Error de red consultando Remedy:</p>
          <p style="margin: 0; font-size: 12px;">${escapeHtml(err.message)}</p>
        </div>
      `;
    }
  }
  window.__loadRemedyWorklog = loadRemedyWorklog;

  function formatFullLogForClipboard(incId) {
    const inc = state.incidents.find(i => i.id === incId);
    const entries = state.orchestratorLogs[incId] || [];
    const incTitle = inc ? inc.titulo : 'Incidencia';
    const nowStr = new Date().toLocaleString('es-ES');

    let text = `📜 BITÁCORA OPERATIVA DE EMERGENCIA IT · ORANGE TECH OPERATIONS\n`;
    text += `━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n`;
    text += `Incidencia: ${incId}\n`;
    text += `Título: ${incTitle}\n`;
    text += `Incident Manager: ${state.defaultIncidentManager}\n`;
    text += `Fecha de Extracción: ${nowStr}\n`;
    text += `Total Hitos Registrados: ${entries.length}\n`;
    text += `━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n`;

    entries.forEach((e, idx) => {
      text += `[${idx + 1}] ${e.time} | ${e.roleLabel || e.role}\n`;
      text += `    ${e.text}\n\n`;
    });

    text += `━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n`;
    text += `Generado desde Consola de Triaje y Orquestador de Emergencias (Módulo 2)`;
    return text;
  }

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
  // Traspaso de Guardia en 1 Clic (US-04 Usabilidad) y Alertas Dinámicas (US-05)
  // --------------------------------------------------------------------------

  function getShiftLabel(now = new Date()) {
    const hour = now.getHours();
    if (hour >= 7 && hour < 15) {
      return 'Turno Mañana (07:00 - 15:00) ➔ Relevo con Turno Tarde';
    } else if (hour >= 15 && hour < 23) {
      return 'Turno Tarde (15:00 - 23:00) ➔ Relevo con Turno Noche';
    } else {
      return 'Turno Noche (23:00 - 07:00) ➔ Relevo con Turno Mañana';
    }
  }

  function buildShiftHandoverReport() {
    const now = new Date();
    const nowFormatted = now.toLocaleString('es-ES', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit', second: '2-digit'
    });
    const shiftLabel = getShiftLabel(now);

    const activeIncidents = (state.incidents || []).filter(i => !isTerminalStatus(i.estatus || i.estado || i.status));
    const activeSL1 = activeIncidents.filter(i => i.prioridad_sugerida === 'P1');
    const activeSL2 = activeIncidents.filter(i => i.prioridad_sugerida === 'P2');
    const discrepancies = activeIncidents.filter(i => i.es_discrepancia);
    const workarounds = activeIncidents.filter(i => i.workaround || i.workaround_info);
    const papsCount = (state.paps && Array.isArray(state.paps)) ? state.paps.length : 0;

    let md = `# 📋 INFORME OFICIAL DE TRASPASO DE GUARDIA (SHIFT HANDOVER)\n`;
    md += `**Fecha y Hora:** ${nowFormatted}\n`;
    md += `**Turno Operativo:** ${shiftLabel}\n`;
    md += `**Incident Manager de Guardia (Saliente):** ${state.defaultIncidentManager}\n`;
    md += `**Fuente de Inspección:** ${state.metadata.source_file || 'high_priority_notifications.json'} (${state.metadata.generated_at || nowFormatted})\n\n`;
    md += `---\n\n`;

    // 1. Resumen Ejecutivo
    md += `### 1. RESUMEN EJECUTIVO DE SITUACIÓN\n`;
    md += `- **Incidencias Activas en Seguimiento:** ${activeIncidents.length}\n`;
    md += `- **Críticas SL1 / P1 Activas:** ${activeSL1.length}\n`;
    md += `- **Mayores SL2 / P2 Activas:** ${activeSL2.length}\n`;
    md += `- **Discrepancias de Triaje (Subescaladas en Remedy):** ${discrepancies.length}\n`;
    md += `- **Workarounds / Desvíos de Tráfico Autorizados:** ${workarounds.length}\n`;
    md += `- **Trabajos Programados (PaP / CRQ) Concurrentes:** ${papsCount}\n\n`;
    md += `---\n\n`;

    // 2. Detalle SL1 Activas
    md += `### 2. INCIDENCIAS CRÍTICAS SL1 / P1 EN CURSO\n`;
    if (activeSL1.length === 0) {
      md += `> ✅ **Sin incidencias SL1 activas.** Todos los servicios core y procesos críticos operan dentro de los parámetros nominales o sin emergencias abiertas al momento del relevo.\n\n`;
    } else {
      activeSL1.forEach(inc => {
        const evaluacion = inc.evaluacion || {};
        const sistemas = Array.isArray(inc.sistemas) ? inc.sistemas.join(', ') : (inc.sistemas || 'Sistemas Core');
        const brand = detectIncidentBrand(inc).toUpperCase();

        // Remedy Aging
        const baseMin = evaluacion.minutos_desde_apertura || 0;
        const remedyMin = Math.max(0, Math.floor(baseMin + (Date.now() - (state.lastInspectionEpoch || Date.now())) / 60000));

        // Crisis War Room T0
        let actEpoch = state.orchestratorActivations[inc.id];
        if (!actEpoch) {
          try {
            const st = localStorage.getItem('emergency_activation_' + inc.id);
            if (st) actEpoch = parseInt(st, 10);
          } catch (_) {}
        }
        const crisisMin = actEpoch ? Math.max(0, Math.floor((Date.now() - actEpoch) / 60000)) : remedyMin;

        // Escalation states
        let escState = state.orchestratorEscalations[inc.id];
        if (!escState) {
          try {
            const st = localStorage.getItem('emergency_esc_' + inc.id);
            if (st) escState = JSON.parse(st);
          } catch (_) {}
        }
        escState = escState || {};

        const status45 = escState.esc45Done
          ? '✅ Confirmado (Escalado N2/N3 ejecutado)'
          : (crisisMin >= 45 ? `🚨 ALARMA VENCIDA (+${crisisMin - 45} min)` : `⏱️ En tiempo (${45 - crisisMin} min restantes)`);

        const status105 = escState.esc105Done
          ? '✅ Confirmado (2º Escalado Jerárquico ejecutado)'
          : (crisisMin >= 105 ? `🚨 ALARMA JERÁRQUICA VENCIDA (+${crisisMin - 105} min)` : `⏱️ En tiempo (${105 - crisisMin} min restantes)`);

        // Last log entry
        let entries = state.orchestratorLogs[inc.id];
        if (!entries || entries.length === 0) {
          try {
            const st = localStorage.getItem('emergency_log_' + inc.id);
            if (st) entries = JSON.parse(st);
          } catch (_) {}
        }
        let lastMilestone = 'Sin hitos adicionales registrados en la bitácora.';
        if (entries && entries.length > 0) {
          const last = entries[entries.length - 1];
          lastMilestone = `[${last.time || '--:--'}] ${last.roleLabel || last.role || 'Hito'}: ${last.text}`;
        }

        const workaroundText = (inc.workaround || inc.workaround_info)
          ? `⚠️ ACTIVO: ${inc.workaround_info || inc.descripcion_workaround || 'Desvío de tráfico temporal en curso'}`
          : '❌ Sin workaround activo (Diagnóstico técnico directo hacia causa raíz)';

        md += `#### 🚨 [${inc.id}] ${sistemas} - ${inc.titulo || 'Incidencia Crítica'}\n`;
        md += `- **Estado Remedy:** ${inc.estatus || 'Asignado'} | **Dominio Marca:** ${brand}\n`;
        md += `- **Proceso Crítico:** ${evaluacion.proceso || 'Transversal'} | **Impacto:** ${evaluacion.impacto_estimado || 'Crítico'}\n`;
        md += `- **Dual Clock:**\n`;
        md += `  - Envejecimiento Global Remedy: **${formatAgingMinutes(remedyMin)}**\n`;
        md += `  - Reloj Táctico Crisis SL1: **${crisisMin} min**\n`;
        md += `  - Reloj 45m (Escalado Telefónico N2/N3): **${status45}**\n`;
        md += `  - Reloj 105m (2º Escalado Jerárquico): **${status105}**\n`;
        md += `- **War Room Teams:** ${generateTeamsWarRoomUrl(inc.id)}\n`;
        md += `- **Último Hito en Bitácora:** ${lastMilestone}\n`;
        md += `- **Workaround / Desvío:** ${workaroundText}\n\n`;
      });
    }
    md += `---\n\n`;

    // 3. Discrepancias Detectadas
    md += `### 3. DISCREPANCIAS DE TRIAJE DETECTADAS (PENDIENTES DE CORRECCIÓN REMEDY)\n`;
    if (discrepancies.length === 0) {
      md += `> ✅ **Sin discrepancias activas.** Todas las incidencias en curso cuentan con la severidad nominal de Remedy alineada con su criticidad técnica real.\n\n`;
    } else {
      discrepancies.forEach(d => {
        const ev = d.evaluacion || {};
        const sistemas = Array.isArray(d.sistemas) ? d.sistemas.join(', ') : (d.sistemas || 'Sistemas Core');
        md += `- **[${d.id}]** Registrada en Remedy como **${d.prioridad_original || d.prioridad || 'P3/P4'}** ➔ Prioridad Real Requerida: **${d.prioridad_sugerida}**\n`;
        md += `  - **Sistema:** ${sistemas} | **Título:** ${d.titulo}\n`;
        md += `  - **Motivo de Subescalación:** ${ev.criterio_aplicado || d.regla_discrepancia || 'Umbral de Proceso Crítico o Regla de Oro N1 superados'}\n`;
      });
      md += `\n`;
    }
    md += `---\n\n`;

    // 4. Workarounds Activos
    md += `### 4. WORKAROUNDS Y MITIGACIONES OPERATIVAS EN VIGOR\n`;
    if (workarounds.length === 0) {
      md += `> ℹ️ **No hay workarounds provisionales activos.** No se registran desvíos de tráfico, bypass de pasarelas ni procedimientos de contingencia activos.\n\n`;
    } else {
      workarounds.forEach(w => {
        md += `- **[${w.id}]**: ${w.workaround_info || w.descripcion_workaround || 'Contramedida provisional autorizada por IM-CSO.'}\n`;
      });
      md += `\n`;
    }
    md += `---\n\n`;

    // 5. Monitor PaP
    md += `### 5. TRABAJOS PROGRAMADOS (PaP / CRQ) EN VENTANA DE RIESGO\n`;
    if (!state.paps || state.paps.length === 0) {
      md += `> ℹ️ **Sin trabajos programados PaP concurrentes** registrados con posible correlación en la ventana actual.\n\n`;
    } else {
      state.paps.forEach(p => {
        md += `- **[${p.crq}]** ${p.titulo}\n`;
        md += `  - **Estado:** ${p.estado || 'En curso'} | **Ventana:** ${p.ventana || 'Activa'} | **Rollback Estimado:** ${p.tiempo_rollback_estimado || '15 min'}\n`;
      });
      md += `\n`;
    }
    md += `---\n`;
    md += `*Informe generado automáticamente por la Consola de Triaje y Reclasificación IT · Orange Tech Operations*\n`;

    const summaryText = `📊 ${activeSL1.length} SL1 activas · ${discrepancies.length} discrepancias · ${workarounds.length} workarounds · ${shiftLabel.split(' ➔ ')[0]}`;

    return { reportMarkdown: md, summaryText };
  }

  function openShiftHandoverModal() {
    if (!dom.modalShiftHandover) return;
    const { reportMarkdown, summaryText } = buildShiftHandoverReport();

    if (dom.handoverReportText) {
      dom.handoverReportText.value = reportMarkdown;
    }
    if (dom.handoverMetaSummary) {
      dom.handoverMetaSummary.textContent = summaryText;
    }

    copyToClipboard(reportMarkdown, '📋 Informe de Traspaso de Guardia generado y copiado al portapapeles');
    dom.modalShiftHandover.classList.add('open');
  }

  function closeShiftHandoverModal() {
    if (dom.modalShiftHandover) {
      dom.modalShiftHandover.classList.remove('open');
    }
  }

  // --- Alertas Dinámicas en Título de Pestaña y Favicon SVG (US-05) ---

  let currentFaviconStatus = null;

  function updateDynamicFavicon(status) {
    if (currentFaviconStatus === status) return;
    currentFaviconStatus = status;

    let svg = '';
    if (status === 'alarm') {
      svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
        <circle cx="16" cy="16" r="15" fill="#DC2626"/>
        <rect x="14.5" y="7" width="3" height="11" rx="1.5" fill="#FFFFFF"/>
        <circle cx="16" cy="23" r="2" fill="#FFFFFF"/>
      </svg>`;
    } else if (status === 'warning') {
      svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
        <circle cx="16" cy="16" r="15" fill="#EA580C"/>
        <rect x="14.5" y="7" width="3" height="11" rx="1.5" fill="#FFFFFF"/>
        <circle cx="16" cy="23" r="2" fill="#FFFFFF"/>
      </svg>`;
    } else if (status === 'discrepancy') {
      svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
        <rect width="32" height="32" rx="6" fill="#F59E0B"/>
        <path d="M17 5L9 18h6l-2 9 10-13h-6l2-9z" fill="#FFFFFF"/>
      </svg>`;
    } else {
      svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
        <rect width="32" height="32" rx="6" fill="#FF7900"/>
        <rect x="7" y="7" width="18" height="18" rx="2" fill="#FFFFFF"/>
        <rect x="11" y="11" width="10" height="10" rx="1" fill="#FF7900"/>
      </svg>`;
    }

    let link = document.querySelector("link[rel~='icon']");
    if (!link) {
      link = document.createElement('link');
      link.rel = 'icon';
      document.head.appendChild(link);
    }
    link.type = 'image/svg+xml';
    link.href = 'data:image/svg+xml;utf8,' + encodeURIComponent(svg.trim());
  }

  function updateBrowserTitleAndFavicon() {
    const activeIncidents = (state.incidents || []).filter(i => !isTerminalStatus(i.estatus || i.estado || i.status));
    const activeSL1 = activeIncidents.filter(i => i.prioridad_sugerida === 'P1');
    const discrepancies = activeIncidents.filter(i => i.es_discrepancia);

    if (activeSL1.length > 0) {
      let maxCrisisMin = 0;
      activeSL1.forEach(inc => {
        let actEpoch = state.orchestratorActivations[inc.id];
        if (!actEpoch) {
          try {
            const st = localStorage.getItem('emergency_activation_' + inc.id);
            if (st) actEpoch = parseInt(st, 10);
          } catch (_) {}
        }
        let elapsedMin = 0;
        if (actEpoch) {
          elapsedMin = Math.floor((Date.now() - actEpoch) / 60000);
        } else {
          const baseMin = (inc.evaluacion && inc.evaluacion.minutos_desde_apertura) || 0;
          elapsedMin = Math.floor(baseMin + (Date.now() - (state.lastInspectionEpoch || Date.now())) / 60000);
        }
        if (elapsedMin > maxCrisisMin) maxCrisisMin = elapsedMin;
      });

      if (maxCrisisMin >= 105) {
        document.title = `🔥 (ALARMA DIR >105m) Consola de Triaje IT · Orange`;
        updateDynamicFavicon('alarm');
      } else if (maxCrisisMin >= 45) {
        const rem105 = 105 - maxCrisisMin;
        document.title = `⚠️ (45m Vencido · ${rem105}m p/Dir) Consola de Triaje IT · Orange`;
        updateDynamicFavicon('alarm');
      } else if (maxCrisisMin >= 35) {
        const rem45 = 45 - maxCrisisMin;
        document.title = `⏱️ (${maxCrisisMin}m/45m ¡Escalado Inminente!) Consola de Triaje IT · Orange`;
        updateDynamicFavicon('warning');
      } else {
        const rem45 = 45 - maxCrisisMin;
        document.title = `🚨 (${rem45}m p/45m · SL1 Activa) Consola de Triaje IT · Orange`;
        updateDynamicFavicon('warning');
      }
    } else if (discrepancies.length > 0) {
      document.title = `⚡ (${discrepancies.length} Discrepancias) Consola de Triaje IT · Orange`;
      updateDynamicFavicon('discrepancy');
    } else {
      document.title = `Consola de Triaje IT · Orange Tech Operations`;
      updateDynamicFavicon('normal');
    }
  }

  // --------------------------------------------------------------------------
  // Función 2: Filtrado y Renderizado en Modo Tabular con Filas Plegables
  // --------------------------------------------------------------------------

  function parseIncidentEpoch(inc) {
    if (!inc) return 0;
    const raw = inc.fecha_apertura || inc.evaluacion?.fecha_apertura || inc.fecha || inc.fecha_creacion;
    if (raw) {
      if (raw instanceof Date) return raw.getTime();
      const s = String(raw).trim();
      const clean = s.replace(/\s+[apAP]\.?$/, '');
      const match = clean.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})(?:\s+(\d{1,2}):(\d{2})(?::(\d{2}))?)?/);
      if (match) {
        const day = parseInt(match[1], 10);
        const month = parseInt(match[2], 10) - 1;
        const year = parseInt(match[3], 10);
        const hour = match[4] ? parseInt(match[4], 10) : 0;
        const minute = match[5] ? parseInt(match[5], 10) : 0;
        const sec = match[6] ? parseInt(match[6], 10) : 0;
        const d = new Date(year, month, day, hour, minute, sec);
        if (!isNaN(d.getTime())) return d.getTime();
      }
      const isoEpoch = Date.parse(s);
      if (!isNaN(isoEpoch)) return isoEpoch;
    }
    const mins = inc.evaluacion?.minutos_desde_apertura;
    if (mins != null && !isNaN(mins)) {
      return Date.now() - (Number(mins) * 60000);
    }
    return 0;
  }

  function formatFechaApertura(raw, mins) {
    if (raw) {
      if (raw instanceof Date) {
        const d = String(raw.getDate()).padStart(2, '0');
        const m = String(raw.getMonth() + 1).padStart(2, '0');
        const y = raw.getFullYear();
        const h = String(raw.getHours()).padStart(2, '0');
        const min = String(raw.getMinutes()).padStart(2, '0');
        return `${d}/${m}/${y} ${h}:${min}`;
      }
      const s = String(raw).trim();
      return s.replace(/\s+[apAP]\.?$/, '');
    }
    if (mins != null && !isNaN(mins)) {
      const approxDate = new Date(Date.now() - (Number(mins) * 60000));
      const d = String(approxDate.getDate()).padStart(2, '0');
      const m = String(approxDate.getMonth() + 1).padStart(2, '0');
      const y = approxDate.getFullYear();
      const h = String(approxDate.getHours()).padStart(2, '0');
      const min = String(approxDate.getMinutes()).padStart(2, '0');
      return `${d}/${m}/${y} ${h}:${min}`;
    }
    return 'Fecha n/d';
  }

  function getFilteredIncidents() {
    let filtered = state.incidents.slice();

    // 1. Filtro de Pestaña Principal (Reclasificaciones vs Orquestador vs Todas vs Correctas)
    if (state.activeFilter === 'reclass_only') {
      filtered = filtered.filter(i => i.es_discrepancia || (i.discrepancia_delta && i.discrepancia_delta > 0));
    } else if (state.activeFilter === 'orchestrator_only') {
      filtered = filtered.filter(i => i.prioridad_sugerida === 'P1');
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
        const guia = i.guia_operador || i.evaluacion?.guia_operador || {};
        const catMatch = (guia.categoria_operativa || '').toLowerCase().includes(q);
        const alertMatch = (guia.alerta_consola || '').toLowerCase().includes(q);
        const actionMatch = (guia.accion_recomendada || '').toLowerCase().includes(q);
        const chanMatch = (guia.canal_escalado || '').toLowerCase().includes(q);
        return idMatch || titleMatch || sysMatch || procMatch || critMatch || impactMatch || catMatch || alertMatch || actionMatch || chanMatch;
      });
    }

    // 5. Ordenación por Fecha de Apertura (más recientes primero)
    filtered.sort((a, b) => {
      const epochA = parseIncidentEpoch(a);
      const epochB = parseIncidentEpoch(b);
      return epochB - epochA;
    });

    return filtered;
  }

  
  // --------------------------------------------------------------------------
  // Helpers para Guía del Operador de Consola (incident-triage-review)
  // --------------------------------------------------------------------------

  function formatCanalEscalado(canal) {
    if (!canal) return 'Ordinario';
    switch (canal) {
      case 'TELEFONICO_OBLIGATORIO_CSO': return 'Telefónico IM-CSO';
      case 'COMUNICACION_EQUIPO_DESPLIEGUES': return 'Equipo Despliegues / Pases';
      case 'ESCALADO_N1_SUPERVISOR_LOCAL': return 'Supervisor N1 / Soporte Local';
      case 'CIERRE_ADMINISTRATIVO_REMEDY': return 'Cierre Administrativo Remedy';
      case 'SEGUIMIENTO_ORDINARIO_RESOLUTOR': return 'Resolutor Ordinario';
      default: return String(canal).replace(/_/g, ' ');
    }
  }

  function buildZombieClosureText(inc) {
    const incId = inc.id || 'INC000000000000';
    const evalData = inc.evaluacion || {};
    const jiraId = evalData.ticket_jira || 'Jira asociado';
    return `SOLICITUD DE CIERRE ADMINISTRATIVO EN REMEDY\n` +
      `-----------------------------------------------\n` +
      `Incidencia: ${incId}\n` +
      `Referencia de entrega/Jira: ${jiraId}\n\n` +
      `La resolución técnica del servicio ha finalizado satisfactoriamente según el registro del equipo de desarrollo/despliegues y el ticket asociado está concluido. Al no existir afectación operativa en producción, se solicita a la Mesa de Seguimiento proceder con el cierre administrativo formal del ticket en Remedy para evitar distorsiones en los KPIs de aging y triaje operativo.\n\n` +
      `Dictamen emitido por la Consola de Triaje y Gestión de Emergencias IT de Orange.`;
  }

function renderFeed() {
    if (!dom.triageFeed) return;

    const filtered = getFilteredIncidents();

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

    const rowsHtml = filtered.map(inc => renderTableRow(inc)).join('');

    dom.triageFeed.innerHTML = `
      <div class="triage-table-toolbar">
        <div class="triage-table-count">
          Mostrando <strong>${filtered.length}</strong> incidencia${filtered.length === 1 ? '' : 's'}
        </div>
        <button type="button" class="triage-btn-toggle-all" id="btn-toggle-all-rows" aria-label="${state.allExpanded ? 'Plegar todas las filas' : 'Expandir todas las filas'}">
          <span aria-hidden="true">${state.allExpanded ? '▲' : '▼'}</span>
          <span>${state.allExpanded ? 'Plegar Todas' : 'Expandir Todas'}</span>
        </button>
      </div>

      <div class="triage-table-wrapper">
        <table class="triage-table" aria-label="Tabla de Triaje de Incidencias">
          <thead>
            <tr>
              <th style="min-width: 200px;">Incidencia / Apertura</th>
              <th style="min-width: 270px;">Título / Resumen IA / Mensajes</th>
              <th style="min-width: 190px;">Proceso Crítico y Sistemas</th>
              <th style="width: 110px; text-align: center;">Remedy INI</th>
              <th style="width: 130px; text-align: center;">Severidad ITIL</th>
              <th style="width: 180px; text-align: right;">Acciones</th>
            </tr>
          </thead>
          <tbody>
            ${rowsHtml}
          </tbody>
        </table>
      </div>
    `;

    // Adjuntar escuchadores de eventos para interacción con la tabla
    attachFeedEventListeners();
  }

  function renderTableRow(inc) {
    const incId = inc.id || 'INC000000000000';
    const isDisc = Boolean(inc.es_discrepancia || (inc.discrepancia_delta && inc.discrepancia_delta > 0));
    const delta = inc.discrepancia_delta || 0;
    const isP1 = inc.prioridad_sugerida === 'P1';
    const isOpen = Boolean(state.expandedRows[incId]);

    // Modificador de clase para la fila principal
    let rowModifier = 'is-correct';
    if (isDisc) {
      rowModifier = delta >= 2 ? 'is-discrepancy-delta2' : 'is-discrepancy-delta1';
    }

    const evaluacion = inc.evaluacion || {};
    const minsElapsed = evaluacion.minutos_desde_apertura || 0;
    const proceso = evaluacion.proceso || evaluacion.proceso_negocio || 'Procesos Críticos';
    const criterio = evaluacion.criterio || 'Regla de Oro N1';
    const impactText = evaluacion.impacto_justificacion || inc.discrepancia_motivo || 'Impacto activo evaluado por el motor de triaje.';
    const urgencyText = evaluacion.urgencia_justificacion || 'Restablecimiento operativo requerido con máxima celeridad.';

    const rawFecha = inc.fecha_apertura || evaluacion.fecha_apertura || inc.fecha || inc.fecha_creacion;
    const fechaStr = formatFechaApertura(rawFecha, minsElapsed);

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

    // Severidad Remedy inicial
    const sevNominal = inc.prioridad_original || 'Media';
    let remedyBadgeClass = 'badge-remedy-media';
    if (sevNominal.toLowerCase().includes('alta')) remedyBadgeClass = 'badge-remedy-alta';
    if (sevNominal.toLowerCase().includes('crítica') || sevNominal.toLowerCase().includes('critica')) remedyBadgeClass = 'badge-remedy-critica';

    // Severidad ITIL sugerida
    let itilBadgeClass = 'badge-itil-sl2';
    let itilLabel = 'SL2 / P2';
    let itilFullLabel = 'SL2 / P2 (Mayor)';
    if (inc.prioridad_sugerida === 'P1') {
      itilBadgeClass = 'badge-itil-sl1';
      itilLabel = 'SL1 / P1';
      itilFullLabel = 'SL1 / P1 (Emergencia Crítica)';
    } else if (inc.prioridad_sugerida === 'P2') {
      itilBadgeClass = 'badge-itil-sl2';
      itilLabel = 'SL2 / P2';
      itilFullLabel = 'SL2 / P2 (Mayor)';
    } else if (inc.prioridad_sugerida === 'P3') {
      itilBadgeClass = 'badge-itil-sl3';
      itilLabel = 'SL3 / P3';
      itilFullLabel = 'SL3 / P3 (Media)';
    } else if (inc.prioridad_sugerida === 'P4') {
      itilBadgeClass = 'badge-itil-sl4';
      itilLabel = 'SL4 / P4';
      itilFullLabel = 'SL4 / P4 (Baja)';
    }

    // Epsilon IA resumen
    const resumenIa = inc.resumen_ia || {};
    const epsilonBloqueos = Array.isArray(resumenIa.bloqueos) ? resumenIa.bloqueos.join('; ') : (resumenIa.bloqueos || '');
    const hasResumenIa = Boolean(
      resumenIa && (
        resumenIa.problema ||
        resumenIa.impacto ||
        resumenIa.solucion ||
        resumenIa.causa_raiz
      )
    );

    // Guía del Operador de Consola (incident-triage-review)
    const guia = inc.guia_operador || (evaluacion && evaluacion.guia_operador) || {};
    const catOperativa = guia.categoria_operativa || (isDisc ? 'DISCREPANCIA_TRIAJE' : 'SEGUIMIENTO_ESTANDAR');
    const alertaConsola = guia.alerta_consola || '';
    const accionRecomendada = guia.accion_recomendada || '';
    const canalEscalado = guia.canal_escalado || 'SEGUIMIENTO_ORDINARIO_RESOLUTOR';
    const prioridadOp = guia.prioridad_operativa_consola || (isP1 ? 'P1_CRITICA' : 'P2_SEGUIMIENTO');
    const reqLlamadaCso = Boolean(guia.requiere_llamada_cso);
    const reqComunicadoDir = Boolean(guia.requiere_comunicado_direccion);

    // Pastilla y estilo operativo por categoría
    let opBadgeClass = 'is-seguimiento-estandar';
    let opBadgeIcon = '📋';
    let opBadgeLabel = 'Seguimiento ITIL';
    if (catOperativa === 'EMERGENCIA_VIVA') {
      opBadgeClass = 'is-emergencia-viva';
      opBadgeIcon = '🚨';
      opBadgeLabel = 'Emergencia Viva P1';
    } else if (catOperativa === 'RESOLUCION_PLANIFICADA') {
      opBadgeClass = 'is-resolucion-planificada';
      opBadgeIcon = '🗓️';
      opBadgeLabel = 'Resolución Planificada';
    } else if (catOperativa === 'ESTANCAMIENTO_LOCAL') {
      opBadgeClass = 'is-estancamiento-local';
      opBadgeIcon = '⚠️';
      opBadgeLabel = 'Estancamiento Local';
    } else if (catOperativa === 'TICKET_ZOMBI_REMEDY') {
      opBadgeClass = 'is-ticket-zombi';
      opBadgeIcon = '🧟';
      opBadgeLabel = 'Zombi Remedy (Jira OK)';
    } else if (catOperativa === 'INFRATRIAJE_REMEDY') {
      opBadgeClass = 'is-infratriaje-remedy';
      opBadgeIcon = '⚡';
      opBadgeLabel = 'Infratriaje Remedy';
    } else if (catOperativa === 'AFECTACION_MULTISEDE_PARCIAL') {
      opBadgeClass = 'is-multisede-parcial';
      opBadgeIcon = '🏢';
      opBadgeLabel = 'Afectación Multisede';
    } else if (catOperativa === 'WORKAROUND_AUTORIZADO') {
      opBadgeClass = 'is-workaround-autorizado';
      opBadgeIcon = '🔒';
      opBadgeLabel = 'Workaround Autorizado';
    } else if (catOperativa === 'REAPERTURA_ACTIVA') {
      opBadgeClass = 'is-reapertura-activa';
      opBadgeIcon = '🔄';
      opBadgeLabel = 'Reapertura Activa';
    }

    // Mensajes Ejecutivos completados (incident-reporter)
    const msgsEjecutivos = inc.mensajes_ejecutivos || {};
    const hasMensajesEjecutivos = Boolean(
      (msgsEjecutivos.apertura && (msgsEjecutivos.apertura.completo || msgsEjecutivos.apertura.generado_por_agente) && msgsEjecutivos.apertura.estado !== 'pendiente') ||
      (msgsEjecutivos.seguimiento && (msgsEjecutivos.seguimiento.completo || msgsEjecutivos.seguimiento.generado_por_agente) && msgsEjecutivos.seguimiento.estado !== 'pendiente') ||
      (msgsEjecutivos.cierre && (msgsEjecutivos.cierre.completo || msgsEjecutivos.cierre.generado_por_agente) && msgsEjecutivos.cierre.estado !== 'pendiente')
    );

    return `
      <!-- Fila Resumen Principal (Modo Tabular - 6 Columnas) -->
      <tr class="triage-row-main ${rowModifier} ${isOpen ? 'is-expanded' : ''}" data-inc="${escapeHtml(incId)}" role="button" tabindex="0" aria-expanded="${isOpen}">
        <!-- 1 Columna: Incidencia, Fecha Apertura y tiempo activa -->
        <td class="triage-cell-incident triage-cell-id">
          <div class="triage-incident-header">
            <button type="button" class="triage-chevron-btn ${isOpen ? 'is-expanded' : ''}" data-inc="${escapeHtml(incId)}" aria-label="${isOpen ? 'Plegar detalle' : 'Desplegar detalle'}">
              <span aria-hidden="true">▶</span>
            </button>
            <span class="triage-id-link" data-inc="${escapeHtml(incId)}" title="Ver ficha técnica Epsilon IA">${escapeHtml(incId)}</span>
            <span class="triage-status-pill ${statusPillClass}">${escapeHtml(inc.estatus || 'Pendiente')}</span>
            ${catOperativa === 'TICKET_ZOMBI_REMEDY' ? '<span class="triage-status-pill status-zombi" title="Resolución Jira completada - Cierre administrativo pendiente en Remedy">🧟 Zombi</span>' : ''}
            ${catOperativa === 'RESOLUCION_PLANIFICADA' ? '<span class="triage-status-pill status-planificada" title="Resolución programada (Batch/Release) - Aging no penalizado">🗓️ Planif</span>' : ''}
            ${catOperativa === 'INFRATRIAJE_REMEDY' ? '<span class="triage-status-pill status-infratriaje" title="Infratriaje Remedy detectado - Requiere reclasificación">⚡ Infratriaje</span>' : ''}
            ${catOperativa === 'AFECTACION_MULTISEDE_PARCIAL' ? '<span class="triage-status-pill status-multisede" title="Afectación multisede parcial - Falso cierre prevenido">🏢 Multisede</span>' : ''}
            ${catOperativa === 'WORKAROUND_AUTORIZADO' ? '<span class="triage-status-pill status-workaround" title="Workaround temporal activo bajo candado IM-CSO">🔒 Workaround</span>' : ''}
            ${catOperativa === 'REAPERTURA_ACTIVA' ? '<span class="triage-status-pill status-reapertura" title="Reapertura activa - Reactivación urgente requerida">🔄 Reabierta</span>' : ''}
          </div>
          <div class="triage-datetime-row">
            <span class="triage-date-label" title="Fecha oficial de apertura en Remedy">📅 ${escapeHtml(fechaStr)}</span>
            <span class="triage-aging-badge ${minsElapsed > 120 ? 'is-aging-warning' : ''}" title="Tiempo transcurrido desde apertura">⏱️ ${formatAgingMinutes(minsElapsed)}</span>
          </div>
        </td>

        <!-- 2 Columna: Titulo e iconos de Resumen IA y Mensajes -->
        <td class="triage-cell-title-comms triage-cell-title">
          <div class="triage-title-text">${escapeHtml(inc.titulo || 'Sin título')}</div>
          <div class="triage-title-indicators">
            <div class="triage-micro-marks" role="group" aria-label="Indicadores de Resumen IA y Mensajes Ejecutivos">
              ${hasResumenIa ? `
                <button type="button" class="triage-micro-mark is-ia btn-view-epsilon" data-inc="${escapeHtml(incId)}" title="Resumen IA completado (Epsilon Telemetría) — Clic para abrir ficha técnica" aria-label="Resumen IA disponible">
                  <span class="mark-icon" aria-hidden="true">✨</span><span>Resumen IA</span>
                </button>
              ` : `
                <span class="triage-micro-mark is-pending" title="Resumen IA pendiente de análisis">
                  <span class="mark-icon" aria-hidden="true">⏳</span><span>Sin IA</span>
                </span>
              `}
              ${hasMensajesEjecutivos ? `
                <button type="button" class="triage-micro-mark is-comms btn-open-exec-comm" data-inc="${escapeHtml(incId)}" title="Mensaje Ejecutivo oficial completado (incident-reporter) — Clic para ver comunicación" aria-label="Mensaje Ejecutivo disponible">
                  <span class="mark-icon" aria-hidden="true">📢</span><span>Mensajes</span>
                </button>
              ` : `
                <span class="triage-micro-mark is-pending" title="Mensajes ejecutivos pendientes de redacción">
                  <span class="mark-icon" aria-hidden="true">⏳</span><span>Sin Mensajes</span>
                </span>
              `}
            </div>
          </div>
        </td>

        <!-- 3 Columna: Proceso Crítico y Sistemas -->
        <td class="triage-cell-process-systems triage-cell-process">
          <div class="triage-process-row">
            <span class="triage-process-badge" style="font-size: 11.5px; padding: 4px 8px;">
              <span aria-hidden="true">🏢</span> ${escapeHtml(proceso)}
            </span>
          </div>
          <div class="triage-systems-tags" style="margin-top: 5px;">
            ${sysTagsHtml || '<span class="triage-sys-tag">Sistemas Core</span>'}
          </div>
        </td>

        <!-- 4 Columna: Remedy INI -->
        <td class="triage-cell-remedy" style="text-align: center;">
          <span class="triage-sev-badge ${remedyBadgeClass}">${escapeHtml(sevNominal)}</span>
        </td>

        <!-- 5 Columna: Severidad Itil -->
        <td class="triage-cell-itil" style="text-align: center;">
          <div class="triage-itil-wrapper">
            <span class="triage-sev-badge ${itilBadgeClass}">${itilLabel}</span>
            ${isDisc ? `
              <span class="triage-itil-delta-sub delta-${delta >= 2 ? '2' : '1'}" title="Discrepancia detectada: subescalación N1 de ${delta} nivel(es)">
                +${delta} Nivel${delta > 1 ? 'es' : ''}
              </span>
            ` : ''}
          </div>
        </td>

        <!-- 6 Columna: Acciones -->
        <td class="triage-cell-actions">
          <div class="triage-actions-cell-group">
            ${isDisc ? `
              <button type="button" class="triage-btn-table-reclass btn-copy-reclass" data-inc="${escapeHtml(incId)}" title="Copiar solicitud formal al portapapeles para pegar en el worklog de Remedy">
                <span aria-hidden="true">⚡</span> Reclasificar
              </button>
            ` : ''}
            ${isP1 ? `
              <button type="button" class="triage-btn-table-orchestrator btn-open-orchestrator" data-inc="${escapeHtml(incId)}" title="Abrir Módulo 2: Orquestador Operativo, War Room Teams y Relojes de Escalado">
                <span aria-hidden="true">🚨</span> Orquestador
              </button>
            ` : ''}
            <button type="button" class="triage-btn-table-toggle btn-toggle-row" data-inc="${escapeHtml(incId)}">
              <span>${isOpen ? 'Plegar ▴' : 'Detalle ▾'}</span>
            </button>
          </div>
        </td>
      </tr>

      <!-- Fila Plegable / Desplegable de Detalle Extendido -->
      <tr class="triage-row-detail ${isOpen ? 'is-open' : ''}" id="detail-row-${escapeHtml(incId)}" data-inc="${escapeHtml(incId)}">
        <td colspan="6">
          <div class="triage-detail-wrapper">
            
            <!-- TARJETA DE GUÍA OPERATIVA PARA EL OPERADOR DE CONSOLA (incident-triage-review) -->
            <div class="triage-operator-guidance-card ${opBadgeClass}">
              <div class="triage-op-header">
                <div class="triage-op-title-group">
                  <span class="triage-op-badge-large ${opBadgeClass}">
                    <span aria-hidden="true">${opBadgeIcon}</span> ${escapeHtml(catOperativa.replace(/_/g, ' '))}
                  </span>
                  <h4 class="triage-op-alert-text">${escapeHtml(alertaConsola || 'INSTRUCCIÓN OPERATIVA PARA EL OPERADOR DE CONSOLA')}</h4>
                </div>
                <div class="triage-op-protocol-flags">
                  <span class="triage-op-protocol-pill ${reqLlamadaCso ? 'pill-cso-yes' : 'pill-cso-no'}" title="${reqLlamadaCso ? 'Protocolo CSO: Requiere llamada telefónica obligatoria antes de 45 min' : 'No requiere llamada a IM-CSO: evitar saturación telefónica de emergencias'}">
                    <span class="pill-icon" aria-hidden="true">📞</span>
                    <span>Llamada IM-CSO: <strong>${reqLlamadaCso ? 'OBLIGATORIA' : 'NO REQUERIDA'}</strong></span>
                  </span>
                  <span class="triage-op-protocol-pill ${reqComunicadoDir ? 'pill-comms-yes' : 'pill-comms-no'}" title="${reqComunicadoDir ? 'Requiere redacción de mensaje ejecutivo oficial para Dirección' : 'No requiere comunicado ejecutivo para Dirección'}">
                    <span class="pill-icon" aria-hidden="true">📢</span>
                    <span>Comms Dirección: <strong>${reqComunicadoDir ? 'OBLIGATORIO' : 'NO REQUERIDO'}</strong></span>
                  </span>
                  <span class="triage-op-protocol-pill pill-channel" title="Canal de escalado u operación prescrito">
                    <span class="pill-icon" aria-hidden="true">📡</span>
                    <span>Canal: <strong>${escapeHtml(formatCanalEscalado(canalEscalado))}</strong></span>
                  </span>
                </div>
              </div>

              <div class="triage-op-body">
                <div class="triage-op-action-box">
                  <span class="triage-op-action-kicker">🎯 INSTRUCCIÓN OPERATIVA Y ACCIÓN RECOMENDADA:</span>
                  <p class="triage-op-action-desc">${escapeHtml(accionRecomendada || 'Realizar seguimiento estándar según matriz de severidad ITIL.')}</p>
                </div>
                <div class="triage-op-scenario-bar">
                  <span class="triage-op-scenario-title">
                    <span aria-hidden="true">📑</span>
                    <strong>${escapeHtml(guia.escenario_titulo || 'Procedimiento Oficial IM-CSO')}</strong>
                  </span>
                  <a href="${escapeHtml(guia.escenario_url || '../../docs/#/02-gestion-emergencias/protocolo-im-cso-escenarios-triaje')}" target="_blank" rel="noopener noreferrer" class="triage-btn-scenario-doc" title="Abrir procedimiento operativo oficial en Docsify">
                    📖 Ver Protocolo Escenario ${escapeHtml(String(guia.escenario_num || ''))} ↗
                  </a>
                </div>
                ${catOperativa === 'TICKET_ZOMBI_REMEDY' ? `
                  <div class="triage-op-zombi-action" style="margin-top: 8px;">
                    <button type="button" class="triage-btn-zombi-copy btn-copy-zombi-close" data-inc="${escapeHtml(incId)}" title="Copiar solicitud formal de cierre administrativo para Remedy">
                      <span aria-hidden="true">📋</span> Copiar Plantilla de Cierre Administrativo Remedy
                    </button>
                  </div>
                ` : ''}
              </div>
            </div>

            <div class="triage-detail-grid">
              
              <!-- Columna 1: Evaluador de Umbrales Críticos y Comparativa -->
              <div class="triage-detail-col">
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

                <!-- Comparador Remedy vs ITIL y Motivo de Reclasificación -->
                <div class="triage-reclass-box ${isDisc ? (delta === 1 ? 'is-delta1' : '') : 'is-nominal-ok'}" style="margin: 0;">
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
                      <span class="triage-sev-badge ${itilBadgeClass}">${itilFullLabel}</span>
                    </div>
                  </div>

                  ${isDisc ? `
                    <div class="triage-reclass-reason">
                      <strong>Motivo del Dictamen de Reclasificación:</strong> ${escapeHtml(inc.discrepancia_motivo || 'Ticket clasificado por debajo del umbral objetivo corporativo de emergencias.')}
                    </div>
                  ` : ''}
                </div>
              </div>

              <!-- Columna 2: Diagnóstico Epsilon Resumen IA -->
              <div class="triage-detail-col">
                <div class="triage-detail-box" style="height: 100%;">
                  <div class="triage-detail-box-title" style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="display: flex; align-items: center; gap: 6px; color: var(--triage-text-main);">
                      <span style="color: var(--triage-orange);">🤖</span> Diagnóstico Epsilon Resumen IA
                    </span>
                    <button type="button" class="btn-view-epsilon" data-inc="${escapeHtml(incId)}" title="Ver ficha técnica completa y línea de tiempo oficial en Epsilon IA" style="background: rgba(255, 121, 0, 0.08); border: 1px solid rgba(255, 121, 0, 0.3); border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: 600; color: var(--triage-orange); cursor: pointer; display: inline-flex; align-items: center; gap: 4px;">
                      <span aria-hidden="true">🔍</span> Ficha Completa
                    </button>
                  </div>

                  <div class="triage-epsilon-grid" style="margin-top: 4px;">
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
                      <span class="triage-epsilon-label">Siguiente Acción / Bloqueos</span>
                      <span class="triage-epsilon-val">${escapeHtml((resumenIa.siguiente_accion && !['[]', '{}', 'None', 'null', 'N/A', '-', 'none'].includes(resumenIa.siguiente_accion.trim())) ? resumenIa.siguiente_accion : (epsilonBloqueos || 'Coordinación con soporte resolutor.'))}</span>
                    </div>
                  </div>

                  <div class="triage-detail-enrichment-bar" style="margin-top: 10px; padding-top: 8px; border-top: 1px dashed var(--triage-border-light); display: flex; align-items: center; justify-content: space-between; font-size: 11.5px;">
                    <span style="color: var(--triage-text-muted);">
                      <strong>Comunicación Oficial Dirección:</strong>
                      ${hasMensajesEjecutivos ? `<span style="color: var(--triage-green-text); font-weight: 600;">✅ Redactada (incident-reporter)</span>` : `<span style="color: var(--triage-text-subtle); font-style: italic;">⏳ Pendiente de redacción oficial</span>`}
                    </span>
                    ${hasMensajesEjecutivos ? `
                      <button type="button" class="btn-open-exec-comm" data-inc="${escapeHtml(incId)}" style="background: none; border: none; color: var(--triage-blue-text); font-weight: 600; cursor: pointer; text-decoration: underline; padding: 0;">
                        Ver Mensaje Oficial ↗
                      </button>
                    ` : ''}
                  </div>
                </div>
              </div>

            </div>

            <!-- Barra Inferior de Acciones -->
            <div class="triage-detail-footer">
              <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                ${isDisc ? `
                  <button type="button" class="triage-btn-action-reclass btn-copy-reclass" data-inc="${escapeHtml(incId)}" title="Copiar solicitud formal al portapapeles para pegar en el worklog de Remedy">
                    <span aria-hidden="true">⚡</span> Copiar Solicitud Reclasificación Remedy
                  </button>
                ` : ''}
                <button type="button" class="triage-btn-action-orchestrator btn-open-orchestrator" data-inc="${escapeHtml(incId)}" title="Abrir Módulo 2: Orquestador Operativo, War Room Teams, Monitor PaP y Relojes">
                  <span aria-hidden="true">🚨</span> Abrir Orquestador Operativo &amp; War Room (Módulo 2)
                </button>
                <button type="button" class="triage-btn triage-btn-sm btn-copy-report" data-inc="${escapeHtml(incId)}" title="Copiar Reporte Oficial de Emergencias en 4 Bloques">
                  <span aria-hidden="true">📋</span> Copiar Reporte 4 Bloques
                </button>
              </div>

              <div style="font-family: var(--font-mono); font-size: 11px; color: var(--triage-text-subtle); display: flex; align-items: center; gap: 14px; flex-wrap: wrap;">
                <span>⏱️ SLA 1ª Notif: &lt;20m</span>
                <span>🔄 Frecuencia: 60m</span>
                <span>📞 Canal: Telefónico Obligatorio</span>
              </div>
            </div>

          </div>
        </td>
      </tr>
    `;
  }

  // Alias para mantener compatibilidad total
  const renderTriageCard = renderTableRow;

  // --------------------------------------------------------------------------
  // Lógica de Plegado / Desplegado e Interacción
  // --------------------------------------------------------------------------

  function toggleRow(incId, forceState) {
    const isCurrentlyOpen = Boolean(state.expandedRows[incId]);
    const nextState = (forceState !== undefined) ? forceState : !isCurrentlyOpen;
    state.expandedRows[incId] = nextState;

    const mainRow = document.querySelector(`.triage-row-main[data-inc="${incId}"]`);
    const detailRow = document.querySelector(`.triage-row-detail[data-inc="${incId}"]`);
    const chevronBtn = document.querySelector(`.triage-chevron-btn[data-inc="${incId}"]`);
    const toggleBtn = document.querySelector(`.btn-toggle-row[data-inc="${incId}"]`);

    if (mainRow) {
      mainRow.classList.toggle('is-expanded', nextState);
      mainRow.setAttribute('aria-expanded', String(nextState));
    }
    if (detailRow) {
      detailRow.classList.toggle('is-open', nextState);
    }
    if (chevronBtn) {
      chevronBtn.classList.toggle('is-expanded', nextState);
      chevronBtn.setAttribute('aria-label', nextState ? 'Plegar detalle' : 'Desplegar detalle');
    }
    if (toggleBtn) {
      toggleBtn.innerHTML = `<span>${nextState ? 'Plegar ▴' : 'Detalle ▾'}</span>`;
    }
  }

  function toggleAllRows() {
    state.allExpanded = !state.allExpanded;
    const filtered = getFilteredIncidents();
    filtered.forEach(inc => {
      state.expandedRows[inc.id] = state.allExpanded;
    });
    renderFeed();
  }

  function getRoleMeta(roleKey) {
    switch (roleKey) {
      case 'IM':
        return { label: '👤 Incident Manager', extraClass: 'role-im' };
      case 'TECNICO':
        return { label: '⚙️ Soporte Resolutor', extraClass: 'role-resolutor' };
      case 'REDES':
        return { label: '🌐 Redes & Comunicaciones', extraClass: 'role-redes' };
      case 'SISTEMAS':
        return { label: '💻 Sistemas & Cloud', extraClass: 'role-sistemas' };
      case 'DBA':
        return { label: '🗄️ Base de Datos (DBA)', extraClass: 'role-dba' };
      case 'ESCALADO':
        return { label: '📞 Escalado Telefónico', extraClass: 'role-escalado' };
      case 'ROLLBACK':
        return { label: '⏪ Rollback PaP', extraClass: 'role-rollback' };
      case 'NOTIFICACION':
        return { label: '📝 Notificación Dirección', extraClass: 'role-notificacion' };
      case 'WARROOM':
        return { label: '📡 War Room Teams', extraClass: 'role-warroom' };
      default:
        return { label: '📌 Operaciones IT', extraClass: '' };
    }
  }

  function attachFeedEventListeners() {
    // 1. Botón Expandir Todas / Plegar Todas
    const btnToggleAll = document.getElementById('btn-toggle-all-rows');
    if (btnToggleAll) {
      btnToggleAll.addEventListener('click', toggleAllRows);
    }

    // 2. Botón Copiar Solicitud Reclasificación Remedy
    document.querySelectorAll('.btn-copy-reclass').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const incId = btn.getAttribute('data-inc');
        const inc = state.incidents.find(i => i.id === incId);
        if (inc) {
          const text = buildFormalReclassificationText(inc);
          copyToClipboard(text, `¡Solicitud de reclasificación para ${incId} copiada! Pégala en el log de Remedy.`);
        }
      });
    });

    // 3. Botón Copiar Reporte de Emergencia en 4 Bloques
    document.querySelectorAll('.btn-copy-report').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const incId = btn.getAttribute('data-inc');
        const inc = state.incidents.find(i => i.id === incId);
        if (inc) {
          const text = build4BlockEmergencyReport(inc);
          copyToClipboard(text, `Reporte oficial de emergencia en 4 bloques copiado para ${incId}`);
        }
      });
    });

    // 4. Botón Abrir Orquestador Operativo (Módulo 2)
    document.querySelectorAll('.btn-open-orchestrator').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const incId = btn.getAttribute('data-inc');
        if (incId) openEmergencyOrchestrator(incId);
      });
    });

    // 5. Botón Ver Ficha Completa Epsilon IA (abre modal interactivo)
    document.querySelectorAll('.btn-view-epsilon, .triage-id-link').forEach(elem => {
      elem.addEventListener('click', (e) => {
        e.stopPropagation();
        const incId = elem.getAttribute('data-inc') || elem.textContent.trim();
        if (incId) {
          if (typeof window.openResumenIA === 'function') {
            window.openResumenIA(incId);
          } else if (window.ResumenIAModal && typeof window.ResumenIAModal.open === 'function') {
            window.ResumenIAModal.open(incId);
          }
        }
      });
    });

        // 5b. Botón Ver Mensaje Ejecutivo Oficial (abre modal de comunicaciones de incident-reporter)
    document.querySelectorAll('.btn-open-exec-comm').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const incId = btn.getAttribute('data-inc');
        if (incId) {
          openExecutiveCommModal(incId, 'inicial');
        }
      });
    });

    // 5c. Botón Copiar Plantilla Cierre Administrativo Zombi Remedy
    document.querySelectorAll('.btn-copy-zombi-close').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const incId = btn.getAttribute('data-inc');
        const inc = state.incidents.find(i => i.id === incId);
        if (inc) {
          const text = buildZombieClosureText(inc);
          copyToClipboard(text, `Plantilla de cierre administrativo copiada para ${incId}`);
        }
      });
    });

// 6. Chevron y Botón Toggle fila
    document.querySelectorAll('.triage-chevron-btn, .btn-toggle-row').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const incId = btn.getAttribute('data-inc');
        if (incId) toggleRow(incId);
      });
    });

    // 7. Clic e interacción por teclado en la fila principal
    document.querySelectorAll('.triage-row-main').forEach(row => {
      row.addEventListener('click', (e) => {
        // Ignorar si el clic ocurrió dentro de un botón interactivo
        if (e.target.closest('button, a, input, select, textarea')) return;
        const incId = row.getAttribute('data-inc');
        if (incId) toggleRow(incId);
      });

      row.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          if (e.target.closest('button, a, input, select, textarea')) return;
          e.preventDefault();
          const incId = row.getAttribute('data-inc');
          if (incId) toggleRow(incId);
        }
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

    if (dom.tabOrchestrator) {
      dom.tabOrchestrator.addEventListener('click', () => {
        state.activeFilter = 'orchestrator_only';
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

    // Botón Sincronizar Remedy (MonTMC API)
    if (dom.btnSyncRemedy) {
      dom.btnSyncRemedy.addEventListener('click', triggerRemedySync);
    }

    // Botón Refrescar Worklog Remedy en Orquestador
    if (dom.btnRefreshRemedyWorklog) {
      dom.btnRefreshRemedyWorklog.addEventListener('click', () => {
        if (state.activeOrchIncId) {
          loadRemedyWorklog(state.activeOrchIncId, true);
        }
      });
    }

    // Selector de intervalo de vigilancia automática
    if (dom.autoRefreshSelect) {
      dom.autoRefreshSelect.addEventListener('change', (e) => {
        const val = parseInt(e.target.value, 10);
        state.refreshIntervalMs = val;
        resetAutoRefreshTimer();
        if (val > 0) {
          setConnectionStatus('', 'Vigilancia SLA Activa');
          showToast(`Vigilancia continua programada cada ${val / 1000}s`, 'info');
        } else {
          setConnectionStatus('paused', 'Vigilancia Pausada');
          showToast('Vigilancia continua de SLAs pausada', 'info');
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
    }

    // Modal Orquestador Operativo (Módulo 2)
    if (dom.btnOrchClose) {
      dom.btnOrchClose.addEventListener('click', closeEmergencyOrchestrator);
    }
    if (dom.modalOrchestrator) {
      dom.modalOrchestrator.addEventListener('click', (e) => {
        if (e.target === dom.modalOrchestrator) closeEmergencyOrchestrator();
      });
    }

    // Modal Rollback (Módulo 2)
    if (dom.modalRollback) {
      dom.modalRollback.addEventListener('click', (e) => {
        if (e.target === dom.modalRollback) dom.modalRollback.classList.remove('open');
      });
    }

    // Modal Notificación Ejecutiva / Generador de Plantillas (Módulo 2)
    if (dom.btnModalExecClose) {
      dom.btnModalExecClose.addEventListener('click', () => {
        if (dom.modalExecutiveComm) dom.modalExecutiveComm.classList.remove('open');
      });
    }
    if (dom.modalExecutiveComm) {
      dom.modalExecutiveComm.addEventListener('click', (e) => {
        if (e.target === dom.modalExecutiveComm) dom.modalExecutiveComm.classList.remove('open');
      });
    }

    // Modal Centro de Comunicaciones y Matrices (Módulo 3)
    if (dom.btnCommsClose) {
      dom.btnCommsClose.addEventListener('click', closeCommsCenterModal);
    }
    if (dom.modalCommsCenter) {
      dom.modalCommsCenter.addEventListener('click', (e) => {
        if (e.target === dom.modalCommsCenter) closeCommsCenterModal();
      });
    }

    // --- Traspaso de Guardia en 1 Clic (US-04) ---
    if (dom.btnShiftHandover) {
      dom.btnShiftHandover.addEventListener('click', openShiftHandoverModal);
    }
    if (dom.footerBtnHandover) {
      dom.footerBtnHandover.addEventListener('click', openShiftHandoverModal);
    }
    if (dom.btnModalHandoverClose) {
      dom.btnModalHandoverClose.addEventListener('click', closeShiftHandoverModal);
    }
    if (dom.btnModalHandoverCloseBottom) {
      dom.btnModalHandoverCloseBottom.addEventListener('click', closeShiftHandoverModal);
    }
    if (dom.btnHandoverCopy) {
      dom.btnHandoverCopy.addEventListener('click', () => {
        const txt = dom.handoverReportText ? dom.handoverReportText.value : '';
        if (txt) copyToClipboard(txt, '📋 Informe de traspaso copiado al portapapeles');
      });
    }
    if (dom.btnHandoverCopyBottom) {
      dom.btnHandoverCopyBottom.addEventListener('click', () => {
        const txt = dom.handoverReportText ? dom.handoverReportText.value : '';
        if (txt) copyToClipboard(txt, '📋 Informe de traspaso copiado al portapapeles');
        closeShiftHandoverModal();
      });
    }
    if (dom.modalShiftHandover) {
      dom.modalShiftHandover.addEventListener('click', (e) => {
        if (e.target === dom.modalShiftHandover) closeShiftHandoverModal();
      });
    }

    // --- Borradores Bitácora de Crisis (US-03) ---
    function discardLogDraft() {
      if (!state.activeOrchIncId) return;
      try {
        localStorage.removeItem('triage_draft_log_' + state.activeOrchIncId);
        localStorage.removeItem('triage_draft_role_' + state.activeOrchIncId);
      } catch (_) {}
      if (dom.orchLogText) dom.orchLogText.value = '';
      if (dom.orchLogRole) dom.orchLogRole.value = 'IM';
      if (dom.orchLogDraftAlert) dom.orchLogDraftAlert.style.display = 'none';
      showToast('Borrador de bitácora descartado', 'info');
    }

    if (dom.orchLogText) {
      dom.orchLogText.addEventListener('input', () => {
        if (!state.activeOrchIncId) return;
        const val = dom.orchLogText.value;
        try {
          if (val && val.trim()) {
            localStorage.setItem('triage_draft_log_' + state.activeOrchIncId, val);
            if (dom.orchLogRole) {
              localStorage.setItem('triage_draft_role_' + state.activeOrchIncId, dom.orchLogRole.value);
            }
          } else {
            localStorage.removeItem('triage_draft_log_' + state.activeOrchIncId);
            localStorage.removeItem('triage_draft_role_' + state.activeOrchIncId);
            if (dom.orchLogDraftAlert) dom.orchLogDraftAlert.style.display = 'none';
          }
        } catch (_) {}
      });
    }

    if (dom.orchLogRole) {
      dom.orchLogRole.addEventListener('change', () => {
        if (!state.activeOrchIncId) return;
        try {
          localStorage.setItem('triage_draft_role_' + state.activeOrchIncId, dom.orchLogRole.value);
        } catch (_) {}
      });
    }

    if (dom.btnDiscardLogDraft) {
      dom.btnDiscardLogDraft.addEventListener('click', discardLogDraft);
    }
    if (dom.btnOrchLogClear) {
      dom.btnOrchLogClear.addEventListener('click', discardLogDraft);
    }

    // --- Borradores Gateway Web de Explotación (US-03) ---
    if (dom.gwSubject) {
      dom.gwSubject.addEventListener('input', () => {
        const incId = state.activeCommsIncId || 'GENERAL';
        try {
          localStorage.setItem('triage_draft_gw_subj_' + incId, dom.gwSubject.value);
        } catch (_) {}
      });
    }

    if (dom.gwBody) {
      dom.gwBody.addEventListener('input', () => {
        const incId = state.activeCommsIncId || 'GENERAL';
        try {
          localStorage.setItem('triage_draft_gw_body_' + incId, dom.gwBody.value);
        } catch (_) {}
      });
    }

    // Escape universal y Atajos de Consola Globales
    window.addEventListener('keydown', (e) => {
      // 1. Escape: cerrar cualquier modal o pop-up abierto
      if (e.key === 'Escape') {
        const openPopups = document.querySelectorAll('.orch-clock-info-wrap.is-open');
        if (openPopups.length > 0) {
          closeAllClockPopups();
          return;
        }
        if (dom.modalBackdrop && dom.modalBackdrop.classList.contains('open')) {
          dom.modalBackdrop.classList.remove('open');
        }
        if (dom.modalOrchestrator && dom.modalOrchestrator.classList.contains('open')) {
          closeEmergencyOrchestrator();
        }
        if (dom.modalRollback && dom.modalRollback.classList.contains('open')) {
          dom.modalRollback.classList.remove('open');
        }
        if (dom.modalExecutiveComm && dom.modalExecutiveComm.classList.contains('open')) {
          dom.modalExecutiveComm.classList.remove('open');
        }
        if (dom.modalCommsCenter && dom.modalCommsCenter.classList.contains('open')) {
          closeCommsCenterModal();
        }
        if (dom.modalShiftHandover && dom.modalShiftHandover.classList.contains('open')) {
          closeShiftHandoverModal();
        }
        if (dom.modalIngestionAudit && dom.modalIngestionAudit.classList.contains('open')) {
          closeIngestionAuditModal();
        }
        return;
      }

      // No interceptar atajos si el foco está en un campo de edición/texto
      const activeEl = document.activeElement;
      const tag = activeEl ? activeEl.tagName.toLowerCase() : '';
      if (tag === 'input' || tag === 'textarea' || (activeEl && activeEl.isContentEditable)) {
        return;
      }

      // Atajo 'F' / 'f': Plegar / Desplegar Footer
      if ((e.key === 'f' || e.key === 'F') && !e.ctrlKey && !e.metaKey && !e.altKey && !e.shiftKey) {
        e.preventDefault();
        toggleFooter();
        return;
      }

      // Atajo 'Shift+H': Informe Oficial de Traspaso de Guardia
      if (e.shiftKey && (e.key === 'H' || e.key === 'h') && !e.ctrlKey && !e.metaKey && !e.altKey) {
        e.preventDefault();
        openShiftHandoverModal();
        return;
      }

      // Atajo 'Shift+M': Buscador de Matrices de Contacto (GRIAL / MasMóvil)
      if (e.shiftKey && (e.key === 'M' || e.key === 'm') && !e.ctrlKey && !e.metaKey && !e.altKey) {
        e.preventDefault();
        openCommsCenterModal(null, 'tab-contacts');
        return;
      }

      // Atajo 'Shift+U': Matriz de Umbrales Oficiales de Emergencia IT
      if (e.shiftKey && (e.key === 'U' || e.key === 'u') && !e.ctrlKey && !e.metaKey && !e.altKey) {
        e.preventDefault();
        if (dom.modalBackdrop) dom.modalBackdrop.classList.add('open');
        return;
      }

      // Atajo 'Shift+I' o 'Shift+C': Consola de Auditoría de Carga & Telemetría IA
      if (e.shiftKey && (e.key === 'I' || e.key === 'i' || e.key === 'C' || e.key === 'c') && !e.ctrlKey && !e.metaKey && !e.altKey) {
        e.preventDefault();
        openIngestionAuditModal();
        return;
      }
    });

    // Gestión interactiva de los Pop-ups de Notas Informativas en los 4 Relojes
    function closeAllClockPopups() {
      document.querySelectorAll('.orch-clock-info-wrap.is-open').forEach(wrap => {
        wrap.classList.remove('is-open');
        const btn = wrap.querySelector('.orch-clock-info-btn');
        if (btn) btn.setAttribute('aria-expanded', 'false');
        const popup = wrap.querySelector('.orch-clock-popup');
        if (popup) popup.setAttribute('aria-hidden', 'true');
      });
    }

    document.addEventListener('click', (e) => {
      // 1. Clic en botón de cierre 'x'
      const closeBtn = e.target.closest('.orch-popup-close');
      if (closeBtn) {
        e.preventDefault();
        e.stopPropagation();
        const wrap = closeBtn.closest('.orch-clock-info-wrap');
        if (wrap) {
          wrap.classList.remove('is-open');
          const btn = wrap.querySelector('.orch-clock-info-btn');
          if (btn) {
            btn.setAttribute('aria-expanded', 'false');
            btn.focus();
          }
          const popup = wrap.querySelector('.orch-clock-popup');
          if (popup) popup.setAttribute('aria-hidden', 'true');
        }
        return;
      }

      // 2. Clic en botón disparador 'ℹ️'
      const infoBtn = e.target.closest('.orch-clock-info-btn');
      if (infoBtn) {
        e.preventDefault();
        e.stopPropagation();
        const wrap = infoBtn.closest('.orch-clock-info-wrap');
        if (!wrap) return;
        const willOpen = !wrap.classList.contains('is-open');
        closeAllClockPopups();
        if (willOpen) {
          wrap.classList.add('is-open');
          infoBtn.setAttribute('aria-expanded', 'true');
          const popup = wrap.querySelector('.orch-clock-popup');
          if (popup) popup.setAttribute('aria-hidden', 'false');
        }
        return;
      }

      // 3. Clic dentro del contenido de un pop-up (no cerrar)
      if (e.target.closest('.orch-clock-popup')) {
        return;
      }

      // 4. Clic fuera: cerrar cualquier pop-up abierto
      closeAllClockPopups();
    });

    // Formulario de Bitácora del Orquestador
    if (dom.orchLogForm) {
      dom.orchLogForm.addEventListener('submit', (e) => {
        e.preventDefault();
        if (!state.activeOrchIncId) return;
        const text = (dom.orchLogText ? dom.orchLogText.value : '').trim();
        const roleKey = dom.orchLogRole ? dom.orchLogRole.value : 'IM';
        if (!text) return;
        const meta = getRoleMeta(roleKey);
        addLogEntry(state.activeOrchIncId, roleKey, meta.label, text, meta.extraClass);
        if (dom.orchLogText) dom.orchLogText.value = '';
        try {
          localStorage.removeItem('triage_draft_log_' + state.activeOrchIncId);
          localStorage.removeItem('triage_draft_role_' + state.activeOrchIncId);
        } catch (_) {}
        if (dom.orchLogDraftAlert) dom.orchLogDraftAlert.style.display = 'none';
        showToast('Hito operativo registrado en la bitácora', 'success');
      });
    }

    // Botones de Bitácora
    if (dom.btnCopyFullLog) {
      dom.btnCopyFullLog.addEventListener('click', () => {
        if (!state.activeOrchIncId) return;
        const fullText = formatFullLogForClipboard(state.activeOrchIncId);
        copyToClipboard(fullText, '¡Bitácora completa copiada al portapapeles!');
      });
    }

    // Selector de Modo Dual Clock (T0 Crisis vs Envejecimiento Remedy)
    if (dom.btnModeCrisis) {
      dom.btnModeCrisis.addEventListener('click', () => {
        state.clockTimeBase = 'crisis';
        updateOrchestratorClocks();
        showToast('Temporizadores en Modo Crisis (T0 Activación SL1)', 'info');
      });
    }
    if (dom.btnModeRemedy) {
      dom.btnModeRemedy.addEventListener('click', () => {
        state.clockTimeBase = 'remedy';
        updateOrchestratorClocks();
        showToast('Temporizadores en Modo Remedy (Envejecimiento Contractual)', 'info');
      });
    }

    if (dom.btnClearLog) {
      dom.btnClearLog.addEventListener('click', () => {
        if (!state.activeOrchIncId) return;
        if (confirm(`¿Deseas reiniciar la bitácora operativa de ${state.activeOrchIncId}? Se restaurarán los hitos iniciales de activación.`)) {
          const inc = state.incidents.find(i => i.id === state.activeOrchIncId);
          localStorage.removeItem('emergency_log_' + state.activeOrchIncId);
          localStorage.removeItem('emergency_activation_' + state.activeOrchIncId);
          delete state.orchestratorLogs[state.activeOrchIncId];
          delete state.orchestratorActivations[state.activeOrchIncId];
          state.orchestratorActivations[state.activeOrchIncId] = Date.now();
          try {
            localStorage.setItem('emergency_activation_' + state.activeOrchIncId, String(state.orchestratorActivations[state.activeOrchIncId]));
          } catch (_) {}
          getOrInitLog(state.activeOrchIncId, inc);
          renderTimelineEntries(state.activeOrchIncId);
          updateOrchestratorClocks();
          showToast('Bitácora y temporizador de crisis reiniciados con éxito', 'info');
        }
      });
    }

    // Acciones de los 4 Relojes de Escalado Controlados
    // Reloj 1: SLA 20 min (Abre modal de comunicación ejecutiva)
    if (dom.btnAction20m) {
      dom.btnAction20m.addEventListener('click', () => {
        if (!state.activeOrchIncId) return;
        openExecutiveCommModal(state.activeOrchIncId);
      });
    }

    // Reloj 2: 45 min (1er Escalado Telefónico N2/N3)
    if (dom.btnAction45m) {
      dom.btnAction45m.addEventListener('click', () => {
        if (!state.activeOrchIncId) return;
        const incId = state.activeOrchIncId;
        const escState = state.orchestratorEscalations[incId] || {};
        escState.esc45Done = true;
        state.orchestratorEscalations[incId] = escState;
        try {
          localStorage.setItem('emergency_esc_' + incId, JSON.stringify(escState));
        } catch (_) {}
        addLogEntry(
          incId,
          'ESCALADO',
          '📞 1er Escalado Telefónico N2/N3',
          `1er Escalado Telefónico Obligatorio completado con soporte resolutor N2/N3. Convocatoria a War Room reforzada conforme al protocolo de 45 min.`,
          'role-escalado'
        );
        updateOrchestratorClocks();
        showToast('1er Escalado Telefónico N2/N3 confirmado y registrado', 'success');
      });
    }

    // Reloj 3: T+1h 45m (2º Escalado Jerárquico)
    if (dom.btnAction105m) {
      dom.btnAction105m.addEventListener('click', () => {
        if (!state.activeOrchIncId) return;
        const incId = state.activeOrchIncId;
        const escState = state.orchestratorEscalations[incId] || {};
        escState.esc105Done = true;
        state.orchestratorEscalations[incId] = escState;
        try {
          localStorage.setItem('emergency_esc_' + incId, JSON.stringify(escState));
        } catch (_) {}
        addLogEntry(
          incId,
          'ESCALADO',
          '👔 2º Escalado Jerárquico',
          `2º Escalado Jerárquico ejecutado formalmente a Responsables de Área y Jefatura de Operaciones IT (>1h 45m sin restablecimiento).`,
          'role-escalado'
        );
        updateOrchestratorClocks();
        showToast('2º Escalado Jerárquico confirmado y registrado en bitácora', 'warning');
      });
    }

    // Reloj 4: >2h (Alarma Estancamiento IM-CSO)
    if (dom.btnAction120m) {
      dom.btnAction120m.addEventListener('click', () => {
        if (!state.activeOrchIncId) return;
        const incId = state.activeOrchIncId;
        const inc = state.incidents.find(i => i.id === incId);
        const escState = state.orchestratorEscalations[incId] || {};
        escState.esc120Done = true;
        state.orchestratorEscalations[incId] = escState;
        try {
          localStorage.setItem('emergency_esc_' + incId, JSON.stringify(escState));
        } catch (_) {}

        const teamsUrl = generateTeamsWarRoomUrl(incId);
        const reconveneNotice = `🚨 ALERTA DE ESTANCAMIENTO (>2h) · RE-CONVOCATORIA EJECUTIVA WAR ROOM CSO 🚨
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Incidencia: ${incId} (${inc ? inc.titulo : 'Incidencia Crítica'})
Incident Manager: ${state.defaultIncidentManager}
Estado: Ticket estancado sin mitigación efectiva tras más de 2 horas desde apertura.
Acción Requerida: Convocatoria obligatoria de Gabinete de Crisis con Jefatura Customer & Service Ops (IM-CSO) y Dirección Técnica.
Puente Teams: ${teamsUrl}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`;

        copyToClipboard(reconveneNotice, '¡Alerta de re-convocatoria IM-CSO copiada al portapapeles!');
        addLogEntry(
          incId,
          'WARROOM',
          '🚨 Alarma Estancamiento IM-CSO',
          `Alarma de Estancamiento (>2h) gestionada. Re-convocatoria ejecutiva transmitida formalmente a Customer & Service Ops (IM-CSO) y Dirección de Operaciones.`,
          'role-warroom'
        );
        updateOrchestratorClocks();
        showToast('Alarma de Estancamiento disparada y notificada a IM-CSO', 'error');
      });
    }

    // --- Listeners Módulo 3: Centro de Comunicaciones y Matrices ---
    // Apertura desde cabecera principal (Despacho General / Directorio)
    if (dom.btnOpenCommsCenter) {
      dom.btnOpenCommsCenter.addEventListener('click', () => {
        openCommsCenterModal(null, 'tab-gateway');
      });
    }

    // Pestañas del Centro de Comunicaciones
    document.querySelectorAll('.comms-tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const targetTab = btn.getAttribute('data-tab');
        if (targetTab) switchCommsTab(targetTab);
      });
    });

    // Selector de fase en Generador de Plantillas
    document.querySelectorAll('.comms-phase-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.comms-phase-btn').forEach(b => b.classList.remove('is-active'));
        btn.classList.add('is-active');
        const phase = btn.getAttribute('data-phase') || 'inicial';
        state.activeCommsPhase = phase;
        const inc = state.incidents.find(i => i.id === state.activeCommsIncId);
        if (inc) {
          renderCommsTemplateTab(inc, phase);
        }
      });
    });

    // Conteo en vivo de palabras y auto-guardado en LocalStorage (US-03)
    if (dom.tplTextCompleto) {
      dom.tplTextCompleto.addEventListener('input', () => {
        updateWordCounters();
        const incId = state.activeCommsIncId || state.activeOrchIncId;
        if (incId) {
          const key = `triage_draft_tpl_comp_${incId}_${state.activeCommsPhase || 'inicial'}`;
          try {
            localStorage.setItem(key, dom.tplTextCompleto.value);
          } catch (_) {}
        }
      });
    }
    if (dom.tplTextBreve) {
      dom.tplTextBreve.addEventListener('input', () => {
        updateWordCounters();
        const incId = state.activeCommsIncId || state.activeOrchIncId;
        if (incId) {
          const key = `triage_draft_tpl_brev_${incId}_${state.activeCommsPhase || 'inicial'}`;
          try {
            localStorage.setItem(key, dom.tplTextBreve.value);
          } catch (_) {}
        }
      });
    }

    // Descartar borrador de plantilla ejecutiva y restaurar oficial
    if (dom.btnDiscardTplDraft) {
      dom.btnDiscardTplDraft.addEventListener('click', () => {
        const incId = state.activeCommsIncId || state.activeOrchIncId;
        const phase = state.activeCommsPhase || 'inicial';
        if (incId) {
          try {
            localStorage.removeItem(`triage_draft_tpl_comp_${incId}_${phase}`);
            localStorage.removeItem(`triage_draft_tpl_brev_${incId}_${phase}`);
          } catch (_) {}
          if (dom.tplDraftAlert) dom.tplDraftAlert.style.display = 'none';
          const inc = state.incidents.find(i => i.id === incId);
          if (inc) {
            const data = generateDynamicTemplates(inc, phase);
            if (dom.tplTextCompleto) dom.tplTextCompleto.value = data.completo;
            if (dom.tplTextBreve) dom.tplTextBreve.value = data.breve;
            updateWordCounters();
          }
          showToast('Borrador descartado. Plantilla oficial restaurada.', 'info');
        }
      });
    }

    // Conteo en vivo en cuerpo del Gateway
    const gwBodyCounter = document.getElementById('gw-body-counter');
    if (dom.gwBody && gwBodyCounter) {
      dom.gwBody.addEventListener('input', () => {
        const words = countWords(dom.gwBody.value);
        gwBodyCounter.textContent = `${words} palabras`;
      });
    }

    // Copia de plantillas generadas
    if (dom.btnCopyTplCompleto) {
      dom.btnCopyTplCompleto.addEventListener('click', () => {
        const txt = dom.tplTextCompleto ? dom.tplTextCompleto.value.trim() : '';
        if (txt) copyToClipboard(txt, '¡Versión Completa copiada al portapapeles!');
      });
    }

    if (dom.btnCopyTplBreve) {
      dom.btnCopyTplBreve.addEventListener('click', () => {
        const txt = dom.tplTextBreve ? dom.tplTextBreve.value.trim() : '';
        if (txt) copyToClipboard(txt, '¡Versión Breve SMS copiada al portapapeles!');
      });
    }

    // Regenerar texto con datos del ticket (limpia borradores)
    if (dom.btnTplRegenerate) {
      dom.btnTplRegenerate.addEventListener('click', () => {
        const incId = state.activeCommsIncId || state.activeOrchIncId;
        const phase = state.activeCommsPhase || 'inicial';
        if (incId) {
          try {
            localStorage.removeItem(`triage_draft_tpl_comp_${incId}_${phase}`);
            localStorage.removeItem(`triage_draft_tpl_brev_${incId}_${phase}`);
          } catch (_) {}
          if (dom.tplDraftAlert) dom.tplDraftAlert.style.display = 'none';
          const inc = state.incidents.find(i => i.id === incId);
          if (inc) {
            renderCommsTemplateTab(inc, phase);
            showToast('Textos oficiales regenerados con datos actuales del ticket', 'info');
          }
        }
      });
    }

    // Copiar y Registrar en Bitácora (Módulo 2: Generador de Plantillas)
    if (dom.btnCopyExecCompleto) {
      dom.btnCopyExecCompleto.addEventListener('click', () => {
        const text = dom.tplTextCompleto ? dom.tplTextCompleto.value.trim() : '';
        if (!text) {
          showToast('No hay contenido en la versión completa para copiar', 'warning');
          return;
        }

        copyToClipboard(text, '¡Versión Completa copiada al portapapeles!');

        const incId = state.activeCommsIncId || state.activeOrchIncId;
        if (incId) {
          const phase = state.activeCommsPhase || 'inicial';
          const phaseLabel = phase === 'inicial'
            ? 'Inicial (<20 min)'
            : (phase === 'actualizacion' ? 'Actualización (Seguimiento)' : 'Cierre / Resolución');

          addLogEntry(
            incId,
            'NOTIFICACION',
            `📢 Difusión Notificación Oficial (${phaseLabel})`,
            `Notificación ejecutiva generada y registrada en bitácora. Contenido:\n"${text}"`,
            'role-notificacion'
          );

          // Si es fase inicial o no estaba completado el reloj 1 (comms 20m):
          const escState = state.orchestratorEscalations[incId] || {};
          escState.commDone = true;
          state.orchestratorEscalations[incId] = escState;
          try {
            localStorage.setItem('emergency_esc_' + incId, JSON.stringify(escState));
          } catch (_) {}

          updateOrchestratorClocks();
          showToast('Notificación registrada en bitácora y Reloj 20m completado', 'success');
        }
      });
    }

    // Transferir plantilla generada al Gateway de la Web de Explotación
    if (dom.btnTplLoadGateway) {
      dom.btnTplLoadGateway.addEventListener('click', () => {
        transferTemplateToGateway();
      });
    }

    // Copiar Payload JSON para consumo API REST del Gateway
    if (dom.btnGwCopyPayload) {
      dom.btnGwCopyPayload.addEventListener('click', () => {
        const incId = state.activeCommsIncId || 'INC-UNKNOWN';
        const selectedChannel = document.querySelector('input[name="gw-channel"]:checked')?.value || 'dual';
        const checkedGroups = Array.from(document.querySelectorAll('input[name="gw-group"]:checked')).map(cb => cb.value);
        const payload = {
          gateway: 'Web de Explotacion Orange',
          api_endpoint: 'https://webexplotacion.orange.es/api/v2/notifications/dispatch',
          incident_id: incId,
          timestamp: new Date().toISOString(),
          channel: selectedChannel,
          target_groups: checkedGroups,
          subject: dom.gwSubject ? dom.gwSubject.value : '',
          message_body: dom.gwBody ? dom.gwBody.value : '',
          sender: state.defaultIncidentManager
        };
        copyToClipboard(JSON.stringify(payload, null, 2), '¡Payload JSON copiado para consumo de API REST!');
      });
    }

    // Despachar notificación formal en la Web de Explotación
    if (dom.btnGwDispatch) {
      dom.btnGwDispatch.addEventListener('click', dispatchGatewayMessage);
    }

    // Conmutación de marca en directorio de contactos
    if (dom.btnBrandOrange) {
      dom.btnBrandOrange.addEventListener('click', () => {
        state.activeContactsBrand = 'orange';
        dom.btnBrandOrange.classList.add('is-active');
        if (dom.btnBrandMasmovil) dom.btnBrandMasmovil.classList.remove('is-active');
        updateCommsBrandBadge('orange');
        renderContactMatrices('orange', dom.contactsSearchInput ? dom.contactsSearchInput.value : '', state.activeContactsDomain);
      });
    }

    if (dom.btnBrandMasmovil) {
      dom.btnBrandMasmovil.addEventListener('click', () => {
        state.activeContactsBrand = 'masmovil';
        dom.btnBrandMasmovil.classList.add('is-active');
        if (dom.btnBrandOrange) dom.btnBrandOrange.classList.remove('is-active');
        updateCommsBrandBadge('masmovil');
        renderContactMatrices('masmovil', dom.contactsSearchInput ? dom.contactsSearchInput.value : '', state.activeContactsDomain);
      });
    }

    // Buscador en vivo de matrices de contacto
    if (dom.contactsSearchInput) {
      dom.contactsSearchInput.addEventListener('input', (e) => {
        renderContactMatrices(state.activeContactsBrand, e.target.value, state.activeContactsDomain);
      });
    }

    // Filtros de dominio funcional en matrices
    if (dom.contactsDomainPills) {
      dom.contactsDomainPills.querySelectorAll('button').forEach(pill => {
        pill.addEventListener('click', () => {
          dom.contactsDomainPills.querySelectorAll('button').forEach(p => p.classList.remove('is-active'));
          pill.classList.add('is-active');
          const domain = pill.getAttribute('data-domain') || 'ALL';
          state.activeContactsDomain = domain;
          renderContactMatrices(state.activeContactsBrand, dom.contactsSearchInput ? dom.contactsSearchInput.value : '', domain);
        });
      });
    }

    // --- Funciones y Listeners Footer Corporativo Desplegable ---
    function setFooterExpanded(expanded, persist = true) {
      const footer = dom.triageFooter || document.getElementById('triage-footer');
      const header = dom.triageFooterHeader || document.getElementById('triage-footer-header');
      const toggleBtn = dom.footerBtnToggle || document.getElementById('footer-btn-toggle');
      const expandable = dom.footerExpandable || document.getElementById('triage-footer-expandable');

      if (!footer) return;

      if (expanded) {
        footer.classList.add('is-expanded');
      } else {
        footer.classList.remove('is-expanded');
      }

      if (header) {
        header.setAttribute('aria-expanded', expanded ? 'true' : 'false');
      }
      if (toggleBtn) {
        toggleBtn.setAttribute('aria-expanded', expanded ? 'true' : 'false');
        const textSpan = toggleBtn.querySelector('.footer-toggle-text');
        if (textSpan) {
          textSpan.textContent = expanded ? 'Plegar' : 'Desplegar';
        }
      }
      if (expandable) {
        expandable.setAttribute('aria-hidden', expanded ? 'false' : 'true');
      }

      if (persist) {
        try {
          localStorage.setItem('triage_footer_expanded', expanded ? 'true' : 'false');
        } catch (_) {}
      }
    }

    function toggleFooter() {
      const footer = dom.triageFooter || document.getElementById('triage-footer');
      if (!footer) return;
      const isExpanded = footer.classList.contains('is-expanded');
      setFooterExpanded(!isExpanded, true);
    }

    function initFooterCollapse() {
      // Estado inicial persistido (por defecto colapsado para maximizar el área de trabajo)
      let isExpanded = false;
      try {
        const saved = localStorage.getItem('triage_footer_expanded');
        isExpanded = (saved === 'true');
      } catch (_) {}
      setFooterExpanded(isExpanded, false);

      // Clic directo en el botón de conmutación
      const toggleBtn = dom.footerBtnToggle || document.getElementById('footer-btn-toggle');
      if (toggleBtn) {
        toggleBtn.addEventListener('click', (e) => {
          e.stopPropagation();
          toggleFooter();
        });
      }

      // Clic o pulsación (Enter/Espacio) en la cabecera del footer
      const header = dom.triageFooterHeader || document.getElementById('triage-footer-header');
      if (header) {
        header.addEventListener('click', (e) => {
          if (e.target.closest('#footer-btn-scroll-top, #footer-btn-toggle, a')) return;
          toggleFooter();
        });

        header.addEventListener('keydown', (e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            if (e.target.closest('#footer-btn-scroll-top, #footer-btn-toggle, a')) return;
            e.preventDefault();
            toggleFooter();
          }
        });
      }
    }

    // Inicializar colapso/despliegue del footer
    initFooterCollapse();

    // Inicializar secciones plegables del Módulo 2 (plegadas por defecto en Fase 1)
    initOrchestratorCollapsibleSections();

    const btnFooterScrollTop = document.getElementById('footer-btn-scroll-top');
    if (btnFooterScrollTop) {
      btnFooterScrollTop.addEventListener('click', () => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
      });
    }

    const btnFooterMatrices = document.getElementById('footer-btn-matrices');
    if (btnFooterMatrices) {
      btnFooterMatrices.addEventListener('click', () => {
        openCommsCenterModal(null, 'tab-contacts');
      });
    }

    const footerEnvName = document.getElementById('footer-env-name');
    if (footerEnvName) {
      const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
      footerEnvName.textContent = isLocal ? 'Desarrollo Local (localhost)' : 'Producción VPS (infocodes)';
    }

    const footerScanFreq = document.getElementById('footer-scan-freq');
    if (dom.autoRefreshSelect && footerScanFreq) {
      const updateFooterFreq = () => {
        const val = parseInt(dom.autoRefreshSelect.value, 10);
        footerScanFreq.textContent = val === 0 ? 'Vigilancia: Pausada' : `Ciclo: ${val / 1000}s`;
      };
      dom.autoRefreshSelect.addEventListener('change', updateFooterFreq);
      updateFooterFreq();
    }
  }

  function updateTabStyles() {
    [dom.tabReclassOnly, dom.tabOrchestrator, dom.tabAll, dom.tabCorrectOnly].forEach(btn => {
      if (btn) btn.classList.remove('active');
    });
    if (state.activeFilter === 'reclass_only' && dom.tabReclassOnly) dom.tabReclassOnly.classList.add('active');
    if (state.activeFilter === 'orchestrator_only' && dom.tabOrchestrator) dom.tabOrchestrator.classList.add('active');
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


  // ==========================================================================
  // Módulo de Auditoría de Carga & Telemetría IA (Atajo Shift+I / Shift+C)
  // ==========================================================================
  let ingestionAuditData = null;
  let activeAuditTab = 'tickets';

  async function openIngestionAuditModal() {
    if (!dom.modalIngestionAudit) return;
    dom.modalIngestionAudit.classList.add('open');
    dom.modalIngestionAudit.setAttribute('aria-hidden', 'false');
    await loadIngestionAuditData();
  }

  function closeIngestionAuditModal() {
    if (!dom.modalIngestionAudit) return;
    dom.modalIngestionAudit.classList.remove('open');
    dom.modalIngestionAudit.setAttribute('aria-hidden', 'true');
  }

  async function loadIngestionAuditData(showLoading = true) {
    if (showLoading && dom.auditActionStatus) {
      dom.auditActionStatus.style.display = 'flex';
      dom.auditActionStatus.className = 'audit-action-status is-loading';
      dom.auditActionStatus.innerHTML = '<span class="audit-spinner">⏳</span> Cargando estado de la carga y trazas de auditoría...';
    }

    try {
      let data = null;
      let usingFallback = false;
      let isEmptyState = false;

      // 1. Intentar endpoint dinámico de la API
      try {
        const resp = await fetch('/api/logs/ingestion');
        if (resp.ok) {
          data = await resp.json();
        }
      } catch (netErr) {
        console.warn('API /api/logs/ingestion no alcanzable, recurriendo a almacenamiento estático:', netErr);
      }

      // 2. Si la API devolvió 404 o falló (servidor estático Nginx o sin API activa), leer de /data/
      if (!data || !data.success) {
        const timestamp = Date.now();
        let summaryJson = null;

        try {
          const summaryResp = await fetch('/data/output/ingestion_audit_summary.json?t=' + timestamp);
          if (summaryResp.ok) {
            summaryJson = await summaryResp.json();
          } else if (summaryResp.status !== 404) {
            console.warn(`HTTP ${summaryResp.status} al consultar ingestion_audit_summary.json`);
          }
        } catch (fetchErr) {
          console.warn('Error accediendo a ingestion_audit_summary.json:', fetchErr);
        }

        let logTailText = 'Sin trazas de log disponibles.';
        try {
          const logResp = await fetch('/data/logs/ingestion_audit.log?t=' + timestamp);
          if (logResp.ok) {
            const rawLog = await logResp.text();
            const lines = rawLog.split('\n');
            logTailText = lines.slice(-200).join('\n');
          }
        } catch (logErr) {
          console.warn('No se pudo cargar el log estático:', logErr);
        }

        if (summaryJson && summaryJson._metadata) {
          data = {
            success: true,
            has_summary: true,
            has_log: logTailText !== 'Sin trazas de log disponibles.',
            summary: summaryJson,
            log_tail: logTailText
          };
          usingFallback = true;
        } else {
          // Entorno inicial limpio o sin ingestas registradas aún (404 controlado)
          data = {
            success: true,
            has_summary: false,
            has_log: logTailText !== 'Sin trazas de log disponibles.',
            summary: {
              _metadata: {
                timestamp: null,
                source_file: 'Ninguno (sin cargas registradas)',
                elapsed_seconds: 0,
                kpis: {
                  total_tickets: 0,
                  completas_count: 0,
                  parciales_count: 0,
                  incompletas_count: 0,
                  terminales_omitidas_count: 0,
                  con_resumen_ia_count: 0,
                  sin_resumen_ia_count: 0,
                  con_mensajes_ejecutivos_count: 0,
                  sin_mensajes_ejecutivos_count: 0,
                  discrepancias_count: 0
                }
              },
              incidents: []
            },
            log_tail: logTailText !== 'Sin trazas de log disponibles.'
              ? logTailText
              : 'Aún no se ha registrado ningún proceso de ingesta en este entorno.\nSube un fichero CSV desde la sección de carga para iniciar la trazabilidad y la auditoría.'
          };
          usingFallback = true;
          isEmptyState = true;
        }
      }

      ingestionAuditData = data;
      renderIngestionAudit(data);

      const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';

      if (dom.auditActionStatus) {
        if (isEmptyState) {
          dom.auditActionStatus.style.display = 'flex';
          dom.auditActionStatus.className = 'audit-action-status is-warning';
          dom.auditActionStatus.innerHTML = 'ℹ️ Sin cargas previas registradas. Sube un fichero CSV o ejecuta una conversión para generar las primeras trazas de auditoría.';
        } else if (usingFallback) {
          dom.auditActionStatus.style.display = 'flex';
          dom.auditActionStatus.className = 'audit-action-status is-warning';
          if (isLocal) {
            dom.auditActionStatus.innerHTML = 'ℹ️ Datos cargados desde archivo local. Si mantienes <code>serve_app.py</code> en ejecución en tu terminal, <strong>reinícialo (Ctrl+C y python serve_app.py)</strong> para activar la API en vivo y reintentos de IA.';
          } else {
            dom.auditActionStatus.innerHTML = 'ℹ️ Mostrando trazas de auditoría y métricas del almacenamiento persistente.';
          }
        } else if (showLoading) {
          dom.auditActionStatus.style.display = 'none';
        }
      }
    } catch (err) {
      console.error('Error cargando auditoría de ingesta:', err);
      const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
      if (dom.auditActionStatus) {
        dom.auditActionStatus.style.display = 'flex';
        dom.auditActionStatus.className = 'audit-action-status is-error';
        const helpHint = isLocal
          ? 'Asegúrate de reiniciar <code>python serve_app.py</code> en tu terminal.'
          : 'Comprueba la conexión con el servidor o sube un nuevo fichero CSV.';
        dom.auditActionStatus.innerHTML = `⚠️ No se pudo obtener la auditoría: ${escapeHtml(err.message || 'Error desconocido')}. ${helpHint}`;
      }
    }
  }

  function renderIngestionAudit(data) {
    if (!data) return;
    const summary = data.summary || {};
    const meta = summary._metadata || {};
    const kpis = meta.kpis || {};
    const incidents = summary.incidents || [];

    if (dom.auditMetaSource) {
      const src = meta.source_file || 'Fichero masivo';
      const elapsed = meta.elapsed_seconds ? `(${meta.elapsed_seconds}s)` : '';
      dom.auditMetaSource.textContent = `📁 ${src} ${elapsed}`;
    }

    const total = kpis.total_tickets || incidents.length || 0;
    const terminal = kpis.terminales_omitidas_count || 0;
    const activas = total - terminal;
    const conIa = kpis.con_resumen_ia_count || 0;
    const completas = kpis.completas_count || 0;
    const parciales = kpis.parciales_count || 0;
    const incompletas = kpis.incompletas_count || 0;
    const disc = kpis.discrepancias_count || 0;

    if (dom.auditKpiTotal) dom.auditKpiTotal.textContent = total;
    if (dom.auditKpiSubTotal) dom.auditKpiSubTotal.textContent = `${activas} activas en triaje · ${terminal} terminales descartadas`;

    const iaPercent = activas > 0 ? Math.round((conIa / activas) * 100) : 0;
    if (dom.auditKpiIa) dom.auditKpiIa.textContent = `${conIa} / ${activas}`;
    if (dom.auditKpiSubIa) dom.auditKpiSubIa.textContent = `${iaPercent}% Cobertura Activas`;

    if (dom.auditKpiCompletas) dom.auditKpiCompletas.textContent = completas;
    if (dom.auditKpiParciales) dom.auditKpiParciales.textContent = parciales;
    if (dom.auditKpiIncompletas) dom.auditKpiIncompletas.textContent = incompletas;
    if (dom.auditKpiDiscrepancias) dom.auditKpiDiscrepancias.textContent = disc;

    filterAndRenderAuditTickets();

    if (dom.auditLogTerminal) {
      const logs = data.log_tail || 'Sin trazas disponibles en ingestion_audit.log';
      dom.auditLogTerminal.textContent = logs;
      dom.auditLogTerminal.scrollTop = dom.auditLogTerminal.scrollHeight;
    }
  }

  function filterAndRenderAuditTickets() {
    if (!ingestionAuditData || !dom.auditTicketsTbody) return;
    const summary = ingestionAuditData.summary || {};
    const allIncidents = summary.incidents || [];

    const filterState = dom.auditFilterState ? dom.auditFilterState.value : 'active';
    const searchQuery = dom.auditFilterSearch ? dom.auditFilterSearch.value.trim().toLowerCase() : '';

    let filtered = allIncidents.filter(inc => {
      if (filterState === 'active' && inc.is_terminal) return false;
      if (filterState === 'COMPLETA' && inc.estado_informacion !== 'COMPLETA') return false;
      if (filterState === 'PARCIAL' && inc.estado_informacion !== 'PARCIAL') return false;
      if (filterState === 'INCOMPLETA' && inc.estado_informacion !== 'INCOMPLETA') return false;
      if (filterState === 'NO_APLICA' && !inc.is_terminal) return false;

      if (searchQuery) {
        const textToSearch = [
          inc.id || '',
          inc.titulo || '',
          inc.sistemas || '',
          inc.proceso_critico || '',
          inc.causa_global || '',
          (inc.resumen_ia && inc.resumen_ia.causa_falta) || '',
          (inc.mensajes_ejecutivos && inc.mensajes_ejecutivos.causa_falta) || ''
        ].join(' ').toLowerCase();
        if (!textToSearch.includes(searchQuery)) return false;
      }
      return true;
    });

    if (dom.auditTabTicketsCount) {
      dom.auditTabTicketsCount.textContent = filtered.length;
    }

    if (filtered.length === 0) {
      dom.auditTicketsTbody.innerHTML = `
        <tr>
          <td colspan="9" style="text-align: center; padding: 24px; color: var(--triage-text-muted);">
            No se encontraron incidencias con los filtros aplicados.
          </td>
        </tr>
      `;
      return;
    }

    const rowsHtml = filtered.map(inc => {
      const isTerminal = inc.is_terminal;
      const estadoInfo = inc.estado_informacion || (isTerminal ? 'NO_APLICA' : 'INCOMPLETA');
      
      let badgeClass = 'audit-badge-terminal';
      if (estadoInfo === 'COMPLETA') badgeClass = 'audit-badge-completa';
      else if (estadoInfo === 'PARCIAL') badgeClass = 'audit-badge-parcial';
      else if (estadoInfo === 'INCOMPLETA') badgeClass = 'audit-badge-incompleta';

      const hasIa = inc.resumen_ia && inc.resumen_ia.disponible;
      const iaOrigin = hasIa ? (inc.resumen_ia.origen || 'Epsilon') : 'No disponible';
      const iaBadgeClass = hasIa ? 'audit-badge-ia-ok' : 'audit-badge-ia-fail';

      const hasComms = inc.mensajes_ejecutivos && inc.mensajes_ejecutivos.disponible;
      const commsFases = hasComms ? (inc.mensajes_ejecutivos.fases_aprobadas || []).join(', ') : 'Pendiente';

      const discMotivo = inc.es_discrepancia ? `⚠️ ${inc.prioridad_nominal} ➔ ${inc.prioridad_sugerida}` : (inc.prioridad_sugerida || inc.prioridad_nominal || '-');

      const causaFalta = inc.causa_global || (isTerminal ? `Omitido por estado final (${inc.estatus})` : 'Información completa');

      const retryBtn = (!isTerminal) ? `
        <button class="btn-ticket-retry-ia" data-inc-id="${escapeHtml(inc.id)}" title="Forzar consulta de Resumen IA en Epsilon">
          ⚡ IA
        </button>
      ` : `<span style="color: #94a3b8; font-size: 11px;">-</span>`;

      return `
        <tr>
          <td><strong style="color: #0284C7; font-family: var(--font-mono);">${escapeHtml(inc.id)}</strong></td>
          <td title="${escapeHtml(inc.titulo || '')}">
            <div style="max-width: 280px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 600;">
              ${escapeHtml(inc.titulo || 'Sin descripción')}
            </div>
            <div style="font-size: 10.5px; color: #64748B;">${escapeHtml(inc.sistemas || inc.proceso_critico || 'General')}</div>
          </td>
          <td><span style="font-size: 11.5px;">${escapeHtml(inc.estatus || 'Asignado')}</span></td>
          <td><span style="font-size: 11px; font-weight: 700; ${inc.es_discrepancia ? 'color: #7C3AED;' : ''}">${escapeHtml(discMotivo)}</span></td>
          <td><span class="audit-badge ${badgeClass}">${escapeHtml(estadoInfo)}</span></td>
          <td>
            <span class="audit-badge ${iaBadgeClass}">
              ${hasIa ? '🤖 ' + escapeHtml(iaOrigin) : '❌ Falta IA'}
            </span>
          </td>
          <td>
            <span style="font-size: 11px; ${hasComms ? 'color: #059669; font-weight: 600;' : 'color: #94A3B8;'}">
              ${hasComms ? '📢 ' + escapeHtml(commsFases) : '⏳ Sin redactar'}
            </span>
          </td>
          <td style="font-size: 11px; color: ${isTerminal ? '#64748B' : (estadoInfo === 'COMPLETA' ? '#059669' : '#DC2626')};">
            ${escapeHtml(causaFalta)}
          </td>
          <td style="text-align: center;">
            ${retryBtn}
          </td>
        </tr>
      `;
    }).join('');

    dom.auditTicketsTbody.innerHTML = rowsHtml;
  }

  async function triggerEpsilonRetry(options = {}) {
    const { incidents = [], force = false, all = false } = options;

    if (dom.auditActionStatus) {
      dom.auditActionStatus.style.display = 'flex';
      dom.auditActionStatus.className = 'audit-action-status is-loading';
      const msg = all || force
        ? '⚡ Conectando con API corporativa de Epsilon y forzando refresco general de Resumen IA...'
        : incidents.length > 0
          ? `⚡ Consultando Resumen IA en Epsilon para ${incidents.join(', ')}...`
          : '🔄 Consultando Resumen IA para incidencias pendientes o con error...';
      dom.auditActionStatus.innerHTML = `<span class="audit-spinner">⚡</span> ${msg}`;
    }

    if (dom.btnAuditForceAll) dom.btnAuditForceAll.disabled = true;
    if (dom.btnAuditRetryMissing) dom.btnAuditRetryMissing.disabled = true;

    try {
      const resp = await fetch('/api/ingestion/retry-ia', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ incidents, force, all })
      });

      if (resp.status === 404) {
        const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
        const hint = isLocal
          ? 'Por favor, reinicia el servidor en tu terminal (Ctrl+C y "python serve_app.py") para activar los endpoints de reintento.'
          : 'El endpoint de reintento dinámico requiere ejecución backend. Puedes relanzarlo en el servidor con "python converters/cli/retry_epsilon_ia.py" o mediante una nueva carga CSV.';
        throw new Error(`Ruta /api/ingestion/retry-ia no encontrada (HTTP 404). ${hint}`);
      }

      const result = await resp.json();
      if (!resp.ok || !result.success) {
        throw new Error(result.error || result.message || 'Error en relanzamiento');
      }

      if (dom.auditActionStatus) {
        dom.auditActionStatus.className = 'audit-action-status is-success';
        dom.auditActionStatus.innerHTML = `✅ ${result.message}`;
      }

      showToast(`✅ ${result.message}`, 'success');

      await loadIngestionAuditData(false);
      if (typeof performInspection === 'function') {
        performInspection(false);
      }
    } catch (err) {
      console.error('Error relanzando Resumen IA:', err);
      if (dom.auditActionStatus) {
        dom.auditActionStatus.className = 'audit-action-status is-error';
        dom.auditActionStatus.innerHTML = `❌ Error en relanzamiento: ${err.message}`;
      }
      showToast(`❌ Error: ${err.message}`, 'error');
    } finally {
      if (dom.btnAuditForceAll) dom.btnAuditForceAll.disabled = false;
      if (dom.btnAuditRetryMissing) dom.btnAuditRetryMissing.disabled = false;
    }
  }

  function setupIngestionAuditListeners() {
    if (dom.btnModalAuditClose) {
      dom.btnModalAuditClose.addEventListener('click', closeIngestionAuditModal);
    }
    if (dom.btnModalAuditCloseBottom) {
      dom.btnModalAuditCloseBottom.addEventListener('click', closeIngestionAuditModal);
    }
    if (dom.btnAuditRefresh) {
      dom.btnAuditRefresh.addEventListener('click', () => loadIngestionAuditData(true));
    }
    if (dom.btnAuditForceAll) {
      dom.btnAuditForceAll.addEventListener('click', () => {
        if (confirm('¿Deseas forzar el refresco de Resumen IA en Epsilon para todas las incidencias activas ignorando la caché previa?')) {
          triggerEpsilonRetry({ all: true, force: true });
        }
      });
    }
    if (dom.btnAuditRetryMissing) {
      dom.btnAuditRetryMissing.addEventListener('click', () => {
        triggerEpsilonRetry({ force: false });
      });
    }
    if (dom.auditTabTickets && dom.auditTabLogs) {
      dom.auditTabTickets.addEventListener('click', () => {
        activeAuditTab = 'tickets';
        dom.auditTabTickets.classList.add('is-active');
        dom.auditTabTickets.setAttribute('aria-selected', 'true');
        dom.auditTabLogs.classList.remove('is-active');
        dom.auditTabLogs.setAttribute('aria-selected', 'false');
        if (dom.auditViewTickets) dom.auditViewTickets.style.display = 'block';
        if (dom.auditViewLogs) dom.auditViewLogs.style.display = 'none';
      });
      dom.auditTabLogs.addEventListener('click', () => {
        activeAuditTab = 'logs';
        dom.auditTabLogs.classList.add('is-active');
        dom.auditTabLogs.setAttribute('aria-selected', 'true');
        dom.auditTabTickets.classList.remove('is-active');
        dom.auditTabTickets.setAttribute('aria-selected', 'false');
        if (dom.auditViewLogs) {
          dom.auditViewLogs.style.display = 'block';
          if (dom.auditLogTerminal) dom.auditLogTerminal.scrollTop = dom.auditLogTerminal.scrollHeight;
        }
        if (dom.auditViewTickets) dom.auditViewTickets.style.display = 'none';
      });
    }
    if (dom.auditFilterSearch) {
      dom.auditFilterSearch.addEventListener('input', filterAndRenderAuditTickets);
    }
    if (dom.auditFilterState) {
      dom.auditFilterState.addEventListener('change', filterAndRenderAuditTickets);
    }
    if (dom.auditTicketsTbody) {
      dom.auditTicketsTbody.addEventListener('click', (e) => {
        const retryBtn = e.target.closest('.btn-ticket-retry-ia');
        if (retryBtn) {
          const incId = retryBtn.dataset.incId;
          if (incId) {
            triggerEpsilonRetry({ incidents: [incId], force: true });
          }
        }
      });
    }
    if (dom.btnAuditCopyLog) {
      dom.btnAuditCopyLog.addEventListener('click', () => {
        const text = dom.auditLogTerminal ? dom.auditLogTerminal.textContent : '';
        copyToClipboard(text, '¡Trazas de auditoría copiadas al portapapeles!');
      });
    }
    if (dom.btnAuditScrollLog) {
      dom.btnAuditScrollLog.addEventListener('click', () => {
        if (dom.auditLogTerminal) {
          dom.auditLogTerminal.scrollTop = dom.auditLogTerminal.scrollHeight;
        }
      });
    }
  }

  async function init() {
    await loadScheduledChangesPaP();
    setupGlobalListeners();
    setupIngestionAuditListeners();
    updateTabStyles();
    performInspection(false);
    resetAutoRefreshTimer();

    // Actualizar el reloj relativo de última inspección y alertas de pestaña/favicon cada segundo
    state.relativeTimer = setInterval(() => {
      updateRelativeTimeDisplay();
      updateBrowserTitleAndFavicon();
    }, 1000);

    document.addEventListener('visibilitychange', () => {
      updateBrowserTitleAndFavicon();
    });
  }

  // Disparar al cargar DOM
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
