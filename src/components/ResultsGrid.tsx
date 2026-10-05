// src/components/ResultsGrid.tsx

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Check, ChevronLeft, ChevronRight, Trash2, Loader2 } from 'lucide-react';
import type { DuplicateGroup } from '../types';
import { api } from '../services/api';

// How many duplicate groups are shown at once. A small page keeps the window responsive and
// only loads thumbnails for the groups you are actually looking at.
const PAGE_SIZE = 20;

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
  const [page, setPage] = useState(1);

  const totalPages = Math.max(1, Math.ceil(groups.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const startIndex = (currentPage - 1) * PAGE_SIZE;
  const pageGroups = groups.slice(startIndex, startIndex + PAGE_SIZE);
  const pageIds = pageGroups.map((g) => g.id);

  // When the page changes, bring the top of this list into view (not the top of the window, which
  // would land on the summary). Compares with the previous page rather than skipping the first
  // render, because React StrictMode runs effects twice in development.
  const listTopRef = useRef<HTMLDivElement>(null);
  const shownPage = useRef(currentPage);
  useEffect(() => {
    if (shownPage.current === currentPage) return;
    shownPage.current = currentPage;
    listTopRef.current?.scrollIntoView({ block: 'start' });
  }, [currentPage]);

  // Forget selected groups that are no longer in the list
  useEffect(() => {
    setSelectedGroupIds((previous) => {
      const valid = new Set(groups.map((g) => g.id));
      const kept = Array.from(previous).filter((id) => valid.has(id));
      return kept.length === previous.size ? previous : new Set(kept);
    });
  }, [groups]);

  const updateSelection = (next: Set<string>) => {
    setSelectedGroupIds(next);
    onSelectGroups(Array.from(next));
  };

  const handleToggleGroup = (groupId: string) => {
    const next = new Set(selectedGroupIds);
    if (next.has(groupId)) {
      next.delete(groupId);
    } else {
      next.add(groupId);
    }
    updateSelection(next);
  };

  const allOnPageSelected = pageIds.length > 0 && pageIds.every((id) => selectedGroupIds.has(id));

  const handleTogglePage = () => {
    const next = new Set(selectedGroupIds);
    if (allOnPageSelected) {
      pageIds.forEach((id) => next.delete(id));
    } else {
      pageIds.forEach((id) => next.add(id));
    }
    updateSelection(next);
  };

  const handleSelectEverything = () => updateSelection(new Set(groups.map((g) => g.id)));
  const handleClearSelection = () => updateSelection(new Set());

  // Space freed by deleting the selected groups (every photo except the kept one)
  const selectedBytes = useMemo(() => {
    let total = 0;
    for (const group of groups) {
      if (!selectedGroupIds.has(group.id)) continue;
      for (const photo of group.photos) {
        if (!photo.is_kept) total += photo.file_size_bytes;
      }
    }
    return total;
  }, [groups, selectedGroupIds]);

  const selectedSizeMb = (selectedBytes / (1024 * 1024)).toFixed(2);
  const selectedOnPage = pageIds.filter((id) => selectedGroupIds.has(id)).length;
  const selectedElsewhere = selectedGroupIds.size - selectedOnPage;
  const multiplePages = totalPages > 1;

  const renderPager = () =>
    multiplePages ? (
      <div className="flex items-center justify-between gap-4 my-4">
        <button
          onClick={() => setPage(Math.max(1, currentPage - 1))}
          disabled={currentPage === 1}
          className="flex items-center gap-1 px-4 py-2 text-sm font-semibold rounded-lg border border-amber-300 dark:border-amber-700 text-amber-700 dark:text-amber-300 bg-white dark:bg-slate-800 hover:bg-amber-50 dark:hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <ChevronLeft className="w-4 h-4" />
          Previous
        </button>
        <span className="text-sm font-semibold text-slate-600 dark:text-slate-400">
          Page {currentPage} of {totalPages}
        </span>
        <button
          onClick={() => setPage(Math.min(totalPages, currentPage + 1))}
          disabled={currentPage === totalPages}
          className="flex items-center gap-1 px-4 py-2 text-sm font-semibold rounded-lg border border-amber-300 dark:border-amber-700 text-amber-700 dark:text-amber-300 bg-white dark:bg-slate-800 hover:bg-amber-50 dark:hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Next
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    ) : null;

  return (
    <div
      ref={listTopRef}
      className="w-full max-w-4xl mx-auto p-8 bg-white dark:bg-slate-900 rounded-lg shadow-lg scroll-mt-28"
    >
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">
          Duplicate Groups
        </h2>
        <p className="text-slate-600 dark:text-slate-400">
          {groups.length} group{groups.length !== 1 ? 's' : ''} found
          {multiplePages
            ? `. Showing ${startIndex + 1} to ${Math.min(startIndex + PAGE_SIZE, groups.length)}.`
            : '.'}{' '}
          {selectedGroupIds.size > 0
            ? `${selectedGroupIds.size} group${selectedGroupIds.size !== 1 ? 's' : ''} selected for deletion (${selectedSizeMb} MB)`
            : 'Select groups to delete'}
        </p>
      </div>

      {/* Selection controls */}
      <div className="mb-2 flex flex-wrap items-center gap-x-6 gap-y-2">
        <button
          onClick={handleTogglePage}
          className="text-sm font-semibold text-amber-600 dark:text-amber-400 hover:text-amber-700 dark:hover:text-amber-300"
        >
          {allOnPageSelected
            ? `\u2713 ${multiplePages ? 'Deselect this page' : 'Deselect all'}`
            : `\u2610 ${multiplePages ? 'Select this page' : 'Select all'}`}
        </button>
        {multiplePages && selectedGroupIds.size < groups.length && (
          <button
            onClick={handleSelectEverything}
            className="text-sm font-semibold text-amber-600 dark:text-amber-400 hover:text-amber-700 dark:hover:text-amber-300"
          >
            Select all {groups.length} groups
          </button>
        )}
        {selectedGroupIds.size > 0 && (
          <button
            onClick={handleClearSelection}
            className="text-sm font-semibold text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200"
          >
            Clear selection
          </button>
        )}
      </div>

      {renderPager()}

      {/* Groups List */}
      <div className="space-y-4">
        {pageGroups.map((group) => {
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
                      onChange={() => handleToggleGroup(group.id)}
                      className="w-5 h-5 rounded border-slate-300 dark:border-slate-600 text-amber-600 dark:text-amber-500 accent-amber-600 cursor-pointer"
                      onClick={(e) => e.stopPropagation()}
                    />
                    <span className="text-sm font-semibold text-slate-500 dark:text-slate-400">
                      {group.type === 'exact' ? '\u2713 Exact Match' : '\u2248 Visual Match'}
                    </span>
                    <span className="text-sm font-semibold text-amber-600 dark:text-amber-400">
                      {Math.round(group.confidence * 100)}% confidence
                    </span>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm font-bold text-red-600 dark:text-red-400">
                    {duplicates.length} duplicate{duplicates.length !== 1 ? 's' : ''} &bull; {duplicateSizeMb} MB
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
                      src={api.thumbnailUrl(keptPhoto.file_path)}
                      alt={keptPhoto.file_path}
                      loading="lazy"
                      className="w-full h-40 object-contain bg-slate-200 dark:bg-slate-800 rounded mb-2"
                    />
                    <p className="text-xs text-slate-700 dark:text-slate-300 truncate mb-1 font-mono">
                      {keptPhoto.file_path.split('\\').pop()}
                    </p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      {(keptPhoto.file_size_bytes / 1024).toFixed(1)} KB &bull;{' '}
                      {keptPhoto.width}&times;{keptPhoto.height}
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
                      src={api.thumbnailUrl(photo.file_path)}
                      alt={photo.file_path}
                      loading="lazy"
                      className="w-full h-40 object-contain bg-slate-200 dark:bg-slate-800 rounded mb-2"
                    />
                    <p className="text-xs text-slate-700 dark:text-slate-300 truncate mb-1 font-mono">
                      {photo.file_path.split('\\').pop()}
                    </p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      {(photo.file_size_bytes / 1024).toFixed(1)} KB &bull;{' '}
                      {photo.width}&times;{photo.height}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {renderPager()}

      {/* Delete bar: one compact row, pinned, so it covers as little of the groups as possible */}
      {selectedGroupIds.size > 0 && (
        <div className="sticky bottom-4 mt-8 px-4 py-3 bg-amber-50 dark:bg-amber-950 rounded-lg border border-amber-200 dark:border-amber-800 shadow-xl flex items-center justify-between gap-4">
          <p className="min-w-0 text-sm text-amber-900 dark:text-amber-200">
            <strong className="font-semibold">
              {selectedGroupIds.size} group{selectedGroupIds.size !== 1 ? 's' : ''} ({selectedSizeMb} MB)
            </strong>
            {selectedElsewhere > 0 ? `, including ${selectedElsewhere} on other pages` : ''}. Files go to
            the Recycle Bin, so you can undo this.
          </p>
          <button
            onClick={() => onDelete(Array.from(selectedGroupIds))}
            disabled={isDeleting}
            className={`shrink-0 py-2 px-4 rounded-lg font-semibold flex items-center justify-center gap-2 transition-all ${
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