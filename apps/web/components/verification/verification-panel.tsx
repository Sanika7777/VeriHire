"use client";

import type { components } from "@verihire/shared";

import { ReportButton } from "@/components/reports/report-button";
import { ScoreBreakdown } from "@/components/verification/score-breakdown";
import { ScoreHistorySparkline } from "@/components/verification/score-history-sparkline";
import { SignalList } from "@/components/verification/signal-list";
import { TrustRing } from "@/components/verification/trust-ring";
import { VerdictBadge } from "@/components/verification/verdict-badge";
import { useCurrentUser } from "@/lib/auth/use-auth";
import { useLatestVerification, useRequestVerification } from "@/lib/verification/use-verification";

type SubjectType = components["schemas"]["SubjectType"];

const STAGE_LABELS: Record<string, string> = {
  pending: "Queued…",
  resolving: "Resolving…",
  fetching: "Fetching data…",
  analysing: "Analysing…",
  scoring: "Scoring…",
  done: "Done",
  failed: "Failed",
};

export function VerificationPanel({
  subjectType,
  subjectId,
}: {
  subjectType: SubjectType;
  subjectId: string;
}) {
  const { data: user } = useCurrentUser();
  const { data: verification, isLoading } = useLatestVerification(subjectType, subjectId);
  const { start, status, isRunning } = useRequestVerification(subjectType, subjectId);

  if (isLoading) {
    return (
      <div
        className="h-32 animate-pulse rounded-[var(--radius-card)] border border-border bg-surface"
        aria-hidden="true"
      />
    );
  }

  if (isRunning) {
    return (
      <div
        className="flex flex-col items-center gap-3 rounded-[var(--radius-card)] border border-border bg-surface p-6 text-center"
        aria-live="polite"
      >
        <div className="h-10 w-10 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        <p className="text-sm text-muted-foreground">{STAGE_LABELS[status ?? "pending"]}</p>
      </div>
    );
  }

  if (!verification || verification.status !== "done") {
    return (
      <div className="rounded-[var(--radius-card)] border border-dashed border-border p-6 text-center">
        <p className="text-sm text-muted-foreground">
          This subject hasn&apos;t been verified yet.
        </p>
        {user ? (
          <button
            type="button"
            onClick={() => void start()}
            className="mt-3 rounded-[var(--radius-control)] bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:opacity-90"
          >
            Run Trust Score check
          </button>
        ) : (
          <p className="mt-2 text-xs text-muted-foreground">Log in to run a verification.</p>
        )}
      </div>
    );
  }

  return (
    <div className="rounded-[var(--radius-card)] border border-border bg-surface p-6">
      <div className="flex flex-col items-center gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex flex-col items-center gap-2 sm:items-start">
          <TrustRing score={verification.score} band={verification.band} />
          <VerdictBadge band={verification.band} />
          {verification.hard_override_reason ? (
            <p className="max-w-xs text-center text-xs text-signal-danger sm:text-left">
              {verification.hard_override_reason}
            </p>
          ) : null}
        </div>
        <div className="w-full sm:max-w-sm">
          <h3 className="mb-2 text-sm font-medium text-foreground">Why this score</h3>
          <ScoreBreakdown subScores={verification.sub_scores as Record<string, number | null>} />
        </div>
      </div>

      <div className="mt-6">
        <h3 className="mb-2 text-sm font-medium text-foreground">Signals</h3>
        <SignalList signals={verification.signals as components["schemas"]["SignalRead"][]} />
      </div>

      <div className="mt-6">
        <h3 className="mb-2 text-sm font-medium text-foreground">Score history</h3>
        <ScoreHistorySparkline subjectType={subjectType} subjectId={subjectId} />
      </div>

      {user ? (
        <div className="mt-4 flex items-center gap-4">
          <button
            type="button"
            onClick={() => void start()}
            className="text-sm font-medium text-primary"
          >
            Re-check now
          </button>
          <ReportButton subjectType={subjectType} subjectId={subjectId} />
        </div>
      ) : null}
    </div>
  );
}
