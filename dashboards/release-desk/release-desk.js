(function (global) {
    'use strict';

    var Domain = (typeof module !== 'undefined' && module.exports)
        ? require('./release-desk-domain.js')
        : (global.ReleaseDeskDomain || {});

    if (typeof module !== 'undefined' && module.exports) {
        module.exports = Domain;
    }

    if (typeof document === 'undefined') return;

    var escapeHtml = Domain.escapeHtml;
    var isClosedStatus = Domain.isClosedStatus;
    var filterNonClosedIncidents = Domain.filterNonClosedIncidents;
    var extractProjectCode = Domain.extractProjectCode;
    var resolveProjectInfo = Domain.resolveProjectInfo;
    var buildFollowupText = Domain.buildFollowupText;
    var computeOpenAgeDays = Domain.computeOpenAgeDays;
    var isIaCacheStale = Domain.isIaCacheStale;
    var matchesKpiFilter = Domain.matchesKpiFilter;
    var buildExportCsv = Domain.buildExportCsv;
    var buildExportFilename = Domain.buildExportFilename;
    var sortIncidents = Domain.sortIncidents;
    var buildMesaBriefing = Domain.buildMesaBriefing;
    var buildMesaBriefingBySystem = Domain.buildMesaBriefingBySystem;
    var getFechaPrevistaStatus = Domain.getFechaPrevistaStatus;
    var getDespliegueBadgeClass = Domain.getDespliegueBadgeClass;
    var groupIncidentsByProject = Domain.groupIncidentsByProject;
    var getSyncChangeBadge = Domain.getSyncChangeBadge;
    var isMassiveIncident = Domain.isMassiveIncident;
    var getPriorityBadgeClassDomain = Domain.getPriorityBadgeClass;
    var getPriorityTooltip = Domain.getPriorityTooltip;
    var state = {
        currentRelease: null,
        postmortemFiles: [],
        activeIncidents: [],
        filteredIncidents: [],
        selectedId: null,
        iaCache: new Map(),
        iaInFlight: new Set(),
        massiveIds: new Set(),
        metadata: {},
        projectsCatalog: {},
        overrides: {},
        editingFechaId: null,
        activeKpiFilter: null,
        sortKey: null,
        sortDir: 'asc',
        viewMode: 'table'
    };

    async function preloadCachedIaSummaries(incidents) {
        if (!Array.isArray(incidents) || incidents.length === 0) return;
        var ids = incidents
            .map(function (r) { return r && r['ID de incidencia']; })
            .filter(Boolean);
        if (ids.length === 0) return;
        try {
            var resp = await fetch('/api/epsilon/resumenIA/cached', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                body: JSON.stringify({ ids: ids })
            });
            if (!resp.ok) return;
            var json = await resp.json();
            var summaries = (json && json.summaries) || {};
            Object.keys(summaries).forEach(function (incId) {
                if (summaries[incId]) {
                    state.iaCache.set(incId, summaries[incId]);
                }
            });
        } catch (_) {
            // Silencioso si el servidor estático no expone el endpoint
        }
    }

    async function loadReleaseOverrides(releaseName) {
        state.overrides = {};
        if (!releaseName) return;
        try {
            var resp = await fetch('/api/release-desk/overrides?release=' + encodeURIComponent(releaseName) + '&t=' + Date.now());
            if (resp.ok) {
                var json = await resp.json();
                if (json && json.overrides && typeof json.overrides === 'object') {
                    state.overrides = json.overrides;
                }
            }
        } catch (_) {
            state.overrides = {};
        }
    }

    async function saveFechaPrevistaOverride(incidentId, fechaPrevista) {
        if (!state.currentRelease || !incidentId) return;
        try {
            var resp = await fetch('/api/release-desk/overrides', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    release_name: state.currentRelease,
                    incident_id: incidentId,
                    fecha_prevista: fechaPrevista || ''
                })
            });
            var data = await resp.json();
            if (!resp.ok || !data.success) {
                throw new Error(data.error || ('HTTP ' + resp.status));
            }
            state.overrides = data.overrides || {};
            state.editingFechaId = null;
            updateKPIs();
            applyFilters();
            notify(
                fechaPrevista
                    ? 'Fecha prevista guardada para ' + incidentId + ' (' + fechaPrevista + ')'
                    : 'Fecha prevista eliminada para ' + incidentId,
                'success'
            );
        } catch (err) {
            notify('Error guardando fecha prevista: ' + (err.message || err), 'error');
        }
    }

    async function loadProjectsCatalog() {
        try {
            var resp = await fetch('/data/config/projects_catalog.json?t=' + Date.now());
            if (!resp.ok) {
                resp = await fetch('/data/projects_catalog.json?t=' + Date.now());
            }
            if (resp.ok) {
                var json = await resp.json();
                if (json && typeof json === 'object') {
                    state.projectsCatalog = json;
                }
            }
        } catch (_) {
            state.projectsCatalog = {};
        }
    }

    function notify(msg, type) {
        if (global.Toast && typeof global.Toast[type] === 'function') {
            global.Toast[type](msg);
        } else if (type === 'error') {
            console.error(msg);
        }
    }

    function execCommandFallback(text, successMsg) {
        var ta = document.createElement('textarea');
        ta.value = text;
        ta.setAttribute('readonly', '');
        ta.style.position = 'fixed';
        ta.style.top = '0';
        ta.style.left = '-9999px';
        ta.style.width = '2em';
        ta.style.height = '2em';
        ta.style.padding = '0';
        ta.style.border = 'none';
        ta.style.outline = 'none';
        ta.style.boxShadow = 'none';
        ta.style.background = 'transparent';
        document.body.appendChild(ta);
        ta.focus();
        ta.select();
        var successful = false;
        try {
            successful = document.execCommand('copy');
        } catch (err) {
            successful = false;
        }
        document.body.removeChild(ta);
        if (successful) {
            notify(successMsg || 'Copiado al portapapeles.', 'success');
        } else {
            notify('No se pudo acceder al portapapeles. Copia el texto manualmente.', 'error');
        }
    }

    function copyTextToClipboard(text, successMsg) {
        if (!text) return;
        if (window.isSecureContext && navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
            navigator.clipboard.writeText(text).then(function () {
                notify(successMsg || 'Copiado al portapapeles.', 'success');
            }).catch(function (err) {
                console.warn('Fallo navigator.clipboard.writeText, usando fallback textarea:', err);
                execCommandFallback(text, successMsg);
            });
            return;
        }
        execCommandFallback(text, successMsg);
    }

    function getStatusBadgeClass(estatus) {
        var s = String(estatus || '').toLowerCase();
        if (s.includes('resuelt')) return 'rd-badge-resuelto';
        if (s.includes('pend')) return 'rd-badge-pendiente';
        if (s.includes('curso') || s.includes('progreso')) return 'rd-badge-curso';
        return 'rd-badge-asignado';
    }

    function getPriorityBadgeClass(prio, urg, isMasiva) {
        if (typeof getPriorityBadgeClassDomain === 'function') {
            return getPriorityBadgeClassDomain(prio, urg, isMasiva);
        }
        var p = String(prio || urg || '').toLowerCase();
        if (p.includes('p1') || p.includes('crít') || p.includes('crit')) return isMasiva ? 'rd-badge-critica rd-badge-masiva' : 'rd-badge-critica';
        if (p.includes('p2') || p.includes('alt')) return isMasiva ? 'rd-badge-alta rd-badge-masiva' : 'rd-badge-alta';
        return isMasiva ? 'rd-badge-masiva' : 'rd-badge-media';
    }

    function getUrlReleaseParam() {
        return new URLSearchParams(window.location.search).get('release');
    }

    function updateUrlReleaseParam(releaseName) {
        if (!releaseName) return;
        var url = new URL(window.location.href);
        url.searchParams.set('release', releaseName);
        window.history.replaceState({}, '', url.toString());
    }

    function collectAvailableReleases(files) {
        var seen = new Set();
        var ordered = [];
        var rawReleases = typeof RAW_RELEASES !== 'undefined'
            ? RAW_RELEASES
            : global.RAW_RELEASES;
        if (Array.isArray(rawReleases)) {
            for (var i = rawReleases.length - 1; i >= 0; i--) {
                var rName = rawReleases[i] && rawReleases[i][0];
                if (rName && !seen.has(rName)) {
                    seen.add(rName);
                    ordered.push(rName);
                }
            }
        }
        (files || []).forEach(function (f) {
            var cleanName = (f && f.release_name ? String(f.release_name).trim() : '');
            if (cleanName && !seen.has(cleanName)) {
                seen.add(cleanName);
                ordered.unshift(cleanName);
            }
        });
        return ordered;
    }

    function populateReleaseSelect(releases, selected) {
        var select = document.getElementById('releaseSelect');
        if (!select) return;
        select.innerHTML = releases.map(function (r) {
            var sel = r === selected ? ' selected' : '';
            return '<option value="' + escapeHtml(r) + '"' + sel + '>' + escapeHtml(r) + '</option>';
        }).join('');
    }

    function populateFilterSelects() {
        var statusSet = new Set();
        var groupSet = new Set();
        var prioSet = new Set();
        var projectSet = new Set();
        var hasMasiva = false;

        state.activeIncidents.forEach(function (inc) {
            if (inc['Estatus']) statusSet.add(inc['Estatus']);
            var sys = (inc['Grupo asignado'] && String(inc['Grupo asignado']).trim()) ||
                      (inc['Grupo Resolutor'] && String(inc['Grupo Resolutor']).trim()) ||
                      (inc['Sistema'] && String(inc['Sistema']).trim()) ||
                      (inc['sistema'] && String(inc['sistema']).trim()) ||
                      (inc['producto'] && String(inc['producto']).trim());
            if (sys) groupSet.add(sys);
            if (inc['Prioridad']) prioSet.add(inc['Prioridad']);
            if (inc['Urgencia']) prioSet.add(inc['Urgencia']);
            if (isMassiveIncident && isMassiveIncident(inc, state.massiveIds)) hasMasiva = true;
            var projCode = extractProjectCode(inc);
            if (projCode) projectSet.add(projCode);
        });

        var statusSel = document.getElementById('filterStatus');
        var groupSel = document.getElementById('filterGroup');
        var prioSel = document.getElementById('filterPriority');
        var projectSel = document.getElementById('filterProject');

        if (statusSel) {
            statusSel.innerHTML = '<option value="">Todos los estados activos</option>' +
                Array.from(statusSet).sort().map(function (s) {
                    return '<option value="' + escapeHtml(s) + '">' + escapeHtml(s) + '</option>';
                }).join('');
        }
        if (groupSel) {
            groupSel.innerHTML = '<option value="">Todos los sistemas</option>' +
                Array.from(groupSet).sort().map(function (g) {
                    return '<option value="' + escapeHtml(g) + '">' + escapeHtml(g) + '</option>';
                }).join('');
        }
        if (prioSel) {
            var prioOptions = Array.from(prioSet).sort().map(function (p) {
                return '<option value="' + escapeHtml(p) + '">' + escapeHtml(p) + '</option>';
            });
            if (hasMasiva) {
                prioOptions.unshift('<option value="Masiva">⚡ Masivas</option>');
            }
            prioSel.innerHTML = '<option value="">Todas las prioridades</option>' +
                prioOptions.join('');
        }
        if (projectSel) {
            projectSel.innerHTML = '<option value="">Todos los proyectos</option>' +
                Array.from(projectSet).sort().map(function (code) {
                    var info = resolveProjectInfo({ 'Descripción': code }, state.projectsCatalog, state.currentRelease);
                    var titleAttr = info && info.summary ? (' title="' + escapeHtml(info.summary) + '"') : '';
                    return '<option value="' + escapeHtml(code) + '"' + titleAttr + '>' + escapeHtml(code) + '</option>';
                }).join('');
            projectSel.title = '';
        }
    }

    function updateKPIs() {
        var total = state.activeIncidents.length;
        var critHigh = 0;
        var inProgress = 0;
        var resolvedPendingClose = 0;
        var overdueOrMissing = 0;

        state.activeIncidents.forEach(function (inc) {
            var p = String(inc['Prioridad'] || inc['Urgencia'] || '').toLowerCase();
            if (p.includes('p1') || p.includes('p2') || p.includes('crít') || p.includes('crit') || p.includes('alt')) {
                critHigh++;
            }
            var st = String(inc['Estatus'] || '').toLowerCase();
            if (st.includes('resuelt')) {
                resolvedPendingClose++;
            } else {
                inProgress++;
                var fst = getFechaPrevistaStatus(inc, state.overrides);
                if (fst === 'overdue' || fst === 'missing') {
                    overdueOrMissing++;
                }
            }
        });

        document.getElementById('kpiActiveTotal').textContent = total;
        document.getElementById('kpiCriticalHigh').textContent = critHigh;
        document.getElementById('kpiInProgress').textContent = inProgress;
        document.getElementById('kpiResolvedPendingClose').textContent = resolvedPendingClose;
        var kpiOmEl = document.getElementById('kpiOverdueMissing');
        if (kpiOmEl) kpiOmEl.textContent = overdueOrMissing;
    }

    function updateKpiActiveUI() {
        Array.from(document.querySelectorAll('.rd-kpi-card[data-kpi-filter]')).forEach(function (card) {
            var kpi = card.getAttribute('data-kpi-filter');
            var active = Boolean(state.activeKpiFilter && state.activeKpiFilter === kpi);
            card.classList.toggle('is-active', active);
            card.setAttribute('aria-pressed', active ? 'true' : 'false');
        });
    }

    function applyFilters() {
        var search = (document.getElementById('filterSearch').value || '').trim().toLowerCase();
        var status = document.getElementById('filterStatus').value;
        var group = document.getElementById('filterGroup').value;
        var prio = document.getElementById('filterPriority').value;
        var projectEl = document.getElementById('filterProject');
        var project = projectEl ? projectEl.value : '';
        if (projectEl) {
            var selectedOpt = projectEl.options && projectEl.selectedIndex >= 0 ? projectEl.options[projectEl.selectedIndex] : null;
            projectEl.title = (project && selectedOpt && selectedOpt.title) ? selectedOpt.title : '';
        }

        state.filteredIncidents = state.activeIncidents.filter(function (inc) {
            if (state.activeKpiFilter && !matchesKpiFilter(inc, state.activeKpiFilter, state.overrides)) return false;
            if (status && inc['Estatus'] !== status) return false;
            if (group) {
                var incSys = (inc['Grupo asignado'] && String(inc['Grupo asignado']).trim()) ||
                             (inc['Grupo Resolutor'] && String(inc['Grupo Resolutor']).trim()) ||
                             (inc['Sistema'] && String(inc['Sistema']).trim()) ||
                             (inc['sistema'] && String(inc['sistema']).trim()) ||
                             (inc['producto'] && String(inc['producto']).trim()) || '';
                if (incSys !== group && inc['Grupo asignado'] !== group && inc['Grupo Resolutor'] !== group) return false;
            }
            if (prio) {
                if (prio === 'Masiva') {
                    if (!isMassiveIncident || !isMassiveIncident(inc, state.massiveIds)) return false;
                } else {
                    var incPrio = (inc['Prioridad'] && String(inc['Prioridad']).trim()) || '';
                    var incUrg = (inc['Urgencia'] && String(inc['Urgencia']).trim()) || '';
                    if (incPrio !== prio && incUrg !== prio) return false;
                }
            }
            var proj = resolveProjectInfo(inc, state.projectsCatalog, state.currentRelease);
            if (project && (!proj || proj.code !== project)) return false;
            if (search) {
                var hay = [
                    inc['ID de incidencia'],
                    inc['Descripción'],
                    inc['Grupo Remitente'],
                    inc['Grupo asignado'],
                    inc['Grupo Resolutor'],
                    inc['producto'],
                    inc['Sistema'],
                    proj ? proj.code : '',
                    proj ? proj.summary : ''
                ].join(' ').toLowerCase();
                if (!hay.includes(search)) return false;
            }
            return true;
        });

        if (state.sortKey) {
            state.filteredIncidents = sortIncidents(
                state.filteredIncidents,
                state.sortKey,
                state.sortDir,
                state.projectsCatalog,
                state.currentRelease,
                state.overrides
            );
        }

        renderTable();
        if (state.viewMode === 'projects') {
            renderProjectSummaryView();
        }
    }

    function setViewMode(mode) {
        state.viewMode = mode === 'projects' ? 'projects' : 'table';
        var tableWrap = document.getElementById('tableViewWrap');
        var projWrap = document.getElementById('projectSummaryView');
        var btnTable = document.getElementById('btnViewTable');
        var btnProj = document.getElementById('btnViewByProject');
        var isProj = state.viewMode === 'projects';

        if (tableWrap) tableWrap.classList.toggle('hidden', isProj);
        if (projWrap) projWrap.classList.toggle('hidden', !isProj);
        if (btnTable) {
            btnTable.classList.toggle('is-active', !isProj);
            btnTable.setAttribute('aria-pressed', !isProj ? 'true' : 'false');
        }
        if (btnProj) {
            btnProj.classList.toggle('is-active', isProj);
            btnProj.setAttribute('aria-pressed', isProj ? 'true' : 'false');
        }
        if (isProj) {
            renderProjectSummaryView();
        }
    }

    function renderProjectSummaryView() {
        var container = document.getElementById('projectSummaryView');
        if (!container) return;

        if (!state.filteredIncidents || state.filteredIncidents.length === 0) {
            container.innerHTML = '<div style="text-align:center; padding:24px; color:#5C5852;">No hay incidencias activas que coincidan con los filtros actuales.</div>';
            return;
        }

        var groups = groupIncidentsByProject(
            state.filteredIncidents,
            state.projectsCatalog,
            state.currentRelease,
            state.overrides
        );

        var healthMeta = {
            crit: { label: 'Riesgo alto', cls: 'rd-badge-critica' },
            warn: { label: 'Atención', cls: 'rd-badge-alta' },
            ok: { label: 'Controlado', cls: 'rd-badge-resuelto' }
        };

        container.innerHTML = '<div class="rd-projects-grid">' + groups.map(function (g) {
            var hm = healthMeta[g.health] || healthMeta.ok;
            var despliegueHtml = g.despliegue
                ? '<span class="rd-badge ' + getDespliegueBadgeClass(g.despliegue) + '">' + escapeHtml(g.despliegue) + '</span>'
                : '';
            var codeBadge = g.hasProject
                ? '<span class="rd-badge rd-badge-jira">' + escapeHtml(g.code) + '</span>'
                : '<span class="rd-badge rd-badge-media">' + escapeHtml(g.code) + '</span>';

            var metrics = [
                '<span class="rd-badge rd-badge-code">Total: ' + g.total + '</span>'
            ];
            if (g.p1 > 0) metrics.push('<span class="rd-badge rd-badge-critica">P1: ' + g.p1 + '</span>');
            if (g.p2 > 0) metrics.push('<span class="rd-badge rd-badge-alta">P2: ' + g.p2 + '</span>');
            if (g.p3Other > 0) metrics.push('<span class="rd-badge rd-badge-media">P3/Otras: ' + g.p3Other + '</span>');
            if (g.overdue > 0) metrics.push('<span class="rd-badge rd-badge-fecha-vencida">⚠ Vencidas: ' + g.overdue + '</span>');
            if (g.missingFecha > 0) metrics.push('<span class="rd-badge rd-badge-curso">Sin fecha: ' + g.missingFecha + '</span>');
            if (g.resolved > 0) metrics.push('<span class="rd-badge rd-badge-resuelto">Resueltas: ' + g.resolved + '</span>');

            var incButtons = g.incidents.map(function (inc) {
                var incId = inc['ID de incidencia'] || '-';
                var st = inc['Estatus'] || '';
                var pVal = (inc['Prioridad'] && String(inc['Prioridad']).trim()) || '';
                var uVal = (inc['Urgencia'] && String(inc['Urgencia']).trim()) || '';
                var pLabel = (pVal && uVal && pVal.toLowerCase() !== uVal.toLowerCase())
                    ? (pVal + ' / ' + uVal)
                    : (pVal || uVal || '');
                return '<button type="button" class="rd-project-inc-btn" data-open-inc="' + escapeHtml(incId) + '" title="' + escapeHtml((pLabel ? pLabel + ' · ' : '') + st) + '">' + escapeHtml(incId) + '</button>';
            }).join('');

            var filterAction = g.hasProject
                ? '<button type="button" class="rd-fecha-add-btn" data-filter-proj="' + escapeHtml(g.code) + '" title="Filtrar la tabla por este proyecto">Ver en tabla →</button>'
                : '';

            return '<article class="rd-project-card is-' + g.health + '">' +
                '<div class="rd-project-head">' +
                    '<div style="display:flex;align-items:center;gap:4px;flex-wrap:wrap;">' + despliegueHtml + codeBadge + '</div>' +
                    '<div style="display:flex;align-items:center;gap:6px;">' +
                        '<span class="rd-badge ' + hm.cls + '">' + hm.label + '</span>' +
                        filterAction +
                    '</div>' +
                '</div>' +
                (g.summary ? '<div class="rd-project-title">' + escapeHtml(g.summary) + '</div>' : '') +
                '<div class="rd-project-metrics">' + metrics.join('') + '</div>' +
                '<div class="rd-project-inc-list">' + incButtons + '</div>' +
            '</article>';
        }).join('') + '</div>';

        Array.from(container.querySelectorAll('[data-filter-proj]')).forEach(function (btn) {
            btn.addEventListener('click', function () {
                var code = btn.getAttribute('data-filter-proj');
                var projSel = document.getElementById('filterProject');
                if (projSel) projSel.value = code;
                setViewMode('table');
                applyFilters();
            });
        });

        Array.from(container.querySelectorAll('[data-open-inc]')).forEach(function (btn) {
            btn.addEventListener('click', function () {
                var incId = btn.getAttribute('data-open-inc');
                state.selectedId = incId;
                setViewMode('table');
                renderTable();
                var row = document.querySelector('#incidentsTableBody tr[data-inc-id="' + incId + '"]');
                if (row && row.scrollIntoView) {
                    row.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            });
        });
    }

    function renderTable() {
        var tbody = document.getElementById('incidentsTableBody');
        var visibleCount = document.getElementById('visibleCount');
        visibleCount.textContent = state.filteredIncidents.length;

        if (state.filteredIncidents.length === 0) {
            tbody.innerHTML = '<tr><td colspan="12" style="text-align:center; padding:24px; color:#5C5852;">No hay incidencias activas que coincidan con los filtros actuales.</td></tr>';
            return;
        }

        tbody.innerHTML = state.filteredIncidents.map(function (inc) {
            var id = inc['ID de incidencia'] || '-';
            var isSelected = id === state.selectedId;
            var fechaApertura = inc['Fecha de envío'] || '-';
            var iaData = state.iaCache.get(id);
            var descOriginal = inc['Descripción'] || '-';
            var producto = inc['producto'] ? String(inc['producto']).trim() : '';
            var descCellHtml = '<div class="rd-cell-clamp">' +
                (producto ? '<span class="rd-badge rd-badge-sistema" style="margin-right:4px;">' + escapeHtml(producto) + '</span>' : '') +
                escapeHtml(descOriginal) +
                '</div>';
            var prioVal = (inc['Prioridad'] && String(inc['Prioridad']).trim()) || '';
            var urgVal = (inc['Urgencia'] && String(inc['Urgencia']).trim()) || '';
            var prioBadgeHtml = '';
            if (prioVal && urgVal && prioVal.toLowerCase() !== urgVal.toLowerCase()) {
                prioBadgeHtml = escapeHtml(prioVal) + '<span class="rd-badge-sep">/</span><span class="rd-badge-urg">' + escapeHtml(urgVal) + '</span>';
            } else {
                prioBadgeHtml = escapeHtml(prioVal || urgVal || '-');
            }
            var isMasiva = isMassiveIncident ? isMassiveIncident(inc, state.massiveIds) : false;
            var prioBadgeClass = getPriorityBadgeClass(inc['Prioridad'], inc['Urgencia'], isMasiva);
            var prioTip = (typeof getPriorityTooltip === 'function')
                ? getPriorityTooltip(inc, iaData, isMasiva)
                : null;
            var prioTooltipAttr = (prioTip && prioTip.text)
                ? ' data-tooltip="' + escapeHtml(prioTip.text) + '" data-tooltip-title="' + escapeHtml(prioTip.title) + '"'
                : '';
            var statusBadgeClass = getStatusBadgeClass(inc['Estatus']);
            var sistema = (inc['Grupo asignado'] && String(inc['Grupo asignado']).trim()) ||
                          (inc['Grupo Resolutor'] && String(inc['Grupo Resolutor']).trim()) ||
                          (inc['Sistema'] && String(inc['Sistema']).trim()) ||
                          (inc['sistema'] && String(inc['sistema']).trim()) ||
                          (inc['producto'] && String(inc['producto']).trim()) || '-';
            var proj = resolveProjectInfo(inc, state.projectsCatalog, state.currentRelease);
            var jiraBug = inc['JIRA'] || inc['Jira'] || inc['jira'] || '';
            var jiraCell = jiraBug
                ? '<span class="rd-badge rd-badge-media">' + escapeHtml(jiraBug) + '</span>'
                : '<span style="color:#9CA3AF;">-</span>';
            var proyectoText = proj
                ? ((proj.despliegue ? '[' + proj.despliegue + '] ' : '') + proj.code + (proj.summary ? ' — ' + proj.summary : ''))
                : '-';
            var despliegueBadgeClass = getDespliegueBadgeClass(proj && proj.despliegue);
            var proyectoCell = proj
                ? '<div class="rd-proj-badges">' +
                  (proj.despliegue ? '<span class="rd-badge ' + despliegueBadgeClass + '">' + escapeHtml(proj.despliegue) + '</span>' : '') +
                  '<span class="rd-badge rd-badge-jira">' + escapeHtml(proj.code) + '</span></div>'
                : '<span style="color:#9CA3AF;">-</span>';
            var acciones = (iaData && !iaData._error && (iaData.siguienteAccion || iaData.siguiente_accion || iaData.solucion))
                || inc['detalleSolucion']
                || '-';
            var estatusLower = String(inc['Estatus'] || '').toLowerCase();
            var isResolved = estatusLower.includes('resuelt') || estatusLower.includes('cerrad');
            var overrideEntry = state.overrides && state.overrides[id];
            var agreedFecha = (overrideEntry && overrideEntry.fecha_prevista) ? overrideEntry.fecha_prevista : '';
            var fechaPrevista = isResolved
                ? (inc['Fecha de última resolución'] || '')
                : agreedFecha;
            var motivoResuelto = inc['Motivo de estado'] ||
                inc['MotivoEstado_Anterior'] ||
                inc['motivoEstado'] ||
                inc['motivoResolucion'] ||
                (isResolved ? (inc['detalleSolucion'] || (iaData && !iaData._error && iaData.solucion ? iaData.solucion : '') || '') : '') ||
                '-';
            var peticionario = inc['Grupo Remitente'] || '-';

            var rowClasses = [];
            if (isSelected) rowClasses.push('is-selected');
            if (prioBadgeClass.indexOf('rd-badge-critica') !== -1) rowClasses.push('rd-row-critica');
            else if (prioBadgeClass.indexOf('rd-badge-alta') !== -1 || prioBadgeClass.indexOf('rd-badge-masiva') !== -1) rowClasses.push('rd-row-alta');
            if (isResolved) rowClasses.push('rd-row-resuelto');
            var rowClassAttr = rowClasses.length ? ' class="' + rowClasses.join(' ') + '"' : '';

            var sistemaCell = sistema !== '-'
                ? '<span class="rd-badge rd-badge-sistema" title="' + escapeHtml(sistema) + '">' + escapeHtml(sistema) + '</span>'
                : '<span style="color:#9CA3AF;">-</span>';

            var fechaPrevistaCell = '';
            if (isResolved) {
                fechaPrevistaCell = fechaPrevista
                    ? '<span class="rd-badge rd-badge-fecha">' + escapeHtml(fechaPrevista) + '</span>'
                    : '';
            } else if (state.editingFechaId === id) {
                fechaPrevistaCell =
                    '<div style="display:flex; align-items:center; gap:4px;" data-fecha-editor="1">' +
                        '<input type="date" class="rd-fecha-input" data-fecha-input="' + escapeHtml(id) + '" value="' + escapeHtml(agreedFecha) + '">' +
                        (agreedFecha ? '<button type="button" class="rd-fecha-add-btn" data-clear-fecha="' + escapeHtml(id) + '" title="Limpiar fecha">✕</button>' : '') +
                    '</div>';
            } else if (agreedFecha) {
                var fst = getFechaPrevistaStatus(inc, state.overrides);
                var fechaClass = 'rd-badge-fecha-acordada';
                var fechaTitle = 'Fecha prevista acordada (clic para editar)';
                var fechaPrefix = '';
                if (fst === 'overdue') {
                    fechaClass = 'rd-badge-fecha-vencida';
                    fechaTitle = 'Fecha prevista vencida (clic para editar)';
                    fechaPrefix = '⚠ ';
                } else if (fst === 'due_soon') {
                    fechaClass = 'rd-badge-fecha-proxima';
                    fechaTitle = 'Vence hoy o mañana (clic para editar)';
                }
                fechaPrevistaCell = '<button type="button" class="rd-badge ' + fechaClass + '" data-edit-fecha="' + escapeHtml(id) + '" title="' + fechaTitle + '">' + fechaPrefix + escapeHtml(agreedFecha) + '</button>';
            } else {
                fechaPrevistaCell = '<button type="button" class="rd-fecha-add-btn" data-edit-fecha="' + escapeHtml(id) + '" title="Asignar fecha prevista acordada">+ Fecha</button>';
            }

            var agingHtml = '';
            if (!isResolved) {
                var ageDays = computeOpenAgeDays(fechaApertura);
                if (ageDays !== null && ageDays > 7) {
                    agingHtml = '<div><span class="rd-aging-badge rd-aging-crit" title="Abierta hace ' + ageDays + ' días">' + ageDays + 'd</span></div>';
                } else if (ageDays !== null && ageDays > 3) {
                    agingHtml = '<div><span class="rd-aging-badge rd-aging-warn" title="Abierta hace ' + ageDays + ' días">' + ageDays + 'd</span></div>';
                }
            }

            var iaStale = iaData && isIaCacheStale(iaData, inc);
            var staleBadgeHtml = iaStale
                ? '<div><span class="rd-badge-stale" title="El ticket se actualizó en Remedy después de generar este resumen; al desplegar se refrescará automáticamente">↻ Nuevo en Remedy</span></div>'
                : '';

            var syncBadgeKind = getSyncChangeBadge(id, state.metadata && state.metadata.last_sync_changes);
            var syncBadgeHtml = '';
            if (syncBadgeKind === 'new') {
                syncBadgeHtml = '<div><span class="rd-badge-sync-new" title="Incidencia nueva en la última sincronización">Nuevo</span></div>';
            } else if (syncBadgeKind === 'status') {
                syncBadgeHtml = '<div><span class="rd-badge-sync-upd" title="Cambió de estado en la última sincronización">Cambió estado</span></div>';
            } else if (syncBadgeKind === 'updated') {
                syncBadgeHtml = '<div><span class="rd-badge-sync-upd" title="Actualizada en la última sincronización">Actualizada</span></div>';
            }

            var iaProblema = (iaData && !iaData._error && iaData.problema) ? String(iaData.problema).trim() : '';
            var descTooltipAttr = '';
            if (iaProblema) {
                descTooltipAttr = ' data-tooltip="' + escapeHtml(iaProblema) + '" data-tooltip-title="Problema Detectado (Resumen IA)"';
            } else if (descOriginal && descOriginal !== '-') {
                descTooltipAttr = ' data-tooltip="' + escapeHtml(descOriginal) + '" data-tooltip-title="Descripción"';
            }
            var projTooltipAttr = (proj && proyectoText !== '-')
                ? ' data-tooltip="' + escapeHtml(proyectoText) + '" data-tooltip-title="Proyecto Asociado"'
                : '';
            var accionesTooltipAttr = (acciones && acciones !== '-')
                ? ' data-tooltip="' + escapeHtml(acciones) + '" data-tooltip-title="Acciones / Siguiente Paso"'
                : '';
            var motivoTooltipAttr = (motivoResuelto && motivoResuelto !== '-')
                ? ' data-tooltip="' + escapeHtml(motivoResuelto) + '" data-tooltip-title="Motivo / Detalle de Resolución"'
                : '';

            var codeLinkHtml = '<a href="javascript:void(0)" class="rd-inc-link" data-open-resumen="' + escapeHtml(id) + '" title="Abrir ventana Resumen IA" onclick="if(window.openResumenIA){event.stopPropagation();window.openResumenIA(\'' + escapeHtml(id) + '\');}return false;">' + escapeHtml(id) + '</a>';

            var rowHtml = '<tr data-inc-id="' + escapeHtml(id) + '"' + rowClassAttr + ' aria-expanded="' + (isSelected ? 'true' : 'false') + '">' +
                '<td style="white-space:nowrap;"><span class="rd-badge rd-badge-code">' + (isSelected ? '▾ ' : '▸ ') + codeLinkHtml + '</span>' + syncBadgeHtml + '</td>' +
                '<td style="font-size:11.5px; min-width:78px;">' + escapeHtml(fechaApertura) + agingHtml + '</td>' +
                '<td style="min-width:200px; max-width:340px;"' + descTooltipAttr + '>' + descCellHtml + '</td>' +
                '<td style="white-space:nowrap;"' + prioTooltipAttr + '><span class="rd-badge ' + prioBadgeClass + '">' + prioBadgeHtml + '</span></td>' +
                '<td style="max-width:120px;">' + sistemaCell + '</td>' +
                '<td style="white-space:nowrap;">' + jiraCell + '</td>' +
                '<td style="min-width:120px; max-width:190px;"' + projTooltipAttr + '>' + proyectoCell + '</td>' +
                '<td style="min-width:150px; max-width:230px;"' + accionesTooltipAttr + '><div class="rd-cell-clamp">' + escapeHtml(acciones) + '</div>' + staleBadgeHtml + '</td>' +
                '<td><span class="rd-badge ' + statusBadgeClass + '">' + escapeHtml(inc['Estatus'] || '-') + '</span></td>' +
                '<td style="font-size:11.5px; min-width:78px;">' + fechaPrevistaCell + '</td>' +
                '<td style="min-width:140px; max-width:220px;"' + motivoTooltipAttr + '><div class="rd-cell-clamp">' + escapeHtml(motivoResuelto) + '</div></td>' +
                '<td style="max-width:120px;">' + escapeHtml(peticionario) + '</td>' +
                '</tr>';

            if (isSelected) {
                rowHtml += '<tr class="rd-detail-row" data-detail-for="' + escapeHtml(id) + '">' +
                    '<td colspan="12">' + renderDetailHtml(inc) + '</td>' +
                    '</tr>';
            }
            return rowHtml;
        }).join('');

        Array.from(tbody.querySelectorAll('tr[data-inc-id]')).forEach(function (row) {
            row.addEventListener('click', function () {
                selectIncident(row.getAttribute('data-inc-id'));
            });
        });

        Array.from(tbody.querySelectorAll('[data-open-resumen]')).forEach(function (link) {
            link.addEventListener('click', function (ev) {
                ev.stopPropagation();
                var incId = link.getAttribute('data-open-resumen');
                if (window.openResumenIA && incId) {
                    window.openResumenIA(incId);
                }
            });
        });

        Array.from(tbody.querySelectorAll('[data-edit-fecha]')).forEach(function (btn) {
            btn.addEventListener('click', function (ev) {
                ev.stopPropagation();
                state.editingFechaId = btn.getAttribute('data-edit-fecha');
                renderTable();
                var inp = tbody.querySelector('[data-fecha-input="' + state.editingFechaId + '"]');
                if (inp) inp.focus();
            });
        });

        Array.from(tbody.querySelectorAll('[data-fecha-editor]')).forEach(function (wrap) {
            wrap.addEventListener('click', function (ev) { ev.stopPropagation(); });
        });

        Array.from(tbody.querySelectorAll('[data-fecha-input]')).forEach(function (inp) {
            var incId = inp.getAttribute('data-fecha-input');
            inp.addEventListener('change', function () {
                saveFechaPrevistaOverride(incId, inp.value);
            });
            inp.addEventListener('keydown', function (ev) {
                if (ev.key === 'Escape') {
                    ev.stopPropagation();
                    state.editingFechaId = null;
                    renderTable();
                } else if (ev.key === 'Enter') {
                    ev.stopPropagation();
                    saveFechaPrevistaOverride(incId, inp.value);
                }
            });
        });

        Array.from(tbody.querySelectorAll('[data-clear-fecha]')).forEach(function (btn) {
            btn.addEventListener('click', function (ev) {
                ev.stopPropagation();
                saveFechaPrevistaOverride(btn.getAttribute('data-clear-fecha'), '');
            });
        });

        var selectedId = state.selectedId;
        if (selectedId) {
            var copyBtn = document.getElementById('btnCopyFollowup');
            if (copyBtn) {
                copyBtn.addEventListener('click', function (ev) {
                    ev.stopPropagation();
                    var inc = state.activeIncidents.find(function (r) { return r['ID de incidencia'] === selectedId; });
                    if (!inc) return;
                    var text = buildFollowupText(inc, state.iaCache.get(selectedId), state.currentRelease, state.projectsCatalog);
                    copyTextToClipboard(text, 'Seguimiento de ' + selectedId + ' copiado al portapapeles.');
                });
            }
            var closeBtn = document.getElementById('btnCloseDetail');
            if (closeBtn) {
                closeBtn.addEventListener('click', function (ev) {
                    ev.stopPropagation();
                    state.selectedId = null;
                    renderTable();
                });
            }
            var refreshBtn = document.getElementById('btnRefreshIA');
            if (refreshBtn) {
                refreshBtn.addEventListener('click', function (ev) {
                    ev.stopPropagation();
                    fetchIaSummary(selectedId, true);
                });
            }
        }
    }

    function renderIaSection(id, iaData, isLoading) {
        if (isLoading) {
            return '<div class="rd-ia-box"><div class="rd-ia-header"><h4 class="rd-ia-title">✨ Resumen IA</h4></div><p style="font-size:13px; color:#5C5852; margin:0;">Consultando Resumen IA para ' + escapeHtml(id) + '...</p></div>';
        }
        if (!iaData) {
            return '<div class="rd-ia-box">' +
                '<div class="rd-ia-header">' +
                '<h4 class="rd-ia-title">✨ Resumen IA</h4>' +
                '<button id="btnRefreshIA" class="rd-btn rd-btn-primary">✨ Generar Resumen IA</button>' +
                '</div>' +
                '<p style="font-size:13px; color:#5C5852; margin:0;">Sin Resumen IA cargado todavía. Pulsa el botón para generarlo.</p>' +
                '</div>';
        }
        if (iaData._error) {
            return '<div class="rd-ia-box">' +
                '<div class="rd-ia-header">' +
                '<h4 class="rd-ia-title">✨ Resumen IA</h4>' +
                '<button id="btnRefreshIA" class="rd-btn rd-btn-primary">↻ Reintentar Resumen IA</button>' +
                '</div>' +
                '<p style="font-size:13px; color:#991B1B; margin:0;">No se pudo obtener el Resumen IA: ' + escapeHtml(iaData._error) + '</p>' +
                '</div>';
        }

        var sintesis = iaData.resumenEjecutivo || iaData.resumen || iaData.sintesis || '';
        var problema = iaData.problema || '';
        var impacto = iaData.impacto || '';
        var causa = iaData.causa || iaData.causaRaiz || '';
        var solucion = iaData.solucion || '';
        var siguiente = iaData.siguienteAccion || iaData.siguiente_accion || '';
        var bloqueos = Array.isArray(iaData.bloqueos) ? iaData.bloqueos : [];
        var hitos = Array.isArray(iaData.hitosTecnicos) ? iaData.hitosTecnicos : [];

        var html = '<div class="rd-ia-box">' +
            '<div class="rd-ia-header">' +
            '<h4 class="rd-ia-title">✨ Resumen IA</h4>' +
            '<button id="btnRefreshIA" class="rd-btn">↻ Refrescar Resumen IA</button>' +
            '</div>';

        if (sintesis) html += '<div class="rd-ia-section"><strong>Síntesis Ejecutiva</strong>' + escapeHtml(sintesis) + '</div>';
        if (problema) html += '<div class="rd-ia-section"><strong>Problema Detectado</strong>' + escapeHtml(problema) + '</div>';
        if (impacto) html += '<div class="rd-ia-section"><strong>Impacto</strong>' + escapeHtml(impacto) + '</div>';
        if (causa) html += '<div class="rd-ia-section"><strong>Causa</strong>' + escapeHtml(causa) + '</div>';
        if (solucion) html += '<div class="rd-ia-section"><strong>Solución / Mitigación</strong>' + escapeHtml(solucion) + '</div>';
        if (siguiente) html += '<div class="rd-ia-section"><strong>Siguiente Acción Recomendada</strong>' + escapeHtml(siguiente) + '</div>';
        if (bloqueos.length > 0) {
            html += '<div class="rd-ia-section"><strong>Bloqueos</strong><ul style="margin:4px 0 0 18px; padding:0;">' +
                bloqueos.map(function (b) { return '<li>' + escapeHtml(typeof b === 'object' ? (b.descripcion || b.categoria || JSON.stringify(b)) : b) + '</li>'; }).join('') +
                '</ul></div>';
        }
        if (hitos.length > 0) {
            html += '<div class="rd-ia-section"><strong>Hitos Técnicos</strong><ul style="margin:4px 0 0 18px; padding:0;">' +
                hitos.map(function (h) { return '<li>' + escapeHtml(h) + '</li>'; }).join('') +
                '</ul></div>';
        }
        if (!sintesis && !problema && !impacto && !causa && !solucion && !siguiente) {
            html += '<p style="font-size:13px; color:#5C5852; margin:0;">Resumen IA recibido sin campos narrativos detallados.</p>';
        }
        html += '</div>';
        return html;
    }

    function renderDetailHtml(inc) {
        var id = inc['ID de incidencia'];
        var iaData = state.iaCache.get(id) || null;
        var isLoadingIa = state.iaInFlight.has(id);
        var estatusLower = String(inc['Estatus'] || '').toLowerCase();
        var isResolved = estatusLower.includes('resuelt') || estatusLower.includes('cerrad');
        var motivo = inc['Motivo de estado'] || inc['MotivoEstado_Anterior'] || inc['motivoEstado'] || '';
        var solucion = inc['detalleSolucion'] || (iaData && !iaData._error && iaData.solucion ? iaData.solucion : '') || '';

        var resolutionBox = '';
        if (isResolved || motivo || solucion) {
            resolutionBox = '<div class="rd-detail-resolution-box">' +
                '<div class="rd-detail-resolution-title">' +
                    '<span>✓ Detalle de Resolución / Motivo</span>' +
                    (motivo ? '<span class="rd-badge rd-badge-resuelto">' + escapeHtml(motivo) + '</span>' : '') +
                '</div>' +
                '<div class="rd-detail-resolution-content">' + escapeHtml(solucion || motivo || 'Sin detalle de solución registrado en Remedy.') + '</div>' +
            '</div>';
        }

        return '<div class="rd-detail-inline-card">' +
            '<div id="detailBody" class="rd-detail-body">' +
                renderIaSection(id, iaData, isLoadingIa) +
                resolutionBox +
            '</div>' +
            '<div class="rd-detail-inline-header">' +
                '<span>Seguimiento · <a href="javascript:void(0)" class="rd-inc-link" title="Abrir ventana Resumen IA" onclick="if(window.openResumenIA){window.openResumenIA(\'' + escapeHtml(id) + '\');}return false;">' + escapeHtml(id) + '</a></span>' +
                '<div class="rd-detail-inline-actions">' +
                    '<button id="btnCopyFollowup" class="rd-btn rd-btn-dark">📋 Copiar seguimiento</button>' +
                    '<button id="btnCloseDetail" class="rd-btn" title="Cerrar desplegable">✕ Cerrar</button>' +
                '</div>' +
            '</div>' +
        '</div>';
    }

    async function fetchIaSummary(id, forceRefresh) {
        if (!id || state.iaInFlight.has(id)) return;
        state.iaInFlight.add(id);
        if (state.selectedId === id) renderTable();

        try {
            var url = '/api/epsilon/resumenIA/' + encodeURIComponent(id) + (forceRefresh ? '?force=1' : '');
            var resp = await fetch(url, { headers: { 'Accept': 'application/json' } });
            var data = await resp.json();
            if (!resp.ok || data.success === false) {
                throw new Error(data.error || ('HTTP ' + resp.status));
            }
            if (!data._cached_at_ms) data._cached_at_ms = Date.now();
            state.iaCache.set(id, data);
            if (forceRefresh) notify('Resumen IA actualizado para ' + id, 'success');
        } catch (err) {
            state.iaCache.set(id, { _error: err && err.message ? err.message : 'Error de conexión' });
            if (forceRefresh) notify('Error al refrescar Resumen IA: ' + (err.message || err), 'error');
        } finally {
            state.iaInFlight.delete(id);
            renderTable();
        }
    }

    function selectIncident(id) {
        if (state.selectedId === id) {
            state.selectedId = null;
            renderTable();
            return;
        }
        state.selectedId = id;
        renderTable();
        if (id && !state.iaCache.has(id)) {
            fetchIaSummary(id, false);
        } else if (id) {
            var inc = state.activeIncidents.find(function (r) { return r['ID de incidencia'] === id; });
            if (inc && isIaCacheStale(state.iaCache.get(id), inc)) {
                fetchIaSummary(id, true);
            }
        }
    }

    function showEmptyState(title, desc, showSyncBtn) {
        document.getElementById('emptyStateTitle').textContent = title;
        document.getElementById('emptyStateDesc').textContent = desc;
        document.getElementById('btnEmptySync').classList.toggle('hidden', !showSyncBtn);
        document.getElementById('emptyStateBox').classList.remove('hidden');
        document.getElementById('workspaceSection').classList.add('hidden');
    }

    function showWorkspace() {
        document.getElementById('emptyStateBox').classList.add('hidden');
        document.getElementById('workspaceSection').classList.remove('hidden');
    }

    async function loadRelease(releaseName) {
        state.currentRelease = releaseName;
        state.selectedId = null;
        state.activeKpiFilter = null;
        updateKpiActiveUI();
        updateUrlReleaseParam(releaseName);

        try {
            var idxResp = await fetch('/data/storage/index.json?t=' + Date.now());
            if (!idxResp.ok) {
                idxResp = await fetch('/data/output/index.json?t=' + Date.now());
            }
            var idxData = idxResp.ok ? await idxResp.json() : {};
            var files = (idxData.postmortem && idxData.postmortem.files) || [];
            state.postmortemFiles = files;

            state.massiveIds = new Set();
            if (idxData.massive && Array.isArray(idxData.massive.files)) {
                for (var mi = 0; mi < idxData.massive.files.length; mi++) {
                    var mFile = idxData.massive.files[mi];
                    var mPath = mFile.path || ('/data/output/' + mFile.name);
                    if (mPath.indexOf('/infocodes/var/storage/release-dashboard/') !== -1) {
                        mPath = mPath.replace('/infocodes/var/storage/release-dashboard/', '/data/');
                    }
                    var mDataMarker = mPath.indexOf('data/');
                    if (mDataMarker !== -1) {
                        mPath = '/' + mPath.substring(mDataMarker);
                    } else if (!mPath.startsWith('http') && !mPath.startsWith('/')) {
                        mPath = '/' + mPath;
                    }
                    try {
                        var mResp = await fetch(mPath + '?t=' + Date.now());
                        if (mResp.ok) {
                            var mJson = await mResp.json();
                            var mRecs = Array.isArray(mJson) ? mJson : (mJson.data || []);
                            mRecs.forEach(function (mRec) {
                                var mid = mRec['ID de incidencia'] || mRec['id'] || mRec['idRemedy'];
                                if (mid) state.massiveIds.add(String(mid).trim());
                            });
                        }
                    } catch (mErr) {
                        console.warn('No se pudo cargar fichero masivo para verificación de tickets:', mPath, mErr);
                    }
                }
            }

            var allReleases = collectAvailableReleases(files);
            if (!state.currentRelease && allReleases.length > 0) {
                state.currentRelease = allReleases[0];
                updateUrlReleaseParam(state.currentRelease);
            }
            populateReleaseSelect(allReleases, state.currentRelease);

            var matching = files.find(function (f) {
                var fRel = f && f.release_name ? String(f.release_name).trim() : '';
                var curRel = state.currentRelease ? String(state.currentRelease).trim() : '';
                return fRel === curRel;
            });
            if (!matching) {
                state.activeIncidents = [];
                state.filteredIncidents = [];
                updateKPIs();
                populateFilterSelects();
                document.getElementById('lastSyncInfo').textContent = '';
                showEmptyState(
                    'Release ' + (state.currentRelease || '') + ' sin datos locales',
                    'Aún no existe un dataset local para esta release. Pulsa "Sincronizar Epsilon" para obtener sus incidencias activas.',
                    true
                );
                return;
            }

            var rawPath = matching.path || '';
            if (rawPath.includes('/infocodes/var/storage/release-dashboard/')) {
                rawPath = rawPath.replace('/infocodes/var/storage/release-dashboard/', '/data/');
            }
            var dataMarker = rawPath.indexOf('data/');
            if (dataMarker !== -1) {
                rawPath = '/' + rawPath.substring(dataMarker);
            } else if (!rawPath.startsWith('http') && !rawPath.startsWith('/')) {
                rawPath = '/' + rawPath;
            }

            var fileName = matching.name || rawPath.split('/').pop().split('\\').pop();
            var candidatePaths = [];
            if (rawPath) candidatePaths.push(rawPath);
            if (fileName) {
                var canCand = '/data/storage/processed/' + fileName;
                var legCand = '/data/output/' + fileName;
                if (!candidatePaths.includes(canCand)) candidatePaths.push(canCand);
                if (!candidatePaths.includes(legCand)) candidatePaths.push(legCand);
            }

            var fileResp = null;
            for (var i = 0; i < candidatePaths.length; i++) {
                try {
                    var r = await fetch(candidatePaths[i] + '?t=' + Date.now());
                    if (r.ok) {
                        fileResp = r;
                        break;
                    }
                } catch (e) {}
            }

            if (!fileResp) {
                throw new Error('No se pudo cargar el archivo de release en ninguna ruta candidata: ' + candidatePaths.join(', '));
            }
            var jsonData = await fileResp.json();
            var rawRecords = Array.isArray(jsonData) ? jsonData : (jsonData.data || []);
            state.metadata = jsonData._metadata || {};

            var syncLabel = state.metadata.last_sync_montmc
                ? 'Última sync Epsilon: ' + state.metadata.last_sync_montmc.replace('T', ' ').slice(0, 16)
                : '';
            document.getElementById('lastSyncInfo').textContent = syncLabel;

            state.activeIncidents = filterNonClosedIncidents(rawRecords);
            await Promise.all([
                loadReleaseOverrides(state.currentRelease),
                preloadCachedIaSummaries(state.activeIncidents)
            ]);
            updateKPIs();
            populateFilterSelects();

            if (state.activeIncidents.length === 0) {
                state.filteredIncidents = [];
                showEmptyState(
                    'Sin incidencias pendientes en ' + state.currentRelease,
                    'Todas las incidencias registradas para esta release están en estado "Cerrado" (' + rawRecords.length + ' cerradas).',
                    true
                );
                return;
            }

            showWorkspace();
            applyFilters();
        } catch (err) {
            notify('Error cargando datos de Mesa de Release: ' + (err.message || err), 'error');
        }
    }

    async function triggerSync(btn) {
        if (!btn || btn.disabled) return;
        var orig = btn.textContent;
        btn.disabled = true;
        btn.textContent = '⚡ Sincronizando...';

        try {
            var resp = await fetch('/api/sync-postmortem', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(state.currentRelease ? { release_name: state.currentRelease } : {})
            });
            var data = await resp.json();
            if (!resp.ok || !data.success) {
                throw new Error(data.error || 'Error al sincronizar con Epsilon');
            }
            notify('Sincronización OK: ' + (data.total_consultadas || 0) + ' consultadas (+' + (data.nuevas || 0) + ' nuevas, ' + (data.actualizadas || 0) + ' actualizadas).', 'success');
            await loadRelease(state.currentRelease || data.release_name);
        } catch (err) {
            notify('Error al sincronizar con Epsilon: ' + (err.message || err), 'error');
        } finally {
            btn.disabled = false;
            btn.textContent = orig;
        }
    }

    function initFloatingTooltip() {
        var tip = document.getElementById('rdFloatingTooltip');
        if (!tip) {
            tip = document.createElement('div');
            tip.id = 'rdFloatingTooltip';
            tip.className = 'rd-floating-tooltip';
            document.body.appendChild(tip);
        }

        function positionTooltip(e) {
            var offset = 14;
            var x = e.clientX + offset;
            var y = e.clientY + offset;
            var rect = tip.getBoundingClientRect();
            var winW = window.innerWidth;
            var winH = window.innerHeight;

            if (x + rect.width > winW - 12) {
                x = e.clientX - rect.width - offset;
            }
            if (y + rect.height > winH - 12) {
                y = e.clientY - rect.height - offset;
            }
            if (x < 12) x = 12;
            if (y < 12) y = 12;

            tip.style.left = x + 'px';
            tip.style.top = y + 'px';
        }

        document.addEventListener('mouseover', function (e) {
            var target = e.target.closest('[data-tooltip]');
            if (!target) return;
            var text = target.getAttribute('data-tooltip');
            if (!text || text.trim() === '' || text.trim() === '-') return;

            var title = target.getAttribute('data-tooltip-title') || '';
            var html = '';
            if (title) {
                html += '<div class="rd-floating-tooltip-title">' + escapeHtml(title) + '</div>';
            }
            html += escapeHtml(text);
            tip.innerHTML = html;
            tip.classList.add('is-visible');
            positionTooltip(e);
        });

        document.addEventListener('mousemove', function (e) {
            if (!tip.classList.contains('is-visible')) return;
            positionTooltip(e);
        });

        document.addEventListener('mouseout', function (e) {
            var target = e.target.closest('[data-tooltip]');
            if (!target) return;
            if (e.relatedTarget && target.contains(e.relatedTarget)) return;
            tip.classList.remove('is-visible');
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        initFloatingTooltip();
        var releaseSelect = document.getElementById('releaseSelect');
        var btnSync = document.getElementById('btnSyncPostmortem');
        var btnEmptySync = document.getElementById('btnEmptySync');
        var btnClear = document.getElementById('btnClearFilters');

        if (releaseSelect) {
            releaseSelect.addEventListener('change', function () {
                loadRelease(releaseSelect.value);
            });
        }
        if (btnSync) btnSync.addEventListener('click', function () { triggerSync(btnSync); });
        if (btnEmptySync) btnEmptySync.addEventListener('click', function () { triggerSync(btnEmptySync); });

        ['filterSearch', 'filterStatus', 'filterGroup', 'filterPriority', 'filterProject'].forEach(function (id) {
            var el = document.getElementById(id);
            if (el) el.addEventListener(id === 'filterSearch' ? 'input' : 'change', applyFilters);
        });

        if (btnClear) {
            btnClear.addEventListener('click', function () {
                document.getElementById('filterSearch').value = '';
                document.getElementById('filterStatus').value = '';
                document.getElementById('filterGroup').value = '';
                document.getElementById('filterPriority').value = '';
                var projEl = document.getElementById('filterProject');
                if (projEl) projEl.value = '';
                state.activeKpiFilter = null;
                updateKpiActiveUI();
                applyFilters();
            });
        }

        Array.from(document.querySelectorAll('.rd-kpi-card[data-kpi-filter]')).forEach(function (card) {
            card.addEventListener('click', function () {
                var kpi = card.getAttribute('data-kpi-filter');
                if (kpi === 'all') {
                    state.activeKpiFilter = null;
                    document.getElementById('filterStatus').value = '';
                    document.getElementById('filterPriority').value = '';
                } else if (state.activeKpiFilter === kpi) {
                    state.activeKpiFilter = null;
                } else {
                    state.activeKpiFilter = kpi;
                    if (kpi === 'in_progress' || kpi === 'resolved') {
                        document.getElementById('filterStatus').value = '';
                    }
                    if (kpi === 'crit_high') {
                        document.getElementById('filterPriority').value = '';
                    }
                }
                updateKpiActiveUI();
                applyFilters();
            });
        });

        var btnExportCsv = document.getElementById('btnExportCsv');
        if (btnExportCsv) {
            btnExportCsv.addEventListener('click', function () {
                if (!state.filteredIncidents || state.filteredIncidents.length === 0) {
                    notify('No hay incidencias visibles para exportar.', 'warning');
                    return;
                }
                var csvContent = buildExportCsv(
                    state.filteredIncidents,
                    state.iaCache,
                    state.projectsCatalog,
                    state.currentRelease,
                    state.overrides
                );
                var blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
                var url = URL.createObjectURL(blob);
                var a = document.createElement('a');
                var filename = buildExportFilename
                    ? buildExportFilename(state.currentRelease)
                    : ('mesa-release-' + (state.currentRelease || 'release').replace(/[^a-zA-Z0-9_-]/g, '_') + '.csv');
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
                notify('Exportadas ' + state.filteredIncidents.length + ' incidencias a CSV (' + filename + ').', 'success');
            });
        }

        function copyBriefingToClipboard(payload, successMsg) {
            if (window.isSecureContext && navigator.clipboard && navigator.clipboard.write && typeof ClipboardItem !== 'undefined' && payload.html) {
                try {
                    var item = new ClipboardItem({
                        'text/html': new Blob([payload.html], { type: 'text/html' }),
                        'text/plain': new Blob([payload.text], { type: 'text/plain' })
                    });
                    navigator.clipboard.write([item]).then(function () {
                        notify(successMsg, 'success');
                    }).catch(function (err) {
                        console.warn('Fallo navigator.clipboard.write con ClipboardItem, usando fallback:', err);
                        copyTextToClipboard(payload.text, successMsg);
                    });
                    return;
                } catch (err) {
                    // Fallback a texto plano
                }
            }
            copyTextToClipboard(payload.text, successMsg);
        }

        function bindBriefingButton(btnId, builderFn, label) {
            var btn = document.getElementById(btnId);
            if (!btn) return;
            btn.addEventListener('click', function () {
                if (!state.filteredIncidents || state.filteredIncidents.length === 0) {
                    notify('No hay incidencias visibles para generar el briefing.', 'warning');
                    return;
                }
                var payload = builderFn(
                    state.filteredIncidents,
                    state.iaCache,
                    state.projectsCatalog,
                    state.currentRelease,
                    state.overrides
                );
                copyBriefingToClipboard(payload, label + ' copiado para Teams (' + state.filteredIncidents.length + ' incidencias).');
            });
        }

        bindBriefingButton('btnCopyBriefing', buildMesaBriefing, 'Briefing de Mesa');
        bindBriefingButton('btnCopyBriefingSystem', buildMesaBriefingBySystem, 'Briefing por Sistema');

        function updateSortHeadersUI() {
            Array.from(document.querySelectorAll('th.rd-sortable[data-sort-key]')).forEach(function (th) {
                var key = th.getAttribute('data-sort-key');
                var ind = th.querySelector('.rd-sort-ind');
                if (state.sortKey === key) {
                    th.classList.add('is-sorted');
                    if (ind) ind.textContent = state.sortDir === 'desc' ? '▼' : '▲';
                } else {
                    th.classList.remove('is-sorted');
                    if (ind) ind.textContent = '';
                }
            });
        }

        Array.from(document.querySelectorAll('th.rd-sortable[data-sort-key]')).forEach(function (th) {
            th.addEventListener('click', function () {
                var key = th.getAttribute('data-sort-key');
                if (state.sortKey === key) {
                    state.sortDir = state.sortDir === 'asc' ? 'desc' : 'asc';
                } else {
                    state.sortKey = key;
                    state.sortDir = 'asc';
                }
                updateSortHeadersUI();
                applyFilters();
            });
        });

        var btnViewTable = document.getElementById('btnViewTable');
        var btnViewByProject = document.getElementById('btnViewByProject');
        if (btnViewTable) {
            btnViewTable.addEventListener('click', function () { setViewMode('table'); });
        }
        if (btnViewByProject) {
            btnViewByProject.addEventListener('click', function () { setViewMode('projects'); });
        }

        loadProjectsCatalog().then(function () {
            loadRelease(getUrlReleaseParam());
        });
    });
})(typeof window !== 'undefined' ? window : globalThis);
