# Guía de Resolución de Problemas (Troubleshooting)

Diagnóstico, causas raíz y soluciones paso a paso para incidencias comunes durante el desarrollo local, ejecución de conversores, visualización de dashboards y despliegue en producción (VPS).

---

## 📑 Índice de Contenidos

1. [Servidor Local y Carga de CSVs](#1-servidor-local-y-carga-de-csvs)
2. [Conversores CLI (Python)](#2-conversores-cli-python)
3. [Dashboards Frontend](#3-dashboards-frontend)
4. [Informes Ejecutivos PowerPoint](#4-informes-ejecutivos-powerpoint)
5. [Proxy de Resumen IA (Epsilon)](#5-proxy-de-resumen-ia-epsilon)
6. [Suite de Tests Automatizados](#6-suite-de-tests-automatizados)
7. [Producción y Despliegue en VPS (10.132.26.96)](#7-producción-y-despliegue-en-vps-101322696)
8. [Control de Versiones y Git](#8-control-de-versiones-y-git)

---

## 1. Servidor Local y Carga de CSVs

### Error: "Failed to fetch" al subir un archivo CSV

- **Síntoma**: Al arrastrar un archivo o hacer clic en "Seleccionar archivo" en los dashboards, el navegador muestra una alerta `Error: Failed to fetch`.
- **Causa**: Se está sirviendo el frontend mediante un servidor estático genérico (`python -m http.server`, Live Server de VSCode o apertura directa `file:///...`). Estos servidores solo admiten peticiones de lectura `GET` y carecen del endpoint `POST /api/upload`.
- **Solución**:
  1. Detén el servidor en ejecución (`Ctrl + C`).
  2. Desde la raíz del repositorio, inicia el servidor oficial de la aplicación:
     ```bash
     python serve_app.py
     ```
  3. Abre en tu navegador la URL:
     ```text
     http://localhost:8080/dashboards/portal/
     ```

### Error: "Address already in use" o puerto 8080 ocupado

- **Síntoma**: Al ejecutar `python serve_app.py`, se produce un error `OSError: [WinError 10048] Solo se permite un uso de cada dirección de socket`.
- **Causa**: Existe otra instancia del servidor abierta en segundo plano o el puerto 8080 está reservado por otra aplicación.
- **Solución**:
  - **Opción A: Cambiar de puerto temporalmente**:
    ```bash
    python serve_app.py --port 8090
    ```
  - **Opción B: Liberar el puerto 8080 en Windows**:
    ```powershell
    # Localizar el identificador del proceso (PID)
    netstat -ano | findstr :8080
    # Finalizar el proceso por su PID
    Stop-Process -Id <PID> -Force
    ```

### Mensaje: "Falló la conversión a JSON" tras subir un CSV

- **Síntoma**: El modal de subida responde con `"success": false` y muestra un desglose de error en el campo `details`.
- **Causa**: El archivo CSV no cumple con el esquema requerido (cabeceras incorrectas, delimitador incompatible, valores no permitidos en campos clave o codificación corrupta).
- **Solución**:
  1. Lee el mensaje detallado en pantalla o revisa el informe generado en `data/errors/<nombre-archivo>_errors.json`.
  2. Verifica que las columnas obligatorias existan conforme a la especificación en [converters/docs/API.md](../04-conversores/README.md).
  3. Asegúrate de que los campos normalizados contengan valores válidos (p. ej. *Urgencia*: `Baja`, `Media`, `Alta`, `Crítica`).

---

## 2. Conversores CLI (Python)

### Error: "ModuleNotFoundError: No module named 'src'" o 'csv_to_json'

- **Síntoma**: Al ejecutar un conversor desde la terminal, Python no localiza los submódulos de conversión.
- **Causa**: El comando se ejecuta desde un directorio no reconocido sin configurar la variable `PYTHONPATH`.
- **Solución**:
  - Ejecuta siempre invocando el script desde la raíz del proyecto:
    ```bash
    python converters/cli/convert_incidents.py data/input/mi-archivo.csv
    ```
  - O bien utiliza los wrappers ejecutables provistos en `converters/scripts/bin/`:
    ```bash
    # En Windows
    converters\scripts\bin\convert_incidents.bat data/input/mi-archivo.csv
    # En Linux / macOS
    ./converters/scripts/bin/convert_incidents.sh data/input/mi-archivo.csv
    ```

### Error de Codificación: "UnicodeDecodeError"

- **Síntoma**: `UnicodeDecodeError: 'utf-8' codec can't decode byte 0x... in position ...`.
- **Causa**: El archivo CSV fue exportado con codificación Windows-1252 o ISO-8859-1 (Latin-1) y contiene caracteres especiales que confunden la autodetección.
- **Solución**:
  1. Abre el archivo CSV en VSCode o Notepad++.
  2. Vuelve a guardarlo seleccionando codificación **UTF-8** (sin BOM).
  3. Ejecuta el conversor con la opción de depuración detallada (`-v`) para identificar la línea exacta:
     ```bash
     converters\scripts\bin\convert_incidents.bat data/input/archivo.csv -v
     ```

### Error de Delimitador: Columnas agrupadas en un único campo

- **Síntoma**: El JSON generado tiene una única clave enorme con todas las columnas unidas por punto y coma.
- **Causa**: El archivo tiene delimitadores mixtos o comillas sin cerrar en celdas multilínea que impiden al analizador heurístico deducir el separador adecuado.
- **Solución**:
  1. Inspecciona la primera fila (cabecera) del CSV.
  2. Asegúrate de que el delimitador sea consistente (punto y coma `;` o coma `,`).
  3. Comprueba que las cadenas de texto que contienen el delimitador estén correctamente entrecomilladas con comillas dobles (`"..."`).

---

## 3. Dashboards Frontend

### Pantalla en blanco o "Cannot GET /data/output/index.json"

- **Síntoma**: El dashboard carga la estructura visual pero no muestra tablas, gráficos ni selectores de datos.
- **Causa**:
  - Estás visualizando los ficheros abriéndolos con doble clic en el explorador (`file:///...`), lo cual bloquea las peticiones `fetch()` por política de seguridad del navegador (CORS).
  - O bien aún no se ha generado el archivo de catálogo `data/output/index.json`.
- **Solución**:
  1. Inicia `python serve_app.py`.
  2. Accede siempre a través del protocolo HTTP: `http://localhost:8080/dashboards/portal/`.
  3. Si la carpeta `data/output/` está vacía, convierte al menos un CSV para crear los JSON iniciales y el índice.

### Datos desactualizados tras una nueva conversión

- **Síntoma**: Tras procesar un nuevo CSV, el dashboard sigue mostrando métricas anteriores.
- **Causa**: La caché del navegador retiene una versión previa del catálogo `index.json`.
- **Solución**:
  - `serve_app.py` envía la cabecera `Cache-Control: no-cache` automáticamente.
  - En el navegador, realiza una recarga forzada pulsando `Ctrl + F5` (o `Cmd + Shift + R` en macOS).

---

## 4. Informes Ejecutivos PowerPoint

### Error: No se localiza el motor de reportes CSO

- **Síntoma**: Al solicitar un informe ejecutivo postmortem (`/api/v1/reports/executive-incident/...`), la respuesta es un error 500 o `ExecutiveReportBuilder no disponible`.
- **Causa**: En el entorno local, `serve_app.py` busca el motor de reportes en el repositorio hermano `cso-incident-masivas-report/backend`. Si la carpeta no está en la misma raíz, el módulo no se importa.
- **Solución**:
  - Define la variable de entorno `CSO_BACKEND_ROOT` indicando la ruta absoluta hacia el backend CSO:
    ```powershell
    $env:CSO_BACKEND_ROOT = "C:\ruta\hacia\cso-incident-masivas-report\backend"
    python serve_app.py
    ```

### Error de permisos al guardar el informe `.pptx`

- **Síntoma**: `PermissionError: [Errno 13] Permission denied: '.../informe.pptx'`.
- **Causa**: El archivo PowerPoint generado está actualmente abierto en Microsoft PowerPoint, lo que bloquea su sobrescritura en disco.
- **Solución**: Cierra Microsoft PowerPoint y vuelve a solicitar la generación del informe.

---

## 5. Proxy de Resumen IA (Epsilon)

### Error 502 Bad Gateway o Timeout al consultar el Resumen IA

- **Síntoma**: El modal flotante de Resumen IA en los dashboards muestra un mensaje de fallo de conexión o tiempo de espera agotado.
- **Causa**:
  - En local: Falta de conexión a la red corporativa de Orange para alcanzar `https://soptmc.si.orange.es/MonTMC/api/epsilon/`.
  - En producción: Problemas transitorios en el servicio remoto de Epsilon.
- **Solución**:
  1. Asegúrate de tener la VPN corporativa de Orange activa.
  2. En producción, Nginx cuenta con una directiva de caché de 15 minutos (`proxy_cache_use_stale`) que devuelve la última respuesta disponible si el servicio remoto se degrada.

---

## 6. Suite de Tests Automatizados

### Comando `pytest` no reconocido

- **Síntoma**: `pytest: command not found` o `'pytest' is not recognized`.
- **Causa**: El entorno virtual no está activo o no se han instalado las dependencias de desarrollo.
- **Solución**:
  ```bash
  # Activar entorno virtual
  .\venv\Scripts\Activate.ps1  # Windows
  # Instalar herramientas de desarrollo
  pip install -r requirements-dev.txt
  ```

### Fallo en cobertura de código (< 80%)

- **Síntoma**: `Coverage failure: total coverage of X% is less than fail-under=80%`.
- **Causa**: Se han introducido nuevas funciones en `converters/src/` sin añadir sus respectivos tests unitarios.
- **Solución**:
  1. Ejecuta pytest con desglose de líneas sin cubrir:
     ```bash
     cd converters
     pytest tests/ -v --cov=src --cov-report=term-missing
     ```
  2. Localiza los archivos y números de línea reportados en la columna `Missing`.
  3. Añade los casos de prueba necesarios en `converters/tests/unit/`.

---

## 7. Producción y Despliegue en VPS (10.132.26.96)

### Fallo de autenticación SSH / SCP en `deploy-production.ps1`

- **Síntoma**: `Permission denied (publickey)` o tiempo de espera agotado al conectar a `infocodes@10.132.26.96`.
- **Causa**:
  - La clave SSH privada no está cargada en el agente SSH de Windows (`ssh-agent`).
  - La máquina de desarrollo no tiene acceso de red a la IP del VPS (VPN desconectada).
- **Solución**:
  1. Verifica conectividad con el VPS:
     ```powershell
     Test-NetConnection -ComputerName 10.132.26.96 -Port 22
     ```
  2. Inicia el agente SSH y añade tu clave:
     ```powershell
     Get-Service ssh-agent | Set-Service -StartupType Automatic -PassThru | Start-Service
     ssh-add ~\.ssh\id_rsa
     ```

### Error de sintaxis en Nginx (`nginx -t` falla)

- **Síntoma**: Durante el despliegue, el script aborta con el mensaje `nginx: configuration file /infocodes/nginx/conf/nginx.conf test failed`.
- **Causa**: La configuración de Nginx contiene directivas inválidas o rutas inexistentes.
- **Solución**:
  - El script `deploy-production.ps1` aborta la recarga de forma automática para no interrumpir el servicio.
  - Conéctate al servidor y revisa el diagnóstico detallado:
    ```bash
    ssh infocodes@10.132.26.96
    /infocodes/nginx/sbin/nginx -t
    ```
  - Corrige el archivo `nginx.conf` en local, prueba la sintaxis y relanza el despliegue.

### Rutas de datos vacías en producción (`/data/` devuelve 404 o sin contenido)

- **Síntoma**: Nginx devuelve 404 para `/data/output/index.json` en producción.
- **Causa**: El symlink hacia el almacenamiento persistente desacoplado (`/infocodes/var/storage/release-dashboard`) está roto o no se creó correctamente en la release activa.
- **Solución**:
  1. Accede al VPS por SSH:
     ```bash
     ssh infocodes@10.132.26.96
     ```
  2. Comprueba el estado del symlink:
     ```bash
     ls -la /infocodes/project/release-dashboard-application/current/data
     ```
  3. Si apunta a una ruta incorrecta, restablécelo manualmente:
     ```bash
     ln -sfn /infocodes/var/storage/release-dashboard /infocodes/project/release-dashboard-application/current/data
     ```

### Procedimiento de Rollback Inmediato ante Emergencia

Si un despliegue produce una anomalía crítica en producción:
- **Desde tu terminal local (PowerShell)**:
  ```powershell
  .\scripts\deploy-production.ps1 -Rollback
  ```
- **Directamente en el VPS (SSH)**:
  ```bash
  ssh infocodes@10.132.26.96
  /infocodes/project/release-dashboard-application/scripts/rollback.sh
  ```

---

## 8. Control de Versiones y Git

### Archivos de datos o temporales rastreados por Git indebidamente

- **Síntoma**: Archivos de `data/output/` o `data/input/` aparecen como modificados en `git status`.
- **Causa**: Fueron añadidos al índice de Git antes de que `.gitignore` estuviera activo.
- **Solución**:
  1. Limpia el índice de Git manteniendo los archivos en disco:
     ```bash
     git rm -r --cached data/
     git status
     ```
  2. Confirma la exclusión:
     ```bash
     git commit -m "chore: eliminar tracking indebido de directorio data/"
     ```

---

## Documentación Relacionada

- [QUICKSTART.md](QUICKSTART.md) — Guía rápida de configuración en 5 minutos.
- [DEVELOPMENT.md](desarrollo.md) — Flujos de trabajo y directrices de desarrollo local.
- [DEPLOYMENT.md](../06-operaciones-y-gobernanza/despliegue-vps.md) — Manual integral de despliegue y topología del VPS.
- [PROJECT-STRUCTURE.md](../03-arquitectura-y-datos/estructura-proyecto.md) — Arquitectura y mapa exhaustivo de directorios.
- [LOGS.md](../06-operaciones-y-gobernanza/logs-y-auditoria.md) — Registro unificado de bitácora técnica e intervenciones.

---

**Última actualización**: 2026-10-20
