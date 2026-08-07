import type { components } from "@verihire/shared";
import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { VerdictBadge } from "@/components/verification/verdict-badge";
import { serverFetch } from "@/lib/api-client/server-fetch";

type CompanyRead = components["schemas"]["CompanyRead"];

async function getCompany(id: string): Promise<CompanyRead | null> {
  return serverFetch<CompanyRead>(`/api/v1/companies/${id}`);
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  const company = await getCompany(id);
  return { title: company?.name ?? "Company" };
}

export default async function CompanyDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const company = await getCompany(id);
  if (!company) notFound();

  return (
    <main id="main-content" className="mx-auto w-full max-w-2xl flex-1 px-6 py-10">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">{company.name}</h1>
          {company.domain ? (
            <p className="mt-1 text-sm text-muted-foreground">{company.domain}</p>
          ) : null}
        </div>
        <VerdictBadge band="unrated" />
      </div>

      <p className="mt-6 text-sm text-foreground">
        {company.description ?? "No description has been added for this company yet."}
      </p>

      <dl className="mt-8 grid grid-cols-2 gap-4 text-sm">
        {company.industry ? (
          <div>
            <dt className="text-muted-foreground">Industry</dt>
            <dd className="text-foreground">{company.industry}</dd>
          </div>
        ) : null}
        {company.hq_city ? (
          <div>
            <dt className="text-muted-foreground">Headquarters</dt>
            <dd className="text-foreground">
              {[company.hq_city, company.hq_country].filter(Boolean).join(", ")}
            </dd>
          </div>
        ) : null}
        {company.employee_count_range ? (
          <div>
            <dt className="text-muted-foreground">Employees</dt>
            <dd className="text-foreground">{company.employee_count_range}</dd>
          </div>
        ) : null}
        {company.founded_year ? (
          <div>
            <dt className="text-muted-foreground">Founded</dt>
            <dd className="text-foreground">{company.founded_year}</dd>
          </div>
        ) : null}
      </dl>

      <p className="mt-8 text-xs text-muted-foreground">
        This company hasn&apos;t been verified yet — a full Trust Score breakdown lands in a
        later phase of this build.
      </p>
    </main>
  );
}
