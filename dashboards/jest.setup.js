/**
 * Jest setup file
 * Runs before each test suite
 */

// Mock fetch API
global.fetch = jest.fn();

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
global.localStorage = localStorageMock;

// Mock DOM for upload modal tests
document.body.innerHTML = `
  <div id="upload-modal" class="modal hidden">
    <div class="modal-content">
      <div class="modal-header">
        <h2>Subir Archivo CSV</h2>
        <button class="modal-close" id="modal-close-btn">×</button>
      </div>
      <div class="modal-body">
        <div id="upload-step-select" class="upload-step active"></div>
        <div id="upload-step-validation" class="upload-step hidden"></div>
        <div id="upload-step-processing" class="upload-step hidden"></div>
      </div>
      <div class="modal-footer">
        <button id="btn-cancel" class="btn-secondary">Cancelar</button>
        <button id="btn-upload" class="btn-primary">Subir y Convertir</button>
        <button id="btn-confirm" class="btn-primary hidden">Confirmar y Convertir</button>
      </div>
    </div>
    <div id="modal-overlay" class="modal-overlay"></div>
  </div>
  <div id="notifications-container" class="notifications-container"></div>
`;

// Suppress console errors in tests
const originalError = console.error;
beforeAll(() => {
  console.error = (...args) => {
    if (
      typeof args[0] === 'string' &&
      args[0].includes('Warning: ReactDOM.render')
    ) {
      return;
    }
    originalError.call(console, ...args);
  };
});

afterAll(() => {
  console.error = originalError;
});

// Clear mocks between tests
afterEach(() => {
  jest.clearAllMocks();
  localStorageMock.getItem.mockClear();
  localStorageMock.setItem.mockClear();
  localStorageMock.removeItem.mockClear();
  localStorageMock.clear.mockClear();
});
