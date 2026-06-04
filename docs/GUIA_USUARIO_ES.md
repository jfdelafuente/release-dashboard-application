# Guía de Usuario: Carga de Archivos CSV y Uso de Dashboards

**Versión**: 1.0
**Fecha**: 2 de junio de 2026
**Idioma**: Español

## Tabla de Contenidos

1. [Introducción](#introducción)
2. [Requisitos Previos](#requisitos-previos)
3. [Acceso al Sistema](#acceso-al-sistema)
4. [Subir un Archivo CSV](#subir-un-archivo-csv)
5. [Ver Datos en los Dashboards](#ver-datos-en-los-dashboards)
6. [Entender el Estado de los Datos](#entender-el-estado-de-los-datos)
7. [Controles de Auto-Actualización](#controles-de-auto-actualización)
8. [Solución de Problemas](#solución-de-problemas)

---

## Introducción

El sistema Release Dashboard permite cargar archivos CSV de incidencias y verlos automáticamente en dashboards interactivos. El sistema:

✅ **Valida** automáticamente el formato de tu archivo
✅ **Convierte** los datos a formato JSON
✅ **Actualiza** los dashboards automáticamente
✅ **Sincroniza** datos entre múltiples dashboards abiertos

Esta guía te enseña cómo usar estas características.

---

## Requisitos Previos

### Navegador Compatible

El sistema funciona en navegadores modernos:
- ✅ Google Chrome (versión 90+)
- ✅ Mozilla Firefox (versión 88+)
- ✅ Apple Safari (versión 14+)
- ✅ Microsoft Edge (versión 90+)

### Formato del Archivo CSV

Tu archivo CSV debe contener las siguientes columnas (requeridas):

| Columna | Descripción | Ejemplo |
|---------|-------------|---------|
| **ID de incidencia** | Identificador único | INC000003884945 |
| **Descripción** | Resumen del problema | LIVEPERSON // ERROR |
| **Estatus** | Estado de la incidencia | Abierto, Cerrado |
| **Fecha de envío** | Cuándo se reportó | 02/06/2026 8:40 AM |
| **Grupo asignado** | Equipo responsable | SOP_TEAM |
| **Urgencia** | Nivel de urgencia | Alta, Media, Baja |
| **Impacto** | Alcance del impacto | Masiva, Normal |

**Ejemplo de archivo válido**:
```csv
ID de incidencia,Descripción,Estatus,Fecha de envío,Grupo asignado,Urgencia,Impacto
INC000003884945,LIVEPERSON ERROR,Abierto,02/06/2026 8:40 AM,SOP_TEAM,Alta,Masiva
INC000003884946,API TIMEOUT,Cerrado,01/06/2026 10:00 AM,OPS_TEAM,Media,Normal
```

---

## Acceso al Sistema

### Paso 1: Abre el Portal Principal

1. Abre tu navegador web
2. Ve a la dirección: `http://localhost:5000` (o la URL de tu institución)
3. Verás la página de inicio con dos dashboards disponibles

### Paso 2: Selecciona un Dashboard

Hay dos dashboards disponibles:

**📊 Dashboard de Incidencias Masivas**
- Muestra incidencias reportadas recientemente
- Incluye gráficos de tendencias (últimos 7, 15, 30 días)
- Muestra backlog (incidencias pendientes)
- Filtra por estado, sistema, urgencia

**📋 Dashboard de Post-Mortem**
- Análisis de incidentes completados
- Desglose por despliegues (PAP, MESA)
- KPIs de resolución
- Histórico de incidentes cerrados

---

## Subir un Archivo CSV

### Paso 1: Abre el Modal de Carga

En cualquier dashboard, haz clic en el botón **"📤 Subir CSV"** en la parte superior.

Se abrirá una ventana emergente (modal) con opciones para subir un archivo.

### Paso 2: Selecciona tu Archivo

**Opción A - Seleccionar con el botón**:
1. Haz clic en **"Seleccionar Archivo CSV"**
2. Elige tu archivo `.csv` de tu computadora
3. Haz clic en **"Abrir"**

**Opción B - Arrastrar y Soltar (Drag & Drop)**:
1. Arrastra tu archivo `.csv` desde tu computadora
2. Suéltalo sobre el área punteada del modal
3. El archivo se cargará automáticamente

### Paso 3: Revisa la Vista Previa

Después de seleccionar el archivo, verás:

```
📄 Nombre del archivo: datos-incidencias.csv
📊 Codificación detectada: UTF-8
🔀 Delimitador: Coma (,)
📈 Número de filas: 150
✅ Validación: PASADA
```

**Si la validación falla**, verás un mensaje de error en rojo:
- "Falta columna requerida: Urgencia"
- "Encoding no soportado: Windows-1252"
- "No hay filas de datos en el archivo"

**Solución**: Ve a [Solución de Problemas](#solución-de-problemas).

### Paso 4: Confirma la Carga

1. Revisa los detalles de la vista previa
2. Haz clic en **"✅ Confirmar y Convertir"**
3. Verás "Procesando..." mientras se carga el archivo

### Paso 5: Espera la Confirmación

Después de unos segundos, verás:
- ✅ "¡Archivo cargado correctamente!"
- Dashboard actualizado con nuevos datos

El modal se cerrará automáticamente.

---

## Ver Datos en los Dashboards

### Dashboard de Incidencias Masivas

#### 1. **Filtro de Tiempo Global** (Arriba a la izquierda)

Selecciona el período que quieres analizar:
- **Todo** - Todos los datos disponibles
- **Últimos 7 días** - Incidencias de la semana pasada
- **Últimos 30 días** - Incidencias del mes pasado
- **Año en curso** - Desde el 1 de enero hasta hoy
- **Personalizado** - Elige tus propias fechas (si está disponible)

Todos los gráficos y KPIs se actualizan automáticamente.

#### 2. **KPI Cards** (Debajo del filtro)

Muestran métricas clave:

| KPI | Significado |
|-----|------------|
| **Total Incidencias** | Cuántas incidencias hay en el período |
| **Incidencias Pendientes** | Cuántas aún no están cerradas |
| **Tendencia 7 días** | Cambio % respecto a hace 7 días (🟢 bajó, 🔴 subió) |
| **Tendencia 15 días** | Cambio % respecto a hace 15 días |
| **Tendencia 30 días** | Cambio % respecto a hace 30 días |

**Ejemplo**: Si ves "Tendencia 7 días: -12% 🟢" significa que hoy hay 12% menos incidencias que hace una semana (mejora).

#### 3. **Gráficos Temporales**

**Gráfico 1: "Evolución Diaria de Incidencias Operativas"**
- Barras naranjas: Incidencias abiertas cada día
- Línea oscura: Backlog (total de pendientes acumulado)
- Ayuda a ver tendencias a lo largo del tiempo

**Gráfico 2: "Incidencias Abiertas por Día y Backlog"**
- Colores por estado (Abierto, Pendiente, En Progreso)
- Línea roja: Backlog total
- Muestra cómo cambia el estado de las incidencias

#### 4. **Tabla de Incidencias**

Muestra los detalles de cada incidencia:

| Columna | Contenido |
|---------|-----------|
| **Código** | ID de incidencia (clickeable → abre en Remedy) |
| **Descripción** | Resumen del problema |
| **Estado** | Abierto/Cerrado/Resuelto (con color) |
| **Urgencia** | Alta/Media/Baja |
| **Grupo Asignado** | Equipo responsable |
| **Impacto** | Masiva/Normal/Mínima |
| **Fecha Envío** | Cuándo se reportó |

**Filtros de Tabla** (Arriba de la tabla):
- Filtra la tabla por Estado, Sistema o Urgencia
- Los filtros se aplican después del filtro de tiempo global

#### 5. **Tabla de Debug** (Opcional)

Haz clic en "📊 Ver Tabla de Cálculos" para ver:
- Cálculos diarios internos
- Entradas y solucionadas por día
- Backlog acumulado

---

## Entender el Estado de los Datos

### Indicador de Frescura (Freshness Indicator)

En la parte superior de cada dashboard, verás un indicador que dice:

```
Ahora mismo        ← Verde (datos recién actualizados)
Hace 5m            ← Amarillo (datos recientes)
Hace 45m           ← Rojo (datos antiguos)
```

**¿Qué significa?**
- 🟢 **Ahora mismo / Hace < 5 min**: Datos frescos y actuales
- 🟡 **Hace 5-30 min**: Datos recientes pero no muy nuevos
- 🔴 **Hace > 30 min**: Considera actualizar manualmente

### Auto-Actualización Automática

Los dashboards se actualizan automáticamente cada 10 segundos si hay nuevos datos disponibles.

**¿Necesitas actualizar antes?** Usa el botón:

```
🔄 Actualizar (Junto al indicador de frescura)
```

Haz clic para refrescar los datos inmediatamente.

---

## Controles de Auto-Actualización

### Botón de Actualización Manual

**Icono**: 🔄 **Actualizar**

- Fuerza una actualización inmediata
- Útil si crees que hay datos nuevos que no se han cargado
- Se deshabilita mientras está actualizando
- Muestra "Actualizando..." durante la carga

### Toggle de Auto-Actualización

**Icono**: 🔘 **Auto-actualizar: [ ON / OFF ]**

- **Activado (ON)**: El dashboard verifica nuevos datos cada 10 segundos
- **Desactivado (OFF)**: Solo se actualiza si haces clic en "Actualizar" manualmente

**¿Cuándo desactivar?**
- Si prefieres actualizar manualmente
- Si tienes una conexión lenta y quieres ahorrar ancho de banda
- Si estás analizando datos históricos y no quieres que cambien

Tu preferencia se guarda automáticamente.

### Sincronización Entre Pestañas

Si tienes el mismo dashboard abierto en varias pestañas del navegador:
- Cuando un tab se actualiza, todos los otros tabs también se actualizan automáticamente
- No necesitas hacer nada - sucede en background
- Los datos se mantienen sincronizados

---

## Solución de Problemas

### ❌ Error: "Falta columna requerida"

**Problema**: Tu archivo CSV no tiene una columna obligatoria.

**Solución**:
1. Abre tu archivo en Excel o un editor de texto
2. Verifica que tenga TODAS estas columnas:
   - ID de incidencia
   - Descripción
   - Estatus
   - Fecha de envío
   - Grupo asignado
   - Urgencia
   - Impacto
3. Si falta una, añádela (puedes dejar algunas celdas en blanco si es necesario)
4. Guarda el archivo y vuelve a intentar

### ❌ Error: "Encoding no soportado"

**Problema**: Tu archivo está guardado en un formato que el sistema no reconoce.

**Solución**:
1. Abre tu archivo en Excel
2. **Archivo > Guardar Como**
3. En "Guardar como tipo", elige: **CSV UTF-8 (delimitado por comas)**
4. Haz clic en "Guardar"
5. Vuelve a intentar subir

### ❌ Error: "No hay filas de datos"

**Problema**: El archivo tiene encabezados pero no filas de datos.

**Solución**:
1. Verifica que el archivo tenga datos debajo de la fila de encabezados
2. Asegúrate de que no haya filas vacías al principio
3. El archivo debe tener al menos una fila de datos

### ⏳ "La actualización está tardando"

**Problema**: El dashboard no se actualiza rápidamente.

**Solución**:
1. Espera 10 segundos (intervalo de polling automático)
2. Haz clic en el botón "🔄 Actualizar" para forzar inmediatamente
3. Verifica tu conexión de internet
4. Si el problema persiste, actualiza la página (F5)

### 📡 "No se pudo verificar datos del servidor"

**Problema**: El dashboard no puede conectar con el servidor para verificar actualizaciones.

**Solución**:
1. Verifica que tienes conexión a internet
2. Espera unos segundos - reintentará automáticamente
3. Si persiste, recarga la página (F5)
4. Contacta al administrador si el problema continúa

### 💾 Los datos no aparecen después de subir

**Problema**: Subiste un archivo pero no ves los datos en el dashboard.

**Solución**:
1. Espera 2-3 minutos para que se complete la conversión
2. Haz clic en "🔄 Actualizar" para cargar los datos manualmente
3. Verifica que el archivo validó correctamente (debería decir "✅ Validación: PASADA")
4. Comprueba que no hay errores en la sección de validación

### 🔄 Múltiples pestañas muestran datos diferentes

**Problema**: El dashboard en una pestaña muestra diferentes datos que en otra.

**Solución**:
1. Verifica que ambas pestañas estén mostrando el mismo dashboard
2. Si Auto-actualización está desactivada, haz clic "🔄 Actualizar" en ambas
3. Espera 10 segundos para que la sincronización automática funcione
4. Si uno de los dashboards sigue desactualizado, recárgalo (F5)

---

## Contacto y Soporte

Si tienes problemas que no se resuelven con esta guía:

📧 **Email de Soporte**: ops-support@example.com
📞 **Teléfono**: +34 XXX XXX XXX
🐛 **Reportar Bug**: Contacta al equipo de desarrollo con detalles de qué sucedió

**Información útil para el soporte**:
- Navegador y versión que usas
- Mensaje de error exacto
- Pasos que realizaste antes del error
- Nombre del archivo CSV que intentaste subir

---

## Consejos y Trucos

### 📌 Trabajar con Múltiples Dashboards

Abre ambos dashboards en pestañas diferentes para comparar:
1. Dashboard de Masivas en Pestaña 1
2. Dashboard de Post-Mortem en Pestaña 2

Los datos se sincronizarán automáticamente entre pestañas cuando uno se actualice.

### 🔍 Filtrar Datos Efectivamente

1. Usa primero el **filtro de tiempo global** para el período que te interesa
2. Luego usa los **filtros de tabla** (Estado, Sistema, Urgencia) para afinar
3. Los dos filtros funcionan juntos para mostrarte exactamente lo que necesitas

### 📊 Analizar Tendencias

- Compara los **KPIs de tendencia** (7d, 15d, 30d) para ver si mejora o empeora
- Usa los **gráficos temporales** para ver patrones en el tiempo
- La **línea de backlog** te muestra si se está acumulando trabajo

### ⚡ Rendimiento

- Si tienes muchas incidencias (>10,000), considera usar filtros para reducir los datos
- Desactiva auto-actualización si solo necesitas un análisis de una vez
- Espera a que terminen las gráficas de cargar antes de hacer zoom

---

## Glosario

| Término | Significado |
|---------|------------|
| **CSV** | Formato de archivo de texto con datos en columnas |
| **Dashboard** | Pantalla con gráficos y datos visuales |
| **Backlog** | Incidencias pendientes de resolver |
| **KPI** | Indicador clave de desempeño |
| **Estatus** | Estado actual (Abierto, Cerrado, etc.) |
| **Encoding** | Formato de caracteres del archivo |
| **Auto-actualizar** | Recargar datos automáticamente |
| **Freshness** | Qué tan recientes son los datos |

---

**¡Gracias por usar Release Dashboard!**

Para más información, contacta al equipo de operaciones.
