// src/App.tsx - Main application component

import React, { useEffect, useState } from 'react';
import { FolderSelector } from './components/FolderSelector';
import { ResultsSummary, ReviewHint } from './components/ResultsSummary';
import { ResultsGrid } from './components/ResultsGrid';
import { InsightsPanel } from './components/InsightsPanel';
import { ResultsTabs, panelId, tabId } from './components/ResultsTabs';
import { api } from './services/api';
import { ScanningView } from './components/ScanningView';
import type { ScanSummary, ScanResults, ScanProgressResponse, DeleteResponse } from './types';

type AppState = 'starting' | 'folder-select' | 'scanning' | 'results' | 'error';
type ResultsTab = 'insights' | 'review';

const RESULTS_TABS: { id: ResultsTab; label: string }[] = [
  { id: 'insights', label: 'Insights' },
  { id: 'review', label: 'Review duplicates' },
];

interface Notice {
  kind: 'success' | 'warning' | 'error';
  title: string;
  details?: string[];
}
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
  const [notice, setNotice] = useState<Notice | null>(null);
  const [clearedByDeleting, setClearedByDeleting] = useState(false);
  const [tab, setTab] = useState<ResultsTab>('insights');
  const [insightsVersion, setInsightsVersion] = useState(0);

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
      setNotice(null);
      setClearedByDeleting(false);
      setAppData({ state: 'scanning' });

      // Start the scan (returns immediately), then follow its progress
      const started = await api.startScan(folderPath);
      const finished = await api.waitForScan(started.scan_id, setScanProgress);

      // Fetch results
      const scanResults = await api.getScanResults(started.scan_id);

      setTab('insights'); // a new scan opens on Insights
      setAppData({
        state: 'results',
        scanResponse: {
          status: 'completed',
          scan_id: started.scan_id,
          folder_path: folderPath,
          total_photos: finished.total_photos,
          exact_duplicates: finished.exact_duplicates,
          visual_duplicates: finished.visual_duplicates,
          duplicate_groups: finished.duplicate_groups,
          skipped_count: finished.skipped_count ?? 0,
          skipped: finished.skipped ?? [],
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
    const scanId = appData.scanResponse.scan_id;

    try {
      setIsDeleting(true);
      setNotice(null);
      const result: DeleteResponse = await api.deleteDuplicates(scanId, groupIds);

      // Reload what is left, so the screen always matches the backend (including any group
      // that still holds a file that could not be moved)
      const scanResults = await api.getScanResults(scanId);

      setAppData((previous) => ({
        ...previous,
        scanResults,
        scanResponse: previous.scanResponse
          ? {
              ...previous.scanResponse,
              total_photos: result.total_photos,
              exact_duplicates: result.exact_duplicates,
              visual_duplicates: result.visual_duplicates,
              duplicate_groups: result.duplicate_groups,
            }
          : previous.scanResponse,
      }));
      setClearedByDeleting(true);

      const freed = result.storage_freed_mb.toFixed(1);
      if (result.failed_count > 0) {
        setNotice({
          kind: 'warning',
          title: `Deleted ${result.files_deleted} file${result.files_deleted !== 1 ? 's' : ''} (${freed} MB freed), but ${result.failed_count} could not be moved to the Recycle Bin.`,
          details: [
            ...result.failed.slice(0, 5).map((f) => `${f.file}: ${f.reason}`),
            ...(result.failed_count > 5 ? [`...and ${result.failed_count - 5} more`] : []),
            'Those groups are still listed so you can try again.',
          ],
        });
      } else {
        setNotice({
          kind: 'success',
          title: `Deleted ${result.files_deleted} file${result.files_deleted !== 1 ? 's' : ''}, freed ${freed} MB. Moved to the Recycle Bin, so you can restore them.`,
        });
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Deletion failed';
      console.error('Delete error:', error);
      setNotice({ kind: 'error', title: `Could not delete: ${errorMessage}` });
    } finally {
      setIsDeleting(false);
      setInsightsVersion((v) => v + 1); // insights are recomputed from what is left
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
          {/* Header: sticky, so the way back is always visible */}
          <div className="sticky top-0 z-10 -mx-4 mb-8 px-4 py-4 flex items-start justify-between gap-4 bg-amber-50/90 dark:bg-slate-950/90 backdrop-blur border-b border-amber-100 dark:border-slate-800">
            <div>
              <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
                📸 Prism
              </h1>
              <p className="text-sm text-slate-600 dark:text-slate-400">
                See your photos clearly • Remove duplicates with confidence
              </p>
            </div>
            <button
              onClick={handleReset}
              className="shrink-0 px-4 py-2 text-sm font-semibold text-amber-700 dark:text-amber-300 bg-white dark:bg-slate-800 border border-amber-300 dark:border-amber-700 rounded-lg hover:bg-amber-50 dark:hover:bg-slate-700"
            >
              &larr; Back to Folder Selection
            </button>
          </div>

          {/* Result of the last delete */}
          {notice && (
            <div
              className={`max-w-4xl mx-auto mb-6 p-4 rounded-lg border flex items-start justify-between gap-4 ${
                notice.kind === 'success'
                  ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800 text-green-900 dark:text-green-200'
                  : notice.kind === 'warning'
                  ? 'bg-amber-50 dark:bg-amber-900/20 border-amber-300 dark:border-amber-700 text-amber-900 dark:text-amber-200'
                  : 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800 text-red-900 dark:text-red-200'
              }`}
              role="status"
            >
              <div className="text-sm">
                <p className="font-semibold">{notice.title}</p>
                {notice.details && (
                  <ul className="mt-2 space-y-1 list-disc list-inside font-mono text-xs">
                    {notice.details.map((line, index) => (
                      <li key={index}>{line}</li>
                    ))}
                  </ul>
                )}
              </div>
              <button
                onClick={() => setNotice(null)}
                className="shrink-0 text-sm font-semibold opacity-70 hover:opacity-100"
                aria-label="Dismiss message"
              >
                &times;
              </button>
            </div>
          )}

          {/* One-line summary and any photos that could not be read (above the tabs: visible on both) */}
          <ResultsSummary
            folderPath={appData.scanResponse.folder_path}
            totalPhotos={appData.scanResponse.total_photos}
            groups={appData.scanResults.groups}
            skippedCount={appData.scanResponse.skipped_count}
            skipped={appData.scanResponse.skipped}
          />

          <div className="max-w-4xl mx-auto mt-6">
            <ResultsTabs tabs={RESULTS_TABS} active={tab} onChange={setTab} label="Scan results" />
          </div>

          {/* Both panels stay mounted (hidden when inactive) so the selection and page survive a tab switch */}
          <div
            id={panelId('insights')}
            role="tabpanel"
            aria-labelledby={tabId('insights')}
            tabIndex={0}
            hidden={tab !== 'insights'}
            className="max-w-4xl mx-auto mt-4 bg-white dark:bg-slate-900 rounded-lg shadow-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500"
          >
            <InsightsPanel scanId={appData.scanResponse.scan_id} refreshKey={insightsVersion} />
          </div>

          <div
            id={panelId('review')}
            role="tabpanel"
            aria-labelledby={tabId('review')}
            tabIndex={0}
            hidden={tab !== 'review'}
            className="max-w-4xl mx-auto mt-4 focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500 rounded-lg"
          >
            <ReviewHint groupCount={appData.scanResults.groups.length} hasDeleted={clearedByDeleting} />
            {appData.scanResults.groups.length > 0 ? (
              <ResultsGrid
                groups={appData.scanResults.groups}
                onSelectGroups={handleSelectGroups}
                onDelete={handleDeleteDuplicates}
                isDeleting={isDeleting}
              />
            ) : (
              <div className="p-8 bg-white dark:bg-slate-900 rounded-lg shadow-lg text-center">
                <p className="text-lg text-slate-600 dark:text-slate-400">
                  {clearedByDeleting
                    ? 'All duplicates cleared. Nice and tidy!'
                    : 'No duplicates found! Your photos are all unique.'}
                </p>
                <button
                  onClick={handleReset}
                  className="mt-4 px-6 py-2 bg-amber-500 text-amber-950 rounded-lg font-semibold hover:bg-amber-400"
                >
                  Scan Another Folder
                </button>
              </div>
            )}
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
            className="w-full py-3 px-4 bg-amber-500 text-amber-950 rounded-lg font-semibold hover:bg-amber-400"
          >
            Try Again
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;
