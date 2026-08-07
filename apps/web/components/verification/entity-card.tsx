import Link from "next/link";

import { VerdictBadge } from "@/components/verification/verdict-badge";
import type { SearchResponse } from "@/lib/search/use-search";

const TYPE_LABELS = {
  company: "Company",
  recruiter: "Recruiter",
  job_posting: "Job posting",
} as const;

function hrefFor(item: SearchResponse["data"][number]): string {
  if (item.subject_type === "recruiter") return `/recruiters/${item.id}`;
  if (item.subject_type === "job_posting") return `/postings/${item.id}`;
  return `/companies/${item.id}`;
}

export function EntityCard({ item }: { item: SearchResponse["data"][number] }) {
  return (
    <Link
      href={hrefFor(item)}
      className="flex items-center justify-between gap-4 rounded-[var(--radius-card)] border border-border bg-surface p-4 transition-colors hover:border-primary"
    >
      <div className="min-w-0">
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          {TYPE_LABELS[item.subject_type]}
        </p>
        <p className="truncate text-base font-medium text-foreground">{item.name}</p>
        {item.subtitle ? (
          <p className="truncate text-sm text-muted-foreground">{item.subtitle}</p>
        ) : null}
      </div>
      <VerdictBadge band={item.band} />
    </Link>
  );
}
