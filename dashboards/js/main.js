/**
 * Main Dashboard Handler
 * Initializes dashboard and handles global interactions
 */

document.addEventListener('DOMContentLoaded', () => {
  // Initialize upload modal handlers
  const uploadButtons = document.querySelectorAll('[data-action="open-upload-modal"]');
  uploadButtons.forEach(button => {
    button.addEventListener('click', () => {
      if (uploadModalHandler) {
        uploadModalHandler.openModal();
      }
    });
  });

  // Check if we're on the portal page and need to initialize it
  initializeDashboardPortal();
});

function initializeDashboardPortal() {
  const portalContainer = document.getElementById('dashboard-portal');
  if (!portalContainer) return;

  // This function would be called on the portal page
  // to set up navigation between dashboards
  console.log('Dashboard portal initialized');
}
