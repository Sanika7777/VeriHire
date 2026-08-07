"use client";

import { useEffect } from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-4 px-6 py-24 text-center">
      <p className="text-sm font-medium text-muted-foreground">
        Something went wrong
      </p>
      <h1 className="text-3xl font-semibold text-foreground">
        We hit a snag loading this page.
      </h1>
      <p className="max-w-md text-muted-foreground">
        This has been logged. You can try again, or head back to the
        homepage.
      </p>
      <button
        type="button"
        onClick={reset}
        className="mt-2 rounded-[var(--radius-control)] bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground transition-colors hover:opacity-90"
      >
        Try again
      </button>
    </main>
  );
}
