"""
PRISM Backend - FastAPI server with IPC messaging from Tauri
"""
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import sys
import os
import json

# Add parent to path so we can import config, models, services
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from models.scan import ScanSession, PhotoRecord, DuplicateGroup

# Initialize FastAPI app
app = FastAPI(title="PRISM Backend", version="0.1.0")
config = Config()

# Global state
current_scan: ScanSession | None = None

@app.get("/health")
async def health():
    """Health check for IPC communication"""
    return {"status": "ok", "message": "PRISM backend is running"}

@app.post("/scan/start")
async def start_scan(folder_path: str, recursive: bool = True, include_videos: bool = False, quality_threshold: float = 0.95):
    """Start a new scan session"""
    global current_scan
    try:
        current_scan = ScanSession(folder_path=folder_path)
        return {"status": "started", "scan_id": current_scan.id, "message": f"Scanning {folder_path}"}
    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})

@app.get("/scan/progress")
async def get_progress(scan_id: str):
    """Get progress of current scan"""
    if not current_scan or current_scan.id != scan_id:
        return JSONResponse(status_code=404, content={"status": "error", "message": "Scan not found"})
    return {"status": "scanning", "progress": 0, "message": "Scan in progress (placeholder)"}

@app.get("/scan/results")
async def get_results(scan_id: str):
    """Get results of completed scan"""
    if not current_scan or current_scan.id != scan_id:
        return JSONResponse(status_code=404, content={"status": "error", "message": "Scan not found"})
    return {"status": "complete", "groups": [], "message": "No duplicates found (placeholder)"}

if __name__ == "__main__":
    import uvicorn
    # Run on localhost:8000 for IPC communication
    uvicorn.run(app, host="127.0.0.1", port=8000)
