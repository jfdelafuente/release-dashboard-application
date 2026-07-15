# Quickstart: probar Dashboards por Release

## Preparación

```bash
python serve_app.py
```

## 1. Ver una release con datos ya cargados

1. Abre `http://localhost:8000/dashboards/release-kpis/`.
2. Localiza cualquier fila de la tabla y haz clic en el nombre de la release (columna "RELEASE").
3. Verifica que se abre `http://localhost:8000/dashboards/postmortem/?release=<nombre>` y que:
   - La cabecera muestra el nombre de esa release, no un título genérico.
   - KPIs, gráfica temporal, distribución por sistema/estado y tabla muestran solo incidencias de esa release.

## 2. Ver una release sin datos todavía

1. Desde `dashboards/release-kpis/`, haz clic en el nombre de una release que sepas que no tiene CSV de postmortem subido.
2. Verifica que se muestra la pantalla de subida de CSV, con el nombre de la release ya asociado (no hay que volver a escribirlo).
3. Sube un CSV de postmortem de prueba y confirma que, al terminar la conversión, el dashboard pasa a mostrar los datos de esa release.
4. Vuelve a `dashboards/release-kpis/` y haz clic de nuevo en esa misma release: debe llevar ahora a los datos recién cargados, no a la pantalla de subida.

## 3. Aislamiento entre releases

1. Con datos cargados para al menos dos releases distintas, abre el dashboard de la primera y anota un par de IDs de incidencia visibles en la tabla.
2. Abre el dashboard de la segunda release y confirma que ninguno de esos IDs aparece.

## 4. Acceso sin parámetro de release

1. Visita directamente `http://localhost:8000/dashboards/postmortem/` (sin `?release=`).
2. Verifica que no se muestra ningún dato combinado de todas las releases, sino un mensaje indicando que hay que acceder desde `dashboards/release-kpis/`, con un enlace directo a esa página.

## 5. Verificación del backend (conversores)

```bash
python converters/cli/convert_postmortems.py data/input/tu-archivo.csv --release-name "2026R4-PRUEBA"
python -c "
import json
d = json.load(open('data/output/tu-archivo-postmortem.json'))
assert d['_metadata']['release_name'] == '2026R4-PRUEBA'
print('OK: release_name presente en _metadata')
"
```

Después, confirma que `data/output/index.json` incluye `release_name: "2026R4-PRUEBA"` en la entrada correspondiente de `postmortem.files`.

## 6. Regresión: JSON de postmortem generados antes de esta feature

1. Confirma que un JSON de postmortem ya existente (sin `release_name` en su `_metadata`) no rompe `build_index_for_hub` ni la carga del índice — debe aparecer en `index.json` con `release_name: null` (o ausente), sin errores en consola del navegador ni en la conversión.
