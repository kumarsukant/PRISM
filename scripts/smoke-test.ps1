param(
    [string]$BaseUrl = 'http://127.0.0.1:8000',
    [string]$PythonExe = 'C:\projects\PRISM\backend\venv\Scripts\python.exe'
)
$script:failed = $false
function Check([bool]$cond, [string]$msg) {
    if ($cond) { Write-Host "PASS  $msg" -ForegroundColor Green }
    else { Write-Host "FAIL  $msg" -ForegroundColor Red; $script:failed = $true }
}
function Get-HttpStatus([scriptblock]$call) {
    try { $null = & $call; return 200 }
    catch { if ($_.Exception.Response) { return [int]$_.Exception.Response.StatusCode } else { return -1 } }
}

$dir = Join-Path $env:TEMP ('prism_smoke_' + [guid]::NewGuid().ToString('N').Substring(0, 8))
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$mk = "import os, sys; from PIL import Image; d = sys.argv[1]; [Image.frombytes('RGB', (128, 128), os.urandom(128*128*3)).save(os.path.join(d, n)) for n in ('a.png', 'c.png', 'd.png')]"
& $PythonExe -c $mk $dir
Copy-Item (Join-Path $dir 'a.png') (Join-Path $dir 'b.png')
$lockedPath = Join-Path $dir 'd.png'
$lock = $null

try {
    $health = Invoke-RestMethod "$BaseUrl/health" -TimeoutSec 5 -ErrorAction Stop
    Check ($health.status -eq 'ok') '/health returns ok'

    $stats = Invoke-RestMethod "$BaseUrl/stats" -TimeoutSec 5 -ErrorAction Stop
    Check ($null -ne $stats.completed_scans) '/stats responds'

    $badBody = @{ folder_path = 'C:\this\folder\does\not\exist' } | ConvertTo-Json
    $code = Get-HttpStatus { Invoke-RestMethod "$BaseUrl/scan/start" -Method Post -ContentType 'application/json' -Body $badBody -TimeoutSec 10 -ErrorAction Stop }
    Check ($code -eq 400) "nonexistent folder is rejected with 400 (got $code)"

    $code = Get-HttpStatus { Invoke-RestMethod "$BaseUrl/scan/progress?scan_id=does-not-exist" -TimeoutSec 10 -ErrorAction Stop }
    Check ($code -eq 404) "unknown scan id returns 404 (got $code)"

    # d.png is held open with no sharing for the whole scan, so the scanner cannot read it
    $lock = [System.IO.File]::Open($lockedPath, 'Open', 'Read', 'None')

    $body = @{ folder_path = $dir } | ConvertTo-Json
    $start = Invoke-RestMethod "$BaseUrl/scan/start" -Method Post -ContentType 'application/json' -Body $body -TimeoutSec 10 -ErrorAction Stop
    Check (($start.status -eq 'started') -and $start.scan_id) '/scan/start returns "started" and a scan_id immediately'

    $deadline = (Get-Date).AddSeconds(120)
    do {
        Start-Sleep -Milliseconds 300
        $prog = Invoke-RestMethod "$BaseUrl/scan/progress?scan_id=$($start.scan_id)" -TimeoutSec 10 -ErrorAction Stop
    } while ($prog.status -eq 'in_progress' -and (Get-Date) -lt $deadline)

    $lock.Close(); $lock = $null
    Remove-Item $lockedPath -Force   # keep the folder at a, b, c for the delete checks below

    Check (($prog.status -eq 'completed') -and ($prog.phase -eq 'completed')) "scan completes (status=$($prog.status), phase=$($prog.phase))"
    Check ($prog.total_photos -eq 3) "scan found 3 photos (got $($prog.total_photos))"
    Check ($prog.skipped_count -eq 1) "1 unreadable file reported as skipped (got $($prog.skipped_count))"
    $skip = @($prog.skipped)[0]
    Check (($skip.file -eq 'd.png') -and ($skip.reason -eq 'open in another program')) "skipped file is d.png, reason 'open in another program' (got '$($skip.file)', '$($skip.reason)')"
    Check ($prog.exact_duplicates -eq 1) "1 exact duplicate (got $($prog.exact_duplicates))"
    Check ($prog.visual_duplicates -eq 0) "0 visual duplicates (got $($prog.visual_duplicates))"
    Check ($prog.duplicate_groups -eq 1) "1 duplicate group (got $($prog.duplicate_groups))"

    $res = Invoke-RestMethod "$BaseUrl/scan/results?scan_id=$($start.scan_id)" -ErrorAction Stop
    $group = $res.groups[0]
    Check (@($group.photos).Count -eq 2) 'group has 2 photos'

    $img = $group.photos[0].file_path
    $thumb = Invoke-WebRequest -UseBasicParsing ("$BaseUrl/thumbnail?path=" + [uri]::EscapeDataString($img)) -ErrorAction Stop
    Check (($thumb.StatusCode -eq 200) -and (([string]$thumb.Headers['Content-Type']) -like 'image/jpeg*')) '/thumbnail returns a JPEG'

    $delBody = @{ scan_id = $start.scan_id; group_ids = @($group.id) } | ConvertTo-Json
    $del = Invoke-RestMethod "$BaseUrl/scan/delete" -Method Post -ContentType 'application/json' -Body $delBody -ErrorAction Stop
    Check ($del.files_deleted -eq 1) "1 file deleted (got $($del.files_deleted))"
    $left = @(Get-ChildItem $dir -File).Count
    Check ($left -eq 2) "2 files remain on disk (got $left); the duplicate went to the Recycle Bin"
    Check (($del.duplicate_groups -eq 0) -and ($del.total_photos -eq 2)) "delete response carries the updated counts (groups=$($del.duplicate_groups), photos=$($del.total_photos))"
    $res2 = Invoke-RestMethod "$BaseUrl/scan/results?scan_id=$($start.scan_id)" -ErrorAction Stop
    Check (@($res2.groups).Count -eq 0) 'the deleted group is gone from /scan/results'
    $del2 = Invoke-RestMethod "$BaseUrl/scan/delete" -Method Post -ContentType 'application/json' -Body $delBody -ErrorAction Stop
    Check ($del2.files_deleted -eq 0) 'deleting the same group again removes nothing'

    # Nothing is locked any more: a fresh scan of the same folder must report no skipped files
    $start2 = Invoke-RestMethod "$BaseUrl/scan/start" -Method Post -ContentType 'application/json' -Body $body -TimeoutSec 10 -ErrorAction Stop
    $deadline = (Get-Date).AddSeconds(120)
    do {
        Start-Sleep -Milliseconds 300
        $prog2 = Invoke-RestMethod "$BaseUrl/scan/progress?scan_id=$($start2.scan_id)" -TimeoutSec 10 -ErrorAction Stop
    } while ($prog2.status -eq 'in_progress' -and (Get-Date) -lt $deadline)
    Check (($prog2.status -eq 'completed') -and ($prog2.skipped_count -eq 0) -and (@($prog2.skipped).Count -eq 0)) "clean rescan reports 0 skipped (status=$($prog2.status), skipped_count=$($prog2.skipped_count))"
}
catch {
    Write-Host "FAIL  exception: $($_.Exception.Message)" -ForegroundColor Red
    $script:failed = $true
}
finally {
    if ($lock) { $lock.Close() }
    Remove-Item $dir -Recurse -Force -ErrorAction SilentlyContinue
}

if ($script:failed) { Write-Host 'SMOKE TEST FAILED' -ForegroundColor Red; exit 1 }
Write-Host 'SMOKE TEST PASSED' -ForegroundColor Green
exit 0