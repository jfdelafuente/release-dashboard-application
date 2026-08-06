"""Tests de report_generator.release_kpis_data."""
from report_generator.release_kpis_data import (
    parse_raw_releases, build_releases, load_release_kpis_context, find_release,
)


_SAMPLE_JS = """"use strict";
// comentario de ejemplo
const RAW_RELEASES = [
  ["2026R1", 2026, "15-feb.", "Febrero", 58, 50, 23, 23],
  ["2026R3", 2026, "", "Marzo", 0, 0, 26, 26],
];
"""


class TestParseRawReleases:
    def test_parses_literal_array(self):
        raw = parse_raw_releases(_SAMPLE_JS)
        assert raw == [
            ["2026R1", 2026, "15-feb.", "Febrero", 58, 50, 23, 23],
            ["2026R3", 2026, "", "Marzo", 0, 0, 26, 26],
        ]

    def test_raises_when_not_found(self):
        import pytest
        with pytest.raises(ValueError):
            parse_raw_releases("const OTHER_VAR = [];")


class TestBuildReleases:
    def test_derives_percentages(self):
        raw = parse_raw_releases(_SAMPLE_JS)
        releases = build_releases(raw)
        assert releases[0]["pct_pap"] == round(100 * 50 / 58)
        assert releases[0]["pct_first_week"] == round(100 * 23 / 23)

    def test_zero_entrada_gives_zero_percent_pap(self):
        """Réplica de buildReleases(): papEntrada == 0 no debe dividir por cero."""
        raw = parse_raw_releases(_SAMPLE_JS)
        releases = build_releases(raw)
        assert releases[1]["pap_entrada"] == 0
        assert releases[1]["pct_pap"] == 0

    def test_date_formatting_uses_fecha_when_present(self):
        raw = parse_raw_releases(_SAMPLE_JS)
        releases = build_releases(raw)
        assert releases[0]["date"] == "15 feb 2026"

    def test_date_formatting_falls_back_to_month_when_fecha_empty(self):
        raw = parse_raw_releases(_SAMPLE_JS)
        releases = build_releases(raw)
        assert releases[1]["date"] == "Marzo 2026"

    def test_total_incidencias_is_pap_plus_post_entrada(self):
        raw = parse_raw_releases(_SAMPLE_JS)
        releases = build_releases(raw)
        assert releases[0]["total_incidencias"] == 58 + 23


class TestFindRelease:
    def test_finds_release_by_exact_name(self):
        raw = parse_raw_releases(_SAMPLE_JS)
        releases = build_releases(raw)
        assert find_release(releases, "2026R3")["name"] == "2026R3"

    def test_returns_none_when_not_found(self):
        raw = parse_raw_releases(_SAMPLE_JS)
        releases = build_releases(raw)
        assert find_release(releases, "NOPE") is None


class TestLoadReleaseKpisContext:
    def test_loads_from_real_file(self, tmp_path):
        path = tmp_path / "releases-data.js"
        path.write_text(_SAMPLE_JS, encoding="utf-8")
        releases = load_release_kpis_context(path=path)
        assert len(releases) == 2
        assert releases[0]["name"] == "2026R1"
