"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";

import { AuthCard } from "@/components/layout/auth-card";
import { ApiError } from "@/lib/api-client/client";
import { useVerifyEmail } from "@/lib/auth/use-auth";

type Status = "verifying" | "success" | "error";

function VerifyEmailContent() {
  const token = useSearchParams().get("token");
  const verifyEmail = useVerifyEmail();
  const [status, setStatus] = useState<Status>("verifying");
  const [errorMessage, setErrorMessage] = useState("");
  const hasRun = useRef(false);

  useEffect(() => {
    if (!token || hasRun.current) return;
    hasRun.current = true;

    verifyEmail.mutate(
      { token },
      {
        onSuccess: () => setStatus("success"),
        onError: (error) => {
          setErrorMessage(
            error instanceof ApiError ? error.problem.detail : "Something went wrong.",
          );
          setStatus("error");
        },
      },
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  if (!token) {
    return (
      <AuthCard title="Invalid link" description="">
        <p className="text-sm text-muted-foreground">
          This verification link is missing its token.
        </p>
      </AuthCard>
    );
  }

  if (status === "verifying") {
    return (
      <AuthCard title="Verifying your email…" description="">
        <div
          className="h-2 w-full animate-pulse rounded-full bg-border"
          aria-live="polite"
          aria-label="Verifying"
        />
      </AuthCard>
    );
  }

  if (status === "error") {
    return (
      <AuthCard title="Verification failed" description="">
        <p className="text-sm text-signal-danger" aria-live="polite">
          {errorMessage}
        </p>
        <Link href="/login" className="mt-4 inline-block text-sm font-medium text-primary">
          Back to login
        </Link>
      </AuthCard>
    );
  }

  return (
    <AuthCard title="Email verified" description="">
      <p className="text-sm text-foreground" aria-live="polite">
        Your email has been verified. You&apos;re all set.
      </p>
      <Link href="/" className="mt-4 inline-block text-sm font-medium text-primary">
        Continue to VeriHire
      </Link>
    </AuthCard>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={null}>
      <VerifyEmailContent />
    </Suspense>
  );
}
