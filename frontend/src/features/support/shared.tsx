import { useCallback, useEffect, useState, type ReactNode } from 'react'
import type { TFunction } from 'i18next'
import { useTranslation } from 'react-i18next'
import { ApiError } from '../../api/client'
import { errorMessage } from '../../api/errors'
import './shared.css'

// Small helpers shared by the support, facilitator, applications and training screens.

export type Loaded<T> = { phase: 'loading' } | { phase: 'error'; error: unknown } | { phase: 'ready'; data: T }
type Loader<T> = (options: { signal: AbortSignal }) => Promise<T>

/** Loads on mount / when `load` changes (wrap in useCallback) and on reload(). */
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

  // After reload() the previous data stays on screen until the new copy arrives.
  const state: Loaded<T> =
    settled && settled.load === load && (settled.attempt === attempt || settled.out.phase === 'ready')
      ? settled.out
      : { phase: 'loading' }
  const reload = useCallback(() => setAttempt((n) => n + 1), [])
  const setData = useCallback(
    (data: T) => setSettled({ load, attempt, out: { phase: 'ready', data } }),
    [load, attempt],
  )
  return { state, reload, setData }
}

/** Server error codes with our own wording first, then the shared messages. */
export function errText(err: unknown, t: TFunction): string {
  if (err instanceof ApiError && err.detail) {
    const own = t(`support.err.${err.detail}`, { defaultValue: '' })
    if (own) return own
  }
  return errorMessage(err, t)
}

/** Shows loading / error+retry, or the children once data is ready. */
export function LoadGate<T>({
  state,
  reload,
  children,
}: {
  state: Loaded<T>
  reload: () => void
  children: (data: T) => ReactNode
}) {
  const { t } = useTranslation()
  if (state.phase === 'loading') return <p role="status">{t('common.loading')}</p>
  if (state.phase === 'error')
    return (
      <div role="alert" className="sp-box">
        <p className="error">{errText(state.error, t)}</p>
        <button type="button" className="btn" onClick={reload}>
          {t('common.retry')}
        </button>
      </div>
    )
  return <>{children(state.data)}</>
}

/** Runs an async action with busy and error state. */
export function useAction() {
  const { t } = useTranslation()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const run = useCallback(
    async <R,>(fn: () => Promise<R>): Promise<R | undefined> => {
      setBusy(true)
      setError(null)
      try {
        return await fn()
      } catch (e) {
        setError(errText(e, t))
        return undefined
      } finally {
        setBusy(false)
      }
    },
    [t],
  )
  const clear = useCallback(() => setError(null), [])
  return { run, busy, error, clear }
}

export function ErrorLine({ message }: { message: string | null }) {
  return message ? (
    <p role="alert" className="error">
      {message}
    </p>
  ) : null
}

export function formatDateTime(iso: string | null | undefined, lang: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString(lang === 'ta' ? 'ta-IN' : 'en-IN', { dateStyle: 'medium', timeStyle: 'short' })
}

/** Only https links are rendered as links. */
export function safeHttps(url: string | null | undefined): string | null {
  if (!url) return null
  try {
    const u = new URL(url)
    return u.protocol === 'https:' ? u.href : null
  } catch {
    return null
  }
}
