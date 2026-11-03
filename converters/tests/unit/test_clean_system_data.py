"""
test_clean_system_data.py
Unit tests for scripts/clean_system_data.py
"""

import json
import pytest
from pathlib import Path
import sys

SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import clean_system_data


def test_collect_and_execute_clean_in_temp_dir(tmp_path):
    storage_dir = tmp_path / "data"
    storage_dir.mkdir()

    # Create directories
    (storage_dir / "input").mkdir()
    (storage_dir / "output").mkdir()
    (storage_dir / "archive").mkdir()
    (storage_dir / "errors").mkdir()
    (storage_dir / ".epsilon_cache").mkdir()
    (storage_dir / "reports" / "executive").mkdir(parents=True)
    (storage_dir / "logs").mkdir()

    # Create dummy files to delete
    csv_file = storage_dir / "input" / "test.csv"
    csv_file.write_text("dummy csv")

    massive_json = storage_dir / "output" / "test-massive.json"
    massive_json.write_text('{"dummy": true}')

    postmortem_json = storage_dir / "output" / "test-postmortem.json"
    postmortem_json.write_text('{"dummy": true}')

    archive_file = storage_dir / "archive" / "old.json"
    archive_file.write_text('{"old": true}')

    error_file = storage_dir / "errors" / "test_errors.json"
    error_file.write_text('{"error": true}')

    cache_file = storage_dir / ".epsilon_cache" / "INC001.json"
    cache_file.write_text('{"summary": "ok"}')

    pptx_file = storage_dir / "reports" / "executive" / "report.pptx"
    pptx_file.write_bytes(b"dummy pptx")

    gitkeep = storage_dir / "reports" / "executive" / ".gitkeep"
    gitkeep.write_text("")

    # Create files to reset
    index_file = storage_dir / "output" / "index.json"
    index_file.write_text('{"postmortem": {"count": 5}}')

    hp_file = storage_dir / "output" / "high_priority_notifications.json"
    hp_file.write_text('{"data": [{"id": "INC001"}]}')

    audit_file = storage_dir / "output" / "ingestion_audit_summary.json"
    audit_file.write_text('{"incidents": [{"id": "INC001"}]}')

    msg_file = storage_dir / "agent_executive_messages.json"
    msg_file.write_text('{"INC001": {"draft": "hello"}}')

    log_file = storage_dir / "logs" / "ingestion_audit.log"
    log_file.write_text("2026-11-03 line 1\n2026-11-03 line 2\n")

    # Create protected files
    pap_file = storage_dir / "scheduled_changes_pap.json"
    pap_file.write_text('{"crq": 123}')

    catalog_file = storage_dir / "output" / "agents_catalog.json"
    catalog_file.write_text('{"agents": []}')

    # 1. Test Dry Run
    dry_result = clean_system_data.execute_clean(storage_dir, dry_run=True)
    assert dry_result["dry_run"] is True
    assert dry_result["deleted_count"] == 7  # csv, massive, postmortem, archive, error, cache, pptx
    assert dry_result["reset_count"] == 5
    assert dry_result["protected_count"] == 2
    assert csv_file.exists()  # Not deleted in dry run

    # 2. Test Real Execution
    real_result = clean_system_data.execute_clean(storage_dir, dry_run=False)
    assert real_result["dry_run"] is False
    assert real_result["deleted_count"] == 7
    assert real_result["reset_count"] == 5

    # Check deleted files are gone
    assert not csv_file.exists()
    assert not massive_json.exists()
    assert not postmortem_json.exists()
    assert not archive_file.exists()
    assert not error_file.exists()
    assert not cache_file.exists()
    assert not pptx_file.exists()

    # Check gitkeep is preserved
    assert gitkeep.exists()

    # Check protected files are intact
    assert pap_file.exists()
    assert json.loads(pap_file.read_text()) == {"crq": 123}
    assert catalog_file.exists()
    assert json.loads(catalog_file.read_text()) == {"agents": []}

    # Check reset files have empty structure
    idx_data = json.loads(index_file.read_text())
    assert idx_data["postmortem"]["count"] == 0
    assert idx_data["massive"]["count"] == 0

    hp_data = json.loads(hp_file.read_text())
    assert hp_data["data"] == []
    assert hp_data["_metadata"]["kpis"]["total_tickets"] == 0

    audit_data = json.loads(audit_file.read_text())
    assert audit_data["incidents"] == []
    assert audit_data["_metadata"]["kpis"]["total_tickets"] == 0

    assert json.loads(msg_file.read_text()) == {}
    assert log_file.read_text() == ""

