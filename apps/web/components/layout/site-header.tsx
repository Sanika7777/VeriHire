"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { useCurrentUser, useLogout } from "@/lib/auth/use-auth";

export function SiteHeader({ likelyAuthenticated }: { likelyAuthenticated: boolean }) {
  const { data: user, isLoading } = useCurrentUser();
  const logout = useLogout();
  const router = useRouter();

  const showAuthedShell = user ?? (isLoading && likelyAuthenticated ? undefined : null);

  return (
    <header className="flex items-center justify-between border-b border-border px-6 py-4">
      <Link href="/" className="text-lg font-semibold text-foreground">
        VeriHire
      </Link>
      <nav className="flex items-center gap-4 text-sm">
        {showAuthedShell === undefined ? (
          <div className="h-8 w-24 animate-pulse rounded-[var(--radius-control)] bg-border" />
        ) : showAuthedShell ? (
          <>
            <span className="text-muted-foreground">{showAuthedShell.full_name}</span>
            <button
              type="button"
              onClick={() => {
                logout.mutate(undefined, { onSuccess: () => router.push("/") });
              }}
              className="rounded-[var(--radius-control)] border border-border px-3 py-1.5 font-medium text-foreground transition-colors hover:bg-surface-0"
            >
              Log out
            </button>
          </>
        ) : (
          <>
            <Link href="/login" className="font-medium text-foreground">
              Log in
            </Link>
            <Link
              href="/register"
              className="rounded-[var(--radius-control)] bg-primary px-3 py-1.5 font-medium text-primary-foreground transition-colors hover:opacity-90"
            >
              Sign up
            </Link>
          </>
        )}
      </nav>
    </header>
  );
}
