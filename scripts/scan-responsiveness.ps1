param([Parameter(Mandatory=$true)][string]$Folder, [string]$BaseUrl = 'http://127.0.0.1:8000')
$start = Invoke-RestMethod "$BaseUrl/scan/start" -Method Post -ContentType 'application/json' -Body (@{ folder_path = $Folder } | ConvertTo-Json) -TimeoutSec 10
"scan_id: $($start.scan_id)  (start returned: $($start.status))"

$sw = [System.Diagnostics.Stopwatch]::StartNew()
$maxHealthMs = 0; $samples = 0; $phases = @(); $monotonic = $true; $lastProcessed = -1; $lastPrint = -5
do {
    Start-Sleep -Milliseconds 250
    $t = [System.Diagnostics.Stopwatch]::StartNew()
    $null = Invoke-RestMethod "$BaseUrl/health" -TimeoutSec 30
    $healthMs = $t.ElapsedMilliseconds
    if ($healthMs -gt $maxHealthMs) { $maxHealthMs = $healthMs }

    $p = Invoke-RestMethod "$BaseUrl/scan/progress?scan_id=$($start.scan_id)" -TimeoutSec 30
    $samples++
    if ($phases -notcontains $p.phase) { $phases += $p.phase }
    if ($p.phase -eq 'hashing') {
        if ($p.files_processed -lt $lastProcessed) { $monotonic = $false }
        $lastProcessed = $p.files_processed
    }
    if (($sw.Elapsed.TotalSeconds - $lastPrint) -ge 5) {
        $lastPrint = $sw.Elapsed.TotalSeconds
        "{0,5:N0}s  phase={1}  {2}/{3}  health={4}ms" -f $sw.Elapsed.TotalSeconds, $p.phase, $p.files_processed, $p.files_total, $healthMs
    }
} while ($p.status -eq 'in_progress')

"----- summary -----"
"final status    : $($p.status) (phase $($p.phase))"
"duration        : {0:N1}s" -f $sw.Elapsed.TotalSeconds
"phases seen     : $($phases -join ', ')"
"progress samples: $samples   hashing count never went backwards: $monotonic"
"photos / groups : $($p.total_photos) / $($p.duplicate_groups)"
"max /health time: $maxHealthMs ms"
if (($p.status -eq 'completed') -and $monotonic -and ($maxHealthMs -lt 1000) -and ($phases -contains 'hashing')) {
    Write-Host 'RESPONSIVENESS TEST PASSED' -ForegroundColor Green
} else { Write-Host 'RESPONSIVENESS TEST FAILED' -ForegroundColor Red }