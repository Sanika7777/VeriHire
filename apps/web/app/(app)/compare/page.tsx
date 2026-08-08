"use client";

import type { components } from "@verihire/shared";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { VerificationPanel } from "@/components/verification/verification-panel";

import { ComparePicker } from "./compare-picker";

type SearchItem = components["schemas"]["SearchResultItem"];
type SubjectType = components["schemas"]["SubjectType"];

function Slot({
  slot,
  subjectType,
  subjectId,
  name,
}: {
  slot: "a" | "b";
  subjectType: SubjectType | null;
  subjectId: string | null;
  name: string | null;
}) {
  const router = useRouter();
  const searchParams = useSearchParams();

  const pick = (item: SearchItem) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set(`${slot}Type`, item.subject_type);
    params.set(`${slot}Id`, item.id);
    params.set(`${slot}Name`, item.name);
    router.push(`/compare?${params.toString()}`);
  };

  if (!subjectType || !subjectId) {
    return <ComparePicker label={`Entity ${slot.toUpperCase()}`} onPick={pick} />;
  }

  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-medium text-foreground">{name}</h2>
        <button
          type="button"
          onClick={() => {
            const params = new URLSearchParams(searchParams.toString());
            params.delete(`${slot}Type`);
            params.delete(`${slot}Id`);
            params.delete(`${slot}Name`);
            router.push(`/compare?${params.toString()}`);
          }}
          className="text-xs font-medium text-muted-foreground hover:text-foreground"
        >
          Change
        </button>
      </div>
      <VerificationPanel subjectType={subjectType} subjectId={subjectId} />
    </div>
  );
}

function CompareContent() {
  const searchParams = useSearchParams();
  const aType = searchParams.get("aType") as SubjectType | null;
  const aId = searchParams.get("aId");
  const aName = searchParams.get("aName");
  const bType = searchParams.get("bType") as SubjectType | null;
  const bId = searchParams.get("bId");
  const bName = searchParams.get("bName");

  return (
    <main id="main-content" className="mx-auto w-full max-w-4xl flex-1 px-6 py-10">
      <h1 className="text-2xl font-semibold text-foreground">Compare trust scores</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Pick two companies, recruiters or postings to see them side by side.
      </p>
      <div className="mt-8 grid gap-8 sm:grid-cols-2">
        <Slot slot="a" subjectType={aType} subjectId={aId} name={aName} />
        <Slot slot="b" subjectType={bType} subjectId={bId} name={bName} />
      </div>
    </main>
  );
}

export default function ComparePage() {
  return (
    <Suspense fallback={null}>
      <CompareContent />
    </Suspense>
  );
}
