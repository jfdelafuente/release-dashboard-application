"""
Interfaz abstracta para adaptadores de salida / renderizado (Puertos de Salida).
"""

from abc import ABC, abstractmethod
from incident_report.domain.models import IncidentReport


class BaseRenderer(ABC):
    """
    Puerto de salida base para renderizadores (Markdown, PowerPoint, etc.).
    """

    @abstractmethod
    def render(self, report: IncidentReport, output_path: str) -> str:
        """Renderiza el informe en la ruta especificada y devuelve la ruta final."""
        raise NotImplementedError

