"""
PRISM Services: Scanner, Deduper, and Deleter - Consolidated
"""
import os, hashlib, sqlite3, subprocess, sys, numpy as np, torch, open_clip
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Callable, List
from PIL import Image

from models.scan import PhotoRecord, DuplicateGroup, ScanSession
from config import Config

@dataclass
class ScanProgress:
    total_files_found: int = 0
    files_processed: int = 0
    current_file: str = ""
    photos_indexed: int = 0
    status: str = "scanning"

class FolderScanner:
    def __init__(self, config: Config):
        self.config = config
        self.session: Optional[ScanSession] = None
        self.progress_callback: Optional[Callable[[ScanProgress], None]] = None
        self.db_path = config.DB_PATH
        
    def scan_folder(self, folder_path: str, session: ScanSession, progress_callback: Optional[Callable[[ScanProgress], None]] = None) -> ScanSession:
        self.session = session
        self.progress_callback = progress_callback
        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            session.status = "failed"
            session.error_message = f"Folder not found: {folder_path}"
            return session
        
        image_files = self._find_image_files(folder)
        session.total_photos = len(image_files)
        
        if len(image_files) == 0:
            session.status = "completed"
            session.completed_at = datetime.now()
            return session
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(self._process_photo, file_path): file_path for file_path in image_files}
            for i, future in enumerate(as_completed(futures)):
                try:
                    photo = future.result()
                    if photo:
                        session.photos.append(photo)
                    if self.progress_callback:
                        self.progress_callback(ScanProgress(total_files_found=len(image_files), files_processed=i + 1, current_file=futures[future].name, photos_indexed=len(session.photos), status="scanning"))
                except Exception as e:
                    print(f"Error processing file: {e}")
        
        session.status = "completed"
        session.completed_at = datetime.now()
        self._save_session_to_db(session)
        return session
    
    def _find_image_files(self, root_path: Path) -> list:
        image_files = []
        for ext in self.config.IMAGE_EXTENSIONS:
            image_files.extend(root_path.rglob(f"*{ext}"))
            image_files.extend(root_path.rglob(f"*{ext.upper()}"))
        return sorted(set(image_files))
    
    def _process_photo(self, file_path: Path) -> Optional[PhotoRecord]:
        try:
            file_size = file_path.stat().st_size
            if file_size < 10_000:
                return None
            photo = PhotoRecord()
            photo.file_path = str(file_path)
            photo.file_size_bytes = file_size
            photo.file_format = file_path.suffix.lower().lstrip(".")
            photo.file_hash_md5 = self._compute_md5(file_path)
            try:
                with Image.open(file_path) as img:
                    photo.width_px = img.width
                    photo.height_px = img.height
                    photo.color_space = img.mode
            except:
                return None
            stat = file_path.stat()
            photo.modified_date = datetime.fromtimestamp(stat.st_mtime)
            photo.created_date = datetime.fromtimestamp(stat.st_ctime)
            return photo
        except:
            return None
    
    def _compute_md5(self, file_path: Path) -> str:
        md5 = hashlib.md5()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    md5.update(chunk)
            return md5.hexdigest()
        except:
            return ""
    
    def _save_session_to_db(self, session: ScanSession) -> None:
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS scan_sessions (id TEXT PRIMARY KEY, folder_path TEXT, started_at TIMESTAMP, completed_at TIMESTAMP, total_photos INTEGER, exact_duplicates INTEGER, visual_duplicates INTEGER, files_deleted INTEGER, storage_freed_mb REAL, status TEXT, error_message TEXT)")
            cursor.execute("CREATE TABLE IF NOT EXISTS photos (id TEXT PRIMARY KEY, scan_id TEXT, file_path TEXT, file_size_bytes INTEGER, file_hash_md5 TEXT, file_hash_sha256 TEXT, width_px INTEGER, height_px INTEGER, color_space TEXT, file_format TEXT, created_date TIMESTAMP, modified_date TIMESTAMP, indexed_at TIMESTAMP, FOREIGN KEY (scan_id) REFERENCES scan_sessions(id))")
            cursor.execute("INSERT INTO scan_sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (session.id, session.folder_path, session.started_at, session.completed_at, session.total_photos, session.exact_duplicates, session.visual_duplicates, session.files_deleted, session.storage_freed_mb, session.status, session.error_message))
            for photo in session.photos:
                cursor.execute("INSERT INTO photos VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (photo.id, session.id, photo.file_path, photo.file_size_bytes, photo.file_hash_md5, photo.file_hash_sha256, photo.width_px, photo.height_px, photo.color_space, photo.file_format, photo.created_date, photo.modified_date, photo.indexed_at))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error saving session to database: {e}")

class VisualDeduper:
    def __init__(self, config: Config):
        self.config = config
        self.device = config.CLIP_DEVICE
        print(f"Loading CLIP model: {config.CLIP_MODEL} on {self.device}...")
        self.model, _, self.preprocess = open_clip.create_model_and_transforms(config.CLIP_MODEL, pretrained='openai', device=self.device)
        self.model.eval()
        print("✓ CLIP model loaded")
    
    def find_visual_duplicates(self, session: ScanSession, progress_callback: Optional[Callable] = None) -> ScanSession:
        if not session.photos:
            return session
        print(f"Computing CLIP embeddings for {len(session.photos)} photos...")
        embeddings = []
        valid_photos = []
        for i, photo in enumerate(session.photos):
            try:
                embedding = self._compute_embedding(photo.file_path)
                if embedding is not None:
                    embeddings.append(embedding)
                    valid_photos.append(photo)
                    if progress_callback:
                        progress_callback({"stage": "embedding", "current": i + 1, "total": len(session.photos)})
            except:
                pass
        if not embeddings:
            return session
        embeddings = np.array(embeddings)
        print("Finding visual duplicates...")
        processed = set()
        for i in range(len(embeddings)):
            if i in processed:
                continue
            distances = self._cosine_distances(embeddings[i:i+1], embeddings)[0]
            matches = np.where(distances < self.config.VISUAL_MATCH_THRESHOLD)[0]
            if len(matches) <= 1:
                continue
            group = DuplicateGroup()
            group.group_type = "visual"
            group.photo_ids = [valid_photos[j].id for j in matches]
            group.kept_photo_id = valid_photos[matches[0]].id
            avg_distance = np.mean(distances[matches])
            group.confidence_score = max(0, 1.0 - avg_distance)
            session.duplicate_groups.append(group)
            session.visual_duplicates += len(matches) - 1
            for j in matches:
                processed.add(j)
        return session
    
    def find_exact_duplicates(self, session: ScanSession) -> ScanSession:
        print("Finding exact duplicates by MD5...")
        hash_groups = {}
        for photo in session.photos:
            if photo.file_hash_md5:
                if photo.file_hash_md5 not in hash_groups:
                    hash_groups[photo.file_hash_md5] = []
                hash_groups[photo.file_hash_md5].append(photo)
        for file_hash, photos in hash_groups.items():
            if len(photos) <= 1:
                continue
            group = DuplicateGroup()
            group.group_type = "exact"
            group.photo_ids = [p.id for p in photos]
            group.kept_photo_id = photos[0].id
            group.confidence_score = 1.0
            session.duplicate_groups.append(group)
            session.exact_duplicates += len(photos) - 1
        return session
    
    def _compute_embedding(self, file_path: str) -> Optional[np.ndarray]:
        try:
            image = Image.open(file_path).convert('RGB')
            image_input = self.preprocess(image).unsqueeze(0).to(self.device)
            with torch.no_grad():
                embedding = self.model.encode_image(image_input)
            embedding = embedding.cpu().numpy()[0]
            embedding = embedding / np.linalg.norm(embedding)
            return embedding
        except:
            return None
    
    def _cosine_distances(self, query: np.ndarray, corpus: np.ndarray) -> np.ndarray:
        query_norm = query / np.linalg.norm(query, axis=1, keepdims=True)
        corpus_norm = corpus / np.linalg.norm(corpus, axis=1, keepdims=True)
        similarities = np.dot(query_norm, corpus_norm.T)
        distances = 1 - similarities
        return distances.flatten()

class SafeDeleter:
    def __init__(self, config: Config):
        self.config = config
        self.platform = sys.platform
    
    def delete_duplicates(self, session: ScanSession, groups_to_delete: List[DuplicateGroup], progress_callback: Optional[Callable] = None) -> ScanSession:
        deleted_count = 0
        freed_bytes = 0
        errors = []
        for i, group in enumerate(groups_to_delete):
            for photo_id in group.photo_ids:
                if photo_id == group.kept_photo_id:
                    continue
                photo = next((p for p in session.photos if p.id == photo_id), None)
                if not photo:
                    continue
                try:
                    success = self._move_to_recycle_bin(photo.file_path)
                    if success:
                        deleted_count += 1
                        freed_bytes += photo.file_size_bytes
                        group.user_action = "delete"
                        group.deleted_at = datetime.now()
                    else:
                        errors.append(f"Failed to delete: {photo.file_path}")
                except Exception as e:
                    errors.append(f"Error deleting {photo.file_path}: {str(e)}")
            if progress_callback:
                progress_callback({"stage": "deleting", "deleted": deleted_count, "total": sum(len(g.photo_ids) - 1 for g in groups_to_delete)})
        session.files_deleted = deleted_count
        session.storage_freed_mb = freed_bytes / (1024 * 1024)
        if errors:
            session.error_message = "; ".join(errors[:5])
        return session
    
    def _move_to_recycle_bin(self, file_path: str) -> bool:
        try:
            try:
                import send2trash
                send2trash.send2trash(file_path)
                return True
            except:
                pass
            if self.platform == 'win32':
                return self._move_to_recycle_bin_windows(file_path)
            elif self.platform == 'darwin':
                return self._move_to_recycle_bin_mac(file_path)
            else:
                return self._move_to_recycle_bin_linux(file_path)
        except:
            return False
    
    def _move_to_recycle_bin_windows(self, file_path: str) -> bool:
        try:
            ps_cmd = f'[System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms") | Out-Null; $file = Get-Item -LiteralPath "{file_path}"; $shell = New-Object -ComObject Shell.Application; $folder = $shell.Namespace($file.Directory.FullName); $folder_item = $folder.ParseName($file.Name); $folder_item.InvokeVerb("delete")'
            result = subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, timeout=5)
            return not Path(file_path).exists()
        except:
            try:
                os.remove(file_path)
                return True
            except:
                return False
    
    def _move_to_recycle_bin_mac(self, file_path: str) -> bool:
        try:
            script = f'tell app "Finder" to delete POSIX file "{file_path}"'
            subprocess.run(["osascript", "-e", script], capture_output=True, timeout=5)
            return not Path(file_path).exists()
        except:
            return False
    
    def _move_to_recycle_bin_linux(self, file_path: str) -> bool:
        try:
            result = subprocess.run(["trash-put", file_path], capture_output=True, timeout=5)
            return result.returncode == 0
        except:
            try:
                result = subprocess.run(["gio", "trash", file_path], capture_output=True, timeout=5)
                return result.returncode == 0
            except:
                return False
