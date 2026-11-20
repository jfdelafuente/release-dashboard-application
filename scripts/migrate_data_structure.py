# -*- coding: utf-8 -*-
"""
Script de migración y modernización de la estructura de data/ (M22).
Crea la nueva taxonomía modular y migra datos existentes preservando
compatibilidad con las ubicaciones legacy.
"""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"


def ensure_directories():
    """Crea los directorios de la nueva arquitectura de datos."""
    new_dirs = [
        DATA_DIR / "config",
        DATA_DIR / "storage" / "raw",
        DATA_DIR / "storage" / "processed",
        DATA_DIR / "storage" / "projects",
        DATA_DIR / "storage" / "archive",
        DATA_DIR / "agents",
        DATA_DIR / "state",
        DATA_DIR / "cache" / "epsilon",
        DATA_DIR / "cache" / "remedy",
        DATA_DIR / "observability" / "logs",
        DATA_DIR / "observability" / "audits",
        DATA_DIR / "observability" / "quarantine",
        DATA_DIR / "reports" / "pptx",
        DATA_DIR / "reports" / "executive",
        PROJECT_ROOT / "specs" / "prompts",
        PROJECT_ROOT / "tests" / "fixtures" / "remedy",
    ]
    for d in new_dirs:
        d.mkdir(parents=True, exist_ok=True)
        print(f"  [DIR] {d.relative_to(PROJECT_ROOT)}")


def copy_or_sync(src: Path, dst: Path, move: bool = False):
    """Copia o mueve un archivo preservando timestamp."""
    if not src.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_file():
        shutil.copy2(src, dst)
        if move:
            try:
                src.unlink()
            except OSError:
                pass
        action = "MOVED" if move else "COPIED"
        print(f"  [{action}] {src.relative_to(PROJECT_ROOT)} -> {dst.relative_to(PROJECT_ROOT)}")
    elif src.is_dir():
        for item in src.iterdir():
            if item.is_file():
                target_file = dst / item.name
                shutil.copy2(item, target_file)
                if move:
                    try:
                        item.unlink()
                    except OSError:
                        pass
        if move:
            try:
                src.rmdir()
            except OSError:
                pass
        action = "SYNC_DIR" if not move else "MOVED_DIR"
        print(f"  [{action}] {src.relative_to(PROJECT_ROOT)} -> {dst.relative_to(PROJECT_ROOT)}")


def run_migration():
    print("=== Iniciando Migración Estructural de data/ ===")
    ensure_directories()

    # 1. Configuración (data/config/)
    copy_or_sync(DATA_DIR / "projects_catalog.json", DATA_DIR / "config" / "projects_catalog.json")
    copy_or_sync(DATA_DIR / "scheduled_changes_pap.json", DATA_DIR / "config" / "scheduled_changes_pap.json")
    copy_or_sync(DATA_DIR / "teams_channels_config.json", DATA_DIR / "config" / "teams_channels.json")

    # 2. Agentes e Inteligencia Artificial (data/agents/)
    copy_or_sync(DATA_DIR / "agent_executive_messages.json", DATA_DIR / "agents" / "executive_messages.json")
    copy_or_sync(DATA_DIR / "output" / "agents_catalog.json", DATA_DIR / "agents" / "catalog.json")
    copy_or_sync(DATA_DIR / "output" / "high_priority_notifications.json", DATA_DIR / "agents" / "high_priority_notifications.json")

    # 3. Estado de Runtime (data/state/)
    copy_or_sync(DATA_DIR / "release_desk_overrides.json", DATA_DIR / "state" / "release_desk_overrides.json")

    # 4. Storage - Procesados, Brutos e Índices (data/storage/)
    copy_or_sync(DATA_DIR / "output" / "index.json", DATA_DIR / "storage" / "index.json")
    copy_or_sync(DATA_DIR / "input", DATA_DIR / "storage" / "raw")
    copy_or_sync(DATA_DIR / "archive", DATA_DIR / "storage" / "archive")
    copy_or_sync(DATA_DIR / "projects", DATA_DIR / "storage" / "projects")

    # Copiar datasets masivos y postmortems a data/storage/processed/
    output_dir = DATA_DIR / "output"
    if output_dir.is_dir():
        for item in output_dir.glob("*.json"):
            if item.name.endswith("-postmortem.json") or item.name.endswith("-massive.json"):
                copy_or_sync(item, DATA_DIR / "storage" / "processed" / item.name)

    # 5. Cachés en disco (data/cache/)
    copy_or_sync(DATA_DIR / ".epsilon_cache", DATA_DIR / "cache" / "epsilon")
    copy_or_sync(DATA_DIR / ".remedy_cache", DATA_DIR / "cache" / "remedy")

    # 6. Observabilidad (data/observability/)
    copy_or_sync(DATA_DIR / "logs" / "ingestion_audit.log", DATA_DIR / "observability" / "logs" / "ingestion.log")
    copy_or_sync(DATA_DIR / "output" / "ingestion_audit_summary.json", DATA_DIR / "observability" / "audits" / "ingestion_summary.json")
    copy_or_sync(DATA_DIR / "output" / "teams_delivery_audit.json", DATA_DIR / "observability" / "audits" / "teams_delivery.json")
    copy_or_sync(DATA_DIR / "errors", DATA_DIR / "observability" / "quarantine")

    # 7. Relocalización de recursos fuera de data/
    copy_or_sync(DATA_DIR / "samples", PROJECT_ROOT / "tests" / "fixtures" / "remedy")
    copy_or_sync(DATA_DIR / "resumen_incidencia_epsilon.md", PROJECT_ROOT / "specs" / "prompts" / "resumen_incidencia_epsilon.md")

    # 8. Informes PPTX a reports/pptx/
    reports_dir = DATA_DIR / "reports"
    if reports_dir.is_dir():
        for pptx in reports_dir.glob("*.pptx"):
            copy_or_sync(pptx, reports_dir / "pptx" / pptx.name)

    print("\n=== Migración completada con éxito ===")


if __name__ == "__main__":
    run_migration()
