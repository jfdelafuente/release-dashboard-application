<#
.SYNOPSIS
    Despliegue automatizado y modernizado de Release Dashboard Application en infocodes@10.132.26.96.

.DESCRIPTION
    Implementa el modelo de despliegue selectivo por artefacto (Standalone Runtime):
      1. Verificación de git local (rama production obligatoria) y push a origin/production.
      2. Empaquetado selectivo de runtime (dist/release-dashboard-runtime.tar.gz):
         - Solo dashboards, converters, scripts, nginx.conf, requirements.txt y VERSION.
         - Excluye .git, tests, specs, documentación, maquetas y ficheros demo.
         - data/ NO se incluye en el artefacto para no sobrescribir jamás datos persistentes.
      3. Subida rápida del artefacto por SCP a /tmp/.
      4. Ejecución remota segura por SSH:
         - Backup preventivo en /infocodes/var/backups/release-dashboard-application/.
         - Extracción limpia sobre /infocodes/project/release-dashboard-application.
         - Preservación íntegra de directorios de datos (data/input, output, reports, errors, archive).
         - Sincronización y validación sintáctica de Nginx (nginx -t) con recarga en caliente (nginx -s reload).
         - Rollback automático de Nginx en caso de error sintáctico.
         - Limpieza de residuos de desarrollo en el servidor.
         - Sondas de verificación (smoke tests) para todos los dashboards y proxies.
         - Rotación automática de copias de seguridad (conserva las últimas 5).

.PARAMETER TargetHost
    Host SSH de destino. Por defecto: "infocodes@10.132.26.96".

.PARAMETER RemoteDir
    Ruta remota de la aplicación. Por defecto: "/infocodes/project/release-dashboard-application".

.PARAMETER SkipPush
    Omite el git push local a origin/production.

.PARAMETER SkipBuild
    Omite el empaquetado local y reutiliza el paquete existente en dist/release-dashboard-runtime.tar.gz.

.PARAMETER SkipUpload
    Omite la subida por SCP y asume que el artefacto ya reside en el servidor.

.PARAMETER VerifyOnly
    No despliega nada; únicamente consulta el estado del servicio y las sondas de salud.

.PARAMETER Rollback
    Restaura instantáneamente la última copia de seguridad remota y recarga Nginx.

.PARAMETER DryRun
    Muestra los comandos que se ejecutarían sin realizar cambios en el servidor.

.EXAMPLE
    .\scripts\deploy-production.ps1
    Flujo estándar: validación de git, push, empaquetado selectivo, subida, despliegue y verificación.

.EXAMPLE
    .\scripts\deploy-production.ps1 -VerifyOnly
    Comprueba el estado de Nginx y todos los endpoints HTTP en el servidor.

.EXAMPLE
    .\scripts\deploy-production.ps1 -Rollback
    Revierte a la copia previa en /infocodes/var/backups/release-dashboard-application/.
#>

[CmdletBinding()]
param(
    [string]$TargetHost = "infocodes@10.132.26.96",
    [string]$RemoteDir = "/infocodes/project/release-dashboard-application",
    [switch]$SkipPush,
    [switch]$SkipBuild,
    [switch]$SkipUpload,
    [switch]$VerifyOnly,
    [switch]$Rollback,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$Stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$DistDir = Join-Path $ProjectRoot "dist"
$TarballRelPath = "dist/release-dashboard-runtime.tar.gz"
$TarballFullPath = Join-Path $ProjectRoot $TarballRelPath
$RemoteTmpTarball = "/tmp/release-dashboard-runtime.tar.gz"

function Write-Step {
    param([string]$Step, [string]$Message)
    Write-Host ""
    Write-Host "[$Step] $Message" -ForegroundColor Cyan
}

function Write-Ok {
    param([string]$Message)
    Write-Host "  [OK] $Message" -ForegroundColor Green
}

function Write-WarnMsg {
    param([string]$Message)
    Write-Host "  [AVISO] $Message" -ForegroundColor Yellow
}

function Write-Failure {
    param([string]$Message)
    Write-Host "  [ERROR] $Message" -ForegroundColor Red
}

function Invoke-RemoteBash {
    param(
        [string]$HostTarget,
        [string]$BashScript
    )
    $Normalized = $BashScript.Replace("`r`n", "`n") + "`n# end-of-script"
    $Normalized | ssh $HostTarget bash
}

Write-Host "=================================================================" -ForegroundColor DarkYellow
Write-Host "   Deploy Standalone Runtime - Release Dashboard Application     " -ForegroundColor Yellow
Write-Host "   Destino : $TargetHost" -ForegroundColor Gray
Write-Host "   Ruta    : $RemoteDir" -ForegroundColor Gray
Write-Host "=================================================================" -ForegroundColor DarkYellow

# -------------------------------------------------------------------------
# MODO SOLO VERIFICACIÓN (-VerifyOnly)
# -------------------------------------------------------------------------
if ($VerifyOnly) {
    Write-Step "0/1" "Consultando estado y salud del servidor remoto..."
    $verifyBash = @"
if [ -x "$RemoteDir/status.sh" ]; then
    "$RemoteDir/status.sh"
elif [ -x "$RemoteDir/scripts/status.sh" ]; then
    "$RemoteDir/scripts/status.sh"
else
    echo "=== Sondas de Salud HTTP ==="
    for ep in "/dashboards/portal/" "/dashboards/massive-incidents/" "/dashboards/postmortem/" "/dashboards/release-kpis/" "/dashboards/reportes-incidencias/" "/api/health"; do
        printf "  %-35s : " "\$ep"
        curl -s -o /dev/null -w "%{http_code}\n" --noproxy '*' "http://localhost:8081\$ep"
    done
fi
"@
    Invoke-RemoteBash -HostTarget $TargetHost -BashScript $verifyBash
    exit 0
}

# -------------------------------------------------------------------------
# MODO ROLLBACK (-Rollback)
# -------------------------------------------------------------------------
if ($Rollback) {
    Write-Step "0/1" "Ejecutando Rollback a la copia previa en $TargetHost..."
    $rollbackBash = @"
if [ -x "$RemoteDir/rollback.sh" ]; then
    "$RemoteDir/rollback.sh"
elif [ -x "$RemoteDir/scripts/rollback.sh" ]; then
    "$RemoteDir/scripts/rollback.sh"
else
    echo "ERROR: No se encontró script de rollback en $RemoteDir"
    exit 1
fi
"@
    Invoke-RemoteBash -HostTarget $TargetHost -BashScript $rollbackBash
    exit 0
}

# -------------------------------------------------------------------------
# COMPROBACIONES DE GIT LOCAL
# -------------------------------------------------------------------------
Push-Location $ProjectRoot
try {
    $currentBranch = (git branch --show-current 2>$null).Trim()
    if ($currentBranch -ne "production") {
        Write-WarnMsg "Rama actual: '$currentBranch'. La rama operativa para despliegue es 'production'."
        $confirm = Read-Host "Deseas continuar desplegando desde '$currentBranch'? (s/N)"
        if ($confirm -notmatch "^[sSyY]$") {
            Write-Failure "Despliegue cancelado por el usuario."
            exit 1
        }
    } else {
        Write-Ok "Rama local verificada: production"
    }

    $gitStatus = git status --porcelain
    if ($gitStatus) {
        Write-WarnMsg "Hay cambios locales pendientes en el repositorio:"
        git status -s
        $confirm = Read-Host "Deseas continuar desplegando sin haber commiteado estos cambios? (s/N)"
        if ($confirm -notmatch "^[sSyY]$") {
            Write-Failure "Despliegue cancelado por el usuario."
            exit 1
        }
    } else {
        Write-Ok "Árbol de trabajo git limpio"
    }

    if (-not $SkipPush) {
        Write-Step "Git" "Enviando commits locales a origin/$currentBranch..."
        git push origin $currentBranch
        if ($LASTEXITCODE -ne 0) {
            Write-Failure "Error al ejecutar 'git push origin $currentBranch'."
            exit $LASTEXITCODE
        }
        Write-Ok "Push completado exitosamente a origin/$currentBranch"
    } else {
        Write-Step "Git" "Omitiendo git push (-SkipPush activo)."
    }
} finally {
    Pop-Location
}

# -------------------------------------------------------------------------
# PASO 1: Empaquetado selectivo del Runtime
# -------------------------------------------------------------------------
if (-not $SkipBuild) {
    Write-Step "1/3" "Empaquetando artefacto runtime selectivo (sin .git ni archivos de desarrollo)..."

    if (-not (Test-Path $DistDir)) {
        New-Item -ItemType Directory -Path $DistDir -Force | Out-Null
    }

    $StagingDir = Join-Path ([System.IO.Path]::GetTempPath()) ("rd-pkg-" + [System.Guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $StagingDir -Force | Out-Null

    try {
        # 1. Copiar dashboards estáticos
        $DashboardsStaging = Join-Path $StagingDir "dashboards"
        New-Item -ItemType Directory -Path $DashboardsStaging -Force | Out-Null
        robocopy "$ProjectRoot\dashboards" "$DashboardsStaging" /E /XD __pycache__ /XF *.pyc *.log | Out-Null

        # 2. Copiar converters (excluyendo tests y caches)
        $ConvertersStaging = Join-Path $StagingDir "converters"
        New-Item -ItemType Directory -Path $ConvertersStaging -Force | Out-Null
        robocopy "$ProjectRoot\converters" "$ConvertersStaging" /E /XD tests __pycache__ .pytest_cache /XF *.pyc *.log | Out-Null

        # 3. Copiar scripts de control
        $ScriptsStaging = Join-Path $StagingDir "scripts"
        New-Item -ItemType Directory -Path $ScriptsStaging -Force | Out-Null
        robocopy "$ProjectRoot\scripts" "$ScriptsStaging" /E /XD __pycache__ /XF *.log | Out-Null

        # 4. Copiar scripts de control en la raíz del paquete
        if (Test-Path "$ProjectRoot\scripts\status.sh") {
            Copy-Item "$ProjectRoot\scripts\status.sh" -Destination $StagingDir
        }
        if (Test-Path "$ProjectRoot\scripts\rollback.sh") {
            Copy-Item "$ProjectRoot\scripts\rollback.sh" -Destination $StagingDir
        }
        if (Test-Path "$ProjectRoot\scripts\deploy.sh") {
            Copy-Item "$ProjectRoot\scripts\deploy.sh" -Destination $StagingDir
        }

        # 5. Copiar configuración de Nginx y metadatos
        Copy-Item "$ProjectRoot\nginx.conf" -Destination $StagingDir
        if (Test-Path "$ProjectRoot\requirements.txt") {
            Copy-Item "$ProjectRoot\requirements.txt" -Destination $StagingDir
        }
        if (Test-Path "$ProjectRoot\VERSION") {
            Copy-Item "$ProjectRoot\VERSION" -Destination $StagingDir
        } else {
            "0.2.0-$(Get-Date -Format 'yyyyMMdd')" | Out-File -FilePath (Join-Path $StagingDir "VERSION") -Encoding utf8
        }

        # 6. Generar archivo tarball comprimido
        if (Test-Path $TarballFullPath) { Remove-Item $TarballFullPath -Force }
        tar --force-local -czf "$TarballFullPath" -C "$StagingDir" .

        $sizeMB = [Math]::Round((Get-Item $TarballFullPath).Length / 1MB, 2)
        Write-Ok "Artefacto generado con éxito: $TarballRelPath ($sizeMB MB)"
    }
    finally {
        if (Test-Path $StagingDir) {
            Remove-Item $StagingDir -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
} else {
    Write-Step "1/3" "Omitiendo empaquetado (-SkipBuild activo). Verificando paquete existente..."
}

if (-not (Test-Path $TarballFullPath)) {
    Write-Failure "No se encontró el artefacto '$TarballFullPath'. Ejecuta sin -SkipBuild primero."
    exit 1
}

# -------------------------------------------------------------------------
# PASO 2: Subida del artefacto por SCP
# -------------------------------------------------------------------------
if (-not $SkipUpload) {
    Write-Step "2/3" "Subiendo artefacto por SCP a ${TargetHost}:${RemoteTmpTarball}..."
    if ($DryRun) {
        Write-WarnMsg "[DryRun] Se ejecutaría: scp '$TarballFullPath' '${TargetHost}:${RemoteTmpTarball}'"
    } else {
        scp "$TarballFullPath" "${TargetHost}:${RemoteTmpTarball}"
        if ($LASTEXITCODE -ne 0) {
            Write-Failure "Error al transferir el artefacto por SCP."
            exit $LASTEXITCODE
        }
        Write-Ok "Artefacto subido correctamente a ${RemoteTmpTarball}"
    }
} else {
    Write-Step "2/3" "Omitiendo subida (-SkipUpload activo). Se utilizará el artefacto presente en el servidor."
}

# -------------------------------------------------------------------------
# PASO 3: Despliegue, sincronización de Nginx y verificación en VPS
# -------------------------------------------------------------------------
Write-Step "3/3" "Ejecutando despliegue seguro, recarga de Nginx y verificación en $TargetHost..."

$remoteDeployScript = @"
set -e

REMOTE_DIR="$RemoteDir"
TMP_TAR="$RemoteTmpTarball"
BACKUP_BASE="/infocodes/var/backups/release-dashboard-application"
LOGS_DIR="`$REMOTE_DIR/logs"
TIMESTAMP="`$(date +%Y%m%d_%H%M%S)"
BACKUP_ARCHIVE="`$BACKUP_BASE/backup_`$TIMESTAMP.tar.gz"

NGINX_CONF_ACTIVE="/infocodes/nginx/conf/nginx.conf"
NGINX_BIN="/infocodes/nginx/sbin/nginx"
NGINX_CONF_D="/infocodes/nginx/conf/conf.d"

if [ -d "/infocodes/nginx/sbin" ]; then
    export PATH="/infocodes/nginx/sbin:`$PATH"
fi

echo "--> [Remoto] Asegurando directorios persistentes y de copias de seguridad..."
mkdir -p "`$REMOTE_DIR" "`$BACKUP_BASE" "`$LOGS_DIR" "`$NGINX_CONF_D"
mkdir -p "`$REMOTE_DIR/data/input" "`$REMOTE_DIR/data/output" "`$REMOTE_DIR/data/reports" "`$REMOTE_DIR/data/errors" "`$REMOTE_DIR/data/archive"

if [ ! -f "`$TMP_TAR" ]; then
    echo "ERROR: No se encuentra `$TMP_TAR en el servidor."
    exit 1
fi

# 1. Copia de seguridad preventiva
echo "--> [Remoto] Creando backup preventivo en `$BACKUP_ARCHIVE..."
(
    cd "`$REMOTE_DIR"
    ITEMS_TO_BACKUP=""
    [ -d "data" ] && ITEMS_TO_BACKUP="`$ITEMS_TO_BACKUP data"
    [ -f "nginx.conf" ] && ITEMS_TO_BACKUP="`$ITEMS_TO_BACKUP nginx.conf"
    [ -f "dashboards/release-kpis/releases-data.js" ] && ITEMS_TO_BACKUP="`$ITEMS_TO_BACKUP dashboards/release-kpis/releases-data.js"
    [ -f "VERSION" ] && ITEMS_TO_BACKUP="`$ITEMS_TO_BACKUP VERSION"

    if [ -n "`$ITEMS_TO_BACKUP" ]; then
        tar -czf "`$BACKUP_ARCHIVE" `$ITEMS_TO_BACKUP 2>/dev/null || true
        echo "--> [Remoto] Backup preventivo generado: `$(ls -lh "`$BACKUP_ARCHIVE" | awk '{print `$5}')"
    fi
)

# 2. Extracción selectiva del nuevo runtime
echo "--> [Remoto] Extrayendo runtime actualizado en `$REMOTE_DIR..."
tar -xzf "`$TMP_TAR" -C "`$REMOTE_DIR"
rm -f "`$TMP_TAR"

# 3. Normalizar permisos y saltos de línea (evitar problemas de CRLF de Windows)
sed -i 's/\r$//' "`$REMOTE_DIR"/scripts/*.sh "`$REMOTE_DIR"/*.sh 2>/dev/null || true
chmod +x "`$REMOTE_DIR"/scripts/*.sh "`$REMOTE_DIR"/*.sh 2>/dev/null || true

# 4. Asegurar scripts de control accesibles en la raíz
cp -f "`$REMOTE_DIR/scripts/status.sh" "`$REMOTE_DIR/status.sh" 2>/dev/null || true
cp -f "`$REMOTE_DIR/scripts/rollback.sh" "`$REMOTE_DIR/rollback.sh" 2>/dev/null || true
chmod +x "`$REMOTE_DIR/status.sh" "`$REMOTE_DIR/rollback.sh" 2>/dev/null || true

# 5. Limpieza de elementos obsoletos de desarrollo en el servidor
for obsolete in tests specs "MASORANGE dashboard redesign" "20260609 Incidencia IVR ExMM.pptx"; do
    if [ -e "`$REMOTE_DIR/`$obsolete" ]; then
        rm -rf "`$REMOTE_DIR/`$obsolete" 2>/dev/null || true
        echo "--> [Remoto] Limpiado elemento no runtime: `$obsolete"
    fi
done

# 6. Sincronización y validación sintáctica de Nginx
echo "--> [Remoto] Comprobando configuración de Nginx..."
NGINX_CHANGED=false
if [ -f "`$REMOTE_DIR/nginx.conf" ] && [ -f "`$NGINX_CONF_ACTIVE" ]; then
    if ! cmp -s "`$REMOTE_DIR/nginx.conf" "`$NGINX_CONF_ACTIVE"; then
        NGINX_CHANGED=true
    fi
elif [ -f "`$REMOTE_DIR/nginx.conf" ]; then
    NGINX_CHANGED=true
fi

if [ "`$NGINX_CHANGED" = true ]; then
    echo "--> [Remoto] Se detectaron cambios en nginx.conf. Sincronizando con `$NGINX_CONF_ACTIVE..."
    cp -f "`$NGINX_CONF_ACTIVE" "`$NGINX_CONF_ACTIVE.bak" 2>/dev/null || true
    cp -f "`$REMOTE_DIR/nginx.conf" "`$NGINX_CONF_ACTIVE"

    echo "--> [Remoto] Validando sintaxis de Nginx (nginx -t)..."
    if "`$NGINX_BIN" -t; then
        echo "--> [Remoto] Sintaxis de Nginx válida. Recargando en caliente..."
        "`$NGINX_BIN" -s reload
        echo "--> [Remoto] Nginx recargado con éxito."
    else
        echo "ERROR: Sintaxis de Nginx incorrecta. Revirtiendo a configuración anterior..."
        if [ -f "`$NGINX_CONF_ACTIVE.bak" ]; then
            cp -f "`$NGINX_CONF_ACTIVE.bak" "`$NGINX_CONF_ACTIVE"
        fi
        exit 1
    fi
else
    echo "--> [Remoto] nginx.conf sin cambios. No requiere recarga."
fi

# 7. Rotación de backups antiguos (conservar los últimos 5)
BACKUPS_COUNT=`$(find "`$BACKUP_BASE" -maxdepth 1 -name "backup_*.tar.gz" -type f | wc -l)
if [ "`$BACKUPS_COUNT" -gt 5 ]; then
    find "`$BACKUP_BASE" -maxdepth 1 -name "backup_*.tar.gz" -type f | sort | head -n -5 | while read -r OLD_BKP; do
        echo "--> [Remoto] Rotación: eliminando backup antiguo `$(basename "`$OLD_BKP")..."
        rm -f "`$OLD_BKP"
    done
fi

echo ""
echo "=== Verificación de Sondas de Salud HTTP ==="
if [ -x "`$REMOTE_DIR/status.sh" ]; then
    "`$REMOTE_DIR/status.sh"
else
    for ep in "/dashboards/portal/" "/dashboards/massive-incidents/" "/dashboards/postmortem/" "/dashboards/release-kpis/" "/dashboards/reportes-incidencias/" "/api/health"; do
        printf "  %-35s : " "\$ep"
        curl -sf --noproxy '*' "http://localhost:8081\$ep" >/dev/null && echo "OK (200)" || echo "ERROR"
    done
fi

echo "--> [Remoto] Despliegue de Release Dashboard completado con éxito."
"@

if ($DryRun) {
    Write-WarnMsg "[DryRun] Se ejecutaría por SSH en ${TargetHost}:"
    Write-Host $remoteDeployScript -ForegroundColor DarkGray
    exit 0
}

Invoke-RemoteBash -HostTarget $TargetHost -BashScript $remoteDeployScript
if ($LASTEXITCODE -ne 0) {
    Write-Failure "El despliegue remoto falló con código de salida $LASTEXITCODE."
    exit $LASTEXITCODE
}

$Stopwatch.Stop()
Write-Host ""
Write-Host "=================================================================" -ForegroundColor DarkGreen
Write-Host ("   ¡Despliegue completado con éxito en {0:N1}s!                   " -f $Stopwatch.Elapsed.TotalSeconds) -ForegroundColor Green
Write-Host "   Portal               : http://infocodes.si.orange.es:8081/dashboards/portal/" -ForegroundColor Cyan
Write-Host "   Incidencias Masivas  : http://infocodes.si.orange.es:8081/dashboards/massive-incidents/" -ForegroundColor Cyan
Write-Host "   Postmortem           : http://infocodes.si.orange.es:8081/dashboards/postmortem/" -ForegroundColor Cyan
Write-Host "   Release KPIs         : http://infocodes.si.orange.es:8081/dashboards/release-kpis/" -ForegroundColor Cyan
Write-Host "   Reportes Incidencias : http://infocodes.si.orange.es:8081/dashboards/reportes-incidencias/" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor DarkGreen
