(function (global) {
    'use strict';

    function isClosedStatus(status) {
        if (!status) return false;
        return String(status).trim().toLowerCase() === 'cerrado';
    }

    function filterNonClosedIncidents(records) {
        if (!Array.isArray(records)) return [];
        return records.filter(function (rec) {
            return rec && !isClosedStatus(rec['Estatus']);
        });
    }

    function escapeHtml(value) {
        return String(value == null ? '' : value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function extractProjectCode(incident) {
        if (!incident || typeof incident !== 'object') return null;
        var raw = String(incident['prj'] || '') + ' ' + String(incident['Descripción'] || '');
        var match = raw.match(/\b(PRJ-\d+)\b/i);
        return match ? match[1].toUpperCase() : null;
    }

    function resolveProjectInfo(incident, catalog, releaseName) {
        var code = extractProjectCode(incident);
        if (!code) return null;
        var entry = null;
        if (catalog && typeof catalog === 'object') {
            if (releaseName && catalog.by_release && catalog.by_release[releaseName] && catalog.by_release[releaseName][code]) {
                entry = catalog.by_release[releaseName][code];
            } else if (catalog.projects && catalog.projects[code]) {
                entry = catalog.projects[code];
            } else if (catalog[code] && typeof catalog[code] === 'object' && catalog[code].summary !== undefined) {
                entry = catalog[code];
            }
        }
        return {
            code: code,
            summary: entry ? (entry.summary || '') : '',
            despliegue: entry ? (entry.despliegue || '') : '',
            descripcion: entry ? (entry.descripcion || '') : ''
        };
    }

    function buildFollowupText(incident, iaData, releaseName, catalog) {
        var id = incident['ID de incidencia'] || '-';
        var estatus = incident['Estatus'] || '-';
        var prio = incident['Prioridad'] || incident['Urgencia'] || '-';
        var grupo = incident['Grupo Resolutor'] || incident['Grupo asignado'] || '-';
        var resp = incident['Grupo Remitente'] || '-';
        var desc = incident['Descripción'] || '-';
        var proj = resolveProjectInfo(incident, catalog, releaseName);

        var lines = [
            '[' + (releaseName || 'Release') + '] ' + id + ' (' + estatus + ' | ' + prio + ')',
            'Descripción: ' + desc
        ];
        if (proj) {
            lines.push('Proyecto: ' + proj.code + (proj.summary ? ' — ' + proj.summary : '') + (proj.despliegue ? ' [' + proj.despliegue + ']' : ''));
        }
        lines.push('Grupo soporte/resolutor: ' + grupo + ' | Responsable: ' + resp);

        if (iaData && !iaData._error) {
            var sintesis = iaData.resumenEjecutivo || iaData.resumen || iaData.sintesis || '';
            var problema = iaData.problema || '';
            var impacto = iaData.impacto || '';
            var causa = iaData.causa || iaData.causaRaiz || '';
            var solucion = iaData.solucion || '';
            var siguiente = iaData.siguienteAccion || iaData.siguiente_accion || '';
            if (sintesis) lines.push('Resumen IA: ' + sintesis);
            if (problema) lines.push('Problema Detectado: ' + problema);
            if (impacto) lines.push('Impacto: ' + impacto);
            if (causa) lines.push('Causa: ' + causa);
            if (solucion) lines.push('Solución: ' + solucion);
            if (siguiente) lines.push('Siguiente acción: ' + siguiente);
        }
        return lines.join('\n');
    }

    if (typeof module !== 'undefined' && module.exports) {
        module.exports = {
            isClosedStatus: isClosedStatus,
            filterNonClosedIncidents: filterNonClosedIncidents,
            extractProjectCode: extractProjectCode,
            resolveProjectInfo: resolveProjectInfo,
            buildFollowupText: buildFollowupText
        };
    }

    if (typeof document === 'undefined') return;

    var state = {
        currentRelease: null,
        postmortemFiles: [],
        activeIncidents: [],
        filteredIncidents: [],
        selectedId: null,
        iaCache: new Map(),
        iaInFlight: new Set(),
        metadata: {},
        projectsCatalog: {}
    };

    async function loadProjectsCatalog() {
        try {
            var resp = await fetch('/data/projects_catalog.json?t=' + Date.now());
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

    function getStatusBadgeClass(estatus) {
        var s = String(estatus || '').toLowerCase();
        if (s.includes('resuelt')) return 'rd-badge-resuelto';
        if (s.includes('pend')) return 'rd-badge-pendiente';
        if (s.includes('curso') || s.includes('progreso')) return 'rd-badge-curso';
        return 'rd-badge-asignado';
    }

    function getPriorityBadgeClass(prio, urg) {
        var p = String(prio || urg || '').toLowerCase();
        if (p.includes('p1') || p.includes('crít') || p.includes('crit')) return 'rd-badge-critica';
        if (p.includes('p2') || p.includes('alt')) return 'rd-badge-alta';
        return 'rd-badge-media';
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
        if (typeof global.RAW_RELEASES !== 'undefined' && Array.isArray(global.RAW_RELEASES)) {
            for (var i = global.RAW_RELEASES.length - 1; i >= 0; i--) {
                var rName = global.RAW_RELEASES[i] && global.RAW_RELEASES[i][0];
                if (rName && !seen.has(rName)) {
                    seen.add(rName);
                    ordered.push(rName);
                }
            }
        }
        (files || []).forEach(function (f) {
            if (f && f.release_name && !seen.has(f.release_name)) {
                seen.add(f.release_name);
                ordered.unshift(f.release_name);
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

        state.activeIncidents.forEach(function (inc) {
            if (inc['Estatus']) statusSet.add(inc['Estatus']);
            if (inc['Grupo asignado']) groupSet.add(inc['Grupo asignado']);
            if (inc['Grupo Resolutor']) groupSet.add(inc['Grupo Resolutor']);
            if (inc['Prioridad']) prioSet.add(inc['Prioridad']);
            else if (inc['Urgencia']) prioSet.add(inc['Urgencia']);
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
            groupSel.innerHTML = '<option value="">Todos los grupos soporte</option>' +
                Array.from(groupSet).sort().map(function (g) {
                    return '<option value="' + escapeHtml(g) + '">' + escapeHtml(g) + '</option>';
                }).join('');
        }
        if (prioSel) {
            prioSel.innerHTML = '<option value="">Todas las prioridades</option>' +
                Array.from(prioSet).sort().map(function (p) {
                    return '<option value="' + escapeHtml(p) + '">' + escapeHtml(p) + '</option>';
                }).join('');
        }
        if (projectSel) {
            projectSel.innerHTML = '<option value="">Todos los proyectos</option>' +
                Array.from(projectSet).sort().map(function (code) {
                    var info = resolveProjectInfo({ 'Descripción': code }, state.projectsCatalog, state.currentRelease);
                    var label = info && info.summary ? (code + ' — ' + info.summary) : code;
                    return '<option value="' + escapeHtml(code) + '">' + escapeHtml(label) + '</option>';
                }).join('');
        }
    }

    function updateKPIs() {
        var total = state.activeIncidents.length;
        var critHigh = 0;
        var inProgress = 0;
        var resolvedPendingClose = 0;

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
            }
        });

        document.getElementById('kpiActiveTotal').textContent = total;
        document.getElementById('kpiCriticalHigh').textContent = critHigh;
        document.getElementById('kpiInProgress').textContent = inProgress;
        document.getElementById('kpiResolvedPendingClose').textContent = resolvedPendingClose;
    }

    function applyFilters() {
        var search = (document.getElementById('filterSearch').value || '').trim().toLowerCase();
        var status = document.getElementById('filterStatus').value;
        var group = document.getElementById('filterGroup').value;
        var prio = document.getElementById('filterPriority').value;
        var projectEl = document.getElementById('filterProject');
        var project = projectEl ? projectEl.value : '';

        state.filteredIncidents = state.activeIncidents.filter(function (inc) {
            if (status && inc['Estatus'] !== status) return false;
            if (group && inc['Grupo asignado'] !== group && inc['Grupo Resolutor'] !== group) return false;
            if (prio) {
                var incPrio = inc['Prioridad'] || inc['Urgencia'] || '';
                if (incPrio !== prio) return false;
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
                    proj ? proj.code : '',
                    proj ? proj.summary : ''
                ].join(' ').toLowerCase();
                if (!hay.includes(search)) return false;
            }
            return true;
        });

        renderTable();
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
            var descProblema = (iaData && !iaData._error && iaData.problema) ? iaData.problema : (inc['Descripción'] || '-');
            var prioridadUrg = inc['Prioridad'] || inc['Urgencia'] || '-';
            var prioBadgeClass = getPriorityBadgeClass(inc['Prioridad'], inc['Urgencia']);
            var statusBadgeClass = getStatusBadgeClass(inc['Estatus']);
            var sistema = inc['producto'] || inc['Grupo Resolutor'] || inc['Grupo asignado'] || '-';
            var proj = resolveProjectInfo(inc, state.projectsCatalog, state.currentRelease);
            var jiraCell = proj
                ? '<span class="rd-badge rd-badge-jira">' + escapeHtml(proj.code) + '</span>'
                : '<span style="color:#9CA3AF;">-</span>';
            var proyectoText = proj
                ? (proj.summary ? (proj.code + ' — ' + proj.summary) : proj.code)
                : '-';
            var acciones = (iaData && !iaData._error && (iaData.siguienteAccion || iaData.siguiente_accion || iaData.solucion))
                || inc['detalleSolucion']
                || '-';
            var estatusLower = String(inc['Estatus'] || '').toLowerCase();
            var fechaPrevista = estatusLower.includes('resuelt')
                ? (inc['Fecha de última resolución'] || '')
                : '';
            var motivoResuelto = inc['Motivo de estado'] || inc['MotivoEstado_Anterior'] || '-';
            var peticionario = inc['Grupo Remitente'] || '-';

            var rowClasses = [];
            if (isSelected) rowClasses.push('is-selected');
            if (prioBadgeClass === 'rd-badge-critica') rowClasses.push('rd-row-critica');
            else if (prioBadgeClass === 'rd-badge-alta') rowClasses.push('rd-row-alta');
            if (estatusLower.includes('resuelt')) rowClasses.push('rd-row-resuelto');
            var rowClassAttr = rowClasses.length ? ' class="' + rowClasses.join(' ') + '"' : '';

            var sistemaCell = sistema !== '-'
                ? '<span class="rd-badge rd-badge-sistema" title="' + escapeHtml(sistema) + '">' + escapeHtml(sistema) + '</span>'
                : '<span style="color:#9CA3AF;">-</span>';
            var fechaPrevistaCell = fechaPrevista
                ? '<span class="rd-badge rd-badge-fecha">' + escapeHtml(fechaPrevista) + '</span>'
                : '';

            var rowHtml = '<tr data-inc-id="' + escapeHtml(id) + '"' + rowClassAttr + ' aria-expanded="' + (isSelected ? 'true' : 'false') + '">' +
                '<td style="white-space:nowrap;"><span class="rd-badge rd-badge-code">' + (isSelected ? '▾ ' : '▸ ') + escapeHtml(id) + '</span></td>' +
                '<td style="font-size:11.5px; min-width:78px;">' + escapeHtml(fechaApertura) + '</td>' +
                '<td style="min-width:140px; max-width:220px;" title="' + escapeHtml(descProblema) + '"><div class="rd-cell-clamp">' + escapeHtml(descProblema) + '</div></td>' +
                '<td style="white-space:nowrap;"><span class="rd-badge ' + prioBadgeClass + '">' + escapeHtml(prioridadUrg) + '</span></td>' +
                '<td style="max-width:120px;">' + sistemaCell + '</td>' +
                '<td style="white-space:nowrap;">' + jiraCell + '</td>' +
                '<td style="min-width:120px; max-width:190px;" title="' + escapeHtml(proyectoText) + '"><div class="rd-cell-clamp">' + escapeHtml(proyectoText) + '</div></td>' +
                '<td style="min-width:150px; max-width:230px;" title="' + escapeHtml(acciones) + '"><div class="rd-cell-clamp">' + escapeHtml(acciones) + '</div></td>' +
                '<td><span class="rd-badge ' + statusBadgeClass + '">' + escapeHtml(inc['Estatus'] || '-') + '</span></td>' +
                '<td style="font-size:11.5px; min-width:78px;">' + fechaPrevistaCell + '</td>' +
                '<td style="max-width:130px;">' + escapeHtml(motivoResuelto) + '</td>' +
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

        var selectedId = state.selectedId;
        if (selectedId) {
            var copyBtn = document.getElementById('btnCopyFollowup');
            if (copyBtn) {
                copyBtn.addEventListener('click', async function (ev) {
                    ev.stopPropagation();
                    var inc = state.activeIncidents.find(function (r) { return r['ID de incidencia'] === selectedId; });
                    if (!inc) return;
                    var text = buildFollowupText(inc, state.iaCache.get(selectedId), state.currentRelease, state.projectsCatalog);
                    try {
                        await navigator.clipboard.writeText(text);
                        notify('Seguimiento de ' + selectedId + ' copiado al portapapeles.', 'success');
                    } catch (_) {
                        notify('No se pudo acceder al portapapeles.', 'warning');
                    }
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

        return '<div class="rd-detail-inline-card">' +
            '<div class="rd-detail-inline-header">' +
                '<span>Seguimiento · ' + escapeHtml(id) + '</span>' +
                '<div class="rd-detail-inline-actions">' +
                    '<button id="btnCopyFollowup" class="rd-btn rd-btn-dark">📋 Copiar seguimiento</button>' +
                    '<button id="btnCloseDetail" class="rd-btn" title="Cerrar desplegable">✕ Cerrar</button>' +
                '</div>' +
            '</div>' +
            '<div id="detailBody" class="rd-detail-body">' +
                renderIaSection(id, iaData, isLoadingIa) +
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
        updateUrlReleaseParam(releaseName);

        try {
            var idxResp = await fetch('/data/output/index.json?t=' + Date.now());
            var idxData = idxResp.ok ? await idxResp.json() : {};
            var files = (idxData.postmortem && idxData.postmortem.files) || [];
            state.postmortemFiles = files;

            var allReleases = collectAvailableReleases(files);
            if (!state.currentRelease && allReleases.length > 0) {
                state.currentRelease = allReleases[0];
                updateUrlReleaseParam(state.currentRelease);
            }
            populateReleaseSelect(allReleases, state.currentRelease);

            var matching = files.find(function (f) { return f.release_name === state.currentRelease; });
            if (!matching) {
                state.activeIncidents = [];
                state.filteredIncidents = [];
                updateKPIs();
                populateFilterSelects();
                document.getElementById('lastSyncInfo').textContent = '';
                showEmptyState(
                    'Release ' + (state.currentRelease || '') + ' sin datos locales',
                    'Aún no existe un dataset local para esta release. Pulsa "Sincronizar MonTMC" para obtener sus incidencias activas.',
                    true
                );
                return;
            }

            var path = matching.path.startsWith('http') ? matching.path : '/' + matching.path;
            var fileResp = await fetch(path + '?t=' + Date.now());
            var jsonData = await fileResp.json();
            var rawRecords = Array.isArray(jsonData) ? jsonData : (jsonData.data || []);
            state.metadata = jsonData._metadata || {};

            var syncLabel = state.metadata.last_sync_montmc
                ? 'Última sync MonTMC: ' + state.metadata.last_sync_montmc.replace('T', ' ').slice(0, 16)
                : '';
            document.getElementById('lastSyncInfo').textContent = syncLabel;

            state.activeIncidents = filterNonClosedIncidents(rawRecords);
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
                throw new Error(data.error || 'Error al sincronizar con MonTMC');
            }
            notify('Sincronización OK: ' + (data.total_consultadas || 0) + ' consultadas (+' + (data.nuevas || 0) + ' nuevas, ' + (data.actualizadas || 0) + ' actualizadas).', 'success');
            await loadRelease(state.currentRelease || data.release_name);
        } catch (err) {
            notify('Error al sincronizar con MonTMC: ' + (err.message || err), 'error');
        } finally {
            btn.disabled = false;
            btn.textContent = orig;
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
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
                applyFilters();
            });
        }

        loadProjectsCatalog().then(function () {
            loadRelease(getUrlReleaseParam());
        });
    });
})(typeof window !== 'undefined' ? window : globalThis);
