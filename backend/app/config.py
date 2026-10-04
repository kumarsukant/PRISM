"""
PRISM Configuration
"""
import os
from pathlib import Path


def _data_dir() -> Path:
    """Writable per-user data directory. The Tauri app passes PRISM_DATA_DIR; dev falls back to ~/.prism."""
    env = os.environ.get("PRISM_DATA_DIR")
    base = Path(env) if env else Path.home() / ".prism"
    base.mkdir(parents=True, exist_ok=True)
    return base


class Config:
    """Application configuration"""

    # Paths
    APP_DIR = Path(__file__).parent
    BACKEND_DIR = APP_DIR.parent
    PROJECT_DIR = BACKEND_DIR.parent
    DB_DIR = _data_dir()
    DB_PATH = DB_DIR / "prism.db"

    # Scanning
    SCAN_TIMEOUT_SECONDS = 3600
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.heic', '.webp', '.gif', '.raw', '.bmp', '.tiff'}
    VISUAL_MATCH_THRESHOLD = 0.05  # reserved for v0.2 near-duplicate matching
    CONFIDENCE_MIN = 0.5

    # Database
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

    # IPC/Communication
    IPC_TIMEOUT = 30

    def __init__(self):
        pass


config = Config()