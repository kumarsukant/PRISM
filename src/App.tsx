// src/App.tsx - Main application component

import React, { useEffect, useState } from 'react';
import { FolderSelector } from './components/FolderSelector';
import { ScanProgress } from './components/ScanProgress';
import { ResultsGrid } from './components/ResultsGrid';
import { api } from './services/api';
import type { ScanStartResponse, ScanResults } from './types';

type AppState = 'folder-select' | 'scanning' | 'results' | 'error';

interface AppData {
  state: AppState;
  error?: string;
  scanResponse?: ScanStartResponse;
  scanResults?: ScanResults;
}

function App() {
  const [appData, setAppData] = useState<AppData>({ state: 'folder-select' });
  const [isDeleting, setIsDeleting] = useState(false);

  // Check backend health on mount
  useEffect(() => {
    const checkBackend = async () => {
      try {
        await api.checkHealth();
        console.log('✓ Backend is running');
      } catch (error) {
        console.error('Backend connection failed:', error);
        setAppData({
          state: 'error',
          error: 'Cannot connect to backend. Make sure the FastAPI server is running on http://127.0.0.1:8000',
        });
      }
    };

    checkBackend();
  }, []);

  const handleFolderSelect = async (folderPath: string) => {
    try {
      setAppData({ state: 'scanning' });

      // Start scan
      const scanResponse = await api.startScan(folderPath);

      // Fetch results
      const scanResults = await api.getScanResults(scanResponse.scan_id);

      setAppData({
        state: 'results',
        scanResponse,
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
  if (appData.state === 'folder-select') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-amber-50 to-slate-50 dark:from-slate-950 dark:to-slate-900 flex items-center justify-center p-4">
        <FolderSelector
          onFolderSelect={handleFolderSelect}
          isLoading={appData.state === 'scanning'}
        />
      </div>
    );
  }

  if (appData.state === 'scanning') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-amber-50 to-slate-50 dark:from-slate-950 dark:to-slate-900 flex items-center justify-center p-4">
        <div className="w-full max-w-2xl">
          <div className="text-center mb-8">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-white dark:bg-slate-800 rounded-full shadow-md mb-4">
              <div className="w-3 h-3 bg-amber-500 rounded-full animate-pulse"></div>
              <span className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                Analyzing photos...
              </span>
            </div>
          </div>
          <div className="bg-white dark:bg-slate-800 rounded-lg shadow-lg p-8">
            <div className="flex flex-col items-center gap-4">
              <div className="w-12 h-12 border-4 border-amber-200 dark:border-amber-800 border-t-amber-600 dark:border-t-amber-400 rounded-full animate-spin"></div>
              <p className="text-slate-600 dark:text-slate-400">
                Scanning folder for photos and detecting duplicates...
              </p>
            </div>
          </div>
        </div>
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
