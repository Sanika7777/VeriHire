"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { zodResolver } from "@hookform/resolvers/zod";
import { Suspense, useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { AuthCard } from "@/components/layout/auth-card";
import { ApiError } from "@/lib/api-client/client";
import { type ResetPasswordFormValues, resetPasswordSchema } from "@/lib/auth/schemas";
import { useResetPassword } from "@/lib/auth/use-auth";

const inputClass =
  "w-full rounded-[var(--radius-control)] border border-border bg-surface-0 px-3 py-2 text-sm text-foreground outline-none focus:border-primary";

function ResetPasswordForm() {
  const token = useSearchParams().get("token");
  const [done, setDone] = useState(false);
  const resetPassword = useResetPassword();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ResetPasswordFormValues>({ resolver: zodResolver(resetPasswordSchema) });

  const onSubmit = handleSubmit(async (values) => {
    if (!token) return;
    try {
      await resetPassword.mutateAsync({ token, new_password: values.new_password });
      setDone(true);
    } catch (error) {
      const message =
        error instanceof ApiError ? error.problem.detail : "Something went wrong.";
      toast.error(message);
    }
  });

  if (!token) {
    return (
      <AuthCard title="Invalid link" description="">
        <p className="text-sm text-muted-foreground">
          This password reset link is missing its token. Request a new one.
        </p>
        <Link
          href="/forgot-password"
          className="mt-4 inline-block text-sm font-medium text-primary"
        >
          Request a new link
        </Link>
      </AuthCard>
    );
  }

  if (done) {
    return (
      <AuthCard title="Password reset" description="">
        <p className="text-sm text-foreground" aria-live="polite">
          Your password has been reset. All existing sessions have been signed out.
        </p>
        <Link href="/login" className="mt-4 inline-block text-sm font-medium text-primary">
          Log in
        </Link>
      </AuthCard>
    );
  }

  return (
    <AuthCard title="Choose a new password" description="">
      <form onSubmit={onSubmit} noValidate className="space-y-4">
        <div>
          <label htmlFor="new_password" className="mb-1 block text-sm font-medium">
            New password
          </label>
          <input
            id="new_password"
            type="password"
            autoComplete="new-password"
            className={inputClass}
            aria-invalid={Boolean(errors.new_password)}
            {...register("new_password")}
          />
          {errors.new_password ? (
            <p className="mt-1 text-sm text-signal-danger">{errors.new_password.message}</p>
          ) : null}
        </div>

        <div>
          <label htmlFor="confirm_password" className="mb-1 block text-sm font-medium">
            Confirm password
          </label>
          <input
            id="confirm_password"
            type="password"
            autoComplete="new-password"
            className={inputClass}
            aria-invalid={Boolean(errors.confirm_password)}
            {...register("confirm_password")}
          />
          {errors.confirm_password ? (
            <p className="mt-1 text-sm text-signal-danger">
              {errors.confirm_password.message}
            </p>
          ) : null}
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full rounded-[var(--radius-control)] bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground transition-colors hover:opacity-90 disabled:opacity-60"
        >
          {isSubmitting ? "Resetting…" : "Reset password"}
        </button>
      </form>
    </AuthCard>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={null}>
      <ResetPasswordForm />
    </Suspense>
  );
}
