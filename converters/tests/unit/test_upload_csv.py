import subprocess
from pathlib import Path
import sys
from unittest.mock import MagicMock, patch

# Ensure converters/cli/ is in sys.path
cli_path = Path(__file__).resolve().parent.parent.parent / "cli"
if str(cli_path) not in sys.path:
    sys.path.insert(0, str(cli_path))

from upload_csv import CONVERTER_SCRIPTS, run_upload


def test_run_upload_uses_project_root_converter(tmp_path):
    # Crear estructura simulada en tmp_path (como si fuera project_root)
    cli_dir = tmp_path / "converters" / "cli"
    cli_dir.mkdir(parents=True, exist_ok=True)
    custom_converter = cli_dir / CONVERTER_SCRIPTS["massive"]
    custom_converter.write_text("# mock converter", encoding="utf-8")

    csv_file = tmp_path / "test.csv"
    csv_file.write_text("a,b,c", encoding="utf-8")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        res = run_upload(csv_file, "massive", project_root=tmp_path)

        assert res["success"] is True
        # Verificar que ejecutó el conversor dentro de project_root y no otro
        called_args = mock_run.call_args_list[0][0][0]
        assert Path(called_args[1]) == custom_converter


def test_run_upload_fallback_when_not_in_project_root(tmp_path):
    # project_root no tiene converters/cli/
    csv_file = tmp_path / "test.csv"
    csv_file.write_text("a,b,c", encoding="utf-8")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        res = run_upload(csv_file, "massive", project_root=tmp_path)

        # Debe hacer fallback a Path(__file__).parent / convert_incidents.py que existe en el repo
        assert res["success"] is True
        called_args = mock_run.call_args_list[0][0][0]
        assert Path(called_args[1]).name == CONVERTER_SCRIPTS["massive"]
        assert Path(called_args[1]).exists()


def test_run_upload_massive_triggers_notifications_evaluator(tmp_path):
    cli_dir = tmp_path / "converters" / "cli"
    cli_dir.mkdir(parents=True, exist_ok=True)
    custom_converter = cli_dir / CONVERTER_SCRIPTS["massive"]
    custom_converter.write_text("# mock converter", encoding="utf-8")
    eval_script = cli_dir / "evaluate_incident_notifications.py"
    eval_script.write_text("# mock eval", encoding="utf-8")

    csv_file = tmp_path / "test.csv"
    csv_file.write_text("a,b,c", encoding="utf-8")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        res = run_upload(csv_file, "massive", project_root=tmp_path)

        assert res["success"] is True
        assert mock_run.call_count == 2
        eval_args = mock_run.call_args_list[1][0][0]
        assert Path(eval_args[1]) == eval_script


def test_run_upload_not_found_returns_error(tmp_path):
    csv_file = tmp_path / "test.csv"
    csv_file.write_text("a,b,c", encoding="utf-8")

    # Si dashboard_type no existe y se busca algo que no está en disco
    with patch.dict(CONVERTER_SCRIPTS, {"invalid": "nonexistent_script.py"}):
        res = run_upload(csv_file, "invalid", project_root=tmp_path)
        assert res["success"] is False
        assert "Converter no encontrado" in res["error"]

