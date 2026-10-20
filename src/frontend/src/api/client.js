/**
 * The single HTTP entry point for the frontend (proposed FC-new-rest-api).
 * Components never call `fetch` inline — everything goes through this client,
 * per the react-component skill.
 *
 * The FastAPI app lands in src/agent/server (see
 * docs/2026-10-19-src-monorepo-structure.md §agent). No endpoints exist yet —
 * add typed helpers here as routers come online, e.g.
 *   export const getDegreeRequirements = () => request('/degrees/requirements');
 * No auth headers: authentication is out of scope (FC36).
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

/**
 * Perform a request against the advisor API and return the parsed JSON body.
 * @param {string} path API path starting with '/'
 * @param {{ method?: 'GET'|'POST'|'PATCH'|'DELETE', body?: unknown, signal?: AbortSignal }} [options]
 * @returns {Promise<unknown>}
 * @throws {Error} on non-2xx responses — callers must render explicit error states
 */
export async function request(path, options = {}) {
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
  return response.json();
}