import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Limitations",
  description: "What VeriHire's Trust Score can and can't tell you.",
};

export default function LimitationsPage() {
  return (
    <main id="main-content" className="mx-auto w-full max-w-2xl flex-1 px-6 py-16">
      <h1 className="text-2xl font-semibold text-foreground">
        Limitations — read this before trusting a score
      </h1>
      <p className="mt-4 text-foreground">
        VeriHire&apos;s Trust Score is <strong>advisory</strong>. It is not a determination of
        guilt, not a legal finding, and not a guarantee. Treat a low score as a reason to look
        closer, not as proof of fraud — and treat a high score as one good signal among several
        you should still apply your own judgement to.
      </p>

      <h2 className="mt-8 text-lg font-semibold text-foreground">
        What the fraud-detection model actually knows
      </h2>
      <p className="mt-2 text-foreground">
        The content-risk model is trained on job postings collected 2012–2014, predominantly in
        English and skewed toward the US. It will underperform on Indian regional postings,
        Hinglish or vernacular scam text, and scam techniques invented since then (Telegram task
        scams, crypto payment demands, deepfaked interviews). It is one of five inputs to the
        Trust Score — never the sole basis for a verdict — and a confirmed human-reviewed fraud
        report always overrides it.
      </p>

      <h2 className="mt-8 text-lg font-semibold text-foreground">Coverage gaps</h2>
      <p className="mt-2 text-foreground">
        Domain-age, DNS, and certificate checks depend on external data sources that don&apos;t
        cover every company or every country, and we don&apos;t run a company registry check at
        all. When a check can&apos;t run, we say so — an absent signal is shown as
        &quot;unrated,&quot; never guessed at as a default middling score.
      </p>

      <h2 className="mt-8 text-lg font-semibold text-foreground">Community signal is gameable</h2>
      <p className="mt-2 text-foreground">
        Reports and reviews are user-submitted. At low volume, a handful of coordinated fake
        reports or reviews can move a score more than they should. We&apos;re working on
        reviewer credibility weighting and brigading detection.
      </p>

      <h2 className="mt-8 text-lg font-semibold text-foreground">Our commitment</h2>
      <p className="mt-2 text-foreground">
        We&apos;ll keep publishing this page as the system changes. If you find a gap it doesn&apos;t
        mention, that&apos;s a bug in our honesty, not just our code.
      </p>
    </main>
  );
}
