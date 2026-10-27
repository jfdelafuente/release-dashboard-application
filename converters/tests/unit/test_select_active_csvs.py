from pathlib import Path
from converters.cli.select_active_csvs import (
    parse_file_date_key,
    detect_file_type_and_release,
    select_active_csv_files,
)


def test_detect_file_type_and_release():
    ftype, rel = detect_file_type_and_release("2026R7 MESA POST. Seguimiento Incidencias - 04 Aug 2026 (1).csv")
    assert ftype == "postmortem"
    assert rel == "2026R7"

    ftype, rel = detect_file_type_and_release("CS-Informe incidencias P1,  P2 y P3 - 2026 - 27 Oct 2026.csv")
    assert ftype == "massive"

    ftype, rel = detect_file_type_and_release("postmortem_general.csv")
    assert ftype == "postmortem"
    assert rel is None


def test_select_active_csv_files(tmp_path: Path):
    # Crear varios ficheros postmortem de R7
    (tmp_path / "2026R7 MESA POST - 04 Aug 2026.csv").write_text("a,b\n1,2")
    (tmp_path / "2026R7 MESA POST - 07 Aug 2026 (2).csv").write_text("a,b\n1,2")
    (tmp_path / "2026R7 MESA POST - 05 Aug 2026.csv").write_text("a,b\n1,2")

    # Crear varios ficheros postmortem de R9
    (tmp_path / "2026R9 MESA POST - 01 Oct 2026.csv").write_text("a,b\n1,2")
    (tmp_path / "2026R9 MESA POST - 26 Oct 2026.csv").write_text("a,b\n1,2")
    (tmp_path / "2026R9 MESA POST - 30 Sep 2026.csv").write_text("a,b\n1,2")

    # Crear varios ficheros masivos
    (tmp_path / "CS-Informe incidencias - 10_08_2026.csv").write_text("a,b\n1,2")
    (tmp_path / "CS-Informe incidencias - 26 Oct 2026.csv").write_text("a,b\n1,2")
    (tmp_path / "CS-Informe incidencias - 27 Oct 2026.csv").write_text("a,b\n1,2")

    selected = select_active_csv_files(tmp_path)

    # Debe haber exactamente 3 archivos seleccionados (R7, R9, massive)
    assert len(selected) == 3

    selected_names = {p.name for p, _, _ in selected}
    assert "2026R7 MESA POST - 07 Aug 2026 (2).csv" in selected_names
    assert "2026R9 MESA POST - 26 Oct 2026.csv" in selected_names
    assert "CS-Informe incidencias - 27 Oct 2026.csv" in selected_names
