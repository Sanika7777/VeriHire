"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { LayoutDashboard, LogOut, UserRound } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { CommandPalette } from "@/components/layout/command-palette";
import { NotificationBell } from "@/components/layout/notification-bell";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { useCurrentUser, useLogout } from "@/lib/auth/use-auth";

export function SiteHeader({ likelyAuthenticated }: { likelyAuthenticated: boolean }) {
  const { data: user, isLoading } = useCurrentUser();
  const logout = useLogout();
  const router = useRouter();

  const showAuthedShell = user ?? (isLoading && likelyAuthenticated ? undefined : null);
  const isStaff = user?.role === "admin" || user?.role === "moderator";

  return (
    <header className="flex items-center justify-between gap-4 border-b border-border px-6 py-4">
      <div className="flex items-center gap-6">
        <Link href="/" className="text-lg font-semibold text-foreground">
          VeriHire
        </Link>
        <nav className="hidden items-center gap-4 text-sm text-muted-foreground sm:flex">
          <Link href="/search" className="hover:text-foreground">
            Search
          </Link>
          <Link href="/compare" className="hover:text-foreground">
            Compare
          </Link>
          {isStaff ? (
            <Link href="/admin" className="hover:text-foreground">
              Admin
            </Link>
          ) : null}
        </nav>
      </div>

      <div className="flex items-center gap-2">
        <CommandPalette />
        <ThemeToggle />

        {showAuthedShell === undefined ? (
          <div className="h-9 w-9 animate-pulse rounded-full bg-border" />
        ) : showAuthedShell ? (
          <>
            <NotificationBell />
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" aria-label="User menu">
                  <UserRound className="size-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuLabel>{showAuthedShell.full_name}</DropdownMenuLabel>
                <DropdownMenuSeparator />
                {isStaff ? (
                  <DropdownMenuItem onClick={() => router.push("/admin")}>
                    <LayoutDashboard />
                    Admin console
                  </DropdownMenuItem>
                ) : null}
                <DropdownMenuItem
                  variant="destructive"
                  onClick={() => logout.mutate(undefined, { onSuccess: () => router.push("/") })}
                >
                  <LogOut />
                  Log out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </>
        ) : (
          <>
            <Button variant="ghost" asChild>
              <Link href="/login">Log in</Link>
            </Button>
            <Button asChild>
              <Link href="/register">Sign up</Link>
            </Button>
          </>
        )}
      </div>
    </header>
  );
}
