// src/components/ResultsGrid.tsx

import React, { useState } from 'react';
import { Check, Trash2, Image as ImageIcon, Loader2 } from 'lucide-react';
import type { DuplicateGroup } from '../types';

interface ResultsGridProps {
  groups: DuplicateGroup[];
  onSelectGroups: (groupIds: string[]) => void;
  onDelete: (groupIds: string[]) => void;
  isDeleting: boolean;
}

export const ResultsGrid: React.FC<ResultsGridProps> = ({
  groups,
  onSelectGroups,
  onDelete,
  isDeleting,
}) => {
  const [selectedGroupIds, setSelectedGroupIds] = useState<Set<string>>(new Set());

  const handleToggleGroup = (groupId: string) => {
    const newSelected = new Set(selectedGroupIds);
    if (newSelected.has(groupId)) {
      newSelected.delete(groupId);
    } else {
      newSelected.add(groupId);
    }
    setSelectedGroupIds(newSelected);
    onSelectGroups(Array.from(newSelected));
  };

  const handleSelectAll = () => {
    if (selectedGroupIds.size === groups.length) {
      setSelectedGroupIds(new Set());
      onSelectGroups([]);
    } else {
      const allIds = new Set(groups.map((g) => g.id));
      setSelectedGroupIds(allIds);
      onSelectGroups(Array.from(allIds));
    }
  };

  const calculateTotalSize = (groupIds: string[]) => {
    let totalBytes = 0;
    groupIds.forEach((groupId) => {
      const group = groups.find((g) => g.id === groupId);
      if (group) {
        // Count all non-kept photos
        group.photos.forEach((photo) => {
          if (!photo.is_kept) {
            totalBytes += photo.file_size_bytes;
          }
        });
      }
    });
    return totalBytes;
  };

  const selectedSize = calculateTotalSize(Array.from(selectedGroupIds));
  const selectedSizeMb = (selectedSize / (1024 * 1024)).toFixed(2);

  return (
    <div className="w-full max-w-4xl mx-auto p-8 bg-white dark:bg-slate-900 rounded-lg shadow-lg">
      {/* Header */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">
          Duplicate Groups
        </h2>
        <p className="text-slate-600 dark:text-slate-400">
          {groups.length} group{groups.length !== 1 ? 's' : ''} found.{' '}
          {selectedGroupIds.size > 0
            ? `${selectedGroupIds.size} group${selectedGroupIds.size !== 1 ? 's' : ''} selected for deletion (${selectedSizeMb} MB)`
            : 'Select groups to delete'}
        </p>
      </div>

      {/* Select All */}
      <button
        onClick={handleSelectAll}
        className="mb-6 text-sm font-semibold text-amber-600 dark:text-amber-400 hover:text-amber-700 dark:hover:text-amber-300"
      >
        {selectedGroupIds.size === groups.length ? '✓ Deselect All' : '☐ Select All'}
      </button>

      {/* Groups List */}
      <div className="space-y-4">
        {groups.map((group) => {
          const isSelected = selectedGroupIds.has(group.id);
          const keptPhoto = group.photos.find((p) => p.is_kept);
          const duplicates = group.photos.filter((p) => !p.is_kept);
          const duplicateSize = duplicates.reduce((sum, p) => sum + p.file_size_bytes, 0);
          const duplicateSizeMb = (duplicateSize / (1024 * 1024)).toFixed(2);

          return (
            <div
              key={group.id}
              className={`p-6 rounded-lg border-2 transition-all cursor-pointer ${
                isSelected
                  ? 'bg-amber-50 dark:bg-amber-900/20 border-amber-300 dark:border-amber-600'
                  : 'bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700 hover:border-amber-200 dark:hover:border-amber-700'
              }`}
              onClick={() => handleToggleGroup(group.id)}
            >
              {/* Group Header */}
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => {}}
                      className="w-5 h-5 rounded border-slate-300 dark:border-slate-600 text-amber-600 dark:text-amber-500 cursor-pointer"
                      onClick={(e) => e.stopPropagation()}
                    />
                    <span className="text-sm font-semibold text-slate-500 dark:text-slate-400">
                      {group.type === 'exact' ? '✓ Exact Match' : '≈ Visual Match'}
                    </span>
                    <span className="text-sm font-semibold text-amber-600 dark:text-amber-400">
                      {Math.round(group.confidence * 100)}% confidence
                    </span>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm font-bold text-red-600 dark:text-red-400">
                    {duplicates.length} duplicate{duplicates.length !== 1 ? 's' : ''} • {duplicateSizeMb} MB
                  </p>
                </div>
              </div>

              {/* Photos Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {/* Kept Photo */}
                {keptPhoto && (
                  <div className="p-3 bg-green-100 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
                    <div className="flex items-center gap-2 mb-2">
                      <Check className="w-4 h-4 text-green-600 dark:text-green-400" />
                      <span className="text-xs font-semibold text-green-700 dark:text-green-300">
                        KEPT
                      </span>
                    </div>
                    <img
                      src={`http://127.0.0.1:8000/thumbnail?path=${encodeURIComponent(keptPhoto.file_path)}`}
                      alt={keptPhoto.file_path}
                      loading="lazy"
                      className="w-full h-40 object-contain bg-slate-200 dark:bg-slate-800 rounded mb-2"
                    />
                    <p className="text-xs text-slate-700 dark:text-slate-300 truncate mb-1 font-mono">
                      {keptPhoto.file_path.split('\\').pop()}
                    </p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      {(keptPhoto.file_size_bytes / 1024).toFixed(1)} KB •{' '}
                      {keptPhoto.width}×{keptPhoto.height}
                    </p>
                  </div>
                )}

                {/* Duplicate Photos */}
                {duplicates.map((photo) => (
                  <div
                    key={photo.id}
                    className="p-3 bg-red-100 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800"
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <Trash2 className="w-4 h-4 text-red-600 dark:text-red-400" />
                      <span className="text-xs font-semibold text-red-700 dark:text-red-300">
                        DELETE
                      </span>
                    </div>
                    <img
                      src={`http://127.0.0.1:8000/thumbnail?path=${encodeURIComponent(photo.file_path)}`}
                      alt={photo.file_path}
                      loading="lazy"
                      className="w-full h-40 object-contain bg-slate-200 dark:bg-slate-800 rounded mb-2"
                    />
                    <p className="text-xs text-slate-700 dark:text-slate-300 truncate mb-1 font-mono">
                      {photo.file_path.split('\\').pop()}
                    </p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      {(photo.file_size_bytes / 1024).toFixed(1)} KB •{' '}
                      {photo.width}×{photo.height}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* Delete Summary */}
      {selectedGroupIds.size > 0 && (
        <div className="mt-8 p-6 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
          <p className="text-sm font-semibold text-amber-900 dark:text-amber-200 mb-2">
            Delete Summary
          </p>
          <p className="text-sm text-amber-800 dark:text-amber-300 mb-4">
            You're about to delete {selectedGroupIds.size} group{selectedGroupIds.size !== 1 ? 's' : ''} of
            duplicates ({selectedSizeMb} MB). This action moves files to Recycle Bin and can
            be undone.
          </p>
          <button
            onClick={() => onDelete(Array.from(selectedGroupIds))}
            disabled={isDeleting}
            className={`w-full py-3 px-4 rounded-lg font-semibold flex items-center justify-center gap-2 transition-all ${
              isDeleting
                ? 'bg-red-400 dark:bg-red-600 text-white cursor-not-allowed opacity-75'
                : 'bg-red-600 dark:bg-red-700 text-white hover:bg-red-700 dark:hover:bg-red-800 active:scale-95'
            }`}
          >
            {isDeleting ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Deleting...
              </>
            ) : (
              <>
                <Trash2 className="w-5 h-5" />
                Delete {selectedGroupIds.size} Group{selectedGroupIds.size !== 1 ? 's' : ''}
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );
};

// Small import we need
import { Loader2 } from 'lucide-react';
