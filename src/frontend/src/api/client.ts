/**
 * The single HTTP entry point for the frontend (proposed FC-new-rest-api).
 * Components never call `fetch` inline — everything goes through this client,
 * per the react-component skill.
 *
 * The FastAPI app lives in src/server (routers for chat FC22–24/27–28,
 * courses FC8–12, classes FC13–14/20–21, plans FC1–7/25–26, degrees FC15/FC18,
 * students FC1/7/16–17/19/36, audits FC24). Non-2xx responses arrive as the
 * shared `{"error": {...}}` envelope — surfaced as a typed ApiError so
 * callers render explicit states (grounded-UI rule, no fabricated filler).
 * No auth headers: authentication is out of scope (FC36); the server's
 * pre-auth fallback identity drives the demo student.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE';
  body?: unknown;
  signal?: AbortSignal;
}

/** Envelope-shaped failure from the advisor API (server/errors.py). */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(path: string, method: string, status: number, code: string, message: string) {
    super(`Advisor API ${method} ${path} failed (HTTP ${status}, ${code}): ${message}`);
    this.status = status;
    this.code = code;
  }
}

interface ErrorEnvelope {
  error?: { code?: string; message?: string; details?: string[] };
}

/**
 * Perform a request against the advisor API and return the parsed JSON body.
 * @throws {ApiError} on non-2xx responses — callers must render explicit error states
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
    let errorBody: ErrorEnvelope = {};
    try {
      errorBody = (await response.json()) as ErrorEnvelope;
    } catch {
      /* non-JSON error body — fall through to the generic message */
    }
    throw new ApiError(
      path,
      method,
      response.status,
      errorBody.error?.code ?? 'error',
      errorBody.error?.message ?? `HTTP ${response.status}`,
    );
  }
  return (await response.json()) as T;
}