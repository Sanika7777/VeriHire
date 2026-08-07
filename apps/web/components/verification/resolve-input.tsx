"use client";

import type { components } from "@verihire/shared";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { apiFetch, ApiError } from "@/lib/api-client/client";

type ResolveResponse = components["schemas"]["ResolveResponse"];

const DETAIL_PATH: Record<ResolveResponse["subject_type"], string> = {
  company: "/companies",
  recruiter: "/recruiters",
  job_posting: "/postings",
};

export function ResolveInput() {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const result = await apiFetch<ResolveResponse>("/api/v1/resolve", {
        method: "POST",
        body: { url },
      });
      router.push(`${DETAIL_PATH[result.subject_type]}/${result.subject_id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.problem.detail : "Something went wrong.");
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex w-full max-w-xl flex-col gap-2">
      <form
        onSubmit={onSubmit}
        className="flex w-full flex-col gap-2 sm:flex-row"
        aria-label="Verify a link"
      >
        <label htmlFor="resolve-url" className="sr-only">
          Paste a job link, recruiter profile, or company URL
        </label>
        <input
          id="resolve-url"
          type="url"
          required
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="Paste a job link, recruiter profile, or company URL"
          className="flex-1 rounded-[var(--radius-control)] border border-border bg-surface-0 px-4 py-3 text-sm text-foreground outline-none focus:border-primary"
        />
        <button
          type="submit"
          disabled={isSubmitting}
          className="rounded-[var(--radius-control)] bg-primary px-5 py-3 text-sm font-medium text-primary-foreground transition-colors hover:opacity-90 disabled:opacity-60"
        >
          {isSubmitting ? "Checking…" : "Check trust score"}
        </button>
      </form>
      {error ? (
        <p className="text-sm text-signal-danger" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
