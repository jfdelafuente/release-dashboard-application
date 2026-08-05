# Quickstart: Informe PPT de Postmortem por Release

## Requisitos previos

- Datos de postmortem ya cargados para al menos una release (`data/output/*-postmortem.json` con
  `_metadata.release_name` informado).
- Dependencias nuevas instaladas: `pip install -r converters/requirements.txt` (incluye
  `python-pptx`, `plotly`, `kaleido` tras esta feature).

## Generar el informe de una release (CLI)

```bash
cd release-dashboard-application
python converters/cli/generate_postmortem_report.py 2026R7
```

Salida esperada: `data/reports/2026R7-postmortem-report.pptx` creado, y por consola la ruta del
fichero. Abrirlo y comprobar:
- Portada con el nombre de la release.
- Tarjetas con los 8 KPIs, coincidiendo con lo que muestra `dashboards/postmortem/index.html?release=2026R7`
  en ese mismo momento.
- Las 4 gráficas propias del dashboard de postmortem para esa release.
- Las 3 gráficas generales del dashboard de KPIs de Release (con todas las releases, no solo
  "2026R7").

## Generar los informes de todas las releases

```bash
python converters/cli/generate_postmortem_report.py --all
```

Comprobar que se genera un `.pptx` por cada release con datos, y que el resumen final indica
cuántos se generaron y cuántos fallaron (si alguno).

## Generar el informe desde el dashboard (una vez implementado el botón)

1. Abrir `dashboards/release-kpis/` (o el dashboard de postmortem de una release concreta).
2. Pulsar el botón/acción de "Descargar informe PPT".
3. Confirmar que el navegador descarga un `.pptx` cuyo contenido coincide con el generado por CLI
   para esa misma release.

## Caso de error a probar

```bash
python converters/cli/generate_postmortem_report.py RELEASE-QUE-NO-EXISTE
```

Debe fallar con un mensaje claro ("No hay datos de postmortem cargados para la release...") y
exit code distinto de 0, sin crear ningún `.pptx` vacío o con ceros.
