"use client";

import type { components } from "@verihire/shared";
import { useState } from "react";
import { toast } from "sonner";

import { ApiError } from "@/lib/api-client/client";
import { useCurrentUser } from "@/lib/auth/use-auth";
import { useCreateReport } from "@/lib/reports/use-reports";

type SubjectType = components["schemas"]["SubjectType"];
type ReportCategory = components["schemas"]["ReportCategory"];

const CATEGORIES: Array<{ value: ReportCategory; label: string }> = [
  { value: "advance_fee", label: "Asked for money upfront" },
  { value: "fake_job_posting", label: "Fake or nonexistent job" },
  { value: "impersonation", label: "Impersonating a real company" },
  { value: "data_harvesting", label: "Collecting personal data" },
  { value: "interview_scam", label: "Fake interview process" },
  { value: "payment_scam", label: "Payment/salary scam" },
  { value: "other", label: "Something else" },
];

export function ReportButton({
  subjectType,
  subjectId,
}: {
  subjectType: SubjectType;
  subjectId: string;
}) {
  const { data: user } = useCurrentUser();
  const [open, setOpen] = useState(false);
  const [category, setCategory] = useState<ReportCategory>("advance_fee");
  const [description, setDescription] = useState("");
  const createReport = useCreateReport();

  if (!user) return null;

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createReport.mutateAsync({
        subject_type: subjectType,
        subject_id: subjectId,
        category,
        description,
      });
      toast.success("Report submitted. Our moderation team will review it.");
      setOpen(false);
      setDescription("");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.problem.detail : "Something went wrong.");
    }
  };

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="text-sm font-medium text-signal-danger"
      >
        Report this
      </button>
    );
  }

  return (
    <form
      onSubmit={onSubmit}
      className="mt-3 space-y-3 rounded-[var(--radius-card)] border border-border bg-surface p-4"
    >
      <div>
        <label htmlFor="report-category" className="mb-1 block text-sm font-medium">
          What happened?
        </label>
        <select
          id="report-category"
          value={category}
          onChange={(e) => setCategory(e.target.value as ReportCategory)}
          className="w-full rounded-[var(--radius-control)] border border-border bg-surface-0 px-3 py-2 text-sm"
        >
          {CATEGORIES.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="report-description" className="mb-1 block text-sm font-medium">
          Details
        </label>
        <textarea
          id="report-description"
          required
          minLength={10}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={4}
          className="w-full rounded-[var(--radius-control)] border border-border bg-surface-0 px-3 py-2 text-sm"
          placeholder="What happened, and when?"
        />
      </div>
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={createReport.isPending}
          className="rounded-[var(--radius-control)] bg-signal-danger px-4 py-2 text-sm font-medium text-white transition-colors hover:opacity-90 disabled:opacity-60"
        >
          {createReport.isPending ? "Submitting…" : "Submit report"}
        </button>
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="rounded-[var(--radius-control)] border border-border px-4 py-2 text-sm font-medium text-foreground"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
