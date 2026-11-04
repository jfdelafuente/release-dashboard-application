"""
Utilidades comunes de limpieza DOM, macros de Confluence y detección de valores triviales.
"""

import copy
import re


def is_checklist_table(table) -> bool:
    """
    Detecta tablas puras de QA/Checklist de Confluence (ej. CHECK | RESULTADO Indicar OK/KO,
    o 'CR Type | Definition | Select').
    Estas tablas evalúan cumplimiento de proceso o clasificación y no contienen narrativa técnica.
    """
    headers_text = " ".join(th.get_text(" ", strip=True).lower() for th in table.find_all("th"))
    if (
        "ok/ko" in headers_text
        or "indicar ok" in headers_text
        or ("cr type" in headers_text and "select" in headers_text)
    ):
        return True
    first_tr = table.find("tr")
    if first_tr:
        first_text = " ".join(td.get_text(" ", strip=True).lower() for td in first_tr.find_all(["th", "td"]))
        if "check" in first_text and ("ok" in first_text or "resultado" in first_text):
            return True
        if "cr type" in first_text and "select" in first_text:
            return True
    return False


def is_trivial_value(val: str) -> bool:
    """
    Comprueba si una cadena es un marcador trivial como 'OK', 'KO', 'X', '—', o texto de ayuda de plantilla.
    """
    if not val:
        return True
    v = val.strip().lower()
    if len(v) <= 1:
        return True
    if v in [
        "ok",
        "ko",
        "si",
        "sí",
        "no",
        "n/a",
        "na",
        "—",
        "-",
        "x",
        "[x]",
        "(*)",
        "none",
        "null",
        "check",
        "indicar ok/ko",
    ]:
        return True
    if any(
        v.startswith(prefix)
        for prefix in [
            "marcar con",
            "indicar",
            "seleccionar",
            "describir",
            "concretar y detallar",
            "en caso de",
            "rellenar",
        ]
    ):
        return True
    return False


def _resolve_confluence_inline_nodes(container) -> None:
    """
    Resuelve in-place macros estructuradas de Jira y etiquetas <time> dentro de una copia DOM.
    """
    for m in container.find_all(["ac:structured-macro", "structured-macro"]):
        macro_name = m.get("ac:name") or m.get("name")
        if macro_name == "jira":
            key_tag = (
                m.find(["ac:parameter", "parameter"], attrs={"ac:name": "key"})
                or m.find(["ac:parameter", "parameter"], attrs={"name": "key"})
            )
            k_val = key_tag.get_text(strip=True) if key_tag else ""
            m.replace_with(f" ({k_val})" if k_val else "")
        else:
            m.decompose()

    for t in container.find_all("time"):
        dt = t.get("datetime", "")
        if dt:
            parts = dt.split("-")
            if len(parts) == 3:
                t.replace_with(f"{parts[2]}/{parts[1]}/{parts[0]}")
            else:
                t.replace_with(dt)
        else:
            t.decompose()


def clean_cell_content(cell) -> str:
    """
    Extrae texto limpio en una sola línea de una celda o bloque DOM:
    - Resuelve macros estructuradas de Jira en claves como '(PROB-17772)'.
    - Resuelve etiquetas <time datetime="YYYY-MM-DD"> al formato DD/MM/YYYY.
    - Elimina parámetros internos de macros y espacios redundantes.
    """
    c = copy.copy(cell)
    _resolve_confluence_inline_nodes(c)
    txt = c.get_text(" ", strip=True)
    return re.sub(r"\s+", " ", txt).strip()


def clean_block_text(elem) -> str:
    """
    Extrae texto limpio de un bloque o celda preservando los saltos de párrafo (<p>, <br>, <li>, <div>),
    pero manteniendo en línea las etiquetas inline (<code>, <strong>, <span>, <a>) y resolviendo
    macros de Jira ('(PROB-XXXXX)') y etiquetas <time>.
    """
    c = copy.copy(elem)
    _resolve_confluence_inline_nodes(c)

    for br in c.find_all(["br", "hr"]):
        br.replace_with("\n")

    for block in c.find_all(["p", "li", "div", "h1", "h2", "h3", "h4", "h5", "h6", "tr"]):
        block.append("\n")

    raw = c.get_text(" ", strip=False)
    lines = []
    for line in raw.split("\n"):
        cleaned_line = re.sub(r"\s+", " ", line).strip()
        if cleaned_line:
            lines.append(cleaned_line)
    return "\n".join(lines).strip()


def collect_sibling_text(heading_tag) -> str:
    """
    Recopila el texto de los elementos hermanos posteriores a un encabezado hasta el siguiente encabezado.
    Omite tablas estructuradas (que se procesan mediante el parser de tablas).
    """
    paragraphs = []
    for sibling in heading_tag.find_next_siblings():
        if sibling.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            if not sibling.get_text(strip=True):
                continue
            break
        if sibling.name == "table":
            continue
        text = clean_block_text(sibling)
        if text:
            paragraphs.append(text)
    return "\n".join(paragraphs).strip()
