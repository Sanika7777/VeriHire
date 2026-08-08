import type { components } from "@verihire/shared";
import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { ReviewComposer } from "@/components/reviews/review-composer";
import { ReviewList } from "@/components/reviews/review-list";
import { VerificationPanel } from "@/components/verification/verification-panel";
import { serverFetch } from "@/lib/api-client/server-fetch";

type RecruiterRead = components["schemas"]["RecruiterRead"];

async function getRecruiter(id: string): Promise<RecruiterRead | null> {
  return serverFetch<RecruiterRead>(`/api/v1/recruiters/${id}`);
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  const recruiter = await getRecruiter(id);
  return { title: recruiter?.full_name ?? "Recruiter" };
}

export default async function RecruiterDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const recruiter = await getRecruiter(id);
  if (!recruiter) notFound();

  return (
    <main id="main-content" className="mx-auto w-full max-w-2xl flex-1 px-6 py-10">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">{recruiter.full_name}</h1>
        {recruiter.headline ? (
          <p className="mt-1 text-sm text-muted-foreground">{recruiter.headline}</p>
        ) : null}
      </div>

      <p className="mt-4 text-sm text-foreground">
        {recruiter.bio ?? "No bio has been added for this recruiter yet."}
      </p>

      {recruiter.linkedin_url ? (
        <a
          href={recruiter.linkedin_url}
          target="_blank"
          rel="noopener noreferrer nofollow"
          className="mt-4 inline-block text-sm font-medium text-primary"
        >
          View LinkedIn profile ↗
        </a>
      ) : null}

      <div className="mt-8">
        <VerificationPanel subjectType="recruiter" subjectId={recruiter.id} />
      </div>

      <div className="mt-8">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-foreground">Reviews</h2>
          <ReviewComposer subjectType="recruiter" subjectId={recruiter.id} />
        </div>
        <ReviewList subjectType="recruiter" subjectId={recruiter.id} />
      </div>
    </main>
  );
}
