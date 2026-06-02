/**
 * CSV Upload Modal Handler
 * Manages file selection, validation, and upload process
 */

class UploadModalHandler {
  constructor(config = {}) {
    this.config = {
      apiBaseUrl: config.apiBaseUrl || 'http://localhost:8000',
      maxFileSize: config.maxFileSize || 500 * 1024 * 1024, // 500MB default
      ...config
    };

    this.modal = document.getElementById('upload-modal');
    this.dropZone = document.getElementById('drop-zone');
    this.fileInput = document.getElementById('file-input');
    this.modalOverlay = document.getElementById('modal-overlay');
    this.modalCloseBtn = document.getElementById('modal-close-btn');

    this.currentFile = null;
    this.validationReport = null;

    this.initEventListeners();
  }

  initEventListeners() {
    // Modal controls
    this.modalCloseBtn.addEventListener('click', () => this.closeModal());
    this.modalOverlay.addEventListener('click', () => this.closeModal());

    // Buttons
    document.getElementById('btn-cancel').addEventListener('click', () => this.closeModal());
    document.getElementById('btn-upload').addEventListener('click', () => this.startUpload());
    document.getElementById('btn-confirm').addEventListener('click', () => this.confirmAndConvert());
    document.getElementById('btn-back-to-select').addEventListener('click', () => this.goBackToSelect());

    // Drag and drop
    this.dropZone.addEventListener('dragover', (e) => this.handleDragOver(e));
    this.dropZone.addEventListener('dragleave', (e) => this.handleDragLeave(e));
    this.dropZone.addEventListener('drop', (e) => this.handleDrop(e));
    this.dropZone.addEventListener('click', () => this.fileInput.click());

    // File input
    this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
  }

  openModal() {
    this.modal.classList.remove('hidden');
    this.resetModal();
  }

  closeModal() {
    this.modal.classList.add('hidden');
    this.resetModal();
  }

  resetModal() {
    this.currentFile = null;
    this.validationReport = null;
    this.showStep('select');
    this.hideFileInfo();
    this.clearError();
    this.fileInput.value = '';
  }

  showStep(stepName) {
    const steps = document.querySelectorAll('.upload-step');
    steps.forEach(step => step.classList.remove('active'));

    const targetStep = document.getElementById(`upload-step-${stepName}`);
    if (targetStep) {
      targetStep.classList.add('active');
    }
  }

  handleDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
    this.dropZone.classList.add('drag-over');
  }

  handleDragLeave(e) {
    e.preventDefault();
    e.stopPropagation();
    this.dropZone.classList.remove('drag-over');
  }

  handleDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    this.dropZone.classList.remove('drag-over');

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      this.handleFileSelect({ target: { files } });
    }
  }

  handleFileSelect(e) {
    const files = e.target.files;
    if (files.length === 0) return;

    const file = files[0];

    // Validate file type
    if (!file.name.endsWith('.csv')) {
      this.showError('El archivo debe ser un CSV válido');
      return;
    }

    // Validate file size
    if (file.size > this.config.maxFileSize) {
      const maxSizeMB = this.config.maxFileSize / (1024 * 1024);
      this.showError(`El archivo excede el límite de ${maxSizeMB}MB`);
      return;
    }

    this.currentFile = file;
    this.showFileInfo();
    this.clearError();
  }

  showFileInfo() {
    const fileInfo = document.getElementById('file-info');
    document.getElementById('file-name').textContent = this.currentFile.name;
    document.getElementById('file-size').textContent = this.formatFileSize(this.currentFile.size);

    fileInfo.classList.remove('hidden');

    // Check for warnings
    const warnings = this.checkFileWarnings();
    if (warnings.length > 0) {
      const warning = document.getElementById('file-warning');
      warning.textContent = warnings.join('; ');
      warning.classList.remove('hidden');
    } else {
      document.getElementById('file-warning').classList.add('hidden');
    }
  }

  hideFileInfo() {
    document.getElementById('file-info').classList.add('hidden');
    document.getElementById('file-warning').classList.add('hidden');
  }

  checkFileWarnings() {
    const warnings = [];
    if (!this.currentFile) return warnings;

    // Check file size (warn if over 50MB)
    if (this.currentFile.size > 50 * 1024 * 1024) {
      warnings.push('Archivo grande: la procesión puede tomar más tiempo');
    }

    return warnings;
  }

  showError(message) {
    const errorDiv = document.getElementById('error-select');
    errorDiv.textContent = message;
    errorDiv.classList.remove('hidden');
  }

  clearError() {
    document.getElementById('error-select').classList.add('hidden');
  }

  formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
  }

  async startUpload() {
    if (!this.currentFile) {
      this.showError('Selecciona un archivo');
      return;
    }

    // Show validation step
    this.showStep('validation');

    // Show progress bar
    const progressBar = document.getElementById('validation-progress');
    progressBar.classList.remove('hidden');

    try {
      // Create FormData
      const formData = new FormData();
      formData.append('file', this.currentFile);

      // Upload and validate
      const response = await fetch(`${this.config.apiBaseUrl}/api/upload`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
      }

      this.validationReport = await response.json();

      // Hide progress bar
      progressBar.classList.add('hidden');

      // Show validation results
      this.showValidationResults();
    } catch (error) {
      console.error('Upload error:', error);
      progressBar.classList.add('hidden');
      this.showValidationError(error.message);
    }
  }

  showValidationResults() {
    const { success, metadata, errors } = this.validationReport;

    if (success) {
      this.showValidationSuccess(metadata);
    } else {
      this.showValidationError(errors);
    }
  }

  showValidationSuccess(metadata) {
    // Hide error section
    document.getElementById('validation-error').classList.add('hidden');

    // Show success section
    const successDiv = document.getElementById('validation-success');
    successDiv.classList.remove('hidden');

    // Update metadata display
    document.getElementById('val-filename').textContent = metadata.filename || this.currentFile.name;
    document.getElementById('val-filesize').textContent = this.formatFileSize(metadata.file_size || this.currentFile.size);
    document.getElementById('val-encoding').textContent = metadata.encoding_detected || 'UTF-8';
    document.getElementById('val-delimiter').textContent = metadata.delimiter_detected || ',';
    document.getElementById('val-rowcount').textContent = metadata.record_count || '0';
    document.getElementById('val-headers').textContent = (metadata.headers || []).join(', ');

    // Show warnings if any
    if (metadata.warnings && metadata.warnings.length > 0) {
      const warningsDiv = document.getElementById('validation-warnings');
      const warningsList = document.getElementById('warnings-list');
      warningsList.innerHTML = metadata.warnings
        .map(w => `<li>${w}</li>`)
        .join('');
      warningsDiv.classList.remove('hidden');
    } else {
      document.getElementById('validation-warnings').classList.add('hidden');
    }

    // Show confirm button
    document.getElementById('btn-confirm').classList.remove('hidden');
    document.getElementById('btn-upload').classList.add('hidden');
  }

  showValidationError(errorMessage) {
    // Hide success section
    document.getElementById('validation-success').classList.add('hidden');

    // Show error section
    const errorDiv = document.getElementById('validation-error');
    errorDiv.classList.remove('hidden');

    const errorDetails = document.getElementById('error-details');
    if (typeof errorMessage === 'object') {
      errorDetails.textContent = JSON.stringify(errorMessage, null, 2);
    } else {
      errorDetails.textContent = errorMessage;
    }

    // Show back button
    document.getElementById('btn-back-to-select').classList.remove('hidden');
    document.getElementById('btn-confirm').classList.add('hidden');
    document.getElementById('btn-upload').classList.add('hidden');
  }

  async confirmAndConvert() {
    if (!this.validationReport) return;

    // Show processing step
    this.showStep('processing');

    try {
      // Call convert endpoint
      const response = await fetch(`${this.config.apiBaseUrl}/api/convert`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          filename: this.currentFile.name,
          metadata: this.validationReport.metadata
        })
      });

      if (!response.ok) {
        throw new Error(`Conversion failed: ${response.statusText}`);
      }

      const result = await response.json();

      // Show success notification
      notificationManager.showSuccess('CSV convertido exitosamente');

      // Close modal after a brief delay
      setTimeout(() => this.closeModal(), 2000);
    } catch (error) {
      console.error('Conversion error:', error);
      notificationManager.showError(`Error en la conversión: ${error.message}`);
      this.goBackToSelect();
    }
  }

  goBackToSelect() {
    this.validationReport = null;
    this.showStep('select');
    document.getElementById('btn-upload').classList.remove('hidden');
    document.getElementById('btn-confirm').classList.add('hidden');
    document.getElementById('btn-back-to-select').classList.add('hidden');
  }
}

// Global instance
let uploadModalHandler = null;

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  uploadModalHandler = new UploadModalHandler({
    apiBaseUrl: 'http://localhost:8000'
  });
});
