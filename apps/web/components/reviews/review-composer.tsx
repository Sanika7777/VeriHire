"use client";

import type { components } from "@verihire/shared";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { StarRatingInput } from "@/components/reviews/star-rating-input";
import { ApiError } from "@/lib/api-client/client";
import { useCurrentUser } from "@/lib/auth/use-auth";
import { useCreateReview } from "@/lib/reviews/use-reviews";

type SubjectType = components["schemas"]["SubjectType"];

const DIMENSIONS = [
  { key: "rating_communication", label: "Communication" },
  { key: "rating_process_transparency", label: "Process transparency" },
  { key: "rating_offer_accuracy", label: "Offer accuracy" },
  { key: "rating_professionalism", label: "Professionalism" },
] as const;

export function ReviewComposer({
  subjectType,
  subjectId,
}: {
  subjectType: SubjectType;
  subjectId: string;
}) {
  const { data: user } = useCurrentUser();
  const [open, setOpen] = useState(false);
  const [ratings, setRatings] = useState<Record<string, number>>({});
  const [body, setBody] = useState("");
  const [verifiedInteraction, setVerifiedInteraction] = useState(false);
  const createReview = useCreateReview(subjectType, subjectId);

  if (!user) return null;

  if (!open) {
    return (
      <Button variant="outline" size="sm" onClick={() => setOpen(true)}>
        Write a review
      </Button>
    );
  }

  const allRated = DIMENSIONS.every((d) => (ratings[d.key] ?? 0) > 0);

  const submit = async () => {
    if (!allRated) {
      toast.error("Rate all four dimensions before submitting.");
      return;
    }
    try {
      await createReview.mutateAsync({
        subject_type: subjectType,
        subject_id: subjectId,
        rating_communication: ratings.rating_communication ?? 0,
        rating_process_transparency: ratings.rating_process_transparency ?? 0,
        rating_offer_accuracy: ratings.rating_offer_accuracy ?? 0,
        rating_professionalism: ratings.rating_professionalism ?? 0,
        body: body || null,
        verified_interaction: verifiedInteraction,
      });
      toast.success("Review posted. Thanks for helping other job seekers.");
      setOpen(false);
      setRatings({});
      setBody("");
      setVerifiedInteraction(false);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.problem.detail : "Couldn't post your review.");
    }
  };

  return (
    <div className="rounded-[var(--radius-card)] border border-border bg-surface p-4">
      <div className="grid gap-4 sm:grid-cols-2">
        {DIMENSIONS.map((d) => (
          <StarRatingInput
            key={d.key}
            label={d.label}
            value={ratings[d.key] ?? 0}
            onChange={(v) => setRatings((prev) => ({ ...prev, [d.key]: v }))}
          />
        ))}
      </div>

      <label className="mt-4 block text-sm text-foreground" htmlFor="review-body">
        Your experience (optional)
      </label>
      <textarea
        id="review-body"
        value={body}
        onChange={(e) => setBody(e.target.value)}
        rows={3}
        className="mt-1 w-full rounded-[var(--radius-control)] border border-border bg-surface-0 px-3 py-2 text-sm"
        placeholder="What was the recruitment process actually like?"
      />

      <label className="mt-3 flex items-center gap-2 text-sm text-foreground">
        <input
          type="checkbox"
          checked={verifiedInteraction}
          onChange={(e) => setVerifiedInteraction(e.target.checked)}
          className="size-4 rounded border-border"
        />
        I actually interacted with this recruiter/company
      </label>

      <div className="mt-4 flex gap-2">
        <Button size="sm" onClick={() => void submit()} disabled={createReview.isPending}>
          {createReview.isPending ? "Posting…" : "Post review"}
        </Button>
        <Button size="sm" variant="ghost" onClick={() => setOpen(false)}>
          Cancel
        </Button>
      </div>
    </div>
  );
}
