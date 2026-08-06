"""Test de integración: generate_all_reports() (User Story 3).

3 releases en releases-data.js; una de ellas provoca un fallo al construir
su presentación, para comprobar que --all no se detiene ante un fallo
individual.
"""
import generate_postmortem_report
from generate_postmortem_report import generate_all_reports


_RELEASES_JS = """"use strict";
const RAW_RELEASES = [
  ["2026R6", 2026, "7-jun.", "Junio", 53, 46, 38, 33],
  ["2026R7-BROKEN", 2026, "7-jul.", "Julio", 70, 54, 107, 84],
  ["2026R8", 2026, "7-ago.", "Agosto", 40, 35, 20, 18],
];
"""


class TestGenerateAllReports:
    def test_continues_after_one_release_fails(self, tmp_path, monkeypatch):
        releases_data_path = tmp_path / "releases-data.js"
        releases_data_path.write_text(_RELEASES_JS, encoding="utf-8")
        monkeypatch.setattr("generate_postmortem_report.DEFAULT_RELEASES_DATA_PATH", releases_data_path)
        monkeypatch.setattr(
            "generate_postmortem_report.load_release_kpis_context",
            lambda: __import__(
                "report_generator.release_kpis_data", fromlist=["load_release_kpis_context"]
            ).load_release_kpis_context(path=releases_data_path),
        )

        real_new_presentation = generate_postmortem_report.new_presentation

        def _fake_new_presentation(release_name):
            if release_name == "2026R7-BROKEN":
                raise ValueError("Datos corruptos simulados")
            return real_new_presentation(release_name)

        monkeypatch.setattr("generate_postmortem_report.new_presentation", _fake_new_presentation)

        result = generate_all_reports(output_dir=tmp_path)

        assert sorted(result["generated"]) == ["2026R6", "2026R8"]
        assert len(result["failed"]) == 1
        assert result["failed"][0]["release_name"] == "2026R7-BROKEN"
        assert (tmp_path / "2026R6-postmortem-report.pptx").exists()
        assert (tmp_path / "2026R8-postmortem-report.pptx").exists()
        assert not (tmp_path / "2026R7-BROKEN-postmortem-report.pptx").exists()

    def test_no_releases_available_returns_empty_lists(self, tmp_path, monkeypatch):
        monkeypatch.setattr("generate_postmortem_report.load_release_kpis_context", lambda: [])
        result = generate_all_reports(output_dir=tmp_path)
        assert result == {"generated": [], "failed": []}
