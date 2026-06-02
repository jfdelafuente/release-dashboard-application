"""
Pytest configuration and fixtures for CSV Upload API tests
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from fastapi.testclient import TestClient
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.config import Config


@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)


@pytest.fixture
def temp_dir():
    """Temporary directory for test files"""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    # Cleanup
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_csv_content():
    """Sample valid CSV content"""
    return """ID de incidencia,Descripción,Estatus,Fecha de envío,Grupo asignado,Urgencia,Impacto,Fecha de última resolución
INC000003884945,LIVEPERSON // DERIO // ERROR FUNCIONAL,Cerrado,02/01/2026 8:14 AM,CEP CAU AGI,Baja,Masiva,12/01/2026 8:24 AM
INC000003884946,DELIVERY // ERROR INTERMITENTE,Abierto,03/01/2026 10:30 AM,SOP_CRMB2B,Media,Normal,
INC000003884947,LOGIN // PROBLEMA DE ACCESO,Pendiente,04/01/2026 2:45 PM,CEP CAU AGI,Alta,Crítica,
"""


@pytest.fixture
def invalid_csv_content():
    """CSV with missing required headers"""
    return """ID de incidencia,Descripción,Fecha de envío
INC000003884945,LIVEPERSON ERROR,02/01/2026 8:14 AM
INC000003884946,DELIVERY ERROR,03/01/2026 10:30 AM
"""


@pytest.fixture
def empty_csv_content():
    """CSV with headers but no data"""
    return """ID de incidencia,Descripción,Estatus,Fecha de envío,Grupo asignado,Urgencia,Impacto,Fecha de última resolución
"""


@pytest.fixture
def test_data_dir():
    """Path to test data directory"""
    return Path(__file__).parent / "test_data"


@pytest.fixture
def config():
    """Configuration fixture"""
    return Config


@pytest.fixture
def mock_upload_dir(temp_dir):
    """Mock upload directory"""
    Config.TEMP_UPLOAD_DIR = temp_dir
    yield temp_dir
    Config.TEMP_UPLOAD_DIR = "temp_uploads"


@pytest.fixture
def mock_data_dirs(temp_dir):
    """Mock data directories"""
    input_dir = Path(temp_dir) / "input"
    output_dir = Path(temp_dir) / "output"
    error_dir = Path(temp_dir) / "errors"

    input_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)
    error_dir.mkdir(exist_ok=True)

    original_input = Config.DATA_INPUT_DIR
    original_output = Config.DATA_OUTPUT_DIR
    original_error = Config.DATA_ERROR_DIR

    Config.DATA_INPUT_DIR = str(input_dir)
    Config.DATA_OUTPUT_DIR = str(output_dir)
    Config.DATA_ERROR_DIR = str(error_dir)

    yield {
        "input": input_dir,
        "output": output_dir,
        "error": error_dir
    }

    Config.DATA_INPUT_DIR = original_input
    Config.DATA_OUTPUT_DIR = original_output
    Config.DATA_ERROR_DIR = original_error


# Test markers
def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as an end-to-end test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow"
    )


@pytest.fixture(autouse=True)
def reset_config():
    """Reset config between tests"""
    yield
    Config.ensure_directories()


# Service fixtures - note: test classes define their own 'service' fixtures
# This fixture is only for tests that don't have a class-level fixture


# Logging fixtures
@pytest.fixture
def caplog_handler(caplog):
    """Fixture for capturing logs"""
    import logging
    caplog.set_level(logging.DEBUG)
    return caplog
