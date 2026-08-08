import type { components } from "@verihire/shared";
import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { VerificationPanel } from "@/components/verification/verification-panel";
import { serverFetch } from "@/lib/api-client/server-fetch";

type JobPostingRead = components["schemas"]["JobPostingRead"];

async function getPosting(id: string): Promise<JobPostingRead | null> {
  return serverFetch<JobPostingRead>(`/api/v1/postings/${id}`);
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  const posting = await getPosting(id);
  return { title: posting?.title ?? "Job posting" };
}

export default async function JobPostingDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const posting = await getPosting(id);
  if (!posting) notFound();

  return (
    <main id="main-content" className="mx-auto w-full max-w-2xl flex-1 px-6 py-10">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">{posting.title}</h1>
        {posting.location_city ? (
          <p className="mt-1 text-sm text-muted-foreground">
            {[posting.location_city, posting.location_country].filter(Boolean).join(", ")}
          </p>
        ) : null}
      </div>

      <p className="mt-4 whitespace-pre-wrap text-sm text-foreground">{posting.description}</p>

      {posting.source_url ? (
        <a
          href={posting.source_url}
          target="_blank"
          rel="noopener noreferrer nofollow"
          className="mt-4 inline-block text-sm font-medium text-primary"
        >
          View original posting ↗
        </a>
      ) : null}

      <div className="mt-8">
        <VerificationPanel subjectType="job_posting" subjectId={posting.id} />
      </div>
    </main>
  );
}
