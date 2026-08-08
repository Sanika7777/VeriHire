"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api-client/client";
import {
  usePreviewScoringConfig,
  usePublishScoringConfig,
  useScoringConfig,
} from "@/lib/admin/use-admin";

const LABELS: Record<string, string> = {
  identity: "Identity",
  company_legitimacy: "Company legitimacy",
  content_risk: "Content risk",
  link_safety: "Link safety",
  community_signal: "Community signal",
};

const ORDER = ["identity", "company_legitimacy", "content_risk", "link_safety", "community_signal"];

export default function AdminScoringPage() {
  const { data: config, isLoading, isError, refetch } = useScoringConfig();
  const [weights, setWeights] = useState<Record<string, number> | null>(null);
  const preview = usePreviewScoringConfig();
  const publish = usePublishScoringConfig();

  useEffect(() => {
    if (config && !weights) setWeights(config.weights);
  }, [config, weights]);

  if (isLoading || !weights) {
    return <Skeleton className="h-64" />;
  }

  if (isError || !config) {
    return <ErrorState message="Couldn't load scoring config." onRetry={() => void refetch()} />;
  }

  const total = Object.values(weights).reduce((sum, v) => sum + v, 0);
  const isValid = Math.abs(total - 1) < 0.001;

  const onPreview = async () => {
    try {
      await preview.mutateAsync({ weights, thresholds: config.thresholds });
    } catch (err) {
      toast.error(err instanceof ApiError ? err.problem.detail : "Preview failed.");
    }
  };

  const onPublish = async () => {
    if (!isValid) {
      toast.error("Weights must sum to 1.0 before publishing.");
      return;
    }
    try {
      await publish.mutateAsync({ weights, thresholds: config.thresholds });
      toast.success("New scoring config published — it applies to future verifications only.");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.problem.detail : "Publish failed.");
    }
  };

  return (
    <div className="max-w-xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-foreground">Scoring configuration</h1>
        <p className="text-sm text-muted-foreground">
          Currently active: version {config.version}. Historical scores are never rewritten —
          a new version only affects verifications computed after publishing.
        </p>
      </div>

      <div className="space-y-4">
        {ORDER.map((key) => (
          <div key={key}>
            <div className="mb-1 flex items-center justify-between text-sm">
              <label htmlFor={key} className="text-foreground">
                {LABELS[key]}
              </label>
              <span className="text-muted-foreground">
                {Math.round((weights[key] ?? 0) * 100)}%
              </span>
            </div>
            <input
              id={key}
              type="range"
              min={0}
              max={1}
              step={0.01}
              value={weights[key] ?? 0}
              onChange={(e) =>
                setWeights((prev) => ({ ...prev, [key]: Number(e.target.value) }))
              }
              className="w-full accent-primary"
            />
          </div>
        ))}
        <p className={`text-sm ${isValid ? "text-muted-foreground" : "text-signal-danger"}`}>
          Total: {Math.round(total * 100)}% {isValid ? "" : "— must equal 100% to publish"}
        </p>
      </div>

      <div className="flex gap-3">
        <Button variant="outline" onClick={() => void onPreview()} disabled={preview.isPending}>
          {preview.isPending ? "Previewing…" : "Preview impact"}
        </Button>
        <Button onClick={() => void onPublish()} disabled={publish.isPending || !isValid}>
          {publish.isPending ? "Publishing…" : "Publish new version"}
        </Button>
      </div>

      {preview.data ? (
        <div className="rounded-[var(--radius-card)] border border-border bg-surface p-4 text-sm">
          <h2 className="mb-2 font-medium text-foreground">
            Preview against {preview.data.sample_size} recent verifications
          </h2>
          <p className="text-muted-foreground">
            Average score: {preview.data.average_score_before ?? "—"} →{" "}
            {preview.data.average_score_after ?? "—"}
          </p>
          {Object.keys(preview.data.band_shifts).length > 0 ? (
            <ul className="mt-2 space-y-1">
              {Object.entries(preview.data.band_shifts).map(([shift, count]) => (
                <li key={shift} className="text-muted-foreground">
                  {shift.replace("->", " → ")}: {count} subject(s)
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-muted-foreground">No band changes in this sample.</p>
          )}
        </div>
      ) : null}
    </div>
  );
}
