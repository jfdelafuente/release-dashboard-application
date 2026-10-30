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
    clocksTicker: null, // Timer de actualización de relojes
    defaultIncidentManager: 'Carlos Morales · Incident Manager de Guardia (Turno Activo CSO)'
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

    // Relojes de Escalado
    clock20mCard: document.getElementById('orch-clock-20m'),
    clock20mTimer: document.getElementById('clock-20m-timer'),
    clock20mFill: document.getElementById('clock-20m-fill'),
    clock20mStatusText: document.getElementById('clock-20m-status-text'),
    btnAction20m: document.getElementById('btn-action-20m'),

    clock45mCard: document.getElementById('orch-clock-45m'),
    clock45mTimer: document.getElementById('clock-45m-timer'),
    clock45mFill: document.getElementById('clock-45m-fill'),
    clock45mStatusText: document.getElementById('clock-45m-status-text'),
    btnAction45m: document.getElementById('btn-action-45m'),

    clock105mCard: document.getElementById('orch-clock-105m'),
    clock105mTimer: document.getElementById('clock-105m-timer'),
    clock105mFill: document.getElementById('clock-105m-fill'),
    clock105mStatusText: document.getElementById('clock-105m-status-text'),
    btnAction105m: document.getElementById('btn-action-105m'),

    clock120mCard: document.getElementById('orch-clock-120m'),
    clock120mTimer: document.getElementById('clock-120m-timer'),
    clock120mFill: document.getElementById('clock-120m-fill'),
    clock120mStatusText: document.getElementById('clock-120m-status-text'),
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
    btnCopyExecCompleto: document.getElementById('btn-copy-exec-completo')
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

    // Contadores de pestañas de filtrado
    const totalCount = state.incidents.length;
    const correctCount = totalCount - discCount;
    if (dom.countAll) dom.countAll.textContent = totalCount;
    if (dom.countReclass) dom.countReclass.textContent = discCount;
    if (dom.countCorrect) dom.countCorrect.textContent = correctCount;
    if (dom.countOrchestrator) dom.countOrchestrator.textContent = p1Count;

    // Renderizar Feed de Triaje (Vista Tabular con Filas Plegables)
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
    // Fallback integrado si no se alcanza el archivo por la red
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
        contacto_guardia: 'Guardia CRM Frontales (+34 91 222 3401)'
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
        contacto_guardia: 'Guardia BFF Digital (+34 91 222 3402)'
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
        contacto_guardia: 'Guardia Middleware TIBCO (+34 91 222 3403)'
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
        contacto_guardia: 'Guardia Apigee (+34 91 222 3404)'
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
        contacto_guardia: 'Guardia Facturación/Mediación (+34 91 222 3405)'
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
          text: `Coincidencia detectada con cambio reciente ${pap.crq}: "${pap.titulo}". Procedimiento de Rollback verificado disponible (${pap.tiempo_rollback_estimado}).`,
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

      dom.orchPapContainer.innerHTML = `
        <div class="orch-pap-alert-card">
          <div class="orch-pap-top-alert">
            <span aria-hidden="true">⚠️</span>
            <span>Trabajo Programado (PaP) reciente coincide con los sistemas afectados:</span>
          </div>
          <div class="orch-pap-details-grid">
            <div class="orch-pap-field">
              <strong>Código de Cambio</strong>
              <span>${escapeHtml(pap.crq)}</span>
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
    const orderText = `⏪ ORDEN FORMAL DE ROLLBACK INMEDIATO (IM-CSO) ⏪
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Ordenante: ${imName}
Motivo: Indisponibilidad crítica ${incId} tras despliegue de cambio.
Código de Cambio (PaP): ${pap.crq}
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

  function openExecutiveCommModal(incId) {
    const inc = state.incidents.find(i => i.id === incId);
    if (!inc || !dom.modalExecutiveComm) return;

    // Buscar si ya existen mensajes redactados
    const msgs = inc.mensajes_ejecutivos || {};
    const evaluacion = inc.evaluacion || {};
    const proceso = evaluacion.proceso || evaluacion.proceso_negocio || 'Atención al Cliente (ATC)';
    const sistemas = Array.isArray(inc.sistemas) ? inc.sistemas.join(', ') : (inc.sistemas || 'Sistemas Core');

    let completo = msgs.apertura?.completo || msgs.completo;
    let breve = msgs.apertura?.breve || msgs.breve;

    if (!completo) {
      completo = `Incidencia crítica ${incId} en ${sistemas} impactando ${proceso}. Umbral superado: ${evaluacion.criterio || 'Regla de Oro N1'}. Resolutores N2/N3 convocados en War Room con IM-CSO. Foco en mitigación inmediata y diagnóstico. Próxima actualización en 60 minutos.`;
    }
    if (!breve) {
      breve = `SL1 ${incId} en ${sistemas} (${proceso}). War Room activa con IM-CSO. Restablecimiento en curso.`;
    }

    if (dom.execCommCompleto) dom.execCommCompleto.textContent = completo;
    if (dom.execCommBreve) dom.execCommBreve.textContent = breve;

    dom.modalExecutiveComm.classList.add('open');

    if (dom.btnCopyExecBreve) {
      dom.btnCopyExecBreve.onclick = () => {
        copyToClipboard(breve, 'Versión breve copiada al portapapeles');
      };
    }

    if (dom.btnCopyExecCompleto) {
      dom.btnCopyExecCompleto.onclick = () => {
        copyToClipboard(completo, 'Versión completa copiada para difusión a Dirección');
        const escState = state.orchestratorEscalations[incId] || {};
        escState.commDone = true;
        state.orchestratorEscalations[incId] = escState;
        try {
          localStorage.setItem('emergency_esc_' + incId, JSON.stringify(escState));
        } catch (_) {}
        addLogEntry(
          incId,
          'NOTIFICACION',
          '📝 Notificación Ejecutiva',
          `1ª Comunicación oficial a Dirección emitida y registrada (SLA <20m).`,
          'role-notificacion'
        );
        updateOrchestratorClocks();
        dom.modalExecutiveComm.classList.remove('open');
        showToast('1ª Comunicación registrada en bitácora', 'success');
      };
    }

    if (dom.btnModalExecClose) {
      dom.btnModalExecClose.onclick = () => {
        dom.modalExecutiveComm.classList.remove('open');
      };
    }
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
    const elapsedSeconds = Math.max(0, Math.floor(baseMinutes * 60) + Math.floor((Date.now() - (state.lastInspectionEpoch || Date.now())) / 1000));
    const elapsedMinutes = Math.floor(elapsedSeconds / 60);

    if (dom.orchAgingTag) {
      dom.orchAgingTag.textContent = `⏱️ ${formatAgingMinutes(elapsedMinutes)}`;
    }

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
        dom.clock20mStatusText.textContent = '🚨 SLA 20m Excedido';
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
          dom.clock20mStatusText.textContent = 'Cuenta atrás SLA';
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

    // 5. Iniciar Relojes de Escalado
    startOrchestratorClocks(inc);

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
    if (dom.modalOrchestrator) {
      dom.modalOrchestrator.classList.remove('open');
    }
  }

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
  // Función 2: Filtrado y Renderizado en Modo Tabular con Filas Plegables
  // --------------------------------------------------------------------------

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
        return idMatch || titleMatch || sysMatch || procMatch || critMatch || impactMatch;
      });
    }

    return filtered;
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
              <th style="width: 44px; text-align: center;" aria-label="Desplegable"></th>
              <th style="width: 140px;">Incidencia</th>
              <th style="min-width: 280px;">Título y Sistemas</th>
              <th style="width: 170px;">Proceso Crítico</th>
              <th style="width: 110px;">Remedy Ini</th>
              <th style="width: 120px;">Severidad ITIL</th>
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
    const itilBadgeClass = isP1 ? 'badge-itil-sl1' : 'badge-itil-sl2';
    const itilLabel = isP1 ? 'SL1 / P1' : 'SL2 / P2';

    // Epsilon IA resumen
    const resumenIa = inc.resumen_ia || {};
    const epsilonBloqueos = Array.isArray(resumenIa.bloqueos) ? resumenIa.bloqueos.join('; ') : (resumenIa.bloqueos || '');

    return `
      <!-- Fila Resumen Principal (Modo Tabular) -->
      <tr class="triage-row-main ${rowModifier} ${isOpen ? 'is-expanded' : ''}" data-inc="${escapeHtml(incId)}" role="button" tabindex="0" aria-expanded="${isOpen}">
        <td style="text-align: center; width: 44px;">
          <button type="button" class="triage-chevron-btn ${isOpen ? 'is-expanded' : ''}" data-inc="${escapeHtml(incId)}" aria-label="${isOpen ? 'Plegar detalle' : 'Desplegar detalle'}">
            <span aria-hidden="true">▶</span>
          </button>
        </td>
        <td class="triage-cell-id">
          <span class="triage-id-link" data-inc="${escapeHtml(incId)}" title="Ver ficha técnica Epsilon IA">${escapeHtml(incId)}</span>
          <div class="triage-id-meta">
            <span class="triage-status-pill ${statusPillClass}">${escapeHtml(inc.estatus || 'Pendiente')}</span>
            <span style="font-family: var(--font-mono); font-size: 11px; color: var(--triage-text-subtle);" title="Tiempo transcurrido desde apertura">⏱️ ${formatAgingMinutes(minsElapsed)}</span>
          </div>
        </td>
        <td class="triage-cell-title">
          <div class="triage-title-text">${escapeHtml(inc.titulo || 'Sin título')}</div>
          <div class="triage-systems-tags">
            ${sysTagsHtml || '<span class="triage-sys-tag">Sistemas Core</span>'}
          </div>
        </td>
        <td class="triage-cell-process">
          <span class="triage-process-badge" style="font-size: 11.5px; padding: 4px 8px;">
            <span aria-hidden="true">🏢</span> ${escapeHtml(proceso)}
          </span>
        </td>
        <td>
          <span class="triage-sev-badge ${remedyBadgeClass}">${escapeHtml(sevNominal)}</span>
        </td>
        <td>
          <span class="triage-sev-badge ${itilBadgeClass}">${itilLabel}</span>
        </td>
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
        <td colspan="7">
          <div class="triage-detail-wrapper">
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
                      <span class="triage-sev-badge ${itilBadgeClass}">${isP1 ? 'SL1 / P1 (Emergencia Crítica)' : 'SL2 / P2 (Mayor)'}</span>
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
                      <span class="triage-epsilon-val">${escapeHtml(resumenIa.siguiente_accion || epsilonBloqueos || 'Coordinación con soporte resolutor.')}</span>
                    </div>
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

    // Modal Notificación Ejecutiva (Módulo 2)
    if (dom.modalExecutiveComm) {
      dom.modalExecutiveComm.addEventListener('click', (e) => {
        if (e.target === dom.modalExecutiveComm) dom.modalExecutiveComm.classList.remove('open');
      });
    }

    // Escape universal para cerrar cualquier modal abierto
    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
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
      }
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

    if (dom.btnClearLog) {
      dom.btnClearLog.addEventListener('click', () => {
        if (!state.activeOrchIncId) return;
        if (confirm(`¿Deseas reiniciar la bitácora operativa de ${state.activeOrchIncId}? Se restaurarán los hitos iniciales de activación.`)) {
          const inc = state.incidents.find(i => i.id === state.activeOrchIncId);
          localStorage.removeItem('emergency_log_' + state.activeOrchIncId);
          delete state.orchestratorLogs[state.activeOrchIncId];
          getOrInitLog(state.activeOrchIncId, inc);
          renderTimelineEntries(state.activeOrchIncId);
          showToast('Bitácora reiniciada con éxito', 'info');
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

  async function init() {
    await loadScheduledChangesPaP();
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
