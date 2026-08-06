$accdbFiles = Get-ChildItem -Filter "*.accdb"
if ($accdbFiles.Count -eq 0) {
    Write-Error "No .accdb file found."
    exit
}
$dbPath = $accdbFiles[0].FullName
$outputPath = Join-Path (Get-Location) "data_export.json"

Write-Output "Connecting to MS Access database: $dbPath"
$conn = New-Object -ComObject ADODB.Connection
try {
    $conn.Open("Provider=Microsoft.ACE.OLEDB.12.0;Data Source=$dbPath;")
    
    $rs = New-Object -ComObject ADODB.Recordset
    Write-Output "Querying table [PRINCIPAL AIT]..."
    $rs.Open("SELECT * FROM [PRINCIPAL AIT]", $conn)
    
    $records = New-Object System.Collections.Generic.List[PSCustomObject]
    $count = 0
    
    while (-not $rs.EOF) {
        $rec = [PSCustomObject]@{
            Codigo = $rs.Fields.Item(0).Value
            DataVal = $rs.Fields.Item(1).Value
            NumeroAIT = $rs.Fields.Item(2).Value
            Agente = $rs.Fields.Item(3).Value
            Status = $rs.Fields.Item(4).Value
            Observacao = $rs.Fields.Item(5).Value
            DataDigitacao = $rs.Fields.Item(6).Value
            Placa = $rs.Fields.Item(7).Value
        }
        $records.Add($rec)
        $count++
        if ($count % 2000 -eq 0) {
            Write-Output "Loaded $count records..."
        }
        $rs.MoveNext()
    }
    
    Write-Output "Total records retrieved: $count"
    $rs.Close()
    $conn.Close()
    
    Write-Output "Saving to JSON: $outputPath"
    # Convert to JSON and save with UTF8 encoding
    $json = ConvertTo-Json -InputObject $records -Depth 5
    Set-Content -Path $outputPath -Value $json -Encoding utf8
    Write-Output "Export complete!"
} catch {
    Write-Error "Error: $_"
    if ($rs -and $rs.State -ne 0) { $rs.Close() }
    if ($conn -and $conn.State -ne 0) { $conn.Close() }
}
