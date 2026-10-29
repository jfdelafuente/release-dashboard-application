#!/usr/bin/env python3
"""Wrapper entrypoint for evaluate_incident_notifications."""
import sys
from pathlib import Path

# Add project root and cli directory to sys.path
root_dir = Path(__file__).resolve().parent.parent
cli_dir = Path(__file__).resolve().parent / "cli"
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))
if str(cli_dir) not in sys.path:
    sys.path.insert(0, str(cli_dir))

from converters.cli.evaluate_incident_notifications import main

if __name__ == "__main__":
    sys.exit(main())

