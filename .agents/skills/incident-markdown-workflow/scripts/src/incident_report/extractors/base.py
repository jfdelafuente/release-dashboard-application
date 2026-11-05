"""
Interfaz abstracta para extractores de informes de incidencias (Puertos de Entrada).
"""

from abc import ABC, abstractmethod
from incident_report.domain.models import IncidentReport


class BaseExtractor(ABC):
    """
    Puerto de entrada base para cualquier adaptador de extracción (HTML, Confluence, etc.).
    """

    @abstractmethod
    def extract(self, raw_content: str) -> IncidentReport:
        """Extrae un IncidentReport estructurado a partir del contenido bruto."""
        raise NotImplementedError

