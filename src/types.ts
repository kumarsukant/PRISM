// src/types.ts - Shared types for frontend

export interface ScanSession {
  id: string;
  folder_path: string;
  started_at: string;
  completed_at: string | null;
  total_photos: number;
  exact_duplicates: number;
  visual_duplicates: number;
  files_deleted: number;
  storage_freed_mb: number;
  status: 'in_progress' | 'completed' | 'failed' | 'cancelled';
  error_message: string | null;
}

export interface PhotoRecord {
  id: string;
  file_path: string;
  file_size_bytes: number;
  width: number;
  height: number;
  is_kept: boolean;
}

export interface DuplicateGroup {
  id: string;
  type: 'exact' | 'visual';
  confidence: number;
  photos: PhotoRecord[];
  kept_photo_id: string;
}

export interface ScanResults {
  status: string;
  scan_id: string;
  total_photos: number;
  duplicate_groups: number;
  groups: DuplicateGroup[];
}

export interface ScanStartRequest {
  folder_path: string;
}

export interface ScanStartResponse {
  status: string;
  scan_id: string;
  total_photos: number;
  exact_duplicates: number;
  visual_duplicates: number;
  duplicate_groups: number;
  message: string;
}

export interface DeleteRequest {
  scan_id: string;
  group_ids: string[];
}

export interface DeleteResponse {
  status: string;
  scan_id: string;
  files_deleted: number;
  storage_freed_mb: number;
  message: string;
}
