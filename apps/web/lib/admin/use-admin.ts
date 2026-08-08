"use client";

import type { components } from "@verihire/shared";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client/client";

type DashboardSummary = components["schemas"]["DashboardSummary"];
type ReportsPage = components["schemas"]["Page_ReportRead_"];
type ReportModerationDecision = components["schemas"]["ReportModerationDecision"];
type ReportRead = components["schemas"]["ReportRead"];
type ScoringConfigRead = components["schemas"]["ScoringConfigRead"];
type ScoringConfigUpdate = components["schemas"]["ScoringConfigUpdate"];
type ScoringConfigPreviewImpact = components["schemas"]["ScoringConfigPreviewImpact"];

export function useAdminDashboard() {
  return useQuery<DashboardSummary>({
    queryKey: ["admin", "dashboard"],
    queryFn: () => apiFetch<DashboardSummary>("/api/v1/admin/dashboard"),
    refetchInterval: 30_000,
  });
}

export function usePendingReports() {
  return useQuery<ReportsPage>({
    queryKey: ["admin", "reports"],
    queryFn: () => apiFetch<ReportsPage>("/api/v1/admin/reports?limit=50"),
  });
}

export function useConfirmReport() {
  const queryClient = useQueryClient();
  return useMutation<ReportRead, Error, { id: string; body: ReportModerationDecision }>({
    mutationFn: ({ id, body }) =>
      apiFetch<ReportRead>(`/api/v1/admin/reports/${id}/confirm`, { method: "POST", body }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["admin"] });
    },
  });
}

export function useRejectReport() {
  const queryClient = useQueryClient();
  return useMutation<ReportRead, Error, { id: string; body: ReportModerationDecision }>({
    mutationFn: ({ id, body }) =>
      apiFetch<ReportRead>(`/api/v1/admin/reports/${id}/reject`, { method: "POST", body }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["admin"] });
    },
  });
}

export function useScoringConfig() {
  return useQuery<ScoringConfigRead>({
    queryKey: ["admin", "scoring-config"],
    queryFn: () => apiFetch<ScoringConfigRead>("/api/v1/admin/scoring-config"),
  });
}

export function usePreviewScoringConfig() {
  return useMutation<ScoringConfigPreviewImpact, Error, ScoringConfigUpdate>({
    mutationFn: (body) =>
      apiFetch<ScoringConfigPreviewImpact>("/api/v1/admin/scoring-config/preview", {
        method: "POST",
        body,
      }),
  });
}

export function usePublishScoringConfig() {
  const queryClient = useQueryClient();
  return useMutation<ScoringConfigRead, Error, ScoringConfigUpdate>({
    mutationFn: (body) =>
      apiFetch<ScoringConfigRead>("/api/v1/admin/scoring-config", { method: "PUT", body }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["admin", "scoring-config"] });
    },
  });
}
