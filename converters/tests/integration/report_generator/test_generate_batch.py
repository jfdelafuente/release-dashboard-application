"""Test de integración: generate_all_reports() (User Story 3).

3 releases sintéticas, una de ellas sin datos válidos (provoca fallo),
para comprobar que --all no se detiene ante un fallo individual.
"""
from generate_postmortem_report import generate_all_reports


class TestGenerateAllReports:
    def test_continues_after_one_release_fails(self, tmp_path, monkeypatch):
        good_records = [
            {"ID de incidencia": "INC1", "Estatus": "Cerrado", "Despliegue": "MESA",
             "Fecha de envío": "10/06/2026 08:00", "Fecha de última resolución": "10/06/2026 09:00",
             "Grupo asignado": "SOP_A"},
        ]

        def fake_list_release_names():
            return ["2026R6", "2026R7-BROKEN", "2026R8"]

        def fake_load_records(release_name, output_dir=None):
            if release_name == "2026R7-BROKEN":
                raise ValueError("Datos corruptos simulados")
            return good_records

        monkeypatch.setattr("generate_postmortem_report.list_available_release_names", fake_list_release_names)
        monkeypatch.setattr("generate_postmortem_report.load_postmortem_records", fake_load_records)
        monkeypatch.setattr(
            "generate_postmortem_report.find_postmortem_file",
            lambda release_name, output_dir=None: tmp_path / f"{release_name}-postmortem.json",
        )
        monkeypatch.setattr(
            "generate_postmortem_report.load_release_kpis_context",
            lambda path=None: (_ for _ in ()).throw(FileNotFoundError()),
        )

        result = generate_all_reports(output_dir=tmp_path)

        assert sorted(result["generated"]) == ["2026R6", "2026R8"]
        assert len(result["failed"]) == 1
        assert result["failed"][0]["release_name"] == "2026R7-BROKEN"
        assert (tmp_path / "2026R6-postmortem-report.pptx").exists()
        assert (tmp_path / "2026R8-postmortem-report.pptx").exists()
        assert not (tmp_path / "2026R7-BROKEN-postmortem-report.pptx").exists()

    def test_no_releases_available_returns_empty_lists(self, tmp_path, monkeypatch):
        monkeypatch.setattr("generate_postmortem_report.list_available_release_names", lambda: [])
        result = generate_all_reports(output_dir=tmp_path)
        assert result == {"generated": [], "failed": []}
