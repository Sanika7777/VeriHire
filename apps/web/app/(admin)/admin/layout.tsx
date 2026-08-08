import Link from "next/link";

import { RequireStaff } from "@/components/layout/require-staff";
import { SiteHeader } from "@/components/layout/site-header";
import { hasServerSession } from "@/lib/auth/get-server-session";

const NAV_ITEMS = [
  { href: "/admin", label: "Dashboard" },
  { href: "/admin/reports", label: "Reports" },
  { href: "/admin/scoring", label: "Scoring config" },
];

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const likelyAuthenticated = await hasServerSession();

  return (
    <div className="flex min-h-full flex-1 flex-col">
      <SiteHeader likelyAuthenticated={likelyAuthenticated} />
      <RequireStaff>
        <div className="flex flex-1">
          <aside className="hidden w-56 shrink-0 border-r border-border px-4 py-6 sm:block">
            <p className="mb-4 px-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Trust &amp; Safety
            </p>
            <nav className="flex flex-col gap-1">
              {NAV_ITEMS.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="rounded-[var(--radius-control)] px-2 py-1.5 text-sm text-foreground transition-colors hover:bg-surface"
                >
                  {item.label}
                </Link>
              ))}
            </nav>
          </aside>
          <main id="main-content" className="flex-1 px-6 py-6">
            {children}
          </main>
        </div>
      </RequireStaff>
    </div>
  );
}
