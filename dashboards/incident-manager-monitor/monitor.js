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

  // --- Constantes Oficiales de Emergencias Orange (Feature 014) ---
  const CRITICAL_PROCESSES = {
    ATC: {
      name: 'Atención al Cliente (ATC)',
      thresholds: [
        'Frontales/CRM con desviación >20% en 30m',
        'Caída total IVR / canal de atención',
        '>20% llamadas abandonadas en 1h'
      ]
    },
    SALES: {
      name: 'Ventas y Canales',
      thresholds: [
        'Impacto >30% volumen comercial',
        '<15% ventas diarias respecto a media de 4 días'
      ]
    },
    PORTABILITY: {
      name: 'Portabilidad',
      thresholds: [
        'Fallo en ventana de cambio 02:00 AM',
        'Retraso >2h en horario comercial (08:00 - 20:00)'
      ]
    },
    PREPAID: {
      name: 'Prepago',
      thresholds: [
        '>10% errores en recargas / altas',
        '>30 min sin transacciones operativas'
      ]
    },
    PROVISIONING: {
      name: 'Provisión y Activación',
      thresholds: [
        'Móvil: >20% pedidos con error (>10m 100% error)',
        'Fijo: >30% pedidos con error (>30m 100% error)'
      ]
    },
    BILLING: {
      name: 'Facturación y Cobros',
      thresholds: [
        'Ventana crítica ciclo +/- 3 días',
        '>3h sin tarificación online',
        'Retraso batch >1 día'
      ]
    }
  };

  const ESCALATION_THRESHOLDS = {
    FIRST_NOTIFICATION_MAX_MIN: 20,
    FIRST_ESCALATION_MIN: 45,
    SECOND_ESCALATION_MIN: 105,
    SL1_UPDATE_FREQ_MIN: 30,
    SL2_UPDATE_FREQ_MIN: 60
  };

  /**
   * Parsea cadenas de fecha Remedy (DD/MM/YYYY HH:mm o ISO) a timestamp epoch UTC en milisegundos.
   * Evita desfases horarios y soporta anotaciones 'a'/'p' de exportaciones de Remedy en español.
   */
  function parseRemedyDateToEpochMs(dateStr) {
    if (!dateStr || typeof dateStr !== 'string') return null;
    const cleanStr = dateStr.trim();
    if (!cleanStr) return null;

    if (cleanStr.includes('T') || cleanStr.startsWith('20')) {
      const parsed = Date.parse(cleanStr);
      if (!isNaN(parsed)) return parsed;
    }

    const match = cleanStr.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})\s+(\d{1,2}):(\d{2})(?::(\d{2}))?(?:\s*([ap])\.?m?\.?)?$/i);
    if (match) {
      const day = parseInt(match[1], 10);
      const month = parseInt(match[2], 10) - 1;
      const year = parseInt(match[3], 10);
      let hours = parseInt(match[4], 10);
      const minutes = parseInt(match[5], 10);
      const seconds = match[6] ? parseInt(match[6], 10) : 0;
      const meridiem = match[7] ? match[7].toLowerCase() : null;

      if (meridiem) {
        if (meridiem === 'p' && hours < 12) {
          hours += 12;
        } else if (meridiem === 'a' && hours === 12) {
          hours = 0;
        }
      }

      const epoch = Date.UTC(year, month, day, hours, minutes, seconds);
      if (!isNaN(epoch)) return epoch;
    }

    const fallback = Date.parse(cleanStr);
    return isNaN(fallback) ? null : fallback;
  }

  // --- Gestor de Persistencia de Estado Operativo (Ciclo de Vida: Pendiente, Comunicada, En Seguimiento, Descartada) ---
  const STORAGE_KEY = 'hp_incident_notifications_state_v1';

  const StateManager = {
    getAll() {
      try {
        const raw = localStorage.getItem(STORAGE_KEY);
        return raw ? JSON.parse(raw) : {};
      } catch (e) {
        console.warn('[IncidentManagerMonitor] Error leyendo localStorage:', e);
        return {};
      }
    },

    getStatus(id, inc) {
      const all = this.getAll();
      if (all[id] && all[id].status) {
        return all[id].status;
      }
      // Heurística de arranque si no hay estado manual guardado:
      // Si ya tiene Apertura oficial aprobada en almacén oficial y no tiene alertas de escalado ni discrepancias
      if (inc && inc.mensajes_ejecutivos?.apertura?.generado_por_agente && !inc.is_redaction_pending) {
        const mins = inc.minutos_desde_apertura || inc.evaluacion?.minutos_desde_apertura || 0;
        const disc = Boolean(inc.es_discrepancia || inc.discrepancia?.es_discrepancia);
        if (mins < 45 && !disc) {
          return 'comunicada';
        }
      }
      return 'pendiente';
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
        console.warn('[IncidentManagerMonitor] Error escribiendo localStorage:', e);
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
        console.warn('[IncidentManagerMonitor] Error guardando custom message:', e);
      }
    }
  };

  function getOperationalStatusLabel(status) {
    switch (status) {
      case 'comunicada':
        return '📣 Comunicada';
      case 'en_seguimiento':
        return '🔍 En Seguimiento';
      case 'descartada':
        return '⚪ Descartada';
      case 'pendiente':
      default:
        return '🟡 Pendiente';
    }
  }

  // --- Estado de la Aplicación ---
  const state = {
    kpis: {
      total_active: 0,
      completed_count: 0,
      pending_count: 0,
      p1_count: 0,
      p2_count: 0,
      discrepancies_count: 0,
      discrepancies_sl1: 0,
      discrepancies_sl2: 0,
      escalation_alerts_count: 0,
      workarounds_pending_cso_count: 0,
      generated_at: '',
      source_file: ''
    },
    pendingIncidents: [],
    completedIncidents: [],
    allIncidents: [],
    activeView: 'pending', // 'pending' | 'all'
    viewMode: 'emergency', // 'emergency' | 'compact'
    presentationMode: 'triage', // 'triage' (default) | 'cards'
    triageFilter: 'urgent', // 'urgent' (default) | 'pending' | 'escalation' | 'discrepancy' | 'all'
    filters: {
      severity: 'all',
      process: 'all',
      commPhase: 'all',
      onlyDiscrepancies: false,
      search: ''
    },
    // Guarda la fase seleccionada por cada incidencia { [incId]: 'apertura' | 'seguimiento' | 'cierre' }
    activePhases: {},
    // Textos temporales ingresados en el asistente de ingesta { [incId]: { completo: '', breve: '' } }
    ingestaDrafts: {},
    // Estado de visibilidad de los reportes por incidencia { [incId]: boolean }
    reportVisibility: {},
    refreshIntervalMs: 30000,
    refreshTimer: null,
    searchDebounceTimer: null,
    liveTimerInterval: null
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
    kpiCardCompleted: document.getElementById('kpi-card-completed'),
    kpiCompletedCount: document.getElementById('kpi-completed-count'),
    kpiCardTotal: document.getElementById('kpi-card-total'),
    kpiTotalActive: document.getElementById('kpi-total-active'),
    kpiSourceFile: document.getElementById('kpi-source-file'),
    kpiCardSeverity: document.getElementById('kpi-card-severity'),
    kpiP1Count: document.getElementById('kpi-p1-count'),
    kpiP2Count: document.getElementById('kpi-p2-count'),
    kpiCardDiscrepancies: document.getElementById('kpi-card-discrepancies'),
    kpiDiscrepanciesCount: document.getElementById('kpi-discrepancies-count'),
    kpiDiscrepanciesSl1: document.getElementById('kpi-discrepancies-sl1'),
    kpiDiscrepanciesSl2: document.getElementById('kpi-discrepancies-sl2'),
    kpiCardEscalation: document.getElementById('kpi-card-escalation'),
    kpiEscalationAlertsCount: document.getElementById('kpi-escalation-alerts-count'),
    kpiCardWorkarounds: document.getElementById('kpi-card-workarounds'),
    kpiWorkaroundsPendingCount: document.getElementById('kpi-workarounds-pending-count'),

    // Modos Principales y Triaje (De un Vistazo)
    tabPresTriage: document.getElementById('tab-pres-triage'),
    tabPresCards: document.getElementById('tab-pres-cards'),
    triageViewContainer: document.getElementById('triage-view-container'),
    triageTableBody: document.getElementById('triage-table-body'),
    triageEmptyState: document.getElementById('triage-empty-state'),
    cardsNavBar: document.getElementById('cards-nav-bar'),
    btnBackToTriage: document.getElementById('btn-back-to-triage'),

    // Chips de Triaje
    chipUrgent: document.getElementById('chip-urgent'),
    chipPending: document.getElementById('chip-pending'),
    chipEscalation: document.getElementById('chip-escalation'),
    chipDiscrepancy: document.getElementById('chip-discrepancy'),
    chipMissingComm: document.getElementById('chip-missing-comm'),
    chipAll: document.getElementById('chip-all'),
    chipCountUrgent: document.getElementById('chip-count-urgent'),
    chipCountPending: document.getElementById('chip-count-pending'),
    chipCountEscalation: document.getElementById('chip-count-escalation'),
    chipCountDiscrepancy: document.getElementById('chip-count-discrepancy'),
    chipCountMissingComm: document.getElementById('chip-count-missing-comm'),
    chipCountAll: document.getElementById('chip-count-all'),

    // Tabs, Badges y Modos
    tabViewPending: document.getElementById('tab-view-pending'),
    tabViewAll: document.getElementById('tab-view-all'),
    badgeCountPending: document.getElementById('badge-count-pending'),
    badgeCountAll: document.getElementById('badge-count-all'),
    btnToggleEmergencyMode: document.getElementById('btn-toggle-emergency-mode'),
    toggleEmergencyModeLabel: document.getElementById('toggle-emergency-mode-label'),

    // Modal RACI
    btnOpenRaci: document.getElementById('btn-open-raci'),
    raciModalBackdrop: document.getElementById('raci-modal-backdrop'),
    btnCloseRaci: document.getElementById('btn-close-raci'),

    // Filtros
    filterSearchInput: document.getElementById('filter-search-input'),
    filterSeveritySelect: document.getElementById('filter-severity-select'),
    filterProcessSelect: document.getElementById('filter-process-select'),
    filterCommSelect: document.getElementById('filter-comm-select'),
    filterOnlyDiscrepancies: document.getElementById('filter-only-discrepancies'),
    btnResetFilters: document.getElementById('btn-reset-filters'),

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

  // --- Utilidades de Cronometraje y Emergencias (Feature 014) ---

  function formatTimerString(mins) {
    if (mins < 60) {
      return `${mins} min`;
    }
    const h = Math.floor(mins / 60);
    const m = mins % 60;
    return `${h}h ${m}m`;
  }

  function generate4BlockEmergencyReport(inc, minsElapsed) {
    if (inc.reporte_emergencia) {
      return inc.reporte_emergencia;
    }
    const incId = inc.id || 'INC000000000000';
    const isP1 = inc.prioridad_sugerida === 'P1';
    const sevItil = isP1 ? 'SL1 / P1 - Emergencia Crítica' : 'SL2 / P2 - Mayor';
    const evaluacion = inc.evaluacion || {};
    const proceso = inc.discrepancia?.proceso_critico || evaluacion.proceso || 'Sistemas Core';
    const criterio = inc.discrepancia?.criterio_umbral || evaluacion.criterio || 'Regla de Oro N1';
    const sistemas = (inc.sistemas && inc.sistemas.length > 0)
      ? (Array.isArray(inc.sistemas) ? inc.sistemas.join(', ') : inc.sistemas)
      : 'Sistemas Core';
    const justificacion = evaluacion.impacto_justificacion || criterio || 'Afectación en proceso crítico.';
    const slaVencido = minsElapsed >= 20;
    const reqTel = isP1 || !!inc.timeline?.requiere_canal_telefonico || !!evaluacion.requiere_escalado_telefonico;
    const rawWa = evaluacion.workaround || 'No';
    const estadoGob = inc.workaround?.estado_gobernanza || (rawWa && !['no', 'desconocido'].includes(rawWa.toLowerCase()) ? 'PENDIENTE_AUTORIZACION_CSO' : 'SIN_WORKAROUND');

    let faseEsc = 'NORMAL';
    if (minsElapsed >= 105) faseEsc = 'ESCALADO_SUPERIOR_REQUERIDO';
    else if (minsElapsed >= 45) faseEsc = 'ESCALADO_45M_REQUERIDO';

    return [
      '🚨 REPORTE DE EMERGENCIA IT - ORANGE TECH OPERATIONS',
      '────────────────────────────────────────────────────────────',
      '[1] CLASIFICACIÓN DEL TICKET',
      `• Incidencia: ${incId} (${sevItil})`,
      `• Proceso Crítico: ${proceso}`,
      `• Umbral de Emergencia: ${criterio}`,
      `• Alcance y Sistemas: ${sistemas}`,
      `• Impacto: ${evaluacion.impacto || 'Alto'} (${justificacion})`,
      `• Urgencia: ${evaluacion.urgencia || 'Media'}`,
      '',
      '[2] ESTADO DE COMUNICACIONES Y SLAS',
      `• Tiempo desde Apertura: ${minsElapsed} min`,
      `• 1ª Notificación a Dirección: ${slaVencido ? '⚠️ SLA Vencido' : '✅ En SLA'}`,
      `• Frecuencia de Actualizaciones: Cada ${isP1 ? '30' : '60'} min`,
      '• War Room / Teams: Liderado por Incident Manager (IM)',
      '',
      '[3] PLAN DE ACCIÓN Y GOBERNANZA DE WORKAROUNDS',
      `• Diagnóstico Técnico: ${inc.titulo || 'En curso'}`,
      `• Workaround: ${rawWa} | Gobernanza: ${estadoGob}`,
      '• Regla de Oro: Prohibida la desescalada automática sin erradicación total del impacto',
      '',
      '[4] ESTADO DE ESCALADO TELEFÓNICO',
      `• Protocolo de Tiempos: ${faseEsc} (${minsElapsed} min)`,
      `• Canal de Escalado: ${reqTel ? 'Vía Telefónica obligatoria (Regla de Oro)' : 'Canal estándar'}`,
      '• Gobernanza RACI: Incident Manager (R) / Customer & Service Ops IM-CSO (A)',
      '────────────────────────────────────────────────────────────'
    ].join('\n');
  }

  /**
   * Genera texto formal para el registro/worklog de Remedy solicitando la reclasificación
   * de prioridad nominal a P1/P2 con base en la matriz ITIL y procesos críticos de Orange.
   */
  function buildRemedyReclassificationText(inc) {
    if (!inc) return '';
    const incId = inc.id || 'INC000000000000';
    const prioOrig = inc.prioridad_original || inc.discrepancia?.prioridad_remedy || 'P3';
    const prioSug = inc.prioridad_sugerida || 'P2';
    const sevLabel = prioSug === 'P1' ? 'P1 / SL1 (Emergencia Crítica)' : 'P2 / SL2 (Incidencia Mayor)';
    const evaluacion = inc.evaluacion || {};
    const proceso = evaluacion.proceso || inc.discrepancia?.proceso_critico || 'Sistemas Core';
    const criterio = evaluacion.criterio || inc.discrepancia?.criterio_umbral || 'Regla de Oro N1';
    const sistemasStr = (inc.sistemas && inc.sistemas.length > 0) ? inc.sistemas.join(', ') : 'No especificado';
    const titulo = inc.titulo || 'Sin título registrado';

    return `[SOLICITUD URGENTE DE RECLASIFICACIÓN REMEDY - CRITERIO ITIL ORANGE]
────────────────────────────────────────────────────────────────────
Incidencia Remedy: ${incId}
Prioridad Actual Remedy: ${prioOrig} (Nominal / Subescalada)
Prioridad Solicitada: ${sevLabel}

DATOS DE IMPACTO Y PROCESO CRÍTICO:
• Proceso Crítico Afectado: ${proceso}
• Umbral Operativo Superado: ${criterio}
• Sistemas Comprometidos: ${sistemasStr}
• Afectación / Título: ${titulo}

JUSTIFICACIÓN OPERATIVA (GOBERNANZA DE EMERGENCIAS IT):
Conforme a la matriz oficial de criticidad IT de Orange y la Regla de Oro de Triaje N1, esta incidencia supera los umbrales de impacto en clientes y procesos críticos de negocio, por lo que su gestión debe elevarse inmediatamente a ${prioSug}.
Se solicita al grupo resolutor asignar la severidad ${prioSug} en Remedy y aplicar los tiempos de resolución y escalado telefónico estipulados por PROCESO OPERATIVO GESTIÓN EMERGENCIAS IT ORANGE .
────────────────────────────────────────────────────────────────────`;
  }

  /**
   * Genera el mensaje estructurado de convocatoria para War Room de audio en Teams,
   * cumpliendo con los umbrales de escalado (45m / 105m) y gobernanza RACI de Orange.
   */
  function buildTeamsWarRoomText(inc, minsElapsed) {
    if (!inc) return '';
    const incId = inc.id || 'INC000000000000';
    const prioSug = inc.prioridad_sugerida || 'P2';
    const sevLabel = prioSug === 'P1' ? 'P1 / SL1 (Emergencia Crítica)' : 'P2 / SL2 (Incidencia Mayor)';
    const evaluacion = inc.evaluacion || {};
    const proceso = evaluacion.proceso || inc.discrepancia?.proceso_critico || 'Sistemas Core';
    const sistemasStr = (inc.sistemas && inc.sistemas.length > 0) ? inc.sistemas.join(', ') : 'Sistemas Core';
    const titulo = inc.titulo || 'Sin título registrado';

    const mins = (minsElapsed !== undefined && minsElapsed !== null)
      ? minsElapsed
      : (inc.apertura_epoch_ms ? Math.max(0, Math.floor((Date.now() - inc.apertura_epoch_ms) / 60000)) : (inc.minutos_desde_apertura || 0));

    const is105 = mins >= 105;
    const umbralTexto = is105 ? '≥105 min (2º Escalado Estamentos Superiores +1h)' : '≥45 min (1er Escalado Telefónico Resolutores)';
    const grupoConvocado = is105
      ? 'Resolutores N2/N3 + Dirección de Operaciones + Customer & Service Ops (IM-CSO)'
      : 'Equipos Resolutores N2/N3 y Responsables de Servicio';

    return `🚨 [CONVOCATORIA URGENTE WAR ROOM AUDIO - ORANGE IT]
──────────────────────────────────────────────────────
Incidencia: ${incId} | Severidad: ${sevLabel}
Tiempo Transcurrido: ${formatTimerString(mins)} (${umbralTexto})
Proceso Crítico: ${proceso}
Sistemas: ${sistemasStr}
Afectación: ${titulo}

MODO DE COMUNICACIÓN OBLIGATORIO:
📞 Convocatoria obligatoria por canal de AUDIO / Teams (Regla de Oro Orange IT)
Convocados: ${grupoConvocado}
Gobernanza RACI: Incident Manager (R - Responsable) | IM-CSO (A - Aprobador)

OBJETIVO DE LA SESIÓN:
1. Sincronización inmediata entre grupos de soporte y resolutores.
2. Identificación de causa raíz o definición de workaround viable (bloqueo de desescalada activo).
3. Establecer plan de acción técnico y frecuencia de comunicación ejecutiva.

Por favor, unirse de inmediato al canal de audio de emergencias IT.
──────────────────────────────────────────────────────`;
  }

  /**
   * Genera un borrador IA oficial para la fase indicada (apertura, seguimiento, cierre),
   * garantizando el cumplimiento estricto de las reglas de Orange:
   * - Versión Completa: máximo 90 palabras en un ÚNICO párrafo cohesionado.
   * - Versión Breve: máximo 30 palabras.
   * - Sin alucinaciones de causas raíz ni datos ausentes.
   */
  function generateAiDraftForIncident(inc, phase) {
    if (!inc) return { completo: '', breve: '' };
    const incId = inc.id || 'INC000000000000';
    const prioSug = inc.prioridad_sugerida || 'P2';
    const sevLabel = prioSug === 'P1' ? 'crítica P1' : 'mayor P2';
    const evaluacion = inc.evaluacion || {};
    const proceso = evaluacion.proceso || inc.discrepancia?.proceso_critico || 'Sistemas Core';
    const criterio = evaluacion.criterio || inc.discrepancia?.criterio_umbral || 'criterio ITIL Orange';
    const sistemasStr = (inc.sistemas && inc.sistemas.length > 0) ? inc.sistemas.join(', ') : 'los sistemas corporativos';
    const rawTitulo = inc.titulo ? inc.titulo.trim().replace(/\.$/, '') : 'afectación en el servicio';
    const titulo = rawTitulo.length > 120 ? (rawTitulo.slice(0, 117) + '...') : rawTitulo;

    // 1. Si ya existe redacción oficial aprobada en almacén o guardada por el usuario
    const customMsg = StateManager.getCustomMessage(incId, phase);
    if (customMsg && customMsg.completo && customMsg.breve) {
      return { completo: customMsg.completo, breve: customMsg.breve };
    }
    const incMsg = inc.mensajes_ejecutivos && inc.mensajes_ejecutivos[phase];
    if (incMsg && incMsg.completo && incMsg.breve) {
      return { completo: incMsg.completo, breve: incMsg.breve };
    }

    // 2. Si no existe, generamos un borrador conforme a las reglas estrictas de Orange (<=90 / <=30 palabras)
    let comp = '';
    let brev = '';

    if (phase === 'apertura') {
      comp = `Se declara incidencia ${sevLabel} (${incId}) por ${titulo}. La anomalía impacta directamente en el proceso de ${proceso} superando el umbral operativo (${criterio}), afectando a ${sistemasStr}. Los equipos técnicos y grupos resolutores investigan el origen del fallo y aplican medidas inmediatas de mitigación para restablecer el servicio a la mayor brevedad. Próxima actualización en 30 minutos.`;
      brev = `Apertura ${prioSug} (${incId}): ${titulo}. Impacto en ${proceso} (${sistemasStr}). Equipos resolutores investigando medidas de mitigación.`;
    } else if (phase === 'seguimiento') {
      comp = `Seguimiento de la incidencia ${prioSug} (${incId}) en ${proceso}. Los grupos resolutores continúan analizando las trazas e integraciones en ${sistemasStr} sobre la afectación reportada (${titulo}). Se ejecutan acciones técnicas de contención operativa para estabilizar los componentes mientras se supervisa de forma continua el impacto en clientes. Próxima actualización en 30 minutos.`;
      brev = `Seguimiento ${prioSug} (${incId}): Diagnóstico y acciones de contención en curso sobre ${sistemasStr}. Servicio bajo monitorización continua de soporte.`;
    } else if (phase === 'cierre') {
      comp = `Queda resuelta la incidencia ${prioSug} (${incId}) que afectaba a ${proceso}. Tras las intervenciones técnicas de los grupos resolutores sobre ${sistemasStr}, se ha subsanado la anomalía (${titulo}) y el servicio opera con plena normalidad. Se confirma la total erradicación del impacto en clientes y se mantiene monitorización preventiva.`;
      brev = `Cierre ${prioSug} (${incId}): Restablecido el servicio en ${sistemasStr} tras resolución técnica. Impacto erradicado y operativa normalizada.`;
    } else {
      comp = `Comunicación oficial de la incidencia ${prioSug} (${incId}) sobre ${proceso} en ${sistemasStr}. Actuación técnica en curso.`;
      brev = `Alerta ${prioSug} (${incId}): Actuación técnica en curso sobre ${sistemasStr}.`;
    }

    return {
      completo: comp.trim(),
      breve: brev.trim()
    };
  }

  /**
   * Comprueba si una incidencia cuenta con comunicación oficial generada para la fase dada
   * ('apertura', 'seguimiento' o 'cierre'), verificando StateManager local y almacén oficial.
   */
  function hasOfficialMessage(inc, phase) {
    if (!inc) return false;
    const incId = inc.id || '';

    // 1. Mensaje guardado localmente en StateManager (edición u homologación de operador)
    const custom = StateManager.getCustomMessage(incId, phase);
    if (custom && custom.completo && typeof custom.completo === 'string' && custom.completo.trim().length > 0) {
      return true;
    }

    // 2. Si es apertura y está marcada explícitamente como pendiente de redacción
    if (phase === 'apertura' && inc.is_redaction_pending) {
      return false;
    }

    // 3. Objeto de mensajes ejecutivos
    const msg = inc.mensajes_ejecutivos && inc.mensajes_ejecutivos[phase];
    if (!msg || typeof msg !== 'object') return false;

    if (msg.estado === 'pendiente') return false;
    if (!msg.completo || typeof msg.completo !== 'string' || !msg.completo.trim()) return false;
    if (msg.generado_por_agente === false) return false;

    return true;
  }

  function renderDiscrepancyTableHtml(inc) {
    const isDisc = Boolean(inc.es_discrepancia || (inc.discrepancia && inc.discrepancia.es_discrepancia));
    if (!isDisc) return '';

    const prioOrig = inc.prioridad_original || inc.discrepancia?.prioridad_remedy || 'P3';
    const prioSug = inc.prioridad_sugerida || 'P2';
    const isP1 = prioSug === 'P1';
    const sevCalc = isP1 ? 'SL1' : 'SL2';
    const badgeClass = isP1 ? 'badge-sl1' : 'badge-sl2';
    const badgeText = isP1 ? 'SL1 · Emergencia Crítica' : 'SL2 · Mayor';

    const proceso = inc.discrepancia?.proceso_critico || inc.evaluacion?.proceso || 'Sistemas Core';
    const criterio = inc.discrepancia?.criterio_umbral || inc.evaluacion?.criterio || 'Regla de Oro N1';

    return `
      <div class="im-discrepancy-panel">
        <div class="im-discrepancy-title" style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
          <span>⚠️ Subescalación Detectada · Triaje N1 vs Criterio ITIL Orange</span>
          <button type="button" class="im-btn im-btn-secondary im-btn-sm btn-copy-remedy-reclass" data-inc="${escapeHtml(inc.id)}" title="Copiar texto formal para el registro de Remedy y requerir al resolutor la elevación de prioridad">
            <span aria-hidden="true">📋</span> Copiar Solicitud Reclasificación Remedy
          </button>
        </div>
        <table class="im-discrepancy-table">
          <thead>
            <tr>
              <th>Severidad Remedy</th>
              <th>Severidad ITIL / Orange</th>
              <th>Proceso Crítico Afectado</th>
              <th>Umbral Numérico Superado</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><span class="badge" style="background:#E2E8F0; color:#334155; font-weight:600;">${escapeHtml(prioOrig)} (Nominal)</span></td>
              <td><span class="badge ${badgeClass}">${escapeHtml(sevCalc)} (${badgeText})</span></td>
              <td><strong>${escapeHtml(proceso)}</strong></td>
              <td><span class="im-threshold-highlight">${escapeHtml(criterio)}</span></td>
            </tr>
          </tbody>
        </table>
      </div>
    `;
  }

  function renderWorkaroundLockBannerHtml(inc) {
    const wa = inc.workaround || {};
    const evaluacion = inc.evaluacion || {};

    let waDetected = Boolean(wa.workaround_detectado);
    let csoAuth = Boolean(wa.autorizado_cso);
    let impactErradicado = Boolean(wa.impacto_erradicado);

    if (wa.workaround_detectado === undefined) {
      const rawWa = String(evaluacion.workaround || '').trim().toLowerCase();
      const waGob = String(evaluacion.workaround_gobernanza || '').trim().toLowerCase();
      if (rawWa && !['desconocido', 'no', 'no identificado', 'ninguno', 'false', '', 'none'].includes(rawWa)) {
        waDetected = true;
      } else if (waGob.includes('workaround') && !waGob.includes('sin') && !waGob.includes('no')) {
        waDetected = true;
      }
      if (waGob.includes('autorizado') && !waGob.includes('pendiente')) {
        csoAuth = true;
      }
      const est = String(inc.estatus || '').trim().toLowerCase();
      impactErradicado = ['cerrado', 'resuelta', 'resuelto'].includes(est);
    }

    if (!waDetected || impactErradicado) {
      return '';
    }

    const prioSug = inc.prioridad_sugerida || 'P2';
    const badgeText = prioSug === 'P1' ? 'P1 / SL1' : 'P2 / SL2';
    const csoBadgeClass = csoAuth ? 'badge-cso-approved' : 'badge-cso-pending';
    const csoBadgeText = csoAuth ? '✅ Autorizado por IM-CSO' : '⏳ Pendiente Autorización IM-CSO';

    return `
      <div class="im-gov-lock-banner" role="alert" id="wa-lock-${escapeHtml(inc.id)}">
        <span class="im-gov-lock-icon" aria-hidden="true">🔒</span>
        <div>
          <strong>Desescalada Bloqueada (Regla de Oro CSO):</strong>
          Mitigación provisional / workaround detectado. La severidad se mantiene institucionalmente en <strong>${badgeText}</strong> hasta la resolución definitiva y erradicación total del impacto en clientes.
          <div style="margin-top: 6px; display: flex; align-items: center; gap: 8px;">
            <span style="font-size: 11px; font-weight: 600;">Gobernanza CSO:</span>
            <span class="badge ${csoBadgeClass}">${csoBadgeText}</span>
            <span style="font-size: 11px; color: var(--im-lock-red); font-style: italic;">(Acción de desescalada deshabilitada en consola)</span>
          </div>
        </div>
      </div>
    `;
  }

  function renderEscalationBannerHtml(inc, minsElapsed) {
    const incId = inc ? inc.id : '';
    if (minsElapsed >= 105) {
      return `
        <div class="im-escalation-alert-banner alert-105m" role="alert" id="escalation-banner-${escapeHtml(incId)}" style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
          <div style="display:flex; align-items:center; gap:10px; flex:1; min-width:260px;">
            <span class="im-phone-icon" aria-hidden="true">🚨</span>
            <div>
              <strong>2º Escalado a Estamentos Superiores (+1h / ≥105 min):</strong> Escalado telefónico inmediato a Dirección y Customer &amp; Service Ops (IM-CSO).
            </div>
          </div>
          <button type="button" class="im-btn im-btn-secondary im-btn-sm btn-copy-teams-warroom" data-inc="${escapeHtml(incId)}" title="Copiar mensaje formal de convocatoria a War Room de audio en Teams" style="white-space:nowrap; background:#fff;">
            <span aria-hidden="true">📞</span> Convocatoria War Room Teams
          </button>
        </div>
      `;
    } else if (minsElapsed >= 45) {
      return `
        <div class="im-escalation-alert-banner alert-45m" role="alert" id="escalation-banner-${escapeHtml(incId)}" style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
          <div style="display:flex; align-items:center; gap:10px; flex:1; min-width:260px;">
            <span class="im-phone-icon" aria-hidden="true">📞</span>
            <div>
              <strong>1er Escalado Telefónico Requerido (≥45 min):</strong> Convocatoria obligatoria a Resolutores N2/N3 vía audio/teléfono (Regla de Oro).
            </div>
          </div>
          <button type="button" class="im-btn im-btn-secondary im-btn-sm btn-copy-teams-warroom" data-inc="${escapeHtml(incId)}" title="Copiar mensaje formal de convocatoria a War Room de audio en Teams" style="white-space:nowrap; background:#fff;">
            <span aria-hidden="true">📞</span> Convocatoria War Room Teams
          </button>
        </div>
      `;
    }
    return '';
  }

  function updateLiveTimers() {
    const timerElements = document.querySelectorAll('.im-timer-badge[data-epoch]');
    const now = Date.now();

    timerElements.forEach((badge) => {
      const epochStr = badge.getAttribute('data-epoch');
      if (!epochStr) return;
      const epoch = parseInt(epochStr, 10);
      if (isNaN(epoch)) return;

      const elapsedMins = Math.max(0, Math.floor((now - epoch) / 60000));
      badge.textContent = `⏱️ ${formatTimerString(elapsedMins)}`;

      const incId = badge.getAttribute('data-inc');
      const card = incId ? document.getElementById(`card-${incId}`) : null;

      if (elapsedMins >= 105) {
        badge.classList.remove('im-timer-pulse-warning');
        badge.classList.add('im-timer-pulse-critical');

        if (card) {
          const incObj = (state.allIncidents || []).find((i) => i.id === incId) || { id: incId };
          let banner = card.querySelector('.im-escalation-alert-banner');
          if (!banner) {
            const bannerHtml = renderEscalationBannerHtml(incObj, elapsedMins);
            const contextBlock = card.querySelector('.incident-context-block');
            if (contextBlock && bannerHtml) {
              contextBlock.insertAdjacentHTML('afterend', bannerHtml);
            }
          } else if (banner.classList.contains('alert-45m')) {
            banner.outerHTML = renderEscalationBannerHtml(incObj, elapsedMins);
          }
        }
      } else if (elapsedMins >= 45) {
        badge.classList.remove('im-timer-pulse-critical');
        badge.classList.add('im-timer-pulse-warning');

        if (card) {
          const incObj = (state.allIncidents || []).find((i) => i.id === incId) || { id: incId };
          let banner = card.querySelector('.im-escalation-alert-banner');
          if (!banner) {
            const bannerHtml = renderEscalationBannerHtml(incObj, elapsedMins);
            const contextBlock = card.querySelector('.incident-context-block');
            if (contextBlock && bannerHtml) {
              contextBlock.insertAdjacentHTML('afterend', bannerHtml);
            }
          }
        }
      } else {
        badge.classList.remove('im-timer-pulse-critical', 'im-timer-pulse-warning');
      }
    });

    // Calcular el conteo único de alertas de escalado directamente sobre las incidencias activas únicas
    const escalationAlerts = (state.allIncidents || []).filter((inc) => {
      const epoch = inc.apertura_epoch_ms;
      const mins = (epoch && !isNaN(epoch))
        ? Math.max(0, Math.floor((now - epoch) / 60000))
        : (inc.minutos_desde_apertura || 0);
      return mins >= 45;
    }).length;

    state.kpis.escalation_alerts_count = escalationAlerts;

    if (dom.kpiEscalationAlertsCount) {
      dom.kpiEscalationAlertsCount.textContent = escalationAlerts;
    }
    if (dom.chipCountEscalation) {
      dom.chipCountEscalation.textContent = escalationAlerts;
    }

    if (dom.kpiCardEscalation) {
      if (escalationAlerts > 0) {
        dom.kpiCardEscalation.style.borderColor = 'var(--im-sl2-amber)';
        dom.kpiCardEscalation.style.background = 'linear-gradient(180deg, #FFFFFF 0%, #FFF7ED 100%)';
      } else {
        dom.kpiCardEscalation.style.borderColor = '';
        dom.kpiCardEscalation.style.background = '';
      }
    }
  }

  function startLiveTimersLoop() {
    if (state.liveTimerInterval) {
      clearInterval(state.liveTimerInterval);
    }
    state.liveTimerInterval = setInterval(updateLiveTimers, 10000);
  }

  function processApiPayload(payload) {
    const kpis = payload.kpis || {};
    const rawAll = payload.all_active_incidents || payload.incidents || [];
    const nowMs = Date.now();

    const all = rawAll.map((raw) => {
      const inc = { ...raw };

      // Parsear fecha apertura a epoch si está presente
      const fechaApertura = inc.fecha_apertura || inc.evaluacion?.fecha_apertura || inc.fecha_envio || '';
      inc.fecha_apertura = fechaApertura;
      let epochMs = inc.apertura_epoch_ms;
      if (!epochMs && fechaApertura) {
        epochMs = parseRemedyDateToEpochMs(fechaApertura);
      }
      inc.apertura_epoch_ms = epochMs;

      const minsElapsed = epochMs
        ? Math.max(0, Math.floor((nowMs - epochMs) / 60000))
        : (inc.minutos_desde_apertura !== undefined
            ? inc.minutos_desde_apertura
            : (inc.evaluacion?.minutos_desde_apertura || 0));
      inc.minutos_desde_apertura = minsElapsed;
      const isDisc = Boolean(inc.es_discrepancia || inc.discrepancia?.es_discrepancia);

      const isRedactionPending = inc.is_redaction_pending !== undefined
        ? Boolean(inc.is_redaction_pending)
        : Boolean(
            inc.mensajes_ejecutivos?.apertura?.estado === 'pendiente' ||
            !inc.mensajes_ejecutivos?.apertura?.completo
          );
      inc.is_redaction_pending = isRedactionPending;

      // Estado operativo del flujo de gestión (Pendiente, Comunicada, En Seguimiento, Descartada)
      // Sincronizado bidireccionalmente con el Centro de Notificaciones (hp_incident_notifications_state_v1)
      const opStatus = StateManager.getStatus(inc.id, inc);
      inc.operational_status = opStatus;

      // Una incidencia se considera PENDIENTE de tratar operativamente si su estado es 'pendiente'
      const isPending = (opStatus === 'pendiente');
      inc.is_pending = isPending;
      return inc;
    });

    const pending = all.filter((i) => i.is_pending);
    const completed = all.filter((i) => !i.is_pending);

    const discSl1 = kpis.discrepancies_sl1 !== undefined
      ? kpis.discrepancies_sl1
      : all.filter((i) => (i.es_discrepancia || i.discrepancia?.es_discrepancia) && (i.prioridad_sugerida === 'P1' || i.severidad_calculada === 'SL1')).length;

    const discSl2 = kpis.discrepancies_sl2 !== undefined
      ? kpis.discrepancies_sl2
      : all.filter((i) => (i.es_discrepancia || i.discrepancia?.es_discrepancia) && (i.prioridad_sugerida === 'P2' || i.severidad_calculada === 'SL2')).length;

    const escAlerts = kpis.escalation_alerts_count !== undefined
      ? kpis.escalation_alerts_count
      : (kpis.alertas_escalado_45m !== undefined ? kpis.alertas_escalado_45m : all.filter((i) => (i.minutos_desde_apertura || 0) >= 45).length);

    const waPendingCso = kpis.workarounds_pending_cso_count !== undefined
      ? kpis.workarounds_pending_cso_count
      : (kpis.workarounds_pendientes_cso !== undefined ? kpis.workarounds_pendientes_cso : all.filter((i) => i.workaround?.workaround_detectado && !i.workaround?.autorizado_cso).length);

    const redacPending = kpis.redactions_pending_count !== undefined
      ? kpis.redactions_pending_count
      : (kpis.redacciones_pendientes !== undefined ? kpis.redacciones_pendientes : all.filter((i) => i.is_redaction_pending).length);

    state.kpis = {
      total_active: all.length,
      completed_count: completed.length,
      pending_count: pending.length,
      redactions_pending_count: redacPending,
      p1_count: kpis.p1_count !== undefined ? kpis.p1_count : (kpis.sl1_criticas !== undefined ? kpis.sl1_criticas : all.filter((i) => i.prioridad_sugerida === 'P1').length),
      p2_count: kpis.p2_count !== undefined ? kpis.p2_count : (kpis.sl2_altas !== undefined ? kpis.sl2_altas : all.filter((i) => i.prioridad_sugerida === 'P2').length),
      discrepancies_count: kpis.discrepancies_count !== undefined ? kpis.discrepancies_count : (kpis.discrepancias_subescalacion !== undefined ? kpis.discrepancias_subescalacion : all.filter((i) => i.es_discrepancia || i.discrepancia?.es_discrepancia).length),
      discrepancies_sl1: discSl1,
      discrepancies_sl2: discSl2,
      escalation_alerts_count: escAlerts,
      workarounds_pending_cso_count: waPendingCso,
      generated_at: kpis.generated_at || payload._metadata?.generated_at || '',
      source_file: kpis.source_file || payload._metadata?.source_file || ''
    };

    state.pendingIncidents = pending;
    state.completedIncidents = completed;
    state.allIncidents = all;

    renderAll();
    updateLiveTimers();
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
    let discSl1 = 0;
    let discSl2 = 0;
    let escAlerts = 0;
    let waPendingCso = 0;

    const nowMs = Date.now();

    rawIncidents.forEach((raw) => {
      const inc = { ...raw };
      const incId = inc.id;
      const prio = inc.prioridad_sugerida || 'P2';

      if (prio === 'P1') p1++;
      else if (prio === 'P2') p2++;

      const isDisc = Boolean(inc.es_discrepancia);
      if (isDisc) {
        discrepancies++;
        if (prio === 'P1') discSl1++;
        else discSl2++;
      }

      // Parsear fecha apertura a epoch
      const fechaApertura = inc.fecha_apertura || inc.evaluacion?.fecha_apertura || inc.fecha_envio || '';
      inc.fecha_apertura = fechaApertura;
      const epochMs = parseRemedyDateToEpochMs(fechaApertura);
      inc.apertura_epoch_ms = epochMs;

      const minsElapsed = epochMs
        ? Math.max(0, Math.floor((nowMs - epochMs) / 60000))
        : (inc.evaluacion?.minutos_desde_apertura || 0);
      inc.minutos_desde_apertura = minsElapsed;

      if (minsElapsed >= 45) {
        escAlerts++;
      }

      // Detección de workaround
      const evaluacion = inc.evaluacion || {};
      const rawWa = String(evaluacion.workaround || '').trim().toLowerCase();
      const waGob = String(evaluacion.workaround_gobernanza || '').trim().toLowerCase();
      let waDetected = false;
      if (rawWa && !['desconocido', 'no', 'no identificado', 'ninguno', 'false', '', 'none'].includes(rawWa)) {
        waDetected = true;
      } else if (waGob.includes('workaround') && !waGob.includes('sin') && !waGob.includes('no')) {
        waDetected = true;
      }
      const csoAuth = waGob.includes('autorizado') && !waGob.includes('pendiente');
      if (waDetected && !csoAuth) {
        waPendingCso++;
      }

      // Enriquecer con mensajes del almacén oficial si están disponibles
      if (storeIncidents[incId]) {
        if (!inc.mensajes_ejecutivos) inc.mensajes_ejecutivos = {};
        ['apertura', 'seguimiento', 'cierre'].forEach((phase) => {
          if (storeIncidents[incId][phase] && (!inc.mensajes_ejecutivos[phase] || !inc.mensajes_ejecutivos[phase].completo)) {
            inc.mensajes_ejecutivos[phase] = storeIncidents[incId][phase];
          }
        });
      }

      const mensajes = inc.mensajes_ejecutivos || {};
      const apertura = mensajes.apertura || {};
      const storeEntry = storeIncidents[incId]?.apertura || {};
      const inStore = !!(storeEntry.completo && storeEntry.generado_por_agente !== false);

      const isRedactionPending = (
        apertura.estado === 'pendiente' ||
        !apertura.completo ||
        !inStore
      );
      inc.is_redaction_pending = isRedactionPending;

      // Estado operativo del flujo de gestión (Pendiente, Comunicada, En Seguimiento, Descartada)
      // Sincronizado bidireccionalmente con el Centro de Notificaciones (hp_incident_notifications_state_v1)
      const opStatus = StateManager.getStatus(incId, inc);
      inc.operational_status = opStatus;
      const isPending = (opStatus === 'pendiente');

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
      redactions_pending_count: all.filter((i) => i.is_redaction_pending).length,
      p1_count: p1,
      p2_count: p2,
      discrepancies_count: discrepancies,
      discrepancies_sl1: discSl1,
      discrepancies_sl2: discSl2,
      escalation_alerts_count: escAlerts,
      workarounds_pending_cso_count: waPendingCso,
      generated_at: catalogData._metadata?.generated_at || '',
      source_file: catalogData._metadata?.source_file || ''
    };

    state.pendingIncidents = pending;
    state.completedIncidents = completed;
    state.allIncidents = all;

    renderAll();
    updateLiveTimers();
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
    renderTriageView();
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
    if (dom.kpiDiscrepanciesSl1) dom.kpiDiscrepanciesSl1.textContent = k.discrepancies_sl1 || 0;
    if (dom.kpiDiscrepanciesSl2) dom.kpiDiscrepanciesSl2.textContent = k.discrepancies_sl2 || 0;
    if (dom.kpiEscalationAlertsCount) dom.kpiEscalationAlertsCount.textContent = k.escalation_alerts_count || 0;
    if (dom.kpiWorkaroundsPendingCount) dom.kpiWorkaroundsPendingCount.textContent = k.workarounds_pending_cso_count || 0;

    if (dom.kpiCardPending) {
      if (k.pending_count > 0) {
        dom.kpiCardPending.className = 'kpi-card kpi-pending-active';
        if (dom.kpiPendingFooter) {
          const detail = `🚨 ${k.pending_count} ${k.pending_count === 1 ? 'incidencia requiere' : 'incidencias requieren'} atención operativa (redacción SL1/P2, escalado >45m o discrepancia)`;
          dom.kpiPendingFooter.textContent = `🚨 ${k.pending_count} por tratar`;
          dom.kpiPendingFooter.title = detail;
        }
      } else {
        dom.kpiCardPending.className = 'kpi-card kpi-pending-clean';
        if (dom.kpiPendingFooter) {
          dom.kpiPendingFooter.textContent = '✅ Al día';
          dom.kpiPendingFooter.title = 'Sin incidencias pendientes de tratar';
        }
      }
    }

    if (dom.kpiCardEscalation) {
      if ((k.escalation_alerts_count || 0) > 0) {
        dom.kpiCardEscalation.style.borderColor = 'var(--im-sl2-amber)';
        dom.kpiCardEscalation.style.background = 'linear-gradient(180deg, #FFFFFF 0%, #FFF7ED 100%)';
      } else {
        dom.kpiCardEscalation.style.borderColor = '';
        dom.kpiCardEscalation.style.background = '';
      }
    }

    if (dom.kpiCardWorkarounds) {
      if ((k.workarounds_pending_cso_count || 0) > 0) {
        dom.kpiCardWorkarounds.style.borderColor = 'var(--im-lock-border)';
        dom.kpiCardWorkarounds.style.background = 'linear-gradient(180deg, #FFFFFF 0%, var(--im-lock-bg) 100%)';
      } else {
        dom.kpiCardWorkarounds.style.borderColor = '';
        dom.kpiCardWorkarounds.style.background = '';
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

  /**
   * Compara el proceso de negocio de la incidencia con el valor del filtro de forma tolerante a variantes
   * (p. ej. 'Provisión' vs 'Provisión y Activación', 'Ventas' vs 'Ventas y Canales').
   */
  function matchProcess(incProcess, filterVal) {
    if (!filterVal || filterVal === 'all') return true;
    if (!incProcess) return false;
    const p = String(incProcess).trim().toLowerCase();
    const f = String(filterVal).trim().toLowerCase();
    if (p === f) return true;

    const isProvision = (s) => s.includes('provis');
    const isSales = (s) => s.includes('venta');
    const isBilling = (s) => s.includes('factur');
    const isAtc = (s) => s.includes('atc') || s.includes('atención') || s.includes('atencion');
    const isOm = (s) => s.includes('o&m') || s.includes('operac') || s.includes('monitor') || s.includes('red');
    const isCore = (s) => s.includes('core');
    const isPrepaid = (s) => s.includes('prepag');
    const isPortability = (s) => s.includes('portabil');

    if (isProvision(f) && isProvision(p)) return true;
    if (isSales(f) && isSales(p)) return true;
    if (isBilling(f) && isBilling(p)) return true;
    if (isAtc(f) && isAtc(p)) return true;
    if (isOm(f) && isOm(p)) return true;
    if (isCore(f) && isCore(p)) return true;
    if (isPrepaid(f) && isPrepaid(p)) return true;
    if (isPortability(f) && isPortability(p)) return true;

    return false;
  }

  function getFilteredIncidents(options = {}) {
    // Si options.useAll está activado (como en la bandeja de triaje inicial),
    // evaluamos sobre allIncidents. En la vista de tarjetas se respeta state.activeView ('pending' vs 'all').
    const sourceList = options.useAll
      ? state.allIncidents
      : (state.activeView === 'pending' ? state.pendingIncidents : state.allIncidents);

    const { severity, process, commPhase, onlyDiscrepancies, search } = state.filters;
    const q = search.trim().toLowerCase();

    return sourceList.filter((inc) => {
      // 1. Filtro de Severidad
      if (severity !== 'all' && inc.prioridad_sugerida !== severity) {
        return false;
      }

      // 2. Filtro de Proceso de Negocio con normalización tolerante
      const proc = inc.evaluacion?.proceso || inc.discrepancia?.proceso_critico || '';
      if (!matchProcess(proc, process)) {
        return false;
      }

      // 3. Filtro de Comunicación Oficial (Apertura / Seguimiento / Cierre)
      if (commPhase && commPhase !== 'all') {
        const hasAp = hasOfficialMessage(inc, 'apertura');
        const hasSeg = hasOfficialMessage(inc, 'seguimiento');
        const hasCie = hasOfficialMessage(inc, 'cierre');

        if (commPhase === 'missing_any' && (hasAp && hasSeg && hasCie)) return false;
        if (commPhase === 'missing_apertura' && hasAp) return false;
        if (commPhase === 'missing_seguimiento' && hasSeg) return false;
        if (commPhase === 'missing_cierre' && hasCie) return false;
        if (commPhase === 'missing_all' && (hasAp || hasSeg || hasCie)) return false;
        if (commPhase === 'has_apertura' && !hasAp) return false;
        if (commPhase === 'has_seguimiento' && !hasSeg) return false;
        if (commPhase === 'has_cierre' && !hasCie) return false;
        if (commPhase === 'all_completed' && (!hasAp || !hasSeg || !hasCie)) return false;
      }

      // 4. Filtro Solo Discrepancias (comprobando flags raíz y anidado)
      if (onlyDiscrepancies) {
        const isDisc = Boolean(inc.es_discrepancia || inc.discrepancia?.es_discrepancia);
        if (!isDisc) return false;
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

  // --- Lógica de Triaje Operativo "De un Vistazo" (Página Inicial) ---

  function determineIncidentUrgency(inc, minsElapsed) {
    const isP1 = inc.prioridad_sugerida === 'P1';
    const isRedactionPending = Boolean(inc.is_redaction_pending !== undefined ? inc.is_redaction_pending : inc.is_pending);
    const mins = Number(minsElapsed) || 0;
    const wa = inc.workaround || {};
    const evaluacion = inc.evaluacion || {};

    let waDetected = Boolean(wa.workaround_detectado);
    let csoAuth = Boolean(wa.autorizado_cso);
    let impactErradicado = Boolean(wa.impacto_erradicado);
    if (wa.workaround_detectado === undefined) {
      const rawWa = String(evaluacion.workaround || '').trim().toLowerCase();
      const waGob = String(evaluacion.workaround_gobernanza || '').trim().toLowerCase();
      if (rawWa && !['desconocido', 'no', 'no identificado', 'ninguno', 'false', '', 'none'].includes(rawWa)) {
        waDetected = true;
      } else if (waGob.includes('workaround') && !waGob.includes('sin') && !waGob.includes('no')) {
        waDetected = true;
      }
      if (waGob.includes('autorizado') && !waGob.includes('pendiente')) {
        csoAuth = true;
      }
      const est = String(inc.estatus || '').trim().toLowerCase();
      impactErradicado = ['cerrado', 'resuelta', 'resuelto'].includes(est);
    }
    const isWaLocked = waDetected && (!csoAuth || !impactErradicado);
    const isDisc = Boolean(inc.es_discrepancia || (inc.discrepancia && inc.discrepancia.es_discrepancia));

    const opStatus = inc.operational_status || 'pendiente';

    // 0.1 Incidencia Descartada
    if (opStatus === 'descartada') {
      return {
        level: 'dismissed',
        code: 'DESCARTADA',
        label: '⚪ DESCARTADA',
        badgeClass: 'urgency-badge-dismissed',
        needsAction: false,
        actionText: '👁️ Ver Detalle',
        actionTitle: 'Incidencia descartada del flujo operativo'
      };
    }

    // 0.2 Incidencia en Seguimiento Activo
    if (opStatus === 'en_seguimiento') {
      return {
        level: 'monitoring',
        code: 'EN_SEGUIMIENTO',
        label: '🔍 EN SEGUIMIENTO',
        badgeClass: 'urgency-badge-monitoring',
        needsAction: false,
        actionText: '👁️ Ver Detalle',
        actionTitle: 'Incidencia bajo seguimiento activo y comunicada a Dirección'
      };
    }

    // 0.3 Incidencia Comunicada Oficialmente
    if (opStatus === 'comunicada') {
      if (mins >= 105) {
        return {
          level: 'critical',
          code: 'ESCALADO_105M',
          label: '🚨 ESCALAR DIR (+105m)',
          badgeClass: 'urgency-badge-105m',
          needsAction: true,
          actionText: '📞 Escalar Dirección',
          actionTitle: 'Superados 105 min de apertura Remedy: llamada inmediata a Dirección y CSO'
        };
      }
      return {
        level: 'communicated',
        code: 'COMUNICADA',
        label: '📣 COMUNICADA',
        badgeClass: 'urgency-badge-communicated',
        needsAction: false,
        actionText: '👁️ Ver Detalle',
        actionTitle: 'Incidencia comunicada oficialmente a Dirección'
      };
    }

    // 1. Crítica Inmediata: SL1 y pendiente de redacción oficial
    if (isP1 && isRedactionPending) {
      return {
        level: 'critical',
        code: 'TRATAR_YA_SL1',
        label: '🚨 TRATAR YA (SL1)',
        badgeClass: 'urgency-badge-sl1',
        needsAction: true,
        actionText: '⚡ Tratar Ya',
        actionTitle: 'Emergencia crítica SL1 sin redacción oficial de agente aprobada'
      };
    }

    // 2. Escalado vencido a Dirección / CSO (≥105 min)
    if (mins >= 105) {
      return {
        level: 'critical',
        code: 'ESCALADO_105M',
        label: '🚨 ESCALAR DIR (+105m)',
        badgeClass: 'urgency-badge-105m',
        needsAction: true,
        actionText: '📞 Escalar Dirección',
        actionTitle: 'Superados 105 min de apertura Remedy: llamada inmediata a Dirección y CSO'
      };
    }

    // 3. Escalado telefónico vencido (≥45 min)
    if (mins >= 45) {
      return {
        level: 'warning',
        code: 'ESCALADO_45M',
        label: '📞 ESCALADO REQUERIDO (≥45m)',
        badgeClass: 'urgency-badge-45m',
        needsAction: true,
        actionText: isRedactionPending ? '⚡ Tratar & Llamar' : '📞 Convocar N2/N3',
        actionTitle: 'Superados 45 min de apertura: convocatoria obligatoria por audio a resolutores'
      };
    }

    // 4. Pendiente de redacción (P2 / SL2)
    if (isRedactionPending) {
      return {
        level: 'pending',
        code: 'PENDIENTE_REDACCION',
        label: '✍️ REDACTAR OFICIAL',
        badgeClass: 'urgency-badge-pending',
        needsAction: true,
        actionText: '✍️ Redactar Agente',
        actionTitle: 'Incidencia pendiente de mensaje oficial para Dirección (incident-reporter)'
      };
    }

    // 5. Discrepancia no resuelta
    if (isDisc) {
      return {
        level: 'discrepancy',
        code: 'DISCREPANCIA_N1',
        label: '⚖️ SUBESCALADO REMEDY',
        badgeClass: 'urgency-badge-disc',
        needsAction: true,
        actionText: '⚖️ Revisar Triaje',
        actionTitle: 'Triaje N1 Remedy subescaló la severidad respecto al criterio ITIL Orange'
      };
    }

    // 6. Workaround bloqueado
    if (isWaLocked) {
      return {
        level: 'locked',
        code: 'WORKAROUND_LOCK',
        label: '🔒 WORKAROUND BLOQUEADO',
        badgeClass: 'urgency-badge-lock',
        needsAction: true,
        actionText: '🔒 Ver Gobernanza',
        actionTitle: 'Mitigación provisional sin autorización CSO o con impacto activo'
      };
    }

    // 7. Al Día / En Seguimiento
    return {
      level: 'stable',
      code: 'AL_DIA',
      label: '🟢 AL DÍA',
      badgeClass: 'urgency-badge-stable',
      needsAction: false,
      actionText: '👁️ Ver Detalle',
      actionTitle: 'Comunicación oficial aprobada y tiempos operativamente controlados'
    };
  }

  function setPresentationMode(mode) {
    state.presentationMode = mode;
    if (dom.tabPresTriage && dom.tabPresCards) {
      if (mode === 'triage') {
        dom.tabPresTriage.classList.add('active');
        dom.tabPresTriage.setAttribute('aria-selected', 'true');
        dom.tabPresCards.classList.remove('active');
        dom.tabPresCards.setAttribute('aria-selected', 'false');

        if (dom.triageViewContainer) dom.triageViewContainer.style.display = 'block';
        if (dom.cardsNavBar) dom.cardsNavBar.style.display = 'none';
        if (dom.queueContainer) dom.queueContainer.style.display = 'none';
        if (dom.emptyStateContainer) dom.emptyStateContainer.style.display = 'none';
        renderTriageView();
      } else {
        dom.tabPresCards.classList.add('active');
        dom.tabPresCards.setAttribute('aria-selected', 'true');
        dom.tabPresTriage.classList.remove('active');
        dom.tabPresTriage.setAttribute('aria-selected', 'false');

        if (dom.triageViewContainer) dom.triageViewContainer.style.display = 'none';
        if (dom.cardsNavBar) dom.cardsNavBar.style.display = 'flex';
        if (dom.queueContainer) dom.queueContainer.style.display = 'flex';
        renderQueue();
      }
    }
  }

  function treatIncident(incId) {
    if (!incId) return;

    // 1. Cambiamos modo a tarjetas
    setPresentationMode('cards');

    // 2. Localizamos la tarjeta correspondiente
    setTimeout(() => {
      const card = document.getElementById(`card-${incId}`);
      if (card) {
        card.scrollIntoView({ behavior: 'smooth', block: 'center' });
        card.classList.add('im-card-highlight');
        setTimeout(() => card.classList.remove('im-card-highlight'), 3000);

        // Desplegamos automáticamente el panel de reportes y redacción
        const reportsWrapper = card.querySelector(`#reports-wrapper-${incId}`);
        const toggleBtn = card.querySelector('.btn-toggle-report');
        if (reportsWrapper && (reportsWrapper.classList.contains('collapsed') || reportsWrapper.hasAttribute('hidden') || reportsWrapper.style.display === 'none')) {
          reportsWrapper.classList.remove('collapsed');
          reportsWrapper.removeAttribute('hidden');
          reportsWrapper.style.display = 'flex';
          state.reportVisibility[incId] = true;
          if (toggleBtn) {
            toggleBtn.setAttribute('aria-expanded', 'true');
            toggleBtn.innerHTML = '<span aria-hidden="true">▲</span> Ocultar Reportes';
          }
        }
        announceSR(`Visualizando detalle de incidencia ${incId}`);
      }
    }, 120);
  }

  function renderTriageView() {
    if (!dom.triageTableBody || !dom.triageEmptyState) return;

    // Obtenemos las incidencias que cumplen los filtros globales sobre allIncidents
    const incidents = getFilteredIncidents({ useAll: true });

    // Calculamos contadores de los chips de urgencia
    let countUrgent = 0;
    let countPending = 0;
    let countEscalation = 0;
    let countDiscrepancy = 0;
    let countMissingComm = 0;
    const countAll = incidents.length;

    const enriched = incidents.map((inc) => {
      const minsElapsed = inc.apertura_epoch_ms
        ? Math.max(0, Math.floor((Date.now() - inc.apertura_epoch_ms) / 60000))
        : (inc.minutos_desde_apertura !== undefined ? inc.minutos_desde_apertura : 0);
      const urgency = determineIncidentUrgency(inc, minsElapsed);
      const hasAp = hasOfficialMessage(inc, 'apertura');
      const hasSeg = hasOfficialMessage(inc, 'seguimiento');
      const hasCie = hasOfficialMessage(inc, 'cierre');
      const hasAnyMissing = !hasAp || !hasSeg || !hasCie;

      if (urgency.needsAction || inc.is_pending) countUrgent++;
      if (inc.is_pending) countPending++;
      if (minsElapsed >= 45) countEscalation++;
      if (inc.es_discrepancia || inc.discrepancia?.es_discrepancia) countDiscrepancy++;
      if (hasAnyMissing) countMissingComm++;
      return { inc, minsElapsed, urgency, hasAp, hasSeg, hasCie, hasAnyMissing };
    });

    if (dom.chipCountUrgent) dom.chipCountUrgent.textContent = countUrgent;
    if (dom.chipCountPending) dom.chipCountPending.textContent = countPending;
    if (dom.chipCountEscalation) dom.chipCountEscalation.textContent = countEscalation;
    if (dom.chipCountDiscrepancy) dom.chipCountDiscrepancy.textContent = countDiscrepancy;
    if (dom.chipCountMissingComm) dom.chipCountMissingComm.textContent = countMissingComm;
    if (dom.chipCountAll) dom.chipCountAll.textContent = countAll;

    // Filtramos según el chip de triaje activo (state.triageFilter) y la sub-vista (state.activeView)
    const activeFilter = state.triageFilter || (state.activeView === 'all' ? 'all' : 'pending');
    const filteredRows = enriched.filter(({ inc, minsElapsed, urgency, hasAnyMissing }) => {
      if (state.activeView === 'pending' && !inc.is_pending) {
        return false;
      }
      if (activeFilter === 'urgent') return urgency.needsAction || inc.is_pending;
      if (activeFilter === 'pending') return Boolean(inc.is_pending);
      if (activeFilter === 'escalation') return minsElapsed >= 45;
      if (activeFilter === 'discrepancy') return Boolean(inc.es_discrepancia || inc.discrepancia?.es_discrepancia);
      if (activeFilter === 'missing_comm') return Boolean(hasAnyMissing);
      return true; // 'all'
    });

    if (filteredRows.length === 0) {
      dom.triageTableBody.innerHTML = '';
      dom.triageEmptyState.style.display = 'flex';
      return;
    }

    dom.triageEmptyState.style.display = 'none';

    const rowsHtml = filteredRows.map(({ inc, minsElapsed, urgency, hasAp, hasSeg, hasCie }) => {
      const incId = inc.id || 'INC000000000000';
      const isP1 = inc.prioridad_sugerida === 'P1';
      const isPending = Boolean(inc.is_pending);
      const isDisc = Boolean(inc.es_discrepancia || (inc.discrepancia && inc.discrepancia.es_discrepancia));
      const evaluacion = inc.evaluacion || {};
      const proceso = evaluacion.proceso || inc.discrepancia?.proceso_critico || 'Sistemas Core';
      const epochMs = inc.apertura_epoch_ms || '';

      let timerPulseClass = '';
      if (minsElapsed >= 105) {
        timerPulseClass = 'im-timer-pulse-critical';
      } else if (minsElapsed >= 45) {
        timerPulseClass = 'im-timer-pulse-warning';
      }

      const sistemasHtml = (inc.sistemas && inc.sistemas.length > 0)
        ? inc.sistemas.slice(0, 3).map((s) => `<span class="context-systems">${escapeHtml(s)}</span>`).join(' ')
        : '<span class="context-systems">N/A</span>';

      return `
        <tr class="im-triage-row ${urgency.needsAction ? 'row-action-needed' : ''}" data-inc="${escapeHtml(incId)}" title="Clic para gestionar ${escapeHtml(incId)}">
          <td>
            <span class="im-urgency-badge ${urgency.badgeClass}" title="${escapeHtml(urgency.actionTitle)}">
              ${urgency.needsAction ? '<span class="chip-pulse-dot" aria-hidden="true"></span>' : ''}
              ${urgency.label}
            </span>
          </td>
          <td>
            <a href="javascript:void(0)" class="incident-id-link triage-inc-link" data-inc="${escapeHtml(incId)}" title="Ver Resumen IA para ${escapeHtml(incId)}">
              <span aria-hidden="true">🤖</span> ${escapeHtml(incId)}
            </a>
            <div class="triage-comm-pills" title="Comunicaciones Oficiales: Apertura (${hasAp ? 'Generada' : 'Pendiente'}), Seguimiento (${hasSeg ? 'Generado' : 'Pendiente'}), Cierre (${hasCie ? 'Generado' : 'Pendiente'})">
              <span class="comm-pill ${hasAp ? 'comm-pill-ok' : 'comm-pill-missing'}" title="Apertura: ${hasAp ? 'Oficial generada' : 'Pendiente'}">Ap: ${hasAp ? '✓' : '✗'}</span>
              <span class="comm-pill ${hasSeg ? 'comm-pill-ok' : 'comm-pill-missing'}" title="Seguimiento: ${hasSeg ? 'Oficial generado' : 'Pendiente'}">Seg: ${hasSeg ? '✓' : '⏳'}</span>
              <span class="comm-pill ${hasCie ? 'comm-pill-ok' : 'comm-pill-missing'}" title="Cierre: ${hasCie ? 'Oficial generado' : 'Pendiente'}">Cie: ${hasCie ? '✓' : '🏁'}</span>
            </div>
          </td>
          <td>
            <div class="triage-title" title="${escapeHtml(inc.titulo || '')}">
              ${escapeHtml(inc.titulo || 'Sin título registrado')}
            </div>
          </td>
          <td>
            <div style="display:flex; align-items:center; gap:4px; flex-wrap:wrap;">
              <span class="badge ${isP1 ? 'badge-sl1' : 'badge-sl2'}">${isP1 ? 'SL1 · P1' : 'SL2 · P2'}</span>
              ${isDisc ? `<span class="badge" style="background:#F3E8FF; color:#6B21A8; font-size:9.5px;" title="Remedy nominal: ${escapeHtml(inc.prioridad_original || 'P3')}">N1: ${escapeHtml(inc.prioridad_original || 'P3')}</span>` : ''}
            </div>
          </td>
          <td>
            <div class="triage-process">
              <span class="context-tag-process" style="font-size:11px;">${escapeHtml(proceso)}</span>
              <div class="triage-systems-list">${sistemasHtml}</div>
            </div>
          </td>
          <td>
            <span class="im-timer-badge ${timerPulseClass}" data-epoch="${epochMs}" data-inc="${escapeHtml(incId)}" title="Tiempo transcurrido">${formatTimerString(minsElapsed)}</span>
          </td>
          <td>
            <select class="im-status-select status-${inc.operational_status || 'pendiente'}" data-action="change-operational-status" data-inc="${escapeHtml(incId)}" title="Cambiar estado del flujo de gestión" onclick="event.stopPropagation()">
              <option value="pendiente" ${(inc.operational_status || 'pendiente') === 'pendiente' ? 'selected' : ''}>🟡 Pendiente</option>
              <option value="comunicada" ${inc.operational_status === 'comunicada' ? 'selected' : ''}>📣 Comunicada</option>
              <option value="en_seguimiento" ${inc.operational_status === 'en_seguimiento' ? 'selected' : ''}>🔍 En Seguimiento</option>
              <option value="descartada" ${inc.operational_status === 'descartada' ? 'selected' : ''}>⚪ Descartada</option>
            </select>
          </td>
          <td style="text-align: right; white-space: nowrap;">
            <div style="display: inline-flex; align-items: center; gap: 4px; justify-content: flex-end;">
              ${isDisc ? `<button type="button" class="im-btn im-btn-secondary im-btn-sm btn-quick-reclass" data-inc="${escapeHtml(incId)}" title="Copiar Solicitud Reclasificación Remedy"><span aria-hidden="true">📋</span> Reclasif.</button>` : ''}
              ${minsElapsed >= 45 ? `<button type="button" class="im-btn im-btn-secondary im-btn-sm btn-quick-warroom" data-inc="${escapeHtml(incId)}" title="Copiar Convocatoria War Room Teams"><span aria-hidden="true">📞</span> War Room</button>` : ''}
              <button type="button" class="im-btn ${urgency.needsAction ? 'im-btn-primary' : 'im-btn-secondary'} im-btn-sm btn-treat-incident" data-inc="${escapeHtml(incId)}" title="Gestionar ${escapeHtml(incId)} en vista detallada">
                <span>${escapeHtml(urgency.actionText)}</span>
                <span aria-hidden="true">↗</span>
              </button>
            </div>
          </td>
        </tr>
      `;
    }).join('');

    dom.triageTableBody.innerHTML = rowsHtml;

    // Vincular eventos en la tabla de triaje
    bindTriageTableEvents();
    updateResetButtonVisibility();
  }

  function bindTriageTableEvents() {
    if (!dom.triageTableBody) return;

    // 1. Enlace de ID -> Abre Resumen IA modal
    dom.triageTableBody.querySelectorAll('.triage-inc-link').forEach((link) => {
      link.addEventListener('click', (e) => {
        e.stopPropagation();
        const incId = link.getAttribute('data-inc');
        if (typeof window.openResumenIA === 'function') {
          window.openResumenIA(incId);
        } else if (window.ResumenIAModal && typeof window.ResumenIAModal.open === 'function') {
          window.ResumenIAModal.open(incId);
        } else {
          showToast(`Abriendo Resumen IA para ${incId}...`, 'info');
        }
      });
    });

    // 2. Botón "Tratar Incidencia"
    dom.triageTableBody.querySelectorAll('.btn-treat-incident').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const incId = btn.getAttribute('data-inc');
        treatIncident(incId);
      });
    });

    // 3. Clic en la fila -> También salta a tratar la incidencia
    dom.triageTableBody.querySelectorAll('.im-triage-row').forEach((row) => {
      row.addEventListener('click', (e) => {
        if (e.target.closest('a') || e.target.closest('button') || e.target.closest('select')) return;
        const incId = row.getAttribute('data-inc');
        treatIncident(incId);
      });
    });

    // 4. Selector de Estado Operativo en la tabla (Pendiente, Comunicada, En Seguimiento, Descartada)
    dom.triageTableBody.querySelectorAll('select[data-action="change-operational-status"]').forEach((sel) => {
      sel.addEventListener('change', (e) => {
        e.stopPropagation();
        const incId = sel.getAttribute('data-inc');
        const newStatus = sel.value;
        StateManager.setStatus(incId, newStatus);
        showToast(`${incId}: Estado cambiado a ${getOperationalStatusLabel(newStatus)}`, 'success');
        loadData(false);
      });
      sel.addEventListener('click', (e) => e.stopPropagation());
    });

    // 5. Botones Rápidos en Fila: Reclasificación y War Room Teams
    dom.triageTableBody.querySelectorAll('.btn-quick-reclass').forEach((btn) => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const incId = btn.getAttribute('data-inc');
        const inc = (state.allIncidents || []).find((i) => i.id === incId);
        if (!inc) return;
        const text = buildRemedyReclassificationText(inc);
        try {
          await navigator.clipboard.writeText(text);
          const origHtml = btn.innerHTML;
          btn.innerHTML = '<span aria-hidden="true">✅</span> Copiado';
          showToast(`¡Solicitud de reclasificación para ${incId} copiada al portapapeles!`, 'success');
          setTimeout(() => { btn.innerHTML = origHtml; }, 2000);
        } catch (err) {
          showToast('Error al copiar: ' + err.message, 'error');
        }
      });
    });

    dom.triageTableBody.querySelectorAll('.btn-quick-warroom').forEach((btn) => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const incId = btn.getAttribute('data-inc');
        const inc = (state.allIncidents || []).find((i) => i.id === incId);
        if (!inc) return;
        const mins = inc.apertura_epoch_ms
          ? Math.max(0, Math.floor((Date.now() - inc.apertura_epoch_ms) / 60000))
          : (inc.minutos_desde_apertura || 0);
        const text = buildTeamsWarRoomText(inc, mins);
        try {
          await navigator.clipboard.writeText(text);
          const origHtml = btn.innerHTML;
          btn.innerHTML = '<span aria-hidden="true">✅</span> Copiado';
          showToast(`¡Convocatoria War Room para ${incId} copiada al portapapeles!`, 'success');
          setTimeout(() => { btn.innerHTML = origHtml; }, 2000);
        } catch (err) {
          showToast('Error al copiar: ' + err.message, 'error');
        }
      });
    });
  }

  function renderQueue() {
    if (!dom.queueContainer || !dom.emptyStateContainer) return;

    const incidents = getFilteredIncidents();

    if (incidents.length === 0) {
      dom.queueContainer.innerHTML = '';
      dom.emptyStateContainer.style.display = 'flex';

      if (state.activeView === 'pending' && state.pendingIncidents.length === 0) {
        dom.emptyStateTitle.textContent = '✅ Sin incidencias pendientes de tratar';
        dom.emptyStateDesc.textContent =
          'Todas las incidencias activas están al día: redacción oficial aprobada, sin escalados telefónicos vencidos (>45 min) ni discrepancias de triaje.';
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
    updateResetButtonVisibility();
  }

  // --- Creación de Tarjeta de Incidencia ---

  function createIncidentCardElement(inc) {
    const isP1 = inc.prioridad_sugerida === 'P1';
    const borderClass = isP1 ? 'border-p1' : 'border-p2';
    const badgeClass = isP1 ? 'badge-p1' : 'badge-p2';
    const badgeText = isP1 ? 'P1 · Crítica' : 'P2 · Alta';

    const incId = inc.id || 'INC000000000000';
    const activePhase = state.activePhases[incId] || 'apertura';
    const hasAp = hasOfficialMessage(inc, 'apertura');
    const hasSeg = hasOfficialMessage(inc, 'seguimiento');
    const hasCie = hasOfficialMessage(inc, 'cierre');

    // Cronometraje y estado de escalado
    const minsElapsed = inc.minutos_desde_apertura !== undefined ? inc.minutos_desde_apertura : 0;
    const epochMs = inc.apertura_epoch_ms || '';
    let timerPulseClass = '';
    if (minsElapsed >= 105) {
      timerPulseClass = 'im-timer-pulse-critical';
    } else if (minsElapsed >= 45) {
      timerPulseClass = 'im-timer-pulse-warning';
    }

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

    // Banners y tablas de Emergencia (US1, US2, US3, US4)
    const discrepancyTableHtml = renderDiscrepancyTableHtml(inc);
    const escalationBannerHtml = renderEscalationBannerHtml(inc, minsElapsed);
    const workaroundBannerHtml = renderWorkaroundLockBannerHtml(inc);
    const isReportVisible = Boolean(state.reportVisibility[incId] === true);

    // Contenido HTML de la tarjeta
    const opStatus = inc.operational_status || StateManager.getStatus(incId, inc);
    card.innerHTML = `
      <div class="incident-card-header">
        <div class="incident-card-badges">
          <a href="javascript:void(0)" class="incident-id-link" data-inc="${escapeHtml(incId)}" title="Ver Resumen IA para ${escapeHtml(incId)}">
            <span aria-hidden="true">🤖</span> ${escapeHtml(incId)}
          </a>
          <span class="badge ${badgeClass}">${badgeText}</span>
          ${discrepancyHtml}
          <span class="badge badge-status">Remedy: ${escapeHtml(inc.estatus || 'En curso')}</span>
          <span class="badge" style="background:#F1F5F9; color:#0F172A; font-family:var(--im-font-mono);">SLA: ${sla}</span>
          <select class="im-status-select status-${opStatus}" data-action="change-operational-status" data-inc="${escapeHtml(incId)}" title="Cambiar estado del flujo de gestión" style="margin-left: 4px;">
            <option value="pendiente" ${opStatus === 'pendiente' ? 'selected' : ''}>🟡 Pendiente</option>
            <option value="comunicada" ${opStatus === 'comunicada' ? 'selected' : ''}>📣 Comunicada</option>
            <option value="en_seguimiento" ${opStatus === 'en_seguimiento' ? 'selected' : ''}>🔍 En Seguimiento</option>
            <option value="descartada" ${opStatus === 'descartada' ? 'selected' : ''}>⚪ Descartada</option>
          </select>
        </div>
        <div style="display:flex; align-items:center; gap:10px;">
          <span class="im-timer-badge ${timerPulseClass}" id="timer-badge-${escapeHtml(incId)}" data-epoch="${epochMs}" data-inc="${escapeHtml(incId)}" title="Tiempo transcurrido desde apertura Remedy">⏱️ ${formatTimerString(minsElapsed)}</span>
          <span class="incident-timing" title="Fecha de apertura Remedy">${escapeHtml(inc.fecha_apertura || inc.fecha_envio || 'Reciente')}</span>
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

      ${discrepancyTableHtml}
      ${escalationBannerHtml}
      ${workaroundBannerHtml}

      <div class="incident-actions-row">
        <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
          <button type="button" class="im-btn im-btn-secondary im-btn-sm btn-card-to-triage" data-inc="${escapeHtml(incId)}" title="Volver a la bandeja de triaje inicial">
            <span aria-hidden="true">⬅</span> Triaje
          </button>
          ${epsilonBtnHtml}
          <button type="button" class="im-btn ${inc.is_redaction_pending ? 'im-btn-primary' : 'im-btn-secondary'} im-btn-sm btn-toggle-report" data-inc="${escapeHtml(incId)}" aria-expanded="${isReportVisible ? 'true' : 'false'}">
            <span aria-hidden="true">${isReportVisible ? '▲' : '📄'}</span> ${isReportVisible ? 'Ocultar Reportes' : (inc.is_redaction_pending ? '✍️ Redactar / Ver Reportes' : '📄 Ver Reportes')}
          </button>
        </div>
        <div style="font-size:11px; display:flex; align-items:center; gap:6px; flex-wrap:wrap;">
          <span class="badge ${hasAp ? 'badge-comm-ok' : 'badge-comm-missing'}" title="Apertura oficial">${hasAp ? '✅ Apertura Oficial' : '⚠️ Sin Apertura'}</span>
          <span class="badge ${hasSeg ? 'badge-comm-ok' : 'badge-comm-missing'}" title="Seguimiento oficial">${hasSeg ? '✅ Seguimiento Oficial' : '⏳ Sin Seguimiento'}</span>
          <span class="badge ${hasCie ? 'badge-comm-ok' : 'badge-comm-missing'}" title="Cierre oficial">${hasCie ? '✅ Cierre Oficial' : '🏁 Sin Cierre'}</span>
          ${minsElapsed >= 45 ? '<span class="badge" style="background:#FFF7ED; color:#C2410C; border:1px solid #FDBA74; font-size:10px;">📞 Escalado >45m</span>' : ''}
          ${inc.es_discrepancia ? '<span class="badge" style="background:#FAF5FF; color:#7E22CE; border:1px solid #D8B4FE; font-size:10px;">⚖️ Discrepancia N1</span>' : ''}
        </div>
      </div>

      <!-- Contenedor Plegable de Reportes y Redacción Oficial (Plegado por Defecto) -->
      <div class="im-reports-wrapper ${isReportVisible ? '' : 'collapsed'}" id="reports-wrapper-${escapeHtml(incId)}" ${isReportVisible ? '' : 'hidden'} style="${isReportVisible ? '' : 'display: none;'}">
        <!-- 1. Reporte Oficial de Emergencia en 4 Bloques Normalizados -->
        <div class="im-emergency-report-box" id="report-box-${escapeHtml(incId)}">
          <div class="im-emergency-report-header">
            <span>🚨 REPORTE DE EMERGENCIA (4 BLOQUES NORMALIZADOS)</span>
            <div style="display:flex; align-items:center; gap:8px;">
              <button type="button" class="im-btn im-btn-secondary im-btn-sm btn-copy-report" data-inc="${escapeHtml(incId)}" title="Copiar reporte normalizado de 4 bloques">
                <span aria-hidden="true">📋</span> Copiar Reporte
              </button>
              <button type="button" class="im-btn im-btn-secondary im-btn-sm btn-close-report" data-inc="${escapeHtml(incId)}" title="Plegar panel de reportes">
                <span aria-hidden="true">▲</span> Plegar
              </button>
            </div>
          </div>
          <pre class="im-emergency-report-content" id="report-content-${escapeHtml(incId)}">${escapeHtml(generate4BlockEmergencyReport(inc, minsElapsed))}</pre>
        </div>

        <!-- 2. Panel de Redacción de Agente e Ingesta Oficial -->
        <section class="agent-panel" aria-label="Espacio de Redacción para ${escapeHtml(incId)}">
          <div class="agent-panel-header">
            <div class="phase-tabs" role="tablist" aria-label="Fases de comunicación">
              <button type="button" class="phase-tab-btn ${activePhase === 'apertura' ? 'active' : ''}" data-phase="apertura" data-inc="${escapeHtml(incId)}">Apertura ${hasAp ? '✅' : '⚠️'}</button>
              <button type="button" class="phase-tab-btn ${activePhase === 'seguimiento' ? 'active' : ''}" data-phase="seguimiento" data-inc="${escapeHtml(incId)}">Seguimiento ${hasSeg ? '✅' : '⏳'}</button>
              <button type="button" class="phase-tab-btn ${activePhase === 'cierre' ? 'active' : ''}" data-phase="cierre" data-inc="${escapeHtml(incId)}">Cierre ${hasCie ? '✅' : '🏁'}</button>
            </div>
            <div style="display:flex; align-items:center; gap:8px;">
              <button type="button" class="im-btn im-btn-secondary im-btn-sm btn-suggest-draft" data-inc="${escapeHtml(incId)}" title="Autocompletar redacción con IA según reglas Orange (≤90 / ≤30 palabras)">
                <span aria-hidden="true">✨</span> Sugerir Borrador IA
              </button>
              <span style="font-size:11px; color:var(--im-text-muted);">Agente: <strong>incident-reporter</strong> (≤90 y ≤30 palabras)</span>
              <button type="button" class="im-btn im-btn-secondary im-btn-sm btn-close-report" data-inc="${escapeHtml(incId)}" title="Plegar panel de reportes">
                <span aria-hidden="true">▲</span> Plegar
              </button>
            </div>
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
                <button type="button" class="im-btn im-btn-secondary im-btn-sm btn-suggest-draft-inline" data-inc="${escapeHtml(incId)}" title="Autocompletar redacción con IA según reglas Orange (≤90 / ≤30 palabras)">
                  <span aria-hidden="true">✨</span> Sugerir Borrador IA
                </button>
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
      </div>
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

    return `Actúa como el agente incident-reporter de Orange para la fase de ${phase.toUpperCase()}.
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
    const activePhase = state.activePhases[incId] || 'apertura';

    // Elementos del Asistente de Ingesta Oficial
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

    // 0. Botón Volver al Triaje
    const toTriageBtn = card.querySelector('.btn-card-to-triage');
    if (toTriageBtn) {
      toTriageBtn.addEventListener('click', () => {
        setPresentationMode('triage');
      });
    }

    // 0.1 Selector de Estado Operativo en la cabecera de la tarjeta
    const statusSelect = card.querySelector('select[data-action="change-operational-status"]');
    if (statusSelect) {
      statusSelect.addEventListener('change', (e) => {
        const newStatus = e.target.value;
        StateManager.setStatus(incId, newStatus);
        showToast(`${incId}: Estado cambiado a ${getOperationalStatusLabel(newStatus)}`, 'success');
        loadData(false);
      });
    }

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

        // Cargar texto de la nueva fase seleccionada si está en StateManager o en inc.mensajes_ejecutivos
        const phaseCustomMsg = StateManager.getCustomMessage(incId, selectedPhase);
        const phaseIncMsg = inc.mensajes_ejecutivos && inc.mensajes_ejecutivos[selectedPhase];
        if (compTextarea) compTextarea.value = phaseCustomMsg?.completo || phaseIncMsg?.completo || '';
        if (brevTextarea) brevTextarea.value = phaseCustomMsg?.breve || phaseIncMsg?.breve || '';
        updateWordCounters();
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

    // 2.1 Enlace de Incidencia (INCXXXXX) -> Abre Resumen IA
    const incidentIdLink = card.querySelector('.incident-id-link');
    if (incidentIdLink) {
      incidentIdLink.addEventListener('click', (e) => {
        e.preventDefault();
        if (typeof window.openResumenIA === 'function') {
          window.openResumenIA(incId);
        } else if (window.ResumenIAModal && typeof window.ResumenIAModal.open === 'function') {
          window.ResumenIAModal.open(incId);
        } else {
          showToast('El visor de Epsilon IA no está disponible en este momento.', 'error');
        }
      });
    }

    // 3. Botón Modal Epsilon IA
    const epsilonBtn = card.querySelector('.btn-open-epsilon');
    if (epsilonBtn) {
      epsilonBtn.addEventListener('click', () => {
        if (typeof window.openResumenIA === 'function') {
          window.openResumenIA(incId);
        } else if (window.ResumenIAModal && typeof window.ResumenIAModal.open === 'function') {
          window.ResumenIAModal.open(incId);
        } else {
          showToast('El visor de Epsilon IA no está disponible en este momento.', 'error');
        }
      });
    }

    // Restaurar borrador en memoria o mensaje persistido inicial
    if (state.ingestaDrafts[incId]) {
      if (compTextarea) compTextarea.value = state.ingestaDrafts[incId].completo || '';
      if (brevTextarea) brevTextarea.value = state.ingestaDrafts[incId].breve || '';
      updateWordCounters();
    } else {
      const customMsg = StateManager.getCustomMessage(incId, activePhase);
      const incMsg = inc.mensajes_ejecutivos && inc.mensajes_ejecutivos[activePhase];
      if (customMsg) {
        if (compTextarea && !compTextarea.value) compTextarea.value = customMsg.completo || '';
        if (brevTextarea && !brevTextarea.value) brevTextarea.value = customMsg.breve || '';
      } else if (incMsg) {
        if (compTextarea && !compTextarea.value) compTextarea.value = incMsg.completo || '';
        if (brevTextarea && !brevTextarea.value) brevTextarea.value = incMsg.breve || '';
      }
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
            // Avanzar automáticamente el estado en el flujo operativo
            let nextStatus = 'comunicada';
            if (currentPhase === 'seguimiento') nextStatus = 'en_seguimiento';
            else if (currentPhase === 'cierre') nextStatus = 'descartada';
            StateManager.setStatus(incId, nextStatus);

            showToast(`¡Mensaje oficial de ${currentPhase} guardado con éxito para ${incId}! Estado avanzado a ${getOperationalStatusLabel(nextStatus)}.`, 'success');
            announceSR(`Mensaje oficial guardado con éxito.`);
            // Limpiar borrador y refrescar
            delete state.ingestaDrafts[incId];
            await loadData(false);
          } else {
            throw new Error(data.error || 'Respuesta insatisfactoria del servidor.');
          }
        } catch (err) {
          console.error('Error guardando mensaje:', err);
          // Modo local/offline o contingencia: persistir en StateManager del cliente
          let nextStatus = 'comunicada';
          if (currentPhase === 'seguimiento') nextStatus = 'en_seguimiento';
          else if (currentPhase === 'cierre') nextStatus = 'descartada';
          StateManager.setCustomMessage(incId, currentPhase, compVal, brevVal);
          StateManager.setStatus(incId, nextStatus);
          delete state.ingestaDrafts[incId];
          showToast(`Mensaje guardado localmente en navegador y estado avanzado a ${getOperationalStatusLabel(nextStatus)}. Puedes copiar el comando CLI para persistir en backend.`, 'info');
          await loadData(false);
        } finally {
          saveOfficialBtn.disabled = false;
          saveOfficialBtn.innerHTML = origBtnText;
        }
      });
    }

    // 7. Acordeón del Asistente de Ingesta Oficial
    const toggleIngesta = card.querySelector(`#toggle-ingesta-${incId}`);
    const ingestaBody = card.querySelector(`#ingesta-body-${incId}`);
    const ingestaToggleIcon = card.querySelector('.ingesta-toggle-icon');
    if (toggleIngesta && ingestaBody) {
      toggleIngesta.addEventListener('click', () => {
        const isHidden = ingestaBody.style.display === 'none';
        ingestaBody.style.display = isHidden ? 'block' : 'none';
        if (ingestaToggleIcon) {
          ingestaToggleIcon.textContent = isHidden ? '▲' : '▼';
        }
      });
    }

    // 8. Botón Alternar Visibilidad del Panel de Reportes (US4)
    const toggleReportBtn = card.querySelector('.btn-toggle-report');
    const reportsWrapper = card.querySelector(`#reports-wrapper-${incId}`);
    if (toggleReportBtn && reportsWrapper) {
      toggleReportBtn.addEventListener('click', () => {
        const isCurrentlyHidden = reportsWrapper.classList.contains('collapsed') || reportsWrapper.hasAttribute('hidden') || reportsWrapper.style.display === 'none';
        if (isCurrentlyHidden) {
          reportsWrapper.classList.remove('collapsed');
          reportsWrapper.removeAttribute('hidden');
          reportsWrapper.style.display = 'flex';
          state.reportVisibility[incId] = true;
          toggleReportBtn.setAttribute('aria-expanded', 'true');
          toggleReportBtn.innerHTML = '<span aria-hidden="true">▲</span> Ocultar Reportes';
        } else {
          reportsWrapper.classList.add('collapsed');
          reportsWrapper.setAttribute('hidden', '');
          reportsWrapper.style.display = 'none';
          state.reportVisibility[incId] = false;
          toggleReportBtn.setAttribute('aria-expanded', 'false');
          toggleReportBtn.innerHTML = `<span aria-hidden="true">📄</span> ${inc.is_pending ? '✍️ Redactar / Ver Reportes' : '📄 Ver Reportes'}`;
        }
      });
    }

    const closeReportBtns = card.querySelectorAll('.btn-close-report');
    closeReportBtns.forEach((btn) => {
      btn.addEventListener('click', () => {
        if (reportsWrapper) {
          reportsWrapper.classList.add('collapsed');
          reportsWrapper.setAttribute('hidden', '');
          reportsWrapper.style.display = 'none';
          state.reportVisibility[incId] = false;
        }
        if (toggleReportBtn) {
          toggleReportBtn.setAttribute('aria-expanded', 'false');
          toggleReportBtn.innerHTML = `<span aria-hidden="true">📄</span> ${inc.is_pending ? '✍️ Redactar / Ver Reportes' : '📄 Ver Reportes'}`;
        }
      });
    });

    // 9. Botón Copiar Reporte de Emergencia (4 Bloques Normalizados) (US4)
    const copyReportBtn = card.querySelector('.btn-copy-report');
    if (copyReportBtn) {
      copyReportBtn.addEventListener('click', async () => {
        const reportContentEl = card.querySelector(`#report-content-${incId}`);
        const reportText = (reportContentEl ? reportContentEl.textContent : '') ||
          inc.reporte_emergencia ||
          generate4BlockEmergencyReport(inc, inc.minutos_desde_apertura || 0);

        try {
          await navigator.clipboard.writeText(reportText);
          const origHtml = copyReportBtn.innerHTML;
          copyReportBtn.innerHTML = '<span aria-hidden="true">✅</span> ¡Reporte copiado!';
          copyReportBtn.style.background = 'var(--im-green-success)';
          copyReportBtn.style.borderColor = 'var(--im-green-success)';
          announceSR(`Reporte de emergencia para ${incId} copiado al portapapeles.`);
          showToast(`¡Reporte oficial de emergencia copiado al portapapeles!`, 'success');
          setTimeout(() => {
            copyReportBtn.innerHTML = origHtml;
            copyReportBtn.style.background = '';
            copyReportBtn.style.borderColor = '';
          }, 2000);
        } catch (err) {
          showToast('No se pudo copiar el reporte: ' + err.message, 'error');
        }
      });
    }

    // 10. Botón Sugerir Borrador IA (Genera redacción ejecutiva oficial ≤90 / ≤30 palabras)
    const suggestDraftBtns = card.querySelectorAll('.btn-suggest-draft, .btn-suggest-draft-inline');
    suggestDraftBtns.forEach((btn) => {
      btn.addEventListener('click', () => {
        const currentPhase = state.activePhases[incId] || 'apertura';
        const draft = generateAiDraftForIncident(inc, currentPhase);
        if (compTextarea) compTextarea.value = draft.completo;
        if (brevTextarea) brevTextarea.value = draft.breve;
        updateWordCounters();
        announceSR(`Borrador IA para fase ${currentPhase} generado.`);
        showToast(`✨ ¡Borrador IA (${currentPhase}) generado conforme a normas Orange!`, 'success');
      });
    });

    // 11. Delegación de eventos para Copiar Solicitud Reclasificación y Convocatoria War Room
    card.addEventListener('click', async (e) => {
      const warBtn = e.target.closest('.btn-copy-teams-warroom');
      if (warBtn) {
        e.stopPropagation();
        const mins = inc.apertura_epoch_ms
          ? Math.max(0, Math.floor((Date.now() - inc.apertura_epoch_ms) / 60000))
          : (inc.minutos_desde_apertura || 0);
        const text = buildTeamsWarRoomText(inc, mins);
        try {
          await navigator.clipboard.writeText(text);
          const origHtml = warBtn.innerHTML;
          warBtn.innerHTML = '<span aria-hidden="true">✅</span> ¡Convocatoria copiada!';
          warBtn.style.background = 'var(--im-green-success)';
          warBtn.style.borderColor = 'var(--im-green-success)';
          warBtn.style.color = '#fff';
          announceSR(`Convocatoria Teams War Room para ${incId} copiada.`);
          showToast(`¡Convocatoria War Room copiada! Pégala en el canal de Teams de audio.`, 'success');
          setTimeout(() => {
            warBtn.innerHTML = origHtml;
            warBtn.style.background = '';
            warBtn.style.borderColor = '';
            warBtn.style.color = '';
          }, 2000);
        } catch (err) {
          showToast('Error al copiar: ' + err.message, 'error');
        }
        return;
      }

      const reclassBtn = e.target.closest('.btn-copy-remedy-reclass');
      if (reclassBtn) {
        e.stopPropagation();
        const text = buildRemedyReclassificationText(inc);
        try {
          await navigator.clipboard.writeText(text);
          const origHtml = reclassBtn.innerHTML;
          reclassBtn.innerHTML = '<span aria-hidden="true">✅</span> ¡Solicitud copiada!';
          reclassBtn.style.background = 'var(--im-green-success)';
          reclassBtn.style.borderColor = 'var(--im-green-success)';
          reclassBtn.style.color = '#fff';
          announceSR(`Solicitud de reclasificación para ${incId} copiada.`);
          showToast(`¡Texto formal de reclasificación copiado! Pégalo en el log de Remedy.`, 'success');
          setTimeout(() => {
            reclassBtn.innerHTML = origHtml;
            reclassBtn.style.background = '';
            reclassBtn.style.borderColor = '';
            reclassBtn.style.color = '';
          }, 2000);
        } catch (err) {
          showToast('Error al copiar: ' + err.message, 'error');
        }
        return;
      }
    });
  }

  // --- Manejo de Filtros y Vistas ---

  function updateResetButtonVisibility() {
    if (!dom.btnResetFilters) return;
    const hasSearch = Boolean(state.filters.search && state.filters.search.trim().length > 0);
    const hasSeverity = state.filters.severity !== 'all';
    const hasProcess = state.filters.process !== 'all';
    const hasCommPhase = Boolean(state.filters.commPhase && state.filters.commPhase !== 'all');
    const hasDiscrepancies = Boolean(state.filters.onlyDiscrepancies);
    const hasNonDefaultTriage = state.presentationMode === 'triage' && (state.triageFilter !== 'urgent' || state.activeView !== 'pending');
    const hasNonDefaultCards = state.presentationMode === 'cards' && state.activeView !== 'pending';

    const isFiltered = hasSearch || hasSeverity || hasProcess || hasCommPhase || hasDiscrepancies || hasNonDefaultTriage || hasNonDefaultCards;
    dom.btnResetFilters.style.display = isFiltered ? 'inline-flex' : 'none';
  }

  function syncTriageChipActive(filterKey) {
    state.triageFilter = filterKey;
    const chipsMap = {
      urgent: dom.chipUrgent,
      pending: dom.chipPending,
      escalation: dom.chipEscalation,
      discrepancy: dom.chipDiscrepancy,
      missing_comm: dom.chipMissingComm,
      all: dom.chipAll
    };
    Object.values(chipsMap).forEach((chip) => {
      if (chip) chip.classList.remove('active');
    });
    if (chipsMap[filterKey]) {
      chipsMap[filterKey].classList.add('active');
    }
  }

  function syncViewTabActive(tabKey) {
    state.activeView = tabKey;
    if (tabKey === 'pending') {
      if (dom.tabViewPending) {
        dom.tabViewPending.classList.add('active');
        dom.tabViewPending.setAttribute('aria-selected', 'true');
      }
      if (dom.tabViewAll) {
        dom.tabViewAll.classList.remove('active');
        dom.tabViewAll.setAttribute('aria-selected', 'false');
      }
    } else {
      if (dom.tabViewAll) {
        dom.tabViewAll.classList.add('active');
        dom.tabViewAll.setAttribute('aria-selected', 'true');
      }
      if (dom.tabViewPending) {
        dom.tabViewPending.classList.remove('active');
        dom.tabViewPending.setAttribute('aria-selected', 'false');
      }
    }
  }

  function resetAllFilters() {
    state.filters.search = '';
    state.filters.severity = 'all';
    state.filters.process = 'all';
    state.filters.commPhase = 'all';
    state.filters.onlyDiscrepancies = false;

    if (dom.filterSearchInput) dom.filterSearchInput.value = '';
    if (dom.filterSeveritySelect) dom.filterSeveritySelect.value = 'all';
    if (dom.filterProcessSelect) dom.filterProcessSelect.value = 'all';
    if (dom.filterCommSelect) dom.filterCommSelect.value = 'all';
    if (dom.filterOnlyDiscrepancies) dom.filterOnlyDiscrepancies.checked = false;

    syncTriageChipActive('urgent');
    syncViewTabActive('pending');

    updateResetButtonVisibility();
    renderTriageView();
    renderQueue();
    announceSR('Filtros restablecidos a la vista inicial por defecto');
    showToast('Filtros restablecidos a la vista inicial', 'info');
  }

  function setupEventListeners() {
    // 0. Selector de Modo Principal: Triaje vs Tarjetas Detalladas
    if (dom.tabPresTriage) {
      dom.tabPresTriage.addEventListener('click', () => {
        setPresentationMode('triage');
        updateResetButtonVisibility();
      });
    }

    if (dom.tabPresCards) {
      dom.tabPresCards.addEventListener('click', () => {
        setPresentationMode('cards');
        updateResetButtonVisibility();
      });
    }

    if (dom.btnBackToTriage) {
      dom.btnBackToTriage.addEventListener('click', () => {
        setPresentationMode('triage');
        updateResetButtonVisibility();
      });
    }

    // Chips de Filtrado Rápido de Triaje
    const triageChips = [
      { el: dom.chipUrgent, filter: 'urgent' },
      { el: dom.chipPending, filter: 'pending' },
      { el: dom.chipEscalation, filter: 'escalation' },
      { el: dom.chipDiscrepancy, filter: 'discrepancy' },
      { el: dom.chipMissingComm, filter: 'missing_comm' },
      { el: dom.chipAll, filter: 'all' }
    ];

    triageChips.forEach(({ el, filter }) => {
      if (el) {
        el.addEventListener('click', () => {
          syncTriageChipActive(filter);
          if (filter === 'all') {
            syncViewTabActive('all');
          } else if (filter === 'pending' || filter === 'urgent') {
            syncViewTabActive('pending');
          }
          updateResetButtonVisibility();
          renderTriageView();
          renderQueue();
        });
      }
    });

    // 1. Selector de Sub-Vistas: Solo Pendientes vs Todas
    if (dom.tabViewPending) {
      dom.tabViewPending.addEventListener('click', () => {
        syncViewTabActive('pending');
        syncTriageChipActive('pending');
        updateResetButtonVisibility();
        renderTriageView();
        renderQueue();
      });
    }

    if (dom.tabViewAll) {
      dom.tabViewAll.addEventListener('click', () => {
        syncViewTabActive('all');
        syncTriageChipActive('all');
        updateResetButtonVisibility();
        renderTriageView();
        renderQueue();
      });
    }

    // 2. Buscador en tiempo real con Debounce
    if (dom.filterSearchInput) {
      dom.filterSearchInput.addEventListener('input', (e) => {
        clearTimeout(state.searchDebounceTimer);
        state.searchDebounceTimer = setTimeout(() => {
          state.filters.search = e.target.value;
          updateResetButtonVisibility();
          renderTriageView();
          renderQueue();
        }, 150);
      });
    }

    // 3. Filtro Severidad
    if (dom.filterSeveritySelect) {
      dom.filterSeveritySelect.addEventListener('change', (e) => {
        state.filters.severity = e.target.value;
        updateResetButtonVisibility();
        renderTriageView();
        renderQueue();
      });
    }

    // 4. Filtro Proceso
    if (dom.filterProcessSelect) {
      dom.filterProcessSelect.addEventListener('change', (e) => {
        state.filters.process = e.target.value;
        updateResetButtonVisibility();
        renderTriageView();
        renderQueue();
      });
    }

    // 4b. Filtro Comunicación Oficial (Apertura / Seguimiento / Cierre)
    if (dom.filterCommSelect) {
      dom.filterCommSelect.addEventListener('change', (e) => {
        state.filters.commPhase = e.target.value;
        updateResetButtonVisibility();
        renderTriageView();
        renderQueue();
      });
    }

    // 5. Filtro Solo Discrepancias
    if (dom.filterOnlyDiscrepancies) {
      dom.filterOnlyDiscrepancies.addEventListener('change', (e) => {
        state.filters.onlyDiscrepancies = e.target.checked;
        updateResetButtonVisibility();
        renderTriageView();
        renderQueue();
      });
    }

    // 5b. Botón Limpiar Filtros
    if (dom.btnResetFilters) {
      dom.btnResetFilters.addEventListener('click', () => {
        resetAllFilters();
      });
    }

    // 5c. Clics Interactivos en Tarjetas de KPIs
    function handleKpiCardClick(cardKey) {
      if (cardKey === 'pending') {
        syncTriageChipActive('urgent');
        syncViewTabActive('pending');
      } else if (cardKey === 'completed') {
        syncTriageChipActive('all');
        syncViewTabActive('all');
      } else if (cardKey === 'total') {
        syncTriageChipActive('all');
        syncViewTabActive('all');
      } else if (cardKey === 'discrepancy') {
        if (state.presentationMode === 'triage') {
          syncTriageChipActive('discrepancy');
        } else {
          state.filters.onlyDiscrepancies = true;
          if (dom.filterOnlyDiscrepancies) dom.filterOnlyDiscrepancies.checked = true;
        }
      } else if (cardKey === 'escalation') {
        if (state.presentationMode !== 'triage') {
          setPresentationMode('triage');
        }
        syncTriageChipActive('escalation');
      }
      updateResetButtonVisibility();
      renderTriageView();
      renderQueue();
    }

    if (dom.kpiCardPending) {
      dom.kpiCardPending.addEventListener('click', () => handleKpiCardClick('pending'));
      dom.kpiCardPending.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleKpiCardClick('pending'); }
      });
    }

    if (dom.kpiCardCompleted) {
      dom.kpiCardCompleted.addEventListener('click', () => handleKpiCardClick('completed'));
      dom.kpiCardCompleted.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleKpiCardClick('completed'); }
      });
    }

    if (dom.kpiCardTotal) {
      dom.kpiCardTotal.addEventListener('click', () => handleKpiCardClick('total'));
      dom.kpiCardTotal.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleKpiCardClick('total'); }
      });
    }

    if (dom.kpiP1Count) {
      dom.kpiP1Count.addEventListener('click', (e) => {
        e.stopPropagation();
        state.filters.severity = 'P1';
        if (dom.filterSeveritySelect) dom.filterSeveritySelect.value = 'P1';
        updateResetButtonVisibility();
        renderTriageView();
        renderQueue();
      });
    }

    if (dom.kpiP2Count) {
      dom.kpiP2Count.addEventListener('click', (e) => {
        e.stopPropagation();
        state.filters.severity = 'P2';
        if (dom.filterSeveritySelect) dom.filterSeveritySelect.value = 'P2';
        updateResetButtonVisibility();
        renderTriageView();
        renderQueue();
      });
    }

    if (dom.kpiCardSeverity) {
      dom.kpiCardSeverity.addEventListener('click', () => {
        const next = state.filters.severity === 'all' ? 'P1' : (state.filters.severity === 'P1' ? 'P2' : 'all');
        state.filters.severity = next;
        if (dom.filterSeveritySelect) dom.filterSeveritySelect.value = next;
        updateResetButtonVisibility();
        renderTriageView();
        renderQueue();
      });
      dom.kpiCardSeverity.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          dom.kpiCardSeverity.click();
        }
      });
    }

    if (dom.kpiCardDiscrepancies) {
      dom.kpiCardDiscrepancies.addEventListener('click', () => handleKpiCardClick('discrepancy'));
      dom.kpiCardDiscrepancies.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleKpiCardClick('discrepancy'); }
      });
    }

    if (dom.kpiCardEscalation) {
      dom.kpiCardEscalation.addEventListener('click', () => handleKpiCardClick('escalation'));
      dom.kpiCardEscalation.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleKpiCardClick('escalation'); }
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

    // 8. Selector de Modo de Consola (Emergencias vs Compacto) (US4)
    if (dom.btnToggleEmergencyMode) {
      dom.btnToggleEmergencyMode.addEventListener('click', () => {
        state.viewMode = state.viewMode === 'emergency' ? 'compact' : 'emergency';
        if (dom.toggleEmergencyModeLabel) {
          dom.toggleEmergencyModeLabel.textContent = state.viewMode === 'emergency'
            ? 'Modo Emergencias: Activo'
            : 'Modo Compacto: Activo';
        }
        if (state.viewMode === 'emergency') {
          dom.btnToggleEmergencyMode.classList.remove('im-btn-secondary');
          dom.btnToggleEmergencyMode.classList.add('im-btn-primary');
          showToast('Vista de Emergencias activada (reportes y gobernanza extendidos)', 'info');
        } else {
          dom.btnToggleEmergencyMode.classList.remove('im-btn-primary');
          dom.btnToggleEmergencyMode.classList.add('im-btn-secondary');
          showToast('Vista Compacta activada', 'info');
        }
        renderQueue();
      });
    }

    // 9. Modal de Protocolo RACI y Contactos (US5)
    function openRaciModal() {
      if (dom.raciModalBackdrop) {
        dom.raciModalBackdrop.style.display = 'flex';
        dom.raciModalBackdrop.setAttribute('aria-hidden', 'false');
        if (dom.btnCloseRaci) dom.btnCloseRaci.focus();
      }
    }

    function closeRaciModal() {
      if (dom.raciModalBackdrop) {
        dom.raciModalBackdrop.style.display = 'none';
        dom.raciModalBackdrop.setAttribute('aria-hidden', 'true');
        if (dom.btnOpenRaci) dom.btnOpenRaci.focus();
      }
    }

    if (dom.btnOpenRaci) {
      dom.btnOpenRaci.addEventListener('click', openRaciModal);
    }

    if (dom.btnCloseRaci) {
      dom.btnCloseRaci.addEventListener('click', closeRaciModal);
    }

    if (dom.raciModalBackdrop) {
      dom.raciModalBackdrop.addEventListener('click', (e) => {
        if (e.target === dom.raciModalBackdrop) {
          closeRaciModal();
        }
      });
    }

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && dom.raciModalBackdrop && dom.raciModalBackdrop.style.display !== 'none') {
        closeRaciModal();
      }
    });
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
    startLiveTimersLoop();
    setPresentationMode('triage');
    loadData(true);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();

