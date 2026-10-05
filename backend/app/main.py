"""
PRISM Backend - FastAPI server with IPC messaging from Tauri
"""
import sys
import os
import argparse
import multiprocessing
import threading


def _setup_std_streams():
    """Make print() and tracebacks safe in the packaged (windowed) build.

    The packaged backend has no console and the Prism app does not read its output, so
    everything goes to backend.log in the data directory. In development (a normal console)
    the streams are only forced to UTF-8.
    """
    frozen = getattr(sys, "frozen", False)
    if frozen or sys.stdout is None or sys.stderr is None:
        data_dir = os.environ.get("PRISM_DATA_DIR") or os.path.join(os.path.expanduser("~"), ".prism")
        os.makedirs(data_dir, exist_ok=True)
        log_path = os.path.join(data_dir, "backend.log")
        mode = "w" if os.path.exists(log_path) and os.path.getsize(log_path) > 5 * 1024 * 1024 else "a"
        log = open(log_path, mode, encoding="utf-8", errors="replace", buffering=1)
        sys.stdout = log
        sys.stderr = log
    else:
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


_setup_std_streams()
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
from typing import Optional, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from models.scan import ScanSession, PhotoRecord, DuplicateGroup
from services.services import FolderScanner, ScanProgress, Deduper, SafeDeleter

app = FastAPI(
    title="PRISM Backend",
    version="0.1.4",
    description="AI-powered photo deduplication backend"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

config = Config()
scanner = FolderScanner(config)
deduper = Deduper(config)
deleter = SafeDeleter(config)

scan_results: dict[str, ScanSession] = {}

@app.get("/health")
async def health():
    """Health check for IPC communication"""
    return {
        "status": "ok",
        "message": "PRISM backend is running",
        "version": "0.1.4"
    }

def _run_scan(session: ScanSession) -> None:
    """Run a whole scan in a background thread, recording progress on the session.

    The session's status stays "in_progress" until every stage has finished, so a client that
    sees "completed" can safely fetch the results.
    """
    try:
        session.phase = "discovering"
        print(f"Scan {session.id}: {session.folder_path}")

        def on_progress(progress: ScanProgress):
            session.phase = progress.phase
            session.files_processed = progress.files_processed
            session.files_total = progress.total_files_found
            if progress.phase == "hashing" and (
                progress.files_processed % 100 == 0
                or progress.files_processed == progress.total_files_found
            ):
                print(f"  Progress: {progress.files_processed}/{progress.total_files_found} files processed")

        scanner.scan_folder(session.folder_path, session, on_progress)

        if session.status == "failed":
            session.phase = "failed"
            print(f"Scan failed: {session.error_message}")
            return

        print(f"  Found {len(session.photos)} valid images")

        session.phase = "grouping"
        deduper.find_exact_duplicates(session)
        deduper.find_visual_duplicates(session)

        session.phase = "completed"
        session.status = "completed"
        print(f"Scan complete: {session.total_photos} photos, {len(session.duplicate_groups)} groups")

    except Exception as e:
        print(f"Scan error: {e}")
        import traceback
        traceback.print_exc()
        session.error_message = str(e)
        session.phase = "failed"
        session.status = "failed"


@app.post("/scan/start")
async def start_scan(request_data: dict):
    """Start a scan in the background and return immediately. Poll /scan/progress for status."""
    folder_path = str(request_data.get("folder_path", "")).strip()
    if not folder_path:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "folder_path is required in request body"}
        )
    if not os.path.isdir(folder_path):
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": f"Folder not found: {folder_path}"}
        )

    session = ScanSession(folder_path=folder_path)
    scan_results[session.id] = session
    threading.Thread(
        target=_run_scan, args=(session,), daemon=True, name=f"scan-{session.id[:8]}"
    ).start()
    return {"status": "started", "scan_id": session.id}


@app.get("/scan/progress")
async def get_progress(scan_id: str):
    """Get progress of a scan (running or finished)"""
    session = scan_results.get(scan_id)
    if session is None:
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "Scan not found"}
        )

    return {
        "status": session.status,
        "phase": session.phase,
        "scan_id": scan_id,
        "files_processed": session.files_processed,
        "files_total": session.files_total,
        "total_photos": session.total_photos,
        "exact_duplicates": session.exact_duplicates,
        "visual_duplicates": session.visual_duplicates,
        "duplicate_groups": len(session.duplicate_groups),
        "skipped_count": len(session.skipped_files),
        "skipped": session.skipped_files[:20],
        "error_message": session.error_message
    }

@app.get("/scan/results")
async def get_results(scan_id: str):
    """Get results of completed scan"""
    if scan_id not in scan_results:
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "Scan not found"}
        )
    
    session = scan_results[scan_id]
    if session.status != "completed":
        return JSONResponse(
            status_code=409,
            content={"status": "error", "message": "Scan is not complete yet"}
        )

    groups = []
    for group in session.duplicate_groups:
        photo_details = []
        for photo_id in group.photo_ids:
            photo = next((p for p in session.photos if p.id == photo_id), None)
            if photo:
                detail = {
                    "id": photo.id,
                    "file_path": photo.file_path,
                    "file_size_bytes": photo.file_size_bytes,
                    "width": photo.width_px,
                    "height": photo.height_px,
                    "is_kept": photo.id == group.kept_photo_id
                }
                photo_details.append(detail)
        
        groups.append({
            "id": group.id,
            "type": group.group_type,
            "confidence": round(group.confidence_score, 3),
            "photos": photo_details,
            "kept_photo_id": group.kept_photo_id
        })
    
    return {
        "status": "complete",
        "scan_id": scan_id,
        "total_photos": session.total_photos,
        "duplicate_groups": len(groups),
        "groups": groups
    }

@app.post("/scan/delete")
def delete_duplicates(request_data: dict):
    """Move the duplicates of the selected groups to the Recycle Bin.

    This is a plain def on purpose: FastAPI runs it in a worker thread, so deleting many files
    cannot block the server (or /health) while it works.
    """
    scan_id = str(request_data.get("scan_id", "")).strip()
    group_ids = request_data.get("group_ids", [])

    if not scan_id:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "scan_id is required"}
        )

    session = scan_results.get(scan_id)
    if session is None:
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "Scan not found"}
        )

    if session.status != "completed":
        return JSONResponse(
            status_code=409,
            content={"status": "error", "message": "Scan is not complete yet"}
        )

    try:
        wanted = set(group_ids)
        groups_to_delete = [g for g in session.duplicate_groups if g.id in wanted]

        print(f"Deleting {len(groups_to_delete)} duplicate groups...")
        result = deleter.delete_duplicates(session, groups_to_delete)

        failed = result["failed"]
        freed_mb = result["freed_bytes"] / (1024 * 1024)
        message = f"Deleted {result['files_deleted']} files, freed {freed_mb:.1f} MB"
        if failed:
            message += f"; {len(failed)} could not be moved to the Recycle Bin"

        return {
            "status": "partial" if failed else "success",
            "scan_id": scan_id,
            "files_deleted": result["files_deleted"],
            "storage_freed_mb": round(freed_mb, 2),
            "groups_resolved": len(result["resolved_group_ids"]),
            "failed": failed[:20],
            "failed_count": len(failed),
            "total_photos": session.total_photos,
            "exact_duplicates": session.exact_duplicates,
            "visual_duplicates": session.visual_duplicates,
            "duplicate_groups": len(session.duplicate_groups),
            "message": message
        }

    except Exception as e:
        print(f"Delete error: {e}")
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": str(e)}
        )

@app.get("/thumbnail")
async def get_thumbnail(path: str):
    """Serve a cached 300px thumbnail for a scanned photo"""
    import hashlib
    import tempfile
    from pathlib import Path
    from PIL import Image
    from fastapi.responses import FileResponse

    known = set()
    for session in scan_results.values():
        for p in session.photos:
            known.add(os.path.normcase(os.path.abspath(p.file_path)))

    target = os.path.normcase(os.path.abspath(path))
    if target not in known:
        return JSONResponse(
            status_code=403,
            content={"status": "error", "message": "File not part of any scan"}
        )

    if not os.path.exists(path):
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "File not found"}
        )

    cache_dir = Path(tempfile.gettempdir()) / "prism_thumbs"
    cache_dir.mkdir(exist_ok=True)

    key = hashlib.md5(target.encode("utf-8")).hexdigest()
    cached = cache_dir / f"{key}.jpg"

    if not cached.exists():
        try:
            with Image.open(path) as img:
                img.draft("RGB", (600, 600))
                img = img.convert("RGB")
                img.thumbnail((300, 300), Image.Resampling.LANCZOS)
                img.save(cached, "JPEG", quality=80)
        except Exception as e:
            print(f"Thumbnail failed for {path}: {e}")
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": str(e)}
            )

    return FileResponse(cached, media_type="image/jpeg")


@app.get("/stats")
async def get_stats():
    """Get server statistics"""
    return {
        "completed_scans": len(scan_results),
        "total_scans_processed": len(scan_results),
        "db_path": str(config.DB_PATH)
    }

def _watch_parent(pid: int):
    """Exit when the Prism app (our parent) exits.

    A PyInstaller --onefile exe is a launcher plus a child process. If the app only kills the
    launcher, the child could survive. Watching the app's PID closes that gap.
    """
    if sys.platform != "win32":
        return
    import ctypes
    from ctypes import wintypes
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.OpenProcess.restype = wintypes.HANDLE
    k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k32.WaitForSingleObject.restype = wintypes.DWORD
    k32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    handle = k32.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE
    if not handle:
        if ctypes.get_last_error() == 87:  # ERROR_INVALID_PARAMETER: that process no longer exists
            os._exit(0)
        return  # cannot watch it (for example access denied): keep running
    k32.WaitForSingleObject(handle, 0xFFFFFFFF)
    os._exit(0)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--parent-pid", type=int, default=0)
    args = parser.parse_args()
    if args.parent_pid:
        threading.Thread(target=_watch_parent, args=(args.parent_pid,), daemon=True).start()
    import uvicorn
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=args.port,
        log_level="warning" if getattr(sys, "frozen", False) else "info",
    )