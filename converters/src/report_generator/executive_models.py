"""
Modelos de datos para el informe ejecutivo de incidencias postmortem.
Feature 010: 010-incident-executive-report
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


def sanitize_incident_ref(ref: str) -> str:
    """Normaliza y sanitiza el código o identificador de incidencia."""
    if not ref:
        return "INCIDENCIA"
    cleaned = re.sub(r'[^a-zA-Z0-9_\-]', '', str(ref).strip())
    return cleaned if cleaned else "INCIDENCIA"


@dataclass
class ExecutiveActionPoint:
    """Representa una fila en la tabla de Puntos de Acción Relevantes de la diapositiva 1."""
    pain_point: str = ""
    description: str = ""
    owner: str = ""
    forecast: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ExecutiveActionPoint:
        if not isinstance(data, dict):
            return cls()
        return cls(
            pain_point=str(data.get("painPoint") or data.get("pain_point") or data.get("tipo") or "Otros").strip(),
            description=str(data.get("description") or data.get("descripcion") or data.get("accion") or "").strip(),
            owner=str(data.get("owner") or data.get("responsable") or "—").strip(),
            forecast=str(data.get("forecast") or data.get("fecha") or data.get("estado") or "—").strip(),
        )

    def to_dict(self) -> Dict[str, str]:
        return {
            "painPoint": self.pain_point,
            "description": self.description,
            "owner": self.owner,
            "forecast": self.forecast,
        }


@dataclass
class ExecutiveTimelineEvent:
    """Representa un hito o evento en la tabla cronológica de las diapositivas 2 y 3."""
    time: str = ""
    event: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ExecutiveTimelineEvent:
        if not isinstance(data, dict):
            return cls()
        return cls(
            time=str(data.get("time") or data.get("hora") or "").strip(),
            event=str(data.get("event") or data.get("evento") or data.get("descripcion") or "").strip(),
        )

    def to_dict(self) -> Dict[str, str]:
        return {
            "time": self.time,
            "event": self.event,
        }


@dataclass
class ExecutiveIncidentData:
    """Datos completos extraídos para elaborar el informe ejecutivo en PowerPoint."""
    incident_ref: str
    title: str = "Incidencia"
    start_time: str = ""
    duration: str = ""
    impact_text: str = ""
    cause_text: str = ""
    solution_text: str = ""
    action_points: List[ExecutiveActionPoint] = field(default_factory=list)
    timeline_events: List[ExecutiveTimelineEvent] = field(default_factory=list)
    source_url: str = ""

    def __post_init__(self):
        self.incident_ref = sanitize_incident_ref(self.incident_ref)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ExecutiveIncidentData:
        if not isinstance(data, dict):
            return cls(incident_ref="DESCONOCIDO")

        ref = str(data.get("incidentRef") or data.get("incident_ref") or data.get("id") or "INCIDENCIA").strip()
        title = str(data.get("title") or data.get("titulo") or "Incidencia").strip()
        start_time = str(data.get("startTime") or data.get("start_time") or data.get("inicio") or "").strip()
        duration = str(data.get("duration") or data.get("duracion") or "").strip()
        impact = str(data.get("impactText") or data.get("impact_text") or data.get("impacto") or "").strip()
        cause = str(data.get("causeText") or data.get("cause_text") or data.get("causa") or "").strip()
        solution = str(data.get("solutionText") or data.get("solution_text") or data.get("solucion") or "").strip()
        source_url = str(data.get("sourceUrl") or data.get("source_url") or data.get("confluenceUrl") or "").strip()

        raw_actions = data.get("actionPoints") or data.get("action_points") or data.get("puntos_accion") or []
        action_points = [ExecutiveActionPoint.from_dict(item) for item in raw_actions if isinstance(item, dict)]

        raw_timeline = data.get("timelineEvents") or data.get("timeline_events") or data.get("cronologia") or []
        timeline_events = [ExecutiveTimelineEvent.from_dict(item) for item in raw_timeline if isinstance(item, dict)]

        return cls(
            incident_ref=ref,
            title=title,
            start_time=start_time,
            duration=duration,
            impact_text=impact,
            cause_text=cause,
            solution_text=solution,
            action_points=action_points,
            timeline_events=timeline_events,
            source_url=source_url,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "incidentRef": self.incident_ref,
            "title": self.title,
            "startTime": self.start_time,
            "duration": self.duration,
            "impactText": self.impact_text,
            "causeText": self.cause_text,
            "solutionText": self.solution_text,
            "sourceUrl": self.source_url,
            "actionPoints": [ap.to_dict() for ap in self.action_points],
            "timelineEvents": [te.to_dict() for te in self.timeline_events],
        }


@dataclass
class ReportMetadata:
    """Metadatos de persistencia del informe en disco."""
    incident_ref: str
    filename: str
    file_path: str
    generated_at: str
    size_bytes: int
    slide_count: int = 3

    def to_dict(self) -> Dict[str, Any]:
        return {
            "incidentRef": self.incident_ref,
            "filename": self.filename,
            "filePath": self.file_path,
            "generatedAt": self.generated_at,
            "sizeBytes": self.size_bytes,
            "slideCount": self.slide_count,
        }

