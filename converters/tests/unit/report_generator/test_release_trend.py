"""Tests de report_generator.release_trend."""
import pytest

from report_generator.release_kpis_data import build_releases
from report_generator.release_trend import compute_release_trend, build_trend_narrative


def _releases(*rows):
    """rows: tuplas (name, pap_entrada, pap_resueltas, post_entrada, post_resueltas)."""
    raw = [
        [name, 2026, "", "Enero", pap_entrada, pap_resueltas, post_entrada, post_resueltas]
        for name, pap_entrada, pap_resueltas, post_entrada, post_resueltas in rows
    ]
    return build_releases(raw)


class TestComputeReleaseTrendNoBaseline:
    def test_first_release_in_history_has_no_baseline(self):
        releases = _releases(("2026R1", 50, 40, 30, 20))
        trend = compute_release_trend(releases, "2026R1", window=4)
        assert trend["has_baseline"] is False
        assert trend["window_releases"] == []
        assert trend["baseline_pct_pap"] is None
        assert trend["delta_pct_pap"] is None
        assert trend["baseline_pct_first_week"] is None
        assert trend["baseline_total_incidencias"] is None


class TestComputeReleaseTrendPartialBaseline:
    def test_uses_fewer_releases_when_history_is_short(self):
        # Solo 1 release anterior disponible, aunque window=4.
        releases = _releases(
            ("2026R1", 100, 50, 50, 25),   # pct_pap=50, pct_first_week=50, total=150
            ("2026R2", 80, 72, 20, 18),    # pct_pap=90, pct_first_week=90, total=100
        )
        trend = compute_release_trend(releases, "2026R2", window=4)
        assert trend["has_baseline"] is True
        assert len(trend["window_releases"]) == 1
        assert trend["baseline_pct_pap"] == 50
        assert trend["delta_pct_pap"] == 40.0
        assert trend["baseline_pct_first_week"] == 50
        assert trend["delta_pct_first_week"] == 40.0
        assert trend["baseline_total_incidencias"] == 150
        assert trend["delta_total_incidencias"] == -50.0


class TestComputeReleaseTrendFullWindow:
    def test_averages_exactly_window_releases(self):
        releases = _releases(
            ("2026R1", 100, 50, 0, 0),   # pct_pap=50
            ("2026R2", 100, 60, 0, 0),   # pct_pap=60
            ("2026R3", 100, 70, 0, 0),   # pct_pap=70
            ("2026R4", 100, 80, 0, 0),   # pct_pap=80
            ("2026R5", 100, 100, 0, 0),  # pct_pap=100 (release evaluada)
        )
        trend = compute_release_trend(releases, "2026R5", window=4)
        assert len(trend["window_releases"]) == 4
        # media de 50,60,70,80 = 65
        assert trend["baseline_pct_pap"] == 65.0
        assert trend["delta_pct_pap"] == 35.0

    def test_window_caps_at_configured_size_even_with_more_history(self):
        releases = _releases(
            ("2026R0", 100, 0, 0, 0),    # pct_pap=0 — debe quedar FUERA de la ventana de 4
            ("2026R1", 100, 50, 0, 0),
            ("2026R2", 100, 60, 0, 0),
            ("2026R3", 100, 70, 0, 0),
            ("2026R4", 100, 80, 0, 0),
            ("2026R5", 100, 100, 0, 0),  # release evaluada
        )
        trend = compute_release_trend(releases, "2026R5", window=4)
        assert len(trend["window_releases"]) == 4
        assert [r["name"] for r in trend["window_releases"]] == ["2026R1", "2026R2", "2026R3", "2026R4"]
        assert trend["baseline_pct_pap"] == 65.0


class TestComputeReleaseTrendErrors:
    def test_raises_for_unknown_release(self):
        releases = _releases(("2026R1", 50, 40, 30, 20))
        with pytest.raises(ValueError, match="NOPE"):
            compute_release_trend(releases, "NOPE")


class TestBuildTrendNarrative:
    def test_narrative_without_baseline(self):
        releases = _releases(("2026R1", 50, 40, 30, 20))
        trend = compute_release_trend(releases, "2026R1", window=4)
        narrative = build_trend_narrative(trend)
        assert "2026R1" in narrative
        assert "primera release" in narrative

    def test_narrative_includes_explicit_sign_on_deltas(self):
        releases = _releases(
            ("2026R1", 100, 50, 0, 0),
            ("2026R2", 100, 60, 0, 0),
            ("2026R3", 100, 70, 0, 0),
            ("2026R4", 100, 80, 0, 0),
            ("2026R5", 100, 100, 0, 0),
        )
        trend = compute_release_trend(releases, "2026R5", window=4)
        narrative = build_trend_narrative(trend)
        assert "2026R5" in narrative
        assert "+35.0 pp" in narrative

    def test_narrative_includes_negative_sign_for_worsening_release(self):
        releases = _releases(
            ("2026R1", 100, 90, 0, 0),
            ("2026R2", 100, 20, 0, 0),
        )
        trend = compute_release_trend(releases, "2026R2", window=4)
        narrative = build_trend_narrative(trend)
        assert "-70.0 pp" in narrative
