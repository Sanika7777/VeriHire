"use client";

import type { components } from "@verihire/shared";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useState } from "react";

import { apiFetch } from "@/lib/api-client/client";

type VerificationRead = components["schemas"]["VerificationRead"];
type SubjectType = components["schemas"]["SubjectType"];

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function useLatestVerification(subjectType: SubjectType, subjectId: string) {
  return useQuery<VerificationRead | null>({
    queryKey: ["verification", "latest", subjectType, subjectId],
    queryFn: () =>
      apiFetch<VerificationRead | null>(
        `/api/v1/verifications/latest?subject_type=${subjectType}&subject_id=${subjectId}`,
      ),
  });
}

export function useRequestVerification(subjectType: SubjectType, subjectId: string) {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);

  const start = useCallback(async () => {
    setIsRunning(true);
    setStatus("pending");
    try {
      const { verification_id } = await apiFetch<{ verification_id: string }>(
        "/api/v1/verifications",
        { method: "POST", body: { subject_type: subjectType, subject_id: subjectId } },
      );

      await new Promise<void>((resolve) => {
        const source = new EventSource(
          `${API_BASE_URL}/api/v1/verifications/${verification_id}/stream`,
        );
        source.addEventListener("stage", (event) => {
          const data = JSON.parse((event as MessageEvent).data) as { status: string };
          setStatus(data.status);
          if (data.status === "done" || data.status === "failed") {
            source.close();
            resolve();
          }
        });
        source.addEventListener("error", () => {
          source.close();
          resolve();
        });
      });

      await queryClient.invalidateQueries({
        queryKey: ["verification", "latest", subjectType, subjectId],
      });
    } finally {
      setIsRunning(false);
    }
  }, [subjectType, subjectId, queryClient]);

  return { start, status, isRunning };
}
