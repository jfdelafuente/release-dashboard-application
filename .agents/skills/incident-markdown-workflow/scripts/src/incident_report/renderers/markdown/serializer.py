"""
Serializador de IncidentReport a documento Markdown estructurado (Etapa 1).
"""

from incident_report.domain.models import IncidentReport


def dump_to_markdown(report: IncidentReport) -> str:
    """
    Serializa un objeto IncidentReport en un documento Markdown limpio y editable por humanos.
    """
    lines = []
    lines.append("# Informe Ejecutivo de Incidencia\n")
    lines.append("## Metadatos")
    lines.append(f"- **ID Incidencia / TT**: {report.incident_id or '—'}")
    lines.append(f"- **Título**: {report.title or '—'}")
    lines.append(f"- **Inicio**: {report.start_time or '—'}")
    lines.append(f"- **Fin**: {report.end_time or '—'}")
    lines.append(f"- **Duración**: {report.duration or '—'}\n")

    lines.append("## Impacto")
    lines.append(f"{report.impact.strip() if report.impact else '—'}\n")

    lines.append("## Impacto de Negocio")
    lines.append(f"{report.business_impact.strip() if report.business_impact else '—'}\n")

    lines.append("## Causa Raíz")
    lines.append(f"{report.cause.strip() if report.cause else '—'}\n")

    lines.append("## Solución")
    lines.append(f"{report.solution.strip() if report.solution else '—'}\n")

    lines.append("## Puntos de Acción")
    lines.append("| Pain Point | Descripción | Responsable | Fecha Prevista |")
    lines.append("|---|---|---|---|")
    if report.action_points:
        for ap in report.action_points:
            p_point = (ap.pain_point or "—").replace("|", "/")
            desc = (ap.description or "—").replace("|", "/")
            owner = (ap.owner or "—").replace("|", "/")
            forecast = (ap.forecast or "—").replace("|", "/")
            lines.append(f"| {p_point} | {desc} | {owner} | {forecast} |")
    else:
        lines.append("| — | — | — | — |")
    lines.append("")

    lines.append("## Cronología")
    lines.append("| Hora | Evento |")
    lines.append("|---|---|")
    if report.chronology:
        for ev in report.chronology:
            t = (ev.time or "—").replace("|", "/")
            e = (ev.event or "—").replace("|", "/")
            lines.append(f"| {t} | {e} |")
    else:
        lines.append("| — | — |")
    lines.append("")

    return "\n".join(lines)

