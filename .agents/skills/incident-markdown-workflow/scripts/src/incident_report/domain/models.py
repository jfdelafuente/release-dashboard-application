"""
Modelos de datos del dominio de Informes Ejecutivos de Incidencias.
"""

from dataclasses import dataclass, field
from typing import List
from incident_report.domain.validators import validate_incident_report


@dataclass
class ActionPoint:
    pain_point: str = "—"
    description: str = "—"
    owner: str = "—"
    forecast: str = "—"

    def to_list(self) -> List[str]:
        return [
            self.pain_point or "—",
            self.description or "—",
            self.owner or "—",
            self.forecast or "—",
        ]


@dataclass
class ChronologyEvent:
    time: str = ""
    event: str = ""

    def to_list(self) -> List[str]:
        return [self.time or "", self.event or ""]


@dataclass
class IncidentReport:
    incident_id: str = ""
    title: str = ""
    start_time: str = ""
    end_time: str = ""
    duration: str = ""
    impact: str = ""
    business_impact: str = "—"
    cause: str = ""
    solution: str = "—"
    action_points: List[ActionPoint] = field(default_factory=list)
    chronology: List[ChronologyEvent] = field(default_factory=list)

    def validate(self) -> List[str]:
        """
        Valida los campos críticos requeridos.
        Devuelve una lista de errores o lista vacía si el informe es válido.
        """
        return validate_incident_report(self)

    def get_formatted_title(self) -> str:
        """
        Devuelve el título formateado con el estilo corporativo:
        RESUMEN EJECUTIVO INCIDENCIA- TT <ID> - <Título>
        """
        id_part = self.incident_id.strip() if self.incident_id else ""
        if id_part and not id_part.upper().startswith("TT"):
            id_part = f"TT {id_part}"

        title_part = self.title.strip() if self.title else "Incidencia en Servicio"

        if id_part:
            return f"RESUMEN EJECUTIVO INCIDENCIA- {id_part} - {title_part}"
        return f"RESUMEN EJECUTIVO INCIDENCIA - {title_part}"

    def get_subtitle_time(self) -> str:
        """
        Devuelve el subtítulo de tiempos:
        Inicio: <start_time>  Duración: <duration>
        """
        start = self.start_time.strip() if self.start_time else "No disponible"
        dur = self.duration.strip() if self.duration else "No disponible"
        return f"Inicio: {start}  Duración: {dur}"

