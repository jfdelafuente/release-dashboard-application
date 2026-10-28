# Quickstart: Frontal Web de Monitorización para Incident Manager (013-incident-manager-monitor)

**Feature**: `013-incident-manager-monitor` | **Date**: 2026-10-28  
**Spec Reference**: [`specs/013-incident-manager-monitor/spec.md`](./spec.md)

Esta guía describe cómo levantar, probar y verificar el Frontal Web de Monitorización del Incident Manager tanto en entorno local como en producción.

---

## 1. Requisitos Previos

- Python 3.10+ configurado en el entorno.
- Repositorio clonado y dependencias instaladas.
- Navegador web moderno (Chrome, Edge, Firefox).

---

## 2. Puesta en Marcha en Entorno Local

1. **Arrancar el servidor de aplicaciones local**:
   ```powershell
   python serve_app.py
   ```
   *El servidor quedará a la escucha en `http://localhost:8080` (o el puerto configurado en `PORT`).*

2. **Acceder a la Consola de Monitorización del Incident Manager**:
   - Abrir en el navegador:
     ```
     http://localhost:8080/dashboards/incident-manager-monitor/
     ```
   - **Nota de Aislamiento**: Verificar que la URL carga directamente y que **no existe enlace** desde `http://localhost:8080/dashboards/portal/`.

---

## 3. Flujo Operativo del Incident Manager

### Paso 1: Detección y Revisión de Incidencias Pendientes
1. Al acceder, observar la barra de KPIs:
   - Si el contador **Pendientes de Redacción** es mayor a 0, la cabecera destacará con resalte visual.
2. Cada tarjeta pendiente muestra:
   - ID Remedy con enlace directo.
   - Severidad sugerida (P1 rojo / P2 ámbar) y badge de discrepancia.
   - Proceso Crítico de Negocio (ej. *Atención al Cliente*) y Criterio ITIL aplicado.
   - Sistemas afectados.

### Paso 2: Obtención del Prompt y Redacción con Agente LLM
1. En la ficha del ticket pendiente, seleccionar la fase requerida (`Apertura`, `Seguimiento` o `Cierre`).
2. Pulsar el botón **"Copiar Prompt para el Agente"**.
3. Pegar el prompt en el chat del agente corporativo (`incident-reporter`).

### Paso 3: Validación e Ingesta del Mensaje Oficial
1. Copiar la salida generada por el agente.
2. En el frontal, pegar la versión completa en el campo de texto y la versión breve en el campo correspondiente.
3. Observar los contadores dinámicos:
   - Verde: $\le$ 90 palabras para versión completa (monopárrafo); $\le$ 30 palabras para versión breve.
   - Rojo: Supera el límite de palabras permitido.
4. **Guardado**:
   - Opción Web: Pulsar **"Guardar en Almacén Oficial"**. La herramienta persistirá en `data/agent_executive_messages.json` y actualizará automáticamente la cola.
   - Opción CLI (alternativa): Pulsar **"Copiar Comando CLI"** y ejecutar en terminal:
     ```powershell
     python converters/cli/update_agent_message.py --id INC000004168775 --phase apertura --completo "..." --breve "..."
     ```

---

## 4. Pruebas Automatizadas y de Aislamiento

Ejecutar la suite de tests para comprobar la lógica de filtrado, contratos API y regla de aislamiento del portal:

```powershell
# Ejecución de tests unitarios del evaluador y del almacén de agente
python -m pytest converters/tests/unit/test_evaluate_incident_notifications.py converters/tests/unit/test_update_agent_message.py -v

# Validación estática de aislamiento (comprobar que portal/index.html no tiene enlaces al monitor)
python -c "
from pathlib import Path
portal_html = Path('dashboards/portal/index.html').read_text(encoding='utf-8')
index_html = Path('dashboards/index.html').read_text(encoding='utf-8')
assert 'incident-manager-monitor' not in portal_html, 'ERROR: incident-manager-monitor detectado en dashboards/portal/index.html'
assert 'incident-manager-monitor' not in index_html, 'ERROR: incident-manager-monitor detectado en dashboards/index.html'
print('✅ Aislamiento verificado con éxito: No hay enlaces en portales generales.')
"
```

---

## 5. Verificación de Casos de Borde

1. **Estado sin incidencias pendientes**:
   - Cuando todas las incidencias de alta prioridad tienen redacciones aprobadas, la cola muestra el estado limpio: *"✅ Todas las incidencias activas disponen de mensajes ejecutivos oficiales"*.
2. **Conmutación de Vistas**:
   - Cambiar a la pestaña **"Todas las Activas"** para revisar tickets ya completados con sus mensajes oficiales guardados.
3. **Filtros Dinámicos**:
   - Probar el filtrado por severidad (`Solo P1`, `Solo P2`), `Solo Discrepancias`, o búsqueda por ID de ticket.

