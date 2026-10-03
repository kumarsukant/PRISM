"""
PRISM Configuration
"""
import os
from pathlib import Path

class Config:
    """Application configuration"""
    
    # Paths
    APP_DIR = Path(__file__).parent
    BACKEND_DIR = APP_DIR.parent
    PROJECT_DIR = BACKEND_DIR.parent
    DB_DIR = PROJECT_DIR / "db"
    DB_PATH = DB_DIR / "prism.db"
    
    # Create directories if they don't exist
    DB_DIR.mkdir(exist_ok=True)
    
    # Scanning
    SCAN_TIMEOUT_SECONDS = 3600
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.heic', '.webp', '.gif', '.raw', '.bmp', '.tiff'}
    
    # CLIP/AI
    CLIP_MODEL = "ViT-B-32"
    CLIP_DEVICE = "cpu"
    CLIP_EMBEDDING_DIM = 512
    VISUAL_MATCH_THRESHOLD = 0.05
    CONFIDENCE_MIN = 0.5
    
    # Database
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"
    
    # IPC/Communication
    IPC_TIMEOUT = 30
    
    def __init__(self):
        pass

config = Config()
