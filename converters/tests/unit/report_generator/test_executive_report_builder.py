"""
Pruebas unitarias para el generador de informes ejecutivos PowerPoint (ExecutiveReportBuilder).
Feature 010: 010-incident-executive-report
"""

import sys
from pathlib import Path
import pytest
import pptx

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from converters.src.report_generator.executive_models import (
    ExecutiveIncidentData,
    ExecutiveActionPoint,
    ExecutiveTimelineEvent,
)
from converters.src.report_generator.executive_report_builder import ExecutiveReportBuilder


@pytest.fixture
def sample_incident_data():
    return ExecutiveIncidentData(
        incident_ref="2606S77393",
        title="Problema de llamadas numeros IVRs de ATC exMM",
        start_time="09/06/2026 14:45:00",
        duration="3h 25m",
        impact_text="Se produjo una degradación progresiva del servicio de voz que evolucionó desde problemas de audio.",
        cause_text="Saturación del límite de conexiones/prefijos BGP en la interconexión con AWS.",
        solution_text="Tras la revisión por parte del TMC IP, se aumenta el límite de prefijos de 15k a 30k.",
        action_points=[
            ExecutiveActionPoint(pain_point="Solución", description="Ampliación prefix-BGP para servicio AWS", owner="TMC Acceso_Fijo", forecast="Cerrado"),
            ExecutiveActionPoint(pain_point="Detección", description="Implementar alarmas WARNING-limit sesiones BGP", owner="TMC Acceso_Fijo", forecast="W26"),
            ExecutiveActionPoint(pain_point="Detección", description="Auditoría de límites de prefijos de sesiones BGP", owner="TMC Acceso_Fijo", forecast="Cerrado"),
        ],
        timeline_events=[
            ExecutiveTimelineEvent(time="15:16", event="Se recibe ticket OPIT-906329 informando de cortes en llamadas."),
            ExecutiveTimelineEvent(time="15:49", event="IM Kyndryl escala a CSO."),
            ExecutiveTimelineEvent(time="16:00", event="Se abre incidencia masiva SL1 y bridge con equipos técnicos."),
            ExecutiveTimelineEvent(time="18:06", event="Se amplía límite de prefijos de 15K a 30K."),
            ExecutiveTimelineEvent(time="18:14", event="Confirmación: límite BGP estaba bloqueando tráfico. Servicio recuperándose."),
        ],
        source_url="https://confluence.si.orange.es/display/POSTMORTEM/INC-2606S77393",
    )


def test_builder_creates_presentation(sample_incident_data, tmp_path):
    output_path = tmp_path / "RESUMEN_EJECUTIVO_2606S77393.pptx"
    builder = ExecutiveReportBuilder()
    metadata = builder.generate(sample_incident_data, output_path)

    assert output_path.exists()
    assert metadata.size_bytes > 0
    assert metadata.slide_count >= 3

    # Inspeccionar la presentación generada
    prs = pptx.Presentation(str(output_path))
    assert len(prs.slides) >= 3

    # Diapositiva 1: Verificar título y textos clave
    slide1 = prs.slides[0]
    slide1_text = " ".join([p.text for shape in slide1.shapes if shape.has_text_frame for p in shape.text_frame.paragraphs])
    assert "2606S77393" in slide1_text
    assert "09/06/2026 14:45:00" in slide1_text
    assert "3h 25m" in slide1_text

    # Diapositivas 2 y 3: Verificar que la cronología está poblada
    slide2 = prs.slides[1]
    slide2_tables = [shape.table for shape in slide2.shapes if shape.has_table]
    assert len(slide2_tables) >= 1
    table = slide2_tables[0]
    assert len(table.rows) > 1
    assert table.rows[0].cells[0].text.strip() == "Hora"
    assert table.rows[0].cells[1].text.strip() == "Evento"


def test_builder_handles_large_timeline(sample_incident_data, tmp_path):
    # Generar más de 40 eventos para verificar paginación
    sample_incident_data.timeline_events = [
        ExecutiveTimelineEvent(time=f"1{i:02d}:00", event=f"Evento hito número {i}")
        for i in range(45)
    ]
    output_path = tmp_path / "RESUMEN_EXTENSO.pptx"
    builder = ExecutiveReportBuilder()
    metadata = builder.generate(sample_incident_data, output_path)

    assert output_path.exists()
    prs = pptx.Presentation(str(output_path))
    # Debe haber al menos 3 diapositivas (incluso 4 por paginación dinámica)
    assert len(prs.slides) >= 3
