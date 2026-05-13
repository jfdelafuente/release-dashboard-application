/* ============================================================================
   Dashboard Hub - Main JavaScript Module
   ============================================================================ */

/**
 * Global state management
 */
const hubState = {
    allIncidents: [],
    lastUpdated: null,
    dataSource: null
};

/**
 * Constants
 */
const DATA_OUTPUT_DIR = 'data/output/';
const PENDING_STATUSES = ['Abierto', 'En Progreso', 'Pendiente', 'Asignado'];
const CLOSED_STATUSES = ['Cerrado', 'Resuelto', 'Cancelado'];

// DOM Elements
const loadingState = document.getElementById('loading-state');
const errorState = document.getElementById('error-state');
const errorText = document.getElementById('error-text');
const contentState = document.getElementById('content-state');
const massiveIncidentsContainer = document.getElementById('massive-incidents-kpis');
const postmortemContainer = document.getElementById('postmortem-kpis');
const lastUpdatedSpan = document.getElementById('last-updated');

/* ============================================================================
   Initialization
   ============================================================================ */

/**
 * Main initialization function - called on page load
 */
async function initHub() {
    try {
        showLoading();

        // Load latest JSON file
        const { incidents, metadata } = await loadLatestJSON();

        if (!incidents || incidents.length === 0) {
            showError('No hay datos disponibles. Por favor cargue archivos JSON en data/output/');
            return;
        }

        // Store in global state
        hubState.allIncidents = incidents;
        hubState.metadata = metadata;
        hubState.lastUpdated = new Date();

        // Extract KPIs
        const kpis = extractKPIs(incidents, metadata);

        // Render the hub
        renderHub(kpis);

        // Update timestamp
        updateLastUpdatedTimestamp();

    } catch (error) {
        console.error('Error initializing hub:', error);
        showError(`Error: ${error.message}`);
    }
}

/**
 * Display loading state
 */
function showLoading() {
    loadingState.style.display = 'flex';
    errorState.style.display = 'none';
    contentState.style.display = 'none';
}

/**
 * Display error state with message
 */
function showError(message) {
    errorText.textContent = message;
    errorState.style.display = 'flex';
    loadingState.style.display = 'none';
    contentState.style.display = 'none';
}

/**
 * Display content state
 */
function showContent() {
    contentState.style.display = 'grid';
    loadingState.style.display = 'none';
    errorState.style.display = 'none';
}

/* ============================================================================
   JSON File Loading
   ============================================================================ */

/**
 * Load the latest JSON file from data/output/ directory
 * Auto-detects the most recent file by timestamp using index.json
 *
 * Supports both old format (array) and new format (object with sections)
 */
async function loadLatestJSON() {
    try {
        // Fetch the index.json file that lists all available JSON files
        const indexResponse = await fetch(`${DATA_OUTPUT_DIR}index.json`);

        if (!indexResponse.ok) {
            throw new Error('No se encontró el archivo index.json en data/output/');
        }

        const indexData = await indexResponse.json();

        // Handle both formats:
        // Old format: [{ name, ... }, { name, ... }]
        // New format: { massive: { files: [...] }, postmortem: { files: [...] } }
        let fileList = [];

        if (Array.isArray(indexData)) {
            // Old format: direct array
            fileList = indexData;
        } else if (typeof indexData === 'object' && indexData.massive && indexData.massive.files) {
            // New format: extract from massive section (prioritize massive incidents for Dashboard Hub)
            fileList = indexData.massive.files;
            console.log(`New index format detected: found ${fileList.length} massive incident file(s)`);
        } else {
            throw new Error('Formato de index.json no reconocido. Esperado: array o objeto con secciones');
        }

        if (!fileList || fileList.length === 0) {
            throw new Error('No hay archivos JSON disponibles en data/output/');
        }

        // Sort by date descending to get latest first (already sorted in index.json)
        const latestFile = fileList[0];

        console.log(`Loading latest JSON file: ${latestFile.name}`);

        const dataResponse = await fetch(`${DATA_OUTPUT_DIR}${latestFile.name}`);

        if (!dataResponse.ok) {
            throw new Error(`No se puede cargar el archivo: ${latestFile.name}`);
        }

        const data = await dataResponse.json();
        hubState.dataSource = latestFile.name;

        // Handle both old format (array) and new format (with metadata)
        let incidents;
        let metadata = null;

        if (Array.isArray(data)) {
            // Old format: direct array of incidents
            incidents = data;
        } else if (data._metadata && data.data) {
            // New format: object with metadata and data
            metadata = data._metadata;

            // Accept both massive and postmortem file types
            const fileType = metadata.type || 'unknown';
            if (!['massive', 'postmortem'].includes(fileType)) {
                throw new Error(`Archivo no válido: esperado tipo 'massive' o 'postmortem', recibido '${fileType}'`);
            }

            incidents = data.data;
            console.log(`Metadata: type=${metadata.type}, version=${metadata.version}, records=${metadata.record_count}`);
            if (metadata.kpis) {
                console.log(`KPIs pre-calculated: total=${metadata.kpis.total}`);
                console.log(`KPIs by_estatus:`, JSON.stringify(metadata.kpis.by_estatus || {}));
            }
        } else {
            throw new Error('Formato de JSON no reconocido');
        }

        console.log(`Successfully loaded ${incidents.length} incidents from ${latestFile.name}`);

        return { incidents, metadata };

    } catch (error) {
        console.error('Error loading JSON:', error);

        if (error.message.includes('index.json')) {
            throw new Error('No se encontraron archivos JSON en data/output/. Por favor asegúrese de que los archivos CSV han sido convertidos a JSON y ejecute: python build_index.py en data/output/');
        } else if (error.message.includes('Failed to fetch')) {
            throw new Error('No se puede acceder al directorio data/output/. Verifique que el directorio existe y contiene archivos JSON.');
        }
        throw error;
    }
}

/* ============================================================================
   KPI Extraction
   ============================================================================ */

/**
 * Extract KPI metrics from incident data
 * Routes to appropriate KPI extraction based on file type and data structure
 */
function extractKPIs(incidents, metadata) {
    const fileType = metadata?.type || 'unknown';
    const hasKPIsMetadata = metadata && metadata.kpis;
    const hasDespliegue = incidents && incidents.length > 0 &&
        incidents.some(i => getIncidentFieldValue(i, 'Despliegue'));

    console.log(`[extractKPIs] File type: ${fileType}, Has KPIs metadata: ${!!hasKPIsMetadata}, Has Despliegue: ${hasDespliegue}`);

    // Decide which KPIs to extract
    let massiveIncidentsKPIs = [];
    let postmortemKPIs = [];

    // Always try to extract massive KPIs if we have metadata.kpis
    if (hasKPIsMetadata) {
        console.log(`[extractKPIs] Extracting Massive KPIs from metadata`);
        massiveIncidentsKPIs = extractMassiveIncidentsKPIs(incidents, metadata);
    }

    // Extract postmortem KPIs if we have Despliegue field
    if (hasDespliegue) {
        console.log(`[extractKPIs] Extracting Postmortem KPIs from Despliegue field`);
        postmortemKPIs = extractPostmortemKPIs(incidents, metadata);
    }

    // Fallback: if no metadata KPIs but no Despliegue either, try massive KPI calculation
    if (!hasKPIsMetadata && !hasDespliegue && incidents && incidents.length > 0) {
        console.log(`[extractKPIs] Fallback: calculating Massive KPIs from incidents data`);
        massiveIncidentsKPIs = extractMassiveIncidentsKPIs(incidents, metadata);
    }

    return {
        massiveIncidents: massiveIncidentsKPIs,
        postmortem: postmortemKPIs
    };
}

/**
 * Extract Massive Incidents KPIs
 * Reads pre-calculated KPIs from JSON metadata (calculated during CSV conversion)
 */
function extractMassiveIncidentsKPIs(incidents, metadata) {
    // If KPIs are already calculated in metadata, use those
    if (metadata && metadata.kpis) {
        const kpis = metadata.kpis;
        return [
            createKPICard(
                'total-incidents',
                'Total de Incidencias',
                kpis.total,
                'incidencias'
            ),
            createKPICard(
                'pending-incidents',
                'Incidencias Pendientes',
                kpis.pending,
                'pendientes'
            ),
            createKPICard(
                'trend-7-day',
                'Tendencia 7 días',
                Math.abs(kpis.trend_7d),
                '%',
                {
                    percentage: kpis.trend_7d,
                    direction: getTrendDirection(kpis.trend_7d),
                    period: '7 días'
                }
            ),
            createKPICard(
                'trend-15-day',
                'Tendencia 15 días',
                Math.abs(kpis.trend_15d),
                '%',
                {
                    percentage: kpis.trend_15d,
                    direction: getTrendDirection(kpis.trend_15d),
                    period: '15 días'
                }
            ),
            createKPICard(
                'trend-30-day',
                'Tendencia 30 días',
                Math.abs(kpis.trend_30d),
                '%',
                {
                    percentage: kpis.trend_30d,
                    direction: getTrendDirection(kpis.trend_30d),
                    period: '30 días'
                }
            )
        ];
    }

    // Fallback: Calculate KPIs from incidents if not in metadata (backward compatibility)
    if (!incidents || incidents.length === 0) {
        return [];
    }

    // Total incidents
    const totalIncidents = incidents.length;

    // Pending incidents (not closed/resolved/cancelled)
    // Using same logic as Massive Incidents Dashboard: check if status INCLUDES these words
    const pendingIncidents = incidents.filter(incident => {
        const status = (incident['Estatus'] || '').toLowerCase();
        // Use .includes() like Massive Incidents Dashboard
        return !status.includes('cerrado') && !status.includes('resuelto') && !status.includes('cancelado');
    });
    const pendingCount = pendingIncidents.length;

    // Calculate backlog trends from pending incidents over time
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const sevenDaysAgo = new Date(today);
    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);

    const fifteenDaysAgo = new Date(today);
    fifteenDaysAgo.setDate(fifteenDaysAgo.getDate() - 15);

    const thirtyDaysAgo = new Date(today);
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

    // Count pending incidents at different dates
    const pendingSevenDaysAgo = countPendingAtDate(incidents, sevenDaysAgo);
    const pendingFifteenDaysAgo = countPendingAtDate(incidents, fifteenDaysAgo);
    const pendingThirtyDaysAgo = countPendingAtDate(incidents, thirtyDaysAgo);

    // Calculate trend percentages
    const trend7Day = calculateTrendPercentage(pendingSevenDaysAgo, pendingCount);
    const trend15Day = calculateTrendPercentage(pendingFifteenDaysAgo, pendingCount);
    const trend30Day = calculateTrendPercentage(pendingThirtyDaysAgo, pendingCount);

    return [
        createKPICard(
            'total-incidents',
            'Total de Incidencias',
            totalIncidents,
            'incidencias'
        ),
        createKPICard(
            'pending-incidents',
            'Incidencias Pendientes',
            pendingCount,
            'pendientes'
        ),
        createKPICard(
            'trend-7-day',
            'Tendencia 7 días',
            Math.abs(trend7Day),
            '%',
            {
                percentage: trend7Day,
                direction: getTrendDirection(trend7Day),
                period: '7 días'
            }
        ),
        createKPICard(
            'trend-15-day',
            'Tendencia 15 días',
            Math.abs(trend15Day),
            '%',
            {
                percentage: trend15Day,
                direction: getTrendDirection(trend15Day),
                period: '15 días'
            }
        ),
        createKPICard(
            'trend-30-day',
            'Tendencia 30 días',
            Math.abs(trend30Day),
            '%',
            {
                percentage: trend30Day,
                direction: getTrendDirection(trend30Day),
                period: '30 días'
            }
        )
    ];
}

/**
 * Helper function to safely get field value from incident record
 * Handles BOM and field name variations
 */
function getIncidentFieldValue(incident, fieldName) {
    // Try direct access
    if (incident[fieldName]) return incident[fieldName];

    // Try without BOM (remove special characters)
    const cleanedName = fieldName.replace(/[\uFEFF\u200B\u200C\u200D]/g, '');
    if (incident[cleanedName]) return incident[cleanedName];

    // Search for key containing the field name (case-insensitive)
    const key = Object.keys(incident).find(k =>
        k.toLowerCase().includes(fieldName.toLowerCase()) ||
        k.replace(/[\uFEFF\u200B\u200C\u200D]/g, '').toLowerCase() === cleanedName.toLowerCase()
    );
    return key ? incident[key] : '';
}

/**
 * Extract Postmortem Dashboard KPIs
 * Calculates KPIs that match postmortem-dashboard.html
 * Only used if file type is 'postmortem' and has Despliegue field
 */
function extractPostmortemKPIs(incidents, metadata) {
    if (!incidents || incidents.length === 0) {
        return [];
    }

    const totalRecords = incidents.length;
    const fileType = metadata?.type || 'unknown';

    console.log(`[KPI DEBUG] File type: ${fileType}, Records: ${totalRecords}`);

    // Check if this is actually postmortem data with Despliegue field
    const hasDespliegue = incidents.some(i => getIncidentFieldValue(i, 'Despliegue'));

    if (!hasDespliegue && fileType !== 'postmortem') {
        console.log(`[KPI DEBUG] No Despliegue field found and file type is '${fileType}'. Returning empty KPIs.`);
        return [];
    }

    // Calculate percentages
    const closedCount = incidents.filter(i => {
        const status = (getIncidentFieldValue(i, 'Estatus') || '').toLowerCase();
        return status.includes('cerrado');
    }).length;
    const closedPercent = totalRecords > 0 ? Math.round((closedCount / totalRecords) * 100) : 0;

    console.log(`[KPI DEBUG] Total: ${totalRecords}, Cerrado: ${closedCount}, % Cerradas: ${closedPercent}%`);

    // Calculate PAP metrics (Cerrado + Resuelto)
    const papIncidents = incidents.filter(i => getIncidentFieldValue(i, 'Despliegue') === 'PAP');
    const papResolved = papIncidents.filter(i => {
        const status = (getIncidentFieldValue(i, 'Estatus') || '').toLowerCase();
        return status.includes('cerrado') || status.includes('resuelto');
    }).length;
    const papPercent = papIncidents.length > 0 ? Math.round((papResolved / papIncidents.length) * 100) : 0;

    console.log(`[KPI DEBUG] PAP Total: ${papIncidents.length}, Resuelto: ${papResolved}, % Resueltas PaP: ${papPercent}%`);

    // Calculate MESA metrics (Cerrado + Resuelto)
    const mesaIncidents = incidents.filter(i => getIncidentFieldValue(i, 'Despliegue') === 'MESA');
    const mesaResolved = mesaIncidents.filter(i => {
        const status = (getIncidentFieldValue(i, 'Estatus') || '').toLowerCase();
        return status.includes('cerrado') || status.includes('resuelto');
    }).length;
    const mesaPercent = mesaIncidents.length > 0 ? Math.round((mesaResolved / mesaIncidents.length) * 100) : 0;

    console.log(`[KPI DEBUG] MESA Total: ${mesaIncidents.length}, Resuelto: ${mesaResolved}, % Resueltas Mesa: ${mesaPercent}%`);

    // Only show postmortem KPIs if we have Despliegue data
    if (papIncidents.length > 0 || mesaIncidents.length > 0) {
        return [
            createKPICard(
                'total-postmortem-incidents',
                'Total Incidencias',
                totalRecords,
                'incidencias'
            ),
            createKPICard(
                'postmortem-closed-percent',
                '% Cerradas',
                closedPercent,
                '%'
            ),
            createKPICard(
                'postmortem-pap-resolved',
                '% Resueltas PaP',
                papPercent,
                '%'
            ),
            createKPICard(
                'postmortem-mesa-resolved',
                '% Resueltas Mesa',
                mesaPercent,
                '%'
            )
        ];
    }

    // Fallback if no Despliegue data found
    return [];
}

/* ============================================================================
   KPI Helper Functions
   ============================================================================ */

/**
 * Create a KPI card object
 */
function createKPICard(id, label, value, unit = '', trend = null) {
    return {
        id,
        label,
        value: Number(value) || 0,
        unit,
        trend,
        link: null // Can be populated with dashboard link
    };
}

/**
 * Count incidents with pending status at a given date
 * Uses SAME logic as Massive Incidents Dashboard:
 * - Count incidents that were OPEN on the target date
 * - Incident is open if: opened before target date AND (not closed OR closed after target date)
 */
function countPendingAtDate(incidents, targetDate) {
    return incidents.filter(incident => {
        const dateStr = incident['Fecha de envío'];
        if (!dateStr) return false;

        const incidentDate = parseDate(dateStr);
        if (!incidentDate) return false;

        // Only count if incident was opened on or before target date
        if (incidentDate > targetDate) return false;

        // Check if incident was still open on target date
        const status = (incident['Estatus'] || '').toLowerCase();

        // If status is closed, check if it was closed AFTER target date
        if (status.includes('cerrado') || status.includes('resuelto') || status.includes('cancelado')) {
            const resolveStr = incident['Fecha de última resolución'];
            if (resolveStr) {
                const resolveDate = parseDate(resolveStr);
                if (resolveDate) {
                    // Incident was still open on target date if resolved AFTER target date
                    return resolveDate > targetDate;
                }
            }
            // No resolution date found, assume it was closed
            return false;
        }

        // Status is not closed, so incident was open on target date
        return true;
    }).length;
}

/**
 * Parse date string in format "dd/mm/yyyy HH:mm a" or "dd/mm/yyyy HH:mm p"
 */
function parseDate(dateStr) {
    try {
        // Handle format: "26/04/2026 8:40 a" or "26/04/2026 8:40 p"
        const regex = /(\d{1,2})\/(\d{1,2})\/(\d{4})\s+(\d{1,2}):(\d{2})\s*([ap])/i;
        const match = dateStr.match(regex);

        if (!match) return null;

        const [, day, month, year, hour, minute, period] = match;
        let hourNum = parseInt(hour);

        // Convert to 24-hour format
        if (period.toLowerCase() === 'p' && hourNum !== 12) {
            hourNum += 12;
        } else if (period.toLowerCase() === 'a' && hourNum === 12) {
            hourNum = 0;
        }

        const date = new Date(parseInt(year), parseInt(month) - 1, parseInt(day), hourNum, parseInt(minute));
        return isValidDate(date) ? date : null;
    } catch (e) {
        console.warn('Failed to parse date:', dateStr, e);
        return null;
    }
}

/**
 * Check if date is valid
 */
function isValidDate(date) {
    return date instanceof Date && !isNaN(date.getTime());
}

/**
 * Calculate trend percentage
 */
function calculateTrendPercentage(oldValue, newValue) {
    if (oldValue === 0) {
        return newValue > 0 ? 100 : 0;
    }
    return ((newValue - oldValue) / oldValue) * 100;
}

/**
 * Get trend direction based on percentage
 */
function getTrendDirection(percentage) {
    if (Math.abs(percentage) < 2) return 'neutral';
    return percentage > 0 ? 'up' : 'down';
}

/* ============================================================================
   Rendering
   ============================================================================ */

/**
 * Render the complete hub with KPI cards
 */
function renderHub(kpiData) {
    try {
        // Clear containers
        massiveIncidentsContainer.innerHTML = '';
        postmortemContainer.innerHTML = '';

        // Render Massive Incidents KPIs
        if (kpiData.massiveIncidents && kpiData.massiveIncidents.length > 0) {
            kpiData.massiveIncidents.forEach(kpi => {
                massiveIncidentsContainer.appendChild(createKPICardElement(kpi));
            });
        }

        // Render Postmortem KPIs
        if (kpiData.postmortem && kpiData.postmortem.length > 0) {
            kpiData.postmortem.forEach(kpi => {
                postmortemContainer.appendChild(createKPICardElement(kpi));
            });
        }

        // Show content
        showContent();

    } catch (error) {
        console.error('Error rendering hub:', error);
        showError('Error al renderizar el hub');
    }
}

/**
 * Create a KPI card DOM element matching Massive Incidents Dashboard style
 */
function createKPICardElement(kpi) {
    const card = document.createElement('div');
    card.className = 'kpi-card';
    card.setAttribute('data-metric', kpi.id);

    // Add trend class if applicable
    if (kpi.trend) {
        card.classList.add(`trend-${kpi.trend.direction}`);
    }

    // Icon
    const icon = document.createElement('div');
    icon.className = 'kpi-icon';
    icon.textContent = getKPIIcon(kpi.id);

    // Content container
    const content = document.createElement('div');
    content.className = 'kpi-content';

    // Label
    const label = document.createElement('div');
    label.className = 'kpi-label';
    label.textContent = kpi.label;

    // Value
    const value = document.createElement('div');
    value.className = 'kpi-value';

    // Format value appropriately based on whether it's an integer or decimal
    let formattedValue = kpi.value;
    if (!Number.isInteger(kpi.value)) {
        formattedValue = kpi.value.toFixed(1);
    } else {
        formattedValue = formatNumber(kpi.value);
    }

    value.textContent = formattedValue;

    content.appendChild(label);
    content.appendChild(value);

    // Trend if present
    if (kpi.trend) {
        const trendDiv = document.createElement('div');
        trendDiv.className = `kpi-trend trend-${kpi.trend.direction}`;

        const trendIcon = document.createElement('span');
        trendIcon.className = 'trend-icon';
        trendIcon.textContent = getTrendIcon(kpi.trend.direction);

        const trendPercentage = document.createElement('span');
        trendPercentage.className = 'trend-percentage';
        const trendSign = kpi.trend.percentage >= 0 ? '+' : '';
        trendPercentage.textContent = `${trendSign}${kpi.trend.percentage.toFixed(1)}%`;

        const trendPeriod = document.createElement('span');
        trendPeriod.className = 'kpi-trend-period';
        trendPeriod.textContent = kpi.trend.period;

        trendDiv.appendChild(trendIcon);
        trendDiv.appendChild(trendPercentage);
        trendDiv.appendChild(trendPeriod);
        content.appendChild(trendDiv);
    }

    card.appendChild(icon);
    card.appendChild(content);

    return card;
}

/**
 * Get appropriate icon for KPI metric
 */
function getKPIIcon(metricId) {
    const icons = {
        'total-incidents': '📌',
        'pending-incidents': '⏳',
        'trend-7-day': '📈',
        'trend-15-day': '📊',
        'trend-30-day': '📉',
        'total-postmortems': '📋',
        'critical-urgency': '⚠️',
        'massive-impact': '💥',
        'unresolved-items': '❌'
    };
    return icons[metricId] || '📊';
}

/**
 * Get trend icon based on direction
 */
function getTrendIcon(direction) {
    switch (direction) {
        case 'up': return '↑';
        case 'down': return '↓';
        case 'neutral': return '→';
        default: return '→';
    }
}

/**
 * Format large numbers with commas
 */
function formatNumber(num) {
    // Handle decimal numbers (for percentages and averages)
    if (!Number.isInteger(num)) {
        // For decimals, limit to 1 decimal place
        return num.toFixed(1);
    }

    // For integers, add thousand separators
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

/**
 * Update last updated timestamp
 */
function updateLastUpdatedTimestamp() {
    if (hubState.lastUpdated) {
        const now = hubState.lastUpdated;
        const formatted = now.toLocaleString('es-ES', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
        lastUpdatedSpan.textContent = formatted;
    }
}

/* ============================================================================
   Event Listeners
   ============================================================================ */

document.addEventListener('DOMContentLoaded', initHub);

// Optional: Refresh data every 5 minutes
setInterval(() => {
    console.log('Auto-refreshing Dashboard Hub data...');
    initHub();
}, 5 * 60 * 1000);
