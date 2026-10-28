"""
Pruebas unitarias para los modelos de datos y extracción de campos ejecutivos.
Feature 010: 010-incident-executive-report
"""

import pytest
from report_generator.executive_models import (
    ExecutiveActionPoint,
    ExecutiveIncidentData,
    ExecutiveReportMetadata,
    ExecutiveTimelineEvent,
    extract_fields_from_jira_description,
    sanitize_incident_ref,
)


class TestSanitizeIncidentRef:
    def test_normal_ref(self):
        assert sanitize_incident_ref("INC123456") == "INC123456"

    def test_ref_with_special_characters(self):
        assert sanitize_incident_ref("INC-1234.56/SPAIN") == "INC-123456SPAIN"

    def test_empty_or_none_ref(self):
        assert sanitize_incident_ref("") == "INCIDENCIA"
        assert sanitize_incident_ref(None) == "INCIDENCIA"
        assert sanitize_incident_ref("   ") == "INCIDENCIA"


class TestExecutiveActionPoint:
    def test_default_values(self):
        ap = ExecutiveActionPoint()
        assert ap.pain_point == ""
        assert ap.description == ""
        assert ap.owner == ""
        assert ap.forecast == ""

    def test_from_dict_standard_keys(self):
        data = {
            "painPoint": "Detección",
            "description": "Mejorar alarmas",
            "owner": "Sistemas",
            "forecast": "W40",
        }
        ap = ExecutiveActionPoint.from_dict(data)
        assert ap.pain_point == "Detección"
        assert ap.description == "Mejorar alarmas"
        assert ap.owner == "Sistemas"
        assert ap.forecast == "W40"

    def test_from_dict_spanish_keys(self):
        data = {
            "tipo": "Solución",
            "descripcion": "Reiniciar servicio",
            "responsable": "Operaciones",
            "estado": "Cerrado",
        }
        ap = ExecutiveActionPoint.from_dict(data)
        assert ap.pain_point == "Solución"
        assert ap.description == "Reiniciar servicio"
        assert ap.owner == "Operaciones"
        assert ap.forecast == "Cerrado"

    def test_from_dict_non_dict(self):
        ap = ExecutiveActionPoint.from_dict("invalid")
        assert ap.pain_point == ""


class TestExecutiveTimelineEvent:
    def test_creation(self):
        event = ExecutiveTimelineEvent(time="10:00", event="Alarma detectada")
        assert event.time == "10:00"
        assert event.event == "Alarma detectada"


class TestExecutiveIncidentData:
    def test_serialization_roundtrip(self):
        data = ExecutiveIncidentData(
            incident_ref="INC001",
            title="Caída de servicio",
            start_time="2026-10-01 10:00",
            duration="2h",
            impact_text="Impacto en ventas",
            business_impact="50 clientes afectados",
            cause_text="Fallo de red",
            solution_text="Reinicio de router",
            action_points=[
                ExecutiveActionPoint(pain_point="Solución", description="Punto 1", owner="Dev", forecast="Listo")
            ],
            timeline_events=[
                ExecutiveTimelineEvent(time="10:05", event="Reinicio")
            ],
            source_url="https://jira.example.com/browse/INC001",
        )
        as_dict = data.to_dict()
        assert as_dict["incidentRef"] == "INC001"
        assert as_dict["title"] == "Caída de servicio"
        assert as_dict["actionPoints"][0]["painPoint"] == "Solución"
        assert as_dict["timelineEvents"][0]["time"] == "10:05"

        reconstructed = ExecutiveIncidentData.from_dict(as_dict)
        assert reconstructed.incident_ref == "INC001"
        assert reconstructed.impact_text == "Impacto en ventas"
        assert len(reconstructed.action_points) == 1
        assert reconstructed.action_points[0].owner == "Dev"
        assert len(reconstructed.timeline_events) == 1

    def test_from_dict_invalid_input(self):
        res = ExecutiveIncidentData.from_dict("invalid")
        assert res.incident_ref == "DESCONOCIDO"


class TestExecutiveReportMetadata:
    def test_to_dict(self):
        meta = ExecutiveReportMetadata(
            incident_ref="INC999",
            filename="RESUMEN_INC999.pptx",
            file_path="/tmp/RESUMEN_INC999.pptx",
            generated_at="2026-10-28T10:00:00Z",
            size_bytes=1024,
            slide_count=2,
        )
        d = meta.to_dict()
        assert d["incidentRef"] == "INC999"
        assert d["sizeBytes"] == 1024
        assert d["slideCount"] == 2


class TestExtractFieldsFromJiraDescription:
    def test_empty_or_none(self):
        assert extract_fields_from_jira_description("") == {}
        assert extract_fields_from_jira_description(None) == {}
        assert extract_fields_from_jira_description("   \n  ") == {}

    def test_explicit_labels(self):
        desc = """
        *INC000004151436 - CAIDA DEL SERVICIO*
        *Impacto:* Imposibilidad de acceso al portal de usuarios afectando a 500 personas.
        *Causa raíz:* Actualización incorrecta de los certificados TLS en el balanceador.
        *Solución:* Rollback de los certificados a la versión anterior y reinicio del ingress.
        """
        extracted = extract_fields_from_jira_description(desc)
        assert "500 personas" in extracted["impactText"]
        assert "certificados TLS" in extracted["causeText"]
        assert "Rollback" in extracted["solutionText"]

    def test_sequential_paragraphs_fallback(self):
        desc = """
        Los operadores no pueden emitir facturas en la plataforma de facturación.
        El pool de conexiones a la base de datos Oracle se agotó por sesiones zombies.
        Se procedió a reiniciar el datasource y liberar los bloqueos activos.
        """
        extracted = extract_fields_from_jira_description(desc)
        assert "facturas" in extracted["impactText"]
        assert "Oracle" in extracted["causeText"]
        assert "datasource" in extracted["solutionText"]

    def test_continuous_narrative_with_cues(self):
        desc = (
            "Se produjo una degradación severa en las llamadas de soporte debido a un fallo "
            "en el enlace de fibra con el proveedor externo. Se solucionó conmutando el tráfico "
            "hacia la ruta redundante secundaria."
        )
        extracted = extract_fields_from_jira_description(desc)
        assert "llamadas de soporte" in extracted["impactText"]
        assert "enlace de fibra" in extracted["causeText"]
        assert "ruta redundante" in extracted["solutionText"]

    def test_ignoring_only_header(self):
        desc = "*INC000004151436*"
        assert extract_fields_from_jira_description(desc) == {}
