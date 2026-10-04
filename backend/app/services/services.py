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
import numpy as np
from scipy.spatial.distance import cosine

# CLIP imports
try:
    import open_clip
    CLIP_AVAILABLE = True
except ImportError:
    CLIP_AVAILABLE = False

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

class VisualDeduper:
    """Finds exact and visual duplicates using MD5 and CLIP"""
    
    VISUAL_MATCH_THRESHOLD = 0.05  # Cosine distance threshold
    
    def __init__(self, config: Config):
        self.config = config
        self.model = None
        self.processor = None
        self._load_clip_model()
    
    def _load_clip_model(self):
        """Load CLIP model"""
        if not CLIP_AVAILABLE:
            print("Warning: open_clip not available. Visual deduplication will be skipped.")
            return
        
        try:
            model_name = self.config.CLIP_MODEL
            print(f"Loading CLIP model: {model_name} on {self.config.CLIP_DEVICE}...")
            
            self.model, _, self.processor = open_clip.create_model_and_transforms(
                model_name,
                device=self.config.CLIP_DEVICE
            )
            self.model.eval()
            print(f"✓ CLIP model loaded")
        except Exception as e:
            print(f"Warning: Could not load CLIP model: {e}")
            self.model = None
    
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
        """Find visual duplicates using CLIP embeddings"""
        print("Finding visual duplicates...")
        
        if not self.model:
            print("CLIP model not available, skipping visual deduplication")
            session.visual_duplicates = 0
            return session
        
        if len(session.photos) < 2:
            session.visual_duplicates = 0
            return session
        
        try:
            # Compute embeddings for all photos
            print(f"Computing CLIP embeddings for {len(session.photos)} photos...")
            embeddings = []
            valid_photos = []
            
            for photo in session.photos:
                try:
                    with Image.open(photo.file_path) as img:
                        img_tensor = self.processor(img).unsqueeze(0).to(self.config.CLIP_DEVICE)
                        
                        with open_clip.set_model_to_eval(self.model):
                            with np.no_grad():
                                embedding = self.model.encode_image(img_tensor)
                                embedding = embedding.cpu().numpy().flatten()
                                embeddings.append(embedding)
                                valid_photos.append(photo)
                except Exception as e:
                    print(f"Could not encode {photo.file_path}: {e}")
                    continue
            
            print(f"Successfully computed embeddings for {len(embeddings)} photos")
            
            if len(embeddings) < 2:
                session.visual_duplicates = 0
                return session
            
            embeddings = np.array(embeddings)
            
            # Find visual duplicates using cosine distance
            print("Computing cosine similarities...")
            
            # Normalize embeddings
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            normalized_embeddings = embeddings / (norms + 1e-8)
            
            visual_count = 0
            processed_indices = set()
            
            for i in range(len(normalized_embeddings)):
                if i in processed_indices:
                    continue
                
                # Compute distances to all other images
                distances = []
                for j in range(i + 1, len(normalized_embeddings)):
                    if j not in processed_indices:
                        # Use dot product on normalized vectors (equivalent to cosine similarity)
                        # Distance = 1 - similarity
                        similarity = np.dot(normalized_embeddings[i], normalized_embeddings[j])
                        distance = 1.0 - similarity
                        
                        # Clamp to [0, 1]
                        distance = max(0.0, min(1.0, distance))
                        
                        if distance < self.VISUAL_MATCH_THRESHOLD:
                            distances.append((j, distance))
                
                if distances:
                    # Sort by distance (closest first)
                    distances.sort(key=lambda x: x[1])
                    
                    # Create group with all visual matches
                    photo_indices = [i] + [j for j, _ in distances]
                    duplicate_photo_ids = [valid_photos[idx].id for idx in photo_indices]
                    
                    group = DuplicateGroup(
                        group_type="visual",
                        confidence_score=float(1.0 - distances[0][1]),  # Confidence based on closest match
                        photo_ids=duplicate_photo_ids,
                        kept_photo_id=valid_photos[i].id
                    )
                    session.duplicate_groups.append(group)
                    
                    # Mark as processed
                    for j, _ in distances:
                        processed_indices.add(j)
                    
                    visual_count += len(distances)
            
            session.visual_duplicates = visual_count
            print(f"Found {visual_count} visual duplicates")
            return session
            
        except Exception as e:
            print(f"Error during visual deduplication: {e}")
            import traceback
            traceback.print_exc()
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
        """Delete a single file safely"""
        try:
            import platform
            
            if platform.system() == "Windows":
                # Use Windows Shell.Application to move to recycle bin
                try:
                    import win32com.client
                    shell = win32com.client.Dispatch("Shell.Application")
                    shell.NameSpace(0).ParseName(file_path).InvokeVerb("delete")
                    return True
                except:
                    # Fallback: try PowerShell
                    import subprocess
                    subprocess.run([
                        "powershell", "-Command",
                        f"Remove-Item '{file_path}' -Recurse -Force"
                    ], check=False)
                    return True
            
            elif platform.system() == "Darwin":
                # macOS: use osascript
                import subprocess
                subprocess.run([
                    "osascript", "-e",
                    f'tell application "Finder" to delete POSIX file "{file_path}"'
                ], check=False)
                return True
            
            else:
                # Linux: try trash-put or gio trash
                import subprocess
                try:
                    subprocess.run(["trash-put", file_path], check=True)
                    return True
                except:
                    try:
                        subprocess.run(["gio", "trash", file_path], check=True)
                        return True
                    except:
                        # Fallback: permanent delete
                        os.remove(file_path)
                        return True
        
        except Exception as e:
            print(f"Could not delete {file_path}: {e}")
            return False
        
