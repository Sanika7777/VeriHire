"use client";

import type { components } from "@verihire/shared";
import { useMutation } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client/client";

type ClaimStart = components["schemas"]["ClaimStart"];
type ClaimStartResponse = components["schemas"]["ClaimStartResponse"];
type ClaimRead = components["schemas"]["ClaimRead"];

export function useStartClaim(companyId: string) {
  return useMutation<ClaimStartResponse, Error, ClaimStart>({
    mutationFn: (body) =>
      apiFetch<ClaimStartResponse>(`/api/v1/companies/${companyId}/claim`, {
        method: "POST",
        body,
      }),
  });
}

export function useVerifyDnsClaim() {
  return useMutation<ClaimRead, Error, string>({
    mutationFn: (claimId) =>
      apiFetch<ClaimRead>(`/api/v1/companies/claims/${claimId}/verify-dns`, { method: "POST" }),
  });
}
