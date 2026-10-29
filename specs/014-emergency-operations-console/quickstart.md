# Quickstart: Consola Operativa de Emergencias Orange en Tiempo Real (014-emergency-operations-console)

**Feature**: `014-emergency-operations-console`  
**Date**: 2026-10-29  

---

## 1. Requisitos Previos

Asegúrate de contar con Python 3.10+ y de tener el entorno de desarrollo activo.

```bash
# Comprobar versión de Python
python --version
```

---

## 2. Iniciar el Servidor de Desarrollo

Inicia el servidor local de desarrollo `serve_app.py`:

```bash
python serve_app.py
```

El servidor estará escuchando en `http://localhost:8080/`.

---

## 3. Acceder a la Consola de Emergencias

Abre en tu navegador la URL dedicada y aislada:

```text
http://localhost:8080/dashboards/incident-manager-monitor/
```

> **Recordatorio de Seguridad**: Este frontal no dispone de enlaces en el portal general público (`/dashboards/portal/index.html`) para preservar el aislamiento operativo.

---

## 4. Verificación de Funcionalidades Clave

### 4.1 Cronómetros y Alertas de Escalado a 45 min
* Observa el reloj en tiempo real de cada incidencia.
* Si han transcurrido más de 45 minutos desde la apertura, la tarjeta exhibirá la alerta:
  `🚨 1er Escalado Telefónico Requerido (Proveedores / Resolutores N2/N3)`.
* Si han transcurrido más de 105 minutos (+1h adicional), la alerta ascenderá a:
  `🚨 2º Escalado Requerido a Estamentos Superiores (Vía Telefónica obligatoria)`.

### 4.2 Métricas Exactas de Discrepancia
* Localiza incidencias con badge `⚠️ Discrepancia Crítica`.
* Comprueba la tabla de triaje:
  - *Remedy*: Media / Baja
  - *Orange ITIL*: SL1 / P1 (o SL2 / P2)
  - *Proceso Crítico y Umbral*: Cifra cuantitativa exacta (ej. Facturación: >3h sin tarificación online).

### 4.3 Bloqueo de Desescalada por Workaround
* Inspecciona tickets con mitigación técnica activa.
* Verifica la presencia del candado institucional:
  `🔒 Desescalada Bloqueada: Workaround temporal no reduce severidad sin erradicación total`.

### 4.4 Reporte de Emergencia en 4 Bloques
* Haz clic en **"Reporte de Emergencia"** en cualquier tarjeta.
* Comprueba la visualización de los 4 bloques estandarizados.
* Pulsa **"Copiar Reporte"** y verifica que el texto copiado al portapapeles respeta la estructura de `orange-it-emergency-management`.

---

## 5. Ejecución de Pruebas Automatizadas

Ejecuta la suite de pruebas unitarias y de integración:

```bash
python -m pytest converters/tests/unit/test_incident_manager_monitor.py -v
```

