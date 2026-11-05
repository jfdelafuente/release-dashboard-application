"""
Servicio opcional de asistencia con LLM (Gemini / OpenAI) para refinamiento de postmortems desestructurados.
"""

import json
import re
import sys
from incident_report.config import Settings
from incident_report.domain.models import ActionPoint, ChronologyEvent, IncidentReport


def refine_report_with_llm(html_content: str, report: IncidentReport) -> None:
    """
    Si hay una API Key configurada en el entorno, consulta al LLM para completar
    o refinar secciones ausentes en el informe de incidencia.
    """
    settings = Settings.from_env()
    if not settings.has_llm_key:
        sys.stderr.write(
            "[Aviso] Flag --use-llm activado pero no se detectó API Key en el entorno "
            "(GEMINI_API_KEY / OPENAI_API_KEY). Continuando con extracción directa.\n"
        )
        return

    try:
        if settings.gemini_api_key:
            _refine_with_gemini(html_content, report, settings.gemini_api_key)
        elif settings.openai_api_key:
            _refine_with_openai(html_content, report, settings.openai_api_key)
    except Exception as e:
        sys.stderr.write(
            f"[Aviso] No se pudo completar la extracción con LLM ({e}). "
            "Se conservan los datos extraídos por parsing.\n"
        )


def _refine_with_gemini(html_content: str, report: IncidentReport, key: str) -> None:
    import requests

    prompt = (
        "Analiza el siguiente postmortem de incidencia y devuelve un objeto JSON con las claves: "
        "'incident_id', 'title', 'start_time', 'end_time', 'duration', 'impact', 'cause', 'solution', "
        "'action_points' (lista de objetos con pain_point, description, owner, forecast), "
        "'chronology' (lista de objetos con time, event). Responde únicamente con JSON válido.\n\n"
        f"Contenido:\n{html_content[:15000]}"
    )
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
    resp = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=15)
    if resp.status_code == 200:
        data = resp.json()
        raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
        _apply_json_to_report(raw_text, report)


def _refine_with_openai(html_content: str, report: IncidentReport, key: str) -> None:
    import requests

    prompt = (
        "Analiza el siguiente postmortem de incidencia y devuelve un objeto JSON con las claves: "
        "'incident_id', 'title', 'start_time', 'end_time', 'duration', 'impact', 'cause', 'solution', "
        "'action_points' (lista de objetos con pain_point, description, owner, forecast), "
        "'chronology' (lista de objetos con time, event). Responde únicamente con JSON válido.\n\n"
        f"Contenido:\n{html_content[:15000]}"
    )
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
    }
    resp = requests.post(
        "https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=15
    )
    if resp.status_code == 200:
        data = resp.json()
        raw_text = data["choices"][0]["message"]["content"]
        _apply_json_to_report(raw_text, report)


def _apply_json_to_report(raw_text: str, report: IncidentReport) -> None:
    match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if not match:
        return
    parsed = json.loads(match.group(0))
    if not report.incident_id and parsed.get("incident_id"):
        report.incident_id = parsed["incident_id"]
    if (not report.title or report.title == "—") and parsed.get("title"):
        report.title = parsed["title"]
    if not report.start_time and parsed.get("start_time"):
        report.start_time = parsed["start_time"]
    if not report.end_time and parsed.get("end_time"):
        report.end_time = parsed["end_time"]
    if not report.duration and parsed.get("duration"):
        report.duration = parsed["duration"]
    if not report.impact and parsed.get("impact"):
        report.impact = parsed["impact"]
    if not report.cause and parsed.get("cause"):
        report.cause = parsed["cause"]
    if (not report.solution or report.solution == "—") and parsed.get("solution"):
        report.solution = parsed["solution"]

    if not report.action_points and parsed.get("action_points"):
        report.action_points = [
            ActionPoint(
                pain_point=ap.get("pain_point", "—"),
                description=ap.get("description", "—"),
                owner=ap.get("owner", "—"),
                forecast=ap.get("forecast", "—"),
            )
            for ap in parsed["action_points"]
        ]
    if not report.chronology and parsed.get("chronology"):
        report.chronology = [
            ChronologyEvent(
                time=ch.get("time", ""),
                event=ch.get("event", ""),
            )
            for ch in parsed["chronology"]
        ]

