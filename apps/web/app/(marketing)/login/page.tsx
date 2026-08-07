"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { AuthCard } from "@/components/layout/auth-card";
import { ApiError } from "@/lib/api-client/client";
import { type LoginFormValues, loginSchema } from "@/lib/auth/schemas";
import { useLogin } from "@/lib/auth/use-auth";

const inputClass =
  "w-full rounded-[var(--radius-control)] border border-border bg-surface-0 px-3 py-2 text-sm text-foreground outline-none focus:border-primary";

export default function LoginPage() {
  const router = useRouter();
  const loginMutation = useLogin();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({ resolver: zodResolver(loginSchema) });

  const onSubmit = handleSubmit(async (values) => {
    try {
      await loginMutation.mutateAsync(values);
      router.push("/");
    } catch (error) {
      const message =
        error instanceof ApiError ? error.problem.detail : "Something went wrong.";
      toast.error(message);
    }
  });

  return (
    <AuthCard
      title="Log in"
      description="Welcome back to VeriHire."
      footer={
        <>
          New here?{" "}
          <Link href="/register" className="font-medium text-primary">
            Create an account
          </Link>
        </>
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

        <div>
          <div className="mb-1 flex items-center justify-between">
            <label htmlFor="password" className="block text-sm font-medium">
              Password
            </label>
            <Link href="/forgot-password" className="text-sm text-primary">
              Forgot password?
            </Link>
          </div>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            className={inputClass}
            aria-invalid={Boolean(errors.password)}
            {...register("password")}
          />
          {errors.password ? (
            <p className="mt-1 text-sm text-signal-danger">{errors.password.message}</p>
          ) : null}
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full rounded-[var(--radius-control)] bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground transition-colors hover:opacity-90 disabled:opacity-60"
        >
          {isSubmitting ? "Logging in…" : "Log in"}
        </button>
      </form>
    </AuthCard>
  );
}
