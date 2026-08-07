"use client";

import type { components } from "@verihire/shared";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch, setAccessToken } from "@/lib/api-client/client";

type UserRead = components["schemas"]["UserRead"];
type AccessTokenResponse = components["schemas"]["AccessTokenResponse"];
type MessageResponse = components["schemas"]["MessageResponse"];
type RegisterRequest = components["schemas"]["RegisterRequest"];
type LoginRequest = components["schemas"]["LoginRequest"];
type ForgotPasswordRequest = components["schemas"]["ForgotPasswordRequest"];
type ResetPasswordRequest = components["schemas"]["ResetPasswordRequest"];
type VerifyEmailRequest = components["schemas"]["VerifyEmailRequest"];

const CURRENT_USER_KEY = ["auth", "me"] as const;

export function useCurrentUser() {
  return useQuery<UserRead | null>({
    queryKey: CURRENT_USER_KEY,
    queryFn: async () => {
      try {
        return await apiFetch<UserRead>("/api/v1/auth/me");
      } catch {
        return null;
      }
    },
    retry: false,
    staleTime: 60_000,
  });
}

function useAuthMutation<TVariables>(
  path: string,
  onSuccess?: (data: AccessTokenResponse) => void,
) {
  const queryClient = useQueryClient();
  return useMutation<AccessTokenResponse, Error, TVariables>({
    mutationFn: (variables) =>
      apiFetch<AccessTokenResponse>(path, { method: "POST", body: variables }),
    onSuccess: (data) => {
      setAccessToken(data.access_token);
      queryClient.setQueryData(CURRENT_USER_KEY, data.user);
      onSuccess?.(data);
    },
  });
}

export function useRegister() {
  return useAuthMutation<RegisterRequest>("/api/v1/auth/register");
}

export function useLogin() {
  return useAuthMutation<LoginRequest>("/api/v1/auth/login");
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => apiFetch<MessageResponse>("/api/v1/auth/logout", { method: "POST" }),
    onSuccess: () => {
      setAccessToken(null);
      queryClient.setQueryData(CURRENT_USER_KEY, null);
    },
  });
}

export function useForgotPassword() {
  return useMutation<MessageResponse, Error, ForgotPasswordRequest>({
    mutationFn: (variables) =>
      apiFetch<MessageResponse>("/api/v1/auth/forgot-password", {
        method: "POST",
        body: variables,
      }),
  });
}

export function useResetPassword() {
  return useMutation<MessageResponse, Error, ResetPasswordRequest>({
    mutationFn: (variables) =>
      apiFetch<MessageResponse>("/api/v1/auth/reset-password", {
        method: "POST",
        body: variables,
      }),
  });
}

export function useVerifyEmail() {
  return useMutation<MessageResponse, Error, VerifyEmailRequest>({
    mutationFn: (variables) =>
      apiFetch<MessageResponse>("/api/v1/auth/verify-email", {
        method: "POST",
        body: variables,
      }),
  });
}
