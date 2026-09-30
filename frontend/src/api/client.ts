/**
 * The one place that talks to the API.
 *
 * Responsibilities: same-origin requests with cookies, a consistent error shape,
 * and a single place to add the CSRF header when cookie auth lands in Phase 1.
 */

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Record<string, unknown>;

  constructor(status: number, code: string, message: string, details: Record<string, unknown>) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

type ApiErrorBody = {
  error?: { code?: string; message?: string; details?: Record<string, unknown> };
};

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...init,
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      ...(init.headers ?? {}),
    },
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();
  const body = text ? (JSON.parse(text) as T & ApiErrorBody) : ({} as T & ApiErrorBody);

  if (!response.ok) {
    throw new ApiError(
      response.status,
      body.error?.code ?? `http.${response.status}`,
      body.error?.message ?? "The request failed.",
      body.error?.details ?? {},
    );
  }

  return body as T;
}
