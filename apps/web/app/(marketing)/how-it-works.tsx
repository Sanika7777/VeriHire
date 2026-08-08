import { Link2, ScanSearch, ShieldCheck } from "lucide-react";

const STEPS = [
  {
    icon: Link2,
    title: "Paste a link",
    description:
      "A job posting, a recruiter's LinkedIn profile, or a company website — VeriHire figures out what it is.",
  },
  {
    icon: ScanSearch,
    title: "We check everything",
    description:
      "Domain age, DNS and TLS records, company registries, a fraud-detection model trained on real scam postings, link safety, and community reports — five signals, computed live.",
  },
  {
    icon: ShieldCheck,
    title: "Get an explainable verdict",
    description:
      "A Trust Score from 0–100 with the plain-language reasons behind it. Never a black box, never a guess dressed up as certainty.",
  },
];

export function HowItWorks() {
  return (
    <section className="mx-auto w-full max-w-4xl px-6 py-16">
      <h2 className="text-center text-2xl font-semibold text-foreground">How it works</h2>
      <div className="mt-10 grid gap-8 sm:grid-cols-3">
        {STEPS.map((step, i) => (
          <div key={step.title} className="flex flex-col items-center text-center">
            <div className="flex size-12 items-center justify-center rounded-full bg-brand-blue-100 text-primary">
              <step.icon className="size-6" />
            </div>
            <p className="mt-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Step {i + 1}
            </p>
            <h3 className="mt-1 font-medium text-foreground">{step.title}</h3>
            <p className="mt-2 text-sm text-muted-foreground">{step.description}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
