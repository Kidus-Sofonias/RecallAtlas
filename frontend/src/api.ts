const BASE = (import.meta.env.VITE_API_BASE || '').replace(/\/+$/, '');

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

function errorMessage(payload: unknown, status: number): string {
  if (payload && typeof payload === 'object') {
    const detail = 'detail' in payload ? payload.detail : undefined;
    if (typeof detail === 'string') return detail;
    if (detail && typeof detail === 'object' && 'message' in detail && typeof detail.message === 'string') {
      return detail.message;
    }
    if ('message' in payload && typeof payload.message === 'string') return payload.message;
  }

  if (status === 401) return 'Your session has expired. Sign in again to continue.';
  if (status === 403) return 'You do not have permission to perform this action.';
  if (status === 404) return 'The requested item could not be found.';
  return `The request could not be completed (${status}).`;
}

function csrfCookie(): string {
  const entry = document.cookie.split('; ').find((part) => part.startsWith('ra_csrf='));
  return entry ? decodeURIComponent(entry.slice('ra_csrf='.length)) : '';
}

async function csrfToken(): Promise<string> {
  const existing = csrfCookie();
  if (existing) return existing;

  const response = await fetch(`${BASE}/api/v1/auth/csrf`, { credentials: 'include' });
  if (!response.ok) throw new ApiError('Could not initialize request protection. Try again.', response.status);
  const payload: unknown = await response.json();
  if (!payload || typeof payload !== 'object' || !('csrf_token' in payload) || typeof payload.csrf_token !== 'string') {
    throw new Error('The API did not return a valid request-protection token.');
  }
  return payload.csrf_token;
}

export async function api<T = unknown>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  const method = (options.method || 'GET').toUpperCase();
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    headers.set('X-CSRF-Token', await csrfToken());
  }
  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, { ...options, headers, credentials: 'include' });
  } catch (reason) {
    if (options.signal?.aborted) throw reason;
    throw new Error('Could not reach Recall Atlas. Check that the API is running and try again.');
  }

  const contentType = response.headers.get('content-type') || '';
  const payload: unknown = contentType.includes('application/json')
    ? await response.json().catch(() => undefined)
    : await response.text().catch(() => '');

  if (!response.ok) throw new ApiError(errorMessage(payload, response.status), response.status);
  if (response.status === 204 || payload === '') return undefined as T;
  return payload as T;
}
