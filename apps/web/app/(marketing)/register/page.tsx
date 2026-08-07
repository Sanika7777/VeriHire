"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { AuthCard } from "@/components/layout/auth-card";
import { ApiError } from "@/lib/api-client/client";
import { type RegisterFormValues, registerSchema } from "@/lib/auth/schemas";
import { useRegister } from "@/lib/auth/use-auth";

const inputClass =
  "w-full rounded-[var(--radius-control)] border border-border bg-surface-0 px-3 py-2 text-sm text-foreground outline-none focus:border-primary";

export default function RegisterPage() {
  const router = useRouter();
  const registerMutation = useRegister();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormValues>({ resolver: zodResolver(registerSchema) });

  const onSubmit = handleSubmit(async (values) => {
    try {
      await registerMutation.mutateAsync(values);
      toast.success("Account created. Check your email to verify it.");
      router.push("/");
    } catch (error) {
      const message =
        error instanceof ApiError ? error.problem.detail : "Something went wrong.";
      toast.error(message);
    }
  });

  return (
    <AuthCard
      title="Create your account"
      description="Verify recruiters and companies before you apply."
      footer={
        <>
          Already have an account?{" "}
          <Link href="/login" className="font-medium text-primary">
            Log in
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} noValidate className="space-y-4">
        <div>
          <label htmlFor="full_name" className="mb-1 block text-sm font-medium">
            Full name
          </label>
          <input
            id="full_name"
            type="text"
            autoComplete="name"
            className={inputClass}
            aria-invalid={Boolean(errors.full_name)}
            {...register("full_name")}
          />
          {errors.full_name ? (
            <p className="mt-1 text-sm text-signal-danger">{errors.full_name.message}</p>
          ) : null}
        </div>

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
          <label htmlFor="password" className="mb-1 block text-sm font-medium">
            Password
          </label>
          <input
            id="password"
            type="password"
            autoComplete="new-password"
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
          {isSubmitting ? "Creating account…" : "Create account"}
        </button>
      </form>
    </AuthCard>
  );
}
