# Quickstart: Sistema de Notificaciones de Incidencias de Alta Prioridad

**Feature**: `012-high-priority-incident-notifications` | **Date**: 2026-10-26

Esta guía rápida describe cómo ejecutar, probar y verificar el Sistema de Notificaciones de Alta Prioridad tanto en entorno local de desarrollo como en producción.

---

## 1. Requisitos Previos

- Python 3.10+ con entorno virtual activo.
- Dependencias de testing: `pytest`, `requests`, `jsonschema` (opcional para validación formal).
- Acceso a la red interna corporativa o al proxy local (`serve_app.py`) para consultar Epsilon Resumen IA.

---

## 2. Ejecución del Escáner y Evaluador CLI

El script CLI principal se ubica en [`converters/cli/evaluate_incident_notifications.py`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/converters/cli/evaluate_incident_notifications.py).

### 2.1. Escaneo Estándar (Generación de Catálogo)
Procesa la última lista de incidencias masivas registradas en `data/output/index.json`, consulta Epsilon (con caché local de 15 min) y genera `data/output/high_priority_notifications.json`:

```powershell
python converters/cli/evaluate_incident_notifications.py
```

### 2.2. Opciones y Parámetros del CLI
```powershell
# Limitar a los primeros 10 tickets (útil para pruebas rápidas)
python converters/cli/evaluate_incident_notifications.py --limit 10

# Especificar un fichero masivo concreto de entrada
python converters/cli/evaluate_incident_notifications.py --input "data/output/CS-Informe incidencias P1,  P2 y P3 - 2026 - 14 Oct 2026-massive.json"

# Especificar fichero de salida alternativo
python converters/cli/evaluate_incident_notifications.py --output "data/output/test_notifications.json"

# Modo Dry-Run (evalúa e imprime resumen sin sobrescribir archivos)
python converters/cli/evaluate_incident_notifications.py --dry-run

# Forzar refresco ignorando caché previa de Epsilon
python converters/cli/evaluate_incident_notifications.py --force
```

---

## 3. Pruebas Automatizadas con Pytest

Ejecuta el conjunto completo de pruebas unitarias y de contrato:

```powershell
# Ejecución de pruebas del evaluador y generador de mensajes
pytest converters/tests/unit/test_evaluate_incident_notifications.py -v

# Ejecución conjunta con todas las pruebas del proyecto
pytest converters/tests/unit/ -v
```

Casos cubiertos en los tests:
- Inferencia ITIL (Matriz de Severidad: Impacto $\times$ Urgencia $\rightarrow$ P1..P4).
- Detección de discrepancias de prioridad (P3 en ticket pero P2/P1 por IA).
- Formato y límites estrictos de palabras para mensajes ejecutivos ($\le$ 90 palabras completo, $\le$ 30 palabras breve).
- Tolerancia a fallos: degradación elegante si Epsilon está offline o no devuelve resumen.
- Validación del esquema JSON del archivo de salida.

---

## 4. Verificación en el Dashboard Frontend

1. **Iniciar el servidor local con proxy de Epsilon**:
   ```powershell
   python serve_app.py --port 8081
   ```
2. **Abrir en el navegador**:
   - `http://localhost:8081/dashboards/massive-incidents/`
3. **Comportamiento esperado en la interfaz**:
   - **Campana de Notificaciones**: En el header superior derecho, icono de campana con badge rojo que indica el conteo de incidencias P1 y P2 activas.
   - **Drawer Lateral (Centro de Notificaciones)**: Al pulsar la campana, se despliega un panel lateral con:
     - Métricas KPI (P1 Críticas, P2 Altas, Discrepancias detectadas).
     - Tarjetas de incidencias ordenadas por criticidad y discrepancia.
     - Botón "Ver Mensaje Ejecutivo" que despliega las pestañas *Apertura*, *Seguimiento* y *Cierre* con botón de copiado al portapapeles en 1 clic.
     - Selector de estado (*Pendiente*, *Comunicada*, *En seguimiento*, *Descartada*) persistido en `localStorage`.
   - **Enlace directo a Resumen IA**: Botón para abrir el modal nativo `resumen-ia.js` con el informe completo de Epsilon.

---

## 5. Despliegue en Producción

El proceso de despliegue a producción actualiza automáticamente el frontend y backend:

```powershell
.\scripts\deploy-production.ps1
```

En producción, el pipeline o el cron puede invocar periódicamente el CLI para mantener actualizado `data/output/high_priority_notifications.json`.

