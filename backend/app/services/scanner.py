"""
Folder scanner and photo hasher for PRISM
"""
import os
import hashlib
import mimetypes
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Callable
from PIL import Image
import sqlite3

from models.scan import PhotoRecord, ScanSession
from config import Config

@dataclass
class ScanProgress:
    """Progress update for scanning"""
    total_files_found: int = 0
    files_processed: int = 0
    current_file: str = ""
    photos_indexed: int = 0
    status: str = "scanning"

class FolderScanner:
    """Scans a folder recursively for image files and computes hashes"""
    
    def __init__(self, config: Config):
        self.config = config
        self.session: Optional[ScanSession] = None
        self.progress_callback: Optional[Callable[[ScanProgress], None]] = None
        self.db_path = config.DB_PATH
        
    def scan_folder(self, folder_path: str, session: ScanSession, 
                   progress_callback: Optional[Callable[[ScanProgress], None]] = None) -> ScanSession:
        """
        Scan a folder recursively for images
        
        Args:
            folder_path: Root folder to scan
            session: ScanSession object to populate
            progress_callback: Callback for progress updates
            
        Returns:
            Updated ScanSession with all photos found
        """
        self.session = session
        self.progress_callback = progress_callback
        
        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            session.status = "failed"
            session.error_message = f"Folder not found: {folder_path}"
            return session
        
        # Find all image files
        image_files = self._find_image_files(folder)
        session.total_photos = len(image_files)
        
        if len(image_files) == 0:
            session.status = "completed"
            session.completed_at = datetime.now()
            return session
        
        # Process files with thread pool (4 workers for parallel hashing)
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(self._process_photo, file_path): file_path 
                for file_path in image_files
            }
            
            for i, future in enumerate(as_completed(futures)):
                try:
                    photo = future.result()
                    if photo:
                        session.photos.append(photo)
                    
                    # Update progress
                    if self.progress_callback:
                        self.progress_callback(ScanProgress(
                            total_files_found=len(image_files),
                            files_processed=i + 1,
                            current_file=futures[future].name,
                            photos_indexed=len(session.photos),
                            status="scanning"
                        ))
                except Exception as e:
                    print(f"Error processing file: {e}")
        
        session.status = "completed"
        session.completed_at = datetime.now()
        
        # Save to database
        self._save_session_to_db(session)
        
        return session
    
    def _find_image_files(self, root_path: Path) -> list[Path]:
        """Recursively find all image files in folder"""
        image_files = []
        
        for ext in self.config.IMAGE_EXTENSIONS:
            # Use glob to find all matching files
            image_files.extend(root_path.rglob(f"*{ext}"))
            image_files.extend(root_path.rglob(f"*{ext.upper()}"))
        
        return sorted(set(image_files))  # Remove duplicates, sort by path
    
    def _process_photo(self, file_path: Path) -> Optional[PhotoRecord]:
        """Process a single photo file"""
        try:
            # Skip if file is too small (likely corrupted)
            file_size = file_path.stat().st_size
            if file_size < 10_000:  # Skip files < 10KB
                return None
            
            photo = PhotoRecord()
            photo.file_path = str(file_path)
            photo.file_size_bytes = file_size
            photo.file_format = file_path.suffix.lower().lstrip(".")
            
            # Compute MD5 hash
            photo.file_hash_md5 = self._compute_md5(file_path)
            
            # Extract image metadata
            try:
                with Image.open(file_path) as img:
                    photo.width_px = img.width
                    photo.height_px = img.height
                    photo.color_space = img.mode  # RGB, RGBA, CMYK, etc.
            except Exception as e:
                print(f"Warning: Could not extract image metadata from {file_path}: {e}")
                return None
            
            # Get file timestamps
            stat = file_path.stat()
            photo.modified_date = datetime.fromtimestamp(stat.st_mtime)
            photo.created_date = datetime.fromtimestamp(stat.st_ctime)
            
            return photo
            
        except Exception as e:
            print(f"Error processing photo {file_path}: {e}")
            return None
    
    def _compute_md5(self, file_path: Path) -> str:
        """Compute MD5 hash of file"""
        md5 = hashlib.md5()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    md5.update(chunk)
            return md5.hexdigest()
        except Exception as e:
            print(f"Error computing MD5 for {file_path}: {e}")
            return ""
    
    def _save_session_to_db(self, session: ScanSession) -> None:
        """Save scan session and photos to SQLite database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Create tables if they don't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scan_sessions (
                    id TEXT PRIMARY KEY,
                    folder_path TEXT,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    total_photos INTEGER,
                    exact_duplicates INTEGER,
                    visual_duplicates INTEGER,
                    files_deleted INTEGER,
                    storage_freed_mb REAL,
                    status TEXT,
                    error_message TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS photos (
                    id TEXT PRIMARY KEY,
                    scan_id TEXT,
                    file_path TEXT,
                    file_size_bytes INTEGER,
                    file_hash_md5 TEXT,
                    file_hash_sha256 TEXT,
                    width_px INTEGER,
                    height_px INTEGER,
                    color_space TEXT,
                    file_format TEXT,
                    created_date TIMESTAMP,
                    modified_date TIMESTAMP,
                    indexed_at TIMESTAMP,
                    FOREIGN KEY (scan_id) REFERENCES scan_sessions(id)
                )
            """)
            
            # Insert scan session
            cursor.execute("""
                INSERT INTO scan_sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session.id,
                session.folder_path,
                session.started_at,
                session.completed_at,
                session.total_photos,
                session.exact_duplicates,
                session.visual_duplicates,
                session.files_deleted,
                session.storage_freed_mb,
                session.status,
                session.error_message
            ))
            
            # Insert photos
            for photo in session.photos:
                cursor.execute("""
                    INSERT INTO photos VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    photo.id,
                    session.id,
                    photo.file_path,
                    photo.file_size_bytes,
                    photo.file_hash_md5,
                    photo.file_hash_sha256,
                    photo.width_px,
                    photo.height_px,
                    photo.color_space,
                    photo.file_format,
                    photo.created_date,
                    photo.modified_date,
                    photo.indexed_at
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Error saving session to database: {e}")
