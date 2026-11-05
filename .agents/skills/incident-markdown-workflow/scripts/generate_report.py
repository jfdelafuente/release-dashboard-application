#!/usr/bin/env python3
"""
Punto de entrada CLI portable para generación de Informes Ejecutivos de Incidencias.
Delega la ejecución en el paquete modular `incident_report.cli`.
"""

import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(SCRIPT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from incident_report.cli import (
    DEFAULT_MD_OUTPUT,
    DEFAULT_PPTX_OUTPUT,
    DEFAULT_TEMPLATE,
    main,
    parse_args,
)

__all__ = [
    "DEFAULT_MD_OUTPUT",
    "DEFAULT_PPTX_OUTPUT",
    "DEFAULT_TEMPLATE",
    "main",
    "parse_args",
]

if __name__ == "__main__":
    main()

