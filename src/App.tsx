// src/App.tsx - Main application component

import React, { useEffect, useState } from 'react';
import { FolderSelector } from './components/FolderSelector';
import { ScanProgress } from './components/ScanProgress';
import { ResultsGrid } from './components/ResultsGrid';
import { api } from './services/api';
import { ScanningView } from './components/ScanningView';
import type { ScanSummary, ScanResults, ScanProgressResponse } from './types';

type AppState = 'starting' | 'folder-select' | 'scanning' | 'results' | 'error';

interface AppData {
  state: AppState;
  error?: string;
  scanResponse?: ScanSummary;
  scanResults?: ScanResults;
}

function App() {
  const [appData, setAppData] = useState<AppData>({ state: 'starting' });
  const [isDeleting, setIsDeleting] = useState(false);
  const [scanProgress, setScanProgress] = useState<ScanProgressResponse | null>(null);

  // Wait for the bundled backend to come up before showing anything
  useEffect(() => {
    let cancelled = false;
    api
      .waitForBackend()
      .then(() => {
        if (!cancelled) setAppData({ state: 'folder-select' });
      })
      .catch((error) => {
        if (cancelled) return;
        console.error('Backend did not start:', error);
        setAppData({
          state: 'error',
          error: error instanceof Error ? error.message : 'The backend did not start',
        });
      });
    return () => {
      cancelled = true;
    };
  }, []);
  const handleFolderSelect = async (folderPath: string) => {
    try {
      setScanProgress(null);
      setAppData({ state: 'scanning' });

      // Start the scan (returns immediately), then follow its progress
      const started = await api.startScan(folderPath);
      const finished = await api.waitForScan(started.scan_id, setScanProgress);

      // Fetch results
      const scanResults = await api.getScanResults(started.scan_id);

      setAppData({
        state: 'results',
        scanResponse: {
          status: 'completed',
          scan_id: started.scan_id,
          total_photos: finished.total_photos,
          exact_duplicates: finished.exact_duplicates,
          visual_duplicates: finished.visual_duplicates,
          duplicate_groups: finished.duplicate_groups,
          message: `Scan complete: ${finished.total_photos} photos, ${finished.duplicate_groups} groups found`,
        },
        scanResults,
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Scan failed';
      console.error('Scan error:', error);
      setAppData({
        state: 'error',
        error: errorMessage,
      });
    }
  };
  const handleSelectGroups = (_groupIds: string[]) => {
    // This will be used to track selection
    // Actual deletion happens via button click in ResultsGrid
  };

  const handleDeleteDuplicates = async (groupIds: string[]) => {
    if (!appData.scanResponse) return;

    try {
      setIsDeleting(true);
      await api.deleteDuplicates(appData.scanResponse.scan_id, groupIds);

      // Reset to folder select after deletion
      setTimeout(() => {
        setAppData({ state: 'folder-select' });
        setIsDeleting(false);
      }, 1000);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Deletion failed';
      console.error('Delete error:', error);
      setAppData({
        state: 'error',
        error: errorMessage,
      });
      setIsDeleting(false);
    }
  };

  const handleReset = () => {
    setAppData({ state: 'folder-select' });
  };

  // Render based on state
  if (appData.state === 'starting') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-amber-50 to-slate-50 dark:from-slate-950 dark:to-slate-900 flex items-center justify-center p-4">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-amber-200 dark:border-amber-800 border-t-amber-600 dark:border-t-amber-400 rounded-full animate-spin"></div>
          <p className="text-slate-600 dark:text-slate-400">Starting Prism...</p>
        </div>
      </div>
    );
  }
  if (appData.state === 'folder-select') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-amber-50 to-slate-50 dark:from-slate-950 dark:to-slate-900 flex items-center justify-center p-4">
        <FolderSelector
          onFolderSelect={handleFolderSelect}
          isLoading={false}
        />
      </div>
    );
  }

  if (appData.state === 'scanning') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-amber-50 to-slate-50 dark:from-slate-950 dark:to-slate-900 flex items-center justify-center p-4">
        <ScanningView progress={scanProgress} />
      </div>
    );
  }
  if (appData.state === 'results' && appData.scanResponse && appData.scanResults) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-amber-50 to-slate-50 dark:from-slate-950 dark:to-slate-900 p-8">
        <div className="max-w-6xl mx-auto">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-4xl font-bold text-slate-900 dark:text-white mb-2">
              📸 Prism
            </h1>
            <p className="text-slate-600 dark:text-slate-400">
              See your photos clearly • Remove duplicates with confidence
            </p>
          </div>

          {/* Scan Results */}
          <ScanProgress
            scanId={appData.scanResponse.scan_id}
            totalPhotos={appData.scanResponse.total_photos}
            exactDuplicates={appData.scanResponse.exact_duplicates}
            visualDuplicates={appData.scanResponse.visual_duplicates}
            duplicateGroups={appData.scanResponse.duplicate_groups}
          />

          {/* Duplicate Groups */}
          {appData.scanResults.groups.length > 0 ? (
            <div className="mt-8">
              <ResultsGrid
                groups={appData.scanResults.groups}
                onSelectGroups={handleSelectGroups}
                onDelete={handleDeleteDuplicates}
                isDeleting={isDeleting}
              />
            </div>
          ) : (
            <div className="mt-8 p-8 bg-white dark:bg-slate-900 rounded-lg shadow-lg text-center">
              <p className="text-lg text-slate-600 dark:text-slate-400">
                No duplicates found! Your photos are all unique.
              </p>
              <button
                onClick={handleReset}
                className="mt-4 px-6 py-2 bg-amber-600 dark:bg-amber-700 text-white rounded-lg font-semibold hover:bg-amber-700 dark:hover:bg-amber-800"
              >
                Scan Another Folder
              </button>
            </div>
          )}

          {/* Reset Button */}
          <div className="mt-8 text-center">
            <button
              onClick={handleReset}
              className="text-sm text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white font-semibold"
            >
              ← Back to Folder Selection
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Error state
  return (
    <div className="min-h-screen bg-gradient-to-br from-red-50 to-slate-50 dark:from-slate-950 dark:to-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md p-8 bg-white dark:bg-slate-900 rounded-lg shadow-lg">
        <div className="text-center">
          <div className="text-4xl mb-4">⚠️</div>
          <h2 className="text-2xl font-bold text-red-600 dark:text-red-400 mb-2">
            Error
          </h2>
          <p className="text-slate-600 dark:text-slate-400 mb-6">
            {appData.error || 'An unknown error occurred'}
          </p>
          <button
            onClick={handleReset}
            className="w-full py-3 px-4 bg-amber-600 dark:bg-amber-700 text-white rounded-lg font-semibold hover:bg-amber-700 dark:hover:bg-amber-800"
          >
            Try Again
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;
