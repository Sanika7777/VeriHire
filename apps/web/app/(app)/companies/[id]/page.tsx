import type { components } from "@verihire/shared";
import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { ClaimCompanyCard } from "@/components/companies/claim-company-card";
import { ReviewComposer } from "@/components/reviews/review-composer";
import { ReviewList } from "@/components/reviews/review-list";
import { VerificationPanel } from "@/components/verification/verification-panel";
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
      <div>
        <h1 className="text-2xl font-semibold text-foreground">{company.name}</h1>
        {company.domain ? (
          <p className="mt-1 text-sm text-muted-foreground">{company.domain}</p>
        ) : null}
      </div>

      <p className="mt-4 text-sm text-foreground">
        {company.description ?? "No description has been added for this company yet."}
      </p>

      <dl className="mt-6 grid grid-cols-2 gap-4 text-sm">
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

      <div className="mt-6">
        <ClaimCompanyCard companyId={company.id} />
      </div>

      <div className="mt-8">
        <VerificationPanel subjectType="company" subjectId={company.id} />
      </div>

      <div className="mt-8">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-foreground">Reviews</h2>
          <ReviewComposer subjectType="company" subjectId={company.id} />
        </div>
        <ReviewList subjectType="company" subjectId={company.id} />
      </div>
    </main>
  );
}
