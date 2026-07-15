#!/usr/bin/env python3
"""
Unit tests for build_index_for_hub() release_name propagation.

No test coverage existed previously for build_index_for_hub() (see
specs/007-per-release-dashboards/research.md, R6) — this file is new.
"""

import json
import sys
from pathlib import Path

import pytest

# convert_postmortems.py lives under converters/cli/, imported as a plain module
cli_path = Path(__file__).parent.parent.parent / "cli"
if str(cli_path) not in sys.path:
    sys.path.insert(0, str(cli_path))

from convert_postmortems import build_index_for_hub  # noqa: E402


def _write_postmortem_json(path, release_name=None, record_count=1):
    metadata = {
        "type": "postmortem",
        "version": "1.0",
        "created": "2026-07-15T00:00:00Z",
        "source_filename": path.stem + ".csv",
        "record_count": record_count,
        "conversion_timestamp": "2026-07-15T00:00:00Z",
        "kpis": {"total": record_count, "by_estatus": {}, "by_urgencia": {}, "by_impacto": {}},
    }
    if release_name is not None:
        metadata["release_name"] = release_name

    path.write_text(
        json.dumps({"_metadata": metadata, "data": []}, ensure_ascii=False),
        encoding="utf-8",
    )


class TestBuildIndexReleaseName:
    """Test that build_index_for_hub() reads release_name from _metadata into index.json."""

    def test_release_name_included_when_present(self, tmp_path):
        """A postmortem JSON with _metadata.release_name gets it copied into index.json."""
        _write_postmortem_json(tmp_path / "2026R4-postmortem.json", release_name="2026R4")

        assert build_index_for_hub(str(tmp_path)) is True

        index = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
        files = index["postmortem"]["files"]
        assert len(files) == 1
        assert files[0]["release_name"] == "2026R4"

    def test_release_name_none_for_legacy_file_without_metadata_field(self, tmp_path):
        """A postmortem JSON generated before this feature (no release_name in _metadata) yields release_name: None, not an error."""
        _write_postmortem_json(tmp_path / "legacy-postmortem.json", release_name=None)

        assert build_index_for_hub(str(tmp_path)) is True

        index = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
        files = index["postmortem"]["files"]
        assert len(files) == 1
        assert files[0]["release_name"] is None

    def test_multiple_files_each_keep_their_own_release_name(self, tmp_path):
        """Two postmortem files with different release_name values don't get mixed up."""
        _write_postmortem_json(tmp_path / "2026R4-postmortem.json", release_name="2026R4")
        _write_postmortem_json(tmp_path / "2026R6-postmortem.json", release_name="2026R6-MESA")

        assert build_index_for_hub(str(tmp_path)) is True

        index = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
        by_name = {f["release_name"]: f["name"] for f in index["postmortem"]["files"]}
        assert by_name["2026R4"] == "2026R4-postmortem.json"
        assert by_name["2026R6-MESA"] == "2026R6-postmortem.json"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
