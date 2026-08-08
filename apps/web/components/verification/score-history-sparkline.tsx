"use client";

import type { components } from "@verihire/shared";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { useVerificationHistory } from "@/lib/verification/use-verification-history";

type SubjectType = components["schemas"]["SubjectType"];

export function ScoreHistorySparkline({
  subjectType,
  subjectId,
}: {
  subjectType: SubjectType;
  subjectId: string;
}) {
  const { data: history, isLoading } = useVerificationHistory(subjectType, subjectId);

  if (isLoading) {
    return <div className="h-24 animate-pulse rounded-[var(--radius-control)] bg-border" />;
  }

  const points = (history ?? [])
    .filter((v) => v.status === "done" && v.score !== null)
    .slice()
    .reverse()
    .map((v) => ({
      date: new Date(v.computed_at).toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
      }),
      score: v.score as number,
      hardOverride: Boolean(v.hard_override_reason),
    }));

  if (points.length < 2) {
    return (
      <p className="text-xs text-muted-foreground">
        Not enough history yet to chart a trend — check back after another verification.
      </p>
    );
  }

  return (
    <div>
      <div className="h-20 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={points}>
            <XAxis dataKey="date" hide />
            <YAxis domain={[0, 100]} hide />
            <Tooltip
              contentStyle={{
                background: "var(--surface-0)",
                border: "1px solid var(--border)",
                borderRadius: "var(--radius-control)",
                color: "var(--foreground)",
                fontSize: 12,
              }}
            />
            <Line
              type="monotone"
              dataKey="score"
              stroke="var(--primary)"
              strokeWidth={2}
              dot={{ r: 3 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-1 text-xs text-muted-foreground">
        {points.length} verification{points.length === 1 ? "" : "s"} over time
        {points.some((p) => p.hardOverride) ? " — dips mark confirmed fraud reports" : ""}.
      </p>
    </div>
  );
}
