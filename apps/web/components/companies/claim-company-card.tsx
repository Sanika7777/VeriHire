"use client";

import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api-client/client";
import { useCurrentUser } from "@/lib/auth/use-auth";
import { useStartClaim, useVerifyDnsClaim } from "@/lib/companies/use-claim";

export function ClaimCompanyCard({ companyId }: { companyId: string }) {
  const { data: user } = useCurrentUser();
  const startClaim = useStartClaim(companyId);
  const verifyDns = useVerifyDnsClaim();
  const [claim, setClaim] = useState<{ claimId: string; instructions: string; method: string } | null>(
    null,
  );
  const [verified, setVerified] = useState(false);

  if (!user) return null;

  const start = async (method: "dns_txt" | "email_domain") => {
    try {
      const result = await startClaim.mutateAsync({ method });
      setClaim({ claimId: result.claim_id, instructions: result.instructions, method });
      if (method === "email_domain") {
        setVerified(true);
        toast.success("Claim approved — your account email matched this company's domain.");
      }
    } catch (err) {
      toast.error(err instanceof ApiError ? err.problem.detail : "Couldn't start claim.");
    }
  };

  const verify = async () => {
    if (!claim) return;
    try {
      await verifyDns.mutateAsync(claim.claimId);
      setVerified(true);
      toast.success("Domain verified — this company is now claimed.");
    } catch (err) {
      toast.error(
        err instanceof ApiError ? err.problem.detail : "DNS record not found yet.",
      );
    }
  };

  if (verified) {
    return (
      <div className="rounded-[var(--radius-card)] border border-signal-verified/30 bg-signal-verified/5 p-4 text-sm text-foreground">
        You&apos;ve claimed this company.
      </div>
    );
  }

  if (claim) {
    return (
      <div className="rounded-[var(--radius-card)] border border-border bg-surface p-4 text-sm">
        <p className="text-foreground">{claim.instructions}</p>
        {claim.method === "dns_txt" ? (
          <Button
            size="sm"
            className="mt-3"
            onClick={() => void verify()}
            disabled={verifyDns.isPending}
          >
            {verifyDns.isPending ? "Checking DNS…" : "I've added the record — verify now"}
          </Button>
        ) : null}
      </div>
    );
  }

  return (
    <div className="rounded-[var(--radius-card)] border border-dashed border-border p-4">
      <p className="text-sm text-foreground">Is this your company?</p>
      <p className="mt-1 text-xs text-muted-foreground">
        Claim it to manage the listing and show it&apos;s verified.
      </p>
      <div className="mt-3 flex gap-2">
        <Button size="sm" variant="outline" onClick={() => void start("email_domain")}>
          Claim with work email
        </Button>
        <Button size="sm" variant="outline" onClick={() => void start("dns_txt")}>
          Claim with DNS record
        </Button>
      </div>
    </div>
  );
}
