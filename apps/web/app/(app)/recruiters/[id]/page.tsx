import type { components } from "@verihire/shared";
import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { VerdictBadge } from "@/components/verification/verdict-badge";
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
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">{recruiter.full_name}</h1>
          {recruiter.headline ? (
            <p className="mt-1 text-sm text-muted-foreground">{recruiter.headline}</p>
          ) : null}
        </div>
        <VerdictBadge band="unrated" />
      </div>

      <p className="mt-6 text-sm text-foreground">
        {recruiter.bio ?? "No bio has been added for this recruiter yet."}
      </p>

      {recruiter.linkedin_url ? (
        <a
          href={recruiter.linkedin_url}
          target="_blank"
          rel="noopener noreferrer nofollow"
          className="mt-6 inline-block text-sm font-medium text-primary"
        >
          View LinkedIn profile ↗
        </a>
      ) : null}

      <p className="mt-8 text-xs text-muted-foreground">
        This recruiter hasn&apos;t been verified yet — a full Trust Score breakdown lands in a
        later phase of this build.
      </p>
    </main>
  );
}
