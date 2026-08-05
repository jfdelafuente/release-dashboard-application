"""Tests de report_generator.data_loader."""
import json
import pytest

from report_generator.data_loader import (
    load_postmortem_records,
    find_postmortem_file,
    list_available_release_names,
    ReleaseNotFoundError,
)


def _write_postmortem_json(path, release_name, records):
    path.write_text(
        json.dumps({"_metadata": {"release_name": release_name}, "data": records}, ensure_ascii=False),
        encoding="utf-8",
    )


class TestFindPostmortemFile:
    def test_finds_matching_release(self, tmp_path):
        _write_postmortem_json(tmp_path / "a-postmortem.json", "2026R7", [{"ID de incidencia": "INC1"}])
        found = find_postmortem_file("2026R7", output_dir=tmp_path)
        assert found == tmp_path / "a-postmortem.json"

    def test_returns_none_when_no_match(self, tmp_path):
        _write_postmortem_json(tmp_path / "a-postmortem.json", "2026R7", [])
        assert find_postmortem_file("2026R6", output_dir=tmp_path) is None

    def test_returns_none_when_directory_missing(self, tmp_path):
        assert find_postmortem_file("2026R7", output_dir=tmp_path / "no-existe") is None

    def test_picks_most_recent_when_duplicates(self, tmp_path):
        older = tmp_path / "older-postmortem.json"
        newer = tmp_path / "newer-postmortem.json"
        _write_postmortem_json(older, "2026R7", [])
        _write_postmortem_json(newer, "2026R7", [])
        import os
        import time
        time.sleep(0.01)
        os.utime(newer, None)
        found = find_postmortem_file("2026R7", output_dir=tmp_path)
        assert found == newer


class TestLoadPostmortemRecords:
    def test_loads_records_for_release(self, tmp_path):
        records = [{"ID de incidencia": "INC1"}, {"ID de incidencia": "INC2"}]
        _write_postmortem_json(tmp_path / "r7-postmortem.json", "2026R7", records)
        assert load_postmortem_records("2026R7", output_dir=tmp_path) == records

    def test_raises_for_unknown_release(self, tmp_path):
        _write_postmortem_json(tmp_path / "r7-postmortem.json", "2026R7", [])
        with pytest.raises(ReleaseNotFoundError, match="2026R6"):
            load_postmortem_records("2026R6", output_dir=tmp_path)

    def test_does_not_mix_different_releases(self, tmp_path):
        _write_postmortem_json(tmp_path / "r7-postmortem.json", "2026R7", [{"ID de incidencia": "INC-R7"}])
        _write_postmortem_json(tmp_path / "r6-postmortem.json", "2026R6", [{"ID de incidencia": "INC-R6"}])
        assert load_postmortem_records("2026R7", output_dir=tmp_path) == [{"ID de incidencia": "INC-R7"}]
        assert load_postmortem_records("2026R6", output_dir=tmp_path) == [{"ID de incidencia": "INC-R6"}]


class TestListAvailableReleaseNames:
    def test_lists_all_distinct_releases(self, tmp_path):
        _write_postmortem_json(tmp_path / "r7-postmortem.json", "2026R7", [])
        _write_postmortem_json(tmp_path / "r6-postmortem.json", "2026R6", [])
        assert list_available_release_names(output_dir=tmp_path) == ["2026R6", "2026R7"]

    def test_empty_when_directory_missing(self, tmp_path):
        assert list_available_release_names(output_dir=tmp_path / "no-existe") == []
