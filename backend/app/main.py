"""
PRISM Backend - FastAPI server with IPC messaging from Tauri
"""
import sys
import io

# Force UTF-8 encoding for stdout/stderr on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
from typing import Optional, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from models.scan import ScanSession, PhotoRecord, DuplicateGroup
from services.services import FolderScanner, ScanProgress, VisualDeduper, SafeDeleter

app = FastAPI(
    title="PRISM Backend",
    version="0.1.0",
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
deduper: Optional[VisualDeduper] = None
deleter = SafeDeleter(config)

current_scan: Optional[ScanSession] = None
scan_results: dict[str, ScanSession] = {}

@app.get("/health")
async def health():
    """Health check for IPC communication"""
    return {
        "status": "ok",
        "message": "PRISM backend is running",
        "version": "0.1.0"
    }

@app.post("/scan/start")
async def start_scan(request_data: dict):
    """Start a new scan session"""
    global current_scan, deduper
    
    try:
        folder_path = request_data.get("folder_path", "").strip()
        if not folder_path:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "folder_path is required in request body"}
            )
        
        print(f"Starting scan: {folder_path}")
        
        if deduper is None:
            deduper = VisualDeduper(config)
        
        current_scan = ScanSession(folder_path=folder_path)
        
        print("Step 1: Scanning folder...")
        def scanner_progress(progress: ScanProgress):
            print(f"  Progress: {progress.files_processed}/{progress.total_files_found} files processed")
        
        current_scan = scanner.scan_folder(folder_path, current_scan, scanner_progress)
        
        if current_scan.status == "failed":
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": current_scan.error_message}
            )
        
        print(f"  Found {len(current_scan.photos)} valid images")
        
        print("Step 2: Finding exact duplicates...")
        current_scan = deduper.find_exact_duplicates(current_scan)
        print(f"  Found {current_scan.exact_duplicates} exact duplicates")
        
        print("Step 3: Finding visual duplicates...")
        current_scan = deduper.find_visual_duplicates(current_scan)
        print(f"  Found {current_scan.visual_duplicates} visual duplicates")
        
        scan_results[current_scan.id] = current_scan
        
        return {
            "status": "completed",
            "scan_id": current_scan.id,
            "total_photos": current_scan.total_photos,
            "exact_duplicates": current_scan.exact_duplicates,
            "visual_duplicates": current_scan.visual_duplicates,
            "duplicate_groups": len(current_scan.duplicate_groups),
            "message": f"Scan complete: {current_scan.total_photos} photos, {len(current_scan.duplicate_groups)} groups found"
        }
        
    except Exception as e:
        print(f"Scan error: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": str(e)}
        )

@app.get("/scan/progress")
async def get_progress(scan_id: str):
    """Get progress of current scan"""
    if scan_id not in scan_results:
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "Scan not found"}
        )
    
    session = scan_results[scan_id]
    return {
        "status": session.status,
        "scan_id": scan_id,
        "total_photos": session.total_photos,
        "exact_duplicates": session.exact_duplicates,
        "visual_duplicates": session.visual_duplicates
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
async def delete_duplicates(scan_id: str, group_ids: List[str]):
    """Delete selected duplicate groups"""
    if scan_id not in scan_results:
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "Scan not found"}
        )
    
    try:
        session = scan_results[scan_id]
        groups_to_delete = [g for g in session.duplicate_groups if g.id in group_ids]
        
        print(f"Deleting {len(groups_to_delete)} duplicate groups...")
        session = deleter.delete_duplicates(session, groups_to_delete)
        
        return {
            "status": "success",
            "scan_id": scan_id,
            "files_deleted": session.files_deleted,
            "storage_freed_mb": round(session.storage_freed_mb, 2),
            "message": f"Deleted {session.files_deleted} files, freed {session.storage_freed_mb:.1f} MB"
        }
        
    except Exception as e:
        print(f"Delete error: {e}")
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": str(e)}
        )

@app.get("/stats")
async def get_stats():
    """Get server statistics"""
    return {
        "completed_scans": len(scan_results),
        "total_scans_processed": len(scan_results),
        "db_path": str(config.DB_PATH),
        "clip_model": config.CLIP_MODEL,
        "clip_device": config.CLIP_DEVICE
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
