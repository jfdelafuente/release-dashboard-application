"""
Pruebas unitarias para el parser de contenidos de Confluence (ConfluenceParser).
Feature 010: 010-incident-executive-report
"""

import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from converters.src.report_generator.confluence_parser import ConfluenceParser


SAMPLE_HTML = """
<html>
<body>
<h1>Postmortem Incidencia - 2606S77393 - Caída del servicio IVR exMM</h1>
<p><strong>Inicio:</strong> 09/06/2026 14:45:00</p>
<p><strong>Duración:</strong> 3h 25m</p>

<h2>Impacto</h2>
<p>Degradación progresiva en la atención de llamadas entrantes afectando a 12.000 clientes.</p>

<h2>Causa</h2>
<p>Límite de prefijos BGP saturado en el enlace contra AWS.</p>

<h2>Solución</h2>
<p>Ampliación del cupo de prefijos de 15K a 30K y verificación de tráfico restablecido.</p>

<h2>Puntos de Acción Relevantes</h2>
<table>
  <thead>
    <tr><th>Pain Point</th><th>Descripción</th><th>Owner</th><th>Forecast</th></tr>
  </thead>
  <tbody>
    <tr><td>Solución</td><td>Ampliación prefix-BGP para servicio AWS</td><td>TMC Acceso_Fijo</td><td>Cerrado</td></tr>
    <tr><td>Detección</td><td>Implementar alarmas WARNING-limit</td><td>TMC Acceso_Fijo</td><td>W26</td></tr>
  </tbody>
</table>

<h2>Cronología</h2>
<table>
  <thead>
    <tr><th>Hora</th><th>Evento</th></tr>
  </thead>
  <tbody>
    <tr><td>15:16</td><td>Recepción de ticket de avería OPIT.</td></tr>
    <tr><td>16:00</td><td>Apertura de SL1 y bridge técnico.</td></tr>
    <tr><td>18:06</td><td>Ampliación de prefijos BGP aplicada.</td></tr>
    <tr><td>18:14</td><td>Confirmación de servicio recuperado.</td></tr>
  </tbody>
</table>
</body>
</html>
"""

SAMPLE_TEXT = """
INCIDENCIA: 2606S77393 - Caída del servicio IVR exMM
Inicio: 09/06/2026 14:45:00
Duración: 3h 25m

IMPACTO:
Degradación progresiva en la atención de llamadas entrantes.

CAUSA:
Límite de prefijos BGP saturado.

SOLUCION:
Ampliación del cupo de prefijos de 15K a 30K.

CRONOLOGÍA:
15:16 Se recibe aviso de corte.
16:00 Bridge técnico abierto.
18:06 Ampliación ejecutada.
"""


def test_parse_confluence_html():
    parser = ConfluenceParser()
    data = parser.parse(SAMPLE_HTML, fallback_ref="2606S77393")

    assert data.incident_ref == "2606S77393"
    assert "IVR" in data.title
    assert "09/06/2026" in data.start_time
    assert "3h 25m" in data.duration
    assert "Degradación" in data.impact_text
    assert "BGP" in data.cause_text
    assert "15K" in data.solution_text

    # Validar acciones
    assert len(data.action_points) == 2
    assert data.action_points[0].pain_point == "Solución"
    assert data.action_points[0].owner == "TMC Acceso_Fijo"

    # Validar cronología
    assert len(data.timeline_events) == 4
    assert data.timeline_events[0].time == "15:16"
    assert "OPIT" in data.timeline_events[0].event


def test_parse_plain_text():
    parser = ConfluenceParser()
    data = parser.parse(SAMPLE_TEXT, fallback_ref="2606S77393")

    assert data.incident_ref == "2606S77393"
    assert "09/06/2026" in data.start_time
    assert "Degradación" in data.impact_text
    assert "BGP" in data.cause_text
    assert len(data.timeline_events) == 3
    assert data.timeline_events[0].time == "15:16"


def test_fallback_graceful_on_empty():
    parser = ConfluenceParser()
    data = parser.parse("", fallback_ref="INC123456")

    assert data.incident_ref == "INC123456"
    assert data.title != ""
    assert data.action_points == []
    assert data.timeline_events == []
