import { SiteFooter } from "@/components/layout/site-footer";
import { SiteHeader } from "@/components/layout/site-header";
import { hasServerSession } from "@/lib/auth/get-server-session";

export default async function MarketingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const likelyAuthenticated = await hasServerSession();

  return (
    <div className="flex min-h-full flex-1 flex-col">
      <SiteHeader likelyAuthenticated={likelyAuthenticated} />
      {children}
      <SiteFooter />
    </div>
  );
}
