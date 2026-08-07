export function ErrorState({
  message = "Something went wrong. Please try again.",
  onRetry,
}: {
  message?: string;
  onRetry?: () => void;
}) {
  return (
    <div
      className="flex flex-col items-center gap-3 rounded-[var(--radius-card)] border border-signal-danger/30 bg-signal-danger/5 px-6 py-10 text-center"
      role="alert"
    >
      <p className="text-sm text-foreground">{message}</p>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="rounded-[var(--radius-control)] border border-border px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-surface-0"
        >
          Try again
        </button>
      ) : null}
    </div>
  );
}
