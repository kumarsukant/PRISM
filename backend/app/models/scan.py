"""
Data models for scanning, photos, and duplicates
"""
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4
from typing import Optional

@dataclass
class PhotoRecord:
    """A single photo in a scan"""
    id: str = field(default_factory=lambda: str(uuid4()))
    file_path: str = ""
    file_size_bytes: int = 0
    file_hash_md5: str = ""
    file_hash_sha256: str = ""
    visual_embedding: Optional[list] = None  # CLIP embedding (list of floats)
    width_px: int = 0
    height_px: int = 0
    color_space: str = ""  # RGB, RGBA, CMYK, etc.
    file_format: str = ""  # JPEG, PNG, HEIC, etc.
    created_date: Optional[datetime] = None
    modified_date: Optional[datetime] = None
    indexed_at: datetime = field(default_factory=datetime.now)

@dataclass
class DuplicateGroup:
    """A group of duplicate photos"""
    id: str = field(default_factory=lambda: str(uuid4()))
    group_type: str = "exact"  # "exact" or "visual"
    confidence_score: float = 0.0  # 0.0 - 1.0
    photo_ids: list[str] = field(default_factory=list)
    kept_photo_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    user_reviewed: bool = False
    user_action: str = "pending"  # "delete", "keep", "pending"
    deleted_at: Optional[datetime] = None

@dataclass
class ScanSession:
    """A scanning session"""
    id: str = field(default_factory=lambda: str(uuid4()))
    folder_path: str = ""
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    total_photos: int = 0
    exact_duplicates: int = 0
    visual_duplicates: int = 0
    files_deleted: int = 0
    storage_freed_mb: float = 0.0
    status: str = "in_progress"  # "in_progress", "completed", "failed", "cancelled"
    error_message: Optional[str] = None
    photos: list[PhotoRecord] = field(default_factory=list)
    duplicate_groups: list[DuplicateGroup] = field(default_factory=list)
