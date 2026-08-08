import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="border-t border-border px-6 py-10 text-sm text-muted-foreground">
      <div className="mx-auto flex max-w-5xl flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">
        <div className="max-w-sm">
          <p className="font-heading text-base font-semibold text-foreground">VeriHire</p>
          <p className="mt-2">
            A Trust Score is advisory, never a determination of guilt. Scores blend identity,
            company legitimacy, ML-derived content risk, link safety and community reports —
            and we always show why.{" "}
            <Link href="/limitations" className="font-medium text-primary">
              Read our limitations
            </Link>
            .
          </p>
        </div>
        <nav className="flex gap-8">
          <div>
            <p className="mb-2 font-medium text-foreground">Product</p>
            <ul className="space-y-1">
              <li>
                <Link href="/search" className="hover:text-foreground">
                  Search
                </Link>
              </li>
              <li>
                <Link href="/limitations" className="hover:text-foreground">
                  Limitations
                </Link>
              </li>
            </ul>
          </div>
          <div>
            <p className="mb-2 font-medium text-foreground">Account</p>
            <ul className="space-y-1">
              <li>
                <Link href="/login" className="hover:text-foreground">
                  Log in
                </Link>
              </li>
              <li>
                <Link href="/register" className="hover:text-foreground">
                  Sign up
                </Link>
              </li>
            </ul>
          </div>
        </nav>
      </div>
      <p className="mx-auto mt-8 max-w-5xl text-xs">
        © {new Date().getFullYear()} VeriHire. Trust scores are advisory only.
      </p>
    </footer>
  );
}
