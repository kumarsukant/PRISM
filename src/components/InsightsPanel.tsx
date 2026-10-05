// src/components/InsightsPanel.tsx
// Where the duplicates are: headline, top folders, folders sharing copies, tips and coverage.
// Read-only. The only action is Open folder, which opens Explorer and changes nothing.
// All wording lives here; the backend sends ids and numbers (GET /scan/insights). Every statement about a
// cause is hedged ("often"), and only describes what the counts show.

import React, { useEffect, useState } from 'react';
import { FolderOpen, Loader2 } from 'lucide-react';
import { api } from '../services/api';
import type { FolderRef, FolderTag, InsightHeadline, InsightTip, InsightsResponse } from '../types';

interface InsightsPanelProps {
  scanId: string;
  refreshKey: number; // bumped after a delete, so the insights are fetched again
}

const count = (n: number, one: string, many: string) => `${n.toLocaleString()} ${n === 1 ? one : many}`;

/** Folder as shown to the user: relative to the scanned folder, which itself shows as "<name> (top level)". */
const folderName = (ref: { relative_path: string }, rootName: string) => ref.relative_path || `${rootName} (top level)`;

/** Shorten a long path from the start, keeping the last folders: "…\2024\Holiday". */
function shortenPath(path: string, max = 34): string {
  if (path.length <= max) return path;
  const parts = path.split('\\');
  let out = parts[parts.length - 1];
  for (let i = parts.length - 2; i >= 0; i--) {
    const candidate = `${parts[i]}\\${out}`;
    if (candidate.length + 2 > max) break;
    out = candidate;
  }
  return out.length + 2 <= max ? `…\\${out}` : `…${out.slice(-(max - 1))}`;
}

const TAGS: Record<FolderTag, { label: string; className: string }> = {
  same_folder: {
    label: 'Copies in same folder',
    className: 'bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-200',
  },
  other_folders: {
    label: 'Copies in other folders',
    className: 'bg-violet-100 text-violet-800 dark:bg-violet-900/40 dark:text-violet-200',
  },
  mixed: {
    label: 'Mixed',
    className: 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-200',
  },
};

function headlineText(h: InsightHeadline, rootName: string): string {
  if (h.id === 'top_folder') {
    const where =
      h.tag === 'same_folder'
        ? 'mostly in that same folder'
        : h.tag === 'other_folders'
        ? 'mostly in other folders'
        : 'some in that folder and some in others';
    return `${folderName(h.folder, rootName)} has the most duplicates: ${h.photos_with_duplicate.toLocaleString()} of its ${count(h.photos, 'photo', 'photos')} ${h.photos_with_duplicate === 1 ? 'has a copy' : 'have copies'}, ${where}.`;
  }
  const { groups_in_one_folder: inOne, groups_across_folders: across } = h;
  if (across === 0) return 'Every set of copies is inside a single folder.';
  if (inOne === 0) return 'Every set of copies spans two or more folders.';
  return `${count(inOne, 'set of copies stays', 'sets of copies stay')} inside one folder; ${count(across, 'set spans', 'sets span')} two or more folders.`;
}

function tipText(t: InsightTip, rootName: string): string {
  switch (t.id) {
    case 'copy_suffix':
      return `${count(t.count, 'extra copy has a name', 'extra copies have names')} ending in “ - Copy”. Windows names a pasted file that way when the folder already has the original, so these often come from pasting into the same folder.`;
    case 'number_suffix':
      return `${count(t.count, 'extra copy has a name', 'extra copies have names')} ending in a number in brackets, like “(1)”. These often come from downloading or saving the same file twice.`;
    case 'folder_pair':
      return `${folderName(t.a, rootName)} and ${folderName(t.b, rootName)} share ${count(t.shared_groups, 'photo', 'photos')}. This often happens when the same photos are saved or backed up to two places.`;
    case 'same_folder':
      return `In ${folderName(t.folder, rootName)}, most copies sit in the same folder as the original. This often happens when the same files are added to a folder more than once.`;
    case 'spread':
      return `${count(t.count, 'photo is', 'photos are')} in three or more folders. This often happens when an album is copied to several places.`;
  }
}

function coverageText(data: InsightsResponse): string {
  const c = data.coverage;
  const notChecked: string[] = [];
  const unsupported: string[] = [];
  if (c.heic_not_checked) unsupported.push(`${c.heic_not_checked.toLocaleString()} HEIC`);
  if (c.raw_not_checked) unsupported.push(`${c.raw_not_checked.toLocaleString()} RAW`);
  if (unsupported.length) notChecked.push(`${unsupported.join(' and ')} (not supported yet)`);
  if (c.under_10kb) notChecked.push(`${count(c.under_10kb, 'image', 'images')} under 10 KB`);
  if (c.unreadable) notChecked.push(`${c.unreadable.toLocaleString()} unreadable (listed above)`);
  const checked = `Checked ${count(c.photos_checked, 'photo', 'photos')} in ${count(c.folders_checked, 'folder', 'folders')}.`;
  return notChecked.length ? `${checked} Not checked: ${notChecked.join(', ')}.` : checked;
}

const SectionTitle: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <h3 className="text-xs font-bold uppercase tracking-wide text-slate-600 dark:text-slate-400 mb-2">{children}</h3>
);

export const InsightsPanel: React.FC<InsightsPanelProps> = ({ scanId, refreshKey }) => {
  const [data, setData] = useState<InsightsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [opening, setOpening] = useState<string | null>(null);
  const [openError, setOpenError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    api
      .getInsights(scanId)
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Could not load insights');
      });
    return () => {
      cancelled = true;
    };
  }, [scanId, refreshKey]);

  const openFolder = async (folder: FolderRef, label: string) => {
    setOpening(folder.id);
    setOpenError(null);
    try {
      await api.openScanFolder(scanId, folder.id);
    } catch (e) {
      setOpenError(`Couldn't open ${label}: ${e instanceof Error ? e.message : 'unknown error'}`);
    } finally {
      setOpening(null);
    }
  };

  if (error) {
    return <p className="p-6 text-sm text-red-700 dark:text-red-300">Couldn&apos;t load insights: {error}</p>;
  }
  if (!data) {
    return (
      <p className="p-6 flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
        <Loader2 className="w-4 h-4 animate-spin" /> Looking at where your duplicates are...
      </p>
    );
  }

  const rootName = data.root_name;
  const onlineOnly = data.coverage.online_only;

  return (
    <div className="p-6 space-y-6">
      {data.headlines.length > 0 ? (
        <div className="space-y-1">
          {data.headlines.map((h, i) => (
            <p key={h.id} className={i === 0 ? 'text-base font-semibold text-slate-900 dark:text-white' : 'text-sm text-slate-700 dark:text-slate-300'}>
              {headlineText(h, rootName)}
            </p>
          ))}
        </div>
      ) : (
        <p className="text-base font-semibold text-slate-900 dark:text-white">No duplicates found.</p>
      )}

      {data.folders.length > 0 && (
        <section aria-labelledby="ins-where">
          <SectionTitle>
            <span id="ins-where">Where your duplicates are</span>
          </SectionTitle>
          <table className="w-full table-fixed text-sm">
            <thead>
              <tr className="text-left text-xs text-slate-600 dark:text-slate-400">
                <th className="font-semibold pb-1">Folder</th>
                <th className="font-semibold pb-1 w-14 text-right pr-3">Photos</th>
                <th className="font-semibold pb-1 w-32">With duplicates</th>
                <th className="font-semibold pb-1 w-44">
                  <span className="sr-only">Where the copies are</span>
                </th>
                <th className="pb-1 w-28">
                  <span className="sr-only">Action</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {data.folders.map((f) => {
                const name = folderName(f, rootName);
                const pct = Math.round(f.share_with_duplicate * 100);
                return (
                  <tr key={f.id} className="border-t border-slate-100 dark:border-slate-800">
                    <td className="py-2 pr-2 font-mono text-xs text-slate-800 dark:text-slate-200 truncate" title={f.path}>
                      {shortenPath(name, 26)}
                    </td>
                    <td className="py-2 pr-3 text-right tabular-nums text-slate-700 dark:text-slate-300">
                      {f.photos.toLocaleString()}
                    </td>
                    <td className="py-2">
                      <div className="flex items-center gap-2 text-slate-700 dark:text-slate-300 tabular-nums">
                        <span className="w-8 text-right">{f.photos_with_duplicate.toLocaleString()}</span>
                        <span className="w-9 text-right text-xs">{pct}%</span>
                        <span className="w-10 h-1.5 rounded bg-slate-200 dark:bg-slate-700 overflow-hidden" aria-hidden="true">
                          <span className="block h-full bg-amber-500" style={{ width: `${pct}%` }} />
                        </span>
                      </div>
                    </td>
                    <td className="py-2">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-semibold whitespace-nowrap ${TAGS[f.tag].className}`}>
                        {TAGS[f.tag].label}
                      </span>
                    </td>
                    <td className="py-2 text-right">
                      <button
                        type="button"
                        onClick={() => openFolder(f, name)}
                        disabled={opening === f.id}
                        aria-label={`Open folder ${name}`}
                        className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded-md border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-60"
                      >
                        <FolderOpen className="w-3.5 h-3.5" aria-hidden="true" />
                        Open folder
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {data.folders_with_duplicates_not_shown > 0 && (
            <p className="mt-2 text-xs text-slate-600 dark:text-slate-400">
              …and {count(data.folders_with_duplicates_not_shown, 'more folder', 'more folders')} with duplicates.
            </p>
          )}
          {openError && (
            <p className="mt-2 text-sm text-red-700 dark:text-red-300" role="status">
              {openError}
            </p>
          )}
        </section>
      )}

      {data.totals.duplicate_groups > 0 && (
        <section aria-labelledby="ins-pairs">
          <SectionTitle>
            <span id="ins-pairs">Copies across folders</span>
          </SectionTitle>
          {data.pairs.length > 0 ? (
            <ul className="space-y-1 text-sm text-slate-700 dark:text-slate-300">
              {data.pairs.map((p) => (
                <li key={`${p.a.id}-${p.b.id}`} className="flex items-baseline justify-between gap-4">
                  <span className="min-w-0 truncate font-mono text-xs text-slate-800 dark:text-slate-200">
                    {shortenPath(folderName(p.a, rootName), 30)} <span aria-label="and">⇄</span> {shortenPath(folderName(p.b, rootName), 30)}
                  </span>
                  <span className="shrink-0 tabular-nums">{count(p.shared_groups, 'photo', 'photos')} in both</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-700 dark:text-slate-300">All copies are inside the same folder as their original.</p>
          )}
          {data.totals.groups_across_3_plus_folders > 0 && (
            <p className="mt-2 text-xs text-slate-600 dark:text-slate-400">
              {count(data.totals.groups_across_3_plus_folders, 'photo is', 'photos are')} in three or more folders, so
              {data.totals.groups_across_3_plus_folders === 1 ? ' it is' : ' they are'} counted in each pair.
            </p>
          )}
        </section>
      )}

      {data.tips.length > 0 && (
        <section aria-labelledby="ins-tips">
          <SectionTitle>
            <span id="ins-tips">What to watch for</span>
          </SectionTitle>
          <ul className="space-y-2 list-disc pl-5 text-sm text-slate-700 dark:text-slate-300">
            {data.tips.map((t) => (
              <li key={t.id}>{tipText(t, rootName)}</li>
            ))}
          </ul>
        </section>
      )}

      <footer className="pt-4 border-t border-slate-100 dark:border-slate-800 space-y-1 text-xs text-slate-600 dark:text-slate-400">
        <p>{coverageText(data)}</p>
        {onlineOnly > 0 && (
          <p className="font-semibold text-slate-800 dark:text-slate-200">
            {count(onlineOnly, 'online-only file was', 'online-only files were')} not scanned. Make them available offline and
            scan again.
          </p>
        )}
      </footer>
    </div>
  );
};
