$root = 'C:\projects\PRISM'
$be   = Join-Path $root 'backend'
$venv = Join-Path $be 'venv-release'
$py   = Join-Path $venv 'Scripts\python.exe'
$req  = Join-Path $be 'requirements-release.txt'
$bin  = Join-Path $root 'src-tauri\binaries'
$out  = Join-Path $bin 'prism-backend-x86_64-pc-windows-msvc.exe'

function Fail([string]$msg) { Write-Host "BUILD FAILED: $msg" -ForegroundColor Red; exit 1 }

if (-not (Test-Path $req)) { Fail "missing $req" }

# 1. clean release venv with only the runtime packages
Write-Host '== 1/5 release venv ==' -ForegroundColor Cyan
if (-not (Test-Path $py)) {
    python -m venv $venv
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $py)) { Fail 'could not create venv-release' }
}
& $py -m pip install --quiet --disable-pip-version-check -r $req
if ($LASTEXITCODE -ne 0) { Fail 'pip install of requirements-release.txt failed' }
& $py -m pip install --quiet --disable-pip-version-check pyinstaller
if ($LASTEXITCODE -ne 0) { Fail 'pip install pyinstaller failed (if it names Python 3.14, use the 3.13 fallback from the chat)' }

# 2. import gate: the backend must import using ONLY the release packages
Write-Host '== 2/5 import check ==' -ForegroundColor Cyan
$env:PRISM_DATA_DIR = Join-Path $env:TEMP 'prism_build_data'
& $py -c "import sys; sys.path.insert(0, r'$be\app'); import main; print('import check OK')"
if ($LASTEXITCODE -ne 0) { Fail 'backend does not import in the release venv: a package is missing from requirements-release.txt (see the error above)' }

# 3. freeze
Write-Host '== 3/5 PyInstaller (this takes a few minutes) ==' -ForegroundColor Cyan
$piArgs = @(
    '--noconfirm', '--clean', '--log-level', 'WARN',
    '--onefile', '--noconsole', '--name', 'prism-backend',
    '--paths', "$be\app",
    '--collect-submodules', 'uvicorn',
    '--collect-submodules', 'anyio',
    '--collect-submodules', 'send2trash',
    '--exclude-module', 'torch', '--exclude-module', 'torchvision', '--exclude-module', 'open_clip',
    '--exclude-module', 'scipy', '--exclude-module', 'numpy', '--exclude-module', 'tkinter',
    '--distpath', "$be\dist", '--workpath', "$be\build", '--specpath', "$be\build"
)
Push-Location $be
& $py -m PyInstaller @piArgs "$be\app\main.py"
$piCode = $LASTEXITCODE
Pop-Location
if ($piCode -ne 0) { Fail 'PyInstaller failed' }
if (-not (Test-Path "$be\dist\prism-backend.exe")) { Fail 'PyInstaller produced no exe (antivirus may have quarantined it)' }

# 4. copy where Tauri expects it
Write-Host '== 4/5 copy sidecar ==' -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path $bin | Out-Null
Copy-Item "$be\dist\prism-backend.exe" $out -Force -ErrorAction Stop

# 5. smoke-test the frozen exe exactly as Tauri will launch it
Write-Host '== 5/5 smoke test of the frozen exe ==' -ForegroundColor Cyan
$env:PRISM_DATA_DIR = Join-Path $env:TEMP 'prism_smoke_data'
if (Test-Path $env:PRISM_DATA_DIR) { Remove-Item $env:PRISM_DATA_DIR -Recurse -Force }
$port = 8765
$p = Start-Process -FilePath $out -ArgumentList '--port', "$port", '--parent-pid', "$PID" -PassThru -WindowStyle Hidden
$smokeCode = 2
try {
    $up = $false
    for ($i = 0; $i -lt 40; $i++) {
        Start-Sleep -Milliseconds 750
        try { $null = Invoke-RestMethod "http://127.0.0.1:$port/health" -TimeoutSec 2 -ErrorAction Stop; $up = $true; break } catch {}
    }
    if ($up) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File "$root\scripts\smoke-test.ps1" -BaseUrl "http://127.0.0.1:$port" -PythonExe $py
        $smokeCode = $LASTEXITCODE
    } else {
        Write-Host 'Backend did not answer /health within 30 seconds' -ForegroundColor Red
    }
} finally {
    taskkill /PID $p.Id /T /F | Out-Null
}

$log = Join-Path $env:PRISM_DATA_DIR 'backend.log'
if (Test-Path $log) { Write-Host '--- backend.log (last 8 lines) ---'; Get-Content $log -Tail 8 }
if ($smokeCode -ne 0) { Fail "frozen backend failed the smoke test (code $smokeCode)" }
$mb = [math]::Round((Get-Item $out).Length / 1MB, 1)
Write-Host "BUILD OK: $out ($mb MB)" -ForegroundColor Green