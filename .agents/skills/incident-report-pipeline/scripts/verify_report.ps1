[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$JsonPath,
    [Parameter(Mandatory=$true)]
    [string]$MdPath,
    [string]$HtmlPath = ""
)

if (-not (Test-Path $JsonPath)) {
    Write-Error "No se encuentra el fichero JSON: $JsonPath"
    exit 1
}
if (-not (Test-Path $MdPath)) {
    Write-Error "No se encuentra el fichero Markdown: $MdPath"
    exit 1
}

$errors = @()
$json = Get-Content $JsonPath -Raw -Encoding utf8 | ConvertFrom-Json
$md = [System.IO.File]::ReadAllText($MdPath, [System.Text.Encoding]::UTF8)

Write-Output "=== 1. Conteo total de incidencias ==="
$jsonCount = $json.rowCount
$mdTableRows = [regex]::Matches($md, '(?m)^\|\s*(INC\d+)\s*\|')
Write-Output "JSON rowCount: $jsonCount | Filas en Markdown: $($mdTableRows.Count)"
if ($jsonCount -ne $mdTableRows.Count) {
    $errors += "Mismatch en total de filas: JSON=$jsonCount, MD=$($mdTableRows.Count)"
}

Write-Output "=== 2. Parseo de tablas del Markdown ==="
$mdLines = $md -split '\r?\n'
$currentProject = ""
$parsedMdRows = [ordered]@{}
$projectRows = [ordered]@{}

foreach ($line in $mdLines) {
    if ($line -match '^## Proyecto:\s*(.*)') {
        $currentProject = $Matches[1].Trim()
        if (-not $projectRows.Contains($currentProject)) {
            $projectRows[$currentProject] = @()
        }
    } elseif ($line -match '^\|\s*(INC\d+)\s*\|\s*([^|]*)\|\s*([^|]*)\|\s*([^|]*)\|\s*(.*?)\|\s*(.*?)\|\s*(.*?)\|\s*$') {
        $code = $Matches[1].Trim()
        $fAp = $Matches[2].Trim()
        $sist = $Matches[3].Trim()
        $est = $Matches[4].Trim()
        $desc = $Matches[5].Trim()
        $imp = $Matches[6].Trim()
        $sol = $Matches[7].Trim()
        
        $rowObj = [pscustomobject]@{
            Project = $currentProject
            Codigo = $code
            FechaApertura = $fAp
            Sistema = $sist
            Estado = $est
            Descripcion = $desc
            Impacto = $imp
            Solucion = $sol
        }
        $parsedMdRows[$code] = $rowObj
        $projectRows[$currentProject] += $rowObj
    }
}

Write-Output "Proyectos encontrados en Markdown: $($projectRows.Count)"
$sumRows = 0
foreach ($pk in $projectRows.Keys) {
    $c = $projectRows[$pk].Count
    $sumRows += $c
    Write-Output " - $pk : $c incidencias"
}
if ($sumRows -ne $jsonCount) {
    $errors += "Suma de filas por proyecto ($sumRows) no coincide con total JSON ($jsonCount)"
}

Write-Output "=== 3. Validación de formato de Estado y Fecha Apertura ==="
$enAnalisisCount = 0
$conFechaCount = 0

foreach ($r in $json.records) {
    $props = $r.psobject.properties
    $code = ($props | Where-Object { $_.Name -like '*digo*' }).Value
    $status = ($props | Where-Object { $_.Name -eq 'Status' }).Value
    $fechaPrev = ($props | Where-Object { $_.Name -like '*Prevista*' }).Value
    $fechaAp = ($props | Where-Object { $_.Name -like '*Apertura*' }).Value
    
    if (-not $parsedMdRows.Contains($code)) {
        $errors += "Incidencia $($code) no encontrada en Markdown"
        continue
    }
    
    $mdRow = $parsedMdRows[$code]
    
    # Check Fecha Apertura
    if ($mdRow.FechaApertura -ne $fechaAp) {
        $errors += "Fecha Apertura incorrecta en $($code): esperado '$fechaAp', obtenido '$($mdRow.FechaApertura)'"
    }
    
    # Check Estado (usando regex segura para evitar dependencias de codificación de tildes)
    if ($status -match '^En An.lisis') {
        $enAnalisisCount++
        if ($mdRow.Estado -notmatch '^En An.lisis$') {
            $errors += "Estado en $($code) debería ser 'En Análisis' estricto sin fecha, pero es '$($mdRow.Estado)'"
        }
    } elseif ($status -eq 'Pendiente') {
        $conFechaCount++
        $expectedDate = if ([string]::IsNullOrWhiteSpace($fechaPrev)) { 'sin fecha' } else { $fechaPrev.Trim() }
        $expectedEst = "Pendiente (Estimado: $expectedDate)"
        if ($mdRow.Estado -ne $expectedEst) {
            $errors += "Estado en $($code) esperado '$expectedEst', pero es '$($mdRow.Estado)'"
        }
    } elseif ($status -match '^Resuelto' -or $status -match '^Soluci.n Rechazada') {
        $conFechaCount++
        $expectedDate = if ([string]::IsNullOrWhiteSpace($fechaPrev)) { 'sin fecha' } else { $fechaPrev.Trim() }
        $cleanStatus = if ($status -match '^Soluci') { "Soluci$([char]0x00F3)n Rechazada" } else { 'Resuelto' }
        $expectedEst = "$cleanStatus ($expectedDate)"
        if ($mdRow.Estado -ne $expectedEst) {
            $errors += "Estado en $($code) esperado '$expectedEst', pero es '$($mdRow.Estado)'"
        }
    }
    
    # Check empty cells
    if ([string]::IsNullOrWhiteSpace($mdRow.Impacto)) {
        $errors += "Impacto vacío en $($code)"
    }
    if ([string]::IsNullOrWhiteSpace($mdRow.Solucion)) {
        $errors += "Solución vacía en $($code)"
    }
}

Write-Output "En Análisis sin fecha: $enAnalisisCount | Con fecha entre paréntesis: $conFechaCount | Suma: $($enAnalisisCount + $conFechaCount) (esperado: $jsonCount)"
if (($enAnalisisCount + $conFechaCount) -ne $jsonCount) {
    $errors += "Suma de estados ($($enAnalisisCount + $conFechaCount)) no coincide con total ($jsonCount)"
}

Write-Output "=== 4. Verificación literal de Descripción / Impacto / Solución ==="
function Clean-Norm([string]$t) {
    if ([string]::IsNullOrWhiteSpace($t)) { return '' }
    $t = $t -replace '\r?\n', ' '
    $t = $t -replace '\s+', ' '
    $t = $t.Trim()
    $t = $t -replace '\\\|', '|'
    return $t
}

function Format-HitosLines([string]$rawHitos) {
    if ([string]::IsNullOrWhiteSpace($rawHitos)) { return '' }
    $rawLines = $rawHitos -split '\r?\n'
    $items = [System.Collections.Generic.List[string]]::new()
    $currentItem = ""
    
    foreach ($l in $rawLines) {
        $trimmed = $l.Trim()
        if ([string]::IsNullOrWhiteSpace($trimmed)) { continue }
        
        if ($trimmed -match '^(\d{2}/\d{2}(?:/\d{2,4})?:?)\s*(.*)$') {
            if (-not [string]::IsNullOrWhiteSpace($currentItem)) {
                $items.Add($currentItem)
            }
            $date = $Matches[1]
            $rest = $Matches[2]
            if ($date -notmatch ':\s*$') { $date += ":" }
            $currentItem = Clean-Norm ("$date $rest")
        } else {
            if ([string]::IsNullOrWhiteSpace($currentItem)) {
                $currentItem = Clean-Norm $trimmed
            } else {
                $currentItem += " " + (Clean-Norm $trimmed)
            }
        }
    }
    if (-not [string]::IsNullOrWhiteSpace($currentItem)) {
        $items.Add($currentItem)
    }
    
    return ($items | ForEach-Object { "• " + $_ }) -join "<br>"
}

function Format-ImpactMarkdown([string]$raw) {
    if ([string]::IsNullOrWhiteSpace($raw)) { return 'Impacto no especificado' }
    
    $pattern = '(?m)^(Hitos t.cnicos|Bloqueos|Siguiente acci.n)\r?$'
    $secMatches = [regex]::Matches($raw, $pattern)
    
    if ($secMatches.Count -eq 0) {
        return Clean-Norm $raw
    }
    
    $main = Clean-Norm $raw.Substring(0, $secMatches[0].Index)
    $parts = [System.Collections.Generic.List[string]]::new()
    if (-not [string]::IsNullOrWhiteSpace($main)) {
        $parts.Add($main)
    }
    
    for ($i = 0; $i -lt $secMatches.Count; $i++) {
        $m = $secMatches[$i]
        $header = $m.Groups[1].Value
        $start = $m.Index + $m.Length
        $end = if ($i + 1 -lt $secMatches.Count) { $secMatches[$i + 1].Index } else { $raw.Length }
        $rawSection = $raw.Substring($start, $end - $start)
        
        if ($header -match '^Bloqueos') {
            $content = Clean-Norm $rawSection
            if (-not [string]::IsNullOrWhiteSpace($content)) {
                $parts.Add("<br><br>**Bloqueos:** $content")
            }
        } elseif ($header -match '^Siguiente') {
            $content = Clean-Norm $rawSection
            if (-not [string]::IsNullOrWhiteSpace($content)) {
                $parts.Add("<br><br>**Siguiente acción:** $content")
            }
        } elseif ($header -match '^Hitos') {
            $hitosFmt = Format-HitosLines $rawSection
            if (-not [string]::IsNullOrWhiteSpace($hitosFmt)) {
                $parts.Add("<br><br>**Hitos técnicos:**<br>$hitosFmt")
            }
        }
    }
    return [string]::Join('', $parts)
}

$discrepancies = 0
foreach ($r in $json.records) {
    $props = $r.psobject.properties
    $code = ($props | Where-Object { $_.Name -like '*digo*' }).Value
    $acciones = ($props | Where-Object { $_.Name -eq 'Acciones' }).Value
    $descProb = ($props | Where-Object { $_.Name -like '*problema*' }).Value
    
    $mdRow = $parsedMdRows[$code]
    if ($null -eq $mdRow) { continue }
    
    # Recalculate mechanically
    $warnChar = [char]0x26A0
    $checkChar = [char]0x2713
    $calcDesc = ''
    $calcImp = ''
    $calcSol = ''
    
    if ($acciones -match '(?s)' + [regex]::Escape($warnChar) + '\s*Impacto' -and $acciones -match '(?s)' + [regex]::Escape($checkChar) + '\s*Soluci.n') {
        if ($acciones -match '(?s)^(.*?)' + [regex]::Escape($warnChar) + '\s*Impacto\r?\n?(.*?)' + [regex]::Escape($checkChar) + '\s*Soluci.n\r?\n?(.*)$') {
            $calcDesc = $Matches[1]
            $calcImp = $Matches[2]
            $calcSol = $Matches[3]
        }
    } elseif ($acciones -match '(?s)' + [regex]::Escape($warnChar) + '\s*Impacto') {
        if ($acciones -match '(?s)^(.*?)' + [regex]::Escape($warnChar) + '\s*Impacto\r?\n?(.*)$') {
            $calcDesc = $Matches[1]
            $calcImp = $Matches[2]
            $calcSol = 'Pendiente de solución'
        }
    } elseif ($acciones -match '(?s)' + [regex]::Escape($checkChar) + '\s*Soluci.n') {
        if ($acciones -match '(?s)^(.*?)' + [regex]::Escape($checkChar) + '\s*Soluci.n\r?\n?(.*)$') {
            $calcDesc = $Matches[1]
            $calcImp = 'Impacto no especificado'
            $calcSol = $Matches[2]
        }
    } else {
        $calcDesc = $acciones
        $calcImp = 'Impacto no especificado'
        $calcSol = 'Pendiente de solución'
    }
    
    $calcDesc = Clean-Norm $calcDesc
    $calcImp = Format-ImpactMarkdown $calcImp
    $calcSol = Clean-Norm $calcSol
    
    # Regla: Si Acciones empezaba directamente con Solución o el texto extraído está vacío
    if ([string]::IsNullOrWhiteSpace($calcDesc)) {
        $calcDesc = Clean-Norm ($descProb -replace '^\[2026R\d+\]\s*(-|\s*\[PRJ-\d+\]\s*-?)?\s*', '')
    }
    if ([string]::IsNullOrWhiteSpace($calcImp)) { $calcImp = 'Impacto no especificado' }
    if ([string]::IsNullOrWhiteSpace($calcSol)) { $calcSol = 'Pendiente de solución' }
    
    $mdDesc = Clean-Norm $mdRow.Descripcion
    $mdImp = Clean-Norm $mdRow.Impacto
    $mdSol = Clean-Norm $mdRow.Solucion
    
    if ($calcDesc -ne $mdDesc) {
        $discrepancies++
        $errors += "Discrepancia Descripcion en $($code):`n  Esperado: $calcDesc`n  Markdown: $mdDesc"
    }
    if ($calcImp -ne $mdImp) {
        $discrepancies++
        $errors += "Discrepancia Impacto en $($code):`n  Esperado: $calcImp`n  Markdown: $mdImp"
    }
    if ($calcSol -ne $mdSol) {
        $discrepancies++
        $errors += "Discrepancia Solucion en $($code):`n  Esperado: $calcSol`n  Markdown: $mdSol"
    }
}

Write-Output "Discrepancias textuales encontradas: $discrepancies"

if (-not [string]::IsNullOrWhiteSpace($HtmlPath) -and (Test-Path $HtmlPath)) {
    Write-Output "=== 5. Verificación de HTML ==="
    $html = [System.IO.File]::ReadAllText($HtmlPath, [System.Text.Encoding]::UTF8)
    $htmlTableRows = [regex]::Matches($html, '(?i)<tr>\s*<td>(INC\d+)</td>')
    Write-Output "Filas en HTML: $($htmlTableRows.Count) (esperado: $jsonCount)"
    if ($htmlTableRows.Count -ne $jsonCount) {
        $errors += "Mismatch de filas en HTML: esperado $jsonCount, encontrado $($htmlTableRows.Count)"
    }
}

Write-Output "=== RESULTADO DE VERIFICACION ==="
if ($errors.Count -eq 0) {
    Write-Output "TODO CORRECTO: 0 errores, 0 discrepancias."
} else {
    Write-Output ("SE ENCONTRARON " + $errors.Count + " ERRORES:")
    foreach ($err in $errors) {
        Write-Output (" - " + $err)
    }
    exit 1
}

