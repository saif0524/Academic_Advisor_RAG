/**
 * The single HTTP entry point for the frontend (proposed FC-new-rest-api).
 * Components never call `fetch` inline — everything goes through this client,
 * per the react-component skill.
 *
 * The FastAPI scaffold lives in src/server (see
 * docs/planning/2026-10-19-src-monorepo-structure.md §server): routers for chat
 * (FC22–24, FC27–28), courses (FC8–12), classes (FC13–14, FC20–21),
 * plans (FC1–7, FC25–26), degrees (FC15, FC18), students (FC1/7/16–17/19/36),
 * and audits (FC24). Endpoints are 501 {"error": ...} stubs until the
 * backend zones are wired — add typed helpers here as services come online,
 * e.g:
 *   export const getMyProfile = () => request<StudentProfile>('/students/me');
 * No auth headers: authentication is out of scope (FC36).
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE';
  body?: unknown;
  signal?: AbortSignal;
}

/**
 * Perform a request against the advisor API and return the parsed JSON body.
 * @throws {Error} on non-2xx responses — callers must render explicit error states
 */
export async function request<T = unknown>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, signal } = options;

  const response = await fetch(`${BASE_URL}${path}`, {
    method,
    signal,
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`Advisor API ${method} ${path} failed: HTTP ${response.status}`);
  }
  return (await response.json()) as T;
}