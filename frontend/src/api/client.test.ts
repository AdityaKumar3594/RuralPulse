import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, apiGet } from './client'

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

afterEach(() => vi.unstubAllGlobals())

describe('apiGet', () => {
  it('throws ApiError kind timeout when fetch hangs', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        (_url: string, init: RequestInit) =>
          new Promise((_res, rej) => {
            init.signal?.addEventListener('abort', () => rej(new DOMException('aborted', 'AbortError')))
          }),
      ),
    )
    const err = (await apiGet('/health', { timeoutMs: 10, retries: 0 }).catch((e) => e)) as ApiError
    expect(err).toBeInstanceOf(ApiError)
    expect(err.kind).toBe('timeout')
  })

  it('retries on 503 then succeeds', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(json({}, 503)).mockResolvedValueOnce(json({ ok: 1 }))
    vi.stubGlobal('fetch', fetchMock)
    await expect(apiGet('/x', { backoffMs: 1 })).resolves.toEqual({ ok: 1 })
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('does not retry on 404', async () => {
    const fetchMock = vi.fn().mockResolvedValue(json({}, 404))
    vi.stubGlobal('fetch', fetchMock)
    const err: unknown = await apiGet('/x', { backoffMs: 1 }).catch((e) => e)
    expect(err).toMatchObject({ kind: 'http', status: 404 })
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('maps network failure and bad JSON', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('fail')))
    expect(await apiGet('/x', { retries: 0 }).catch((e) => e.kind)).toBe('network')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('nope', { status: 200 })))
    expect(await apiGet('/x', { retries: 0 }).catch((e) => e.kind)).toBe('parse')
  })
})
