import { SiteHeader } from "@/components/layout/site-header";
import { hasServerSession } from "@/lib/auth/get-server-session";

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const likelyAuthenticated = await hasServerSession();

  return (
    <div className="flex min-h-full flex-1 flex-col">
      <SiteHeader likelyAuthenticated={likelyAuthenticated} />
      {children}
    </div>
  );
}
