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

  get needsSignIn(): boolean {
    return this.status === 401;
  }
}

type ApiErrorBody = {
  error?: { code?: string; message?: string; details?: Record<string, unknown> };
};

const CSRF_HEADER = "X-Mshikaki-Request";

/** The backend rejects any write without this header. See docs/standards.md. */
export async function apiFetch<T>(
  path: string,
  options: RequestInit & { json?: unknown } = {},
): Promise<T> {
  const { json, ...rest } = options;

  const init: RequestInit = {
    ...rest,
    credentials: "same-origin",
    headers: {
      [CSRF_HEADER]: "1",
      ...(json === undefined ? {} : { "Content-Type": "application/json" }),
      ...(rest.headers ?? {}),
    },
  };
  if (json !== undefined) {
    init.body = JSON.stringify(json);
  }

  const response = await fetch(`/api${path}`, init);

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

/** For the plain-text summary export, which is not JSON. */
export async function apiFetchText(path: string): Promise<string> {
  const response = await fetch(`/api${path}`, { credentials: "same-origin" });
  if (!response.ok) {
    throw new ApiError(response.status, "export.failed", "Could not load the export.", {});
  }
  return response.text();
}
