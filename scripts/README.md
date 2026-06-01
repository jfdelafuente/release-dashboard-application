# Scripts de Automatización

Scripts para ejecutar los converters y generar dashboards automáticamente.

## 📜 generate-dashboards.sh

Script principal que ejecuta todo el proceso de conversión de datos.

### Características

- ✅ Procesa todos los CSV en `data/input/`
- ✅ Ejecuta converters de incidencias masivas
- ✅ Ejecuta converters de postmortems
- ✅ Genera `index.json`
- ✅ Logging detallado
- ✅ Manejo de errores
- ✅ Validación de salida

### Instalación

1. **Hacer el script ejecutable:**
```bash
chmod +x /infocodes/release-dashboard-application/scripts/generate-dashboards.sh
```

2. **Configurar Python (en el VPS):**
```bash
cd /infocodes/release-dashboard-application
pip install -r converters/requirements.txt
```

### Uso Manual

```bash
./scripts/generate-dashboards.sh
```

### Configurar en Crontab

**Opción A: Diariamente a las 2 AM**
```bash
0 2 * * * /infocodes/release-dashboard-application/scripts/generate-dashboards.sh >> /var/log/dashboards-cron.log 2>&1
```

**Opción B: Cada 6 horas**
```bash
0 */6 * * * /infocodes/release-dashboard-application/scripts/generate-dashboards.sh >> /var/log/dashboards-cron.log 2>&1
```

**Opción C: Cada hora**
```bash
0 * * * * /infocodes/release-dashboard-application/scripts/generate-dashboards.sh >> /var/log/dashboards-cron.log 2>&1
```

### Agregar a Crontab

```bash
# Editar crontab
crontab -e

# Pegar la línea deseada y guardar (Ctrl+X, Y, Enter en nano)
```

### Logs

Los logs se guardan en:
- `logs/dashboards-generation-YYYYMMDD.log` (dentro del proyecto)
- Además el cron puede redirigir a `/var/log/dashboards-cron.log`

Ver logs:
```bash
tail -f /infocodes/release-dashboard-application/logs/dashboards-generation-*.log
```

### Estructura de Directorios Esperada

```
/infocodes/release-dashboard-application/
├── converters/
│   ├── cli/
│   │   ├── convert_incidents.py
│   │   ├── convert_postmortems.py
│   │   └── build_index.py
│   └── requirements.txt
├── data/
│   ├── input/          ← CSV files a procesar
│   ├── output/         ← JSON files generados
│   └── errors/         ← Reportes de error
├── logs/               ← Logs del script (se crea automáticamente)
└── scripts/
    ├── generate-dashboards.sh
    └── README.md
```

### Solución de Problemas

**El script no ejecuta:**
```bash
# Verificar permisos
ls -la scripts/generate-dashboards.sh

# Debe mostrar: -rwxr-xr-x
# Si no, ejecutar:
chmod +x scripts/generate-dashboards.sh
```

**Error: "No such file or directory"**
- Verificar que el path `/infocodes/release-dashboard-application/` es correcto
- Ajustar la variable `PROJECT_ROOT` en el script si es diferente

**Error: "Python not found"**
- Instalar Python en el VPS
- O usar el path completo: `/usr/bin/python3` o similar

**Los converters no generan datos:**
- Verificar que existen archivos CSV en `data/input/`
- Ver logs en `logs/dashboards-generation-*.log`
- Probar manualmente: `python converters/cli/convert_incidents.py data/input/archivo.csv`

### Monitoreo

**Ver último log:**
```bash
tail /infocodes/release-dashboard-application/logs/dashboards-generation-$(date +%Y%m%d).log
```

**Ver ejecuciones de cron:**
```bash
grep generate-dashboards /var/log/syslog  # En sistemas Linux
```

**Ver estado de los datos:**
```bash
ls -lh /infocodes/release-dashboard-application/data/output/
```
