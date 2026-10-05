# Prism — Full Project History and Reference

**Purpose.** This document transfers everything learned and built in a long claude.ai chat between the owner (Sukant) and Claude, so that Claude Code can continue without the owner re-explaining anything. It covers: where the project stood, every decision and why, every change to the code, every incident and fix, test assets and measurements, and the backlog.

**Date of writing:** 2026-10-05. **Covers:** the state at the start of Checkpoint 4 (carried in from an earlier chat that hit its 100-image limit), all of Checkpoint 4, all of Checkpoint 5, and most of Checkpoint 6. **Updated** later on 2026-10-05 after the first Claude Code session (section 6.5; reference sections 4, 5, 7, 8, 10 to 13 brought up to date), and again for Checkpoint 7, dark mode (section 6.6).

**How to read the confidence markers.**
- Facts shown with commit hashes, command output or screenshots in the chat are **confirmed**.
- `[INSTRUCTED]` = the owner was told to run it and later reported "all tests passed", but the exact output was not shown.
- `[VERIFY]` = could not be confirmed from the chat; check with git or the filesystem before relying on it.
- Files marked **(never seen)** were not displayed in the chat, so their contents are unknown to the author: do not assume anything about them without reading them.

---

## Table of contents

1. Product and business context
2. The owner and how to work with him
3. Machine and toolchain facts
4. Architecture and code reference
5. Git history
6. Chronology: what happened, in order
7. Decisions log (with reasoning)
8. Test assets, scripts and measurements
9. Gotchas and lessons
10. Known issues and observations
11. Backlog and roadmap
12. Open verification items (do these first)
13. UI copy reference
14. Dependency appendix
15. Mistakes made during the chat (do not repeat)

---

## 1. Product and business context

- **Prism**: an AI-positioned, privacy-first desktop app that finds duplicate photos and moves the extras to the Recycle Bin. Tagline "See your photos clearly". Brand colour amber `#F59E0B`, font Inter. Window title: "PRISM - See Your Photos Clearly".
- Planned pricing tiers: **Free / Pro $4.99 per month / Business $14.99 per month**. Not implemented in code; there is no licensing, account or payment code.
- It is a **serious product venture**, to be evolved into a production-grade, market-ready application. It is not a toy or a demo.
- **Why "defer visual dedup" was a business decision, not only a technical one** (explained to the owner step by step because he has no business background): installer size is a *conversion cost* (every extra step and megabyte between "click download" and "see value" loses some users); the free tier exists to get people into the product; a feature that has never produced a single result should not drive the size of the installer; exact-match deduplication already delivers demonstrable value (238 groups found on a real 24k library).
- The "AI" in the positioning becomes honest when the optional AI Pack (CLIP via ONNX Runtime) ships (v0.3+). Until then the honest claim is "finds exact and near-identical copies safely".
- Distribution status: only the owner has the MSI. It is **unsigned** (SmartScreen warning). Code signing is the last item on the owner's roadmap; certificates cost money and have lead time, so decide before any public launch.

## 2. The owner and how to work with him

- Name: Sukant. Senior technology and consulting background (IAM/identity security, cloud, managed services; 21+ years). Strong technical depth. **No formal business, entrepreneurship or operations background**: explain those reasoning steps accessibly, step by step, with hand-holding, without assuming prior knowledge. Technical explanations need no hand-holding.
- Based in Bengaluru, India (relevant for India-first go-to-market thinking).
- **Working style he explicitly asked for:** "lets start with just step 0, let me know whats required, we'll do it, you validate everything, then we move to step 1, 2, 3". He found plans that mixed all steps and validations at once confusing ("it adds complexity"). So: one step at a time, give only that step's actions and checks, wait for his output, validate it, then move on.
- He pastes terminal output (and sometimes screenshots) after each step. He reads results carefully and noticed real product issues himself (the back button at the bottom, the single-group selection bug, the locked-file scan gap).
- He reported "all tests passed" a few times without pasting output; accept that for steps marked `[INSTRUCTED]` but note it.
- He likes to be told what comes next and why, and appreciates when the assistant says what it did not verify.
- He is considering moving the build work from claude.ai chat to Claude Code (this document exists for that).

## 3. Machine and toolchain facts

- OS: Windows 11 (PyInstaller reported `Windows-11-10.0.26300-SP0`). Locale/date format on the machine shows `dd-mm-yyyy` (e.g. `04-10-2026`).
- Disks: **C: = internal NVMe SSD (WD SN740, 512 GB)**; **D: = WD My Passport, spinning HDD on USB.** This matters: scanning D:\ (24,263 photos) runs at about 9 to 10 files per second.
- Python **3.14.5** (the only Python installed; `py -0` shows just 3.14). PyInstaller **6.22.3** works on it. If PyInstaller ever fails on 3.14, the documented fallback is to install Python 3.13 and rebuild only `venv-release` with `py -3.13 -m venv backend\venv-release`.
- Node **v24.19.0**, Vite **5.4.21**, Rust **1.99.0**, Cargo **1.99.0**.
- Tauri crate **2.12.1**, tauri-build 2.7.1, tauri-plugin-dialog 2.8.1, tauri-plugin-shell 2.4.0 (added in Checkpoint 4), tauri-plugin-log 2.10.0. Cargo locks "to highest Rust 1.90 compatible versions" (`rust-version = "1.90"`, `edition = "2024"`).
- WiX 3.14: Tauri's automatic download kept timing out, so `wix314-binaries.zip` was downloaded by hand and extracted **directly** into `%LOCALAPPDATA%\tauri\WixTools314` (binaries in that folder, not nested).
- Paths on this machine: project `C:\projects\PRISM` (some tools print `C:\Projects\PRISM`; same folder). User profile `C:\Users\sukan`.
- Installed app (MSI): `C:\Program Files\PRISM\` containing `prism.exe` (11,497,472 bytes), `prism-backend.exe` (22,083,946 bytes) and `Uninstall PRISM.lnk`. Start-menu name "PRISM".
- Runtime data: `%LOCALAPPDATA%\com.kumarsukant.prism\` (contains `backend.log`); thumbnail cache `%TEMP%\prism_thumbs\`; dev backend data dir `~/.prism` (`C:\Users\sukan\.prism`).
- Clean-machine caveat: Tauri needs the **WebView2** runtime (present on Windows 11). The installed app has so far only been tested on this dev machine, which has Python installed. A test on a machine or VM **without** Python is still outstanding (section 12).

## 4. Architecture and code reference

### 4.1 Overview

```
React UI (WebView2)  --HTTP-->  FastAPI on 127.0.0.1:<port>  --->  Pillow / hashlib / send2trash
      ^                                   ^
      |  invoke('backend_port')           |  spawned + killed by Rust
  Tauri (Rust, lib.rs)  -----------------+
```

- **Dev mode:** the owner starts the backend by hand on port **8000**; Rust does not spawn anything (`cfg!(debug_assertions)`); `backend_port` returns 8000.
- **Release mode:** Rust picks a free port (`TcpListener::bind("127.0.0.1:0")`), creates `app_local_data_dir`, spawns the sidecar `prism-backend` with `--port <p> --parent-pid <rust pid>` and env `PRISM_DATA_DIR=<data dir>`, drains its event channel in a spawned task so pipes never fill, stores the `CommandChild` in managed state, and kills it on `RunEvent::Exit`. The frontend calls `invoke('backend_port')` and polls `/health`.
- The Python process also **watches the parent PID** (`_watch_parent`, Windows `OpenProcess(SYNCHRONIZE)` + `WaitForSingleObject`, then `os._exit(0)`) because a PyInstaller one-file exe is a launcher plus a child, and killing only the launcher could orphan the child. Error 87 (process gone) exits immediately; access denied keeps running.
- Scan results live **in memory** (`scan_results: dict[str, ScanSession]`). SQLite is planned but nothing reads or writes it yet (`Config.SQLALCHEMY_DATABASE_URL` exists but is unused).

### 4.2 File map (what each file is, and whether it was seen)

| Path | Role |
|---|---|
| `backend/app/main.py` | FastAPI app, routes, scan worker `_run_scan`, `_setup_std_streams`, `_watch_parent`, `__main__` |
| `backend/app/config.py` | `Config` + `_data_dir()` |
| `backend/app/models/scan.py` | dataclasses |
| `backend/app/models/__init__.py` | `from .scan import PhotoRecord, DuplicateGroup, ScanSession` |
| `backend/app/services/services.py` | `ScanProgress`, `FolderScanner`, `Deduper`, `SafeDeleter`, `describe_file_error`, `_windows_open_error` |
| `backend/tests/test_skipped_files.py` | stdlib `unittest`, 7 tests (added 2026-10-05; see 8) |
| `backend/app/services/__init__.py`, `utils/__init__.py` | docstring only |
| `backend/app/services/deduper.py` | **DEAD**: old CLIP deduper (imports numpy, torch, open_clip); not imported by live code |
| `backend/app/services/main.py` | **DEAD**: an old copy of the server (mentions CLIP); not imported |
| `backend/requirements-release.txt` | pinned runtime dependencies (see 14) |
| `backend/requirements.txt` | **STALE** (lists torch 2.1.1, numpy 1.26.2 etc. that cannot be installed on 3.14) |
| `scripts/build-backend.ps1` | builds the frozen backend (5 stages, below) |
| `scripts/smoke-test.ps1` | 20-check API test (17 until 2026-10-05), parameters `-BaseUrl`, `-PythonExe` |
| `scripts/scan-responsiveness.ps1` | scan-only responsiveness test, `-Folder`, `-BaseUrl` |
| `src/App.tsx` | state machine and screens |
| `src/components/FolderSelector.tsx` | folder picker using the Tauri dialog plugin **(never seen)** |
| `src/components/ScanningView.tsx` | live progress screen (new in CP5) |
| `src/components/ResultsSummary.tsx` | results summary: one-line strip, status line, skipped-files notice. **Replaced `ScanProgress.tsx`** (the old tall card, deleted in `eed8354`) |
| `src/components/ResultsGrid.tsx` | paginated duplicate groups |
| `src/services/api.ts`, `src/types.ts` | API client and types |
| `src/main.tsx`, `src/index.css`, `index.html`, `package.json`, `vite.config.ts`, `tailwind.config.*`, `postcss.config.js`, `tsconfig.json`, `tsconfig.node.json` | **(never seen, except that they exist)**; `vite.config.ts`, both tsconfigs and `postcss.config.js` were created in earlier checkpoints |
| `src-tauri/src/lib.rs`, `main.rs` | `lib.rs` shown (below); `main.rs` calls `app_lib::run()` (never seen) |
| `src-tauri/Cargo.toml`, `tauri.conf.json`, `capabilities/default.json` | shown (below) |
| `src-tauri/binaries/prism-backend-x86_64-pc-windows-msvc.exe` | build output, git-ignored |
| `.gitignore` | see 4.8 |

### 4.3 Backend behaviour (as of the Checkpoint 6 branch)

**main.py**
- Top of file: `_setup_std_streams()` runs before other imports. If `sys.frozen` or stdout/stderr is `None`, stdout and stderr are redirected to `backend.log` in `PRISM_DATA_DIR` (fallback `~/.prism`), line-buffered, UTF-8, appended (truncated if over 5 MB). Otherwise they are reconfigured to UTF-8 (`errors="replace"`). The old code wrapped `sys.stdout.buffer`, which does not exist in a windowed build; that would have crashed on startup.
- `sys.path.insert(0, backend/)` then imports `config`, `models.scan`, `services.services`.
- CORS: `allow_origins=["*"]`, credentials allowed, all methods and headers (see hardening note in 10).
- Globals: `config`, `scanner = FolderScanner(config)`, `deduper = Deduper(config)`, `deleter = SafeDeleter(config)`, `scan_results`.
- `_run_scan(session)` (runs in a daemon thread named `scan-<first 8 chars of id>`): sets `phase="discovering"`, calls `scanner.scan_folder(...)` with a progress callback that updates `session.phase`, `files_processed`, `files_total` and logs every 100 files while hashing; if the scanner failed, sets `phase="failed"` and returns; then `phase="grouping"`, `find_exact_duplicates`, `find_visual_duplicates` (stub), then `phase="completed"` **and** `status="completed"` last. Any exception sets `error_message`, `phase="failed"`, `status="failed"`.
- `__main__`: `multiprocessing.freeze_support()`, argparse (`--port` default 8000, `--parent-pid` default 0), starts `_watch_parent` thread if a pid was given, `uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning" if frozen else "info")`. **Pass the app object, not an import string** (string imports break when frozen).

**Scanner (`FolderScanner`)**
- `os.walk`; accepted extensions: `.jpg .jpeg .png .gif .bmp .webp .tiff`; files under **10 KB are silently skipped**. (`Config.IMAGE_EXTENSIONS` also lists `.heic` and `.raw`, but the scanner uses its own set, so **HEIC and RAW are not scanned**; this matters for phone photo libraries.)
- Discovery reports progress every 200 files found (`phase="discovering"`); when hashing starts it reports `0/N` (`phase="hashing"`).
- Hashing: `ThreadPoolExecutor(max_workers=4)`; `_process_image` reads the file in **4096-byte chunks** for MD5, then opens it with Pillow for width, height, mode (on failure: 0, 0, "unknown"). It returns `(photo, None)` or `(None, reason)`.
- **Skipped files (since `098df1e`, 2026-10-05):** a file that cannot be read (in `getsize` during discovery, or while hashing) is recorded in `session.skipped_files` as `{file, path, reason}`, sorted by path, and logged as `Error processing ...` / `Skipping ...`. Before this, such files were dropped silently. `reason` comes from `describe_file_error(error, action, file_path)`: `"open in another program"` (Windows error 32/33), `"no longer there (moved or deleted)"` (FileNotFoundError, 2/3), `"Windows denied access"` (PermissionError, 5), else `"could not be <read|moved> (<ExceptionName>)"`. Python's `open()` reports a locked file as a bare `PermissionError` with no `winerror`, so on that path `_windows_open_error` calls `CreateFileW` via `ctypes` to ask Windows which it is (32 vs 5). Files under 10 KB and non-image extensions are still filtered without being reported (by design; see 10).
- The scanner no longer sets `status="completed"` itself (that caused a race where a poller could fetch empty results); `_run_scan` does it.

**Deduper**
- `find_exact_duplicates`: groups by MD5; groups of two or more become `DuplicateGroup(group_type="exact", confidence_score=1.0)`. Photos are sorted with `_keeper_sort_key` = `(len(basename), os.path.getctime or inf, path.lower())` and the first is `kept_photo_id`. `exact_duplicates = sum(len(photos) - 1)`.
- `find_visual_duplicates`: stub, sets `visual_duplicates = 0` (planned v0.2: perceptual hash).

**SafeDeleter (Checkpoint 6)**
- `delete_duplicates(session, groups) -> dict` with keys `files_deleted`, `freed_bytes`, `resolved_group_ids`, `failed` (list of `{file, reason}`).
- For each group, the kept photo is never touched. A photo already gone from the session is skipped; a file missing on disk counts as gone (so a group cannot get stuck); otherwise `_delete_file` (send2trash) returns `None` on success or a short error string (max 200 chars).
- A group is removed once at most its kept photo remains. A group with a failed file stays, holding only the photos still on disk, so the user can retry.
- Lists are **replaced, not edited in place** (`session.duplicate_groups`, `session.photos`) so concurrent requests (for example thumbnails) never see a half-edited list. Then `files_deleted`, `storage_freed_mb`, `total_photos`, `exact_duplicates`, `visual_duplicates` are recomputed.

### 4.4 API contract (current)

| Route | Behaviour |
|---|---|
| `GET /health` | `{status:"ok", message:"PRISM backend is running", version:"0.1.0"}` |
| `POST /scan/start` body `{folder_path}` | 400 if missing or not an existing directory; otherwise registers the session immediately, starts the worker thread, returns `{status:"started", scan_id}` |
| `GET /scan/progress?scan_id=` | 404 unknown id; else `{status, phase, scan_id, files_processed, files_total, total_photos, exact_duplicates, visual_duplicates, duplicate_groups, skipped_count, skipped, error_message}`. `skipped` is the first **20** `{file, path, reason}` entries (capped, like delete `failed`); `skipped_count` is the full total (both added in `098df1e`). `status` in_progress/completed/failed/cancelled; `phase` queued/discovering/hashing/grouping/completed/failed. Since CP9 also `coverage: {photos_checked, folders_checked, heic_not_checked, raw_not_checked, under_10kb, online_only, unreadable}` |
| `GET /scan/insights?scan_id=` | (CP9) plain `def`. 404 unknown; 409 not complete; else, computed on demand from the session (so it follows deletes): `{status, scan_id, root, root_name, headlines:[top_folder / split], totals:{photos, folders, folders_with_duplicates, duplicate_groups, groups_in_one_folder, groups_across_folders, groups_across_3_plus_folders, extra_copies, extra_bytes}, folders (top 10):[{id, path, relative_path, photos, photos_with_duplicate, share_with_duplicate, extra_copies, extra_bytes, inside_share, tag}], folders_with_duplicates_not_shown, pairs (top 5):[{a:{id, relative_path}, b, shared_groups}], tips (0-4):[{id, ...numbers}], coverage}`. Definitions in 6.7 and in `services/insights.py` |
| `GET /scan/folder?scan_id=&folder_id=` | (CP9) plain `def`. 404 unknown scan or a folder id that holds no photo of that scan; 409 not complete; else `{status:"ok", path}`. Used only by the app's Rust `open_scan_folder` |
| All routes (CP9) | `Host` must be `127.0.0.1` or `localhost` (any port), else 400. A request with an `Origin` other than `http(s)://tauri.localhost`, `tauri://localhost`, `http(s)://localhost[:port]`, `http(s)://127.0.0.1[:port]` gets 403 (logged once per origin to backend.log); CORS allows only those origins, methods GET/POST, header Content-Type, no credentials. Requests without `Origin` (img thumbnails, Rust, scripts) are unaffected |
| `GET /scan/results?scan_id=` | 404 unknown; **409** until `status == "completed"`; else `{status:"complete", scan_id, total_photos, duplicate_groups, groups:[{id, type, confidence, kept_photo_id, photos:[{id, file_path, file_size_bytes, width, height, is_kept}]}]}` |
| `POST /scan/delete` body `{scan_id, group_ids}` | plain `def` (thread pool). 400 no scan_id; 404 unknown; 409 not complete; else `{status:"success"|"partial", scan_id, files_deleted, storage_freed_mb, groups_resolved, failed (first 20), failed_count, total_photos, exact_duplicates, visual_duplicates, duplicate_groups, message}`. Each `failed` entry is `{file, reason}`; since `098df1e` the reason is plain language from `describe_file_error` (e.g. `"open in another program"`), not the raw `[WinError 32] ... C:\PRISM_~1\...` text |
| `GET /thumbnail?path=` | 403 if the path is not a photo in any scan (the allow-list is rebuilt by iterating every photo of every session **on every request**); 404 missing file; 409 if the file has become online-only (never opened, CP9); 500 on failure; else JPEG. 300 px thumbnail, quality 80, `img.draft("RGB",(600,600))`, cached at `%TEMP%\prism_thumbs\<md5 of normcased path>.jpg` |
| `GET /stats` | `{completed_scans, total_scans_processed, db_path}` (the CLIP fields were removed) |

### 4.5 Data models (`models/scan.py`, dataclasses)

- `PhotoRecord`: `id` (uuid4 str), `file_path`, `file_size_bytes`, `file_hash_md5`, `file_hash_sha256` (unused), `visual_embedding` (unused, for CLIP), `width_px`, `height_px`, `color_space`, `file_format` (unused), `created_date`, `modified_date` (unused), `indexed_at`.
- `DuplicateGroup`: `id`, `group_type` ("exact" or "visual"), `confidence_score`, `photo_ids`, `kept_photo_id`, `created_at`, `user_reviewed`, `user_action`, `deleted_at` (the last three are unused).
- `ScanSession`: `id`, `folder_path`, `started_at`, `completed_at` (never set), `total_photos`, `exact_duplicates`, `visual_duplicates`, `files_deleted`, `storage_freed_mb`, `status`, `error_message`, **`phase`, `files_processed`, `files_total`** (added in CP5), **`skipped_files`** (list of `{file, path, reason}`, added in `098df1e`), **`coverage`** (dict `{heic, raw, under_10kb, online_only, photos_checked, folders_checked}`, CP9), `photos`, `duplicate_groups`.

### 4.6 Frontend behaviour

**State machine (`App.tsx`)**: `starting` → `folder-select` → `scanning` → `results`, plus `error`. Extra state: `scanProgress`, `isDeleting`, `notice` (banner), `clearedByDeleting`.
- `starting`: spinner "Starting Prism..." while `api.waitForBackend()` runs (invokes `backend_port`, polls `/health` every 300 ms, up to 30 s; on timeout shows an error pointing at `backend.log`).
- `handleFolderSelect`: resets progress, notice and `clearedByDeleting`, sets `scanning`, `api.startScan`, `api.waitForScan(scanId, setScanProgress)`, `api.getScanResults`, then builds a `ScanSummary` from the final progress response.
- `waitForScan` polls `/scan/progress` every 400 ms, tolerates up to 5 consecutive failed polls, throws on `failed`/`cancelled` with the backend's `error_message`.
- Errors from `request()` (since `4d59a37`, CP7): a non-OK response throws the backend's JSON `message` if the body has one, else the old `HTTP <status>: <statusText>` (or `HTTP <status>` when there is no status text); a failed `fetch` (no response: backend stopped) throws "Prism's background service isn't responding. Close Prism and open it again." Before, users saw "HTTP 400: Bad Request" for a missing folder and the browser's "Failed to fetch" when the backend was down.
- Theme (since `67868bb`, CP7): follows the Windows setting via `prefers-color-scheme` (`darkMode: 'media'`); `color-scheme: light dark` on `html`.
- `ScanningView`: discovering shows a spinner and "Found N photos so far..." (a count only; the total is unknown); hashing shows percentage, an amber bar, "N of TOTAL photos", a smoothed photos-per-second rate (sampled at least every 1.5 s, smoothing 0.7 old / 0.3 new) and "About Xm Ys left" (only after at least 3 s of hashing); grouping shows a spinner. Footer text: "Large libraries and external drives can take a while. Your photos are never changed during a scan."
- `results` screen: sticky header (title, tagline, **"← Back to Folder Selection"** button at top right), then the delete **notice** banner, then `ResultsSummary`, then `ResultsGrid`, or an "empty" panel when there are no groups. The banner, summary and grid share the `max-w-4xl` column.
- `ResultsSummary` (since `eed8354`, replacing the `ScanProgress` card): a strip with the folder path (truncated, full path on hover) and "N photos · N duplicate groups · N extra copies (X MB)" (extra copies and size computed from the current groups); a status line ("Prism keeps one photo from each group (marked KEPT)..." before any delete, "N groups left to review." after one, nothing when there are no groups because the empty panel explains); and, when `skipped_count > 0`, an amber notice "N photo(s) couldn't be read and was/were skipped, so it isn't / they aren't in these results." with "Close the program that's using it/them, then scan again." when every reason is "open in another program" (else "See why below, then scan again.") and a collapsible "Show file(s)" list (`file: reason`, plus "...and N more" beyond the 20 listed). The notice persists after deletes (those photos were still not scanned) and disappears on a new scan. `ScanSummary` now carries `folder_path`, `skipped_count`, `skipped`.
- `ResultsGrid` (CP6): `PAGE_SIZE = 20`, app-side paging, pager (Previous / "Page X of Y" / Next) above and below the list; "Select this page" (or "Select all" when there is a single page), "Select all N groups" (shown when several pages and not everything is selected), "Clear selection"; selection survives page changes and is pruned when groups disappear; the current page is clamped if the list shrinks; on page change the top of the groups list scrolls into view (`scrollIntoView` with `scroll-mt-28` to clear the sticky header; it compares with the previously shown page instead of skipping the first render, because `main.tsx` uses `React.StrictMode`, which runs effects twice in dev; before `eed8354` it was `window.scrollTo` to the top of the *page*); a pinned (`sticky bottom-4`) delete bar shows count, MB, and "including N on other pages" (since `49c75a2` it is one compact row, 66 px instead of 182 px at 800x600: text on the left, "Delete N Groups" on the right; the text wraps to two short lines inside the button's height when the other-pages note is present). Checkboxes are amber (`accent-amber-600`, since `127cf8e`; before, the Windows accent colour). Each group card shows confidence, "N duplicates • X MB", a KEPT card (green) and DELETE cards (red) with lazy thumbnails. The whole card toggles selection; the checkbox calls the same handler and stops propagation.
- Delete flow (CP6): `handleDeleteDuplicates` calls `api.deleteDuplicates`, then **re-fetches `/scan/results`**, updates the summary counts from the delete response, sets a notice: green "Deleted N files, freed X MB. Moved to the Recycle Bin, so you can restore them."; amber when `failed_count > 0` ("...but K could not be moved to the Recycle Bin." plus up to 5 `file: reason` lines, "...and N more", "Those groups are still listed so you can try again."); red "Could not delete: <message>" on exceptions (the user stays on the results screen). When no groups remain after a cleanup the empty panel says "All duplicates cleared. Nice and tidy!" with a **Scan Another Folder** button; with zero groups straight after a scan it says "No duplicates found! Your photos are all unique."

### 4.7 Tauri / Rust

- `lib.rs` (current): imports `std::net::TcpListener`, `Mutex`, `tauri::{Manager, RunEvent}`, `tauri_plugin_shell::{process::CommandChild, ShellExt}`. Managed state `BackendPort(u16)` and `BackendChild(Mutex<Option<CommandChild>>)`; command `backend_port`; `free_port()`; `run()` builds the app with plugins dialog and shell, registers the command, `setup` as described in 4.1 (plus `tauri_plugin_log` in debug builds at level Info); after `.build(...)` it runs `app.run(|handle, event| ...)` and kills the child on `RunEvent::Exit`.
- `tauri.conf.json`: productName `PRISM`, version `0.1.0`, identifier `com.kumarsukant.prism`; build `frontendDist ../dist`, `devUrl http://localhost:5173`, `beforeDevCommand "npm run dev"`, `beforeBuildCommand "npm run build"` (= `tsc -b && vite build`); one window 800x600, resizable, `csp: null`; `plugins: {}` (must stay empty); bundle `active: true`, `targets: ["msi"]` (NSIS disabled because its download kept timing out), `externalBin: ["binaries/prism-backend"]`, icons list, `android.debugApplicationIdSuffix ".debug"`.
- `capabilities/default.json`: identifier `default`, `windows: ["main"]`, permissions `["dialog:allow-open"]`. No capability is needed for the sidecar because Rust spawns it, not JavaScript.
- `Cargo.toml`: package `prism` 0.1.0, authors `["Prism by Sukant"]`, `[lib] name = "app_lib"`, `crate-type = ["staticlib","cdylib","rlib"]`; deps serde_json, serde (derive), log, tauri 2.12.1, tauri-plugin-log 2, tauri-plugin-dialog 2, **tauri-plugin-shell 2**.

### 4.8 Build script and `.gitignore`

`scripts/build-backend.ps1` stages: (1) create `backend\venv-release` if missing, `pip install -r requirements-release.txt`, install PyInstaller; (2) **import gate**: import `main` with the release venv (with `PRISM_DATA_DIR` set to a temp folder) so a missing package fails here; (3) PyInstaller `--noconfirm --clean --log-level WARN --onefile --noconsole --name prism-backend --paths backend\app --collect-submodules uvicorn --collect-submodules anyio --collect-submodules send2trash --exclude-module torch/torchvision/open_clip/scipy/numpy/tkinter` with dist/work/spec paths under `backend\`; (4) copy to `src-tauri\binaries\prism-backend-x86_64-pc-windows-msvc.exe` (Tauri requires the target-triple suffix; it strips it when bundling, so the installed name is `prism-backend.exe`); (5) start the exe on port **8765** with `--parent-pid $PID` and a temp `PRISM_DATA_DIR`, wait up to about 30 s for `/health`, run `smoke-test.ps1` against it with `-PythonExe` set to the release venv's python, kill the process tree with `taskkill /T /F`, print the last lines of `backend.log`, and finish with `BUILD OK: <path> (<MB>)`.

`.gitignore` highlights: `.env*`, Python caches, `venv/`, `build/`, `dist/`, `node_modules/`, IDE folders, `*.db`, `*.sqlite*`, `logs/`, `*.log`, `uploads/ media/ photos/`, `src-tauri/target/`, plus (added in CP4) `backend/build/`, `backend/dist/`, `backend/venv-release/`, `src-tauri/binaries/`, and (instructed in CP5) `*.tsbuildinfo`. Note `lib/` is ignored (with an exception `!frontend/lib/`), which would catch a `src/lib` folder if one is ever created.

## 5. Git history

Repository `https://github.com/kumarsukant/PRISM`. Line endings: Git converts LF to CRLF on this machine ("LF will be replaced by CRLF" warnings); harmless. PowerShell shows every git message as a red `NativeCommandError`.

**Before this chat (Checkpoints 1 to 3), oldest first (as far as known):**
- `e256966 feat: add thumbnail previews to results grid`
- `f28c462 build: add tsconfig and vite config, fix type errors, produce release exe`
- `7842de0 build: rename binary to prism, set metadata, produce MSI installer`
- `4234c80 chore: explicitly ignore Rust build artifacts` (this was `main` when Checkpoint 4 started)

**Checkpoint 4, branch `checkpoint-4-packaging` (7 commits; confirmed):**
1. `4a2d711 refactor: remove CLIP from backend, add port/parent-pid args and windowed-safe logging`
2. `471d33c build: add PyInstaller sidecar build script and pinned release requirements`
3. `f593625 feat: launch backend as Tauri sidecar on a free port`
4. `dda3ef8 feat: frontend resolves backend port at startup and waits for health`
5. `d79831c fix: thumbnails use dynamic backend URL`
6. `f935eb1 fix: group checkbox toggles selection, delete bar stays pinned`
7. `68e95de fix: deterministic keeper selection (shortest name, oldest, then path)`
- Merge: **`495de33 Checkpoint 4: package backend as Tauri sidecar, defer visual dedup to v0.2`**, tag **`v0.1.0-cp4`**, pushed.

**Checkpoint 5, branch `checkpoint-5-async-scan` (all confirmed from `git log` on 2026-10-05):**
1. `53a5bb2 feat: run scans in a background thread with phase and progress reporting`
2. `ccd11fc test: async smoke test and scan responsiveness script`
3. `0fe953b feat: poll scan progress and show a live progress screen`
4. `464233d feat: sticky results header with back-to-folder button`
5. `8d5de94 chore: stop tracking TypeScript build cache`
- Merge: **`902187a Checkpoint 5: asynchronous scanning with live progress screen`**, tag **`v0.1.1-cp5`**, pushed (`495de33..902187a`).

**Checkpoint 6, branch `checkpoint-6-pagination` (created from `902187a`; not merged; all confirmed from `git log` on 2026-10-05):**
1. `f6366e7 feat: paginate results grid with page-level and all-groups selection`
2. `b6dc3c3 feat: delete updates the scan in place, reports failures, runs off the event loop`
3. `deb52da test: smoke test covers in-place delete behaviour` (the 17-check smoke test)
4. `e87697c feat: stay on results after deleting, with a confirmation or warning banner`
5. `2fe436e docs: add Claude Code handoff` (this document and `CLAUDE.md`)

Added in the first Claude Code session (2026-10-05; see 6.5):

6. `2a6d46f docs: replace verification markers with confirmed commit hashes`
7. `098df1e feat: report files the scanner could not read, with plain-language reasons` (backend, `/scan/progress` fields, delete-failure wording, smoke test 17 → 19)
8. `3415415 docs: smoke test now has 19 checks`
9. `eed8354 feat: summary strip with skipped-files notice replaces the scan-complete card` (6 files: `App.tsx`, `FolderSelector.tsx`, `ResultsGrid.tsx`, `ResultsSummary.tsx` added, `ScanProgress.tsx` deleted, `types.ts`)
10. `6666c15 chore: add desktop UI dev server to the browser-pane launch config` (`.claude/launch.json` only)
11. `5c4611d test: unit tests for skipped files; smoke test checks a clean rescan reports 0 skipped` (smoke test 19 → 20)
12. the commit that adds this update to the docs (`docs: ...`; see `git log`)

The branch itself has not been pushed (its commits reached GitHub through the CP7 branch, below).

**Checkpoint 7, branch `checkpoint-7-dark-mode` — STACKED on `checkpoint-6-pagination`, not on `main`** (owner's choice on 2026-10-05: `main` was still at CP5 and lacked the CP6 screens dark mode had to cover; fixes made on `main` would have conflicted with CP6). See 6.6.
1. `67868bb feat: follow the Windows light/dark setting (darkMode media, color-scheme)` — pushed to `origin/checkpoint-7-dark-mode` (this push also put the CP6 commits on GitHub)
2. `9ab5ca9 fix: dark-mode contrast on the Select Folder button and scanning footer`
3. `49c75a2 feat: compact the pinned delete bar to one row`
4. `edcbd1a fix: amber buttons use dark text on the bright brand amber (light and dark)`
5. `127cf8e feat: amber checkboxes (accent-amber-600)`
6. `4d59a37 feat: show the backend's own error message instead of only the HTTP status`
7. `b223774 build: run the backend unit tests in the import-gate stage, before PyInstaller`
8. the commit that adds this update to the docs (`docs: ...`; see `git log`)

Merges (2026-10-05, after the owner's 11-step installed-app test passed):
- **`2de3458 Checkpoint 6: pagination, in-place delete, skipped-files report`**, tag **`v0.1.2-cp6`**.
- **`8faacf8 Checkpoint 7: dark mode follows Windows, polish`**, tag **`v0.1.3-cp7`**.
- **CP6 was tested inside the CP7 installer.** No separate CP6 exe or MSI was built: the one installer was built from `checkpoint-7-dark-mode` @ `e4151b2`, which contains every CP6 commit, and `main`'s tree after the CP7 merge is identical to it (`git diff e4151b2 8faacf8` is empty). The tag `v0.1.2-cp6` marks the code, not a separately tested installer.
- Followed on `main` by the commit that adds this update to the docs (`docs: ...`; see `git log`).

**Checkpoint 8, branch `checkpoint-8-version-bump`** (from `main` `3e9f885`; not merged): app version 0.1.0 → 0.2.0 → 0.1.4 and the "Releasing" section; see that branch's docs.

**Checkpoint 9, branch `checkpoint-9-insights`** (from `main` `3e9f885`; not merged, not pushed; see 6.7):
1. `baaff97 docs: backlog the Reorganizer as a later, not-started item`
2. `54de0fa feat: scan .tif files (only .tiff was recognised; .tif photos were silently ignored)`
3. `37d9f05 feat: scan insights endpoint, coverage counters, never open online-only (cloud) files`
4. `0885fad test: insights definitions, thresholds, tips, recompute after delete, 25k-photo timing, online-only never opened`
5. `5c087da test: nested insights test tree generator; smoke test checks /scan/insights and /scan/folder (20 -> 30 checks)`
6. `e27a001 feat: Insights and Review duplicates tabs; Insights panel with headline, folders, pairs, tips and coverage`
7. `fb83fcd feat: Open folder via the app's Rust side; backend accepts only the app's origins and loopback Host names`
8. the commit that adds this update to the docs (`docs: ...`; see `git log`)

## 6. Chronology: what happened, in order

### 6.0 State when this chat began (carried over from the previous chat)

- Checkpoint 3 complete. Full flow validated: folder picker → scan → thumbnail review → select groups → delete to Recycle Bin. Tested on a **24,321-file library: 238 duplicate groups found and deleted, all recoverable from the Recycle Bin.** Release `prism.exe` 9 MB; `PRISM_0.1.0_x64_en-US.msi` 3 MB; installs, launches from the Start menu, full flow worked from the installed copy.
- Problem: the installed app needed the Python backend started by hand, so it was not distributable. Task: package the backend.
- Already fixed in earlier checkpoints (do not re-debug): Tauri v2 dialog plugin needed three separate things (see CLAUDE.md section 6); Tailwind was inert until `postcss.config.js` was created and autoprefixer installed (Tailwind pinned to v3); `/scan/delete` used query params while the frontend sent a JSON body (silent 422; now takes `request_data: dict`); the Delete button had no `onClick`; `SafeDeleter._delete_file` was **permanently deleting** files (tried win32com, swallowed the ImportError in a bare `except`, fell through to `Remove-Item -Force`, returned True) while the UI promised Recycle Bin recovery, replaced by send2trash with no permanent-delete fallback; missing `tsconfig.json`, `tsconfig.node.json`, `vite.config.ts` created (`noUnusedLocals`/`noUnusedParameters` false on purpose); first-ever `tsc` run found a duplicate `Loader2` import and a dead comparison in `App.tsx`; build config (`frontendDist "../dist"`, identifier, Cargo package renamed `app` → `prism`, authors); WiX manual download.
- Backlog at that time (all "non-blocking"): CLIP doubly broken (random weights because `No pretrained weights loaded for model 'ViT-B-32'`, **and** `open_clip has no attribute 'set_model_to_eval'`), CLIP reloads every scan, non-deterministic keep/delete choice, synchronous `/scan/start`, no pagination or filtering, per-file progress logging overhead (24,321 console writes), `/thumbnail` validating against in-memory results, unsigned MSI, unpinned Send2Trash, NSIS bundling disabled.

### 6.1 Checkpoint 4: packaging the backend

**The decision (before any code).** The owner asked whether visual dedup should stay. Reasoning given: it had never produced a result; fixing it needs two fixes together (the attribute **and** real weights); it needs torch + open_clip (a CPU build likely means a several-hundred-MB installer and over 1 GB unpacked; later `pip freeze` showed `torch==2.14.1+cpu`, which does have a Python 3.14 wheel, so compatibility was not the blocker); CLIP measures *semantic* similarity ("same scene"), which is the wrong tool for deleting near-duplicates (two different beach photos could match); most real near-duplicates (WhatsApp-compressed copies, resized exports) are caught by a **perceptual hash (dHash)**, about 10 lines of Pillow + numpy. **Chosen ladder:** v0.1 exact MD5 → v0.2 perceptual-hash near-duplicates → v0.3+ CLIP via **ONNX Runtime** as an optional downloaded "AI Pack" (roughly 90 to 350 MB, only for users who opt in). The owner agreed ("lets do it").

**Packaging design.** PyInstaller one-file sidecar + Tauri `externalBin` + `tauri-plugin-shell`; random free port; app data dir via env var; parent-PID watcher; log file; frontend waits for `/health`. (one-file chosen because Tauri's `externalBin` wants a single binary; onedir would need `bundle.resources`; one-file costs about 1 to 3 s cold start.)

**Process lesson that shaped everything after:** the first plan gave all steps and validations at once; the owner asked to go one step at a time with validation. From then on each step had Actions plus "what a pass looks like", and the assistant validated the pasted output before continuing.

**Steps and findings.**
- *Step 0:* branch `checkpoint-4-packaging` (clean tree), `.gitignore` additions, files collected. Findings from the owner's output: `ResultsGrid.tsx` hard-coded `http://127.0.0.1:8000` on two lines (143 and 171); `models/scan.py` imports only the standard library; dead files `services/deduper.py` and `services/main.py` exist; `requirements.txt` is stale.
- *Step 1 (backend patch):* new `_setup_std_streams`, argparse, `_watch_parent`, `Deduper` (CLIP removed), `config.py` rewritten for `PRISM_DATA_DIR`, progress logging throttled to every 100 files. Validated with `py_compile`, a case-sensitive grep that must print nothing, an in-venv `import main`, and the first **smoke test (10 checks)** against the dev backend. (A first grep run showed the *unpatched* code because the patch had not been run yet; a second run showed the same, until the owner ran it.) Commit `4a2d711`.
- *Step 2 (frozen backend):* `requirements-release.txt` pinned from the working venv minus torch/numpy/scipy/timm/open_clip/huggingface_hub etc.; `build-backend.ps1` created. First build: PyInstaller 6.22.3 on Python 3.14.5 worked; **BUILD OK, 21.1 MB**; the frozen exe passed the smoke test. Warnings were harmless (section 7). Commit `471d33c`.
- *Step 3 (Tauri):* Cargo.toml, tauri.conf.json, `lib.rs` patched; `cargo check` downloaded 14 new crates and finished; commit `f593625` (Cargo.lock included).
- *Step 4 (frontend):* `api.ts` `baseUrl` + `waitForBackend` + `thumbnailUrl`; `App.tsx` `starting` state; `tsc` clean; commit `dda3ef8`.
- *Step 5:* `ResultsGrid.tsx` thumbnails switched to `api.thumbnailUrl`; commit `d79831c`.
- *Step 6 (dev regression):* first `npm run tauri dev` crashed with Vite `EBUSY ... target\debug\deps\prism.exe` (Vite's watcher vs Cargo rewriting the exe during the first rebuild); fixed by setting `VITE_CHOKIDAR_USEPOLLING` in the same terminal; leftover processes were identified from their command lines before being stopped; the dev flow then passed (folder picker, thumbnails, 3 of 5 files remained after deleting 2, files in the Recycle Bin).
- *Step 7 (MSI):* first MSI build failed at WiX `light` with `Access is denied. (os error 5)`; `icacls` showed the old MSI carried `Mandatory Label\High Mandatory Level:(I)(NW)` (created by an earlier **elevated** build) and the terminal was elevated (`IsInRole(Administrator)` printed True). Fix: delete `bundle\msi\*` and `release\wix` from the elevated terminal, rebuild from a **non-elevated** terminal. Result: **MSI 24.64 MiB**.
- *Step 8 (install):* uninstalled the old PRISM, installed the new MSI. Verified: `C:\Program Files\PRISM` holds `prism.exe` and `prism-backend.exe`; launching from the Start menu started the sidecar (two `prism-backend` processes one second after `prism`); it listened on `127.0.0.1` at a random port (52042 in one check, never 8000); `backend.log` existed and showed a real scan (8 images, 3 duplicate groups).
- *Step 9/10 (functional tests on the installed app):* thumbnails visible; 2 files deleted to the Recycle Bin (3 remained); **closing the window left no `prism` or `prism-backend` process** (the key leak check); **two instances at once** each worked independently on its own port; the **24k scan completed** and showed results (the owner did not time it).
- *Bugs the owner found by using the installed app:* (1) "when I select only one for deletion it's not happening": the group checkbox had an empty `onChange` and `stopPropagation()`, so clicking the checkbox did nothing (clicking elsewhere on the card worked), and the Delete bar sat at the very bottom of a long page; fixed (checkbox now toggles, delete bar `sticky bottom-4`), commit `f935eb1`. (2) The KEPT file flipped between runs (the installed test kept `sunset - Copy.png` and deleted `sunset.png`); fixed with the deterministic sort key, commit `68e95de`, verified with a 5-run test over 30 pairs (`kept_copies=0` every run, `KEEPER TEST PASSED`) and the smoke test.
- *Rebuild and merge:* exe then MSI rebuilt (timestamps checked: MSI newer than exe), reinstalled, five checks passed (30 groups, thumbnails, `remaining: 30 copies still present: 0`, clean shutdown). Merged with `--no-ff` as `495de33`, tag `v0.1.0-cp4`, pushed.
- *Result:* a 3 MB MSI that needed manual Python became a self-contained 24.6 MB installer.

### 6.2 Checkpoint 5: asynchronous scanning

**Why.** `/scan/start` blocked until the entire scan finished, so the window looked frozen for the whole scan; worse, `async def` with inline blocking work freezes the whole server (even `/health`). Chosen as backlog item 1 because it is the first thing a real user hits.

**Design.** Start the scan in a background thread, return immediately, poll `/scan/progress`, show a real progress screen. Findings that shaped it: the scanner marked the session `completed` after hashing but before grouping (a poller would have fetched empty results); the session was only registered in `scan_results` at the very end (progress would have 404'd); a nonexistent folder returned "0 photos" instead of an error.

**Steps and findings.**
- *Step 0:* branch `checkpoint-5-async-scan` from `495de33` (after `git pull`), six files collected. Observation: `ScanProgress.tsx` is the **results summary card** with an effect that sets `isComplete` immediately; it was never a progress display, so the live progress screen got a new component name, `ScanningView`.
- *Step 1 (backend):* new `ScanSession` fields, `ScanProgress.phase`, `_run_scan`, new `/scan/start`, `/scan/progress`, 409 guard in `/scan/results`. An in-process pipeline test printed `before: in_progress queued` and `after : completed completed 3 3 3 1`.
- *Step 2 (API tests):* `smoke-test.ps1` rewritten for the async flow (**14 checks** at that time; all passed). `scan-responsiveness.ps1` created. Run on **`D:\`**: `/health` answered in **1 to 3 ms throughout**, including the ~50 s discovery phase (in the old design it would have hung). Discovery took about 47 to 52 s; hashing then ran at only **about 9 to 10 files per second** (50 of 24,263 at 52 s; 1,010 at 166 s), implying roughly 40 minutes. The run was deliberately stopped. A second run on a generated folder on the SSD (1,100 files) passed: **2.1 s**, `phases seen: hashing, completed` (discovering and grouping were shorter than the 250 ms poll), `photos / groups: 1100 / 100`, max `/health` 3 ms, `RESPONSIVENESS TEST PASSED`. `Get-PhysicalDisk` showed why D: is slow (HDD over USB). Commit `test: async smoke test and scan responsiveness script`.
- *Step 3 (frontend):* types, `waitForScan`, `ScanningView.tsx`, `App.tsx`. First `tsc` failed with 5 errors because `ScanStartResponse` had been narrowed to `{status, scan_id}` while `App.tsx` still typed the results summary with it; fixed by adding the **`ScanSummary`** type. Then clean.
- *Step 4 (dev test):* owner's screenshot on D:\ showed 4%, 941 of 24,263 photos, 9.9 photos/sec, "About 39m 27s left" (consistent: 23,322 / 9.9 ≈ 39 min). SSD folder test: 198 files left after deleting two groups. All fine.
- *Step 5 (installer):* the exe was rebuilt but the MSI timestamp (22:10) was older than the exe (22:46), which would have installed the old backend; caught by comparing timestamps, MSI rebuilt (23:25). The installed app showed the progress screen on D:\; closing the window mid-scan left no processes.
- *Owner feedback during testing:* "Back to folder picker always comes at the bottom of the page; with a long list someone must scroll all the way down." Fixed: compact **sticky header** with the button at top right; bottom button removed; empty-state "Scan Another Folder" kept. Also found that `tsconfig.tsbuildinfo` (TypeScript's incremental cache) was tracked in git and showed as modified after every build; untracking plus `*.tsbuildinfo` in `.gitignore` was done in `8d5de94` (confirmed 2026-10-05: not tracked, and listed in `.gitignore`).
- *Rebuild and merge:* final MSI built and installed; the owner confirmed all tests passed; merged as `902187a`, tag `v0.1.1-cp5`, pushed.

### 6.3 Checkpoint 6: pagination and "stay on results after delete" (in progress)

**Why.** With 100 groups the page is already long; a real library gives hundreds. And after deleting, the old app jumped back to the folder picker one second later, so a user who reviewed several pages had to **rescan** (about 40 minutes on the external drive) to continue. The owner independently wanted the stay-on-results behaviour ("you literally read my mind").

**Design choices.** App-side paging (all groups fetched once, 20 shown at a time) instead of server-side paging: the data is small (a few hundred KB for 238 groups); the slow part was drawing the page, not downloading it; no backend change needed; server-side paging fits better with the later SQLite work. Defaults picked because the owner did not answer the page-style question: Previous/Next buttons with "Page X of Y", page size 20, "Select this page" as the primary control, "Select all N groups" as a deliberate extra click (accidentally selecting everything is the costly mistake), selection kept across pages.

**Steps and findings.**
- *Step 0:* branch `checkpoint-6-pagination` from `902187a`; `ResultsGrid.tsx`, `App.tsx`, `api.ts`, `types.ts` collected. Observed: the grid mapped over every group (thousands of DOM nodes); selection lives inside `ResultsGrid` so it survives page changes for free; `handleDeleteDuplicates` reset to the folder picker.
- *Step 1:* `ResultsGrid.tsx` replaced wholesale (the script first verified marker strings so it would not overwrite an unexpected file); also removed the unused `ImageIcon` import and replaced the O(groups × selected) size calculation with a `useMemo` pass. `tsc` clean.
- *Step 2 (dev test, 100 groups = 5 pages):* the owner reported all checks passed.
- *Step 3 (backend):* new `SafeDeleter` and `/scan/delete` as described in 4.3. A **unit test** (not in the repo; written to `%TEMP%\prism_delete_unit_test.py`) built 8 files in 3 groups plus 1 unique file and checked: setup; **simulated lock** on one file (2 moved, 1 reported, its group stays, counts recomputed); retry succeeds; the endpoint function itself (counts updated, repeating a delete removes nothing, `inspect.iscoroutinefunction` is False); guard rails (404/409/400). It printed `UNIT TEST PASSED`. Commit `b6dc3c3`. The **smoke test was extended to 17 checks** (updated counts in the delete response; deleted group gone from `/scan/results`; repeat delete removes nothing); the first update attempt was not run, the 14-check version ran against the new endpoint and passed, then the patch was applied (`smoke-test.ps1 updated (17 checks)`) and the 17-check run passed (`SMOKE TEST PASSED`).
- *Step 4 (frontend):* `DeleteFailure` and expanded `DeleteResponse` types; `App.tsx` banner and re-fetch logic; `tsc` exit 0; the old `setTimeout` and folder-picker reset are gone.
- *Step 5 (dev test), partial:* screenshot after deleting 5 groups on page 3: green banner "Deleted 5 files, freed 1.3 MB. Moved to the Recycle Bin, so you can restore them.", still on "Page 3 of 5", header "95 groups found. Showing 41 to 60", cards 195 / 95 / 95, "Select all 95 groups" visible. Screenshot after "Select all 95 groups" then delete: "Deleted 95 files, freed 24.5 MB", cards 100 photos / 0 groups, and the empty panel "All duplicates cleared. Nice and tidy!" with **Scan Another Folder**. (The checklist said "190 photos"; that was the assistant's arithmetic error; 195 is correct.)
- *Problems exposed by those screenshots:* (a) the tall "Scan Complete" card says "No duplicates found in this folder. All 100 photos are unique." right after deleting 95 duplicates (contradicts the empty panel), still shows a Scan ID, and says "You can review and delete duplicates in the next step" while already in that step; (b) the card fills the first screen of an 800x600 window so the groups start off-screen, and every pager click scrolls to the top of the page, i.e. onto that card.
- *Locked-file testing (still unfinished):* the owner locked `img005 - Copy.png` with a PowerShell command **before scanning** and saw 199 photos instead of 200 and no `img005` group: the scanner cannot open a locked file, prints `Error processing ...` and **silently drops it**. (Skipping is the safe behaviour; the silence is the flaw.) A second attempt with the Windows Photos app open on a file showed "It appears that the file was moved or renamed": Photos does not lock files, so the Recycle Bin move **succeeded**; this did not test the failure path. Later the stuck lock came from **Windows PowerShell ISE**: the lock script's `$fs.Close()` never ran when the script was stopped early, so Explorer reported "File In Use ... open in Windows PowerShell ISE" and blocked both deleting the file and regenerating the test folder. The owner restarted the machine. The correct test order is: **scan first, then lock, then delete in Prism**, using a normal PowerShell window and a lock script with `try/finally` and `Read-Host` (see 8).

### 6.4 Handoff decision

The owner noticed that the copy-paste loop (assistant writes a patch script, owner pastes it, owner pastes output back) caused most of the friction (scripts not run, `NO MATCH` on stale file versions, the 14-versus-17 check confusion). The recommendation was to move the **building** to Claude Code (it reads real files, edits directly, runs `tsc`/tests/smoke test itself, commits) and keep claude.ai for product and business decisions. The owner asked for this document so nothing has to be re-explained.

### 6.5 First Claude Code session (2026-10-05): verification, skipped files, summary strip

- *Verification (section 12, items 1 to 4):* all CP6 commits confirmed in `git log`; `*.tsbuildinfo` untracked; `tsc` clean; 17-check smoke test passed on a fresh backend. The **locked-file delete test** was run through the API (not the UI) with a real lock held by a hidden helper process that releases in `finally`: 21/21 checks passed (`status=partial`, the locked file untouched, its group still listed, retry after release succeeds, disk counts 199 → 198 → 195 after 5 groups → 100 after clearing, every original kept). "Back to Folder Selection then a new scan shows no old banner" was confirmed by **reading** `App.tsx` (`handleFolderSelect` calls `setNotice(null)`), not by clicking. Item 6 (clean-machine test) is **blocked**: the machine runs Windows 11 Home, which has no Windows Sandbox or Hyper-V; it needs a second PC or a VirtualBox VM.
- *Findings that led to the work below:* the delete-failure reason shown to users was raw (`[WinError 32] ... ['C:\\PRISM_~1\\IMG005~1.PNG']`, an 8.3 short path); the folder-picker tip promised "visual duplicates (AI-detected similar)", which v0.1 does not do.
- *Step 1, backend (`098df1e`):* skipped-files recording and `describe_file_error` (see 4.3, 4.4). The new smoke check caught a real bug on its first run: Python raises a bare `PermissionError` for a **locked** file, so the first version labelled it "Windows denied access"; fixed with the `CreateFileW` probe. A scratch check confirmed a truly access-denied file (via `icacls /deny <user>:(RD)`) still gets "Windows denied access".
- *Step 2, frontend (`eed8354`):* `ResultsSummary` replaces `ScanProgress`; pager scrolls to the list; tip text corrected. Verified in Claude's browser pane at 800x600 against a live dev backend, with the Tauri folder dialog stubbed from the page console (no stub in `src`): strip "198 photos · 98 duplicate groups · 98 extra copies (25.3 MB)" with 2 locked copies, plural notice and file list, bottom-pager Next lands the list just below the header, a 2-group delete updates strip and status ("96 groups left to review."), Back + rescan clears banner and notice, Select all + delete leaves "100 photos · 0 duplicate groups", no status line, the "All duplicates cleared" panel, and 100 originals on disk. No console errors. **Not verified there:** the native dialog, the Tauri window, dark mode.
- *Step 2b (`5c4611d`):* owner asked for a unit test with a *simulated* unreadable file (a real lock is flaky) and a clean-scan smoke check: `backend/tests/test_skipped_files.py` (7 tests) and smoke check 20.
- *Mistakes during the session (fixed, not repeated):* a first commit of step 2 recorded only the staged deletion of `ScanProgress.tsx` because `git add` aborted on that path (`fatal: pathspec`); it was never pushed and was redone with `git reset --soft HEAD~2` (stage folders with `git add -A src` when a file was removed). A scratch test denied `(R)` on a temp file, which also denies reading the ACL, so it could not be undone with `icacls`; it was removed with `[IO.File]::Delete` (use `(RD)`).
- *Open:* the owner tests the native dialog, the locked-file scan notice and the locked-file delete failure in `tauri dev`; then the backend exe and the MSI are built (approved: backend first, normal terminal).

### 6.6 Checkpoint 7: dark mode that follows Windows, and polish (2026-10-05)

- *Why.* `tailwind.config.js` had `darkMode: 'class'` and nothing ever set the `dark` class on `<html>`, so Prism was always light and the existing `dark:` styles had never been shown on screen.
- *Branch.* The owner asked for `checkpoint-7-dark-mode` from `main`; `main` was still at CP5, so the results strip, skipped notice, banners and pager to be reviewed did not exist there and fixes would have conflicted with CP6. The owner chose to **stack it on `checkpoint-6-pagination`**.
- *Step 1 (`67868bb`).* `darkMode: 'media'`; `color-scheme: light dark` in `index.css`. Built CSS: 5 `prefers-color-scheme: dark` blocks, 0 class-strategy selectors.
- *Step 2: review.* In Claude's browser pane at 800x600 emulating `prefers-color-scheme: dark`, every visible text element on every screen was measured against its real (blended) background, plus a scan for light patches and for text under CSS opacity. Hard-to-reach states were produced from the page console only (no change in `src`): the scanning screen by holding `/scan/progress` at a fixed response, the red banner and error screen by failing `/scan/delete` and `/scan/start`; the amber banner and skipped notice with real locks. Screens: folder picker, scanning (discovering, hashing, grouping), results strip and status line, all 20 group cards (selected and not), pager, delete bar, green/amber/red banners, skipped notice with its list open, both empty states, error screen. **Dark failures: two.** Select Folder, white on amber-600 = **3.19**; scanning footer, slate-500 on slate-800 = **3.07**. Everything else passed (faded dismiss buttons about 7.7; disabled Previous exempt). Also noted: checkboxes used the Windows accent (blue) in both modes; the delete bar covered 30% of the window (182 px); error texts were raw ("HTTP 500: Internal Server Error"); light mode had its own pre-existing failures (Select Folder white on amber-500 = **2.15**; Scan Another Folder and Try Again white on amber-600 = **3.19**).
- *Step 3 (`9ab5ca9`).* Minimal dark-only fixes: Select Folder `dark:bg-amber-700` (5.02; hover amber-800), footer `dark:text-slate-400` (5.71). Light mode measured identical (2.15, 4.76).
- *Polish, one commit each, `tsc` + 7 unit tests + 20-check smoke test passing after each:*
  - (a) `49c75a2` delete bar to one row: 66 px, 11% of the window; text 8.75 light / 12.03 dark, button 4.83 / 6.47.
  - (b) `edcbd1a` amber buttons: two options measured and shown side by side; owner chose **A, dark text on the bright amber**: `bg-amber-500 text-amber-950`, hover `amber-400` (6.97 / 8.97). Option B (white on amber-700, 5.02 / 7.09) kept the step-3 look but moved the main buttons off the brand colour; amber-900 text on amber-500 was rejected at 4.22. A also read better in dark mode (6.97 vs 5.02, and 8.31 vs 3.56 against the dark card), so per the owner's instruction it replaced the step-3 dark override on these three buttons; the button style now matches the landing page.
  - (c) `127cf8e` `accent-amber-600` on the checkboxes (verified amber in both modes).
  - (d) `4d59a37` `api.ts` shows the backend's `message` (real 400 → "Folder not found: C:\does\not\exist"; 409 → "Could not delete: Scan is not complete yet"), keeps "HTTP 500: Internal Server Error" when there is no message, and with the backend actually stopped shows "Prism's background service isn't responding. Close Prism and open it again." for both a delete and a new scan.
  - `b223774` `build-backend.ps1` stage 2 runs `backend/tests` with the release venv after the import check; verified 7 OK in `venv-release`, and a temporary failing probe test made the stage exit 1.
- *PR attempt.* The owner chose "Create PR". The branch was pushed at `67868bb` (first time the CP6 commits reached GitHub), but `gh` is not installed, so no PR was opened; the title and body were drafted for the owner to paste at `https://github.com/kumarsukant/PRISM/pull/new/checkpoint-7-dark-mode` (or install `gh` with `winget install GitHub.cli` and `gh auth login`). Later commits are not pushed.
- *Testing lessons from this checkpoint:* Vite served a stale `api.ts` (the watcher missed the second of two quick saves), giving `errorMessage is not defined` even after a reload; fixed by restarting the dev server, and diagnosed by fetching the served module. The browser pane re-syncs its colour-scheme emulation to the app theme, so a "light" reading once came back with dark colours: check `matchMedia('(prefers-color-scheme: dark)')` in the same call as every measurement. With the pane hidden, screenshots go stale and CSS transitions freeze mid-way (a selected card read as the dark tint until its transition was finished).
- *Not verified (owner will):* the native window and Windows title bar in both themes; anything in the installed MSI.
- *Release (2026-10-05).* The owner passed the native dark-mode checks; on Claude's recommendation one installer was built from `checkpoint-7-dark-mode` @ `e4151b2` instead of a CP6-only one first: `build-backend.ps1` BUILD OK (21.1 MB; stage 2 ran 7 unit tests OK; the frozen exe passed 20/20 smoke checks), then `npm run tauri build` (MSI 24.65 MiB, 96 s newer than the exe, bundled backend byte-identical to the sidecar, no High Mandatory label). The owner uninstalled the old PRISM, installed the MSI and passed an 11-step installed-app test. Then CP6 and CP7 were merged to `main` in that order (`2de3458`, `8faacf8`) and tagged `v0.1.2-cp6` / `v0.1.3-cp7`; CP6 was therefore tested inside the CP7 installer (see 5). The app still reports version 0.1.0 (backlog: bump the version per release).

### 6.7 Checkpoint 9: scan insights (2026-10-05)

- *Goal (owner).* After a scan, show where the duplicates are, so users understand what to be careful about. Read-only. **Scope guard:** no reorganize feature of any kind (no button, not even disabled; no wizard; no endpoint that moves, renames or deletes; no tip telling the user to reorganize). The only action is Open folder. The Reorganizer went to the backlog as a later, not-started item (section 11).
- *Process.* Step 1 was a design only (endpoint JSON, definitions, coverage counters, an 800x600 mockup in both themes, how Open folder stays safe, CORS); the owner approved it with changes: online-only protection, 1-2 headline sentences, tag names "Copies in same folder" / "Copies in other folders" / "Mixed", pin only the header and delete bar, a CORS origin pattern with logging, a Host check, Rust loopback timeouts and tests, notices above the tabs, separate " - Copy" and "(1)" tips hedged with "often", and extra tests (drive root, 25k photos, `.tif`, tab accessibility).
- *Definitions (also in `services/insights.py`).*
  - **Folder:** the directory directly containing the photo, matched by `normcase(normpath())`. A drive-root scan shows its own name as "D:", and the scanned folder itself shows as "<name> (top level)".
  - **Photos with a duplicate:** members of duplicate groups, whichever copy is kept.
  - **Extra copies:** members that are not the kept photo.
  - **Inside share:** memberships in groups entirely inside that folder. Tagged `same_folder` at ≥ 0.70, `other_folders` at ≤ 0.30, otherwise `mixed`.
  - **Pairs:** +1 per group for every unordered pair of distinct folders it spans. A group spanning 3+ folders counts in each of its pairs and once in `groups_across_3_plus_folders`, so pair counts are never summed.
  - **Display limits:** top 10 folders, top 5 pairs, at most 4 tips.
- *Tips (shown only when the numbers clear a bar).* All wording is in `InsightsPanel.tsx`; every cause is hedged with "often".
  - **`copy_suffix`:** " - Copy" names (incl. "Copy of"), at least 5 **and** at least 20% of extra copies.
  - **`number_suffix`:** " (1)" names, same thresholds.
  - **`folder_pair`:** the top pair shares at least 10 groups and at least 25% of the smaller folder's photos.
  - **`same_folder`:** a folder with at least 10 photos with a duplicate, tagged same_folder.
  - **`spread`:** at least 5 groups spanning 3+ folders.
- *Coverage.* The scanner now walks with `os.scandir`, so each file's size and Windows attributes come from the folder listing itself. That means no extra disk access, and one `getsize` call per image fewer than before. It counts:
  - HEIC/HEIF;
  - RAW (`.cr2 .cr3 .nef .arw .dng .orf .rw2 .raf .srw .pef .raw`);
  - supported images under 10 KB;
  - online-only files.

  Unreadable files are the existing `skipped_files`. The coverage line also says "Checked N photos in M folders" (as of the scan).
- *Online-only (cloud) files* (owner's requirement).
  - **Detection:** attributes only, never by reading the file: RECALL_ON_DATA_ACCESS 0x400000, RECALL_ON_OPEN 0x40000, OFFLINE 0x1000. PINNED / UNPINNED alone are not online-only.
  - **Where it is checked:** in the listing, again with `GetFileAttributesW` just before hashing (a file can be dehydrated in between), and before making a thumbnail (409).
  - **Unit tests:** fake the attribute, spy on `open` and `PIL.Image.open`, and assert the file is never passed to either. With the protection switched off, all 3 of those tests fail (checked).
  - **UI:** online-only files are shown as "N online-only files were not scanned. Make them available offline and scan again."
- *`.tif` (owner's decision).* `.tif` (one f) was not in the scanner's list, so such photos were **silently ignored**, breaking the "never silently drop" rule. Now scanned like `.tiff`; separate commit with a test.
- *Open folder.*
  - **Plugin:** the Tauri v2 Opener plugin (`tauri-plugin-opener`), called **from Rust only**. Per the docs, Rust-side calls are not gated by capabilities. The page has no `opener:*` permission, and the capabilities file still has only `dialog:allow-open`.
  - **The command:** `open_scan_folder(scan_id, folder_id)` validates both ids, then asks the backend for the path (`GET /scan/folder`, which answers only for folders holding photos in that scan). The request is plain std TCP to 127.0.0.1 with a proper `Host`, `Connection: close` and 2-second connect/read/write timeouts, so no HTTP crate was added. The command then requires an absolute, existing directory and calls `open_path`, which goes through the Windows shell. `explorer.exe` is not launched directly, because it misparses folder names containing commas.
  - **Rust tests (9):** reply parsing (200, 404 message, generic error, chunked, malformed), id validation, the request's Host and Connection headers, a real loopback exchange, and a silent server timing out in about 2 seconds.
- *CORS and Host (approved in the same checkpoint, since Open folder is the first action that touches the file system).*
  - **Before:** `allow_origins=["*"]`, so any web page could drive the backend.
  - **Now:**
    - CORS uses an origin pattern that accepts `http(s)://tauri.localhost`, `tauri://localhost`, and `localhost` / `127.0.0.1` on any port, with GET/POST, Content-Type and no credentials.
    - Any request with another `Origin` gets 403. That's stricter than CORS headers alone, which only hide the reply. Each refused origin is logged once to backend.log.
    - `TrustedHostMiddleware` allows only `127.0.0.1` and `localhost`, against DNS rebinding.
    - Requests without `Origin` (img thumbnails, Rust, scripts) are unaffected.
  - **Tests:** 4 unit tests run through the full middleware stack, including that each refused origin is logged once; 4 smoke checks.
  - **Reminder:** `tauri dev` loads `http://localhost:5173`, so only the installed MSI exercises `http://tauri.localhost`.
- *UI.*
  - **Tabs:** Insights (the default after a scan) and Review duplicates. Both panels stay mounted (`hidden`), so the selection and page survive a switch. After a delete the insights are fetched again.
  - **Above the tabs:** the delete banner and skipped-files notice. The "keeps one photo" line moved into the Review tab.
  - **Pinned:** only the header and the delete bar; the summary strip and the tabs scroll.
  - **Accessibility:** tabs follow the WAI-ARIA pattern (tablist/tab/tabpanel, aria-selected/controls/labelledby, roving tabindex, Left/Right wrap, Home/End; selection follows focus).
- *Measurements (browser pane, 800x600 page).*
  - **Contrast:** light-mode minimum 4.76 (the existing folder path in the strip); dark-mode minimum 6.96. The only lower readings are the strip's decorative "·" separators, which are hidden from screen readers.
  - **Tags:** light 9.45 / 6.59 / 7.57, dark 8.40 / 10.87 / 11.11 (Mixed / same folder / other folders).
  - **Open folder:** 10.35 light, 11.87 dark.
  - **Pixel budget (scrolled, with a selection):** header 85 px, delete bar 66 px + 16 px gap, **433 px of content between them**. Without a selection, 515 px. The real window is about 39 px shorter (title bar), so expect about 394 px.
  - **Table columns:** folder 208 / photos 56 / with duplicates 128 / tag 176 / button 112 px, no overflow. Long paths are shortened from the start to 26 characters ("…\2024\Holiday"), with the full path on hover.
  - **Speed:** `build_insights` on a synthetic 25,000-photo / 12,500-group session took about 111 ms; the unit test bar is under 1 s.
- *Test tree.* `scripts/make-insights-tree.ps1` (default `C:\prism_insights`; refuses a drive root, and refuses an existing folder without its `_expected.json` marker) plants:
  - Pictures\Camera: 20 photos plus 6 " - Copy" copies.
  - Pictures\WhatsApp\Images: 12 copies of Camera photos plus 3 unique.
  - Downloads: 6 photos plus 6 " (1)" copies, 3 photos that are also in both other folders, a HEIC, a CR2 and a tiny PNG.
  - One photo at the top level.

  Expected: 57 photos, 4 folders, 24 groups (12 in one folder, 12 across, 3 across three folders), 27 extra copies, and the tips copy_suffix, number_suffix, folder_pair and same_folder. The smoke test builds it in %TEMP%, checks totals, folders, tags, pairs, tips, coverage, headlines and `/scan/folder`, then deletes the 6 Camera copy groups and checks the recompute: 18 groups, the copy tip gone, and the same folder id.
- *Testing notes.*
  - **No frontend test runner** (Python and PowerShell tests only), so tab accessibility was verified in the browser pane by script: roles, aria wiring, tabindex, and every key. Adding Vitest + Testing Library is on the backlog and needs the owner's OK (new dev dependencies).
  - **Vite crashed** with `EBUSY` while `cargo check` wrote `src-tauri\target` (the browser-pane server runs without polling); restarted.
  - **Screenshots:** the pane sometimes captured only the top-left quarter at 2× density; measurements were taken from the DOM.
- *Not verified (owner will):* the real Open folder button and the window in `tauri dev`; the installed MSI (the release origin, the frozen backend's new routes and middleware). No exe or MSI was built in this checkpoint.

## 7. Decisions log (with reasoning)

| Decision | Reasoning |
|---|---|
| Defer visual dedup; ship v0.1 without torch | Never produced a result; doubly broken; installer size is a conversion cost; MD5 already finds real duplicates; CLIP is semantic, risky for deletions |
| Ladder: MD5 → perceptual hash (v0.2) → CLIP/ONNX AI Pack | Matches what real near-duplicates look like; keeps AI claim honest and optional |
| PyInstaller **one-file** sidecar | Tauri `externalBin` expects a single file; startup cost 1 to 3 s accepted |
| Random free port in release, 8000 in dev | Avoids collisions (two instances proved this); dev keeps manual backend |
| `--parent-pid` watcher in addition to Tauri's kill on exit | One-file launcher/child could survive a launcher-only kill |
| Backend logs to `backend.log` in the data dir | Windowed build has no console; this is how failures get diagnosed |
| Release deps pinned in a separate file + import gate in the build | Reproducible builds; catches missing packages before PyInstaller |
| Keep Tailwind v3 | v4 would break the existing config |
| Scan in a worker thread; `completed` set last; 409 before that | Responsiveness and correctness (no empty-results race) |
| `ScanningView` separate from `ScanProgress` | The old component is the results summary, not a progress display |
| App-side pagination, 20 per page | Small data; drawing cost is the problem; no backend change |
| "Select all N groups" is a separate deliberate click | Guard against costly accidental select-all |
| Stay on results after delete and re-fetch the list | Avoids multi-minute rescans; keeps server and screen consistent even when a file fails |
| A group with a failed file stays listed | Lets the user retry; never claims success it did not achieve |
| Treat "file already gone" as success | Prevents groups getting stuck |
| `/scan/delete` as plain `def` | Runs in a thread pool; does not block `/health` |
| Report unreadable files instead of dropping them; still never delete them | Skipping is safe, silence is not: a user seeing 199 of 200 deserves the reason and what to do |
| User-facing reasons are short plain phrases; raw errors only in the log | `[WinError 32] ... C:\PRISM_~1\...` is not actionable; "open in another program" is |
| Probe Windows (`CreateFileW`) only when `open()` gives a bare `PermissionError` | "In use" and "access denied" need different advice; the probe costs nothing on the happy path |
| Skipped list capped at 20 in `/scan/progress`, total in `skipped_count` | Same as delete `failed`; keeps the response small on a library with thousands of locked/offline files |
| One-line summary strip instead of the tall card | At 800x600 the card hid the groups; the counts fit on one line; the empty panel and banner already carry the messages |
| Unit tests use stdlib `unittest` and a *simulated* unreadable file | No new dependency; a real lock is timing-dependent (the smoke test keeps one real-lock check) |
| Theme follows Windows (`darkMode: 'media'`), no in-app toggle | The dark styles already existed but were unreachable; following the OS is what users expect and needs no settings UI |
| `color-scheme: light dark` on `html` | Native controls (checkboxes, scrollbars) otherwise stay light on a dark page |
| CP7 stacked on CP6, merge CP6 first | `main` lacked the CP6 screens; stacking avoids fixing deleted components and merge conflicts |
| Contrast is measured, both themes, at 4.5:1 | Eyeballing missed white-on-amber at 2.15 for months; numbers settle design choices quickly |
| Amber buttons: amber-950 text on amber-500 (option A), both themes | Keeps the bright brand amber with 6.97; reads better than white on amber-700 in dark too; matches the landing page |
| Delete bar compacted to one row, reassurance text kept | It covered 30% of an 800x600 window; the "Recycle Bin, so you can undo" line is a safety message worth its second line |
| Show the backend's `message`, keep "HTTP n" as fallback | The backend already explains errors; the fallback keeps unknown failures diagnosable |
| Unit tests run in the build's import gate with the release venv | A failing test stops the build before freezing, and proves the tests work with only the pinned packages |
| Roadmap order (owner's): async scan → pagination → `/thumbnail` via SQLite → perceptual hash → code signing | First user-visible pain first; wait for real-user feedback before v0.2 |

## 8. Test assets, scripts and measurements

**Scripts (all in `scripts/`)**
- `smoke-test.ps1 [-BaseUrl http://127.0.0.1:8000] [-PythonExe <python with Pillow>]`: generates four random 128x128 PNGs (`a`, `b` = copy of `a`, `c`, `d`) in a temp folder, holds `d.png` open with no sharing for the whole scan (released in `finally`, then removed), and checks, in order: `/health`; `/stats`; nonexistent folder → 400; unknown scan id → 404; `/scan/start` returns `started` + `scan_id`; polls until completed; 3 photos; **1 skipped; skipped file is `d.png` with reason "open in another program"**; 1 exact duplicate; 0 visual duplicates; 1 group; group has 2 photos; `/thumbnail` returns `image/jpeg`; delete removes 1 file; 2 files remain on disk (the duplicate went to the Recycle Bin); delete response carries updated counts (groups=0, photos=2); the deleted group is gone from `/scan/results`; deleting it again removes 0; **a clean rescan reports 0 skipped**. **20 PASS lines, then `SMOKE TEST PASSED`** (17 before 2026-10-05). Exits non-zero on failure. Puts one temp image in the Recycle Bin per run (expected).
- `backend/tests/test_skipped_files.py` (run: `backend\venv\Scripts\python.exe -m unittest discover -s backend\tests -v`; no backend needed): locked → "open in another program"; access denied → "Windows denied access"; vanished during discovery → "no longer there (moved or deleted)"; clean scan → nothing skipped; list sorted by path; `/scan/progress` lists at most 20 but counts all 25; a locked file on delete gets the plain reason and its group stays. Unreadable files are simulated by patching `open()` / `os.path.getsize` and `_windows_open_error`. **7 tests, OK.** Not yet run by `build-backend.ps1`.
- `build-backend.ps1`: see 4.8; success line `BUILD OK: ...prism-backend-x86_64-pc-windows-msvc.exe (21.1 MB)`; it runs the smoke test (now 20 checks) against the frozen exe. Since `b223774` stage 2 is "import check + unit tests": `backend/tests` runs with the release venv right after the import check, before PyInstaller.
- `scan-responsiveness.ps1 -Folder <path>`: starts a scan, polls `/health` and `/scan/progress` every 250 ms, prints a status line every 5 s, and passes only if the scan completed, the hashing counter never went backwards, max `/health` time was under 1000 ms, and the `hashing` phase was seen. **It only scans; it never deletes.**

**Test folders.** `C:\prism_test` (generator in CLAUDE.md; 100 unique images plus 100 exact copies; random noise PNGs about 264 to 270 KB each, comfortably above the 10 KB minimum). `C:\prism_perf` (1,100 files: 1,000 unique plus 100 copies, about 300 MB, deleted afterwards). Real data **never to be modified**: `D:\` (24,263 photos on a USB HDD) and the earlier 24,321-file library.

**Locked-file test.** Done through the API on 2026-10-05 (21/21, see 6.5); the owner still runs it once in the dev app to see the banner. Order: (1) generate the folder, scan it in Prism (100 groups); (2) in a separate **normal PowerShell** (not ISE) run:
```powershell
$fs = [System.IO.File]::Open('C:\prism_test\img005 - Copy.png', 'Open', 'Read', 'None')
try { "Locked. Delete in Prism now. Press Enter here to release the file."; $null = Read-Host } finally { $fs.Close(); "Released." }
```
(3) select the `img005` group plus one other group and delete. Expected: amber banner naming `img005 - Copy.png`, the `img005` group still listed, the other group gone. (4) press Enter to release, delete `img005` again: green banner, group gone. If Windows lets the delete through anyway, that is not a Prism bug (the unit test already proves the failure path with a simulated lock).

**Measurements.** Original MSI 3 MB → now 24.64 MiB. Frozen backend 21.1 MB (22,083,946 bytes). Installed `prism.exe` 11.5 MB. USB HDD: discovery ~50 s for 24k files, hashing ~9 to 10 files/s (est. 39 min). SSD: 1,100 files in 2.1 s. `/health` 1 to 3 ms during scans. Frontend bundle at CP4 time: JS 167 kB (52 kB gzip), CSS 19.7 kB, 1,918 modules.

## 9. Gotchas and lessons

**PowerShell / Windows** (also in CLAUDE.md): BOM-free file writes; absolute paths for .NET; normalize CRLF before matching; here-strings; git stderr red; cp1252 console; no grep/head; do not use `$ErrorActionPreference='Stop'` around native tools; `$env:VITE_CHOKIDAR_USEPOLLING` must be set in the same terminal. A pasted multi-line script needs the **whole block**; the owner sometimes pastes partial blocks, which is how steps got skipped.
**Build chain:** backend exe **before** MSI; confirm the MSI timestamp is newer than the exe; elevated-vs-normal terminal (High Mandatory Level label); uninstall before reinstall; `tsc -b` (inside `npm run build`) rewrites `tsconfig.tsbuildinfo` (hence the untracking); `Cargo.lock` changes whenever a crate is added and should be committed.
**Process hygiene:** before building or testing, check `Get-Process prism, prism-backend, python, node`; Python does not hot-reload (a backend started before a patch has the old code, which once made a smoke test look wrong); identify processes by command line before stopping them.
**Testing lessons:** the installed-app checks that matter most are *shutdown leaks* (no `prism-backend` after closing, including mid-scan) and *the real port* (random, not 8000). Locked-file tests need the right tool (Photos does not lock; ISE holds locks until its session ends). Always scan **before** locking.
**Process lessons for the assistant side:** do not assume a step was run (check the output); do not predict exact counts without checking (see section 15); one step at a time.

## 10. Known issues and observations

Confirmed by testing:
1. **[FIXED in `eed8354`, replaced by `ResultsSummary`] Stale summary card** (`ScanProgress.tsx`): says "Scan Complete", shows the Scan ID, says "No duplicates found in this folder. All N photos are unique." after a cleanup, and "You can review and delete duplicates in the next step"; takes the whole first screen on a small window; every page change scrolls to the top of the page onto it.
2. **[FIXED in `098df1e` + `eed8354`: now reported with a reason in the results notice] Unreadable (e.g. locked) files are silently skipped** by the scanner; a scan can report 199 of 200 photos with no explanation, and the partner of a skipped duplicate is not listed. The skip is correct (never delete what you could not read); the silence is the problem. Likely also happens for files being synced by OneDrive or still downloading.
3. **Hashing is slow on spinning/USB disks** (about 9 to 10 files/s): 4 KB read chunks and 4 concurrent threads suit SSDs but make a spinning disk seek constantly. Candidate fixes: 1 MB chunks, fewer threads when the folder is on an HDD/USB drive. Measure before and after on `D:\`; do not guess.
4. **No way to cancel a running scan** (a 40-minute scan started by mistake can only be stopped by closing the app). Needs a cancel flag checked by the worker.
5. **HEIC and RAW are not scanned** (the scanner's own extension set omits them although `Config.IMAGE_EXTENSIONS` lists them) and **files under 10 KB are skipped silently**; relevant for phone libraries.

From reading the code (not tested; treat as hypotheses):
6. `/thumbnail` rebuilds a set of every photo path across all sessions on every request (O(photos) per thumbnail; fine for hundreds, wasteful for tens of thousands) and depends on in-memory results, so it breaks if the backend restarts between scan and review (this is backlog item 3, to be solved with SQLite).
7. `/scan/results` finds each photo with `next(p for p in session.photos ...)` per group member (quadratic-ish); a dict by id would be better for very large scans.
8. `scan_results` is never cleaned up (memory grows with every scan in a long session).
9. **CORS is `*`** and the API has no authentication. The server binds `127.0.0.1` and the release port is random, but any web page open in the user's browser could in principle call a local port; consider restricting origins to the Tauri origins (and the Vite dev origin) and/or a per-launch token passed from Rust.
10. Two dead files in `backend/app/services/` and a stale `requirements.txt` can mislead; delete or rewrite them.
11. `Config` and `main.py` each create a `Config()` instance (the module also defines `config = Config()`); harmless.
12. `PhotoRecord.created_date`, `modified_date`, `file_format`, `file_hash_sha256`, and `DuplicateGroup.user_*` fields are unused placeholders; `ScanSession.completed_at` is never set.
13. Vite's file watcher can crash with `EBUSY` while Cargo rebuilds (polling env var is the workaround; the real fix is ignoring `src-tauri` in `vite.config.ts`, which was never seen).
14. `tsconfig.tsbuildinfo` tracking (see 12 for verification).
15. Installer is unsigned (SmartScreen); NSIS target disabled (download timeouts); the installed app has not been tested on a clean machine.

## 11. Backlog and roadmap

**Immediate (Checkpoints 6 and 7 wrap-up)**
1. ✔ Summary strip + status line + skipped-files notice; pager scrolls to the list (done 2026-10-05: `098df1e`, `eed8354`, `5c4611d`).
2. ✔ Owner tests, one exe + MSI from `checkpoint-7-dark-mode`, 11-step installed-app test, merges CP6 then CP7 to `main` with tags `v0.1.2-cp6` and `v0.1.3-cp7` (done 2026-10-05; CP6 tested inside the CP7 installer, see 5 and 6.6).
3. Push `main` and both tags (ask first). The drafted CP7 PR is no longer needed.
4. **Bump the app version per release.** `tauri.conf.json`, `package.json` and `Cargo.toml` all still say 0.1.0 while the tags reached 0.1.3, so every MSI is "PRISM 0.1.0" and Windows will not upgrade in place (uninstall first). Set the version to match the release (for example 0.1.4 for the next tag) in all three files as part of each release, before `npm run tauri build`; the MSI file name follows it.

**Owner's roadmap, in his chosen order**
2. Pagination ✔ (in CP6)
3. `/thumbnail` validation against SQLite so it survives backend restarts (also the natural moment to persist scan sessions and use `SQLALCHEMY_DATABASE_URL`).
4. Perceptual-hash near-duplicates (v0.2): dHash with Pillow + numpy (avoid scipy); wait for real-user feedback on whether exact matches suffice; consider a "similar" group type and lower confidence scores; this is where `group_type="visual"` and the "≈ Visual Match" label come alive.
5. Code signing (cost and lead time; decide before any public launch).

**Additional backlog (unordered)**: Cancel Scan; faster hashing on slow disks; Vite ignores `src-tauri` (bit again in CP9: `cargo check` crashed the browser-pane dev server); delete dead files (including `backend/app/main_old.py`, found in CP9) and rewrite `requirements.txt`; ~~CORS hardening~~ (done in CP9); a frontend test runner (Vitest + Testing Library, for components such as the tabs; ask first, adds dev dependencies); HEIC/RAW support (the Insights coverage line now shows how many were not checked) and a clearer message about tiny files; thumbnails allow-list as a set maintained per session; dict lookups in `/scan/results`; session cleanup; clean-machine (no Python) install test; NSIS bundling (needs a reliable download); licensing/tiers (Free/Pro/Business) when the product is ready; AI Pack via ONNX Runtime (v0.3+).

**Later, not started (owner's decision, 2026-10-05): Reorganizer.** After the user confirms, help move files into a simpler structure. Needs, before any code: a defined meaning of "simpler" (by date? by event? merging similar folders?); a preview of every move before it happens; a saved undo log and one-click Undo; no overwriting of files with the same name; care with OneDrive-synced folders and moves across drives; a warning for photo-catalog apps such as Lightroom, which track files by location; tests on generated folder trees including a failure halfway through. Reason it is held back: unlike deleting, moving has no Recycle Bin, so a bug could scramble a user's organized library. Revisit once real users ask for it. (Checkpoint 9, scan insights, was explicitly scoped to exclude any reorganize button, wizard, file-moving endpoint or reorganize tip.)

## 12. Open verification items (do these first in a new session)

**Status 2026-10-05 (see 6.5):** items 1 to 4 done and passed; item 5 done (built); item 6 blocked on this machine (Windows 11 Home: no Sandbox/Hyper-V). Still open: the owner's `tauri dev` check of the native dialog and the two locked-file screens, and item 6 on another PC or a VirtualBox VM. The list below is kept as written for reference; checks that mention 17 now have 20.

1. `git status`, `git branch --show-current` (expect `checkpoint-6-pagination`), `git log --oneline -8`. Confirm the instructed commits exist (paginate, delete-in-place `b6dc3c3`, smoke-test 17 checks, stay-on-results banner). The owner restarted his PC at the end of the chat, so nothing should be lost, but confirm.
2. `git ls-files | Select-String tsbuildinfo` should print nothing and `.gitignore` should contain `*.tsbuildinfo` (CP5 housekeeping was instructed, not shown).
3. Run `npx tsc --noEmit` and, with a fresh backend started, the 17-check `smoke-test.ps1`, to re-establish the baseline.
4. Finish the locked-file test (section 8) and the two unconfirmed dev checks from the CP6 checklist: **Back to Folder Selection** works from the results screen and a new scan starts with no old banner; disk counts after deleting (195 files after the 5-group delete, 100 after clearing everything in a fresh 200-file folder).
5. Decide with the owner whether to start with the summary strip + skipped-files notice (recommended) before merging CP6.
6. Before any release: a clean-machine (or Windows Sandbox/VM) install test without Python.

## 13. UI copy reference

- Window title: "PRISM - See Your Photos Clearly". Startup: "Starting Prism...". Backend failure: "Prism could not start its background service. Details are in backend.log in %LOCALAPPDATA%\com.kumarsukant.prism".
- Scanning: "Starting scan..." / "Looking for photos..." / "Found N photos so far..." / "Checking your photos..." / "Grouping duplicates..." / "Large libraries and external drives can take a while. Your photos are never changed during a scan."
- Results header: "📸 Prism", "See your photos clearly • Remove duplicates with confidence", button "← Back to Folder Selection".
- Grid: "Duplicate Groups"; "N groups found. Showing A to B."; "Select groups to delete" / "N groups selected for deletion (X MB)"; "☐ Select this page" / "✓ Deselect this page"; "Select all N groups"; "Clear selection"; "Page X of Y"; group labels "✓ Exact Match" / "≈ Visual Match", "N% confidence", "N duplicates • X MB"; card tags "KEPT" and "DELETE".
- Delete bar (since `49c75a2`): "**N groups (X MB)**, including K on other pages. Files go to the Recycle Bin, so you can undo this."; button "Delete N Groups" / "Deleting...". (Before: "Delete Summary" heading and "You're about to delete N groups of duplicates (X MB), including K on other pages. This action moves files to Recycle Bin and can be undone.")
- Results summary (since `eed8354`): "<folder>" · "N photos · N duplicate groups · N extra copies (X MB)"; status "Prism keeps one photo from each group (marked KEPT) and moves the extra copies to the Recycle Bin. Select the groups you want to clean up." / "N groups left to review."; skipped notice "N photos couldn't be read and were skipped, so they aren't in these results." + "Close the program that's using them, then scan again." / "See why below, then scan again.", "Show files", "<file>: <reason>", "...and N more".
- Skip/failure reasons: "open in another program", "Windows denied access", "no longer there (moved or deleted)", "could not be read (<Error>)" / "could not be moved (<Error>)".
- Folder picker tip (since `eed8354`): "Tip: Prism scans this folder and all its subfolders and finds exact copies of your photos. Nothing is changed until you choose what to delete." (It used to promise "visual duplicates (AI-detected similar)".)
- Banners: see 4.6. Empty: "No duplicates found! Your photos are all unique." / "All duplicates cleared. Nice and tidy!" and "Scan Another Folder".
- Errors: "Scan failed", "Deletion failed" fallbacks; the error screen has a "Try Again" button that returns to the folder picker. Since `4d59a37` the text is the backend's message (e.g. "Folder not found: <path>", "Scan is not complete yet"), else "HTTP <status>: <statusText>"; backend unreachable: "Prism's background service isn't responding. Close Prism and open it again."

## 14. Dependency appendix

**`backend/requirements-release.txt` (pinned, source of truth for releases):**
```
annotated-doc==0.0.5
annotated-types==0.8.0
anyio==4.15.1
click==8.5.0
colorama==0.4.6
fastapi==0.142.2
h11==0.16.0
idna==3.20
pillow==12.3.0
pydantic==2.13.5
pydantic_core==2.46.5
Send2Trash==2.1.0
starlette==1.7.0
typing-inspection==0.4.4
typing_extensions==4.16.0
uvicorn==0.54.0
```
(PyInstaller 6.22.3 is installed separately into `venv-release` by the build script and is not in the file.)

**Dev venv (`backend\venv`, Python 3.14.5) `pip freeze` at the start of CP4 (includes the CLIP stack that the release build deliberately excludes):** annotated-doc 0.0.5, annotated-types 0.8.0, anyio 4.15.1, click 8.5.0, colorama 0.4.6, fastapi 0.142.2, filelock 3.32.3, fsspec 2026.7.0, ftfy 6.3.1, h11 0.16.0, hf-xet 1.6.0, httpcore2 2.13.1, httpx2 2.13.1, huggingface_hub 2.1.1, idna 3.20, Jinja2 3.1.6, MarkupSafe 3.0.3, mpmath 1.3.0, networkx 3.6.1, numpy 2.5.2, open_clip_torch 3.3.0, opentelemetry-api 1.45.0, packaging 26.3, pillow 12.3.0, pydantic 2.13.5, pydantic_core 2.46.5, python-dotenv 1.2.4, python-multipart 0.0.32, PyYAML 6.0.3, regex 2026.9.29, safetensors 0.8.0, scipy 1.18.1, Send2Trash 2.1.0, setuptools 78.1.0, SQLAlchemy 2.1.3, starlette 1.7.0, sympy 1.14.0, timm 1.0.30, torch 2.14.1+cpu, torchaudio 2.11.0+cpu, torchvision 0.29.1+cpu, tqdm 4.70.1, truststore 0.10.4, typing-inspection 0.4.4, typing_extensions 4.16.0, uvicorn 0.54.0, wcwidth 0.9.1.

**Stale `backend/requirements.txt` (do not use):** fastapi 0.104.1, uvicorn 0.24.0, python-multipart 0.0.6, pillow 10.1.0, open-clip-torch 2.24.0, torch 2.1.1, numpy 1.26.2, scipy 1.11.4, python-dotenv 1.0.0, pydantic 2.5.0, sqlalchemy 2.0.23, Send2Trash (unpinned).

**Frontend:** React 18, TypeScript, Tailwind v3 (+ autoprefixer), Vite 5.4.21, `lucide-react` icons (Check, ChevronLeft, ChevronRight, Trash2, Loader2, CheckCircle2, AlertCircle), `@tauri-apps/api` (`invoke` from `@tauri-apps/api/core`). `package.json` itself was never shown.

## 15. Mistakes made during the chat (so they are not repeated)

- Predicted counts that were off: said the checkpoint had 8 commits (it had 7); predicted 3 modified files when 4 appeared (`.gitignore` from an earlier step); counted 11 smoke-test PASS lines when there were 10; wrote "190 photos" in a checklist (195 is right); estimated "a few more minutes" for a scan of the USB drive that needed about 40. **Lesson: do not predict exact counts when the answer can be read from output; check the output first.**
- A validation grep was case-insensitive and would have flagged the harmless string `SQLALCHEMY_DATABASE_URL`; a case-sensitive one was needed.
- Narrowing `ScanStartResponse` broke an unrelated use of that type in `App.tsx`; search for all uses of a type before changing it.
- The "locked file" test was designed with a lock command that never releases when the script is stopped early; use `try/finally`.
- Several steps silently did not happen because a pasted script was not run or only partly pasted (the smoke-test 17-check update; the first Step 1 patch). **Always verify that the change is actually on disk (grep for a marker) before testing.**
- Early plans bundled every step and validation into one message, which the owner found confusing. One step at a time, validated, was the working method from then on.
