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

    function computeOpenAgeDays(fechaEnvio, nowDate) {
        if (!fechaEnvio) return null;
        var s = String(fechaEnvio).trim();
        var dt = null;
        var m = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})(?:\s+(\d{1,2}):(\d{2})(?::(\d{2}))?)?$/);
        if (m) {
            dt = new Date(
                parseInt(m[3], 10),
                parseInt(m[2], 10) - 1,
                parseInt(m[1], 10),
                m[4] ? parseInt(m[4], 10) : 0,
                m[5] ? parseInt(m[5], 10) : 0,
                m[6] ? parseInt(m[6], 10) : 0
            );
        } else {
            var parsed = new Date(s);
            if (!isNaN(parsed.getTime())) dt = parsed;
        }
        if (!dt || isNaN(dt.getTime())) return null;
        var ref = nowDate instanceof Date ? nowDate : new Date();
        var diff = Math.floor((ref.getTime() - dt.getTime()) / 86400000);
        return diff < 0 ? 0 : diff;
    }

    function isIaCacheStale(iaData, inc) {
        if (!iaData || iaData._error || !inc) return false;
        var cachedMs = Number(iaData._cached_at_ms);
        if (!cachedMs || isNaN(cachedMs)) return false;
        var modStr = inc['fechaUltimaModificacion'];
        if (!modStr) return false;
        var modMs = Date.parse(modStr);
        if (isNaN(modMs)) return false;
        return modMs > cachedMs;
    }

    function isCriticalOrHighPriority(inc) {
        if (!inc) return false;
        var p = String(inc['Prioridad'] || inc['Urgencia'] || '').toLowerCase();
        return p.includes('p1') || p.includes('p2') || p.includes('crít') || p.includes('crit') || p.includes('alt');
    }

    function matchesKpiFilter(inc, kpiFilter) {
        if (!kpiFilter || kpiFilter === 'all') return true;
        if (!inc) return false;
        var st = String(inc['Estatus'] || '').toLowerCase();
        if (kpiFilter === 'crit_high') return isCriticalOrHighPriority(inc);
        if (kpiFilter === 'in_progress') return !st.includes('resuelt');
        if (kpiFilter === 'resolved') return st.includes('resuelt');
        return true;
    }

    function escapeCsvCell(val) {
        var str = val == null ? '' : String(val);
        str = str.replace(/\r?\n/g, ' ').replace(/"/g, '""');
        return '"' + str + '"';
    }

    function buildExportCsv(incidents, iaCache, projectsCatalog, releaseName, overrides) {
        var headers = [
            'Código Incidencia',
            'Fecha Apertura',
            'Descripción problema',
            'Prioridad / Urg.',
            'Sistema',
            'JIRA',
            'PROYECTO',
            'Acciones',
            'Status',
            'Fecha Prevista',
            'Motivo Estado Resuelto',
            'Grupo Peticionario'
        ];
        var lines = [headers.map(escapeCsvCell).join(';')];
        (incidents || []).forEach(function (inc) {
            var id = inc['ID de incidencia'] || '-';
            var iaData = iaCache ? (typeof iaCache.get === 'function' ? iaCache.get(id) : iaCache[id]) : null;
            var descBase = (iaData && !iaData._error && iaData.problema) ? iaData.problema : (inc['Descripción'] || '-');
            var producto = inc['producto'] ? String(inc['producto']).trim() : '';
            var descProblema = producto ? ('[' + producto + '] ' + descBase) : descBase;
            var prioridadUrg = inc['Prioridad'] || inc['Urgencia'] || '-';
            var sistema = inc['Grupo asignado'] || '-';
            var jiraBug = inc['JIRA'] || inc['Jira'] || inc['jira'] || '';
            var proj = resolveProjectInfo(inc, projectsCatalog, releaseName);
            var proyectoText = proj
                ? ((proj.despliegue ? '[' + proj.despliegue + '] ' : '') + proj.code + (proj.summary ? ' — ' + proj.summary : ''))
                : '-';
            var acciones = (iaData && !iaData._error && (iaData.siguienteAccion || iaData.siguiente_accion || iaData.solucion))
                || inc['detalleSolucion']
                || '-';
            var estatusLower = String(inc['Estatus'] || '').toLowerCase();
            var isResolved = estatusLower.includes('resuelt');
            var overrideEntry = overrides && overrides[id];
            var agreedFecha = (overrideEntry && overrideEntry.fecha_prevista) ? overrideEntry.fecha_prevista : '';
            var fechaPrevista = isResolved
                ? (inc['Fecha de última resolución'] || '')
                : agreedFecha;
            var motivoResuelto = inc['Motivo de estado'] || inc['MotivoEstado_Anterior'] || '-';
            var peticionario = inc['Grupo Remitente'] || '-';

            var row = [
                id,
                inc['Fecha de envío'] || '-',
                descProblema,
                prioridadUrg,
                sistema,
                jiraBug,
                proyectoText,
                acciones,
                inc['Estatus'] || '-',
                fechaPrevista,
                motivoResuelto,
                peticionario
            ];
            lines.push(row.map(escapeCsvCell).join(';'));
        });
        return '\uFEFF' + lines.join('\r\n');
    }

    function parseSortableDate(raw) {
        if (!raw) return null;
        var s = String(raw).trim();
        if (!s || s === '-') return null;
        var m = s.match(/^(\d{2})\/(\d{2})\/(\d{4})(?:\s+(\d{2}):(\d{2}))?/);
        if (m) {
            return new Date(Number(m[3]), Number(m[2]) - 1, Number(m[1]), Number(m[4] || 0), Number(m[5] || 0)).getTime();
        }
        var d = new Date(s);
        return isNaN(d.getTime()) ? null : d.getTime();
    }

    function priorityRank(inc) {
        var raw = String((inc && (inc['Prioridad'] || inc['Urgencia'])) || '').toLowerCase();
        if (raw.includes('crít') || raw.includes('crit') || raw.includes('p1')) return 1;
        if (raw.includes('alta') || raw.includes('p2')) return 2;
        if (raw.includes('medi') || raw.includes('p3')) return 3;
        if (raw.includes('baj') || raw.includes('p4')) return 4;
        return 99;
    }

    function getSortValue(inc, sortKey, projectsCatalog, releaseName, overrides) {
        var id = (inc && inc['ID de incidencia']) || '';
        if (sortKey === 'code') return id;
        if (sortKey === 'fecha_apertura') return parseSortableDate(inc && inc['Fecha de envío']);
        if (sortKey === 'prioridad') return priorityRank(inc);
        if (sortKey === 'proyecto') {
            var proj = resolveProjectInfo(inc, projectsCatalog, releaseName);
            return proj ? (proj.code + ' ' + (proj.despliegue || '') + ' ' + (proj.summary || '')) : '';
        }
        if (sortKey === 'status') return String((inc && inc['Estatus']) || '');
        if (sortKey === 'fecha_prevista') {
            var isRes = String((inc && inc['Estatus']) || '').toLowerCase().includes('resuelt');
            var rawFecha = isRes
                ? (inc && inc['Fecha de última resolución'])
                : (overrides && overrides[id] && overrides[id].fecha_prevista);
            return parseSortableDate(rawFecha);
        }
        return '';
    }

    function sortIncidents(incidents, sortKey, sortDir, projectsCatalog, releaseName, overrides) {
        if (!Array.isArray(incidents) || !sortKey) return incidents ? incidents.slice() : [];
        var dir = sortDir === 'desc' ? -1 : 1;
        return incidents.slice().sort(function (a, b) {
            var va = getSortValue(a, sortKey, projectsCatalog, releaseName, overrides);
            var vb = getSortValue(b, sortKey, projectsCatalog, releaseName, overrides);
            var aEmpty = va === null || va === undefined || va === '';
            var bEmpty = vb === null || vb === undefined || vb === '';
            if (aEmpty && bEmpty) return 0;
            if (aEmpty) return 1;
            if (bEmpty) return -1;
            if (typeof va === 'number' && typeof vb === 'number') {
                return (va - vb) * dir;
            }
            return String(va).localeCompare(String(vb), 'es', { sensitivity: 'base' }) * dir;
        });
    }

    function buildMesaBriefing(incidents, iaCache, projectsCatalog, releaseName, overrides, nowDate) {
        var list = Array.isArray(incidents) ? incidents : [];
        var today = nowDate ? new Date(nowDate) : new Date();
        var todayYmd = today.getFullYear() + '-' +
            String(today.getMonth() + 1).padStart(2, '0') + '-' +
            String(today.getDate()).padStart(2, '0');

        var buckets = {
            1: { title: 'Crítica (P1)', items: [] },
            2: { title: 'Alta (P2)', items: [] },
            3: { title: 'Media (P3)', items: [] },
            99: { title: 'Baja / Otras', items: [] }
        };
        var overdueCount = 0;
        var resolvedCount = 0;

        list.forEach(function (inc) {
            var id = inc['ID de incidencia'] || '-';
            var iaData = iaCache ? (typeof iaCache.get === 'function' ? iaCache.get(id) : iaCache[id]) : null;
            var descBase = (iaData && !iaData._error && iaData.problema) ? iaData.problema : (inc['Descripción'] || '-');
            var producto = inc['producto'] ? String(inc['producto']).trim() : '';
            var desc = (producto ? '[' + producto + '] ' : '') + String(descBase).replace(/\r?\n/g, ' ').trim();
            var acciones = (iaData && !iaData._error && (iaData.siguienteAccion || iaData.siguiente_accion || iaData.solucion))
                || inc['detalleSolucion']
                || '';
            acciones = String(acciones).replace(/\r?\n/g, ' ').trim();

            var proj = resolveProjectInfo(inc, projectsCatalog, releaseName);
            var projLabel = proj
                ? ((proj.despliegue ? '[' + proj.despliegue + '] ' : '') + proj.code + (proj.summary ? ' — ' + proj.summary : ''))
                : '';

            var estatus = inc['Estatus'] || '-';
            var isResolved = String(estatus).toLowerCase().includes('resuelt');
            if (isResolved) resolvedCount++;
            var agreedFecha = (overrides && overrides[id] && overrides[id].fecha_prevista) ? overrides[id].fecha_prevista : '';
            var fechaPrevista = isResolved ? (inc['Fecha de última resolución'] || '') : agreedFecha;
            var isOverdue = !isResolved && agreedFecha && agreedFecha < todayYmd;
            if (isOverdue) overdueCount++;

            var metaParts = [estatus];
            if (inc['Grupo asignado']) metaParts.push(inc['Grupo asignado']);
            if (projLabel) metaParts.push(projLabel);
            if (fechaPrevista) {
                metaParts.push((isOverdue ? '⚠️ VENCIDA ' : 'Prev: ') + fechaPrevista);
            } else if (!isResolved) {
                metaParts.push('Sin fecha prevista');
            }

            var line = '- **' + id + '** (' + metaParts.join(' | ') + '): ' + desc;
            if (acciones) line += ' — *Acción:* ' + acciones;

            var rank = priorityRank(inc);
            var bucketKey = buckets[rank] ? rank : 99;
            buckets[bucketKey].items.push(line);
        });

        var header = '### Briefing Mesa de Release ' + (releaseName || '') + ' (' + todayYmd + ')\n' +
            '**Total visibles:** ' + list.length +
            ' | **Resueltas:** ' + resolvedCount +
            ' | **Compromisos vencidos:** ' + overdueCount;

        var sections = [header];
        [1, 2, 3, 99].forEach(function (k) {
            if (buckets[k].items.length > 0) {
                sections.push('\n#### ' + buckets[k].title + ' (' + buckets[k].items.length + ')\n' + buckets[k].items.join('\n'));
            }
        });
        return sections.join('\n');
    }

    if (typeof module !== 'undefined' && module.exports) {
        module.exports = {
            isClosedStatus: isClosedStatus,
            filterNonClosedIncidents: filterNonClosedIncidents,
            extractProjectCode: extractProjectCode,
            resolveProjectInfo: resolveProjectInfo,
            buildFollowupText: buildFollowupText,
            computeOpenAgeDays: computeOpenAgeDays,
            isIaCacheStale: isIaCacheStale,
            matchesKpiFilter: matchesKpiFilter,
            buildExportCsv: buildExportCsv,
            sortIncidents: sortIncidents,
            buildMesaBriefing: buildMesaBriefing
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
        projectsCatalog: {},
        overrides: {},
        editingFechaId: null,
        activeKpiFilter: null,
        sortKey: null,
        sortDir: 'asc'
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
            renderTable();
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
            if (state.activeKpiFilter && !matchesKpiFilter(inc, state.activeKpiFilter)) return false;
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
            var descBase = (iaData && !iaData._error && iaData.problema) ? iaData.problema : (inc['Descripción'] || '-');
            var producto = inc['producto'] ? String(inc['producto']).trim() : '';
            var descProblema = producto ? ('[' + producto + '] ' + descBase) : descBase;
            var descCellHtml = (producto ? '<span class="rd-badge rd-badge-sistema" style="margin-right:4px;">' + escapeHtml(producto) + '</span>' : '') + escapeHtml(descBase);
            var prioridadUrg = inc['Prioridad'] || inc['Urgencia'] || '-';
            var prioBadgeClass = getPriorityBadgeClass(inc['Prioridad'], inc['Urgencia']);
            var statusBadgeClass = getStatusBadgeClass(inc['Estatus']);
            var sistema = inc['Grupo asignado'] || '-';
            var proj = resolveProjectInfo(inc, state.projectsCatalog, state.currentRelease);
            var jiraBug = inc['JIRA'] || inc['Jira'] || inc['jira'] || '';
            var jiraCell = jiraBug
                ? '<span class="rd-badge rd-badge-media">' + escapeHtml(jiraBug) + '</span>'
                : '<span style="color:#9CA3AF;">-</span>';
            var proyectoText = proj
                ? ((proj.despliegue ? '[' + proj.despliegue + '] ' : '') + proj.code + (proj.summary ? ' — ' + proj.summary : ''))
                : '-';
            var despliegueLower = proj && proj.despliegue ? String(proj.despliegue).toLowerCase() : '';
            var despliegueBadgeClass = 'rd-badge-despliegue-otro';
            if (despliegueLower.includes('complet')) despliegueBadgeClass = 'rd-badge-despliegue-completo';
            else if (despliegueLower.includes('pilot')) despliegueBadgeClass = 'rd-badge-despliegue-piloto';
            else if (despliegueLower.includes('ocult')) despliegueBadgeClass = 'rd-badge-despliegue-oculto';
            else if (despliegueLower.includes('pap') || despliegueLower.includes('técnic') || despliegueLower.includes('tecnic')) despliegueBadgeClass = 'rd-badge-despliegue-pap';
            var proyectoCell = proj
                ? '<div class="rd-cell-clamp">' +
                  (proj.despliegue ? '<span class="rd-badge ' + despliegueBadgeClass + '" style="margin-right:4px;">' + escapeHtml(proj.despliegue) + '</span>' : '') +
                  '<span class="rd-badge rd-badge-jira">' + escapeHtml(proj.code) + '</span></div>'
                : '<span style="color:#9CA3AF;">-</span>';
            var acciones = (iaData && !iaData._error && (iaData.siguienteAccion || iaData.siguiente_accion || iaData.solucion))
                || inc['detalleSolucion']
                || '-';
            var estatusLower = String(inc['Estatus'] || '').toLowerCase();
            var isResolved = estatusLower.includes('resuelt');
            var overrideEntry = state.overrides && state.overrides[id];
            var agreedFecha = (overrideEntry && overrideEntry.fecha_prevista) ? overrideEntry.fecha_prevista : '';
            var fechaPrevista = isResolved
                ? (inc['Fecha de última resolución'] || '')
                : agreedFecha;
            var motivoResuelto = inc['Motivo de estado'] || inc['MotivoEstado_Anterior'] || '-';
            var peticionario = inc['Grupo Remitente'] || '-';

            var rowClasses = [];
            if (isSelected) rowClasses.push('is-selected');
            if (prioBadgeClass === 'rd-badge-critica') rowClasses.push('rd-row-critica');
            else if (prioBadgeClass === 'rd-badge-alta') rowClasses.push('rd-row-alta');
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
                fechaPrevistaCell = '<button type="button" class="rd-badge rd-badge-fecha-acordada" data-edit-fecha="' + escapeHtml(id) + '" title="Fecha prevista acordada (clic para editar)">' + escapeHtml(agreedFecha) + '</button>';
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

            var rowHtml = '<tr data-inc-id="' + escapeHtml(id) + '"' + rowClassAttr + ' aria-expanded="' + (isSelected ? 'true' : 'false') + '">' +
                '<td style="white-space:nowrap;"><span class="rd-badge rd-badge-code">' + (isSelected ? '▾ ' : '▸ ') + escapeHtml(id) + '</span></td>' +
                '<td style="font-size:11.5px; min-width:78px;">' + escapeHtml(fechaApertura) + agingHtml + '</td>' +
                '<td style="min-width:140px; max-width:220px;" title="' + escapeHtml(descProblema) + '"><div class="rd-cell-clamp">' + descCellHtml + '</div></td>' +
                '<td style="white-space:nowrap;"><span class="rd-badge ' + prioBadgeClass + '">' + escapeHtml(prioridadUrg) + '</span></td>' +
                '<td style="max-width:120px;">' + sistemaCell + '</td>' +
                '<td style="white-space:nowrap;">' + jiraCell + '</td>' +
                '<td style="min-width:120px; max-width:190px;" title="' + escapeHtml(proyectoText) + '">' + proyectoCell + '</td>' +
                '<td style="min-width:150px; max-width:230px;" title="' + escapeHtml(acciones) + '"><div class="rd-cell-clamp">' + escapeHtml(acciones) + '</div>' + staleBadgeHtml + '</td>' +
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
            '<div id="detailBody" class="rd-detail-body">' +
                renderIaSection(id, iaData, isLoadingIa) +
            '</div>' +
            '<div class="rd-detail-inline-header">' +
                '<span>Seguimiento · ' + escapeHtml(id) + '</span>' +
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
                var safeRel = (state.currentRelease || 'release').replace(/[^a-zA-Z0-9_-]/g, '_');
                a.href = url;
                a.download = 'mesa-release-' + safeRel + '.csv';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
                notify('Exportadas ' + state.filteredIncidents.length + ' incidencias a CSV.', 'success');
            });
        }

        var btnCopyBriefing = document.getElementById('btnCopyBriefing');
        if (btnCopyBriefing) {
            btnCopyBriefing.addEventListener('click', function () {
                if (!state.filteredIncidents || state.filteredIncidents.length === 0) {
                    notify('No hay incidencias visibles para generar el briefing.', 'warning');
                    return;
                }
                var text = buildMesaBriefing(
                    state.filteredIncidents,
                    state.iaCache,
                    state.projectsCatalog,
                    state.currentRelease,
                    state.overrides
                );
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    navigator.clipboard.writeText(text).then(function () {
                        notify('Briefing de Mesa copiado (' + state.filteredIncidents.length + ' incidencias).', 'success');
                    }).catch(function () {
                        notify('No se pudo copiar al portapapeles.', 'error');
                    });
                } else {
                    var ta = document.createElement('textarea');
                    ta.value = text;
                    ta.style.position = 'fixed';
                    ta.style.opacity = '0';
                    document.body.appendChild(ta);
                    ta.select();
                    try {
                        document.execCommand('copy');
                        notify('Briefing de Mesa copiado (' + state.filteredIncidents.length + ' incidencias).', 'success');
                    } catch (err) {
                        notify('No se pudo copiar al portapapeles.', 'error');
                    }
                    document.body.removeChild(ta);
                }
            });
        }

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

        loadProjectsCatalog().then(function () {
            loadRelease(getUrlReleaseParam());
        });
    });
})(typeof window !== 'undefined' ? window : globalThis);
