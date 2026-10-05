# Prism — working instructions for Claude Code

> This file is loaded every session, so it is deliberately short. The full story (history, every decision and its reasoning, incidents, measurements, API contract, backlog) is in `docs/PROJECT_HISTORY.md`.
> **At the start of your first session on this project, read `docs/PROJECT_HISTORY.md` completely**, then work through section 12 of it ("Open verification items"). Afterwards, read it again only when you need background. Do not `@import` it (imports load into context every session and save nothing).
> Last updated: 2026-10-05, in the first Claude Code session (after a long claude.ai chat that covered Checkpoints 4, 5 and most of 6).

## 1. What Prism is

- **Prism** is a desktop duplicate-photo finder. Tagline: "See your photos clearly". Brand: amber `#F59E0B`, Inter font.
- It is a **real product venture**, not a toy. Planned pricing: Free / Pro $4.99 per month / Business $14.99 per month.
- Owner: **Sukant** (GitHub `kumarsukant/PRISM`, branch `main`). Project root: `C:\projects\PRISM`. Windows 11.
- Current version: v0.1 = exact-duplicate detection (MD5). Near-duplicates (perceptual hash) are planned for v0.2. AI/CLIP similarity is deferred to an optional downloadable "AI Pack" (v0.3+).

## 2. Working agreement with the owner

- **The owner has no formal business background.** Explain business, product and operations reasoning step by step in plain language, without assuming prior knowledge. Technical depth is fine.
- Work **one step at a time with validation**: say what you will change, change it, run the checks, report the real output. Say plainly what you verified and what you did not. Never claim a check passed unless you ran it.
- **Never modify or delete files in the owner's real photo libraries**: the external drive `D:\` (about 24,263 photos on a slow USB HDD) and the 24,321-file library used in earlier tests. Test only on generated folders such as `C:\prism_test`.
- Git: one branch per checkpoint (`checkpoint-N-name`), one commit per step, merge to `main` with `--no-ff` and the message `Checkpoint N: ...`, tag `v0.1.X-cpN`. Commit freely on the checkpoint branch. **Ask before** merging to `main`, pushing, tagging, building installers, or uninstalling or installing the app.
- Use a **normal (non-elevated) PowerShell**. Building the MSI from an elevated terminal breaks later builds (see section 7).

## 3. Stack (locked, do not change without asking)

- **Tauri 2.x** (Rust) shell + **React 18 + TypeScript + Tailwind v3** (v3 on purpose; v4 would break the config) + Vite 5.
- **Theme follows the Windows light/dark setting** (since Checkpoint 7): `darkMode: 'media'` in `tailwind.config.js` (it was `'class'` and nothing set the class, so `dark:` styles never showed) and `color-scheme: light dark` on `html` in `src/index.css` (native checkboxes and scrollbars follow too). There is no in-app toggle.
- **FastAPI + Python 3.14.5**, SQLite (planned, not used yet), Pillow, send2trash. IPC is plain HTTP from the React frontend to `127.0.0.1:<port>`.
- The backend ships inside the MSI as a **PyInstaller one-file sidecar** (`prism-backend.exe`). No torch, numpy or scipy in the release build.
- Deletes go to the **Recycle Bin via send2trash only**.

## 4. Layout

```
C:\projects\PRISM
  backend\app\main.py              FastAPI app, scan worker thread, all routes, __main__ (argparse --port --parent-pid)
  backend\app\config.py            Config (data dir from PRISM_DATA_DIR, dev fallback ~/.prism)
  backend\app\models\scan.py       dataclasses: PhotoRecord, DuplicateGroup, ScanSession
  backend\app\services\services.py FolderScanner (records skipped_files), ScanProgress, Deduper (MD5), SafeDeleter, describe_file_error
  backend\tests\test_skipped_files.py  unittest (stdlib): skipped-file reasons, progress cap, delete failure reason
  backend\app\services\deduper.py, services\main.py   DEAD files (old CLIP code / old server copy), safe to delete
  backend\requirements-release.txt pinned runtime deps for the frozen backend (source of truth for releases)
  backend\requirements.txt         STALE, do not trust
  backend\venv                     dev venv (has torch etc., Python 3.14.5)
  backend\venv-release             release venv (git-ignored, created by the build script)
  src\App.tsx                      state machine: starting / folder-select / scanning / results / error
  src\components\                  FolderSelector, ScanningView (live progress), ResultsSummary (one-line strip, status line, skipped-files notice; replaced ScanProgress.tsx), ResultsGrid
  src\services\api.ts              ApiService: dynamic base URL, waitForBackend, polling, thumbnailUrl
  src\types.ts
  src-tauri\src\lib.rs             spawns and kills the sidecar, backend_port command
  src-tauri\tauri.conf.json, Cargo.toml, capabilities\default.json
  src-tauri\binaries\              built sidecar exe (git-ignored)
  scripts\build-backend.ps1, smoke-test.ps1, scan-responsiveness.ps1
  docs\PROJECT_HISTORY.md          full history and reference
  .claude\launch.json              Claude browser-pane dev servers: "frontend" (landing page, :3000), "desktop-ui" (this app's Vite, :5173); machine-specific paths
```

## 5. Commands

```powershell
# Dev: terminal 1 (backend on port 8000; Python does NOT hot-reload, restart after every backend edit)
cd C:\projects\PRISM\backend
venv\Scripts\python.exe app/main.py

# Dev: terminal 2 (set the variable in the SAME terminal as the command)
cd C:\projects\PRISM
$env:VITE_CHOKIDAR_USEPOLLING = "true"
npm run tauri dev

# Checks
npx tsc --noEmit
backend\venv\Scripts\python.exe -m unittest discover -s backend\tests -v               # no backend needed, 7 tests
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\smoke-test.ps1            # needs a backend on :8000, 20 checks
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\scan-responsiveness.ps1 -Folder <folder>   # scan only, never deletes

# Release (ORDER MATTERS: backend first, then the MSI)
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build-backend.ps1   # ends with BUILD OK (about 21 MB exe)
npm run tauri build                                                              # MSI in src-tauri\target\release\bundle\msi\ (about 24.6 MiB)
```

Generate a test folder (100 unique images plus 100 exact copies, so 200 files and 100 groups):

```powershell
$dir = 'C:\prism_test'
if (Test-Path $dir) { Remove-Item $dir -Recurse -Force }
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$mk = "import os, sys, shutil; from PIL import Image; d = sys.argv[1]; [(Image.frombytes('RGB', (300, 300), os.urandom(300*300*3)).save(os.path.join(d, f'img{i:03d}.png')), shutil.copy(os.path.join(d, f'img{i:03d}.png'), os.path.join(d, f'img{i:03d} - Copy.png'))) for i in range(100)]"
& C:\projects\PRISM\backend\venv\Scripts\python.exe -c $mk $dir
```

## 6. Rules that must stay true

- **Never permanently delete.** `send2trash` only, no fallback. Failing loudly beats destroying data. The kept photo of a group is never deleted.
- The scan runs in a **background thread**; `/scan/start` returns immediately. A session's `status` becomes `completed` only after hashing **and** grouping finish. `/scan/results` and `/scan/delete` return 409 until then.
- `/scan/delete` is a **plain `def`** (runs in a worker thread). Do not put long work in `async def` handlers; it blocks `/health` and everything else.
- Keeper choice must be **deterministic**: shortest filename, then oldest creation time, then lowercased path.
- A file the scanner cannot read is **skipped and reported, never silently dropped** (`session.skipped_files`, shown in the results notice). Reasons shown to users come from `describe_file_error` (plain language); raw errors go to the log only.
- **Text contrast is at least 4.5:1 in both themes** (measure, don't eyeball; check light and dark). Amber action buttons (Select Folder, Scan Another Folder, Try Again) are `bg-amber-500 text-amber-950 hover:bg-amber-400` in both themes (6.97 / 8.97); never white text on amber-500/600 (2.15 / 3.19). Checkboxes use `accent-amber-600`.
- Errors shown to users come from the backend's JSON `message` field when present, else `HTTP <status>: <statusText>` (`errorMessage` in `api.ts`); no response at all shows "Prism's background service isn't responding...". Backend error responses should keep returning `{"status": "error", "message": "..."}`.
- Release backend dependencies are **pinned** in `requirements-release.txt`. Anything the backend imports must be in it (the build script has an import gate that catches omissions; the same stage runs `backend/tests` with the release venv, before PyInstaller).
- Backend binds `127.0.0.1` only. In release the port is random and passed by Tauri; the frontend asks Rust via the `backend_port` command. Never hard-code `8000` outside the dev default in `api.ts`.
- Tauri v2 quirks: the dialog plugin needs `tauri_plugin_dialog::init()` in `lib.rs`, `dialog:allow-open` in `capabilities/default.json`, and an EMPTY `plugins` block in `tauri.conf.json`. `fs:*` and `http:*` permissions do not exist in v2. `capabilities` is not valid inside `app.windows[]`. `[lib] name = "app_lib"` stays because `main.rs` calls `app_lib::run()`.

## 7. Windows and PowerShell traps (learned the hard way)

- Write files with `[System.IO.File]::WriteAllText($path, $text, (New-Object System.Text.UTF8Encoding($false)))`. Never `Out-File` (adds a BOM that breaks JSON and Vite). Use absolute paths: .NET methods resolve relative paths against `C:\WINDOWS\system32`.
- Normalize `\r\n` to `\n` before string-matching source files. Use literal here-strings `@' ... '@` for code.
- Git writes progress to stderr, so PowerShell shows normal git output as red `NativeCommandError`. Read the text, not the colour. LF/CRLF warnings are harmless.
- The console renders UTF-8 as cp1252 (a bullet shows as `â€¢`); files are fine.
- No `grep`/`head`: use `Select-String` and `Select-Object -First N`.
- Do not set `$ErrorActionPreference = 'Stop'` around pip, PyInstaller or cargo: their stderr output aborts the script. Check `$LASTEXITCODE` instead.
- **Elevated builds poison the MSI folder.** A `.msi` created from an Administrator terminal carries a High Mandatory Level label; a later non-elevated build then fails with `Access is denied (os error 5)`. Fix: delete `src-tauri\target\release\bundle\msi\*` and `...\release\wix` from an elevated terminal, rebuild from a normal one.
- **Vite `EBUSY` crash** on `src-tauri\target\debug\deps\prism.exe`: set `VITE_CHOKIDAR_USEPOLLING` in the same terminal. A permanent fix (make Vite ignore `src-tauri`) is on the backlog.
- **Vite can serve a stale module** when a file is saved twice in quick succession (its watcher missed the second save): the page then fails with errors like `errorMessage is not defined` even after a full reload. Check what is served (`fetch('/src/services/api.ts')` in the page) and restart the dev server.
- Before building or testing the installed app, make sure no `prism`, `prism-backend`, `python` or `node` process from an earlier run is alive; confirm a process is yours with `Get-CimInstance Win32_Process -Filter "ProcessId=<id>"` before stopping it. Two `python.exe` rows for one venv backend, and two `prism-backend` rows for the installed app, are normal (launcher plus child).
- The same MSI version does not upgrade in place: uninstall the old PRISM (Settings, Apps) before installing a new MSI. The MSI is unsigned, so SmartScreen warns (More info, Run anyway).
- PyInstaller prints a deprecation warning when run as admin (v7 will refuse). Harmless build warnings: pip "Cache entry deserialization failed", `send2trash.mac` submodule, `tzdata` hidden import.

## 8. Current state (2026-10-05)

- `main` holds Checkpoint 6 (merge `2de3458`, tag **`v0.1.2-cp6`**: pagination, in-place delete, stay-on-results banner, summary strip + skipped-files notice) and Checkpoint 7 (merge `8faacf8`, tag **`v0.1.3-cp7`**: dark mode following Windows, contrast fixes, compact delete bar, amber buttons with dark text, amber checkboxes, backend error messages in the UI, unit tests in the build script). Merged 2026-10-05 after the owner's 11-step installed-app test passed.
- **CP6 was never built on its own:** `checkpoint-7-dark-mode` was stacked on `checkpoint-6-pagination`, so one installer built from `e4151b2` tested both, and `v0.1.2-cp6` was verified inside the CP7 installer. `main`'s tree after the CP7 merge is identical to that build.
- The app version is still **0.1.0** in `tauri.conf.json`, `package.json` and `Cargo.toml`, although the tags say 0.1.3 (see next tasks).
- Start each session with `git status` and `git log --oneline -10`.

## 9. Next tasks (in order; confirm the first with the owner)

1. Push `main` and the tags `v0.1.2-cp6` / `v0.1.3-cp7` (ask before each push). No PR is needed any more: CP6 and CP7 are merged locally.
2. Backlog in the owner's chosen order: `/thumbnail` validation against SQLite (survive backend restarts) → perceptual-hash near-duplicates (v0.2, wait for user feedback first) → code signing. Plus: **bump the app version per release** (so a new MSI upgrades in place instead of needing an uninstall), Cancel Scan button, faster hashing on spinning/USB disks, make Vite ignore `src-tauri`, delete the dead files, CORS hardening, HEIC/RAW support. Details in `docs/PROJECT_HISTORY.md` section 11.
