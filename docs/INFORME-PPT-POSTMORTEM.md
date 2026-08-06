# Informe PPT de Postmortem por Release — Guía de Usuario

Cómo generar el informe `.pptx` de una release, tanto desde el navegador
como a mano desde la línea de comandos.

## Qué es este informe

Un `.pptx` de 3 diapositivas con el estilo visual MASORANGE:

1. **Portada** — nombre de la release.
2. **Métricas Globales** — 3 tarjetas de KPI (Total Incidencias, % Resueltas
   PaP, % Resueltas Mesa) junto a la gráfica "Incidencias por Release".
3. **Comparativa de KPIs por Release** — las gráficas "KPI % PaP" y
   "KPI % 1ª semana", una junto a la otra.

Todos los KPIs y gráficas se calculan a partir de
`dashboards/release-kpis/releases-data.js` — es la misma fuente de datos
que ves en el dashboard de KPIs de Release (`dashboards/release-kpis/`), así
que los números del informe siempre coinciden con lo que muestra ese
dashboard en ese momento. Las 3 gráficas muestran siempre las **últimas 9
releases**, no el histórico completo.

### Cómo leer las tarjetas de KPI

- **% Resueltas PaP** y **% Resueltas Mesa** se muestran en **verde** si
  alcanzan el objetivo (75%) o en **rojo** si quedan por debajo. El
  objetivo aparece siempre en la propia tarjeta ("Objetivo: 75%").
- Debajo del objetivo se indica el detalle de la cuenta, p. ej. "54 de 70
  incidencias PaP resueltas el día del PaP" o "84 de 107 incidencias Mesa".

## Cómo generarlo (forma habitual)

No hace falta ninguna acción manual en el uso normal: hay un botón de
descarga en dos sitios:

- **Dashboard de KPIs de Release** (`dashboards/release-kpis/`): icono ⬇
  junto al nombre de cada release, en la tabla.
- **Dashboard de Postmortem de una release** (`dashboards/postmortem/?release=...`):
  botón "Descargar informe PPT".

Ambos descargan el mismo fichero (llaman al mismo endpoint,
`GET /api/reports/postmortem/{release}`), y requieren que `serve_app.py`
(local) o el backend de producción estén corriendo.

## Cómo generarlo a mano (línea de comandos)

Útil cuando no tienes el dashboard a mano, quieres generar varios informes
de golpe, o el botón del navegador ha fallado y quieres ver el error
completo.

### Requisitos previos

```bash
cd release-dashboard-application
pip install -r converters/requirements.txt   # instala python-pptx, plotly y kaleido si faltan
```

Los comandos siguientes se ejecutan **desde la raíz del repositorio**
(`release-dashboard-application/`), porque el script busca
`dashboards/release-kpis/releases-data.js` con una ruta relativa.

### Generar el informe de una release

```bash
python converters/cli/generate_postmortem_report.py 2026R7
```

Salida esperada: la ruta del `.pptx` generado, por ejemplo

```
C:\Users\...\release-dashboard-application\data\reports\2026R7-postmortem-report.pptx
```

Puedes elegir la ruta de salida con `-o`:

```bash
python converters/cli/generate_postmortem_report.py 2026R7 -o C:\ruta\que\quieras\informe.pptx
```

### Generar el informe de todas las releases

```bash
python converters/cli/generate_postmortem_report.py --all
```

Genera un `.pptx` por cada release presente en `releases-data.js`, en
`data/reports/`, y termina imprimiendo un resumen:

```
Generados: 51 (2021R1, 2021R3, ..., 2026R7)
```

Si alguna release falla, no detiene el resto — al final lista cuáles
fallaron y por qué. Puedes usar `--output-dir` para generarlos todos en
otra carpeta:

```bash
python converters/cli/generate_postmortem_report.py --all --output-dir C:\ruta\que\quieras
```

> ⚠️ Con muchas releases (actualmente hay más de 50), `--all` puede tardar
> varios minutos, porque cada informe renderiza sus propias 3 gráficas.
> Para probar rápido, genera solo la release que te interese.

### ¿No se regenera aunque he subido datos nuevos?

El informe se guarda en caché: si ya existe un `.pptx` para esa release y
es más reciente que `releases-data.js`, se te devuelve el mismo fichero sin
volver a renderizar nada (tarda ~1-2 segundos en vez de ~20). Si necesitas
forzar la regeneración sin haber cambiado los datos, borra el fichero y
vuelve a generarlo:

```bash
del data\reports\2026R7-postmortem-report.pptx
python converters/cli/generate_postmortem_report.py 2026R7
```

## Solución de problemas

### "No hay datos de KPIs de Release para la release 'X'"
La release no aparece en `dashboards/release-kpis/releases-data.js`.
Comprueba el nombre exacto (mayúsculas/minúsculas incluidas) en la tabla
del dashboard de KPIs de Release.

### "No se pudieron cargar los datos de KPIs de Release: ..."
No se ha podido leer o interpretar `releases-data.js` (fichero no
encontrado, o formato inesperado). Verifica que el fichero existe en
`dashboards/release-kpis/releases-data.js` y que no está corrupto.

### "el fichero anterior (...) está abierto en otro programa"
El `.pptx` generado anteriormente para esa release está abierto en
PowerPoint (u otro programa). Cierra el programa y vuelve a intentarlo.

### "ModuleNotFoundError: No module named 'pptx'" (o `plotly` / `kaleido`)
Faltan las dependencias del generador de informes:

```bash
pip install -r converters/requirements.txt
```

## Documentación relacionada

- [Especificación de la feature](../specs/008-postmortem-ppt-report/spec.md)
- [Quickstart técnico (validación end-to-end)](../specs/008-postmortem-ppt-report/quickstart.md)
- [CLAUDE.md](../CLAUDE.md) — sección "Informe PPT de Postmortem por Release"

---

**Última actualización**: 2026-08-06
