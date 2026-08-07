import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "VeriHire — Verify a recruiter before you apply",
};

export default function MarketingHomePage() {
  return (
    <main
      id="main-content"
      className="flex flex-1 flex-col items-center justify-center gap-6 px-6 py-24 text-center"
    >
      <span className="rounded-[var(--radius-pill)] border border-border bg-surface px-4 py-1 text-sm font-medium text-muted-foreground">
        Built for job seekers in India
      </span>
      <h1 className="max-w-2xl text-4xl font-semibold text-foreground sm:text-5xl">
        Know who&apos;s hiring you before you send a single reply.
      </h1>
      <p className="max-w-xl text-lg text-muted-foreground">
        Paste a job link, a recruiter profile, or a company name. VeriHire
        returns a Trust Score with a full, explainable breakdown — never a
        black box.
      </p>
    </main>
  );
}
