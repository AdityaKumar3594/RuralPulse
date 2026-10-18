export type ApiErrorKind = 'timeout' | 'network' | 'http' | 'parse'

export class ApiError extends Error {
  readonly kind: ApiErrorKind
  readonly status: number | null
  /** Machine-readable error code from the server's `{"detail": "..."}` body, if any. */
  readonly detail: string | null

  constructor(
    kind: ApiErrorKind,
    message: string,
    status: number | null = null,
    detail: string | null = null,
  ) {
    super(message)
    this.name = 'ApiError'
    this.kind = kind
    this.status = status
    this.detail = detail
  }
}

export interface ApiGetOptions {
  timeoutMs?: number
  retries?: number
  /** Base backoff between retries; grows linearly per attempt. */
  backoffMs?: number
  signal?: AbortSignal
}

export interface ApiRequestOptions extends ApiGetOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  body?: unknown
}

let tokenProvider: () => string | null = () => null
let onUnauthorized: () => void = () => {}

/** The auth layer registers how to read the token and what to do when the server rejects it. */
export function configureAuth(provider: () => string | null, unauthorizedHandler: () => void) {
  tokenProvider = provider
  onUnauthorized = unauthorizedHandler
}

const BASE_URL: string = import.meta.env.VITE_API_BASE_URL || '/api'

function isRetryable(err: ApiError): boolean {
  return err.kind === 'network' || err.kind === 'timeout' || (err.kind === 'http' && (err.status ?? 0) >= 500)
}

function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve) => {
    const t = setTimeout(resolve, ms)
    signal?.addEventListener(
      'abort',
      () => {
        clearTimeout(t)
        resolve()
      },
      { once: true },
    )
  })
}

async function attempt<T>(
  url: string,
  timeoutMs: number,
  external: AbortSignal | undefined,
  method: string,
  body: unknown,
): Promise<T> {
  const controller = new AbortController()
  let timedOut = false
  const timer = setTimeout(() => {
    timedOut = true
    controller.abort()
  }, timeoutMs)
  const onExternalAbort = () => controller.abort()
  external?.addEventListener('abort', onExternalAbort, { once: true })
  if (external?.aborted) controller.abort()

  try {
    let res: Response
    try {
      const token = tokenProvider()
      const headers: Record<string, string> = { Accept: 'application/json' }
      if (body !== undefined) headers['Content-Type'] = 'application/json'
      if (token) headers.Authorization = `Bearer ${token}`
      res = await fetch(url, {
        method,
        signal: controller.signal,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
      })
    } catch {
      if (timedOut) throw new ApiError('timeout', `Request timed out after ${timeoutMs}ms`)
      throw new ApiError('network', external?.aborted ? 'Request aborted' : 'Network error')
    }
    if (!res.ok) {
      let detail: string | null = null
      try {
        const data: unknown = await res.json()
        const d = (data as { detail?: unknown } | null)?.detail
        if (typeof d === 'string') detail = d
      } catch {
        // error body was not JSON; the status code is enough
      }
      if (res.status === 401 && tokenProvider()) onUnauthorized()
      throw new ApiError('http', `HTTP ${res.status}`, res.status, detail)
    }
    if (res.status === 204) return undefined as T
    try {
      return (await res.json()) as T
    } catch {
      if (timedOut) throw new ApiError('timeout', `Request timed out after ${timeoutMs}ms`)
      throw new ApiError('parse', 'Invalid JSON response', res.status)
    }
  } finally {
    clearTimeout(timer)
    external?.removeEventListener('abort', onExternalAbort)
  }
}

export async function apiRequest<T>(
  path: string,
  { method = 'GET', body, timeoutMs = 8000, retries, backoffMs = 300, signal }: ApiRequestOptions = {},
): Promise<T> {
  const url = `${BASE_URL.replace(/\/+$/, '')}/${path.replace(/^\/+/, '')}`
  // Only GETs are retried automatically: repeating a POST could record an answer twice.
  const maxRetries = retries ?? (method === 'GET' ? 1 : 0)
  for (let i = 0; ; i++) {
    try {
      return await attempt<T>(url, timeoutMs, signal, method, body)
    } catch (e) {
      const err = e instanceof ApiError ? e : new ApiError('network', 'Network error')
      if (signal?.aborted || i >= maxRetries || !isRetryable(err)) throw err
      await sleep(backoffMs * (i + 1), signal)
    }
  }
}

export function apiGet<T>(path: string, options: ApiGetOptions = {}): Promise<T> {
  return apiRequest<T>(path, options)
}

export function apiPost<T>(path: string, body?: unknown, options: ApiGetOptions = {}): Promise<T> {
  return apiRequest<T>(path, { ...options, method: 'POST', body })
}

export function apiPut<T>(path: string, body: unknown, options: ApiGetOptions = {}): Promise<T> {
  return apiRequest<T>(path, { ...options, method: 'PUT', body })
}
