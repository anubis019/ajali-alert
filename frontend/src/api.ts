/* ================================================================== */
/* Types                                                              */
/* ================================================================== */

export type IncidentType = {
  code: string;
  name: string;
  icon: string;
};

export type Topic = {
  id: string;
  title: string;
  steps: string[];
  warnings: string[];
};

export type IncidentHistoryEvent = {
  status: string;
  note?: string | null;
  created_at: string;
};

export type IncidentAssignment = {
  eta_minutes: number;
  status: string;
  responder: {
    name: string;
    responder_type: string;
  };
};

export type Incident = {
  id: string;
  incident_number: string;
  status: string;
  priority: number;
  casualty_count: number;
  description: string;
  latitude: number;
  longitude: number;
  location_description: string;
  landmark: string;
  created_at: string;
  updated_at: string;
  type?: IncidentType;
  /** Backend sometimes returns `history`, sometimes `status_history`. */
  history?: IncidentHistoryEvent[];
  status_history?: IncidentHistoryEvent[];
  assignments?: IncidentAssignment[];
  first_aid_suggestions: Topic[];
};

export type AuthUser = {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
};

export type TokenPair = {
  access_token: string;
  refresh_token: string;
};

/* ================================================================== */
/* Errors                                                             */
/* ================================================================== */

export class ApiError extends Error {
  status: number;
  detail?: unknown;

  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }

  /** True when the server says we need to log in again. */
  get isAuthError() {
    return this.status === 401 || this.status === 403;
  }
}

export class NetworkError extends Error {
  constructor(message = "Could not reach the server. Check your connection.") {
    super(message);
    this.name = "NetworkError";
  }
}

export class TimeoutError extends Error {
  constructor(message = "The request took too long. Try again.") {
    super(message);
    this.name = "TimeoutError";
  }
}

/* ================================================================== */
/* Config                                                             */
/* ================================================================== */

const API = (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000";
const DEFAULT_TIMEOUT_MS = 15_000;
const DEFAULT_RETRIES = 2;
const RETRY_BASE_DELAY_MS = 400;

/* ================================================================== */
/* Auth token store                                                   */
/* ================================================================== */

const TOKEN_KEY = "ajali_token";
const REFRESH_KEY = "ajali_refresh";
const USER_KEY = "ajali_user";

export const auth = {
  getToken: (): string | null => {
    try {
      return localStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },
  getRefresh: (): string | null => {
    try {
      return localStorage.getItem(REFRESH_KEY);
    } catch {
      return null;
    }
  },
  getUser: (): AuthUser | null => {
    try {
      const raw = localStorage.getItem(USER_KEY);
      return raw ? (JSON.parse(raw) as AuthUser) : null;
    } catch {
      return null;
    }
  },
  set: (tokens: TokenPair, user?: AuthUser) => {
    try {
      localStorage.setItem(TOKEN_KEY, tokens.access_token);
      localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
      if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));
    } catch {
      /* storage full or disabled — ignore */
    }
  },
  clear: () => {
    try {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(REFRESH_KEY);
      localStorage.removeItem(USER_KEY);
    } catch {
      /* ignore */
    }
  },
  isLoggedIn: (): boolean => Boolean(auth.getToken()),
};

/* ================================================================== */
/* Token refresh (single-flight)                                      */
/* ================================================================== */

let refreshPromise: Promise<boolean> | null = null;

async function refreshAccessToken(): Promise<boolean> {
  // Coalesce concurrent refresh attempts into one request
  if (refreshPromise) return refreshPromise;

  const refresh_token = auth.getRefresh();
  if (!refresh_token) return false;

  refreshPromise = (async () => {
    try {
      const res = await fetch(`${API}/api/v1/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token }),
      });
      if (!res.ok) {
        auth.clear();
        return false;
      }
      const data = (await res.json()) as TokenPair;
      auth.set(data);
      return true;
    } catch {
      auth.clear();
      return false;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

/* ================================================================== */
/* Core request                                                       */
/* ================================================================== */

export interface RequestOptions extends Omit<RequestInit, "body"> {
  /** JSON-serialisable body. Ignored if `rawBody` is provided. */
  body?: unknown;
  /** Raw body — FormData, Blob, URLSearchParams, etc. */
  rawBody?: BodyInit;
  /** Per-request timeout in milliseconds. */
  timeoutMs?: number;
  /** Number of automatic retries on network errors / 5xx. */
  retries?: number;
  /** Attach the current Bearer token (default: true). */
  auth?: boolean;
  /** AbortSignal to cancel from the caller. */
  signal?: AbortSignal;
}

async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const {
    body,
    rawBody,
    timeoutMs = DEFAULT_TIMEOUT_MS,
    retries = DEFAULT_RETRIES,
    auth: withAuth = true,
    signal: externalSignal,
    headers: extraHeaders,
    ...fetchInit
  } = opts;

  const url = path.startsWith("http") ? path : `${API}${path}`;
  let attempt = 0;

  while (true) {
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);

    // If the caller gave us a signal, chain it
    const onAbort = () => controller.abort();
    if (externalSignal) {
      if (externalSignal.aborted) controller.abort();
      else externalSignal.addEventListener("abort", onAbort);
    }

    const headers = new Headers(extraHeaders);
    if (!(rawBody instanceof FormData) && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
    if (withAuth) {
      const token = auth.getToken();
      if (token) headers.set("Authorization", `Bearer ${token}`);
    }

    let response: Response;
    try {
      response = await fetch(url, {
        ...fetchInit,
        headers,
        signal: controller.signal,
        body: rawBody ?? (body !== undefined ? JSON.stringify(body) : undefined),
      });
    } catch (err) {
      window.clearTimeout(timeoutId);
      externalSignal?.removeEventListener("abort", onAbort);

      const aborted = (err as { name?: string })?.name === "AbortError";
      // Caller cancelled — do not retry
      if (aborted && externalSignal?.aborted) {
        throw new NetworkError("Request cancelled.");
      }
      // Timeout — allow one retry
      if (aborted) {
        if (attempt < retries) {
          attempt++;
          await sleep(RETRY_BASE_DELAY_MS * 2 ** (attempt - 1));
          continue;
        }
        throw new TimeoutError();
      }
      // Network error
      if (attempt < retries) {
        attempt++;
        await sleep(RETRY_BASE_DELAY_MS * 2 ** (attempt - 1));
        continue;
      }
      throw new NetworkError();
    } finally {
      window.clearTimeout(timeoutId);
      externalSignal?.removeEventListener("abort", onAbort);
    }

    // 401: try to refresh once, then retry
    if (response.status === 401 && withAuth && auth.getRefresh()) {
      const refreshed = await refreshAccessToken();
      if (refreshed) {
        // Retry immediately without counting against attempts
        continue;
      }
    }

    // 5xx: retry with backoff
    if (response.status >= 500 && attempt < retries) {
      attempt++;
      await sleep(RETRY_BASE_DELAY_MS * 2 ** (attempt - 1));
      continue;
    }

    // Success — no body (204, 205, 304)
    if (response.status === 204 || response.status === 205 || response.status === 304) {
      return undefined as T;
    }

    const text = await response.text();
    let parsed: unknown = undefined;
    if (text) {
      try {
        parsed = JSON.parse(text);
      } catch {
        parsed = text;
      }
    }

    if (!response.ok) {
      const detail =
        (parsed && typeof parsed === "object" && "detail" in parsed
          ? (parsed as { detail: unknown }).detail
          : undefined) ?? parsed;
      const message =
        typeof detail === "string"
          ? detail
          : "Ajali Alert could not complete that request.";
      throw new ApiError(response.status, message, detail);
    }

    return parsed as T;
  }
}

function sleep(ms: number) {
  return new Promise<void>((resolve) => setTimeout(resolve, ms));
}

/* ================================================================== */
/* Public API                                                         */
/* ================================================================== */

/**
 * Drop-in replacement for the original `api()`. Same signature — accepts
 * a JSON body via `options.body`, returns the parsed response.
 */
export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  // Translate the old RequestInit-style call into our richer options
  const { body, ...rest } = options ?? {};
  let parsedBody: unknown = body;
  if (typeof body === "string") {
    try {
      parsedBody = JSON.parse(body);
    } catch {
      /* leave as-is; treat as raw */
    }
  }
  return request<T>(path, {
    ...rest,
    body: parsedBody,
  } as RequestOptions);
}

/** Rich client for new code that wants timeouts, retries, auth control. */
export const http = {
  get: <T>(path: string, opts?: RequestOptions) =>
    request<T>(path, { ...opts, method: "GET" }),
  post: <T>(path: string, body?: unknown, opts?: RequestOptions) =>
    request<T>(path, { ...opts, method: "POST", body }),
  patch: <T>(path: string, body?: unknown, opts?: RequestOptions) =>
    request<T>(path, { ...opts, method: "PATCH", body }),
  put: <T>(path: string, body?: unknown, opts?: RequestOptions) =>
    request<T>(path, { ...opts, method: "PUT", body }),
  del: <T>(path: string, opts?: RequestOptions) =>
    request<T>(path, { ...opts, method: "DELETE" }),
  /** For file uploads — takes a FormData directly. */
  upload: <T>(path: string, form: FormData, opts?: RequestOptions) =>
    request<T>(path, { ...opts, method: "POST", rawBody: form }),
  raw: request,
};

/* ================================================================== */
/* WebSocket URL                                                      */
/* ================================================================== */

export const socketUrl = (): string => {
  const base = API.replace(/^http/, "ws");
  const token = auth.getToken();
  // Some backends accept ?token=… for WS auth since headers aren't available
  return token ? `${base}/ws?token=${encodeURIComponent(token)}` : `${base}/ws`;
};

/* ================================================================== */
/* Convenience helpers used elsewhere                                 */
/* ================================================================== */

export const endpoints = {
  incidentTypes: () => http.get<IncidentType[]>("/api/v1/incident-types"),

  createIncident: (payload: {
    type_code: string;
    description: string;
    casualty_count: number;
    latitude: number;
    longitude: number;
    location_description: string;
    landmark?: string;
  }) => http.post<Incident>("/api/v1/incidents", payload, { auth: false }),

  getIncident: (id: string) => http.get<Incident>(`/api/v1/incidents/${id}`),

  updateIncidentStatus: (id: string, status: string, note?: string) =>
    http.patch<Incident>(`/api/v1/incidents/${id}/status`, { status, note }),

  askFirstAid: (query: string, incident_id?: string) =>
    http.post<Topic[]>("/api/v1/first-aid/ask", { query, incident_id }, { auth: false }),

  login: (email: string, password: string) =>
    http.post<TokenPair>("/api/v1/auth/login", { email, password }, { auth: false }),

  register: (email: string, password: string) =>
    http.post<TokenPair>("/api/v1/auth/register", { email, password }, { auth: false }),

  me: () => http.get<AuthUser>("/api/v1/auth/me"),

  logout: (refresh_token: string) =>
    http.post<void>("/api/v1/auth/logout", { refresh_token }),
};

/* ================================================================== */
/* Exported API base (in case you need it)                            */
/* ================================================================== */

export { API };
