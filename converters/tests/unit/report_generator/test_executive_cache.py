"""
Pruebas unitarias para la caché y comprobación de existencia de informes ejecutivos.
Feature 010: 010-incident-executive-report
"""

import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from converters.src.report_generator.executive_models import ExecutiveIncidentData
from converters.src.report_generator.executive_paths import (
    get_executive_report_path,
    get_executive_report_filename,
)
from converters.src.report_generator.executive_report_builder import ExecutiveReportBuilder


def test_cache_and_force_regeneration(tmp_path):
    incident_ref = "TESTCACHE01"
    output_path = tmp_path / get_executive_report_filename(incident_ref)

    assert not output_path.exists()

    data = ExecutiveIncidentData(
        incident_ref=incident_ref,
        title="Incidencia de prueba de caché",
    )
    builder = ExecutiveReportBuilder()

    # 1. Primera generación
    meta1 = builder.generate(data, output_path)
    assert output_path.exists()
    mtime1 = output_path.stat().st_mtime_ns

    # 2. Generación forzada
    data.title = "Título actualizado tras regenerar"
    meta2 = builder.generate(data, output_path)
    assert output_path.exists()
    assert meta2.slide_count >= 3
