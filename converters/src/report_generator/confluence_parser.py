"""
[DEPRECADO - Fase 1.1 Single Source of Truth]
El motor de informes ejecutivos PowerPoint (.pptx) reside exclusivamente en:
  cso-incident-masivas-report/backend/report_generator/confluence_parser.py

Este archivo actúa únicamente como puente de compatibilidad (re-export) hacia
la fuente única de verdad para no romper scripts o tests heredados.
"""

import os
import sys
from pathlib import Path

_CSO_BACKEND = Path(os.environ.get(
    "CSO_BACKEND_ROOT",
    str(Path(__file__).resolve().parents[4] / "cso-incident-masivas-report" / "backend")
))
try:
    if _CSO_BACKEND.is_dir() and str(_CSO_BACKEND) not in sys.path:
        sys.path.insert(0, str(_CSO_BACKEND))
except OSError:
    pass

from report_generator.confluence_parser import (  # noqa: F401, E402
    ConfluenceParser,
)

__all__ = ["ConfluenceParser"]
