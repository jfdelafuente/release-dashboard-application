/**
 * ============================================================
 * Resumen Inteligente de Incidencias (Epsilon IA) - Pantalla Flotante
 * Diseño Colorido y Dinámico
 * ============================================================
 */

(function () {
    let overlayEl = null;
    let modalEl = null;
    let lastFocusedElement = null;
    let currentIncidentCode = null;

    // Caché en cliente (memoria y sessionStorage) para no saturar la API
    const clientCache = new Map();
    const inFlightRequests = new Map();
    const CLIENT_CACHE_TTL_MS = 15 * 60 * 1000; // 15 minutos en cliente

    function getCachedData(code) {
        const mem = clientCache.get(code);
        if (mem && (Date.now() - mem.timestamp < CLIENT_CACHE_TTL_MS)) {
            return mem;
        }
        try {
            const raw = sessionStorage.getItem(`resumen_ia_${code}`);
            if (raw) {
                const parsed = JSON.parse(raw);
                if (parsed && (Date.now() - parsed.timestamp < CLIENT_CACHE_TTL_MS)) {
                    clientCache.set(code, parsed);
                    return parsed;
                }
            }
        } catch (_) {}
        return null;
    }

    function setCachedData(code, data) {
        const item = {
            timestamp: Date.now(),
            data: data
        };
        clientCache.set(code, item);
        try {
            sessionStorage.setItem(`resumen_ia_${code}`, JSON.stringify(item));
        } catch (_) {}
    }

    function clearCachedData(code) {
        clientCache.delete(code);
        try {
            sessionStorage.removeItem(`resumen_ia_${code}`);
        } catch (_) {}
    }

    function getRemedyUrl(code) {
        return `https://soptmc.si.orange.es/MonTMC/epsilon/remedyC/${encodeURIComponent(code)}`;
    }

    function createModalDOM() {
        if (overlayEl) return;

        overlayEl = document.createElement('div');
        overlayEl.id = 'resumen-ia-overlay';
        overlayEl.className = 'resumen-ia-overlay';
        overlayEl.setAttribute('role', 'dialog');
        overlayEl.setAttribute('aria-modal', 'true');
        overlayEl.setAttribute('aria-labelledby', 'resumen-ia-title');

        modalEl = document.createElement('div');
        modalEl.className = 'resumen-ia-modal';
        overlayEl.appendChild(modalEl);

        // Cerrar al hacer click en el fondo oscuro exterior
        overlayEl.addEventListener('click', (e) => {
            if (e.target === overlayEl) {
                closeModal();
            }
        });

        // Cerrar al pulsar Escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && overlayEl.classList.contains('is-open')) {
                closeModal();
            }
        });

        document.body.appendChild(overlayEl);
    }

    function closeModal() {
        if (!overlayEl) return;
        overlayEl.classList.remove('is-open');
        document.body.style.overflow = '';
        if (lastFocusedElement && typeof lastFocusedElement.focus === 'function') {
            lastFocusedElement.focus();
        }
    }

    function renderLoading(code) {
        modalEl.innerHTML = `
            <div class="resumen-ia-top-bar"></div>
            <div class="resumen-ia-header">
                <div class="resumen-ia-header-top">
                    <div class="resumen-ia-badges">
                        <span class="resumen-ia-ai-tag">✨ Resumen IA · Epsilon</span>
                        <span class="resumen-ia-code-badge">${escapeHtml(code)}</span>
                    </div>
                    <div class="resumen-ia-header-actions">
                        <a href="${getRemedyUrl(code)}" target="_blank" rel="noopener noreferrer" class="resumen-ia-remedy-btn" title="Abrir ficha completa en Remedy">
                            <span>Remedy</span>
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                                <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                                <polyline points="15 3 21 3 21 9"></polyline>
                                <line x1="10" y1="14" x2="21" y2="3"></line>
                            </svg>
                        </a>
                        <button type="button" class="resumen-ia-close-btn" onclick="window.ResumenIAModal.close()" aria-label="Cerrar modal">&times;</button>
                    </div>
                </div>
            </div>
            <div class="resumen-ia-body">
                <div class="resumen-ia-loading">
                    <div class="resumen-ia-spinner" aria-hidden="true"></div>
                    <h3 class="resumen-ia-loading-text">Sintetizando información con IA...</h3>
                    <p class="resumen-ia-loading-subtext">Consultando servicio Epsilon en soptmc.si.orange.es para ${escapeHtml(code)}</p>
                </div>
            </div>
            <div class="resumen-ia-footer">
                <span class="resumen-ia-footer-note">Customer &amp; Service Operations · Epsilon IA</span>
                <button type="button" class="resumen-ia-btn-secondary" onclick="window.ResumenIAModal.close()">Cerrar</button>
            </div>
        `;
    }

    function renderError(code, errorMessage) {
        modalEl.innerHTML = `
            <div class="resumen-ia-top-bar"></div>
            <div class="resumen-ia-header">
                <div class="resumen-ia-header-top">
                    <div class="resumen-ia-badges">
                        <span class="resumen-ia-ai-tag">✨ Resumen IA · Epsilon</span>
                        <span class="resumen-ia-code-badge">${escapeHtml(code)}</span>
                    </div>
                    <div class="resumen-ia-header-actions">
                        <button type="button" class="resumen-ia-close-btn" onclick="window.ResumenIAModal.close()" aria-label="Cerrar modal">&times;</button>
                    </div>
                </div>
            </div>
            <div class="resumen-ia-body">
                <div class="resumen-ia-error">
                    <div class="resumen-ia-error-icon" aria-hidden="true">⚠️</div>
                    <h3 class="resumen-ia-error-title">No se pudo cargar el resumen de IA</h3>
                    <p class="resumen-ia-error-desc">
                        ${escapeHtml(errorMessage || 'El servicio de IA no devolvió respuesta para esta incidencia.')}
                    </p>
                    <div style="display: flex; gap: 10px; margin-top: 14px;">
                        <button type="button" class="resumen-ia-btn-secondary" onclick="window.ResumenIAModal.open('${escapeHtml(code)}')">
                            🔄 Reintentar
                        </button>
                        <a href="${getRemedyUrl(code)}" target="_blank" rel="noopener noreferrer" class="resumen-ia-btn-primary">
                            <span>Ver en Remedy directo</span>
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                                <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                                <polyline points="15 3 21 3 21 9"></polyline>
                                <line x1="10" y1="14" x2="21" y2="3"></line>
                            </svg>
                        </a>
                    </div>
                </div>
            </div>
            <div class="resumen-ia-footer">
                <span class="resumen-ia-footer-note">Customer &amp; Service Operations · Epsilon IA</span>
                <button type="button" class="resumen-ia-btn-secondary" onclick="window.ResumenIAModal.close()">Cerrar</button>
            </div>
        `;
    }

    function getStatusClass(status) {
        if (!status) return '';
        const s = status.toLowerCase();
        if (s.includes('cerrad') || s.includes('resuelt')) return 'status-cerrado';
        if (s.includes('asigna') || s.includes('progreso') || s.includes('curso') || s.includes('análisis')) return 'status-asignado';
        if (s.includes('pend')) return 'status-pendiente';
        return '';
    }

    function renderContent(code, data) {
        const estado = data.estadoActual || 'DESCONOCIDO';
        const statusClass = getStatusClass(estado);
        const sistemas = Array.isArray(data.sistemas) ? data.sistemas : [];
        const hitos = Array.isArray(data.hitosTecnicos) ? data.hitosTecnicos : [];
        const bloqueos = Array.isArray(data.bloqueos) ? data.bloqueos : [];

        // Generar chips de sistemas afectados
        const sistemasHtml = sistemas.length > 0 ? `
            <div class="resumen-ia-sistemas">
                <span class="resumen-ia-sistemas-label">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                        <rect x="2" y="2" width="20" height="8" rx="2" ry="2"></rect>
                        <rect x="2" y="14" width="20" height="8" rx="2" ry="2"></rect>
                        <line x1="6" y1="6" x2="6.01" y2="6"></line>
                        <line x1="6" y1="18" x2="6.01" y2="18"></line>
                    </svg>
                    Sistemas Afectados:
                </span>
                ${sistemas.map(s => `<span class="resumen-ia-system-chip">${escapeHtml(s)}</span>`).join('')}
            </div>
        ` : '';

        // Generar bloque de solución / causa raíz si existe
        const solucionHtml = data.solucion ? `
            <div class="resumen-ia-block block-solucion">
                <div class="resumen-ia-block-header">
                    <span class="resumen-ia-icon-circle" aria-hidden="true">✅</span>
                    <h4 class="resumen-ia-block-title">Causa Raíz y Solución</h4>
                </div>
                <p class="resumen-ia-block-content">${escapeHtml(data.solucion)}</p>
            </div>
        ` : '';

        // Generar bloque de bloqueos si existen
        const bloqueosHtml = bloqueos.length > 0 ? `
            <div class="resumen-ia-block block-bloqueos">
                <div class="resumen-ia-block-header">
                    <span class="resumen-ia-icon-circle" aria-hidden="true">⚠️</span>
                    <h4 class="resumen-ia-block-title">Bloqueos e Impedimentos</h4>
                </div>
                <ul class="resumen-ia-list">
                    ${bloqueos.map(b => `<li>${escapeHtml(b)}</li>`).join('')}
                </ul>
            </div>
        ` : '';

        // Generar bloque de siguiente acción si existe
        const siguienteAccionHtml = data.siguienteAccion ? `
            <div class="resumen-ia-block block-siguiente">
                <div class="resumen-ia-block-header">
                    <span class="resumen-ia-icon-circle" aria-hidden="true">➡️</span>
                    <h4 class="resumen-ia-block-title">Siguiente Acción Recomendada</h4>
                </div>
                <p class="resumen-ia-block-content">${escapeHtml(data.siguienteAccion)}</p>
            </div>
        ` : '';

        // Generar cronología de hitos
        let hitosHtml = '';
        if (hitos.length > 0) {
            const hitosItems = hitos.map(h => {
                const sepIdx = h.indexOf(':');
                if (sepIdx > 0 && sepIdx <= 15) {
                    const datePart = h.substring(0, sepIdx).trim();
                    const textPart = h.substring(sepIdx + 1).trim();
                    return `
                        <div class="resumen-ia-timeline-item">
                            <span class="resumen-ia-timeline-dot" aria-hidden="true"></span>
                            <span class="resumen-ia-timeline-date">${escapeHtml(datePart)}</span>
                            <span>${escapeHtml(textPart)}</span>
                        </div>
                    `;
                }
                return `
                    <div class="resumen-ia-timeline-item">
                        <span class="resumen-ia-timeline-dot" aria-hidden="true"></span>
                        <span>${escapeHtml(h)}</span>
                    </div>
                `;
            }).join('');

            hitosHtml = `
                <div class="resumen-ia-timeline-card">
                    <h4 class="resumen-ia-timeline-title">
                        <span aria-hidden="true">⏱️</span>
                        <span>Cronología de Hitos Técnicos</span>
                        <span class="resumen-ia-timeline-count-badge">${hitos.length} hitos</span>
                    </h4>
                    <div class="resumen-ia-timeline">
                        ${hitosItems}
                    </div>
                </div>
            `;
        }

        modalEl.innerHTML = `
            <div class="resumen-ia-top-bar"></div>
            <div class="resumen-ia-header">
                <div class="resumen-ia-header-top">
                    <div class="resumen-ia-badges">
                        <span class="resumen-ia-ai-tag">✨ Resumen IA · Epsilon</span>
                        <span class="resumen-ia-code-badge">${escapeHtml(code)}</span>
                        <span class="resumen-ia-status-badge ${statusClass}">${escapeHtml(estado)}</span>
                        ${data._cached ? `<span class="resumen-ia-cache-pill" title="Respuesta guardada en caché local">⚡ En caché (${data._cacheAgeMinutes === 0 ? 'reciente' : `${data._cacheAgeMinutes}m`})</span>` : ''}
                    </div>
                    <div class="resumen-ia-header-actions">
                        <button type="button" class="resumen-ia-refresh-btn" onclick="window.ResumenIAModal.refresh()" title="Consultar última versión en tiempo real desde Epsilon IA (evitar caché)">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                                <polyline points="23 4 23 10 17 10"></polyline>
                                <polyline points="1 20 1 14 7 14"></polyline>
                                <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
                            </svg>
                            <span>Refrescar</span>
                        </button>
                        <a href="${getRemedyUrl(code)}" target="_blank" rel="noopener noreferrer" class="resumen-ia-remedy-btn" title="Abrir ficha completa en Remedy">
                            <span>Remedy</span>
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                                <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                                <polyline points="15 3 21 3 21 9"></polyline>
                                <line x1="10" y1="14" x2="21" y2="3"></line>
                            </svg>
                        </a>
                        <button type="button" class="resumen-ia-close-btn" onclick="window.ResumenIAModal.close()" aria-label="Cerrar modal">&times;</button>
                    </div>
                </div>
                <h3 id="resumen-ia-title" class="resumen-ia-title">${escapeHtml(data.titulo || 'Sin título')}</h3>
            </div>
            <div class="resumen-ia-body">
                ${sistemasHtml}

                <!-- Bloque: Problema -->
                <div class="resumen-ia-block block-problema">
                    <div class="resumen-ia-block-header">
                        <span class="resumen-ia-icon-circle" aria-hidden="true">🔍</span>
                        <h4 class="resumen-ia-block-title">Problema Detectado</h4>
                    </div>
                    <p class="resumen-ia-block-content">${escapeHtml(data.problema || 'No se proporcionó detalle del problema.')}</p>
                </div>

                <!-- Bloque: Impacto -->
                <div class="resumen-ia-block block-impacto">
                    <div class="resumen-ia-block-header">
                        <span class="resumen-ia-icon-circle" aria-hidden="true">💥</span>
                        <h4 class="resumen-ia-block-title">Impacto en Servicio y Negocio</h4>
                    </div>
                    <p class="resumen-ia-block-content">${escapeHtml(data.impacto || 'No se detalló el impacto.')}</p>
                </div>

                ${solucionHtml}
                ${bloqueosHtml}
                ${siguienteAccionHtml}
                ${hitosHtml}
            </div>
            <div class="resumen-ia-footer">
                <span class="resumen-ia-footer-note">Sintetizado por el motor de IA de Epsilon (soptmc.si.orange.es)${data._cached ? ' · Servido desde caché local' : ' · En tiempo real'}</span>
                <div class="resumen-ia-footer-actions">
                    <button type="button" class="resumen-ia-btn-secondary" onclick="window.ResumenIAModal.close()">Cerrar</button>
                    <a href="${getRemedyUrl(code)}" target="_blank" rel="noopener noreferrer" class="resumen-ia-btn-primary">
                        <span>Ver en Remedy</span>
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                            <polyline points="15 3 21 3 21 9"></polyline>
                            <line x1="10" y1="14" x2="21" y2="3"></line>
                        </svg>
                    </a>
                </div>
            </div>
        `;
    }

    async function fetchResumenIA(code, forceRefresh = false) {
        if (!forceRefresh) {
            const cached = getCachedData(code);
            if (cached && cached.data) {
                return {
                    ...cached.data,
                    _cached: true,
                    _cacheAgeMinutes: Math.round((Date.now() - cached.timestamp) / 60000)
                };
            }
        } else {
            clearCachedData(code);
        }

        // Deduplicación de peticiones concurrentes para el mismo código
        if (inFlightRequests.has(code)) {
            return inFlightRequests.get(code);
        }

        const fetchPromise = (async () => {
            const proxyUrl = `/api/epsilon/resumenIA/${encodeURIComponent(code)}`;
            const directUrl = `https://soptmc.si.orange.es/MonTMC/api/epsilon/resumenIA/${encodeURIComponent(code)}`;

            const headers = { 'Accept': 'application/json' };
            if (forceRefresh) {
                headers['Cache-Control'] = 'no-cache';
            }

            let proxyErrorMsg = null;
            try {
                const resp = await fetch(proxyUrl, { headers });
                if (resp.ok) {
                    const data = await resp.json();
                    if (data && data.success) {
                        setCachedData(code, data);
                        return data;
                    }
                    if (data && data.error) throw new Error(data.error);
                    setCachedData(code, data);
                    return data;
                } else {
                    proxyErrorMsg = `El proxy local devolvió HTTP ${resp.status} (${resp.statusText || 'Error'})`;
                    console.warn('Proxy local no devolvió 200 OK:', resp.status, resp.statusText);
                }
            } catch (proxyErr) {
                proxyErrorMsg = proxyErr.message || 'Error de conexión con el proxy local';
                console.warn('Proxy local no disponible o con error:', proxyErr);
            }

            // 2. Fallback: consulta directa a soptmc.si.orange.es
            try {
                const respDirect = await fetch(directUrl, { headers });
                if (!respDirect.ok) {
                    throw new Error(`Error HTTP ${respDirect.status} al consultar Epsilon IA`);
                }
                const dataDirect = await respDirect.json();
                if (dataDirect && dataDirect.success) {
                    setCachedData(code, dataDirect);
                    return dataDirect;
                }
                throw new Error(dataDirect.error || 'La respuesta de la IA no marcó success: true');
            } catch (directErr) {
                console.error('Error al consultar Epsilon IA directamente:', directErr);
                if (proxyErrorMsg) {
                    throw new Error(`${proxyErrorMsg}. (Consulta directa falló: ${directErr.message || 'CORS / Sin conexión'})`);
                }
                throw directErr;
            }
        })();

        inFlightRequests.set(code, fetchPromise);
        try {
            return await fetchPromise;
        } finally {
            inFlightRequests.delete(code);
        }
    }

    async function openModal(code, forceRefresh = false) {
        if (!code || code === '-') return;

        createModalDOM();
        lastFocusedElement = document.activeElement;
        currentIncidentCode = code;

        // Bloquear scroll de la página
        document.body.style.overflow = 'hidden';
        overlayEl.classList.add('is-open');

        // Si tenemos datos en caché y no se pide refrescar a la fuerza, mostrar de inmediato
        if (!forceRefresh) {
            const cached = getCachedData(code);
            if (cached && cached.data) {
                renderContent(code, {
                    ...cached.data,
                    _cached: true,
                    _cacheAgeMinutes: Math.round((Date.now() - cached.timestamp) / 60000)
                });
                return;
            }
        }

        // Mostrar estado de carga si hay que consultar por red
        renderLoading(code);

        try {
            const data = await fetchResumenIA(code, forceRefresh);
            if (currentIncidentCode === code) {
                renderContent(code, data);
            }
        } catch (err) {
            if (currentIncidentCode === code) {
                renderError(code, err.message);
            }
        }
    }

    function escapeHtml(str) {
        if (str == null) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    // Exponer API global
    window.ResumenIAModal = {
        open: openModal,
        close: closeModal,
        refresh: () => {
            if (currentIncidentCode) {
                openModal(currentIncidentCode, true);
            }
        }
    };

    // Alias directo
    window.openResumenIA = openModal;
})();
