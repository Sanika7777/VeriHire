const SUB_SCORE_LABELS: Record<string, string> = {
  identity: "Identity",
  company_legitimacy: "Company legitimacy",
  content_risk: "Content risk",
  link_safety: "Link safety",
  community_signal: "Community signal",
};

const SUB_SCORE_WEIGHTS: Record<string, number> = {
  identity: 0.2,
  company_legitimacy: 0.25,
  content_risk: 0.3,
  link_safety: 0.1,
  community_signal: 0.15,
};

const ORDER = ["identity", "company_legitimacy", "content_risk", "link_safety", "community_signal"];

export function ScoreBreakdown({ subScores }: { subScores: Record<string, number | null> }) {
  return (
    <div className="space-y-3">
      {ORDER.map((key) => {
        const value = subScores[key];
        const weight = SUB_SCORE_WEIGHTS[key] ?? 0;
        return (
          <div key={key}>
            <div className="mb-1 flex items-center justify-between text-sm">
              <span className="text-foreground">
                {SUB_SCORE_LABELS[key]}{" "}
                <span className="text-muted-foreground">({Math.round(weight * 100)}%)</span>
              </span>
              <span className="text-muted-foreground">
                {value === null || value === undefined ? "Unrated" : `${value}/100`}
              </span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-[var(--radius-pill)] bg-border">
              <div
                className="h-full rounded-[var(--radius-pill)] bg-primary transition-all"
                style={{ width: `${value ?? 0}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
