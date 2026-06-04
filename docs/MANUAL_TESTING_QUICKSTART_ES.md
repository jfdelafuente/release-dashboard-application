# Test Manual - Guía de Inicio Rápido

**Fecha**: 2 de junio de 2026
**Objetivo**: Preparar el entorno y ejecutar test manuales de funcionalidad

---

## 🚀 Paso 1: Preparar el Entorno (2-3 minutos)

### Verificar Directorios de Datos

```bash
# Navega a la carpeta del proyecto
cd c:\Users\jose.delafuente\proyectos\release-dashboard-application

# Verifica que existan los directorios
ls data/

# Deberías ver:
# input/      (para CSVs pendientes de conversión)
# output/     (para JSONs convertidos)
# errors/     (para reportes de error)
# temp_uploads/ (para archivos temporales)
```

**✓ Verificado**: Directorios existen

### Preparar Datos de Test

```bash
# Asegúrate de que test data esté disponible
ls tests/test_data/

# Deberías ver:
# - valid_sample.csv
# - missing_headers.csv
# - empty.csv
```

**✓ Verificado**: Archivos de test existen

---

## 🖥️ Paso 2: Iniciar Backend (FastAPI Server)

### Terminal 1: Backend

```bash
# Navega al directorio del backend
cd backend

# Activa el ambiente virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instala dependencias (primera vez)
pip install -r requirements.txt

# Inicia el servidor FastAPI
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Deberías ver:
# Uvicorn running on http://0.0.0.0:8000
# Application startup complete
```

**⏳ Espera**: La salida `Application startup complete` antes de continuar

**✓ Verificado**: Backend ejecutándose en puerto 8000

### Prueba Rápida del Backend

```bash
# En otra terminal, verifica que el backend responde
curl http://localhost:8000/health

# Deberías recibir:
# {"status": "ok", "service": "CSV Upload API", "version": "1.0.0"}
```

---

## 🌐 Paso 3: Iniciar Frontend (Dashboards)

### Terminal 2: Frontend

```bash
# Navega a la carpeta de dashboards
cd dashboards

# Inicia un servidor HTTP simple
python -m http.server 5000

# Deberías ver:
# Serving HTTP on 0.0.0.0 port 5000
```

**✓ Verificado**: Frontend servido en puerto 5000

### Acceder a los Dashboards

Abre tu navegador en estas URLs:

1. **Dashboard Portal (selecciona el dashboard)**
   ```
   http://localhost:5000/dashboard-portal.html
   ```

2. **Massive Incidents Dashboard** (PRINCIPAL)
   ```
   http://localhost:5000/massive-incidents-dashboard.html
   ```

3. **Postmortem Dashboard**
   ```
   http://localhost:5000/postmortem-dashboard.html
   ```

---

## ✅ Paso 4: Ejecutar Test Manual - Escenario 1

### Test 1.1: Cargar CSV Válido

**Objetivo**: Verificar que puedo cargar un archivo CSV válido

**Pasos**:

1. Abre: http://localhost:5000/massive-incidents-dashboard.html

2. Haz clic en el botón **"📤 Subir CSV"** (arriba a la derecha)

3. Se abrirá un modal de upload. Verás:
   ```
   📂 Seleccionar Archivo CSV
   O arrastra tu archivo aquí
   ```

4. Haz clic en **"Seleccionar Archivo CSV"**

5. Navega a: `tests/test_data/`

6. Selecciona: **`valid_sample.csv`**

7. Haz clic en **"Abrir"**

**Resultado Esperado** (en 2-3 segundos):

```
✓ Vista Previa Mostrada:
  📄 valid_sample.csv
  📊 Codificación detectada: UTF-8
  🔀 Delimitador: Coma (,)
  📈 Número de filas: 3
  ✅ Validación: PASADA

  [Botón] ✅ Confirmar y Convertir
  [Botón] ❌ Cancelar
```

**Acciones**:
1. Revisa que la información sea correcta
2. Haz clic en **"✅ Confirmar y Convertir"**

**Resultado Final Esperado** (en 3-5 segundos):

```
✓ Notificación Verde:
  "¡Archivo cargado correctamente!"

✓ Modal se cierra automáticamente

✓ Dashboard se actualiza con nuevos datos
```

---

## 📊 Paso 5: Verificar Dashboard

### Después de Cargar Datos

Deberías ver automáticamente:

**KPI Cards** (arriba del dashboard):
```
┌────────────────────────────┐
│ Total Incidencias: 3       │
│ Incidencias Pendientes: 2  │
│ Tendencia 7 días: +5% 🔴   │
│ Tendencia 15 días: -2% 🟢  │
│ Tendencia 30 días: +8% 🔴  │
└────────────────────────────┘
```

**Tabla de Incidencias**:
```
Código    | Descripción | Estado   | Urgencia | Grupo
INC000001 | Incident 1  | Abierto  | Alta     | TEAM1
INC000002 | Incident 2  | Cerrado  | Media    | TEAM2
...
```

**Gráficas**:
- Barras naranjas mostrando incidencias por día
- Línea mostrando backlog acumulado

**✓ Verificado**: Dashboard muestra datos correctamente

---

## 🔄 Paso 6: Verificar Auto-Refresh

### Indicador de Frescura

En la parte superior derecha del dashboard deberías ver:

```
"Ahora mismo" (verde) ← Datos muy recientes (<1 min)
```

Espera 2-3 minutos y deberías ver:

```
"Hace 2m" (verde) ← Datos actuales
```

Si pasas 30 minutos sin actualizar:

```
"Hace 45m" (rojo) ← Datos antiguos, necesita actualización
```

**✓ Verificado**: Indicador de frescura funciona

### Botón de Actualización Manual

1. Busca el botón **"🔄 Actualizar"** (junto al indicador)

2. Haz clic en él

3. Deberías ver:
   ```
   🔄 Actualizando... (deshabilitado mientras se actualiza)
   ```

4. Después de 2-3 segundos:
   ```
   ✓ Notificación: "Datos del dashboard actualizados"
   ✓ Indicador vuelve a "Ahora mismo"
   ```

**✓ Verificado**: Actualización manual funciona

---

## 🗂️ Próximos Pasos

Una vez hayas completado estos test, continúa con la **guía completa de test manual**:

📄 `docs/MANUAL_TESTING_GUIDE_ES.md`

Ahí encontrarás:
- **Parte 2**: Test de Upload (3 escenarios)
- **Parte 3**: Test de Dashboard (3 escenarios)
- **Parte 4**: Test de Auto-Refresh (4 escenarios)
- **Parte 5**: Test de Manejo de Errores (2 escenarios)
- **Parte 6**: Test Responsivo (2 escenarios)
- **Parte 7**: Checklist completo de funcionalidad

---

## 🐛 Si Algo Falla

### Error: Backend no responde (Connection refused)

```bash
# Verifica que el backend esté ejecutándose
lsof -i :8000

# Si no aparece nada, el backend no está corriendo
# Vuelve a la Terminal 1 y verifica que uvicorn se inició
```

### Error: Frontend no se carga (Page not found)

```bash
# Verifica que el frontend esté ejecutándose
lsof -i :5000

# Si no aparece nada, el frontend no está corriendo
# Vuelve a la Terminal 2 y verifica que http.server se inició
```

### Error: Upload falla con "ERR_001"

```
Esto significa: Falta columnas requeridas
Solución: Asegúrate de usar valid_sample.csv, no missing_headers.csv
```

### Error: Dashboard vacío después de upload

```
Esto puede significar:
1. Los datos no se procesaron aún
2. El archivo JSON no se generó
3. Hay un error en la conversión

Pasos para verificar:
1. Abre DevTools (F12)
2. Ve a la pestaña "Console"
3. Busca mensajes de error
4. Revisa la carpeta data/output/ para ver si el JSON se creó
```

---

## ✨ Éxito

Si ves el dashboard cargado con datos, la notificación "¡Archivo cargado correctamente!", y el indicador de frescura funcionando, entonces:

### ✅ **LA APLICACIÓN FUNCIONA CORRECTAMENTE**

---

**¿Preguntas?** Describe qué paso falla y el error exacto que ves.

**Próximo paso**: Ve a `docs/MANUAL_TESTING_GUIDE_ES.md` para los test detallados.
