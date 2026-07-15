# Contrato: URL del dashboard de postmortem por release

## Formato

```
/dashboards/postmortem/?release=<nombre-de-release-url-encoded>
```

- `release` es el mismo valor que aparece literalmente en la columna "RELEASE" de la tabla de `dashboards/release-kpis/` (primer elemento de cada entrada de `RAW_RELEASES` en `releases-data.js`), codificado con `encodeURIComponent`.
- Ejemplo: release `"2026R6-MESA"` → `/dashboards/postmortem/?release=2026R6-MESA`.

## Origen del enlace

`dashboards/release-kpis/app.js`, función `renderTable()`: cada fila de la tabla enlaza incondicionalmente a esta URL para su release, exista o no ya un archivo de postmortem asociado.

## Comportamiento de `dashboards/postmortem/index.html` según el parámetro `release`

| Caso | Condición | Comportamiento |
|---|---|---|
| Sin parámetro | `?release` ausente o vacío | No se intenta cargar ningún dato. Se muestra un mensaje "Accede a una release desde el dashboard de KPIs de Release" con enlace a `/dashboards/release-kpis/`. No hay ya un dashboard combinado de "todas las releases". |
| Con parámetro, release con datos | `index.json.postmortem.files` contiene una entrada con `release_name` igual al parámetro | Se carga esa entrada (no la más reciente por defecto) y se renderiza igual que hoy: KPIs, gráfica temporal, distribución, tabla. La cabecera muestra el nombre de la release en vez del título genérico. |
| Con parámetro, release sin datos | Ninguna entrada de `index.json.postmortem.files` tiene ese `release_name` | Se muestra la pantalla de subida de CSV ya existente (`upload-screen`), con el nombre de release tomado del parámetro (de solo lectura, no editable) preasociado a la subida. |

## Compatibilidad

Los tres estados se resuelven enteramente en el cliente (JavaScript), sin nuevas rutas de servidor ni cambios en `nginx.conf` — `/dashboards/postmortem/` sigue siendo el mismo `index.html` estático de siempre; el parámetro de query string no requiere configuración adicional en nginx (`alias` + `try_files` ya sirve el archivo tal cual, ignorando la query string, tal como ocurre en cualquier servidor estático).
