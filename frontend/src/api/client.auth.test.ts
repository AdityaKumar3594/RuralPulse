import { describe, expect, it, vi } from 'vitest'
import { ApiError, apiGet, apiPost, configureAuth } from './client'

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status })

describe('apiPost / auth', () => {
  it('sends a JSON body and the bearer token', async () => {
    configureAuth(() => 'tok', () => {})
    const fetchMock = vi.fn().mockResolvedValue(json({ ok: 1 }))
    vi.stubGlobal('fetch', fetchMock)
    await apiPost('/x', { a: 1 })
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(init.method).toBe('POST')
    expect(init.body).toBe('{"a":1}')
    const headers = init.headers as Record<string, string>
    expect(headers.Authorization).toBe('Bearer tok')
    expect(headers['Content-Type']).toBe('application/json')
    configureAuth(() => null, () => {})
  })

  it('never retries a POST, even on 503 (it could record an answer twice)', async () => {
    const fetchMock = vi.fn().mockResolvedValue(json({}, 503))
    vi.stubGlobal('fetch', fetchMock)
    await expect(apiPost('/x', {}, { backoffMs: 1 })).rejects.toBeInstanceOf(ApiError)
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('exposes the server error code as `detail`', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json({ detail: 'account_locked' }, 429)))
    const err: unknown = await apiPost('/x', {}).catch((e) => e)
    expect(err).toMatchObject({ kind: 'http', status: 429, detail: 'account_locked' })
  })

  it('handles error bodies that are not JSON and 204 responses', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('<html>', { status: 500 })))
    const err: unknown = await apiGet('/x', { retries: 0 }).catch((e) => e)
    expect(err).toMatchObject({ kind: 'http', detail: null })
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 204 })))
    await expect(apiPost('/x')).resolves.toBeUndefined()
  })

  it('calls the unauthorized handler on 401 only when a token was sent', async () => {
    const onUnauthorized = vi.fn()
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json({ detail: 'x' }, 401)))
    configureAuth(() => null, onUnauthorized)
    await apiPost('/auth/login', {}).catch(() => {})
    expect(onUnauthorized).not.toHaveBeenCalled() // a wrong PIN at login is not an expired session
    configureAuth(() => 'tok', onUnauthorized)
    await apiGet('/me', { retries: 0 }).catch(() => {})
    expect(onUnauthorized).toHaveBeenCalledOnce()
    configureAuth(() => null, () => {})
  })
})
