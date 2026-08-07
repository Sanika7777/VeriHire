"use client";

import type { components } from "@verihire/shared";
import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client/client";

export type SearchResponse = components["schemas"]["SearchResponse"];
export type SubjectType = components["schemas"]["SubjectType"];
export type TrustBand = components["schemas"]["TrustBand"];

export interface SearchFilters {
  q: string;
  subjectType?: SubjectType;
  band?: TrustBand;
  cursor?: string;
}

function buildSearchPath(filters: SearchFilters): string {
  const params = new URLSearchParams({ q: filters.q, limit: "20" });
  if (filters.subjectType) params.set("type", filters.subjectType);
  if (filters.band) params.set("band", filters.band);
  if (filters.cursor) params.set("cursor", filters.cursor);
  return `/api/v1/search?${params.toString()}`;
}

export function useSearch(filters: SearchFilters) {
  return useQuery<SearchResponse>({
    queryKey: ["search", filters],
    queryFn: () => apiFetch<SearchResponse>(buildSearchPath(filters)),
    enabled: filters.q.trim().length > 0,
    placeholderData: (previous) => previous,
  });
}
