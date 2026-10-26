<#
.SYNOPSIS
    Despliegue automatizado y modernizado de Release Dashboard Application en infocodes@10.132.26.96.

.DESCRIPTION
    Implementa el modelo de despliegue selectivo por artefacto (Standalone Runtime):
      1. Regeneración automática de data/output/agents_catalog.json desde biblioteca-agentes.
      2. Verificación de git local (rama production obligatoria) y push a origin/production.
      3. Empaquetado selectivo de runtime (dist/release-dashboard-runtime.tar.gz):
         - Dashboards, converters, scripts, nginx.conf, requirements.txt, VERSION y catálogo de agentes.
         - Excluye .git, tests, specs, documentación, maquetas y ficheros demo.
         - data/ persistente se preserva en el servidor; agents_catalog.json se sincroniza automáticamente.
      4. Subida rápida del artefacto por SCP a /tmp/.
      5. Ejecución remota segura por SSH:
         - Backup preventivo en /infocodes/var/backups/release-dashboard-application/.
         - Extracción limpia sobre /infocodes/project/release-dashboard-application.
         - Sincronización del catálogo de agentes en almacenamiento persistente.
         - Switch atómico symlink 'current'.
         - Validación y recarga en caliente de Nginx.
         - Sondas de verificación HTTP.
         - Rotación automática de copias de seguridad (conserva las últimas 5).

.PARAMETER TargetHost
    Host SSH de destino. Por defecto: "infocodes@10.132.26.96".

.PARAMETER RemoteDir
    Ruta remota de la aplicación. Por defecto: "/infocodes/project/release-dashboard-application".

.PARAMETER AgentsLibraryPath
    Ruta personalizada a la biblioteca de agentes. Por defecto: C:\Users\jose.delafuente\Claude\Projects\biblioteca-agentes.

.PARAMETER SkipCatalogBuild
    Omite la regeneración automática de data/output/agents_catalog.json antes del despliegue.

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
    Flujo estándar: regeneración de catálogo, git push, empaquetado selectivo, subida, despliegue y verificación.

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
    [string]$AgentsLibraryPath,
    [switch]$SkipCatalogBuild,
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
    for ep in "/dashboards/portal/" "/dashboards/massive-incidents/" "/dashboards/postmortem/" "/dashboards/release-kpis/" "/dashboards/reportes-incidencias/" "/dashboards/agents-catalog/" "/api/health"; do
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
# Auto-detectar git si no se encuentra en el PATH de la sesión actual
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    $GitCandidates = @(
        "C:\Program Files\Git\cmd\git.exe",
        "C:\Program Files\Git\bin\git.exe",
        "C:\Program Files\Git\mingw64\bin\git.exe",
        "$env:LOCALAPPDATA\Programs\Git\cmd\git.exe",
        "$env:ProgramFiles\Git\cmd\git.exe"
    )
    foreach ($cand in $GitCandidates) {
        if (Test-Path $cand) {
            $gitFolder = Split-Path -Parent $cand
            $env:PATH = "$gitFolder;$env:PATH"
            break
        }
    }
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Failure "No se encontró el ejecutable 'git' en el PATH ni en las rutas estándar de Windows."
    Write-WarnMsg "Añade Git a tu PATH con: `$env:PATH += ';C:\Program Files\Git\cmd' e inténtalo de nuevo."
    exit 1
}

# Auto-detectar ejecutable de python si no se encuentra en el PATH de la sesión actual
$PythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonCmd = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonCmd = "py"
} else {
    $PyCandidates = @(
        "C:\Program Files\Python312\python.exe",
        "C:\Program Files\Python311\python.exe",
        "C:\Program Files\Python310\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"
    )
    foreach ($cand in $PyCandidates) {
        if (Test-Path $cand) {
            $PythonCmd = $cand
            break
        }
    }
}

Push-Location $ProjectRoot
try {
    # -------------------------------------------------------------------------
    # REGENERACIÓN PREVIA DEL CATÁLOGO DE AGENTES IA
    # -------------------------------------------------------------------------
    if (-not $SkipCatalogBuild) {
        Write-Step "Catálogo" "Regenerando catálogo de agentes IA desde la biblioteca..."

        if ($DryRun) {
            Write-Ok "[DRY-RUN] Se ejecutaría: python converters/cli/build_agents_catalog.py"
        } else {
            $CatalogScript = Join-Path $ProjectRoot "converters\cli\build_agents_catalog.py"
            if (Test-Path $CatalogScript) {
                if ($PythonCmd) {
                    $catalogArgs = @($CatalogScript)
                    if ($AgentsLibraryPath) {
                        $catalogArgs += @("--library-path", $AgentsLibraryPath)
                    }

                    & $PythonCmd @catalogArgs
                    if ($LASTEXITCODE -eq 0) {
                        Write-Ok "Catálogo de agentes generado con éxito en data/output/agents_catalog.json"

                        # Si el catálogo cambió respecto a git, registrar commit automático específico
                        $catalogDiff = (git status --porcelain "data/output/agents_catalog.json" 2>$null)
                        if ($catalogDiff) {
                            git add "data/output/agents_catalog.json"
                            git commit "data/output/agents_catalog.json" -m "data(agents): regenerar catalogo de agentes pre-deploy" | Out-Null
                            if ($LASTEXITCODE -eq 0) {
                                Write-Ok "Catálogo actualizado y commiteado automáticamente en git"
                            }
                        } else {
                            Write-Ok "Catálogo de agentes al día (sin cambios en la biblioteca)"
                        }
                    } else {
                        Write-WarnMsg "No se pudo regenerar el catálogo (código de salida: $LASTEXITCODE). Se continuará con la versión existente."
                    }
                } else {
                    Write-WarnMsg "No se encontró el ejecutable de Python. Se continuará con la versión existente si está disponible."
                }
            } else {
                Write-WarnMsg "No se encontró el script generador en: $CatalogScript"
            }
        }
    } else {
        Write-Step "Catálogo" "Omitiendo regeneración del catálogo (-SkipCatalogBuild activo)."
    }

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

        # 6. Copiar catálogo de agentes regenerado al paquete runtime
        if (Test-Path "$ProjectRoot\data\output\agents_catalog.json") {
            $DataOutStaging = Join-Path $StagingDir "data\output"
            New-Item -ItemType Directory -Path $DataOutStaging -Force | Out-Null
            Copy-Item "$ProjectRoot\data\output\agents_catalog.json" -Destination $DataOutStaging
            Write-Ok "Catálogo de agentes empaquetado en el artefacto runtime"
        } else {
            Write-WarnMsg "No se encontró data/output/agents_catalog.json para empaquetar"
        }

        # 7. Generar archivo tarball comprimido
        if (Test-Path $TarballFullPath) { Remove-Item $TarballFullPath -Force }

        $tarExe = "tar"
        if (Test-Path "$env:SystemRoot\System32\tar.exe") {
            $tarExe = "$env:SystemRoot\System32\tar.exe"
        }

        # Empaquetar con bsdtar nativo de Windows (sin --force-local)
        & $tarExe -czf "$TarballFullPath" -C "$StagingDir" .
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path $TarballFullPath)) {
            # Reintento con --force-local por si se trata de un entorno GNU tar
            & $tarExe --force-local -czf "$TarballFullPath" -C "$StagingDir" . 2>$null
        }

        if (-not (Test-Path $TarballFullPath)) {
            Write-Failure "No se pudo generar el archivo comprimido $TarballFullPath."
            exit 1
        }

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
RELEASES_DIR="`$REMOTE_DIR/releases"
SHARED_DIR="`$REMOTE_DIR/shared"
CURRENT_LINK="`$REMOTE_DIR/current"
NGINX_CONF_ACTIVE="/infocodes/nginx/conf/nginx.conf"
NGINX_BIN="/infocodes/nginx/sbin/nginx"
NGINX_CONF_D="/infocodes/nginx/conf/conf.d"

# Desacoplamiento de almacenamiento persistente a /infocodes/var/storage (Single Source of Truth)
STORAGE_BASE="/infocodes/var/storage/release-dashboard"
EXECUTIVE_STORAGE="/infocodes/var/storage/executive_pptx"
LOGS_BASE="/infocodes/var/log/release-dashboard"

if [ -d "/infocodes/nginx/sbin" ]; then
    export PATH="/infocodes/nginx/sbin:`$PATH"
fi

echo "--> [Remoto] Asegurando estructura en /infocodes/var/storage y directorios de release..."
mkdir -p "`$REMOTE_DIR" "`$BACKUP_BASE" "`$RELEASES_DIR" "`$SHARED_DIR" "`$NGINX_CONF_D"
mkdir -p "`$STORAGE_BASE/input" "`$STORAGE_BASE/output" "`$STORAGE_BASE/reports" "`$STORAGE_BASE/errors" "`$STORAGE_BASE/archive"
mkdir -p "`$EXECUTIVE_STORAGE" "`$LOGS_BASE"

# Enlace de sinergia entre informes ejecutivos y release dashboard
ln -sfn "`$EXECUTIVE_STORAGE" "`$STORAGE_BASE/reports/executive"

if [ ! -f "`$TMP_TAR" ]; then
    echo "ERROR: No se encuentra `$TMP_TAR en el servidor."
    exit 1
fi

# 1. Preservar y migrar datos históricos hacia /infocodes/var/storage/release-dashboard
if [ -d "`$SHARED_DIR/data" ] && [ ! -L "`$SHARED_DIR/data" ]; then
    echo "--> [Remoto] Migrando datos existentes desde `$SHARED_DIR/data/ a `$STORAGE_BASE/..."
    cp -rn "`$SHARED_DIR/data"/* "`$STORAGE_BASE/" 2>/dev/null || true
    rm -rf "`$SHARED_DIR/data"
fi
if [ -d "`$REMOTE_DIR/data" ] && [ ! -L "`$REMOTE_DIR/data" ]; then
    echo "--> [Remoto] Migrando datos locales desde `$REMOTE_DIR/data/ a `$STORAGE_BASE/..."
    cp -rn "`$REMOTE_DIR/data"/* "`$STORAGE_BASE/" 2>/dev/null || true
    rm -rf "`$REMOTE_DIR/data"
fi
if [ -d "`$SHARED_DIR/logs" ] && [ ! -L "`$SHARED_DIR/logs" ]; then
    echo "--> [Remoto] Migrando logs existentes desde `$SHARED_DIR/logs/ a `$LOGS_BASE/..."
    cp -rn "`$SHARED_DIR/logs"/* "`$LOGS_BASE/" 2>/dev/null || true
    rm -rf "`$SHARED_DIR/logs"
fi
if [ -d "`$REMOTE_DIR/logs" ] && [ ! -L "`$REMOTE_DIR/logs" ]; then
    echo "--> [Remoto] Migrando logs existentes desde `$REMOTE_DIR/logs/ a `$LOGS_BASE/..."
    cp -rn "`$REMOTE_DIR/logs"/* "`$LOGS_BASE/" 2>/dev/null || true
    rm -rf "`$REMOTE_DIR/logs"
fi

# Enlaces de compatibilidad hacia el almacenamiento desacoplado
ln -sfn "`$STORAGE_BASE" "`$SHARED_DIR/data"
ln -sfn "`$LOGS_BASE" "`$SHARED_DIR/logs"
ln -sfn "`$STORAGE_BASE" "`$REMOTE_DIR/data"
ln -sfn "`$LOGS_BASE" "`$REMOTE_DIR/logs"

# 2. Copia de seguridad preventiva
TIMESTAMP="`$(date +%Y%m%d_%H%M%S)"
BACKUP_ARCHIVE="`$BACKUP_BASE/backup_`$TIMESTAMP.tar.gz"
echo "--> [Remoto] Creando backup preventivo en `$BACKUP_ARCHIVE..."
(
    cd "`$STORAGE_BASE"
    tar -czf "`$BACKUP_ARCHIVE" output "`$REMOTE_DIR/nginx.conf" 2>/dev/null || tar -czf "`$BACKUP_ARCHIVE" output 2>/dev/null || true
    echo "--> [Remoto] Backup preventivo generado: `$(ls -lh "`$BACKUP_ARCHIVE" 2>/dev/null | awk '{print `$5}')"
)

# 3. Extraer nueva release en releases/<TIMESTAMP>
RELEASE_ID="`$(date +%Y%m%d_%H%M%S)"
NEW_RELEASE_DIR="`$RELEASES_DIR/`$RELEASE_ID"
mkdir -p "`$NEW_RELEASE_DIR"
echo "--> [Remoto] Extrayendo nueva release en `$NEW_RELEASE_DIR..."
tar -xzf "`$TMP_TAR" -C "`$NEW_RELEASE_DIR"
rm -f "`$TMP_TAR"

# 4. Sincronizar catálogo de agentes en almacenamiento persistente si viene en el paquete
if [ -f "`$NEW_RELEASE_DIR/data/output/agents_catalog.json" ]; then
    echo "--> [Remoto] Sincronizando catálogo de agentes a `$STORAGE_BASE/output/agents_catalog.json..."
    cp -f "`$NEW_RELEASE_DIR/data/output/agents_catalog.json" "`$STORAGE_BASE/output/agents_catalog.json" 2>/dev/null || true
    rm -rf "`$NEW_RELEASE_DIR/data"
fi

# Enlazar datos desacoplados y logs dentro de la nueva release
ln -sfn "`$STORAGE_BASE" "`$NEW_RELEASE_DIR/data"
ln -sfn "`$LOGS_BASE" "`$NEW_RELEASE_DIR/logs"

# 5. Normalizar permisos y saltos de línea (CRLF -> LF)
sed -i 's/\r$//' "`$NEW_RELEASE_DIR"/scripts/*.sh "`$NEW_RELEASE_DIR"/*.sh 2>/dev/null || true
chmod +x "`$NEW_RELEASE_DIR"/scripts/*.sh "`$NEW_RELEASE_DIR"/*.sh 2>/dev/null || true

# 6. Switch atómico del enlace simbólico 'current'
echo "--> [Remoto] Activando symlink atómico: current -> releases/`$RELEASE_ID"
ln -sfn "releases/`$RELEASE_ID" "`$CURRENT_LINK"

# 7. Sincronizar scripts de control y metadatos en la raíz de `$REMOTE_DIR
cp -f "`$NEW_RELEASE_DIR/status.sh" "`$REMOTE_DIR/status.sh"
cp -f "`$NEW_RELEASE_DIR/rollback.sh" "`$REMOTE_DIR/rollback.sh"
if [ -f "`$NEW_RELEASE_DIR/VERSION" ]; then
    cp -f "`$NEW_RELEASE_DIR/VERSION" "`$REMOTE_DIR/VERSION"
fi
chmod +x "`$REMOTE_DIR/status.sh" "`$REMOTE_DIR/rollback.sh"

# 8. Limpiar elementos residuales en la raíz de `$REMOTE_DIR
#    Solo deben quedar: current, releases, shared, data, logs, status.sh, rollback.sh, VERSION
echo "--> [Remoto] Limpiando elementos residuales en la raíz de `$REMOTE_DIR..."
for entry in `$(ls -A "`$REMOTE_DIR"); do
    case "`$entry" in
        current|releases|shared|data|logs|status.sh|rollback.sh|VERSION)
            ;;
        *)
            rm -rf "`$REMOTE_DIR/`$entry" 2>/dev/null || true
            echo "--> [Remoto] Limpiado elemento residual: `$entry"
            ;;
    esac
done

# 10. Sincronización y validación de Nginx
echo "--> [Remoto] Comprobando configuración de Nginx..."
NGINX_CHANGED=false
if [ -f "`$CURRENT_LINK/nginx.conf" ] && [ -f "`$NGINX_CONF_ACTIVE" ]; then
    if ! cmp -s "`$CURRENT_LINK/nginx.conf" "`$NGINX_CONF_ACTIVE"; then
        NGINX_CHANGED=true
    fi
elif [ -f "`$CURRENT_LINK/nginx.conf" ]; then
    NGINX_CHANGED=true
fi

if [ "`$NGINX_CHANGED" = true ]; then
    echo "--> [Remoto] Se detectaron cambios en nginx.conf. Sincronizando con `$NGINX_CONF_ACTIVE..."
    cp -f "`$NGINX_CONF_ACTIVE" "`$NGINX_CONF_ACTIVE.bak" 2>/dev/null || true
    cp -f "`$CURRENT_LINK/nginx.conf" "`$NGINX_CONF_ACTIVE"

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

# 11. Rotación de releases antiguas (conservar las últimas 3 releases)
if [ -d "`$RELEASES_DIR" ]; then
    OLD_RELEASES=`$(ls -1 "`$RELEASES_DIR" 2>/dev/null | sort | head -n -3 || true)
    for old_rel in `$OLD_RELEASES; do
        if [ -n "`$old_rel" ] && [ "`$old_rel" != "`$RELEASE_ID" ]; then
            echo "--> [Remoto] Rotación: eliminando release antigua `$old_rel..."
            rm -rf "`$RELEASES_DIR/`$old_rel" 2>/dev/null || true
        fi
    done
fi

# 12. Rotación de backups antiguos (conservar los últimos 5)
BACKUPS_COUNT=`$(find "`$BACKUP_BASE" -maxdepth 1 -name "backup_*.tar.gz" -type f | wc -l)
if [ "`$BACKUPS_COUNT" -gt 5 ]; then
    find "`$BACKUP_BASE" -maxdepth 1 -name "backup_*.tar.gz" -type f | sort | head -n -5 | while read -r OLD_BKP; do
        echo "--> [Remoto] Rotación: eliminando backup antiguo `$(basename "`$OLD_BKP")..."
        rm -f "`$OLD_BKP"
    done
fi

# 12.1. Reiniciar servicio backend de reportes (cso-incident-masivas-report) si existe
CSO_SERVICE="/infocodes/project/cso-incident-masivas-report/current/backend/service.sh"
if [ -x "`$CSO_SERVICE" ]; then
    echo "--> [Remoto] Reiniciando backend de reportes para recargar módulos y converters..."
    "`$CSO_SERVICE" restart || true
fi

# 13. Verificación de Sondas de Salud HTTP
echo ""
echo "=== Verificación de Sondas de Salud HTTP ==="
if [ -x "`$REMOTE_DIR/status.sh" ]; then
    "`$REMOTE_DIR/status.sh"
else
    for ep in "/dashboards/portal/" "/dashboards/massive-incidents/" "/dashboards/postmortem/" "/dashboards/release-kpis/" "/dashboards/reportes-incidencias/" "/dashboards/agents-catalog/" "/api/health"; do
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
Write-Host "   Gestión de Problemas : http://infocodes.si.orange.es:8081/problemas" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor DarkGreen
