import type { TrustBand } from "@/lib/search/use-search";

const BAND_STYLES: Record<TrustBand, string> = {
  unrated: "bg-border text-muted-foreground",
  high_risk: "bg-signal-danger/10 text-signal-danger",
  caution: "bg-signal-caution/10 text-signal-caution",
  trusted: "bg-signal-verified/10 text-signal-verified",
};

const BAND_LABELS: Record<TrustBand, string> = {
  unrated: "Unrated",
  high_risk: "High risk",
  caution: "Caution",
  trusted: "Trusted",
};

export function VerdictBadge({ band }: { band: TrustBand }) {
  return (
    <span
      className={`inline-flex items-center rounded-[var(--radius-pill)] px-2.5 py-1 text-xs font-medium ${BAND_STYLES[band]}`}
    >
      {BAND_LABELS[band]}
    </span>
  );
}
