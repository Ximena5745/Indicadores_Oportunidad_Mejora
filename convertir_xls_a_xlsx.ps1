$DATA_RAW = "c:\Users\ximen\OneDrive\Proyectos_DS\Indicadores_Oportunidad_Mejora\data\raw"

$files = @(
    @{ src = "$DATA_RAW\OM.xls";                      dst = "$DATA_RAW\OM.xlsx" },
    @{ src = "$DATA_RAW\Plan de accion\PA_1.xls";     dst = "$DATA_RAW\Plan de accion\PA_1.xlsx" },
    @{ src = "$DATA_RAW\Plan de accion\PA_2.xls";     dst = "$DATA_RAW\Plan de accion\PA_2.xlsx" }
)

$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false
$ok = 0

foreach ($f in $files) {
    if (-not (Test-Path $f.src)) {
        Write-Host "  -  $($f.src) no encontrado"
        continue
    }
    try {
        $wb = $excel.Workbooks.Open($f.src)
        $wb.SaveAs($f.dst, 51)   # 51 = xlOpenXMLWorkbook (.xlsx)
        $wb.Close($false)
        Write-Host "  ok  $([System.IO.Path]::GetFileName($f.src)) -> $([System.IO.Path]::GetFileName($f.dst))"
        $ok++
    } catch {
        Write-Host "  error  $($f.src): $_"
    }
}

$excel.Quit()
[System.Runtime.Interopservices.Marshal]::ReleaseComObject($excel) | Out-Null
Write-Host "Convertidos: $ok archivo(s)"
