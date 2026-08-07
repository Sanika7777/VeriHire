import "server-only";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** Fetch helper for Server Components hitting public (unauthenticated) read
 * endpoints. Returns null on a 404 so pages can call Next's notFound(). */
export async function serverFetch<T>(path: string): Promise<T | null> {
  const response = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store" });
  if (response.status === 404) return null;
  if (!response.ok) {
    throw new Error(`Request to ${path} failed with status ${response.status}`);
  }
  return (await response.json()) as T;
}
