"use client";

import type { components } from "@verihire/shared";
import { useMutation } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client/client";

type ReportCreate = components["schemas"]["ReportCreate"];
type ReportRead = components["schemas"]["ReportRead"];

export function useCreateReport() {
  return useMutation<ReportRead, Error, ReportCreate>({
    mutationFn: (body) =>
      apiFetch<ReportRead>("/api/v1/reports", {
        method: "POST",
        body,
      }),
  });
}
