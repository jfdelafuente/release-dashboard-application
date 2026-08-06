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
fichero. Abrirlo y comprobar (3 diapositivas en total):
- Portada con el nombre de la release.
- Diapositiva "Métricas Globales": 3 tarjetas de KPI (Total Incidencias, % Resueltas PaP,
  % Resueltas Mesa) junto a la gráfica "Incidencias por Release". % Resueltas PaP y % Resueltas
  Mesa deben verse en verde si son ≥75% o en rojo si están por debajo, con "Objetivo: 75%" visible
  en la propia tarjeta. Los 3 valores deben coincidir con la fila de "2026R7" en
  `dashboards/release-kpis/` (columnas Incid., % PaP, % 1ª sem.) en ese mismo momento.
- Diapositiva final con las gráficas "KPI % PaP" y "KPI % 1ª semana" lado a lado, con todas las
  releases (no solo "2026R7").

Todos los KPIs y gráficas del informe se calculan a partir de `releases-data.js` — el JSON de
postmortem de la release ya no interviene en la generación (ver FR-002/003/004 en spec.md,
rediseñados).

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
