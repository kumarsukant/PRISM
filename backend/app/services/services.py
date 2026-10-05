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
    phase: str = "hashing"  # "discovering" or "hashing"

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
                            if progress_callback and len(image_files) % 200 == 0:
                                progress_callback(ScanProgress(
                                    files_processed=0,
                                    total_files_found=len(image_files),
                                    phase="discovering"
                                ))
            
            print(f"Found {len(image_files)} candidate image files")
            if progress_callback:
                progress_callback(ScanProgress(
                    files_processed=0,
                    total_files_found=len(image_files),
                    phase="hashing"
                ))
            
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

    @staticmethod
    def _keeper_sort_key(photo: PhotoRecord):
        """Deterministic keeper choice: shortest filename, then oldest creation time, then path.

        So '3.jpeg' beats '3 - Copy.jpeg' on every run, no matter which file finished hashing first.
        """
        try:
            created = os.path.getctime(photo.file_path)
        except OSError:
            created = float("inf")
        return (len(os.path.basename(photo.file_path)), created, photo.file_path.lower())

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
                photos = sorted(photos, key=self._keeper_sort_key)
                group = DuplicateGroup(
                    group_type="exact",
                    confidence_score=1.0,
                    photo_ids=[p.id for p in photos],
                    kept_photo_id=photos[0].id  # first after sorting: shortest name, oldest, then path
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
    """Safely deletes files by moving them to the Recycle Bin"""

    def __init__(self, config: Config):
        self.config = config

    def delete_duplicates(self, session: ScanSession, groups: List[DuplicateGroup]) -> dict:
        """Move the duplicates of the given groups to the Recycle Bin and bring the session up to date.

        The kept photo of each group is never touched. A group disappears from the session once only
        its kept photo is left. If a file could not be moved, its group stays (holding only the photos
        still on disk) so the user can see what failed and try again.
        """
        photos_by_id = {p.id: p for p in session.photos}
        deleted_count = 0
        freed_bytes = 0
        gone_ids = set()
        resolved_group_ids = []
        failed = []

        for group in groups:
            remaining = []
            for photo_id in group.photo_ids:
                if photo_id == group.kept_photo_id:
                    remaining.append(photo_id)
                    continue
                photo = photos_by_id.get(photo_id)
                if photo is None:
                    continue  # already removed from this scan
                if not os.path.exists(photo.file_path):
                    gone_ids.add(photo_id)  # already deleted outside Prism
                    continue
                error = self._delete_file(photo.file_path)
                if error is None:
                    deleted_count += 1
                    freed_bytes += photo.file_size_bytes
                    gone_ids.add(photo_id)
                else:
                    failed.append({"file": os.path.basename(photo.file_path), "reason": error})
                    remaining.append(photo_id)
            group.photo_ids = remaining
            if len(remaining) <= 1:
                resolved_group_ids.append(group.id)

        # Replace the lists instead of editing them in place, so a request reading them at the same
        # moment (a thumbnail, for example) always sees a complete list.
        resolved = set(resolved_group_ids)
        session.duplicate_groups = [g for g in session.duplicate_groups if g.id not in resolved]
        session.photos = [p for p in session.photos if p.id not in gone_ids]
        session.files_deleted += deleted_count
        session.storage_freed_mb += freed_bytes / (1024 * 1024)
        session.total_photos = len(session.photos)
        session.exact_duplicates = sum(
            len(g.photo_ids) - 1 for g in session.duplicate_groups if g.group_type == "exact"
        )
        session.visual_duplicates = sum(
            len(g.photo_ids) - 1 for g in session.duplicate_groups if g.group_type == "visual"
        )

        return {
            "files_deleted": deleted_count,
            "freed_bytes": freed_bytes,
            "resolved_group_ids": resolved_group_ids,
            "failed": failed,
        }

    def _delete_file(self, file_path: str) -> Optional[str]:
        """Move one file to the Recycle Bin. Returns None on success, or a short error message."""
        try:
            from send2trash import send2trash
            send2trash(file_path)
            return None
        except Exception as e:
            print(f"Could not move {file_path} to Recycle Bin: {e}")
            return (str(e) or type(e).__name__)[:200]
