"use client";

import type { components } from "@verihire/shared";
import { ThumbsDown, ThumbsUp } from "lucide-react";
import { toast } from "sonner";

import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api-client/client";
import { useCurrentUser } from "@/lib/auth/use-auth";
import { useReviews, useVoteReview } from "@/lib/reviews/use-reviews";

type SubjectType = components["schemas"]["SubjectType"];

function average(review: components["schemas"]["ReviewRead"]): number {
  return (
    (review.rating_communication +
      review.rating_process_transparency +
      review.rating_offer_accuracy +
      review.rating_professionalism) /
    4
  );
}

export function ReviewList({
  subjectType,
  subjectId,
}: {
  subjectType: SubjectType;
  subjectId: string;
}) {
  const { data: user } = useCurrentUser();
  const { data, isLoading } = useReviews(subjectType, subjectId);
  const vote = useVoteReview(subjectType, subjectId);

  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 2 }).map((_, i) => (
          <Skeleton key={i} className="h-20" />
        ))}
      </div>
    );
  }

  if (!data || data.data.length === 0) {
    return (
      <EmptyState
        title="No reviews yet"
        description="Be the first to share what the recruitment process was actually like."
      />
    );
  }

  const castVote = async (reviewId: string, isHelpful: boolean) => {
    if (!user) {
      toast.error("Log in to vote.");
      return;
    }
    try {
      await vote.mutateAsync({ reviewId, isHelpful });
    } catch (err) {
      toast.error(err instanceof ApiError ? err.problem.detail : "Couldn't record your vote.");
    }
  };

  return (
    <ul className="space-y-3">
      {data.data.map((review) => (
        <li
          key={review.id}
          className="rounded-[var(--radius-card)] border border-border bg-surface p-4"
        >
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-foreground">
              {average(review).toFixed(1)} / 5
            </span>
            {review.verified_interaction ? (
              <span className="rounded-[var(--radius-pill)] bg-signal-verified/10 px-2 py-0.5 text-xs font-medium text-signal-verified">
                Verified interaction
              </span>
            ) : null}
          </div>
          {review.body ? (
            <p className="mt-2 text-sm text-foreground">{review.body}</p>
          ) : null}
          <div className="mt-3 flex items-center gap-3 text-xs text-muted-foreground">
            <button
              type="button"
              onClick={() => void castVote(review.id, true)}
              className="flex items-center gap-1 hover:text-foreground"
            >
              <ThumbsUp className="size-3.5" /> {review.helpful_count}
            </button>
            <button
              type="button"
              onClick={() => void castVote(review.id, false)}
              className="flex items-center gap-1 hover:text-foreground"
            >
              <ThumbsDown className="size-3.5" /> {review.unhelpful_count}
            </button>
          </div>
        </li>
      ))}
    </ul>
  );
}
