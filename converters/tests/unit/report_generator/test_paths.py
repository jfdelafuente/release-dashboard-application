"""Tests de report_generator.paths."""
import pytest
from pathlib import Path

from report_generator.paths import sanitize_release_name, report_output_path, DEFAULT_REPORTS_DIR


class TestSanitizeReleaseName:
    def test_alphanumeric_unchanged(self):
        assert sanitize_release_name("2026R7") == "2026R7"

    def test_spaces_replaced(self):
        assert sanitize_release_name("2026 R7 Final") == "2026_R7_Final"

    def test_special_characters_replaced(self):
        assert sanitize_release_name("2026/R7:Final?") == "2026_R7_Final"

    def test_repeated_separators_collapsed(self):
        assert sanitize_release_name("2026   R7") == "2026_R7"

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            sanitize_release_name("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError):
            sanitize_release_name("   ")

    def test_only_special_characters_raises(self):
        with pytest.raises(ValueError):
            sanitize_release_name("///???")


class TestReportOutputPath:
    def test_default_directory(self):
        path = report_output_path("2026R7")
        assert path == DEFAULT_REPORTS_DIR / "2026R7-postmortem-report.pptx"

    def test_custom_directory(self):
        path = report_output_path("2026R7", output_dir="custom/dir")
        assert path == Path("custom/dir") / "2026R7-postmortem-report.pptx"

    def test_sanitizes_release_name_in_filename(self):
        path = report_output_path("2026 R7!")
        assert path.name == "2026_R7-postmortem-report.pptx"
