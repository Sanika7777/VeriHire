import Link from "next/link";

export default function NotFound() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-4 px-6 py-24 text-center">
      <p className="text-sm font-medium text-muted-foreground">404</p>
      <h1 className="text-3xl font-semibold text-foreground">
        We couldn&apos;t find that page.
      </h1>
      <p className="max-w-md text-muted-foreground">
        The link may be broken or the page may have moved. Try searching for
        the recruiter, company or posting you were looking for instead.
      </p>
      <Link
        href="/"
        className="mt-2 rounded-[var(--radius-control)] bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground transition-colors hover:opacity-90"
      >
        Back to VeriHire
      </Link>
    </main>
  );
}
