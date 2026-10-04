# Prism Desktop MVP — Architecture

**Checkpoint:** 3 (Desktop MVP) · **Status:** Draft for review · **Last updated:** 2026-10-03

This document covers the desktop app only. The web app (Checkpoint 4) reuses the
same Python engine and is sketched at the end.

---

## 1. Goals and non-goals

**The MVP must:**

1. Scan one or more folders the user picks, on their own machine, with no network access.
2. Find **exact duplicates** (same bytes) and **near-duplicates** (resized, re-encoded, lightly edited, burst shots).
3. Pick the best shot in each group and explain why ("sharper", "higher resolution").
4. Let the user review every group before anything moves.
5. Move rejected photos to the Recycle Bin. Never delete permanently.
6. Write an audit log of every action and an HTML report of each scan.
7. Rescan quickly: unchanged files aren't re-analyzed.

**Not in the MVP:** accounts, payments and quota enforcement (Checkpoint 6), video,
cloud storage integrations, macOS builds (needs a Mac to build and sign), RAW
decoding beyond pairing (see §4.6).

---

## 2. System overview

```
┌──────────────────────────── Prism.exe (Tauri 2) ────────────────────────────┐
│                                                                              │
│  ┌────────────── WebView2 ──────────────┐     ┌──────── Rust core ────────┐  │
│  │ React + TypeScript + Vite + Tailwind │     │ • Tauri commands          │  │
│  │ Folder picker → Scan → Review →      │◄───►│ • Sidecar lifecycle       │  │
│  │ Confirm → Done                       │ IPC │ • Forwards RPC + events   │  │
│  └──────────────────────────────────────┘     └─────────────┬─────────────┘  │
│                                                             │ stdin/stdout   │
│                                                             │ JSON lines     │
│                                               ┌─────────────▼─────────────┐  │
│                                               │ prism-engine (Python,     │  │
│                                               │ bundled with PyInstaller) │  │
│                                               │ scan · hash · embed ·     │  │
│                                               │ group · score · trash ·   │  │
│                                               │ audit · report            │  │
│                                               └──┬──────────────┬─────────┘  │
└──────────────────────────────────────────────────┼──────────────┼────────────┘
                                                   │              │
                          %APPDATA%\Prism\prism.db (SQLite)   Ollama on localhost
                          %APPDATA%\Prism\audit.jsonl         (optional, §4.5)
                          %LOCALAPPDATA%\Prism\thumbs\
```

### Why this split

- **Python engine:** the dedup logic, image libraries (Pillow, OpenCV, imagehash)
  and ONNX Runtime all live there, and the same package will power the FastAPI
  backend in Checkpoint 4. Write it once.
- **Tauri shell:** a small installer and native file dialogs, and the UI reuses the
  web stack and brand tokens from `frontend/`.
- **stdio, not a localhost HTTP server:** no open port, no firewall prompt, and no
  other process on the machine can talk to the engine. The engine also runs
  standalone as a CLI, which the README's "hardened CLI" scope asks for.

### IPC protocol

Newline-delimited JSON over the sidecar's stdin/stdout. Requests carry an `id`,
events don't. Logs go to stderr, never stdout.

```jsonc
// UI → engine
{"id": 1, "method": "scan.start", "params": {"roots": ["D:\\Photos"], "semantic": true}}
// engine → UI (streamed)
{"event": "scan.progress", "scanId": "s_01", "stage": "hashing", "done": 1200, "total": 8400}
// engine → UI (reply)
{"id": 1, "result": {"scanId": "s_01"}}
```

Methods: `scan.start`, `scan.cancel`, `groups.list`, `groups.update` (user overrides),
`actions.preview`, `actions.apply`, `report.export`, `engine.health`.

The Rust side spawns the engine with `tauri-plugin-shell`'s sidecar API, and the app's
capability file allows **only** that sidecar. The UI can't run arbitrary commands.

---

## 3. Repository layout

```
engine/                     # Python package — shared by desktop and (later) backend
  pyproject.toml
  prism_engine/
    cli.py                  # `prism-engine scan|apply|report` + `prism-engine rpc`
    rpc.py                  # JSON-lines server for the desktop sidecar
    discover.py  hashing.py  embed.py  group.py  score.py
    actions.py   audit.py    report.py  db.py   models.py
  tests/                    # pytest, synthetic fixtures (§7)
desktop/                    # Tauri 2 app
  src/                      # React UI (Vite)
  src-tauri/                # Rust: main.rs, commands.rs, sidecar.rs, tauri.conf.json
```

This adds two top-level folders to the README's planned structure. `backend/` then
imports `prism_engine` rather than duplicating it.

---

## 4. Engine pipeline

Every stage is incremental: results are cached in SQLite keyed by
`(path, size, mtime)`, so a rescan only processes new or changed files.

### 4.1 Discover

- Walk the chosen roots and keep `jpg jpeg png heic heif webp tif tiff`. RAW files
  are recorded for pairing only (§4.6).
- Don't follow symlinks or junctions. Skip hidden/system folders.
- **Skip cloud placeholders.** OneDrive / iCloud "online-only" files carry the
  `RECALL_ON_DATA_ACCESS` / `OFFLINE` attributes, and reading them silently
  downloads them. Count them in the report as "skipped: not on this PC".

### 4.2 Exact duplicates

Group by file size first (cheap), then hash only same-size files with BLAKE2b
(in the standard library, fast, no MD5 collision worries).

### 4.3 Near-duplicates (perceptual)

- Decode with Pillow (+ `pillow-heif`), apply EXIF orientation, and use JPEG
  draft mode to decode at reduced size. Large JPEGs decode several times faster that way.
- Compute pHash and dHash (`imagehash`). Candidate pairs: Hamming distance ≤ a
  threshold, found with a BK-tree rather than comparing every pair.
- Catches resized, re-encoded, re-saved and lightly color-adjusted copies.

### 4.4 Near-duplicates (semantic, CLIP)

- CLIP image embeddings (ViT-B/32 image encoder exported to **ONNX**, run with
  ONNX Runtime on CPU). PyTorch is avoided because it would add well over a GB to the installer.
- Pairs with cosine similarity above a tuned threshold become candidates. Catches
  bursts, small crops and edits that perceptual hashes miss.
- MVP search: blocked NumPy matrix multiply, plus a capture-time window to skip
  obviously unrelated pairs. Move to FAISS once libraries pass roughly 50k photos.
- Hardware: this machine has Intel Arc and no NVIDIA GPU, so CUDA is out. CPU is fine for
  the MVP; OpenVINO / DirectML execution providers are a later speed-up.

**Grouping:** exact matches, perceptual pairs and CLIP pairs become edges.
Union-find turns them into groups, and each group records *why* it formed so the UI
can say "exact copy" vs "similar shot".

### 4.5 Picking the best shot

Deterministic, explainable scoring per photo:

| Signal | How |
|---|---|
| Sharpness | Variance of Laplacian (OpenCV) |
| Exposure | Share of clipped highlights / crushed shadows |
| Resolution | Pixel count |
| Originality | Has camera EXIF, larger file, not a re-encode or a messaging-app copy |
| Tie-break | Oldest capture time, then shortest path |

The top score is suggested as **Best shot**, and the UI shows the reasons.

**Where Ollama fits (optional):** `llama2` is text-only and can't look at photos, so
it can't pick between them. The MVP ships the scoring above. A follow-up can add an
opt-in "Ask AI" tie-breaker for close calls that sends the top two thumbnails to
a **local vision model** (e.g. `llama3.2-vision`) via Ollama on `localhost`. If
Ollama isn't running, the feature hides itself and nothing else changes.

### 4.6 RAW + JPEG pairs

Photographers often shoot RAW+JPEG (`IMG_1234.CR2` + `IMG_1234.JPG`). These are
**not duplicates**: same base name, same folder, one RAW plus one rendered file.
They are treated as one item. Prism never suggests trashing half of a pair.

---

## 5. Safety

The roadmap calls this "hardened" for a reason. These rules are enforced in the
engine, not just the UI, and each has a test.

1. **Preview by default.** `actions.apply` requires a preview token from
   `actions.preview` for the exact same set of files.
2. **Never empty a group.** At least one photo per group is always kept, even
   if the user unticks everything.
3. **Re-verify before moving.** Size, mtime and hash are checked again
   immediately before each move. If anything changed, that file is skipped and logged.
4. **Recycle Bin only, never permanent delete.** Via `send2trash` (Windows
   shell file operation). **Gotcha:** USB and network drives often have no
   Recycle Bin, and Windows would delete permanently. Prism detects that and instead moves
   files to a `Prism Trash\<scan-id>\` folder on the same drive.
5. **Stay inside the roots.** Any path that resolves outside the scanned folders
   is refused.
6. **Audit everything.** Append-only `audit.jsonl` (fsync per write): timestamp,
   action, original path, hash, destination, result. The HTML report links to it.
7. **Locked or in-use files** are skipped with a clear message, never retried in a loop.

---

## 6. Desktop UI

Vite + React + TypeScript + Tailwind v4 with the same brand tokens as
`frontend/app/globals.css`. (Next.js isn't a good fit inside Tauri; a static Vite build is simpler.)
The tokens move to a shared file once both apps use them.

1. **Choose folders.** Native picker, recent folders, estimated photo count.
2. **Scanning.** Stage-by-stage progress and a cancel button. Partial results are kept.
3. **Review.** One group at a time, or a grid view. Best-shot badge and reasons,
   keep/trash toggles, keyboard shortcuts (←/→ groups, K keep, T trash), plus a
   running "space to recover" total. Thumbnails come from the local cache through Tauri's
   asset protocol, restricted to the cache folder.
4. **Confirm.** Plain summary: "Move 214 photos (3.1 GB) to the Recycle Bin."
5. **Done.** Totals, "Open Recycle Bin", "View report".

---

## 7. Testing and validation

- **Synthetic fixture set**, generated in tests: originals plus resized,
  re-encoded, cropped, rotated, brightness-shifted and burst-style variants, plus
  true negatives (different photos of the same scene). Grouping is scored for
  **precision and recall**. Precision matters more, because a false "duplicate" risks
  losing a real photo.
- **Safety tests** for every rule in §5, including a fake drive with no Recycle Bin.
- **Validation harness:** the roadmap specifies 8 checks from the existing
  PhotoDedup code. They get ported here (open question 1).
- **Performance targets** (to be measured on this laptop): first scan of 10,000
  photos in under 10 minutes with CLIP on, rescans in under 1 minute.

---

## 8. Build order

| # | Milestone | Done when |
|---|---|---|
| M1 | Engine core CLI: discover, exact + perceptual, group, score, HTML report (read-only) | `prism-engine scan <dir> --report out.html` works on a real folder |
| M2 | Safe actions + audit log | Every §5 rule has a passing test |
| M3 | CLIP stage (ONNX) | Precision/recall measured on fixtures; thresholds chosen |
| M4 | Tauri shell + sidecar RPC + the five screens | Full flow works in `tauri dev` |
| M5 | Packaging | Windows installer (NSIS/MSI) with the bundled engine runs on a clean machine |
| M6 | Optional Ollama vision tie-breaker | Hidden when Ollama is absent |

Code signing: an unsigned installer triggers SmartScreen warnings. That's fine for beta
testers but needs a certificate before public launch.

---

## 9. Looking ahead: web app (Checkpoint 4)

`backend/` (FastAPI) imports `prism_engine`. Uploaded photos run through the same
pipeline in a Celery worker. That path is **not** offline or on-device, so the
landing page's privacy claims must stay specific to the desktop app.

---

## 10. Open questions

1. **Where is the existing PhotoDedup Python code?** The roadmap says to harden it,
   including its 8-check validation harness and `dedup_audit.jsonl` format. If it
   exists, M1–M2 start from it instead of from scratch.
2. **Ollama's role.** OK to ship deterministic scoring first and make the local
   vision model an opt-in tie-breaker? (`llama2` can't see images.)
3. **CLIP model delivery.** Bundle it in the installer (fully offline from first
   launch, larger download) or fetch once on first run (smaller installer, needs
   internet once)? Recommendation: bundle, so "works offline" is true from day one.
4. **What does the Free tier's "100 photos a month" count:** photos scanned, or
   photos cleaned? Recommendation: photos cleaned. Enforcement waits for Checkpoint 6
   (needs a signed license file to work offline).
5. **Ollama location.** The market research mentions running Ollama on a DigitalOcean
   Droplet. For the desktop app that would contradict "photos never leave your
   device", so this design assumes local-only.
6. **macOS in the MVP?** Building and signing needs a Mac. This plan is Windows-first.
