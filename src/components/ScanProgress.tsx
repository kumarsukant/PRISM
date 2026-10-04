// src/components/ScanProgress.tsx

import React, { useEffect, useState } from 'react';
import { Loader2, CheckCircle2, AlertCircle } from 'lucide-react';

interface ScanProgressProps {
  scanId: string;
  totalPhotos: number;
  exactDuplicates: number;
  visualDuplicates: number;
  duplicateGroups: number;
}

export const ScanProgress: React.FC<ScanProgressProps> = ({
  scanId,
  totalPhotos,
  exactDuplicates,
  visualDuplicates,
  duplicateGroups,
}) => {
  const [isComplete, setIsComplete] = useState(false);

  useEffect(() => {
    // Scan is complete when this component mounts
    // In a real implementation, you'd poll /scan/progress endpoint
    setIsComplete(true);
  }, [scanId]);

  const hasErrors = duplicateGroups === 0 && totalPhotos > 0;

  return (
    <div className="w-full max-w-2xl mx-auto p-8 bg-white dark:bg-slate-900 rounded-lg shadow-lg">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          {isComplete ? (
            <CheckCircle2 className="w-8 h-8 text-green-600 dark:text-green-400" />
          ) : (
            <Loader2 className="w-8 h-8 text-amber-600 dark:text-amber-400 animate-spin" />
          )}
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white">
            {isComplete ? 'Scan Complete' : 'Scanning...'}
          </h2>
        </div>
        <p className="text-slate-600 dark:text-slate-400 text-sm">
          Scan ID: <code className="font-mono text-xs">{scanId}</code>
        </p>
      </div>

      {/* Results Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {/* Total Photos */}
        <div className="p-4 bg-slate-100 dark:bg-slate-800 rounded-lg">
          <p className="text-sm font-semibold text-slate-600 dark:text-slate-400 mb-1">
            Photos Found
          </p>
          <p className="text-2xl font-bold text-slate-900 dark:text-white">{totalPhotos}</p>
        </div>

        {/* Exact Duplicates */}
        <div className="p-4 bg-amber-100 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
          <p className="text-sm font-semibold text-amber-900 dark:text-amber-200 mb-1">
            Exact Matches
          </p>
          <p className="text-2xl font-bold text-amber-900 dark:text-amber-400">
            {exactDuplicates}
          </p>
        </div>

        {/* Visual Duplicates */}
        <div className="p-4 bg-blue-100 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
          <p className="text-sm font-semibold text-blue-900 dark:text-blue-200 mb-1">
            Visual Matches
          </p>
          <p className="text-2xl font-bold text-blue-900 dark:text-blue-400">
            {visualDuplicates}
          </p>
        </div>

        {/* Duplicate Groups */}
        <div className="p-4 bg-purple-100 dark:bg-purple-900/20 rounded-lg border border-purple-200 dark:border-purple-800">
          <p className="text-sm font-semibold text-purple-900 dark:text-purple-200 mb-1">
            Groups Found
          </p>
          <p className="text-2xl font-bold text-purple-900 dark:text-purple-400">
            {duplicateGroups}
          </p>
        </div>
      </div>

      {/* Status Message */}
      {hasErrors && totalPhotos > 0 ? (
        <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800 flex items-start gap-3 mb-6">
          <AlertCircle className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-blue-800 dark:text-blue-300">
            No duplicates found in this folder. All {totalPhotos} photos are unique.
          </p>
        </div>
      ) : null}

      {/* Summary */}
      <div className="p-4 bg-slate-100 dark:bg-slate-800 rounded-lg">
        <p className="text-sm text-slate-700 dark:text-slate-300">
          Scan identified{' '}
          <strong className="font-semibold">
            {duplicateGroups} group{duplicateGroups !== 1 ? 's' : ''} of duplicate photos
          </strong>
          . You can review and delete duplicates in the next step.
        </p>
      </div>
    </div>
  );
};
