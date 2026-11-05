"""
test_incident_triage_review.py

Pruebas unitarias para el script review_incident_triage.py de la skill incident-triage-review.
Valida la detección determinista de:
- LIFECYCLE_STATUS_MISMATCH (falsos cierres prematuros en tickets activos).
- AGING_ESCALATION_INDEBIDO (escalado a P1 en tickets con resolución planificada).
- INFRATRIAJE_REMEDY / SOBRETIAJE_REMEDY (desalineación entre Remedy y evaluación).
- CIERRE_PREMATURO_MULTI_SEDE (cierre con afectación persistente en alguna sede).
- Cumplimiento de límites de palabras (<= 90 monopárrafo, <= 30 telegráfico).
"""

import importlib.util
import json
from pathlib import Path
import pytest

# Cargar dinámicamente el módulo desde .agents/skills/incident-triage-review/scripts/review_incident_triage.py
SCRIPT_PATH = Path(__file__).resolve().parents[3] / ".agents" / "skills" / "incident-triage-review" / "scripts" / "review_incident_triage.py"

spec = importlib.util.spec_from_file_location("review_incident_triage", str(SCRIPT_PATH))
review_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review_mod)

normalize_priority = review_mod.normalize_priority
count_words = review_mod.count_words
is_single_paragraph = review_mod.is_single_paragraph
IncidentTriageReviewer = review_mod.IncidentTriageReviewer
format_markdown_report = review_mod.format_markdown_report


class TestIncidentTriageReviewHelpers:
    def test_normalize_priority(self):
        assert normalize_priority("Crítica") == "P1"
        assert normalize_priority("CRITICA") == "P1"
        assert normalize_priority("Alta") == "P2"
        assert normalize_priority("Media") == "P3"
        assert normalize_priority("Baja") == "P4"
        assert normalize_priority("P1") == "P1"
        assert normalize_priority("P2") == "P2"
        assert normalize_priority("") == ""

    def test_count_words(self):
        assert count_words("Hola mundo prueba de conteo") == 5
        assert count_words("") == 0
        assert count_words("   palabra1    palabra2   ") == 2

    def test_is_single_paragraph(self):
        assert is_single_paragraph("Texto en un solo párrafo.") is True
        assert is_single_paragraph("Texto con\nsalto de línea.") is False
        assert is_single_paragraph("") is True


class TestIncidentTriageReviewerMocked:
    @pytest.fixture
    def reviewer(self, tmp_path):
        # Crear estructura mínima simulada
        data_dir = tmp_path / "data"
        out_dir = data_dir / "output"
        out_dir.mkdir(parents=True)
        (data_dir / ".epsilon_cache").mkdir(parents=True)
        (tmp_path / "VERSION").write_text("1.0.0", encoding="utf-8")

        r = IncidentTriageReviewer(tmp_path)
        return r

    def test_detect_lifecycle_status_mismatch(self, reviewer):
        """Si el ticket está 'Asignado' y tiene mensaje de 'cierre', debe marcar LIFECYCLE_STATUS_MISMATCH."""
        inc_id = "INC000009990001"
        reviewer.massive_data[inc_id] = {
            "ID de incidencia": inc_id,
            "Estatus": "Asignado",
            "Prioridad": "Media",
            "Descripción": "Error en login"
        }
        reviewer.notifications_data[inc_id] = {
            "id": inc_id,
            "estatus": "Asignado",
            "prioridad_original": "P3",
            "prioridad_sugerida": "P3"
        }
        reviewer.executive_messages[inc_id] = {
            "apertura": {"completo": "Apertura P3", "breve": "Apertura P3"},
            "cierre": {"completo": "Cierre falso", "breve": "Cierre falso"}
        }

        res = reviewer.review_incident(inc_id)
        codes = [a["code"] for a in res["anomalias"]]
        assert "LIFECYCLE_STATUS_MISMATCH" in codes
        assert res["es_conforme"] is False

    def test_detect_infratriaje_remedy(self, reviewer):
        """Si Remedy es P3 y la evaluación técnica es P1 o P2, debe marcar INFRATRIAJE_REMEDY."""
        inc_id = "INC000009990002"
        reviewer.massive_data[inc_id] = {
            "ID de incidencia": inc_id,
            "Estatus": "Asignado",
            "Prioridad": "Media",
            "Descripción": "Caída masiva de ventas en Call Center"
        }
        reviewer.notifications_data[inc_id] = {
            "id": inc_id,
            "estatus": "Asignado",
            "prioridad_original": "P3",
            "prioridad_sugerida": "P1"
        }
        reviewer.executive_messages[inc_id] = {
            "seguimiento": {"completo": "Seguimiento P1", "breve": "Seguimiento P1"}
        }

        res = reviewer.review_incident(inc_id)
        codes = [a["code"] for a in res["anomalias"]]
        assert "INFRATRIAJE_REMEDY" in codes
        assert res["prioridad_remedy"] == "P3"
        assert res["prioridad_evaluada"] == "P1"

    def test_detect_aging_escalation_indebido_on_planned(self, reviewer):
        """Si el ticket tiene solución planificada y se escaló a P1 por aging, marcar AGING_ESCALATION_INDEBIDO."""
        inc_id = "INC000009990003"
        reviewer.massive_data[inc_id] = {
            "ID de incidencia": inc_id,
            "Estatus": "Pendiente",
            "Prioridad": "Media",
            "Descripción": "Subida prevista 17/11/2026 tras pase a producción"
        }
        reviewer.notifications_data[inc_id] = {
            "id": inc_id,
            "estatus": "Pendiente",
            "prioridad_original": "P3",
            "prioridad_sugerida": "P1",
            "es_planificada": True,
            "aging_escalated": True
        }
        reviewer.executive_messages[inc_id] = {
            "seguimiento": {"completo": "Seguimiento P1", "breve": "Seguimiento P1"}
        }

        res = reviewer.review_incident(inc_id)
        codes = [a["code"] for a in res["anomalias"]]
        assert "AGING_ESCALATION_INDEBIDO" in codes

    def test_detect_multisite_partial_resolution_false_closure(self, reviewer):
        """Si una sede está normalizada y otra reporta 'NO RESUELTO', marcar CIERRE_PREMATURO_MULTI_SEDE si hay cierre."""
        inc_id = "INC000009990004"
        reviewer.massive_data[inc_id] = {
            "ID de incidencia": inc_id,
            "Estatus": "Asignado",
            "Prioridad": "Media",
            "Descripción": "Afecta a sede Bosch-Vigo y Madison-Valladolid"
        }
        reviewer.notifications_data[inc_id] = {
            "id": inc_id,
            "estatus": "Asignado",
            "prioridad_original": "P3",
            "prioridad_sugerida": "P2",
            "resumen_ia": {
                "solucion": "Vigo normalizado el 26/10. Madison-Valladolid reportó NO RESUELTO."
            }
        }
        reviewer.executive_messages[inc_id] = {
            "cierre": {"completo": "Cierre anticipado", "breve": "Cierre anticipado"}
        }

        res = reviewer.review_incident(inc_id)
        codes = [a["code"] for a in res["anomalias"]]
        assert "CIERRE_PREMATURO_MULTI_SEDE" in codes

    def test_conforming_incident(self, reviewer):
        """Incidencia cerrada en Remedy con mensaje de cierre válido y sin discrepancias."""
        inc_id = "INC000009990005"
        reviewer.massive_data[inc_id] = {
            "ID de incidencia": inc_id,
            "Estatus": "Cerrado",
            "Prioridad": "Baja",
            "Descripción": "Consulta resuelta"
        }
        reviewer.notifications_data[inc_id] = {
            "id": inc_id,
            "estatus": "Cerrado",
            "prioridad_original": "P4",
            "prioridad_sugerida": "P4"
        }
        reviewer.executive_messages[inc_id] = {
            "cierre": {
                "completo": "Cierre confirmado del ticket sin incidencias adicionales.",
                "breve": "Cierre confirmado del ticket."
            }
        }

        res = reviewer.review_incident(inc_id)
        assert res["es_conforme"] is True
        assert len(res["anomalias"]) == 0

    def test_markdown_formatter(self, reviewer):
        inc_id = "INC000009990006"
        reviewer.massive_data[inc_id] = {
            "ID de incidencia": inc_id,
            "Estatus": "Asignado",
            "Prioridad": "Media",
            "Descripción": "Incidencia de prueba"
        }
        reviewer.notifications_data[inc_id] = {
            "id": inc_id,
            "estatus": "Asignado",
            "prioridad_original": "P3",
            "prioridad_sugerida": "P3"
        }
        res = reviewer.review_incident(inc_id)
        md = format_markdown_report(res)
        assert "Ficha de Revisión de Triaje: `INC000009990006`" in md
        assert "Estado en Remedy:" in md

