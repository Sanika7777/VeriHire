/**
 * The access token lives in memory only, for the lifetime of the tab. It is
 * never written to localStorage/sessionStorage — a compromised page (XSS)
 * that reads storage should not walk away with a durable credential. The
 * refresh token never reaches JS at all; it's an HTTP-only cookie the
 * browser attaches automatically to the auth endpoints (see CLAUDE.md §2
 * auth client note, and PHASES.md Phase 2 DoD).
 */

let accessToken: string | null = null;

export function getAccessToken(): string | null {
  return accessToken;
}

export function setAccessToken(token: string | null): void {
  accessToken = token;
}
