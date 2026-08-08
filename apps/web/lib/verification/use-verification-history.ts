"use client";

import type { components } from "@verihire/shared";
import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client/client";

type VerificationRead = components["schemas"]["VerificationRead"];
type SubjectType = components["schemas"]["SubjectType"];

export function useVerificationHistory(subjectType: SubjectType, subjectId: string) {
  return useQuery<VerificationRead[]>({
    queryKey: ["verification", "history", subjectType, subjectId],
    queryFn: () =>
      apiFetch<VerificationRead[]>(
        `/api/v1/verifications/history?subject_type=${subjectType}&subject_id=${subjectId}`,
      ),
  });
}
