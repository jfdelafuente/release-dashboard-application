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
        var prjField = String(incident['prj'] || '').trim();
        if (prjField && /^[A-Z0-9]+-\d+$/i.test(prjField)) {
            return prjField.toUpperCase();
        }
        var raw = prjField + ' ' + String(incident['Descripción'] || '');
        var match = raw.match(/\b((?:PRJ|AB2CJ|OCA)-\d+)\b/i);
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

        var inact = computeInactivityStatus(incident);
        if (inact) {
            lines.push('Alerta inactividad: ⏸ ' + inact.label + ' (' + inact.tooltip + ')');
        }
        var pp = detectPingPong(incident, null, iaData);
        if (pp) {
            lines.push('Alerta reasignación: 🏓 ' + pp.label + ' (' + pp.tooltip + ')');
        }

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

        var motivo = incident['Motivo de estado'] || incident['MotivoEstado_Anterior'] || incident['motivoEstado'] || '';
        if (motivo) lines.push('Motivo estado: ' + motivo);
        if (incident['detalleSolucion'] && (!iaData || !iaData.solucion)) {
            lines.push('Solución Remedy: ' + incident['detalleSolucion']);
        }
        return lines.join('\n');
    }

    function parseDateRobust(dateStr) {
        if (!dateStr) return null;
        var s = String(dateStr).trim();
        if (!s || s === '-') return null;
        var m = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})(?:\s+(\d{1,2}):(\d{2})(?::(\d{2}))?)?$/);
        if (m) {
            var dt = new Date(
                parseInt(m[3], 10),
                parseInt(m[2], 10) - 1,
                parseInt(m[1], 10),
                m[4] ? parseInt(m[4], 10) : 0,
                m[5] ? parseInt(m[5], 10) : 0,
                m[6] ? parseInt(m[6], 10) : 0
            );
            if (!isNaN(dt.getTime())) return dt;
        }
        var parsedMs = Date.parse(s);
        if (!isNaN(parsedMs)) return new Date(parsedMs);
        var parsed = new Date(s);
        if (!isNaN(parsed.getTime())) return parsed;
        return null;
    }

    function computeOpenAgeDays(fechaEnvio, nowDate) {
        var dt = parseDateRobust(fechaEnvio);
        if (!dt) return null;
        var ref = nowDate instanceof Date ? nowDate : new Date();
        var diff = Math.floor((ref.getTime() - dt.getTime()) / 86400000);
        return diff < 0 ? 0 : diff;
    }

    function computeInactivityStatus(incident, nowDate) {
        if (!incident || typeof incident !== 'object') return null;
        var st = String(incident['Estatus'] || '').toLowerCase();
        if (st.includes('resuelt') || st.includes('cerrad')) return null;

        var modStr = incident['fechaUltimaModificacion'] ||
                     incident['Fecha de última modificación'] ||
                     incident['fechaModificacion'] ||
                     incident['last_modified'] ||
                     incident['Fecha de envío'];
        if (!modStr) return null;

        var dt = parseDateRobust(modStr);
        if (!dt) return null;

        var ref = nowDate instanceof Date ? nowDate : new Date();
        var diffMs = ref.getTime() - dt.getTime();
        if (diffMs < 0) diffMs = 0;
        var diffHours = Math.floor(diffMs / 3600000);
        var diffDays = Math.floor(diffMs / 86400000);

        if (diffHours < 48) return null;

        var isCrit = diffHours >= 72;
        var level = isCrit ? 'crit' : 'warn';
        var label = diffDays >= 2 ? (diffDays + 'd sin mov.') : (diffHours + 'h sin mov.');
        var tooltip = 'Sin actividad registrada en Remedy desde hace ' + (diffDays >= 1 ? (diffDays + ' días (' + diffHours + 'h)') : (diffHours + ' horas')) + ' (última mod.: ' + modStr + ').';

        return {
            hours: diffHours,
            days: diffDays,
            level: level,
            label: label,
            tooltip: tooltip
        };
    }

    function detectPingPong(incident, remedyCacheItem, iaData) {
        if (!incident || typeof incident !== 'object') return null;

        var gAsignado = String(incident['Grupo asignado'] || incident['grupoAsignado'] || '').trim();
        var gResolutor = String(incident['Grupo Resolutor'] || incident['grupoResolutor'] || '').trim();
        var gRemitente = String(incident['Grupo Remitente'] || incident['grupoRemitente'] || '').trim();

        var groups = [];
        if (gRemitente && gRemitente !== '-') groups.push(gRemitente);
        if (gResolutor && gResolutor !== '-' && groups.indexOf(gResolutor) === -1) groups.push(gResolutor);
        if (gAsignado && gAsignado !== '-' && groups.indexOf(gAsignado) === -1) groups.push(gAsignado);

        if (incident['pingPong'] === true || incident['ping_pong'] === true || Number(incident['reasignaciones'] || 0) > 1 || Number(incident['numReasignaciones'] || 0) > 1) {
            return {
                isPingPong: true,
                count: Number(incident['reasignaciones'] || incident['numReasignaciones'] || 2),
                label: 'Ping-pong',
                groups: groups,
                tooltip: 'Ticket reasignado múltiples veces entre grupos (' + groups.join(' ↔ ') + ').'
            };
        }

        if (gAsignado && gResolutor && gAsignado !== '-' && gResolutor !== '-' && gAsignado.toLowerCase() !== gResolutor.toLowerCase()) {
            return {
                isPingPong: true,
                count: 2,
                label: 'Ping-pong',
                groups: groups,
                tooltip: 'Posible discrepancia/rebote: Grupo asignado (' + gAsignado + ') difiere del Grupo Resolutor (' + gResolutor + ').'
            };
        }

        if (remedyCacheItem && Array.isArray(remedyCacheItem.worklogs) && remedyCacheItem.worklogs.length > 0) {
            var transferCount = 0;
            var transferRegex = /\b(?:reasigna\w*|transfer\w*|devuelt\w*|derivad\w*|cambio de grupo|cambio asignaci[oó]n)\b/i;
            remedyCacheItem.worklogs.forEach(function (wl) {
                var txt = typeof wl === 'string' ? wl : (wl && (wl.texto || wl.text || wl.descripcion || ''));
                if (transferRegex.test(txt)) {
                    transferCount++;
                }
            });
            if (transferCount >= 2) {
                return {
                    isPingPong: true,
                    count: transferCount,
                    label: 'Ping-pong',
                    groups: groups,
                    tooltip: 'Detectadas ' + transferCount + ' transferencias/devoluciones de grupo en el historial de Remedy.'
                };
            }
        }

        if (iaData && !iaData._error) {
            var iaText = (iaData.problema || '') + ' ' + (iaData.siguienteAccion || '') + ' ' + (Array.isArray(iaData.bloqueos) ? iaData.bloqueos.join(' ') : '');
            if (/\b(?:ping-pong|ping pong|reasignado entre|rebote entre grupos|devuelto al grupo)\b/i.test(iaText)) {
                return {
                    isPingPong: true,
                    count: 2,
                    label: 'Ping-pong',
                    groups: groups,
                    tooltip: 'Resumen IA alerta de bloqueo por transferencias o ping-pong entre grupos.'
                };
            }
        }

        return null;
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

    function getFechaPrevistaStatus(inc, overrides, nowDate) {
        if (!inc) return 'missing';
        var st = String(inc['Estatus'] || '').toLowerCase();
        if (st.includes('resuelt')) return 'resolved';
        var id = inc['ID de incidencia'] || '';
        var agreedFecha = (overrides && overrides[id] && overrides[id].fecha_prevista) ? String(overrides[id].fecha_prevista).trim() : '';
        if (!agreedFecha) return 'missing';
        var today = nowDate ? new Date(nowDate) : new Date();
        var todayYmd = today.getFullYear() + '-' +
            String(today.getMonth() + 1).padStart(2, '0') + '-' +
            String(today.getDate()).padStart(2, '0');
        var tomorrow = new Date(today.getFullYear(), today.getMonth(), today.getDate() + 1);
        var tomorrowYmd = tomorrow.getFullYear() + '-' +
            String(tomorrow.getMonth() + 1).padStart(2, '0') + '-' +
            String(tomorrow.getDate()).padStart(2, '0');
        if (agreedFecha < todayYmd) return 'overdue';
        if (agreedFecha <= tomorrowYmd) return 'due_soon';
        return 'ok';
    }

    function matchesKpiFilter(inc, kpiFilter, overrides, nowDate) {
        if (!kpiFilter || kpiFilter === 'all') return true;
        if (!inc) return false;
        var st = String(inc['Estatus'] || '').toLowerCase();
        if (kpiFilter === 'crit_high') return isCriticalOrHighPriority(inc);
        if (kpiFilter === 'in_progress') return !st.includes('resuelt');
        if (kpiFilter === 'resolved') return st.includes('resuelt');
        if (kpiFilter === 'overdue_or_missing') {
            var fst = getFechaPrevistaStatus(inc, overrides, nowDate);
            return fst === 'overdue' || fst === 'missing';
        }
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
            var prioVal = (inc['Prioridad'] && String(inc['Prioridad']).trim()) || '';
            var urgVal = (inc['Urgencia'] && String(inc['Urgencia']).trim()) || '';
            var prioridadUrg = (prioVal && urgVal && prioVal.toLowerCase() !== urgVal.toLowerCase())
                ? (prioVal + ' / ' + urgVal)
                : (prioVal || urgVal || '-');
            var sistema = (inc['Grupo asignado'] && String(inc['Grupo asignado']).trim()) ||
                          (inc['Grupo Resolutor'] && String(inc['Grupo Resolutor']).trim()) ||
                          (inc['Sistema'] && String(inc['Sistema']).trim()) ||
                          (inc['sistema'] && String(inc['sistema']).trim()) ||
                          (inc['producto'] && String(inc['producto']).trim()) || '-';
            var jiraBug = inc['JIRA'] || inc['Jira'] || inc['jira'] || '';
            var proj = resolveProjectInfo(inc, projectsCatalog, releaseName);
            var proyectoText = proj
                ? ((proj.despliegue ? '[' + proj.despliegue + '] ' : '') + proj.code + (proj.summary ? ' — ' + proj.summary : ''))
                : '-';
            var acciones = (iaData && !iaData._error && (iaData.siguienteAccion || iaData.siguiente_accion || iaData.solucion))
                || inc['detalleSolucion']
                || '-';
            var estatusLower = String(inc['Estatus'] || '').toLowerCase();
            var isResolved = estatusLower.includes('resuelt') || estatusLower.includes('cerrad');
            var overrideEntry = overrides && overrides[id];
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

    function buildExportFilename(releaseName, date) {
        var safeRel = (releaseName || 'release').replace(/[^a-zA-Z0-9_-]/g, '_');
        var d = (date instanceof Date && !isNaN(date.getTime())) ? date : new Date();
        var pad = function (n) { return String(n).padStart(2, '0'); };
        var yyyy = d.getFullYear();
        var mm = pad(d.getMonth() + 1);
        var dd = pad(d.getDate());
        var hh = pad(d.getHours());
        var min = pad(d.getMinutes());
        var ss = pad(d.getSeconds());
        return 'mesa-release-' + safeRel + '_' + yyyy + mm + dd + '_' + hh + min + ss + '.csv';
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
        if (sortKey === 'sistema') {
            return (inc && (
                (inc['Grupo asignado'] && String(inc['Grupo asignado']).trim()) ||
                (inc['Grupo Resolutor'] && String(inc['Grupo Resolutor']).trim()) ||
                (inc['Sistema'] && String(inc['Sistema']).trim()) ||
                (inc['sistema'] && String(inc['sistema']).trim()) ||
                (inc['producto'] && String(inc['producto']).trim())
            )) || '';
        }
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

    function getBriefingTodayYmd(nowDate) {
        var today = nowDate ? new Date(nowDate) : new Date();
        return today.getFullYear() + '-' +
            String(today.getMonth() + 1).padStart(2, '0') + '-' +
            String(today.getDate()).padStart(2, '0');
    }

    function formatBriefingIncidentInfo(inc, iaCache, projectsCatalog, releaseName, overrides, todayYmd, includePriority) {
        var id = inc['ID de incidencia'] || '-';
        var iaData = iaCache ? (typeof iaCache.get === 'function' ? iaCache.get(id) : iaCache[id]) : null;
        var hasIa = Boolean(iaData && !iaData._error);

        var problemaBase = (hasIa && (iaData.problema || iaData.problemaDetectado))
            ? (iaData.problema || iaData.problemaDetectado)
            : (inc['Descripción'] || '-');
        var producto = inc['producto'] ? String(inc['producto']).trim() : '';
        var problema = (producto ? '[' + producto + '] ' : '') + String(problemaBase).replace(/\r?\n/g, ' ').trim();

        var impactoRaw = (hasIa && (iaData.impacto || iaData.impactoNegocio || iaData.impacto_negocio))
            || inc['Impacto']
            || inc['impacto']
            || '';
        var impacto = String(impactoRaw).replace(/\r?\n/g, ' ').trim();

        var acciones = (hasIa && (iaData.siguienteAccion || iaData.siguiente_accion || iaData.solucion))
            || inc['detalleSolucion']
            || '';
        acciones = String(acciones).replace(/\r?\n/g, ' ').trim();

        var proj = resolveProjectInfo(inc, projectsCatalog, releaseName);
        var projLabel = proj
            ? ((proj.despliegue ? '[' + proj.despliegue + '] ' : '') + proj.code + (proj.summary ? ' — ' + proj.summary : ''))
            : '';

        var estatus = inc['Estatus'] || '-';
        var isResolved = String(estatus).toLowerCase().includes('resuelt');
        var agreedFecha = (overrides && overrides[id] && overrides[id].fecha_prevista) ? overrides[id].fecha_prevista : '';
        var fechaPrevista = isResolved ? (inc['Fecha de última resolución'] || '') : agreedFecha;
        var isOverdue = !isResolved && agreedFecha && agreedFecha < todayYmd;

        var metaText = [];
        var metaHtml = [];
        if (includePriority) {
            var prioLabel = inc['Prioridad'] || inc['Urgencia'] || '-';
            metaText.push(prioLabel);
            metaHtml.push(escapeHtml(prioLabel));
        }
        metaText.push(estatus);
        metaHtml.push(escapeHtml(estatus));
        if (!includePriority && inc['Grupo asignado']) {
            metaText.push(inc['Grupo asignado']);
            metaHtml.push(escapeHtml(inc['Grupo asignado']));
        }
        if (projLabel) {
            metaText.push(projLabel);
            metaHtml.push(escapeHtml(projLabel));
        }
        if (fechaPrevista) {
            var fechaTag = (isOverdue ? '⚠️ VENCIDA ' : 'Prev: ') + fechaPrevista;
            metaText.push(fechaTag);
            metaHtml.push(isOverdue
                ? '<strong style="color:#B91C1C;">' + escapeHtml(fechaTag) + '</strong>'
                : escapeHtml(fechaTag));
        } else if (!isResolved) {
            metaText.push('Sin fecha prevista');
            metaHtml.push('Sin fecha prevista');
        }

        var inact = computeInactivityStatus(inc, null);
        if (inact) {
            metaText.push('⏸ ' + inact.label);
            var inactColor = inact.level === 'crit' ? '#DC2626' : '#D97706';
            metaHtml.push('<span style="color:' + inactColor + '; font-weight:600;">⏸ ' + escapeHtml(inact.label) + '</span>');
        }

        var pp = detectPingPong(inc, null, iaData);
        if (pp) {
            metaText.push('🏓 ' + pp.label);
            metaHtml.push('<span style="color:#7C3AED; font-weight:600;">🏓 ' + escapeHtml(pp.label) + '</span>');
        }

        var textLines = [
            '• ' + id + ' (' + metaText.join(' | ') + ')',
            '  - Problema Detectado: ' + problema,
            '  - IMPACTO: ' + (impacto || (isResolved ? 'Subsanado' : 'Sin impacto reseñado'))
        ];
        if (acciones) {
            textLines.push('  - Acción: ' + acciones);
        }
        var textLine = textLines.join('\n');

        var htmlLine = '<li><strong>' + escapeHtml(id) + '</strong> (' + metaHtml.join(' | ') + ')' +
            '<div style="margin-left: 18px; margin-top: 3px; margin-bottom: 8px; font-size: 13px; line-height: 1.45;">' +
            '<div><strong>Problema Detectado:</strong> ' + escapeHtml(problema) + '</div>' +
            '<div><strong>IMPACTO:</strong> ' + escapeHtml(impacto || (isResolved ? 'Subsanado' : 'Sin impacto reseñado')) + '</div>' +
            (acciones ? '<div><em>Acción:</em> ' + escapeHtml(acciones) + '</div>' : '') +
            '</div></li>';

        return {
            textLine: textLine,
            htmlLine: htmlLine,
            isResolved: isResolved,
            isOverdue: isOverdue,
            sistema: (inc['Grupo asignado'] && String(inc['Grupo asignado']).trim()) ||
                     (inc['Grupo Resolutor'] && String(inc['Grupo Resolutor']).trim()) ||
                     (inc['Sistema'] && String(inc['Sistema']).trim()) ||
                     (inc['sistema'] && String(inc['sistema']).trim()) ||
                     (inc['producto'] && String(inc['producto']).trim()) || 'Sin asignar',
            rank: priorityRank(inc)
        };
    }

    function renderBriefingOutput(titleText, totalCount, resolvedCount, overdueCount, sections) {
        var textParts = [
            titleText + '\nTotal visibles: ' + totalCount + ' | Resueltas: ' + resolvedCount + ' | Compromisos vencidos: ' + overdueCount
        ];
        var overdueHtml = overdueCount > 0
            ? '<strong style="color:#B91C1C;">' + overdueCount + '</strong>'
            : '<strong>0</strong>';
        var htmlParts = [
            '<div><p><strong>' + escapeHtml(titleText) + '</strong><br>' +
            'Total visibles: <strong>' + totalCount + '</strong> | Resueltas: <strong>' + resolvedCount + '</strong> | Compromisos vencidos: ' + overdueHtml + '</p>'
        ];

        sections.forEach(function (sec) {
            textParts.push('\n[' + sec.heading + '] (' + sec.items.length + ')\n' + sec.items.map(function (x) { return x.textLine; }).join('\n\n'));
            htmlParts.push('<p><strong>' + escapeHtml(sec.heading) + ' (' + sec.items.length + ')</strong></p><ul>' +
                sec.items.map(function (x) { return x.htmlLine; }).join('') + '</ul>');
        });
        htmlParts.push('</div>');

        return {
            text: textParts.join('\n'),
            html: htmlParts.join('')
        };
    }

    function buildMesaBriefing(incidents, iaCache, projectsCatalog, releaseName, overrides, nowDate) {
        var list = Array.isArray(incidents) ? incidents : [];
        var todayYmd = getBriefingTodayYmd(nowDate);

        var buckets = {
            1: { title: 'Crítica (P1)', items: [] },
            2: { title: 'Alta (P2)', items: [] },
            3: { title: 'Media (P3)', items: [] },
            99: { title: 'Baja / Otras', items: [] }
        };
        var overdueCount = 0;
        var resolvedCount = 0;

        list.forEach(function (inc) {
            var info = formatBriefingIncidentInfo(inc, iaCache, projectsCatalog, releaseName, overrides, todayYmd, false);
            if (info.isResolved) resolvedCount++;
            if (info.isOverdue) overdueCount++;
            var bucketKey = buckets[info.rank] ? info.rank : 99;
            buckets[bucketKey].items.push(info);
        });

        var sections = [];
        [1, 2, 3, 99].forEach(function (k) {
            if (buckets[k].items.length > 0) {
                sections.push({ heading: buckets[k].title, items: buckets[k].items });
            }
        });
        var title = 'Briefing Mesa de Release ' + (releaseName || '') + ' (' + todayYmd + ')';
        return renderBriefingOutput(title, list.length, resolvedCount, overdueCount, sections);
    }

    function buildMesaBriefingBySystem(incidents, iaCache, projectsCatalog, releaseName, overrides, nowDate) {
        var list = Array.isArray(incidents) ? incidents : [];
        var todayYmd = getBriefingTodayYmd(nowDate);

        var groups = {};
        var overdueCount = 0;
        var resolvedCount = 0;

        list.forEach(function (inc) {
            var info = formatBriefingIncidentInfo(inc, iaCache, projectsCatalog, releaseName, overrides, todayYmd, true);
            if (info.isResolved) resolvedCount++;
            if (info.isOverdue) overdueCount++;
            if (!groups[info.sistema]) groups[info.sistema] = [];
            groups[info.sistema].push(info);
        });

        var systemNames = Object.keys(groups).sort(function (a, b) {
            if (a === 'Sin asignar') return 1;
            if (b === 'Sin asignar') return -1;
            return a.localeCompare(b, 'es', { sensitivity: 'base' });
        });

        var sections = systemNames.map(function (sys) {
            var items = groups[sys].slice().sort(function (a, b) { return a.rank - b.rank; });
            return { heading: sys, items: items };
        });
        var title = 'Briefing Mesa de Release por Sistema ' + (releaseName || '') + ' (' + todayYmd + ')';
        return renderBriefingOutput(title, list.length, resolvedCount, overdueCount, sections);
    }

    function getDespliegueBadgeClass(despliegue) {
        var d = despliegue ? String(despliegue).toLowerCase() : '';
        if (d.includes('complet')) return 'rd-badge-despliegue-completo';
        if (d.includes('pilot')) return 'rd-badge-despliegue-piloto';
        if (d.includes('ocult')) return 'rd-badge-despliegue-oculto';
        if (d.includes('pap') || d.includes('técnic') || d.includes('tecnic')) return 'rd-badge-despliegue-pap';
        return 'rd-badge-despliegue-otro';
    }

    function groupIncidentsByProject(incidents, projectsCatalog, releaseName, overrides, nowDate) {
        var list = Array.isArray(incidents) ? incidents : [];
        var map = {};
        list.forEach(function (inc) {
            var proj = resolveProjectInfo(inc, projectsCatalog, releaseName);
            var key = proj ? proj.code : '__NO_PROJECT__';
            if (!map[key]) {
                map[key] = {
                    code: proj ? proj.code : 'Sin proyecto',
                    hasProject: Boolean(proj),
                    despliegue: proj ? (proj.despliegue || '') : '',
                    summary: proj ? (proj.summary || '') : '',
                    total: 0,
                    p1: 0,
                    p2: 0,
                    p3Other: 0,
                    resolved: 0,
                    overdue: 0,
                    missingFecha: 0,
                    stalled: 0,
                    pingPong: 0,
                    health: 'ok',
                    incidents: []
                };
            }
            var grp = map[key];
            grp.total++;
            grp.incidents.push(inc);
            var rank = priorityRank(inc);
            if (rank === 1) grp.p1++;
            else if (rank === 2) grp.p2++;
            else grp.p3Other++;

            var fst = getFechaPrevistaStatus(inc, overrides, nowDate);
            if (fst === 'resolved') grp.resolved++;
            else if (fst === 'overdue') grp.overdue++;
            else if (fst === 'missing') grp.missingFecha++;

            var inact = computeInactivityStatus(inc, nowDate);
            if (inact) grp.stalled++;
            var pp = detectPingPong(inc, null, null);
            if (pp) grp.pingPong++;
        });

        var healthOrder = { crit: 0, warn: 1, ok: 2 };
        return Object.keys(map).map(function (k) {
            var g = map[k];
            if (g.p1 > 0 || g.overdue > 0) g.health = 'crit';
            else if (g.p2 > 0 || g.missingFecha > 0 || g.stalled > 0 || g.pingPong > 0) g.health = 'warn';
            else g.health = 'ok';
            return g;
        }).sort(function (a, b) {
            if (a.hasProject !== b.hasProject) return a.hasProject ? -1 : 1;
            var ho = healthOrder[a.health] - healthOrder[b.health];
            if (ho !== 0) return ho;
            if (b.total !== a.total) return b.total - a.total;
            return a.code.localeCompare(b.code, 'es', { sensitivity: 'base' });
        });
    }

    function getSyncChangeBadge(incId, lastSyncChanges) {
        if (!incId || !lastSyncChanges || typeof lastSyncChanges !== 'object') return null;
        var hasId = function (col) {
            if (!col) return false;
            if (typeof col.has === 'function') return col.has(incId);
            if (Array.isArray(col)) return col.indexOf(incId) !== -1;
            return false;
        };
        if (hasId(lastSyncChanges.new_ids)) return 'new';
        if (hasId(lastSyncChanges.status_changed_ids)) return 'status';
        if (hasId(lastSyncChanges.updated_ids)) return 'updated';
        return null;
    }

    function isMassiveIncident(inc, massiveIds) {
        if (!inc || typeof inc !== 'object') return false;
        if (inc.masiva === true || inc.esMasiva === true) return true;
        var m = inc.masiva !== undefined ? inc.masiva : (inc.esMasiva !== undefined ? inc.esMasiva : (inc['Es Masiva'] !== undefined ? inc['Es Masiva'] : inc['Masiva']));
        if (typeof m === 'string') {
            var ms = m.trim().toLowerCase();
            if (ms === 's' || ms === 'si' || ms === 'sí' || ms === 'true' || ms === 'masiva' || ms === '1') return true;
        }
        if (m === 1) return true;
        var impacto = inc['Impacto'] || inc['impacto'];
        if (typeof impacto === 'string' && impacto.trim().toLowerCase() === 'masiva') return true;
        var id = inc['ID de incidencia'] || inc['id'] || inc['idRemedy'];
        if (id && massiveIds) {
            var cleanId = String(id).trim();
            if (typeof massiveIds.has === 'function' && massiveIds.has(cleanId)) return true;
            if (Array.isArray(massiveIds) && massiveIds.indexOf(cleanId) !== -1) return true;
        }
        return false;
    }

    function getPriorityBadgeClass(prio, urg, isMasiva) {
        var p = String(prio || urg || '').toLowerCase();
        if (p.includes('p1') || p.includes('crít') || p.includes('crit')) {
            return isMasiva ? 'rd-badge-critica rd-badge-masiva' : 'rd-badge-critica';
        }
        if (p.includes('p2') || p.includes('alt')) {
            return isMasiva ? 'rd-badge-alta rd-badge-masiva' : 'rd-badge-alta';
        }
        if (isMasiva) {
            return 'rd-badge-masiva';
        }
        return 'rd-badge-media';
    }

    function getPriorityTooltip(incident, iaData, isMasiva) {
        var iaImpacto = (iaData && !iaData._error && (iaData.impacto || iaData.impactoNegocio || iaData.impacto_negocio || iaData.impacto_justificacion))
            ? String(iaData.impacto || iaData.impactoNegocio || iaData.impacto_negocio || iaData.impacto_justificacion).trim()
            : '';
        if (iaImpacto && iaImpacto !== '-') {
            return {
                title: 'Impacto en Servicio y Negocio',
                text: iaImpacto
            };
        }
        if (isMasiva) {
            return {
                title: 'Impacto en Servicio y Negocio',
                text: 'Incidencia con afectación masiva de servicio.'
            };
        }
        var incImpacto = incident && (incident['Impacto'] || incident['impacto']);
        if (incImpacto && typeof incImpacto === 'string' && incImpacto.trim() && incImpacto.trim() !== '-') {
            return {
                title: 'Impacto en Servicio y Negocio',
                text: incImpacto.trim()
            };
        }
        return null;
    }

    var api = {
        escapeHtml: escapeHtml,
        isClosedStatus: isClosedStatus,
        filterNonClosedIncidents: filterNonClosedIncidents,
        extractProjectCode: extractProjectCode,
        resolveProjectInfo: resolveProjectInfo,
        buildFollowupText: buildFollowupText,
        computeOpenAgeDays: computeOpenAgeDays,
        isIaCacheStale: isIaCacheStale,
        matchesKpiFilter: matchesKpiFilter,
        buildExportCsv: buildExportCsv,
        buildExportFilename: buildExportFilename,
        sortIncidents: sortIncidents,
        buildMesaBriefing: buildMesaBriefing,
        buildMesaBriefingBySystem: buildMesaBriefingBySystem,
        getFechaPrevistaStatus: getFechaPrevistaStatus,
        getDespliegueBadgeClass: getDespliegueBadgeClass,
        groupIncidentsByProject: groupIncidentsByProject,
        getSyncChangeBadge: getSyncChangeBadge,
        isMassiveIncident: isMassiveIncident,
        getPriorityBadgeClass: getPriorityBadgeClass,
        getPriorityTooltip: getPriorityTooltip,
        parseDateRobust: parseDateRobust,
        computeInactivityStatus: computeInactivityStatus,
        detectPingPong: detectPingPong
    };
    global.ReleaseDeskDomain = api;
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = api;
    }
})(typeof window !== 'undefined' ? window : globalThis);
