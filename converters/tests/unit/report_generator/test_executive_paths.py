"""
Pruebas unitarias para las rutas y gestión de archivos de informes ejecutivos.
Feature 010: 010-incident-executive-report
"""

import time
from pathlib import Path
import pytest
from report_generator.executive_paths import (
    get_executive_template_path,
    get_executive_reports_dir,
    get_executive_report_filename,
    get_executive_report_path,
    cleanup_old_executive_reports,
)


def test_get_executive_template_path():
    path = get_executive_template_path()
    assert path.exists()
    assert path.name.endswith(".pptx")


def test_get_executive_reports_dir():
    d = get_executive_reports_dir()
    assert d.exists()
    assert d.is_dir()


def test_get_executive_report_filename():
    fn = get_executive_report_filename("INC000123")
    assert fn == "RESUMEN_EJECUTIVO_INC000123.pptx"


def test_get_executive_report_path():
    p = get_executive_report_path("INC000123")
    assert p.name == "RESUMEN_EJECUTIVO_INC000123.pptx"


def test_cleanup_old_executive_reports(tmp_path, monkeypatch):
    import report_generator.executive_paths as ep
    monkeypatch.setattr(ep, "get_executive_reports_dir", lambda: tmp_path)

    # Create dummy files
    f1 = tmp_path / "RESUMEN_EJECUTIVO_1.pptx"
    f2 = tmp_path / "RESUMEN_EJECUTIVO_2.pptx"
    f3 = tmp_path / "RESUMEN_EJECUTIVO_3.pptx"
    f4 = tmp_path / "RESUMEN_EJECUTIVO_4.pptx"
    f5 = tmp_path / "RESUMEN_EJECUTIVO_5.pptx"
    f6 = tmp_path / "RESUMEN_EJECUTIVO_6.pptx"

    for f in [f1, f2, f3, f4, f5, f6]:
        f.write_text("dummy")

    # Set old mtime on f6
    old_time = time.time() - (20 * 86400)
    import os
    os.utime(f6, (old_time, old_time))

    removed = cleanup_old_executive_reports(max_age_days=14, keep_min=5)
    assert "RESUMEN_EJECUTIVO_6.pptx" in removed
    assert not f6.exists()
    assert f1.exists()

