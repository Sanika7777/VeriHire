import type { components } from "@verihire/shared";

import { StatTile } from "@/components/ui/stat-tile";
import { serverFetch } from "@/lib/api-client/server-fetch";

type PublicStats = components["schemas"]["PublicStats"];

export async function HomeStats() {
  const stats = await serverFetch<PublicStats>("/api/v1/stats");
  if (!stats) return null;

  return (
    <section className="mx-auto grid w-full max-w-4xl grid-cols-2 gap-4 px-6 py-12 sm:grid-cols-4">
      <StatTile label="Companies tracked" value={stats.companies_verified.toLocaleString()} />
      <StatTile label="Recruiters tracked" value={stats.recruiters_tracked.toLocaleString()} />
      <StatTile label="Scams confirmed" value={stats.scams_confirmed.toLocaleString()} />
      <StatTile label="Community reviews" value={stats.community_reviews.toLocaleString()} />
    </section>
  );
}
