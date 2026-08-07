"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { EntityCard } from "@/components/verification/entity-card";
import { useDebouncedValue } from "@/lib/hooks/use-debounced-value";
import { type SubjectType, type TrustBand, useSearch } from "@/lib/search/use-search";

const TYPE_FILTERS: Array<{ value: SubjectType | undefined; label: string }> = [
  { value: undefined, label: "All" },
  { value: "company", label: "Companies" },
  { value: "recruiter", label: "Recruiters" },
  { value: "job_posting", label: "Postings" },
];

const BAND_FILTERS: Array<{ value: TrustBand | undefined; label: string }> = [
  { value: undefined, label: "Any trust level" },
  { value: "trusted", label: "Trusted" },
  { value: "caution", label: "Caution" },
  { value: "high_risk", label: "High risk" },
  { value: "unrated", label: "Unrated" },
];

function ResultsSkeleton() {
  return (
    <div className="space-y-3" aria-hidden="true">
      {Array.from({ length: 5 }).map((_, i) => (
        <div
          key={i}
          className="h-20 animate-pulse rounded-[var(--radius-card)] border border-border bg-surface"
        />
      ))}
    </div>
  );
}

export function SearchPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get("q") ?? "";

  const [inputValue, setInputValue] = useState(initialQuery);
  const [subjectType, setSubjectType] = useState<SubjectType | undefined>(undefined);
  const [band, setBand] = useState<TrustBand | undefined>(undefined);
  const debouncedQuery = useDebouncedValue(inputValue, 300);

  useEffect(() => {
    const params = new URLSearchParams();
    if (debouncedQuery) params.set("q", debouncedQuery);
    router.replace(params.size > 0 ? `/search?${params.toString()}` : "/search");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedQuery]);

  const { data, isLoading, isError, refetch } = useSearch({
    q: debouncedQuery,
    subjectType,
    band,
  });

  return (
    <main id="main-content" className="mx-auto w-full max-w-3xl flex-1 px-6 py-10">
      <h1 className="text-2xl font-semibold text-foreground">Search VeriHire</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Look up a recruiter, company or job posting by name.
      </p>

      <div className="mt-6">
        <label htmlFor="search-input" className="sr-only">
          Search
        </label>
        <input
          id="search-input"
          type="search"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder="Search by name…"
          className="w-full rounded-[var(--radius-control)] border border-border bg-surface-0 px-4 py-3 text-base text-foreground outline-none focus:border-primary"
        />
      </div>

      <div className="mt-4 flex flex-wrap gap-2" role="group" aria-label="Filter by type">
        {TYPE_FILTERS.map((filter) => (
          <button
            key={filter.label}
            type="button"
            onClick={() => setSubjectType(filter.value)}
            aria-pressed={subjectType === filter.value}
            className={`rounded-[var(--radius-pill)] border px-3 py-1.5 text-sm font-medium transition-colors ${
              subjectType === filter.value
                ? "border-primary bg-primary text-primary-foreground"
                : "border-border text-foreground hover:bg-surface-0"
            }`}
          >
            {filter.label}
            {data && filter.value
              ? (() => {
                  const count = data.facets.subject_type.find(
                    (f) => f.value === filter.value,
                  )?.count;
                  return count ? ` (${count})` : "";
                })()
              : ""}
          </button>
        ))}
      </div>

      <div className="mt-2 flex flex-wrap gap-2" role="group" aria-label="Filter by trust band">
        {BAND_FILTERS.map((filter) => (
          <button
            key={filter.label}
            type="button"
            onClick={() => setBand(filter.value)}
            aria-pressed={band === filter.value}
            className={`rounded-[var(--radius-pill)] border px-3 py-1 text-xs font-medium transition-colors ${
              band === filter.value
                ? "border-primary bg-primary text-primary-foreground"
                : "border-border text-muted-foreground hover:bg-surface-0"
            }`}
          >
            {filter.label}
          </button>
        ))}
      </div>

      <div className="mt-6" aria-live="polite">
        {debouncedQuery.trim().length === 0 ? (
          <EmptyState
            title="Start typing to search"
            description="Search across every company, recruiter and job posting VeriHire knows about."
          />
        ) : isLoading ? (
          <ResultsSkeleton />
        ) : isError ? (
          <ErrorState
            message="We couldn't load search results."
            onRetry={() => void refetch()}
          />
        ) : data && data.data.length === 0 ? (
          <EmptyState
            title="No matches"
            description={`Nothing matched "${debouncedQuery}". Try a different spelling, or paste a link on the homepage to add it.`}
          />
        ) : (
          <div className="space-y-3">
            {data?.data.map((item) => <EntityCard key={item.id} item={item} />)}
          </div>
        )}
      </div>
    </main>
  );
}
