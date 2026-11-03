// Editor integration with backend
// Handles loading, saving, auto-saving, concurrency control, and conflict resolution
// Compatible with multi-user environments

console.log('[editor.js] Script loaded');

const ReportEditor = {
  currentReportId: null,
  lastLoadedUpdatedAt: null,
  autoSaveTimer: null,
  heartbeatTimer: null,
  isDirty: false,
  isSaving: false,
  isViewMode: false,
  hasConflict: false,
  isAutoSavePaused: false,
  conflictingRemoteReport: null,
  HEARTBEAT_INTERVAL: 15000, // 15 segundos

  async init() {
    const params = new URLSearchParams(window.location.search);
    const reportId = params.get('report');
    this.isViewMode = params.has('view');

    console.log('[ReportEditor] URL params:', { reportId, fullUrl: window.location.href, isViewMode: this.isViewMode });

    if (reportId) {
      console.log('[ReportEditor] Cargando informe:', reportId);
      await this.loadReport(reportId);
      if (!this.isViewMode) {
        this.startHeartbeat();
      }
    } else {
      console.log('[ReportEditor] Nuevo informe (sin parámetro)');
      this.initializeNew();
    }

    // Setup auto-save on changes (only if not in view mode)
    if (!this.isViewMode) {
      this.setupAutoSave();
      this.setupKeyboardShortcuts();
      this.setupBeforeUnload();
      this.enableEditControls();
    } else {
      this.disableEditControls();
    }
  },

  disableEditControls() {
    console.log('[ReportEditor] Desactivando controles de edición (modo visualización)');
    const inputs = document.querySelectorAll('input, textarea, select');
    inputs.forEach(el => {
      if (el.id !== 'reportStatusSelect') el.disabled = true;
    });

    const buttons = document.querySelectorAll('button');
    buttons.forEach(btn => {
      if (!btn.textContent.includes('Volver') && !btn.textContent.includes('←')) {
        btn.disabled = true;
        btn.style.opacity = '0.5';
      }
    });

    const reportTitle = document.getElementById('reportTitle');
    if (reportTitle) reportTitle.textContent += ' (Visualización)';

    const statusSelect = document.getElementById('reportStatusSelect');
    if (statusSelect) statusSelect.disabled = true;
  },

  enableEditControls() {
    console.log('[ReportEditor] Activando controles de edición');
    const inputs = document.querySelectorAll('input, textarea, select');
    inputs.forEach(el => el.disabled = false);

    const buttons = document.querySelectorAll('button');
    buttons.forEach(btn => {
      btn.disabled = false;
      btn.style.opacity = '1';
    });
  },

  async loadReport(reportId) {
    try {
      console.log(`[loadReport] Cargando informe ${reportId}...`);
      const report = await ApiClient.getReport(reportId);
      console.log(`[loadReport] Informe cargado:`, report);
      this.currentReportId = reportId;
      this.lastLoadedUpdatedAt = report.updatedAt || null;

      // Reset conflict state on fresh load
      this.hasConflict = false;
      this.isAutoSavePaused = false;
      this.conflictingRemoteReport = null;
      this.hideConflictBanner();

      // Update title and status
      const reportTitle = document.getElementById('reportTitle');
      if (reportTitle) reportTitle.textContent = reportId;

      // Load metadata
      const metaYear = document.getElementById('metaYear');
      const metaWeek = document.getElementById('metaWeek');
      const metaRange = document.getElementById('metaRange');
      const metaDept = document.getElementById('metaDept');

      if (metaYear) metaYear.value = report.year;
      if (metaWeek) metaWeek.value = report.week;
      if (metaRange) metaRange.value = report.range || '';
      if (metaDept) metaDept.value = report.dept || '';

      // Load status selector
      const statusSelect = document.getElementById('reportStatusSelect');
      if (statusSelect) {
        statusSelect.value = report.status || 'draft';
        statusSelect.style.display = 'block';
      }

      // Load incidents into App state
      if (typeof App !== 'undefined' && App.state) {
        App.state.meta = {
          year: report.year,
          week: report.week,
          range: report.range || '',
          dept: report.dept || '',
        };
        App.state.incidents = JSON.parse(JSON.stringify(report.incidents || []));
        App.state.openIdx = 0;
        App.renderSidebarList();
        App.renderDeck();
        App.fit();

        // Save isolated snapshot
        this.persistLocalSnapshot();
      }

      this.isDirty = false;
      console.log(`✓ Informe ${reportId} cargado (${(report.incidents || []).length} incidencias) - updatedAt: ${this.lastLoadedUpdatedAt}`);
      this.setSaveStatus('saved');
    } catch (error) {
      console.error('Error cargando informe:', error);
      if (window.Toast) Toast.error('Error al cargar el informe: ' + error.message);
      else alert('Error al cargar el informe: ' + error.message);
    }
  },

  setSaveStatus(state, msg) {
    const dot = document.getElementById('saveStatusDot');
    const text = document.getElementById('saveStatusText');
    const badge = document.getElementById('saveStatusBadge');
    if (!dot || !text || !badge) return;

    badge.classList.remove('badge-pulse');

    if (state === 'saving') {
      dot.style.background = '#FF7900';
      dot.style.boxShadow = '0 0 6px rgba(255,121,0,0.6)';
      text.textContent = 'Guardando...';
      badge.style.borderColor = 'rgba(255,121,0,0.4)';
    } else if (state === 'saved') {
      dot.style.background = '#28A745';
      dot.style.boxShadow = 'none';
      const timeStr = msg || new Date().toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
      text.textContent = `Guardado (${timeStr})`;
      badge.style.borderColor = '#3C3934';
    } else if (state === 'error') {
      dot.style.background = '#D43A2F';
      dot.style.boxShadow = '0 0 6px rgba(212,58,47,0.6)';
      text.textContent = msg || 'Error al guardar';
      badge.style.borderColor = 'rgba(212,58,47,0.5)';
    } else if (state === 'pending') {
      dot.style.background = '#FFC107';
      dot.style.boxShadow = 'none';
      text.textContent = 'Guardando cambios...';
      badge.style.borderColor = 'rgba(255,193,7,0.4)';
    } else if (state === 'conflict') {
      dot.style.background = '#D43A2F';
      dot.style.boxShadow = '0 0 8px rgba(212,58,47,0.8)';
      text.textContent = msg || '⚠️ Conflicto detectado';
      badge.style.borderColor = '#D43A2F';
      badge.classList.add('badge-pulse');
    }
  },

  initializeNew() {
    this.currentReportId = null;
    this.lastLoadedUpdatedAt = null;
    this.hasConflict = false;
    this.isAutoSavePaused = false;
    document.getElementById('reportTitle').textContent = 'Nuevo informe';
    const badge = document.getElementById('reportStatusBadge');
    if (badge) badge.style.display = 'none';
    this.setSaveStatus('saved', 'Nuevo');
  },

  setupAutoSave() {
    // Mark as dirty on metadata inputs (input and change)
    const metaInputs = document.querySelectorAll('#metaYear, #metaWeek, #metaRange, #metaDept');
    metaInputs.forEach(input => {
      const handler = () => {
        this.isDirty = true;
        this.scheduleAutoSave();
      };
      input.addEventListener('input', handler);
      input.addEventListener('change', handler);
    });

    // Mark as dirty on incident changes
    document.addEventListener('incident-changed', () => {
      this.isDirty = true;
      this.scheduleAutoSave();
    });
  },

  setupKeyboardShortcuts() {
    window.addEventListener('keydown', (e) => {
      // Ctrl+S o Cmd+S: Guardado inmediato
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
        e.preventDefault();
        this.saveReport();
        return;
      }

      // Alt+Up / Alt+Down: Reordenación de la incidencia activa
      if (e.altKey && (e.key === 'ArrowUp' || e.key === 'ArrowDown')) {
        e.preventDefault();
        if (typeof App !== 'undefined' && App.state) {
          const curIdx = App.state.openIdx;
          const incidents = App.state.incidents || [];
          if (curIdx >= 0 && curIdx < incidents.length) {
            const dir = e.key === 'ArrowUp' ? -1 : 1;
            const targetIdx = curIdx + dir;
            if (targetIdx >= 0 && targetIdx < incidents.length) {
              App.moveIncident(curIdx, dir);
              if (window.Toast) {
                Toast.info(`Incidencia movida a posición ${targetIdx + 1}`, 1200);
              }
            }
          }
        }
      }
    });
  },

  setupBeforeUnload() {
    window.addEventListener('beforeunload', (e) => {
      if (this.isDirty) {
        e.preventDefault();
        e.returnValue = 'Hay modificaciones no guardadas en el informe.';
      }
    });
  },

  // ========== Heartbeat / Concurrency Collision Detection ==========

  startHeartbeat() {
    this.stopHeartbeat();
    this.heartbeatTimer = setInterval(() => {
      this.checkRemoteChanges();
    }, this.HEARTBEAT_INTERVAL);
  },

  stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  },

  async checkRemoteChanges() {
    if (!this.currentReportId || this.isViewMode || this.isSaving) return;

    try {
      const remote = await ApiClient.getReport(this.currentReportId);
      if (!remote || !remote.updatedAt) return;

      const remoteTime = new Date(remote.updatedAt).getTime();
      const localLoadedTime = this.lastLoadedUpdatedAt ? new Date(this.lastLoadedUpdatedAt).getTime() : 0;

      // Si el servidor tiene una versión posterior a la que cargamos
      if (remote.updatedAt !== this.lastLoadedUpdatedAt && remoteTime > localLoadedTime + 1000) {
        console.warn(`[ReportEditor] Detectada versión remota más reciente (${remote.updatedAt} vs local ${this.lastLoadedUpdatedAt})`);

        if (!this.isDirty) {
          // El usuario NO tiene cambios pendientes: actualizar limpiamente
          console.log('[ReportEditor] Sin cambios locales pendientes. Sincronizando con versión remota automáticamente...');
          this.lastLoadedUpdatedAt = remote.updatedAt;

          if (typeof App !== 'undefined' && App.state) {
            App.state.meta = {
              year: remote.year,
              week: remote.week,
              range: remote.range || '',
              dept: remote.dept || '',
            };
            App.state.incidents = JSON.parse(JSON.stringify(remote.incidents || []));
            App.renderSidebarList();
            App.renderDeck();
            App.fit();
            this.persistLocalSnapshot();
          }

          const timeFormatted = new Date(remote.updatedAt).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
          this.setSaveStatus('saved', `Sync ${timeFormatted}`);
          if (window.Toast) {
            Toast.info(`Informe sincronizado con la versión remota (${timeFormatted})`, 2500);
          }
        } else {
          // El usuario SÍ tiene cambios pendientes: ¡Conflicto de concurrencia detectado!
          console.warn('[ReportEditor] ¡Conflicto detectado! El usuario tiene cambios locales y el servidor ha cambiado.');
          this.hasConflict = true;
          this.isAutoSavePaused = true;
          this.conflictingRemoteReport = remote;
          this.setSaveStatus('conflict', 'Modificación simultánea');
          this.showConflictBanner(remote);
        }
      }
    } catch (err) {
      console.warn('[ReportEditor] Heartbeat check error:', err.message);
    }
  },

  showConflictBanner(remoteReport) {
    const banner = document.getElementById('conflictAlertBanner');
    const msg = document.getElementById('conflictAlertMsg');
    if (!banner) return;

    const timeStr = remoteReport?.updatedAt
      ? new Date(remoteReport.updatedAt).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })
      : 'recientemente';

    if (msg) {
      msg.textContent = `Otro usuario guardó cambios en este informe a las ${timeStr}. El guardado automático se ha pausado para proteger tu trabajo.`;
    }
    banner.style.display = 'flex';
  },

  hideConflictBanner() {
    const banner = document.getElementById('conflictAlertBanner');
    if (banner) banner.style.display = 'none';
  },

  scheduleAutoSave() {
    if (this.isAutoSavePaused || this.hasConflict) {
      console.log('[scheduleAutoSave] Autoguardado pausado debido a conflicto activo.');
      this.setSaveStatus('conflict', 'Autoguardado pausado');
      return;
    }
    clearTimeout(this.autoSaveTimer);
    this.setSaveStatus('pending');
    this.autoSaveTimer = setTimeout(() => this.autoSave(), 1500);
  },

  async autoSave() {
    if (!this.isDirty || !this.currentReportId || this.isSaving) return;
    if (this.isAutoSavePaused || this.hasConflict) return;

    await this.performSave({ isAuto: true });
  },

  async saveReport(options = {}) {
    if (!this.currentReportId) {
      // Creación de nuevo informe
      await this.createNewReport();
      return;
    }

    if (this.hasConflict && !options.force) {
      this.openConflictModal();
      return;
    }

    await this.performSave({ force: !!options.force, isAuto: false });
  },

  async performSave(options = {}) {
    if (this.isSaving) return;
    this.isSaving = true;

    try {
      this.setSaveStatus('saving');
      const update = {
        range: document.getElementById('metaRange')?.value || '',
        dept: document.getElementById('metaDept')?.value || '',
        incidents: App?.state?.incidents || [],
      };

      const updateOpts = {
        expectedUpdatedAt: options.force ? undefined : this.lastLoadedUpdatedAt,
        force: !!options.force,
      };

      const saved = await ApiClient.updateReport(this.currentReportId, update, updateOpts);

      this.lastLoadedUpdatedAt = saved.updatedAt;
      this.isDirty = false;
      this.hasConflict = false;
      this.isAutoSavePaused = false;
      this.conflictingRemoteReport = null;
      this.hideConflictBanner();
      this.setSaveStatus('saved');
      this.persistLocalSnapshot();

      console.log(`✓ Informe guardado (${options.force ? 'Forzado' : options.isAuto ? 'Auto' : 'Manual'})`);
      if (!options.isAuto) {
        if (window.Toast) Toast.success('Informe guardado correctamente');
        else alert('✓ Informe guardado');
      }
    } catch (error) {
      console.error('Error al guardar informe:', error);

      if (error.status === 409 || error.data?.code === 'CONCURRENT_MODIFICATION') {
        // Conflicto de modificación concurrente retornado por el servidor
        this.hasConflict = true;
        this.isAutoSavePaused = true;
        this.conflictingRemoteReport = error.data?.server_report || (await ApiClient.getReport(this.currentReportId).catch(() => null));
        this.setSaveStatus('conflict', 'Conflicto detectado');
        this.showConflictBanner(this.conflictingRemoteReport);
        this.openConflictModal();
      } else {
        this.setSaveStatus('error', error.message || 'Error al guardar');
        if (window.Toast) Toast.error('Error al guardar: ' + error.message);
      }
    } finally {
      this.isSaving = false;
    }
  },

  async createNewReport() {
    try {
      this.setSaveStatus('saving');
      const report = {
        year: parseInt(document.getElementById('metaYear').value),
        week: parseInt(document.getElementById('metaWeek').value),
        range: document.getElementById('metaRange').value,
        dept: document.getElementById('metaDept').value,
        incidents: App.state.incidents,
        status: 'draft',
      };

      const created = await ApiClient.createReport(report);
      this.currentReportId = created.id;
      this.lastLoadedUpdatedAt = created.updatedAt;

      // Update URL and UI
      const url = new URL(window.location);
      url.searchParams.set('report', created.id);
      window.history.replaceState({}, '', url);

      const reportTitle = document.getElementById('reportTitle');
      if (reportTitle) reportTitle.textContent = created.id;

      const statusSelect = document.getElementById('reportStatusSelect');
      if (statusSelect) {
        statusSelect.value = 'draft';
        statusSelect.style.display = 'block';
      }

      this.setSaveStatus('saved');
      this.isDirty = false;
      this.startHeartbeat();
      if (window.Toast) Toast.success('Informe creado exitosamente');
      else alert('✓ Informe creado exitosamente');
    } catch (error) {
      this.setSaveStatus('error');
      if (window.Toast) Toast.error('Error al crear el informe: ' + error.message);
      else alert('Error al crear el informe: ' + error.message);
    }
  },

  async updateStatus(newStatus) {
    if (!this.currentReportId) {
      if (window.Toast) Toast.warning('Primero debes crear el informe');
      else alert('Primero debes crear el informe');
      return;
    }

    try {
      await ApiClient.updateReport(this.currentReportId, { status: newStatus }, { force: true });
      if (window.Toast) Toast.success(`Estado actualizado a ${newStatus}`);
      console.log(`✓ Estado cambiado a ${newStatus}`);
    } catch (error) {
      if (window.Toast) Toast.error('Error al cambiar estado: ' + error.message);
      else alert('Error al cambiar estado: ' + error.message);
      // Recargar para restaurar el estado anterior
      const statusSelect = document.getElementById('reportStatusSelect');
      if (statusSelect) {
        const report = await ApiClient.getReport(this.currentReportId);
        statusSelect.value = report.status;
      }
    }
  },

  // ========== Conflict Resolution Modal and Tools ==========

  openConflictModal() {
    const modal = document.getElementById('conflictModal');
    if (!modal) return;

    const localIncidents = App?.state?.incidents || [];
    const remote = this.conflictingRemoteReport || {};
    const remoteIncidents = remote.incidents || [];

    // Local summary
    document.getElementById('conflictLocalIncCount').textContent = localIncidents.length;
    document.getElementById('conflictLocalTime').textContent = new Date().toLocaleTimeString('es-ES');
    document.getElementById('conflictLocalRange').textContent = document.getElementById('metaRange')?.value || '—';

    // Remote summary
    document.getElementById('conflictRemoteIncCount').textContent = remoteIncidents.length;
    document.getElementById('conflictRemoteTime').textContent = remote.updatedAt
      ? new Date(remote.updatedAt).toLocaleTimeString('es-ES')
      : 'Desconocido';
    document.getElementById('conflictRemoteRange').textContent = remote.range || '—';

    // Difference analysis
    const diffContainer = document.getElementById('conflictDiffText');
    if (diffContainer) {
      const diffLines = [];
      if (localIncidents.length !== remoteIncidents.length) {
        diffLines.push(`• Cantidad de incidencias: local (${localIncidents.length}) vs servidor (${remoteIncidents.length}).`);
      }

      const localTickets = new Set(localIncidents.map(i => i.ticket || i.title).filter(Boolean));
      const remoteTickets = new Set(remoteIncidents.map(i => i.ticket || i.title).filter(Boolean));

      const onlyLocal = [...localTickets].filter(t => !remoteTickets.has(t));
      const onlyRemote = [...remoteTickets].filter(t => !localTickets.has(t));

      if (onlyLocal.length > 0) {
        diffLines.push(`• Incidencias creadas en tu borrador que no están en el servidor: ${onlyLocal.slice(0, 3).join(', ')}${onlyLocal.length > 3 ? '...' : ''}.`);
      }
      if (onlyRemote.length > 0) {
        diffLines.push(`• Incidencias añadidas en el servidor por otro usuario: ${onlyRemote.slice(0, 3).join(', ')}${onlyRemote.length > 3 ? '...' : ''}.`);
      }

      if (diffLines.length === 0) {
        diffLines.push('• Se modificaron campos de texto o detalles de incidencias entre ambas versiones.');
      }

      diffContainer.innerHTML = diffLines.map(l => `<div style="margin-bottom:3px;">${l}</div>`).join('');
    }

    modal.style.display = 'flex';
  },

  closeConflictModal() {
    const modal = document.getElementById('conflictModal');
    if (modal) modal.style.display = 'none';
  },

  downloadLocalBackup() {
    const payload = {
      meta: App?.state?.meta || {},
      incidents: App?.state?.incidents || [],
      savedAt: new Date().toISOString(),
      reportId: this.currentReportId,
    };

    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    a.href = url;
    a.download = `Borrador_${this.currentReportId || 'Nuevo'}_Local_${timestamp}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 1000);

    // Also persist in localStorage
    try {
      localStorage.setItem(`mo_backup_${this.currentReportId}_${timestamp}`, JSON.stringify(payload));
    } catch (e) {}

    if (window.Toast) Toast.success('Borrador local descargado con éxito.');
  },

  async resolveConflict(action) {
    if (action === 'reload') {
      // Auto-backup first
      try {
        localStorage.setItem(`mo_backup_${this.currentReportId}_before_reload`, JSON.stringify({
          meta: App?.state?.meta,
          incidents: App?.state?.incidents,
          date: new Date().toISOString(),
        }));
      } catch (e) {}

      this.closeConflictModal();
      await this.loadReport(this.currentReportId);
      if (window.Toast) Toast.success('Versión del servidor cargada correctamente (copia previa guardada en navegador).');
    } else if (action === 'force') {
      this.closeConflictModal();
      await this.saveReport({ force: true });
    } else if (action === 'merge') {
      // Fusionar: incorporar incidencias del servidor que no existan en el borrador local
      const localIncidents = App?.state?.incidents || [];
      const remoteIncidents = this.conflictingRemoteReport?.incidents || [];

      const localKeys = new Set(localIncidents.map(i => (i.ticket || i.title || '').trim().toUpperCase()));
      let addedCount = 0;

      for (const remoteInc of remoteIncidents) {
        const key = (remoteInc.ticket || remoteInc.title || '').trim().toUpperCase();
        if (key && !localKeys.has(key)) {
          localIncidents.push(JSON.parse(JSON.stringify(remoteInc)));
          addedCount++;
        }
      }

      App.renderSidebarList();
      App.renderDeck();
      App.fit();

      this.closeConflictModal();
      await this.saveReport({ force: true });

      if (window.Toast) {
        Toast.success(`Fusión completada (${addedCount} incidencias incorporadas del servidor) y guardada.`);
      }
    }
  },

  persistLocalSnapshot() {
    if (!this.currentReportId) return;
    try {
      const key = `mo_inc_report_${this.currentReportId}`;
      localStorage.setItem(key, JSON.stringify({
        meta: App?.state?.meta,
        incidents: App?.state?.incidents,
        openIdx: App?.state?.openIdx || 0,
        updatedAt: this.lastLoadedUpdatedAt,
      }));
    } catch (e) {}
  },
};

// Initialize when App is ready
function initEditor() {
  console.log('[initEditor] Checking if App is defined:', typeof App);
  if (typeof App === 'undefined') {
    setTimeout(initEditor, 100);
    return;
  }
  console.log('[initEditor] App is ready, calling ReportEditor.init()');
  ReportEditor.init();
}

console.log('[editor.js] Adding DOMContentLoaded listener');
document.addEventListener('DOMContentLoaded', () => {
  setTimeout(initEditor, 200);
});
