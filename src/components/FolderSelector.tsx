// src/components/FolderSelector.tsx

import React, { useState } from 'react';
import { open } from '@tauri-apps/plugin-dialog';
import { FolderOpen, AlertCircle } from 'lucide-react';

interface FolderSelectorProps {
  onFolderSelect: (folderPath: string) => void;
  isLoading: boolean;
}

export const FolderSelector: React.FC<FolderSelectorProps> = ({
  onFolderSelect,
  isLoading,
}) => {
  const [selectedFolder, setSelectedFolder] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSelectFolder = async () => {
    try {
      setError(null);
      const selected = await open({
        directory: true,
        multiple: false,
        title: 'Select Photo Folder',
      });

      if (selected && typeof selected === 'string') {
        setSelectedFolder(selected);
        onFolderSelect(selected);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to select folder';
      setError(errorMessage);
      console.error('Folder selection error:', err);
    }
  };

  return (
    <div className="w-full max-w-md mx-auto p-8 bg-white dark:bg-slate-900 rounded-lg shadow-lg">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">
          Select Photo Folder
        </h2>
        <p className="text-slate-600 dark:text-slate-400">
          Choose a folder containing your photos to scan for duplicates
        </p>
      </div>

      {selectedFolder ? (
        <div className="mb-6 p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
          <p className="text-sm font-semibold text-amber-900 dark:text-amber-200 mb-2">
            Selected Folder:
          </p>
          <p className="text-sm text-amber-800 dark:text-amber-300 break-all font-mono">
            {selectedFolder}
          </p>
        </div>
      ) : null}

      {error ? (
        <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-red-800 dark:text-red-300">{error}</p>
        </div>
      ) : null}

      <button
        onClick={handleSelectFolder}
        disabled={isLoading}
        className={isLoading ? 'w-full py-3 px-4 rounded-lg font-semibold flex items-center justify-center gap-2 bg-amber-400 dark:bg-amber-600 text-amber-900 cursor-not-allowed opacity-75' : 'w-full py-3 px-4 rounded-lg font-semibold flex items-center justify-center gap-2 bg-amber-500 dark:bg-amber-700 text-white hover:bg-amber-600 dark:hover:bg-amber-800 active:scale-95'}
      >
        {isLoading ? (
          <>
            <div className="w-5 h-5 border-2 border-amber-900 border-t-transparent rounded-full animate-spin" />
            Scanning...
          </>
        ) : (
          <>
            <FolderOpen className="w-5 h-5" />
            {selectedFolder ? 'Change Folder' : 'Select Folder'}
          </>
        )}
      </button>

      <div className="mt-6 p-4 bg-slate-100 dark:bg-slate-800 rounded-lg">
        <p className="text-xs text-slate-600 dark:text-slate-400">
          💡 <strong>Tip:</strong> Prism scans this folder and all its subfolders and finds exact
          copies of your photos. Nothing is changed until you choose what to delete.
        </p>
      </div>
    </div>
  );
};