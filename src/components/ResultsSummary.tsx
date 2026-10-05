// src/components/ResultsSummary.tsx
// Compact summary above the duplicate groups: one line of counts, a short "what now" line, and a
// notice for photos the scanner could not read. Replaces the old tall "Scan Complete" card.

import React, { useMemo } from 'react';
import { AlertCircle } from 'lucide-react';
import type { DuplicateGroup, SkippedFile } from '../types';

interface ResultsSummaryProps {
  folderPath: string;
  totalPhotos: number;
  groups: DuplicateGroup[];
  skippedCount: number;
  skipped: SkippedFile[];
  hasDeleted: boolean;
}

const count = (n: number, one: string, many: string) => `${n.toLocaleString()} ${n === 1 ? one : many}`;

function formatSize(bytes: number): string {
  const mb = bytes / (1024 * 1024);
  return mb >= 1024 ? `${(mb / 1024).toFixed(1)} GB` : `${mb.toFixed(1)} MB`;
}

export const ResultsSummary: React.FC<ResultsSummaryProps> = ({
  folderPath,
  totalPhotos,
  groups,
  skippedCount,
  skipped,
  hasDeleted,
}) => {
  // Everything except the kept photo of each group is an extra copy
  const { extraCopies, extraBytes } = useMemo(() => {
    let copies = 0;
    let bytes = 0;
    for (const group of groups) {
      for (const photo of group.photos) {
        if (!photo.is_kept) {
          copies += 1;
          bytes += photo.file_size_bytes;
        }
      }
    }
    return { extraCopies: copies, extraBytes: bytes };
  }, [groups]);

  // With no groups left, the empty panel below already says what happened
  let status: string | null = null;
  if (groups.length > 0) {
    status = hasDeleted
      ? `${count(groups.length, 'group', 'groups')} left to review.`
      : 'Prism keeps one photo from each group (marked KEPT) and moves the extra copies to the Recycle Bin. Select the groups you want to clean up.';
  }

  const allInUse = skipped.length > 0 && skipped.every((s) => s.reason === 'open in another program');
  const unlisted = skippedCount - skipped.length;

  return (
    <section className="max-w-4xl mx-auto" aria-label="Scan summary">
      <div className="px-5 py-3 bg-white dark:bg-slate-900 rounded-lg shadow flex flex-wrap items-center justify-between gap-x-6 gap-y-1">
        <p
          className="min-w-0 truncate font-mono text-xs text-slate-500 dark:text-slate-400"
          title={folderPath}
        >
          {folderPath}
        </p>
        <p className="text-sm text-slate-700 dark:text-slate-300">
          <strong className="text-slate-900 dark:text-white">{count(totalPhotos, 'photo', 'photos')}</strong>
          <span className="mx-2 text-slate-400" aria-hidden="true">&middot;</span>
          <strong className="text-slate-900 dark:text-white">
            {count(groups.length, 'duplicate group', 'duplicate groups')}
          </strong>
          {extraCopies > 0 && (
            <>
              <span className="mx-2 text-slate-400" aria-hidden="true">&middot;</span>
              {count(extraCopies, 'extra copy', 'extra copies')} ({formatSize(extraBytes)})
            </>
          )}
        </p>
      </div>

      {status && <p className="mt-3 px-1 text-sm text-slate-600 dark:text-slate-400">{status}</p>}

      {skippedCount > 0 && (
        <div
          className="mt-3 p-4 rounded-lg border bg-amber-50 dark:bg-amber-900/20 border-amber-300 dark:border-amber-700 text-amber-900 dark:text-amber-200 flex items-start gap-3"
          role="status"
        >
          <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <div className="text-sm min-w-0">
            <p className="font-semibold">
              {count(skippedCount, 'photo', 'photos')} couldn&apos;t be read and{' '}
              {skippedCount === 1 ? 'was' : 'were'} skipped, so {skippedCount === 1 ? "it isn't" : "they aren't"} in
              these results.
            </p>
            <p className="mt-1">
              {allInUse
                ? `Close the program that's using ${skippedCount === 1 ? 'it' : 'them'}, then scan again.`
                : 'See why below, then scan again.'}
            </p>
            <details className="mt-2">
              <summary className="cursor-pointer font-semibold">
                Show {skippedCount === 1 ? 'file' : 'files'}
              </summary>
              <ul className="mt-2 space-y-1 font-mono text-xs">
                {skipped.map((s) => (
                  <li key={s.path} className="truncate" title={s.path}>
                    {s.file}: {s.reason}
                  </li>
                ))}
                {unlisted > 0 && <li>...and {unlisted.toLocaleString()} more</li>}
              </ul>
            </details>
          </div>
        </div>
      )}
    </section>
  );
};
