"use client";

import type { components } from "@verihire/shared";
import { useState } from "react";

import { VerdictBadge } from "@/components/verification/verdict-badge";
import { useDebouncedValue } from "@/lib/hooks/use-debounced-value";
import { useSearch } from "@/lib/search/use-search";

type SearchItem = components["schemas"]["SearchResultItem"];

export function ComparePicker({
  label,
  onPick,
}: {
  label: string;
  onPick: (item: SearchItem) => void;
}) {
  const [query, setQuery] = useState("");
  const debounced = useDebouncedValue(query, 300);
  const { data } = useSearch({ q: debounced });

  return (
    <div>
      <label className="mb-1 block text-sm font-medium text-foreground">{label}</label>
      <input
        type="search"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search by name…"
        className="w-full rounded-[var(--radius-control)] border border-border bg-surface-0 px-3 py-2 text-sm"
      />
      {data && data.data.length > 0 ? (
        <div className="mt-2 max-h-64 space-y-2 overflow-y-auto">
          {data.data.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => onPick(item)}
              className="flex w-full items-center justify-between gap-3 rounded-[var(--radius-card)] border border-border bg-surface p-3 text-left transition-colors hover:border-primary"
            >
              <span className="min-w-0 truncate text-sm text-foreground">{item.name}</span>
              <VerdictBadge band={item.band} />
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
