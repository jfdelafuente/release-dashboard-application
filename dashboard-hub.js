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
        const incidents = await loadLatestJSON();

        if (!incidents || incidents.length === 0) {
            showError('No hay datos disponibles. Por favor cargue archivos JSON en data/output/');
            return;
        }

        // Store in global state
        hubState.allIncidents = incidents;
        hubState.lastUpdated = new Date();

        // Extract KPIs
        const kpis = extractKPIs(incidents);

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
 */
async function loadLatestJSON() {
    try {
        // Fetch the index.json file that lists all available JSON files
        const indexResponse = await fetch(`${DATA_OUTPUT_DIR}index.json`);

        if (!indexResponse.ok) {
            throw new Error('No se encontró el archivo index.json en data/output/');
        }

        const fileList = await indexResponse.json();

        if (!Array.isArray(fileList) || fileList.length === 0) {
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
        if (Array.isArray(data)) {
            // Old format: direct array of incidents
            incidents = data;
        } else if (data._metadata && data.data) {
            // New format: object with metadata and data
            const metadata = data._metadata;

            // Validate that this is a massive incidents file
            if (metadata.type !== 'massive') {
                throw new Error(`Archivo no válido: esperado tipo 'massive', recibido '${metadata.type}'`);
            }

            incidents = data.data;
            console.log(`Metadata: type=${metadata.type}, version=${metadata.version}, records=${metadata.record_count}`);
        } else {
            throw new Error('Formato de JSON no reconocido');
        }

        console.log(`Successfully loaded ${incidents.length} incidents from ${latestFile.name}`);

        return incidents;

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
 */
function extractKPIs(incidents) {
    return {
        massiveIncidents: extractMassiveIncidentsKPIs(incidents),
        postmortem: extractPostmortemKPIs(incidents)
    };
}

/**
 * Extract Massive Incidents KPIs
 * Uses same logic as Massive Incidents Dashboard for consistency
 */
function extractMassiveIncidentsKPIs(incidents) {
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
 * Extract Postmortem Dashboard KPIs
 * Note: Currently using incident data; connect to postmortem data when available
 */
function extractPostmortemKPIs(incidents) {
    if (!incidents || incidents.length === 0) {
        return [];
    }

    // For now, create summary statistics from incident data
    // When postmortem data is available, this should extract from that instead

    const totalRecords = incidents.length;
    const byUrgencia = {};
    const byImpacto = {};

    incidents.forEach(incident => {
        // Count by urgency
        const urgencia = incident['Urgencia'] || 'Desconocida';
        byUrgencia[urgencia] = (byUrgencia[urgencia] || 0) + 1;

        // Count by impact
        const impacto = incident['Impacto'] || 'Desconocida';
        byImpacto[impacto] = (byImpacto[impacto] || 0) + 1;
    });

    // Find most critical urgency
    const criticalCount = byUrgencia['Crítica'] || 0;
    const highCount = byUrgencia['Alta'] || 0;

    // Find most impactful incidents
    const massiveImpactCount = byImpacto['Masiva'] || 0;

    return [
        createKPICard(
            'total-postmortems',
            'Total de Registros',
            totalRecords,
            'registros'
        ),
        createKPICard(
            'critical-urgency',
            'Criticidad Alta/Crítica',
            criticalCount + highCount,
            'incidencias'
        ),
        createKPICard(
            'massive-impact',
            'Impacto Masivo',
            massiveImpactCount,
            'incidencias'
        ),
        createKPICard(
            'unresolved-items',
            'Elementos Pendientes',
            incidents.filter(i => !CLOSED_STATUSES.includes(i['Estatus'])).length,
            'pendientes'
        )
    ];
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
 */
function countPendingAtDate(incidents, targetDate) {
    return incidents.filter(incident => {
        const dateStr = incident['Fecha de envío'];
        if (!dateStr) return false;

        const incidentDate = parseDate(dateStr);
        if (!incidentDate) return false;

        // Only count if incident was opened before or on target date
        if (incidentDate > targetDate) return false;

        // Check if incident was still pending on target date
        // For simplicity, we'll count incidents that were opened before target date
        // In production, would need resolution date to know exact status at that time
        const estatus = (incident['Estatus'] || '').toLowerCase().trim();
        return !CLOSED_STATUSES.some(s => s.toLowerCase() === estatus);
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
