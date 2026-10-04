"""
PRISM Backend - Core Services for photo scanning and deduplication
"""
from typing import Callable, Optional, List
from dataclasses import dataclass
from models.scan import ScanSession, PhotoRecord, DuplicateGroup
from config import Config
import hashlib
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image

@dataclass
class ScanProgress:
    """Progress update for a scan operation"""
    files_processed: int
    total_files_found: int

class FolderScanner:
    """Recursively scans folders for image files and computes MD5 hashes"""
    
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff'}
    MIN_FILE_SIZE = 10 * 1024  # 10 KB
    
    def __init__(self, config: Config):
        self.config = config
    
    def scan_folder(self, folder_path: str, session: ScanSession, progress_callback: Optional[Callable[[ScanProgress], None]] = None) -> ScanSession:
        """Scan folder recursively for images"""
        try:
            print(f"Scanning: {folder_path}")
            
            # Find all image files
            image_files = []
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if Path(file).suffix.lower() in self.IMAGE_EXTENSIONS:
                        file_path = os.path.join(root, file)
                        file_size = os.path.getsize(file_path)
                        if file_size >= self.MIN_FILE_SIZE:
                            image_files.append(file_path)
            
            print(f"Found {len(image_files)} candidate image files")
            
            # Process files in parallel
            photos = []
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {executor.submit(self._process_image, filepath): filepath for filepath in image_files}
                
                for idx, future in enumerate(as_completed(futures), 1):
                    try:
                        photo = future.result()
                        if photo:
                            photos.append(photo)
                        
                        if progress_callback:
                            progress_callback(ScanProgress(
                                files_processed=idx,
                                total_files_found=len(image_files)
                            ))
                    except Exception as e:
                        print(f"Error processing file {futures[future]}: {e}")
            
            session.photos = photos
            session.total_photos = len(photos)
            session.status = "completed"
            print(f"Scan complete: {len(photos)} valid images")
            return session
            
        except Exception as e:
            print(f"Scan error: {e}")
            session.status = "failed"
            session.error_message = str(e)
            return session
    
    def _process_image(self, file_path: str) -> Optional[PhotoRecord]:
        """Process a single image file"""
        try:
            # Compute MD5 hash
            md5_hash = hashlib.md5()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    md5_hash.update(chunk)
            
            # Get file size
            file_size = os.path.getsize(file_path)
            
            # Get image dimensions and color space
            try:
                with Image.open(file_path) as img:
                    width, height = img.size
                    color_space = img.mode
            except Exception as e:
                print(f"Could not read image metadata for {file_path}: {e}")
                width, height, color_space = 0, 0, "unknown"
            
            photo = PhotoRecord(
                file_path=file_path,
                file_size_bytes=file_size,
                file_hash_md5=md5_hash.hexdigest(),
                width_px=width,
                height_px=height,
                color_space=color_space
            )
            return photo
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            return None

class Deduper:
    """Finds duplicate photos. v0.1: exact matches by MD5. Near-duplicates (perceptual hash) arrive in v0.2."""

    def __init__(self, config: Config):
        self.config = config

    def find_exact_duplicates(self, session: ScanSession) -> ScanSession:
        """Find exact duplicates by MD5 hash"""
        print("Finding exact duplicates by MD5...")
        
        hash_groups = {}
        for photo in session.photos:
            if photo.file_hash_md5 not in hash_groups:
                hash_groups[photo.file_hash_md5] = []
            hash_groups[photo.file_hash_md5].append(photo)
        
        # Create duplicate groups for MD5 matches
        exact_count = 0
        for md5_hash, photos in hash_groups.items():
            if len(photos) > 1:
                group = DuplicateGroup(
                    group_type="exact",
                    confidence_score=1.0,
                    photo_ids=[p.id for p in photos],
                    kept_photo_id=photos[0].id  # Keep the first one
                )
                session.duplicate_groups.append(group)
                exact_count += len(photos) - 1
        
        session.exact_duplicates = exact_count
        print(f"Found {exact_count} exact duplicates")
        return session
    
    def find_visual_duplicates(self, session: ScanSession) -> ScanSession:
        """Near-duplicate detection is planned for v0.2 (perceptual hash)."""
        session.visual_duplicates = 0
        return session

class SafeDeleter:
    """Safely deletes files by moving them to recycle bin"""
    
    def __init__(self, config: Config):
        self.config = config
    
    def delete_duplicates(self, session: ScanSession, groups: List[DuplicateGroup]) -> ScanSession:
        """Delete files in the specified duplicate groups"""
        try:
            deleted_count = 0
            freed_bytes = 0
            
            for group in groups:
                # Delete all photos except the kept one
                for photo_id in group.photo_ids:
                    if photo_id != group.kept_photo_id:
                        photo = next((p for p in session.photos if p.id == photo_id), None)
                        if photo and self._delete_file(photo.file_path):
                            deleted_count += 1
                            freed_bytes += photo.file_size_bytes
            
            session.files_deleted = deleted_count
            session.storage_freed_mb = freed_bytes / (1024 * 1024)
            
            return session
            
        except Exception as e:
            print(f"Delete error: {e}")
            return session
    
    def _delete_file(self, file_path: str) -> bool:
        """Move a single file to the Recycle Bin / Trash"""
        try:
            from send2trash import send2trash
            send2trash(file_path)
            return True
        except Exception as e:
            print(f"Could not move {file_path} to Recycle Bin: {e}")
            return False
        
