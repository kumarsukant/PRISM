// src/components/ResultsTabs.tsx
// Accessible tab bar (WAI-ARIA tabs pattern): role="tablist"/"tab", aria-selected, aria-controls, roving
// tabindex, and Left/Right/Home/End to move between tabs (selection follows focus).

import React, { useRef } from 'react';

export interface TabDef<T extends string> {
  id: T;
  label: string;
}

/** Index of the tab a key moves to, or null for keys the tab bar does not handle. */
export function nextTabIndex(key: string, current: number, count: number): number | null {
  switch (key) {
    case 'ArrowRight':
      return (current + 1) % count;
    case 'ArrowLeft':
      return (current - 1 + count) % count;
    case 'Home':
      return 0;
    case 'End':
      return count - 1;
    default:
      return null;
  }
}

export const tabId = (id: string) => `tab-${id}`;
export const panelId = (id: string) => `panel-${id}`;

interface ResultsTabsProps<T extends string> {
  tabs: TabDef<T>[];
  active: T;
  onChange: (id: T) => void;
  label: string;
}

export function ResultsTabs<T extends string>({ tabs, active, onChange, label }: ResultsTabsProps<T>) {
  const buttons = useRef<(HTMLButtonElement | null)[]>([]);

  const handleKeyDown = (event: React.KeyboardEvent, index: number) => {
    const next = nextTabIndex(event.key, index, tabs.length);
    if (next === null) return;
    event.preventDefault();
    onChange(tabs[next].id);
    buttons.current[next]?.focus();
  };

  return (
    <div role="tablist" aria-label={label} className="flex gap-1 border-b border-slate-200 dark:border-slate-700">
      {tabs.map((tab, index) => {
        const selected = tab.id === active;
        return (
          <button
            key={tab.id}
            ref={(el) => {
              buttons.current[index] = el;
            }}
            id={tabId(tab.id)}
            role="tab"
            type="button"
            aria-selected={selected}
            aria-controls={panelId(tab.id)}
            tabIndex={selected ? 0 : -1}
            onClick={() => onChange(tab.id)}
            onKeyDown={(event) => handleKeyDown(event, index)}
            className={`-mb-px px-4 py-2 text-sm font-semibold border-b-2 rounded-t focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500 ${
              selected
                ? 'border-amber-600 dark:border-amber-500 text-slate-900 dark:text-white'
                : 'border-transparent text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
