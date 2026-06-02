/**
 * Notification Manager
 * Handles toast notifications for user feedback
 */

class NotificationManager {
  constructor(config = {}) {
    this.config = {
      duration: config.duration || 5000, // 5 seconds default
      maxNotifications: config.maxNotifications || 5,
      ...config
    };

    this.container = document.getElementById('notifications-container');
    if (!this.container) {
      // Create container if it doesn't exist
      this.container = document.createElement('div');
      this.container.id = 'notifications-container';
      this.container.className = 'notifications-container';
      document.body.appendChild(this.container);
    }

    this.notifications = [];
  }

  show(message, type = 'info', duration = null) {
    // Check max notifications
    if (this.notifications.length >= this.config.maxNotifications) {
      this.notifications[0].remove();
      this.notifications.shift();
    }

    const notificationEl = document.createElement('div');
    notificationEl.className = `notification ${type}`;
    notificationEl.textContent = message;
    notificationEl.setAttribute('role', 'alert');
    notificationEl.setAttribute('aria-live', 'polite');

    this.container.appendChild(notificationEl);
    this.notifications.push(notificationEl);

    // Auto-remove after duration
    const removeDelay = duration || this.config.duration;
    setTimeout(() => {
      notificationEl.style.animation = 'slideOut 0.3s ease';
      setTimeout(() => {
        notificationEl.remove();
        this.notifications = this.notifications.filter(n => n !== notificationEl);
      }, 300);
    }, removeDelay);

    return notificationEl;
  }

  success(message, duration = null) {
    return this.show(message, 'success', duration);
  }

  error(message, duration = null) {
    return this.show(message, 'error', duration || 7000); // Errors stay longer
  }

  warning(message, duration = null) {
    return this.show(message, 'warning', duration);
  }

  info(message, duration = null) {
    return this.show(message, 'info', duration);
  }

  clear() {
    this.notifications.forEach(notification => {
      notification.remove();
    });
    this.notifications = [];
  }
}

// Global instance
let notificationManager = null;

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  notificationManager = new NotificationManager();
});
