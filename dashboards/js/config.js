/**
 * Frontend Configuration
 * API endpoints and settings
 */

const API_CONFIG = {
  // Backend API base URL
  baseUrl: window.location.hostname === 'localhost'
    ? 'http://localhost:8000'
    : window.location.origin,

  // API endpoints
  endpoints: {
    upload: '/api/upload',
    confirmUpload: '/api/confirm-upload',
    health: '/api/health'
  },

  // Upload settings
  upload: {
    maxFileSize: 500 * 1024 * 1024, // 500MB
    maxFileSizeMB: 500,
    warningFileSize: 100 * 1024 * 1024, // 100MB
    allowedExtensions: ['.csv'],
    timeout: 300000 // 5 minutes
  },

  // Retry settings
  retry: {
    maxAttempts: 3,
    delayMs: [1000, 3000, 5000] // 1s, 3s, 5s
  },

  // Notification settings
  notifications: {
    duration: 5000,
    errorDuration: 7000,
    maxNotifications: 5
  },

  // Auto-refresh settings
  autoRefresh: {
    enabled: true,
    intervalMs: 10000, // 10 seconds default
    minIntervalMs: 5000, // Minimum 5 seconds
    maxIntervalMs: 60000, // Maximum 60 seconds
    indexJsonPath: '/data/output/index.json',
    changeDetectionCooldown: 1000 // 1 second before allowing next check
  },

  // Debug mode
  debug: window.location.hostname === 'localhost'
};

/**
 * Build full API URL
 * @param {string} endpoint - Endpoint path
 * @returns {string} Full API URL
 */
function getApiUrl(endpoint) {
  const baseUrl = API_CONFIG.baseUrl.replace(/\/$/, '');
  const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return `${baseUrl}${path}`;
}

/**
 * Log debug message if debug mode enabled
 * @param {string} message - Message to log
 * @param {*} data - Optional data
 */
function debugLog(message, data) {
  if (API_CONFIG.debug) {
    console.log(`[DEBUG] ${message}`, data || '');
  }
}
