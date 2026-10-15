<#
.SYNOPSIS
    Despliegue automatizado en 1 clic de Release Dashboard Application en infocodes@10.132.26.96.

.DESCRIPTION
    1. Comprueba el estado del repositorio local (rama production).
    2. Sube cambios locales a origin/production (salvo con -SkipPush).
    3. Ejecuta de forma segura scripts/deploy.sh en el VPS remoto por SSH:
       - Backup preventivo de data/output y nginx.conf activo.
       - Auto-stash de ficheros de runtime generados en el servidor.
       - Pull de la rama production.
       - Sincronizacion y validacion sintactica de Nginx (nginx -t).
       - Recarga suave en caliente (nginx -s reload).
       - Smoke tests de salud (/dashboards/portal/, /api/epsilon/, /dashboards/reportes-incidencias/).
       - Rotacion automatica de backups.

.PARAMETER TargetHost
    Host SSH de destino. Por defecto: "infocodes@10.132.26.96".

.PARAMETER RemoteDir
    Ruta remota de la aplicacion. Por defecto: "/infocodes/project/release-dashboard-application".

.PARAMETER SkipPush
    Omite el git push local y salta directamente a la ejecucion remota de deploy.sh.

.PARAMETER VerifyOnly
    No realiza despliegue ni pull; solo ejecuta las comprobaciones de salud en el servidor remoto.

.EXAMPLE
    .\scripts\deploy-production.ps1
    Flujo estandar: push a origin/production y ejecucion de deploy.sh en el VPS.

.EXAMPLE
    .\scripts\deploy-production.ps1 -VerifyOnly
    Verifica los endpoints activos sin desplegar.
#>

[CmdletBinding()]
param(
    [string]$TargetHost = "infocodes@10.132.26.96",
    [string]$RemoteDir = "/infocodes/project/release-dashboard-application",
    [switch]$SkipPush,
    [switch]$VerifyOnly
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "`n[$([DateTime]::Now.ToString('HH:mm:ss'))] === $Message ===" -ForegroundColor Cyan
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

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

Write-Host "=================================================================" -ForegroundColor DarkYellow
Write-Host "   Deploy 1-Clic - Release Dashboard Application                 " -ForegroundColor Yellow
Write-Host "   Destino : $TargetHost                                         " -ForegroundColor Gray
Write-Host "   Ruta    : $RemoteDir                                          " -ForegroundColor Gray
Write-Host "=================================================================" -ForegroundColor DarkYellow

# -------------------------------------------------------------------------
# Modo Solo Verificacion (-VerifyOnly)
# -------------------------------------------------------------------------
if ($VerifyOnly) {
    Write-Step "Verificando estado y salud del servidor remoto..."
    $verifyScript = @"
echo -n "Portal (/dashboards/portal/): "
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8081/dashboards/portal/
echo -n "Incidencias Masivas (/dashboards/massive-incidents/): "
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8081/dashboards/massive-incidents/
echo -n "Postmortem (/dashboards/postmortem/): "
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8081/dashboards/postmortem/
echo -n "Release KPIs (/dashboards/release-kpis/): "
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8081/dashboards/release-kpis/
echo -n "Reportes Incidencias (/dashboards/reportes-incidencias/): "
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8081/dashboards/reportes-incidencias/
echo -n "Proxy API Epsilon (/api/epsilon/...): "
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8081/api/epsilon/resumenIA/INC000004141215
"@

    $Normalized = $verifyScript.Replace("`r`n", "`n") + "`n# end-of-script"
    $Normalized | ssh $TargetHost bash
    exit 0
}

# -------------------------------------------------------------------------
# 1. Comprobaciones locales de Git
# -------------------------------------------------------------------------
Write-Step "1/3. Comprobando repositorio local..."

Push-Location $repoRoot
try {
    $currentBranch = (git branch --show-current).Trim()
    if ($currentBranch -ne "production") {
        Write-WarnMsg "Estas en la rama '$currentBranch'. La rama de despliegue en servidor es 'production'."
        $confirm = Read-Host "Deseas continuar de todos modos? (s/N)"
        if ($confirm -notmatch "^[sSyY]$") {
            Write-Failure "Despliegue cancelado por el usuario."
            exit 1
        }
    } else {
        Write-Ok "Rama local: $currentBranch"
    }

    $gitStatus = git status --porcelain
    if ($gitStatus) {
        Write-WarnMsg "Hay cambios locales pendientes en el repositorio:"
        git status -s
        Write-WarnMsg "Por favor haz commit antes de desplegar para que lleguen a produccion."
        $confirm = Read-Host "Deseas continuar desplegando sin estos cambios locales? (s/N)"
        if ($confirm -notmatch "^[sSyY]$") {
            Write-Failure "Despliegue cancelado."
            exit 1
        }
    } else {
        Write-Ok "Arbol de trabajo local limpio."
    }

    # -------------------------------------------------------------------------
    # 2. Push a origin/production
    # -------------------------------------------------------------------------
    if (-not $SkipPush) {
        Write-Step "2/3. Enviando commits a origin/$currentBranch..."
        git push origin $currentBranch
        if ($LASTEXITCODE -ne 0) {
            Write-Failure "Error al ejecutar 'git push origin $currentBranch'."
            exit 1
        }
        Write-Ok "Push completado exitosamente."
    } else {
        Write-Step "2/3. Salto de push solicitado (-SkipPush)."
    }
} finally {
    Pop-Location
}

# -------------------------------------------------------------------------
# 3. Ejecucion de deploy.sh en VPS remoto
# -------------------------------------------------------------------------
Write-Step "3/3. Ejecutando deploy.sh en $TargetHost..."

$remoteCmd = "bash $RemoteDir/scripts/deploy.sh"
ssh -t $TargetHost $remoteCmd

if ($LASTEXITCODE -ne 0) {
    Write-Failure "El despliegue remoto fallo con codigo de salida $LASTEXITCODE."
    exit $LASTEXITCODE
}

Write-Host "`n=================================================================" -ForegroundColor DarkGreen
Write-Host "   [OK] Despliegue en produccion completado con exito            " -ForegroundColor Green
Write-Host "   Portal : http://infocodes.si.orange.es:8081/dashboards/portal/" -ForegroundColor Cyan
Write-Host "=================================================================`n" -ForegroundColor DarkGreen
