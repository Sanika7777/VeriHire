"use client";

import type { components } from "@verihire/shared";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client/client";

type ReviewCreate = components["schemas"]["ReviewCreate"];
type ReviewsPage = components["schemas"]["Page_ReviewRead_"];
type ReviewRead = components["schemas"]["ReviewRead"];
type SubjectType = components["schemas"]["SubjectType"];

export function useReviews(subjectType: SubjectType, subjectId: string) {
  return useQuery<ReviewsPage>({
    queryKey: ["reviews", subjectType, subjectId],
    queryFn: () =>
      apiFetch<ReviewsPage>(
        `/api/v1/reviews?subject_type=${subjectType}&subject_id=${subjectId}&limit=20`,
      ),
  });
}

export function useCreateReview(subjectType: SubjectType, subjectId: string) {
  const queryClient = useQueryClient();
  return useMutation<ReviewRead, Error, ReviewCreate>({
    mutationFn: (body) => apiFetch<ReviewRead>("/api/v1/reviews", { method: "POST", body }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["reviews", subjectType, subjectId] });
    },
  });
}

export function useVoteReview(subjectType: SubjectType, subjectId: string) {
  const queryClient = useQueryClient();
  return useMutation<ReviewRead, Error, { reviewId: string; isHelpful: boolean }>({
    mutationFn: ({ reviewId, isHelpful }) =>
      apiFetch<ReviewRead>(`/api/v1/reviews/${reviewId}/vote`, {
        method: "POST",
        body: { is_helpful: isHelpful },
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["reviews", subjectType, subjectId] });
    },
  });
}
