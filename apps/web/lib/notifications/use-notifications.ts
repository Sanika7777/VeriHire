"use client";

import type { components } from "@verihire/shared";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client/client";
import { useCurrentUser } from "@/lib/auth/use-auth";

type NotificationRead = components["schemas"]["NotificationRead"];
type Page = components["schemas"]["Page_NotificationRead_"];

export function useUnreadCount() {
  const { data: user } = useCurrentUser();
  return useQuery<{ count: number }>({
    queryKey: ["notifications", "unread-count"],
    queryFn: () => apiFetch<{ count: number }>("/api/v1/notifications/unread-count"),
    enabled: Boolean(user),
    refetchInterval: 30_000,
  });
}

export function useNotifications() {
  const { data: user } = useCurrentUser();
  return useQuery<Page>({
    queryKey: ["notifications", "list"],
    queryFn: () => apiFetch<Page>("/api/v1/notifications?limit=10"),
    enabled: Boolean(user),
  });
}

export function useMarkNotificationRead() {
  const queryClient = useQueryClient();
  return useMutation<NotificationRead, Error, string>({
    mutationFn: (id) =>
      apiFetch<NotificationRead>(`/api/v1/notifications/${id}/read`, { method: "POST" }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });
}
