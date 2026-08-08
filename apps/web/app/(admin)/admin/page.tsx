"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { StatTile } from "@/components/ui/stat-tile";
import { useAdminDashboard } from "@/lib/admin/use-admin";

const BAND_LABELS: Record<string, string> = {
  unrated: "Unrated",
  high_risk: "High risk",
  caution: "Caution",
  trusted: "Trusted",
};

const BAND_COLORS: Record<string, string> = {
  unrated: "var(--muted-foreground)",
  high_risk: "var(--signal-danger)",
  caution: "var(--signal-caution)",
  trusted: "var(--signal-verified)",
};

export default function AdminDashboardPage() {
  const { data, isLoading, isError, refetch } = useAdminDashboard();

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-24" />
        ))}
      </div>
    );
  }

  if (isError || !data) {
    return <ErrorState message="Couldn't load the dashboard." onRetry={() => void refetch()} />;
  }

  const chartData = Object.entries(data.band_distribution).map(([band, count]) => ({
    band,
    label: BAND_LABELS[band] ?? band,
    count,
    fill: BAND_COLORS[band] ?? "var(--primary)",
  }));

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-xl font-semibold text-foreground">Trust &amp; Safety dashboard</h1>
        <p className="text-sm text-muted-foreground">Live counts from the database.</p>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatTile label="Pending reports" value={data.pending_reports} />
        <StatTile label="Confirmed reports" value={data.confirmed_reports} />
        <StatTile label="Rejected reports" value={data.rejected_reports} />
        <StatTile label="Verifications (7d)" value={data.verifications_last_7_days} />
      </div>

      <div className="rounded-[var(--radius-card)] border border-border bg-surface p-4">
        <h2 className="mb-4 text-sm font-medium text-foreground">Trust band distribution</h2>
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="label" stroke="var(--muted-foreground)" fontSize={12} />
              <YAxis stroke="var(--muted-foreground)" fontSize={12} allowDecimals={false} />
              <Tooltip
                contentStyle={{
                  background: "var(--surface-0)",
                  border: "1px solid var(--border)",
                  borderRadius: "var(--radius-control)",
                  color: "var(--foreground)",
                }}
              />
              <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                {chartData.map((entry) => (
                  <Cell key={entry.band} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {data.top_reported_subjects.length > 0 ? (
        <div className="rounded-[var(--radius-card)] border border-border bg-surface p-4">
          <h2 className="mb-3 text-sm font-medium text-foreground">Most-reported subjects</h2>
          <ul className="space-y-2 text-sm">
            {data.top_reported_subjects.map((row) => {
              const r = row as { subject_type: string; subject_id: string; report_count: number };
              return (
                <li key={r.subject_id} className="flex justify-between text-foreground">
                  <span className="text-muted-foreground">
                    {r.subject_type} · {r.subject_id.slice(0, 8)}…
                  </span>
                  <span className="font-medium">{r.report_count} reports</span>
                </li>
              );
            })}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
