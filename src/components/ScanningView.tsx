// src/components/ScanningView.tsx - live progress while a scan runs

import React, { useEffect, useRef, useState } from 'react';
import type { ScanProgressResponse } from '../types';

interface ScanningViewProps {
  progress: ScanProgressResponse | null;
}

function formatDuration(totalSeconds: number): string {
  const s = Math.max(0, Math.round(totalSeconds));
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ${s % 60}s`;
  return `${Math.floor(m / 60)}h ${m % 60}m`;
}

export const ScanningView: React.FC<ScanningViewProps> = ({ progress }) => {
  const [rate, setRate] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const hashStart = useRef<number | null>(null);
  const last = useRef<{ t: number; n: number } | null>(null);

  const phase = progress?.phase ?? 'queued';
  const done = progress?.files_processed ?? 0;
  const total = progress?.files_total ?? 0;

  useEffect(() => {
    if (phase !== 'hashing') return;
    const now = Date.now();
    if (hashStart.current === null) {
      hashStart.current = now;
      last.current = { t: now, n: done };
      return;
    }
    setElapsed((now - hashStart.current) / 1000);
    if (last.current && now - last.current.t >= 1500 && done >= last.current.n) {
      const instant = (done - last.current.n) / ((now - last.current.t) / 1000);
      setRate((previous) => (previous === 0 ? instant : previous * 0.7 + instant * 0.3));
      last.current = { t: now, n: done };
    }
  }, [phase, done]);

  const percent = total > 0 ? Math.min(100, Math.round((done / total) * 100)) : 0;
  const remaining = rate > 0 && elapsed >= 3 ? (total - done) / rate : null;

  let title = 'Starting scan...';
  if (phase === 'discovering') title = 'Looking for photos...';
  if (phase === 'hashing') title = 'Checking your photos...';
  if (phase === 'grouping' || phase === 'completed') title = 'Grouping duplicates...';

  return (
    <div className="w-full max-w-2xl">
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 px-4 py-2 bg-white dark:bg-slate-800 rounded-full shadow-md mb-4">
          <div className="w-3 h-3 bg-amber-500 rounded-full animate-pulse"></div>
          <span className="text-sm font-semibold text-slate-700 dark:text-slate-300">{title}</span>
        </div>
      </div>

      <div className="bg-white dark:bg-slate-800 rounded-lg shadow-lg p-8">
        {phase === 'hashing' && total > 0 ? (
          <div className="flex flex-col gap-4">
            <div className="flex items-baseline justify-between">
              <span className="text-3xl font-bold text-slate-900 dark:text-white">{percent}%</span>
              <span className="text-sm text-slate-600 dark:text-slate-400">
                {done.toLocaleString()} of {total.toLocaleString()} photos
              </span>
            </div>
            <div className="w-full h-3 bg-amber-100 dark:bg-slate-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-amber-500 transition-all duration-300"
                style={{ width: `${percent}%` }}
              ></div>
            </div>
            <div className="flex justify-between text-sm text-slate-600 dark:text-slate-400">
              <span>{rate > 0 ? `${rate.toFixed(rate < 10 ? 1 : 0)} photos/sec` : 'Measuring speed...'}</span>
              <span>{remaining !== null ? `About ${formatDuration(remaining)} left` : ''}</span>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-4">
            <div className="w-12 h-12 border-4 border-amber-200 dark:border-amber-800 border-t-amber-600 dark:border-t-amber-400 rounded-full animate-spin"></div>
            <p className="text-slate-600 dark:text-slate-400">
              {phase === 'discovering' && total > 0
                ? `Found ${total.toLocaleString()} photos so far...`
                : title}
            </p>
          </div>
        )}
        <p className="mt-6 text-xs text-center text-slate-500 dark:text-slate-400">
          Large libraries and external drives can take a while. Your photos are never changed during a scan.
        </p>
      </div>
    </div>
  );
};