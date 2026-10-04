param(
    [string]$BaseUrl = 'http://127.0.0.1:8000',
    [string]$PythonExe = 'C:\projects\PRISM\backend\venv\Scripts\python.exe'
)
$script:failed = $false
function Check([bool]$cond, [string]$msg) {
    if ($cond) { Write-Host "PASS  $msg" -ForegroundColor Green }
    else { Write-Host "FAIL  $msg" -ForegroundColor Red; $script:failed = $true }
}

$dir = Join-Path $env:TEMP ('prism_smoke_' + [guid]::NewGuid().ToString('N').Substring(0, 8))
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$mk = "import os, sys; from PIL import Image; d = sys.argv[1]; [Image.frombytes('RGB', (128, 128), os.urandom(128*128*3)).save(os.path.join(d, n)) for n in ('a.png', 'c.png')]"
& $PythonExe -c $mk $dir
Copy-Item (Join-Path $dir 'a.png') (Join-Path $dir 'b.png')

try {
    $health = Invoke-RestMethod "$BaseUrl/health" -TimeoutSec 5 -ErrorAction Stop
    Check ($health.status -eq 'ok') '/health returns ok'

    $stats = Invoke-RestMethod "$BaseUrl/stats" -TimeoutSec 5 -ErrorAction Stop
    Check ($null -ne $stats.completed_scans) '/stats responds'

    $body = @{ folder_path = $dir } | ConvertTo-Json
    $scan = Invoke-RestMethod "$BaseUrl/scan/start" -Method Post -ContentType 'application/json' -Body $body -TimeoutSec 120 -ErrorAction Stop
    Check ($scan.total_photos -eq 3) "scan found 3 photos (got $($scan.total_photos))"
    Check ($scan.exact_duplicates -eq 1) "1 exact duplicate (got $($scan.exact_duplicates))"
    Check ($scan.visual_duplicates -eq 0) "0 visual duplicates (got $($scan.visual_duplicates))"
    Check ($scan.duplicate_groups -eq 1) "1 duplicate group (got $($scan.duplicate_groups))"

    $res = Invoke-RestMethod "$BaseUrl/scan/results?scan_id=$($scan.scan_id)" -ErrorAction Stop
    $group = $res.groups[0]
    Check (@($group.photos).Count -eq 2) 'group has 2 photos'

    $img = $group.photos[0].file_path
    $thumb = Invoke-WebRequest -UseBasicParsing ("$BaseUrl/thumbnail?path=" + [uri]::EscapeDataString($img)) -ErrorAction Stop
    Check (($thumb.StatusCode -eq 200) -and (([string]$thumb.Headers['Content-Type']) -like 'image/jpeg*')) '/thumbnail returns a JPEG'

    $delBody = @{ scan_id = $scan.scan_id; group_ids = @($group.id) } | ConvertTo-Json
    $del = Invoke-RestMethod "$BaseUrl/scan/delete" -Method Post -ContentType 'application/json' -Body $delBody -ErrorAction Stop
    Check ($del.files_deleted -eq 1) "1 file deleted (got $($del.files_deleted))"
    $left = @(Get-ChildItem $dir -File).Count
    Check ($left -eq 2) "2 files remain on disk (got $left); the duplicate went to the Recycle Bin"
}
catch {
    Write-Host "FAIL  exception: $($_.Exception.Message)" -ForegroundColor Red
    $script:failed = $true
}
finally {
    Remove-Item $dir -Recurse -Force -ErrorAction SilentlyContinue
}

if ($script:failed) { Write-Host 'SMOKE TEST FAILED' -ForegroundColor Red; exit 1 }
Write-Host 'SMOKE TEST PASSED' -ForegroundColor Green
exit 0