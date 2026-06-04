# Guía de Testing Manual - Release Dashboard
## Validación Funcional Paso a Paso

**Fecha**: 2 de junio de 2026
**Objetivo**: Verificar que todos los componentes funcionan correctamente

---

## Parte 1: Preparación del Entorno

### Paso 1.1: Verificar Directorios de Datos

```bash
# En la raíz del proyecto, verifica que existan estos directorios:
data/
├── input/           # Archivos CSV esperando conversión
├── output/          # Archivos JSON convertidos
├── errors/          # Reportes de errores
└── temp_uploads/    # Archivos temporales

# Crealos si no existen:
mkdir -p data/input data/output data/errors data/temp_uploads
```

**✓ Verificado**: Los directorios existen y están vacíos

### Paso 1.2: Verificar Archivos de Test

```bash
# Navega a la carpeta de test data
cd tests/test_data

# Deberías ver archivos como:
ls -la | grep -E "\.csv|\.json"

# Ejemplo de salida esperada:
# sample_incidents.csv
# sample_massive_incidents.csv
# dates_normalized.json
```

**✓ Verificado**: Existen archivos de prueba

---

## Parte 2: Testing del Upload (Carga de Archivos)

### Escenario 2.1: Upload Exitoso de CSV Válido

**Objetivo**: Cargar un archivo CSV válido y verificar validación automática

**Pasos**:
1. Abre el navegador: `http://localhost:5000`
2. Haz clic en **"📤 Subir CSV"** (arriba en cualquier dashboard)
3. Verás el modal de upload

**Opción A - Seleccionar archivo**:
```
1. Haz clic en "Seleccionar Archivo CSV"
2. Navega a: tests/test_data/
3. Selecciona: "sample_massive_incidents.csv"
4. Haz clic en "Abrir"
```

**Opción B - Arrastrar y soltar**:
```
1. Abre: tests/test_data/ en el Explorador
2. Arrastra "sample_massive_incidents.csv"
3. Suéltalo en el área punteada del modal
```

**Resultado Esperado** (después de 2-3 segundos):
```
✓ Vista Previa Mostrada:
  📄 sample_massive_incidents.csv
  📊 Codificación detectada: UTF-8
  🔀 Delimitador: Coma (,)
  📈 Número de filas: 150 (aproximadamente)
  ✅ Validación: PASADA

  [Botón] ✅ Confirmar y Convertir
  [Botón] ❌ Cancelar
```

**Acciones**:
1. Revisa que la vista previa sea correcta
2. Haz clic en **"✅ Confirmar y Convertir"**

**Resultado Final Esperado** (después de 3-5 segundos):
```
✓ Notificación Verde:
  "¡Archivo cargado correctamente!"

✓ Modal se cierra automáticamente

✓ Dashboard se actualiza con nuevos datos
```

---

### Escenario 2.2: Upload Rechazado (CSV Inválido)

**Objetivo**: Cargar un archivo inválido y verificar mensaje de error

**Crear archivo de prueba inválido**:
```csv
ID de incidencia,Descripción
INC000001,Test Incident
```
Guarda como: `invalid_test.csv`

**Pasos**:
1. Abre upload modal
2. Carga el archivo `invalid_test.csv`
3. Espera validación (2-3 segundos)

**Resultado Esperado**:
```
✗ Vista Previa con Error (fondo rojo):
  ❌ Validación: FALLÓ

  Error: "Falta columnas requeridas: ['Estatus', 'Fecha de envío', ...]"

  [Botón] ❌ Cancelar
  [Botón] 📥 Seleccionar otro archivo
```

**Acciones**:
1. Haz clic en **"Seleccionar otro archivo"** para intentar de nuevo
2. O **"Cancelar"** para cerrar el modal

**✓ Verificado**: Sistema rechaza archivos inválidos con mensajes claros

---

### Escenario 2.3: Validación de Encoding

**Objetivo**: Verificar que detecta correctamente el encoding

**Pasos**:
1. Upload un archivo UTF-8 (como `sample_massive_incidents.csv`)
2. Revisa la vista previa

**Resultado Esperado**:
```
Codificación detectada: UTF-8 ✓
```

---

## Parte 3: Testing del Dashboard

### Escenario 3.1: Visualizar Datos Cargados

**Objetivo**: Verificar que los datos aparecen en el dashboard

**Prerequisito**: Haber completado Escenario 2.1 (upload exitoso)

**Pasos**:
1. Espera 2-3 segundos después del upload
2. El dashboard debería mostrar automáticamente nuevos datos
3. Deberías ver:

**En los KPI Cards** (arriba del dashboard):
```
┌─────────────────────────────┐
│ Total Incidencias: 150      │
│ Incidencias Pendientes: 45  │
│ Tendencia 7 días: +5% 🔴    │
│ Tendencia 15 días: -2% 🟢   │
│ Tendencia 30 días: +8% 🔴   │
└─────────────────────────────┘
```

**En la Tabla**:
```
Código         | Descripción     | Estado   | Urgencia | Grupo Asignado
INC000001      | Test Incident   | Abierto  | Alta     | SOP_TEAM
INC000002      | Test Incident   | Cerrado  | Media    | OPS_TEAM
[... más registros ...]
```

**En los Gráficos**:
- Gráfico 1: Barras naranjas mostrando incidencias por día
- Gráfico 2: Línea mostrando backlog (pendientes acumulados)

**✓ Verificado**: Datos cargados y visualizados correctamente

---

### Escenario 3.2: Aplicar Filtro de Tiempo

**Objetivo**: Verificar que los filtros funcionan

**Pasos**:
1. Localiza el selector de período arriba a la izquierda (debajo del título)
2. Verás opciones como:
   - Todo
   - Últimos 7 días
   - Últimos 30 días
   - Año en curso

**Prueba 1 - Selecciona "Últimos 7 días"**:
```
Resultado Esperado:
- Los KPIs se actualizan
- Las gráficas se actualizan
- La tabla muestra solo incidencias de los últimos 7 días
- Los números bajan (menos incidencias en 7 días que en "Todo")
```

**Prueba 2 - Selecciona "Año en curso"**:
```
Resultado Esperado:
- Los KPIs se actualizan nuevamente
- Las gráficas cambian
- La tabla muestra incidencias desde el 1 de enero
```

**✓ Verificado**: Filtro de tiempo funciona correctamente

---

### Escenario 3.3: Filtrar la Tabla

**Objetivo**: Verificar filtros de estado, urgencia y grupo

**Pasos**:
1. Busca los selectores de filtro en la tabla (debajo de los gráficos)
2. Deberías ver 3 dropdown:
   - **Estado**: Todos, Abierto, Cerrado, etc.
   - **Sistema**: Todos, SOP_TEAM, OPS_TEAM, etc.
   - **Urgencia**: Todos, Alta, Media, Baja

**Prueba 1 - Filtra por Estado "Abierto"**:
```
Pasos:
1. Haz clic en dropdown "Estado"
2. Selecciona "Abierto"
3. La tabla se actualiza inmediatamente

Resultado Esperado:
- Tabla muestra solo filas con Estado = "Abierto"
- El número total en los KPIs se reduce
- Las gráficas se actualizan
```

**Prueba 2 - Filtra por Urgencia "Alta"**:
```
Pasos:
1. Haz clic en dropdown "Urgencia"
2. Selecciona "Alta"

Resultado Esperado:
- Tabla muestra solo filas con Urgencia = "Alta"
- Los gráficos también se filtran
- Los KPIs se recalculan
```

**✓ Verificado**: Filtros de tabla funcionan correctamente

---

## Parte 4: Testing de Auto-Refresh

### Escenario 4.1: Verificar Indicador de Frescura

**Objetivo**: Ver el indicador que muestra qué tan recientes son los datos

**Pasos**:
1. Mira la parte superior derecha del dashboard (en el header)
2. Deberías ver:

```
"Ahora mismo" (verde)    ← Datos muy recientes (<1 min)
   o
"Hace 5m" (amarillo)     ← Datos recientes (5-30 min)
   o
"Hace 45m" (rojo)        ← Datos antiguos (>30 min)
```

**Resultado Esperado**:
- Si acabas de cargar datos: muestra "Ahora mismo" en color verde ✓
- Si esperas 2 minutos: muestra "Hace 2m" en color verde ✓
- Color cambia a rojo si pasan más de 30 minutos ✓

**✓ Verificado**: Indicador de frescura funciona

---

### Escenario 4.2: Botón de Actualización Manual

**Objetivo**: Verificar que puedes actualizar datos manualmente

**Pasos**:
1. Localiza el botón **"🔄 Actualizar"** (junto al indicador de frescura)
2. Haz clic en él
3. Observa:

**Durante la actualización** (2-3 segundos):
```
El botón muestra estado de carga:
🔄 Actualizando... (deshabilitado)
```

**Después** (si hay datos nuevos):
```
✓ Notificación: "Datos del dashboard actualizados"
✓ Indicador de frescura se reinicia ("Ahora mismo")
```

**✓ Verificado**: Actualización manual funciona

---

### Escenario 4.3: Toggle de Auto-Actualización

**Objetivo**: Verificar que puedes activar/desactivar auto-refresh

**Pasos**:
1. Localiza el toggle **"Auto-actualizar:"** (junto al indicador)
2. Verás un botón que dice "ON" o "OFF"

**Prueba 1 - Desactivar auto-refresh**:
```
Pasos:
1. Haz clic en el toggle (si está en ON, lo pones en OFF)
2. Espera 30 segundos sin hacer nada
3. Carga un archivo CSV nuevo en otra pestaña

Resultado Esperado:
- El dashboard NO se actualiza automáticamente
- El indicador de frescura se pone rojo/naranja
- Solo se actualiza si haces clic en "Actualizar" manualmente
```

**Prueba 2 - Reactivar auto-refresh**:
```
Pasos:
1. Haz clic en el toggle (lo pones en ON)
2. Espera 10 segundos

Resultado Esperado:
✓ Notificación: "Auto-actualización activada"
✓ Datos se actualizan automáticamente cada 10 segundos
✓ Indicador de frescura se reinicia
```

**✓ Verificado**: Toggle de auto-refresh funciona

---

### Escenario 4.4: Sincronización Entre Pestañas

**Objetivo**: Verificar que múltiples pestañas se sincronizan

**Pasos**:
1. Abre el dashboard en **Pestaña A**
2. Abre el dashboard en **Pestaña B** (misma URL)
3. Ambas deberían mostrar los mismos datos

**Prueba 1 - Upload en una pestaña**:
```
Pasos:
1. En Pestaña A: Carga un archivo CSV nuevo
2. Espera 2-3 segundos
3. Mira Pestaña B sin hacer nada

Resultado Esperado:
✓ Pestaña B se actualiza automáticamente
✓ Ambas pestañas muestran los mismos datos
✓ Indicador de frescura es igual en ambas
```

**Prueba 2 - Actualizar en una pestaña**:
```
Pasos:
1. En Pestaña A: Haz clic en "🔄 Actualizar"
2. Pestaña B debería actualizarse también

Resultado Esperado:
✓ Ambas pestañas muestran datos idénticos
✓ Ambas tienen mismo indicador de frescura
```

**✓ Verificado**: Sincronización entre pestañas funciona

---

## Parte 5: Testing de Manejo de Errores

### Escenario 5.1: Error de Validación

**Objetivo**: Verificar mensajes de error claros

**Pasos**:
1. Crea un archivo CSV sin la columna "Urgencia"
2. Intenta cargarlo

**Resultado Esperado**:
```
❌ Error (fondo rojo en la vista previa):

"Falta columnas requeridas: ['Urgencia']
Verifica que el archivo CSV incluya todas las columnas necesarias."

[Acciones]:
- Botón "Cancelar" - cierra el modal
- Botón "Seleccionar otro archivo" - intenta cargar otro
```

**✓ Verificado**: Mensajes de error son claros y útiles

---

### Escenario 5.2: Error de Conexión (Simular)

**Objetivo**: Verificar comportamiento cuando no hay conexión al servidor

**Pasos**:
1. Cierra el backend (si está corriendo)
2. Intenta cargar un archivo en el frontend
3. Espera la respuesta

**Resultado Esperado**:
```
❌ Notificación amarilla:
"No se pudo verificar datos del servidor. Reintentando..."

La aplicación reintentar automáticamente cada 10 segundos
```

**Si rearrancas el backend**:
```
✓ La notificación desaparece
✓ El sistema se recupera automáticamente
✓ Los datos se sincronizan
```

**✓ Verificado**: Manejo de errores es robusto

---

## Parte 6: Testing Responsivo

### Escenario 6.1: Desktop (1920x1080)

**Pasos**:
1. Abre el dashboard en un navegador desktop
2. Verifica:
   - ✓ Todos los elementos visibles
   - ✓ Las gráficas se ven bien
   - ✓ La tabla es legible
   - ✓ El modal cabe en la pantalla
   - ✓ Los colores se ven correctos (naranjas, verdes)

**Resultado Esperado**:
```
✓ Interfaz completa y funcional
✓ Sin necesidad de hacer scroll horizontal
✓ Todos los botones accesibles
```

---

### Escenario 6.2: Tablet (768x1024)

**Pasos** (si tienes tablet):
1. Abre dashboard en tablet
2. Verifica:
   - ✓ Interfaz adaptada al ancho
   - ✓ Gráficas redimensionadas
   - ✓ Tabla desplazable horizontalmente si es necesario
   - ✓ Touch interactions funcionan (arrastrar, tocar)

**En Chrome Desktop** (simular tablet):
```
1. F12 para abrir Developer Tools
2. Presiona Ctrl+Shift+M para modo responsive
3. Selecciona "iPad" del dropdown
4. Verifica que todo se ve bien
```

**Resultado Esperado**:
```
✓ Interfaz se adapta bien a pantalla más pequeña
✓ Textos legibles sin zoom
✓ Botones accesibles
```

---

## Parte 7: Checklist de Funcionalidad Completa

Marca cada uno conforme lo verifiques:

### Upload y Validación
- [ ] Upload de archivo CSV válido funciona
- [ ] Validación automática detecta errores
- [ ] Mensajes de error son claros
- [ ] Modal se cierra después de upload exitoso
- [ ] Datos se cargan en el dashboard dentro de 5 segundos

### Dashboard
- [ ] Los KPI cards muestran números correctos
- [ ] Las gráficas se renderizan correctamente
- [ ] Las tablas muestran todos los datos
- [ ] Los filtros de tiempo funcionan
- [ ] Los filtros de tabla funcionan
- [ ] Los colores son consistentes (naranjas)

### Auto-Refresh
- [ ] Indicador de frescura se actualiza
- [ ] Botón manual de actualización funciona
- [ ] Toggle de auto-refresh funciona
- [ ] Sincronización entre pestañas funciona
- [ ] Notificaciones de actualización aparecen

### Manejo de Errores
- [ ] Errores de validación son claros
- [ ] El sistema se recupera de errores
- [ ] Notificaciones aparecen cuando hay problemas
- [ ] No hay crashes del navegador
- [ ] Los datos no se pierden en errores

### Responsividad
- [ ] Se ve bien en desktop (1920x1080)
- [ ] Se ve bien en tablet (768x1024)
- [ ] Texto es legible en todos los tamaños
- [ ] Botones son clickeables en todos los tamaños
- [ ] Las gráficas se adaptan

---

## Resumen de Testing

Si TODOS los items están marcados ✓, entonces:

✅ **LA APLICACIÓN FUNCIONA CORRECTAMENTE EN SUS CARACTERÍSTICAS PRINCIPALES**

**Próximos pasos**:
1. Si todo funciona: Sistema listo para producción
2. Si hay problemas: Reporta el número del escenario que falla
3. Si quieres más testing: Testing de seguridad, performance, etc.

---

**¿Preguntas o problemas durante el testing?**
- Describe qué paso falla
- Incluye el número del escenario
- Cuéntame el comportamiento esperado vs actual

**¡Éxito!** 🚀
