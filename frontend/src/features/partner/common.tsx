import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { TFunction } from 'i18next'
import { ApiError } from '../../api/client'
import { errorMessage } from '../../api/errors'

export type Loaded<T> = { phase: 'loading' } | { phase: 'error'; error: unknown } | { phase: 'ready'; data: T }
type Loader<T> = (options: { signal: AbortSignal }) => Promise<T>

/** Loads when `load` changes (wrap in useCallback) and on reload(). */
export function useLoad<T>(load: Loader<T>) {
  const [attempt, setAttempt] = useState(0)
  const [settled, setSettled] = useState<{ load: Loader<T>; attempt: number; out: Loaded<T> } | null>(null)
  useEffect(() => {
    const controller = new AbortController()
    load({ signal: controller.signal }).then(
      (data) => setSettled({ load, attempt, out: { phase: 'ready', data } }),
      (error: unknown) => {
        if (!controller.signal.aborted) setSettled({ load, attempt, out: { phase: 'error', error } })
      },
    )
    return () => controller.abort()
  }, [load, attempt])
  const state: Loaded<T> =
    settled && settled.load === load && settled.attempt === attempt ? settled.out : { phase: 'loading' }
  const reload = useCallback(() => setAttempt((n) => n + 1), [])
  return { state, reload }
}

/** Translated message for an error; falls back to the generic message plus the server's code. */
export function errText(err: unknown, t: TFunction): string {
  if (err instanceof ApiError && err.kind === 'http' && err.detail) {
    const [code, arg] = err.detail.split(':')
    const key = `partner.errors.${code}`
    const text = t(key, { defaultValue: '', field: arg ?? '' })
    if (text) return text
    return `${errorMessage(err, t)} (${err.detail})`
  }
  return errorMessage(err, t)
}

export function LoadState({ state, onRetry }: { state: Loaded<unknown>; onRetry: () => void }) {
  const { t } = useTranslation()
  if (state.phase === 'loading') return <p role="status">{t('partner.loading')}</p>
  if (state.phase === 'error')
    return (
      <div role="alert">
        <p className="error">{errText(state.error, t)}</p>
        <button type="button" className="btn" onClick={onRetry}>
          {t('partner.retry')}
        </button>
      </div>
    )
  return null
}

export function Msg({ error, ok }: { error?: string | null; ok?: string | null }) {
  if (error)
    return (
      <p role="alert" className="error">
        {error}
      </p>
    )
  if (ok) return <p role="status" className="ptn-ok">{ok}</p>
  return null
}

export function formatDate(iso: string | null | undefined, lang: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString(lang === 'ta' ? 'ta-IN' : 'en-IN')
}
