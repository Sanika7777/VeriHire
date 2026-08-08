import type { components } from "@verihire/shared";

type SignalRead = components["schemas"]["SignalRead"];

const SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"];

const SEVERITY_STYLES: Record<string, string> = {
  critical: "border-signal-danger/40 bg-signal-danger/5",
  high: "border-signal-danger/30 bg-signal-danger/5",
  medium: "border-signal-caution/40 bg-signal-caution/5",
  low: "border-border bg-surface",
  info: "border-border bg-surface",
};

const SEVERITY_DOT: Record<string, string> = {
  critical: "bg-signal-danger",
  high: "bg-signal-danger",
  medium: "bg-signal-caution",
  low: "bg-muted-foreground",
  info: "bg-muted-foreground",
};

export function SignalList({ signals }: { signals: SignalRead[] }) {
  if (signals.length === 0) {
    return <p className="text-sm text-muted-foreground">No signals recorded.</p>;
  }

  const sorted = [...signals].sort(
    (a, b) => SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity),
  );

  return (
    <ul className="space-y-2">
      {sorted.map((signal, i) => (
        <li
          key={`${signal.code}-${i}`}
          className={`rounded-[var(--radius-card)] border p-3 ${SEVERITY_STYLES[signal.severity] ?? SEVERITY_STYLES.info}`}
        >
          <div className="flex items-start gap-2">
            <span
              className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${SEVERITY_DOT[signal.severity] ?? SEVERITY_DOT.info}`}
              aria-hidden="true"
            />
            <div>
              <p className="text-sm font-medium text-foreground">{signal.title}</p>
              <p className="text-sm text-muted-foreground">{signal.detail}</p>
            </div>
          </div>
        </li>
      ))}
    </ul>
  );
}
