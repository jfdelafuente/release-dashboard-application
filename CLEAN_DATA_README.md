# Scripts de Limpieza de Datos

Estos scripts permiten limpiar todos los archivos CSV y JSON del proyecto para dejar el ambiente limpio y listo para nuevas pruebas.

## 📁 Archivos Limpiados

Los scripts eliminan archivos de estos directorios:

```
data/input/          → Archivos CSV cargados
data/output/         → Archivos JSON convertidos
data/errors/         → Reportes de errores
backend/temp_uploads/ → Archivos temporales del backend
```

⚠️ **IMPORTANTE**: Los scripts **mantienen los directorios intactos**, solo eliminan los archivos.

---

## 🔧 Uso en Linux/Mac

### 1. Hacer el script ejecutable (primera vez)
```bash
chmod +x clean-data.sh
```

### 2. Ejecutar la limpieza
```bash
./clean-data.sh
```

### Ejemplo de salida
```
🧹 Iniciando limpieza de datos...

Limpiando data/input... ✓ Eliminados 3 archivo(s)
Limpiando data/output... ✓ Eliminados 5 archivo(s)
Limpiando data/errors... ✓ Limpiado
Limpiando backend/temp_uploads... ✓ Limpiado

✅ Limpieza completada

Resumen de directorios:
  data/input: 0 archivo(s) total (CSV: 0, JSON: 0)
  data/output: 0 archivo(s) total (CSV: 0, JSON: 0)
  data/errors: 0 archivo(s) total (CSV: 0, JSON: 0)
  backend/temp_uploads: 0 archivo(s) total (CSV: 0, JSON: 0)

🚀 Ambiente limpio y listo para pruebas
```

---

## 🪟 Uso en Windows (PowerShell)

### 1. Abrir PowerShell como Administrador (recomendado)

### 2. Navegar al proyecto
```powershell
cd C:\Users\tu-usuario\proyectos\release-dashboard-application
```

### 3. Ejecutar el script
```powershell
.\clean-data.ps1
```

**Si obtienes error de permisos**, ejecuta esto primero:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## ✨ Qué hace cada script

### clean-data.sh (Linux/Mac)
- ✓ Encuentra y elimina todos los `.csv` y `.json`
- ✓ Usa `find` para búsqueda recursiva
- ✓ Muestra un resumen con colores
- ✓ Maneja errores de forma silenciosa

### clean-data.ps1 (Windows)
- ✓ Encuentra y elimina todos los `.csv` y `.json`
- ✓ Usa cmdlets nativos de PowerShell
- ✓ Muestra un resumen con colores
- ✓ Seguro: solo toca archivos especificados

---

## 🚨 Seguridad

Ambos scripts:
- ❌ No eliminan directorios
- ❌ No modifican archivos `.py`, `.js`, `.html`, etc.
- ❌ Solo tocan archivos con extensión `.csv` y `.json`
- ✅ Muestran resumen antes y después

---

## 📋 Alternativa Manual

Si prefieres limpiar manualmente, puedes usar:

### Linux/Mac
```bash
# Limpiar cada directorio
rm -f data/input/*.{csv,json}
rm -f data/output/*.{csv,json}
rm -f data/errors/*.{csv,json}
rm -f backend/temp_uploads/*
```

### Windows (CMD)
```cmd
del data\input\*.csv /s /q
del data\input\*.json /s /q
del data\output\*.csv /s /q
del data\output\*.json /s /q
del data\errors\*.csv /s /q
del data\errors\*.json /s /q
del backend\temp_uploads\* /q
```

---

## 💡 Consejos

1. **Antes de pruebas de testing**: Ejecuta el script para empezar con un ambiente limpio
2. **Después de fallos**: Limpia y reinicia el backend para un estado fresco
3. **Para debugging**: Deja algunos archivos de prueba si necesitas verificar conversiones

---

## 🆘 Resolución de Problemas

### "Permission denied" (Linux/Mac)
```bash
chmod +x clean-data.sh  # Vuelve a dar permisos
./clean-data.sh
```

### "Script is disabled" (Windows PowerShell)
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### No se eliminan algunos archivos
- Verifica que no haya procesos usando esos archivos
- Cierra navegadores y servidores
- Intenta ejecutar como administrador (Windows)

---

## 📝 Ejemplo Completo de Testing

```bash
# 1. Limpiar datos previos
./clean-data.sh

# 2. Iniciar backend
cd backend
python -m uvicorn app.main:app --reload

# 3. En otra terminal, abrir dashboard
# Abrir: http://localhost:5500/dashboards/massive-incidents-dashboard.html

# 4. Cargar CSV de prueba
# Seleccionar archivo CSV en el dashboard

# 5. Verificar dashboard cargado correctamente

# 6. Cuando termines, vuelve a limpiar
./clean-data.sh
```

¡Listo! 🎉
