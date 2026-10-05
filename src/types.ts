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

/** A photo the scanner could not read (locked, access denied, vanished). Never silently dropped. */
export interface SkippedFile {
  file: string;
  path: string;
  reason: string;
}

export interface ScanSummary {
  status: string;
  scan_id: string;
  folder_path: string;
  total_photos: number;
  exact_duplicates: number;
  visual_duplicates: number;
  duplicate_groups: number;
  skipped_count: number;
  skipped: SkippedFile[];
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
  skipped_count: number;
  skipped: SkippedFile[]; // first 20 only; skipped_count has the total
  coverage?: Coverage;
  error_message: string | null;
}

/** What the scan did and did not look at. Online-only (cloud) files are never opened, only counted. */
export interface Coverage {
  photos_checked: number;
  folders_checked: number;
  heic_not_checked: number;
  raw_not_checked: number;
  under_10kb: number;
  online_only: number;
  unreadable: number;
}

/** same_folder: >= 70% of the folder's duplicate memberships are in groups entirely inside it; other_folders: <= 30% */
export type FolderTag = 'same_folder' | 'other_folders' | 'mixed';

export interface FolderRef {
  id: string;
  relative_path: string; // "" = the scanned folder itself
}

export interface InsightFolder extends FolderRef {
  path: string;
  photos: number;
  photos_with_duplicate: number;
  share_with_duplicate: number;
  extra_copies: number;
  extra_bytes: number;
  inside_share: number;
  tag: FolderTag;
}

export interface InsightPair {
  a: FolderRef;
  b: FolderRef;
  shared_groups: number;
}

/** The backend sends ids and numbers; the wording is in InsightsPanel. */
export type InsightHeadline =
  | { id: 'top_folder'; folder: FolderRef; photos: number; photos_with_duplicate: number; tag: FolderTag }
  | { id: 'split'; groups_in_one_folder: number; groups_across_folders: number };

export type InsightTip =
  | { id: 'copy_suffix'; count: number }
  | { id: 'number_suffix'; count: number }
  | { id: 'folder_pair'; a: FolderRef; b: FolderRef; shared_groups: number }
  | { id: 'same_folder'; folder: FolderRef; photos_with_duplicate: number }
  | { id: 'spread'; count: number };

export interface InsightsResponse {
  status: string;
  scan_id: string;
  root: string;
  root_name: string;
  headlines: InsightHeadline[];
  totals: {
    photos: number;
    folders: number;
    folders_with_duplicates: number;
    duplicate_groups: number;
    groups_in_one_folder: number;
    groups_across_folders: number;
    groups_across_3_plus_folders: number;
    extra_copies: number;
    extra_bytes: number;
  };
  folders: InsightFolder[];
  folders_with_duplicates_not_shown: number;
  pairs: InsightPair[];
  tips: InsightTip[];
  coverage: Coverage;
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