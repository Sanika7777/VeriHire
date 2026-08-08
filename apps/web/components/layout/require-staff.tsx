"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useCurrentUser } from "@/lib/auth/use-auth";

export function RequireStaff({ children }: { children: React.ReactNode }) {
  const { data: user, isLoading } = useCurrentUser();
  const router = useRouter();
  const isStaff = user?.role === "admin" || user?.role === "moderator";

  useEffect(() => {
    if (!isLoading && !isStaff) {
      router.replace("/");
    }
  }, [isLoading, isStaff, router]);

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center py-24">
        <div className="h-10 w-10 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!isStaff) return null;

  return <>{children}</>;
}
