import "server-only";

import { cookies } from "next/headers";

const REFRESH_COOKIE_NAME = "verihire_refresh_token";

/**
 * Whether this request is likely from a logged-in visitor, for a Server
 * Component to pick the right SSR shell before any client JS runs.
 *
 * This deliberately does NOT call the API's refresh endpoint: that endpoint
 * rotates the refresh token, and a Server Component has no way to forward
 * the resulting Set-Cookie back to the browser (only Server Actions and
 * Route Handlers can set cookies). Calling it here would rotate the token
 * server-side while the browser keeps presenting the now-revoked one on its
 * next request — tripping reuse detection and locking the user out.
 *
 * The client API client (lib/api-client/client.ts) performs the real,
 * authoritative refresh transparently on the first 401 it sees.
 */
export async function hasServerSession(): Promise<boolean> {
  const cookieStore = await cookies();
  return cookieStore.has(REFRESH_COOKIE_NAME);
}
