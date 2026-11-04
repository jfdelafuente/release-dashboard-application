[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$ExcelPath,
    [string]$SheetName = "Incidencias Pdtes",
    [string]$OutJsonPath = ""
)

if (-not (Test-Path $ExcelPath)) {
    Write-Error "El fichero Excel no existe: $ExcelPath"
    exit 1
}

if ([string]::IsNullOrWhiteSpace($OutJsonPath)) {
    $dir = Split-Path -Parent $ExcelPath
    $baseName = [System.IO.Path]::GetFileNameWithoutExtension($ExcelPath)
    $OutJsonPath = Join-Path $dir "$baseName-extracted.json"
}

Write-Output "Iniciando extracción desde: $ExcelPath"
Write-Output "Hoja objetivo: $SheetName"

$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false
$excel.AutomationSecurity = 3 # msoAutomationSecurityForceDisable

try {
    $wb = $excel.Workbooks.Open($ExcelPath, 0, $true)
    $ws = $null
    foreach ($sheet in $wb.Worksheets) {
        if ($sheet.Name -eq $SheetName) {
            $ws = $sheet
            break
        }
    }
    
    if ($null -eq $ws) {
        Write-Error "No se encontró la hoja '$SheetName' en el libro."
        exit 1
    }

    $ur = $ws.UsedRange
    $rowCount = $ur.Rows.Count
    $colCount = $ur.Columns.Count
    Write-Output "Dimensiones de la hoja: $rowCount filas x $colCount columnas"

    $headers = @()
    for ($c = 1; $c -le $colCount; $c++) {
        $headers += [string]($ws.Cells.Item(1, $c).Text).Trim()
    }

    $records = @()
    for ($r = 2; $r -le $rowCount; $r++) {
        $codeCell = $ws.Cells.Item($r, 1).Text
        if ([string]::IsNullOrWhiteSpace($codeCell)) {
            continue
        }

        $obj = [ordered]@{}
        $hasData = $false

        for ($c = 1; $c -le $colCount; $c++) {
            $cell = $ws.Cells.Item($r, $c)
            $rawVal = $cell.Value2
            $textVal = $cell.Text

            # Manejo de celdas con errores de fórmula (#¡VALOR!, #N/A, #REF!, etc.)
            # En COM, Value2 para fórmulas rotas devuelve un entero negativo grande (p. ej. -2146826273)
            if (($rawVal -is [int] -or $rawVal -is [long] -or $rawVal -is [double]) -and ($rawVal -lt 0) -and ($textVal -match '^#')) {
                $v = ""
            } elseif ($rawVal -is [datetime]) {
                $v = $rawVal.ToString("dd/MM/yyyy")
            } elseif ($rawVal -is [double] -and $rawVal -gt 30000 -and $rawVal -lt 60000 -and ($headers[$c-1] -like '*Fecha*' -or $headers[$c-1] -like '*Apertura*' -or $headers[$c-1] -like '*Prevista*')) {
                # Fecha serial de Excel
                try {
                    $v = [datetime]::FromOADate($rawVal).ToString("dd/MM/yyyy")
                } catch {
                    $v = [string]$textVal
                }
            } elseif (-not [string]::IsNullOrWhiteSpace($textVal)) {
                $v = [string]$textVal
            } else {
                $v = [string]$rawVal
            }

            $key = $headers[$c - 1]
            if ([string]::IsNullOrWhiteSpace($key)) {
                $key = "Col$c"
            }
            $obj[$key] = [string]$v
            if (-not [string]::IsNullOrWhiteSpace($v)) {
                $hasData = $true
            }
        }

        if ($hasData) {
            $records += [pscustomobject]$obj
        }
    }

    $outData = [ordered]@{
        headers = $headers
        rowCount = $records.Count
        records = $records
    }

    $jsonStr = $outData | ConvertTo-Json -Depth 6
    [System.IO.File]::WriteAllText($OutJsonPath, $jsonStr, [System.Text.Encoding]::UTF8)
    Write-Output "OK: $($records.Count) filas extraídas y guardadas en: $OutJsonPath"

    $wb.Close($false)
} finally {
    $excel.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($excel) | Out-Null
}

