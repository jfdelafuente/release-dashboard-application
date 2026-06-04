/**
 * Auto-Refresh Manager
 * Handles intelligent polling of index.json for data changes
 * Provides freshness indicators and cross-tab synchronization
 */

class AutoRefreshManager {
  constructor(config = {}) {
    this.config = {
      enabled: config.enabled !== false,
      intervalMs: config.intervalMs || 10000,
      minIntervalMs: config.minIntervalMs || 5000,
      maxIntervalMs: config.maxIntervalMs || 60000,
      indexJsonPath: config.indexJsonPath || '/data/output/index.json',
      changeDetectionCooldown: config.changeDetectionCooldown || 1000,
      onDataChanged: config.onDataChanged || (() => {}),
      onRefreshStart: config.onRefreshStart || (() => {}),
      onRefreshComplete: config.onRefreshComplete || (() => {}),
      onRefreshError: config.onRefreshError || (() => {}),
      ...config
    };

    this.pollingIntervalId = null;
    this.lastIndexData = null;
    this.lastCheckTime = 0;
    this.isRefreshing = false;
    this.lastUpdateTime = new Date();
    this.refreshCount = 0;
    this.errorCount = 0;

    // Storage key for cross-tab synchronization
    this.storageKey = 'dashboard_refresh_state';
    this.freshnessIndicatorId = 'data-freshness-indicator';

    // Initialize cross-tab listening
    this.initCrossTabSync();
  }

  /**
   * Start polling for data changes
   */
  startPolling() {
    if (!this.config.enabled) {
      debugLog('Auto-refresh disabled by configuration');
      return;
    }

    if (this.pollingIntervalId) {
      debugLog('Auto-refresh already running');
      return;
    }

    debugLog('Starting auto-refresh polling', { intervalMs: this.config.intervalMs });

    // Initial check immediately
    this.checkForChanges();

    // Setup interval polling
    this.pollingIntervalId = setInterval(() => {
      this.checkForChanges();
    }, this.config.intervalMs);
  }

  /**
   * Stop polling for data changes
   */
  stopPolling() {
    if (this.pollingIntervalId) {
      clearInterval(this.pollingIntervalId);
      this.pollingIntervalId = null;
      debugLog('Auto-refresh polling stopped');
    }
  }

  /**
   * Check if index.json has changed
   */
  async checkForChanges() {
    // Respect cooldown period
    const now = Date.now();
    if (now - this.lastCheckTime < this.config.changeDetectionCooldown) {
      return;
    }
    this.lastCheckTime = now;

    try {
      this.config.onRefreshStart();

      const response = await fetch(this.config.indexJsonPath, {
        method: 'GET',
        cache: 'no-cache',
        credentials: 'same-origin'
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch index.json: ${response.status}`);
      }

      const currentData = await response.json();
      const hasChanged = this.detectDataChange(currentData);

      if (hasChanged) {
        debugLog('Data change detected in index.json');
        this.lastIndexData = JSON.parse(JSON.stringify(currentData));
        this.lastUpdateTime = new Date();
        this.refreshCount++;
        this.errorCount = 0;

        // Notify all listeners
        this.broadcastRefreshEvent(currentData);
        this.config.onDataChanged(currentData);

        // Show notification
        if (notificationManager) {
          notificationManager.success('Datos del dashboard actualizados', 3000);
        }
      }

      this.config.onRefreshComplete(hasChanged);
      this.updateFreshnessIndicator();

    } catch (error) {
      debugLog('Error checking for data changes', error);
      this.errorCount++;

      this.config.onRefreshError(error);

      // Show error notification for network errors (not in cooldown)
      if (notificationManager && this.errorCount === 1) {
        notificationManager.warning('No se pudo verificar datos del servidor. Reintentando...', 5000);
      }
    } finally {
      this.isRefreshing = false;
    }
  }

  /**
   * Detect if data has changed by comparing checksums
   */
  detectDataChange(currentData) {
    if (!this.lastIndexData) {
      this.lastIndexData = JSON.parse(JSON.stringify(currentData));
      return true; // First load counts as change
    }

    // Simple deep comparison of JSON
    const lastChecksum = JSON.stringify(this.lastIndexData);
    const currentChecksum = JSON.stringify(currentData);

    return lastChecksum !== currentChecksum;
  }

  /**
   * Manually trigger a refresh
   */
  async manualRefresh() {
    debugLog('Manual refresh triggered');
    this.lastCheckTime = 0; // Reset cooldown
    return this.checkForChanges();
  }

  /**
   * Set polling interval
   */
  setInterval(intervalMs) {
    // Validate interval
    const validInterval = Math.max(
      this.config.minIntervalMs,
      Math.min(intervalMs, this.config.maxIntervalMs)
    );

    if (validInterval !== this.config.intervalMs) {
      this.config.intervalMs = validInterval;

      // Restart polling with new interval
      if (this.pollingIntervalId) {
        this.stopPolling();
        this.startPolling();
      }

      debugLog('Auto-refresh interval updated', { intervalMs: validInterval });
    }
  }

  /**
   * Enable/disable auto-refresh
   */
  setEnabled(enabled) {
    this.config.enabled = enabled;

    if (enabled) {
      this.startPolling();
    } else {
      this.stopPolling();
    }

    // Save to localStorage for persistence
    localStorage.setItem('auto_refresh_enabled', enabled);
  }

  /**
   * Get current state
   */
  getState() {
    return {
      enabled: this.config.enabled,
      intervalMs: this.config.intervalMs,
      isRefreshing: this.isRefreshing,
      lastUpdateTime: this.lastUpdateTime,
      refreshCount: this.refreshCount,
      errorCount: this.errorCount
    };
  }

  /**
   * Initialize cross-tab synchronization using storage events
   */
  initCrossTabSync() {
    window.addEventListener('storage', (event) => {
      if (event.key === 'dashboard_refresh_event') {
        try {
          const eventData = JSON.parse(event.newValue);
          debugLog('Refresh event from another tab', eventData);

          // Update our state from the event
          if (eventData.data) {
            this.lastIndexData = eventData.data;
            this.lastUpdateTime = new Date(eventData.timestamp);
            this.config.onDataChanged(eventData.data);
          }

          this.updateFreshnessIndicator();
        } catch (error) {
          console.error('Error processing refresh event from another tab:', error);
        }
      }
    });
  }

  /**
   * Broadcast refresh event to other tabs
   */
  broadcastRefreshEvent(data) {
    try {
      localStorage.setItem('dashboard_refresh_event', JSON.stringify({
        timestamp: new Date().toISOString(),
        data: data,
        tabId: this.getTabId()
      }));
    } catch (error) {
      debugLog('Error broadcasting refresh event', error);
    }
  }

  /**
   * Get unique tab ID
   */
  getTabId() {
    if (!window.__tabId) {
      window.__tabId = `tab_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
    return window.__tabId;
  }

  /**
   * Update freshness indicator display
   */
  updateFreshnessIndicator() {
    const indicator = document.getElementById(this.freshnessIndicatorId);
    if (!indicator) return;

    const now = new Date();
    const diff = now - this.lastUpdateTime;
    const minutes = Math.floor(diff / 60000);
    const seconds = Math.floor((diff % 60000) / 1000);

    let statusText = '';
    let statusClass = 'fresh';

    if (diff < 60000) {
      // Less than 1 minute
      statusText = 'Ahora mismo';
      statusClass = 'fresh';
    } else if (minutes < 5) {
      statusText = `Hace ${minutes}m`;
      statusClass = 'fresh';
    } else if (minutes < 30) {
      statusText = `Hace ${minutes}m`;
      statusClass = 'medium';
    } else {
      statusText = `Hace ${minutes}m`;
      statusClass = 'stale';
    }

    indicator.textContent = statusText;
    indicator.className = `freshness-indicator ${statusClass}`;
    indicator.setAttribute('aria-label', `Datos actualizados ${statusText}`);
  }

  /**
   * Create freshness indicator HTML
   */
  createFreshnessIndicator() {
    const indicator = document.createElement('div');
    indicator.id = this.freshnessIndicatorId;
    indicator.className = 'freshness-indicator fresh';
    indicator.setAttribute('role', 'status');
    indicator.setAttribute('aria-live', 'polite');
    indicator.setAttribute('aria-label', 'Estado de actualización de datos');
    return indicator;
  }

  /**
   * Create manual refresh button
   */
  createRefreshButton() {
    const button = document.createElement('button');
    button.className = 'refresh-button';
    button.id = 'manual-refresh-btn';
    button.textContent = '🔄 Actualizar';
    button.setAttribute('aria-label', 'Actualizar datos manualmente');
    button.addEventListener('click', async () => {
      button.disabled = true;
      button.classList.add('loading');
      try {
        await this.manualRefresh();
      } finally {
        button.disabled = false;
        button.classList.remove('loading');
      }
    });
    return button;
  }

  /**
   * Create auto-refresh toggle button
   */
  createAutoRefreshToggle() {
    const container = document.createElement('div');
    container.className = 'auto-refresh-toggle';

    const label = document.createElement('label');
    label.htmlFor = 'auto-refresh-toggle';
    label.textContent = 'Auto-actualizar:';

    const button = document.createElement('button');
    button.id = 'auto-refresh-toggle';
    button.className = 'toggle-switch active';
    button.setAttribute('aria-label', 'Alternar actualización automática');
    button.setAttribute('aria-pressed', 'true');

    button.addEventListener('click', () => {
      const newState = !button.classList.contains('active');
      this.setEnabled(newState);
      if (newState) {
        button.classList.add('active');
        button.setAttribute('aria-pressed', 'true');
        if (notificationManager) {
          notificationManager.info('Auto-actualización activada', 3000);
        }
      } else {
        button.classList.remove('active');
        button.setAttribute('aria-pressed', 'false');
        if (notificationManager) {
          notificationManager.info('Auto-actualización desactivada', 3000);
        }
      }
    });

    container.appendChild(label);
    container.appendChild(button);
    return container;
  }

  /**
   * Add controls (refresh button and toggle) to page
   */
  addControls(targetSelector = 'header') {
    const target = document.querySelector(targetSelector);
    if (!target) {
      debugLog('Target selector not found for controls', { targetSelector });
      return;
    }

    // Create controls container
    const controlsContainer = document.createElement('div');
    controlsContainer.className = 'dashboard-controls';

    // Add refresh button
    controlsContainer.appendChild(this.createRefreshButton());

    // Add toggle
    controlsContainer.appendChild(this.createAutoRefreshToggle());

    // Try to find existing controls container or create one
    let existingControls = target.querySelector('.dashboard-controls');
    if (existingControls) {
      existingControls.innerHTML = controlsContainer.innerHTML;
    } else {
      target.appendChild(controlsContainer);
    }
  }

  /**
   * Add freshness indicator to page
   */
  addFreshnessIndicator(targetSelector = 'header') {
    const target = document.querySelector(targetSelector);
    if (!target) {
      debugLog('Target selector not found for freshness indicator', { targetSelector });
      return;
    }

    let indicator = document.getElementById(this.freshnessIndicatorId);
    if (!indicator) {
      indicator = this.createFreshnessIndicator();
      target.appendChild(indicator);
    }

    this.updateFreshnessIndicator();

    // Update indicator every 10 seconds
    setInterval(() => this.updateFreshnessIndicator(), 10000);
  }
}

// Global instance
let autoRefreshManager = null;

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  if (window.AutoRefreshConfig) {
    autoRefreshManager = new AutoRefreshManager(window.AutoRefreshConfig);
  }
});
