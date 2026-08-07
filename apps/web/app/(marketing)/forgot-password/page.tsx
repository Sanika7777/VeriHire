"use client";

import Link from "next/link";
import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { AuthCard } from "@/components/layout/auth-card";
import { type ForgotPasswordFormValues, forgotPasswordSchema } from "@/lib/auth/schemas";
import { useForgotPassword } from "@/lib/auth/use-auth";

const inputClass =
  "w-full rounded-[var(--radius-control)] border border-border bg-surface-0 px-3 py-2 text-sm text-foreground outline-none focus:border-primary";

export default function ForgotPasswordPage() {
  const [submitted, setSubmitted] = useState(false);
  const forgotPassword = useForgotPassword();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ForgotPasswordFormValues>({ resolver: zodResolver(forgotPasswordSchema) });

  const onSubmit = handleSubmit(async (values) => {
    await forgotPassword.mutateAsync(values);
    setSubmitted(true);
  });

  if (submitted) {
    return (
      <AuthCard title="Check your email" description="">
        <p className="text-sm text-foreground" aria-live="polite">
          If an account exists for that email, we&apos;ve sent a link to reset your
          password. It expires in 1 hour.
        </p>
        <Link href="/login" className="mt-4 inline-block text-sm font-medium text-primary">
          Back to login
        </Link>
      </AuthCard>
    );
  }

  return (
    <AuthCard
      title="Forgot your password?"
      description="We'll email you a link to reset it."
      footer={
        <Link href="/login" className="font-medium text-primary">
          Back to login
        </Link>
      }
    >
      <form onSubmit={onSubmit} noValidate className="space-y-4">
        <div>
          <label htmlFor="email" className="mb-1 block text-sm font-medium">
            Email
          </label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            className={inputClass}
            aria-invalid={Boolean(errors.email)}
            {...register("email")}
          />
          {errors.email ? (
            <p className="mt-1 text-sm text-signal-danger">{errors.email.message}</p>
          ) : null}
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full rounded-[var(--radius-control)] bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground transition-colors hover:opacity-90 disabled:opacity-60"
        >
          {isSubmitting ? "Sending…" : "Send reset link"}
        </button>
      </form>
    </AuthCard>
  );
}
