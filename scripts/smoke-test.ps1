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

function Send-Raw([string]$method, [string]$path, [hashtable]$headers, [string]$hostName = '') {
    # HttpWebRequest, because Invoke-RestMethod cannot send a different Host header
    $req = [System.Net.HttpWebRequest]::Create("$BaseUrl$path")
    $req.Method = $method
    $req.Timeout = 10000
    foreach ($k in $headers.Keys) { $req.Headers.Add($k, $headers[$k]) }
    if ($hostName) { $req.Host = $hostName }
    try { $resp = $req.GetResponse() } catch [System.Net.WebException] { $resp = $_.Exception.Response }
    if (-not $resp) { return @{ Status = -1; AllowOrigin = $null } }
    $result = @{ Status = [int]$resp.StatusCode; AllowOrigin = $resp.Headers['Access-Control-Allow-Origin'] }
    $resp.Close()
    return $result
}

$dir = Join-Path $env:TEMP ('prism_smoke_' + [guid]::NewGuid().ToString('N').Substring(0, 8))
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$mk = "import os, sys; from PIL import Image; d = sys.argv[1]; [Image.frombytes('RGB', (128, 128), os.urandom(128*128*3)).save(os.path.join(d, n)) for n in ('a.png', 'c.png', 'd.png')]"
& $PythonExe -c $mk $dir
Copy-Item (Join-Path $dir 'a.png') (Join-Path $dir 'b.png')
$treeDir = Join-Path $env:TEMP ('prism_insights_' + [guid]::NewGuid().ToString('N').Substring(0, 8))
$lockedPath = Join-Path $dir 'd.png'
$lock = $null

try {
    $health = Invoke-RestMethod "$BaseUrl/health" -TimeoutSec 5 -ErrorAction Stop
    Check ($health.status -eq 'ok') '/health returns ok'

    $stats = Invoke-RestMethod "$BaseUrl/stats" -TimeoutSec 5 -ErrorAction Stop
    Check ($null -ne $stats.completed_scans) '/stats responds'

    # Who may call the backend: the app's and dev server's origins only, and only Host 127.0.0.1/localhost
    $evil = Send-Raw 'OPTIONS' '/scan/start' @{ Origin = 'https://example.com'; 'Access-Control-Request-Method' = 'POST' }
    Check (($evil.Status -eq 403) -and (-not $evil.AllowOrigin)) "preflight from https://example.com is refused (got $($evil.Status), allow-origin '$($evil.AllowOrigin)')"
    $okApp = Send-Raw 'OPTIONS' '/scan/start' @{ Origin = 'http://tauri.localhost'; 'Access-Control-Request-Method' = 'POST'; 'Access-Control-Request-Headers' = 'content-type' }
    $okDev = Send-Raw 'OPTIONS' '/scan/start' @{ Origin = 'http://localhost:5173'; 'Access-Control-Request-Method' = 'POST'; 'Access-Control-Request-Headers' = 'content-type' }
    Check (($okApp.Status -eq 200) -and ($okApp.AllowOrigin -eq 'http://tauri.localhost') -and ($okDev.AllowOrigin -eq 'http://localhost:5173')) "preflight from the app (tauri.localhost) and dev server (localhost:5173) is allowed (got $($okApp.Status) '$($okApp.AllowOrigin)', '$($okDev.AllowOrigin)')"
    $evilGet = Send-Raw 'GET' '/health' @{ Origin = 'https://evil.example' }
    Check ($evilGet.Status -eq 403) "a simple GET from another web page is refused (got $($evilGet.Status))"
    $badHost = Send-Raw 'GET' '/health' @{} 'evil.example'
    $okHost = Send-Raw 'GET' '/health' @{} 'localhost'
    Check (($badHost.Status -eq 400) -and ($okHost.Status -eq 200)) "Host evil.example is refused, Host localhost accepted (got $($badHost.Status), $($okHost.Status))"

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

    # --- Insights, on a generated nested tree with known counts (scripts\make-insights-tree.ps1) ---
    $code = Get-HttpStatus { Invoke-RestMethod "$BaseUrl/scan/insights?scan_id=does-not-exist" -TimeoutSec 10 -ErrorAction Stop }
    Check ($code -eq 404) "/scan/insights for an unknown scan returns 404 (got $code)"

    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'make-insights-tree.ps1') -Root $treeDir -PythonExe $PythonExe | Out-Null
    $exp = Get-Content (Join-Path $treeDir '_expected.json') -Raw | ConvertFrom-Json
    $tbody = @{ folder_path = $treeDir } | ConvertTo-Json
    $ts = Invoke-RestMethod "$BaseUrl/scan/start" -Method Post -ContentType 'application/json' -Body $tbody -TimeoutSec 10 -ErrorAction Stop
    $deadline = (Get-Date).AddSeconds(120)
    do {
        Start-Sleep -Milliseconds 300
        $tp = Invoke-RestMethod "$BaseUrl/scan/progress?scan_id=$($ts.scan_id)" -TimeoutSec 10 -ErrorAction Stop
    } while ($tp.status -eq 'in_progress' -and (Get-Date) -lt $deadline)
    $c = $tp.coverage
    Check (($tp.status -eq 'completed') -and ($c.heic_not_checked -eq 1) -and ($c.raw_not_checked -eq 1) -and ($c.under_10kb -eq 1)) "tree scan completes; progress reports 1 HEIC, 1 RAW, 1 under 10 KB not checked (got $($c.heic_not_checked), $($c.raw_not_checked), $($c.under_10kb))"

    $ins = Invoke-RestMethod "$BaseUrl/scan/insights?scan_id=$($ts.scan_id)" -TimeoutSec 10 -ErrorAction Stop
    $keys = 'photos', 'folders', 'folders_with_duplicates', 'duplicate_groups', 'groups_in_one_folder', 'groups_across_folders', 'groups_across_3_plus_folders', 'extra_copies'
    $gotT = ($keys | ForEach-Object { "$_=$($ins.totals.$_)" }) -join ' '
    $wantT = ($keys | ForEach-Object { "$_=$($exp.$_)" }) -join ' '
    Check ($gotT -eq $wantT) "insights totals match the tree ($gotT)"
    $gotF = (@($ins.folders) | ForEach-Object { "$($_.relative_path)|$($_.photos)|$($_.photos_with_duplicate)|$($_.tag)" }) -join '; '
    $wantF = (@($exp.folders_ranked) | ForEach-Object { $_ -join '|' }) -join '; '
    Check ($gotF -eq $wantF) "folders ranked with counts and tags ($gotF)"
    $gotP = (@($ins.pairs) | ForEach-Object { "$($_.a.relative_path)|$($_.b.relative_path)|$($_.shared_groups)" }) -join '; '
    $wantP = (@($exp.pairs) | ForEach-Object { $_ -join '|' }) -join '; '
    Check ($gotP -eq $wantP) "folder pairs, including the 3-folder groups counted once per pair ($gotP)"
    $gotTips = (@($ins.tips) | ForEach-Object { $_.id }) -join ','
    Check ($gotTips -eq ($exp.tips -join ',')) "tips fire as planted ($gotTips)"
    $ck = 'photos_checked', 'folders_checked', 'heic_not_checked', 'raw_not_checked', 'under_10kb', 'online_only', 'unreadable'
    $gotC = ($ck | ForEach-Object { "$_=$($ins.coverage.$_)" }) -join ' '
    Check ($gotC -eq (($ck | ForEach-Object { "$_=$($exp.coverage.$_)" }) -join ' ')) "coverage ($gotC)"
    $h = @($ins.headlines)
    Check (($h[0].folder.relative_path -eq 'Pictures\Camera') -and ($h[1].groups_in_one_folder -eq 12) -and ($h[1].groups_across_folders -eq 12)) 'headlines: top folder Pictures\Camera, 12 groups in one folder, 12 across'

    $camId = @($ins.folders)[0].id
    $fold = Invoke-RestMethod "$BaseUrl/scan/folder?scan_id=$($ts.scan_id)&folder_id=$camId" -TimeoutSec 10 -ErrorAction Stop
    $code = Get-HttpStatus { Invoke-RestMethod "$BaseUrl/scan/folder?scan_id=$($ts.scan_id)&folder_id=000000000000" -TimeoutSec 10 -ErrorAction Stop }
    Check (($fold.path -eq (Join-Path $treeDir 'Pictures\Camera')) -and ($code -eq 404)) "/scan/folder resolves a scanned folder's id, unknown id 404 (got '$($fold.path)', $code)"

    # Delete the 6 same-folder " - Copy" groups in Camera, then insights must recompute
    $tres = Invoke-RestMethod "$BaseUrl/scan/results?scan_id=$($ts.scan_id)" -ErrorAction Stop
    $copyGroups = @($tres.groups | Where-Object { @($_.photos | Where-Object { $_.file_path -like '* - Copy.png' }).Count -gt 0 } | ForEach-Object { $_.id })
    $tdel = @{ scan_id = $ts.scan_id; group_ids = $copyGroups } | ConvertTo-Json
    $null = Invoke-RestMethod "$BaseUrl/scan/delete" -Method Post -ContentType 'application/json' -Body $tdel -ErrorAction Stop
    $ins2 = Invoke-RestMethod "$BaseUrl/scan/insights?scan_id=$($ts.scan_id)" -TimeoutSec 10 -ErrorAction Stop
    $gotTips2 = (@($ins2.tips) | ForEach-Object { $_.id }) -join ','
    $cam2 = @($ins2.folders | Where-Object { $_.relative_path -eq 'Pictures\Camera' })[0]
    Check (($copyGroups.Count -eq 6) -and ($ins2.totals.duplicate_groups -eq $exp.after_deleting_camera_copies.duplicate_groups) -and ($gotTips2 -eq ($exp.after_deleting_camera_copies.tips -join ',')) -and ($cam2.id -eq $camId)) "insights recompute after a delete: groups $($ins2.totals.duplicate_groups), tips $gotTips2, Camera keeps its id"
}
catch {
    Write-Host "FAIL  exception: $($_.Exception.Message)" -ForegroundColor Red
    $script:failed = $true
}
finally {
    if ($lock) { $lock.Close() }
    Remove-Item $dir -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item $treeDir -Recurse -Force -ErrorAction SilentlyContinue
}

if ($script:failed) { Write-Host 'SMOKE TEST FAILED' -ForegroundColor Red; exit 1 }
Write-Host 'SMOKE TEST PASSED' -ForegroundColor Green
exit 0