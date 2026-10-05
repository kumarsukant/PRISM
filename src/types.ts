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
}

export interface ScanSummary {
  status: string;
  scan_id: string;
  total_photos: number;
  exact_duplicates: number;
  visual_duplicates: number;
  duplicate_groups: number;
  message: string;
}

export interface ScanProgressResponse {
  status: 'in_progress' | 'completed' | 'failed' | 'cancelled';
  phase: 'queued' | 'discovering' | 'hashing' | 'grouping' | 'completed' | 'failed';
  scan_id: string;
  files_processed: number;
  files_total: number;
  total_photos: number;
  exact_duplicates: number;
  visual_duplicates: number;
  duplicate_groups: number;
  error_message: string | null;
}
export interface DeleteRequest {
  scan_id: string;
  group_ids: string[];
}

export interface DeleteFailure {
  file: string;
  reason: string;
}

export interface DeleteResponse {
  status: 'success' | 'partial' | string;
  scan_id: string;
  files_deleted: number;
  storage_freed_mb: number;
  groups_resolved: number;
  failed: DeleteFailure[];
  failed_count: number;
  total_photos: number;
  exact_duplicates: number;
  visual_duplicates: number;
  duplicate_groups: number;
  message: string;
}