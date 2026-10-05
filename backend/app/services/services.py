"""
PRISM Backend - Core Services for photo scanning and deduplication
"""
from typing import Callable, Optional, List, Tuple
from dataclasses import dataclass
from models.scan import ScanSession, PhotoRecord, DuplicateGroup
from config import Config
import hashlib
import os
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image

def _windows_open_error(file_path: str) -> Optional[int]:
    """Ask Windows why a file cannot be opened: 32 = in use, 5 = access denied, 0 = it opens now.

    Python's open() turns both "in use" and "access denied" into the same PermissionError without
    the Windows code, so this tells them apart. Only called on the failure path.
    """
    if sys.platform != "win32":
        return None
    import ctypes
    from ctypes import wintypes
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateFileW.restype = wintypes.HANDLE
    k32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
                                wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    # GENERIC_READ, share read/write/delete, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL
    handle = k32.CreateFileW(file_path, 0x80000000, 0x7, None, 3, 0x80, None)
    if handle == wintypes.HANDLE(-1).value:
        return ctypes.get_last_error()
    k32.CloseHandle(handle)
    return 0


def describe_file_error(error: BaseException, action: str, file_path: Optional[str] = None) -> str:
    """A short, plain-language reason a file could not be read or moved, for showing to the user.

    `action` is the past participle used in the fallback ("read" or "moved"). The raw error still
    goes to the log, where it is useful; users get a reason they can act on.
    """
    winerror = getattr(error, "winerror", None)
    if winerror is None and isinstance(error, PermissionError) and file_path:
        winerror = _windows_open_error(file_path)
    if winerror in (32, 33):  # sharing violation / lock violation
        return "open in another program"
    if isinstance(error, FileNotFoundError) or winerror in (2, 3):
        return "no longer there (moved or deleted)"
    if isinstance(error, PermissionError) or winerror == 5:
        return "Windows denied access"
    return f"could not be {action} ({type(error).__name__})"


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
            skipped = []  # files we could not read: never silently dropped, the user is told
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if Path(file).suffix.lower() in self.IMAGE_EXTENSIONS:
                        file_path = os.path.join(root, file)
                        try:
                            file_size = os.path.getsize(file_path)
                        except OSError as e:
                            print(f"Skipping {file_path}: {e}")
                            skipped.append(self._skip(file_path, describe_file_error(e, "read", file_path)))
                            continue
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
                        photo, reason = future.result()
                        if photo:
                            photos.append(photo)
                        else:
                            skipped.append(self._skip(futures[future], reason))

                        if progress_callback:
                            progress_callback(ScanProgress(
                                files_processed=idx,
                                total_files_found=len(image_files)
                            ))
                    except Exception as e:
                        print(f"Error processing file {futures[future]}: {e}")
                        skipped.append(self._skip(futures[future], f"could not be read ({type(e).__name__})"))

            session.photos = photos
            session.total_photos = len(photos)
            session.skipped_files = sorted(skipped, key=lambda s: s["path"].lower())
            print(f"Scan complete: {len(photos)} valid images, {len(skipped)} skipped")
            return session
            
        except Exception as e:
            print(f"Scan error: {e}")
            session.status = "failed"
            session.error_message = str(e)
            return session
    
    @staticmethod
    def _skip(file_path: str, reason: str) -> dict:
        return {"file": os.path.basename(file_path), "path": file_path, "reason": reason}

    def _process_image(self, file_path: str) -> Tuple[Optional[PhotoRecord], Optional[str]]:
        """Process a single image file. Returns (photo, None), or (None, reason) if it could not be read."""
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
            return photo, None

        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            return None, describe_file_error(e, "read", file_path)

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
            return describe_file_error(e, "moved", file_path)
