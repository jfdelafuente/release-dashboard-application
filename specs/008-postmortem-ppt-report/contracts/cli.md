# Contrato: CLI `generate_postmortem_report.py`

```
python converters/cli/generate_postmortem_report.py <release_name> [-o OUTPUT_PATH]
python converters/cli/generate_postmortem_report.py --all [--output-dir DIR]
```

## Modo individual

- `release_name` (posicional, requerido): nombre exacto de la release.
- `-o, --output` (opcional): ruta de salida del `.pptx`. Por defecto:
  `data/reports/<release_name_saneado>-postmortem-report.pptx`.

**Salida (stdout)**: ruta del fichero generado, o mensaje de error si la release no tiene datos
(exit code 1 en ese caso, igual que el resto de scripts en `converters/cli/`).

## Modo `--all` (User Story 3)

- Recorre todas las releases con `-postmortem.json` en `data/output/` (mismo criterio de
  agrupación por `release_name` que `cleanup_output.py`) y genera el informe de cada una.
- `--output-dir` (opcional): directorio de salida. Por defecto `data/reports/`.
- No se detiene ante el fallo de una release: continúa con las demás y al final imprime un
  resumen (generadas / fallidas), exit code 1 si al menos una falló, igual que el patrón ya usado
  en `convert_postmortems.py` con `total_success`.

## Uso como librería

```python
from converters.cli.generate_postmortem_report import generate_report

result = generate_report(release_name="2026R7", output_path=None)
# result: {"success": True, "path": "data/reports/2026R7-postmortem-report.pptx"}
# o: {"success": False, "error": "No hay datos de postmortem cargados para la release '2026R7'"}
```

Misma forma de resultado (`{"success": bool, ...}`) que ya usa `converters/cli/upload_csv.py`,
para que el backend (local o el del repo hermano) pueda invocarlo de forma consistente.
