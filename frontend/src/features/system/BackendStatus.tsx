import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { getHealth, type Health } from '../../api/health'

type State =
  | { phase: 'loading' }
  | { phase: 'done'; health: Health }
  | { phase: 'error' }

export function BackendStatus() {
  const { t } = useTranslation()
  const [state, setState] = useState<State>({ phase: 'loading' })
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    getHealth({ signal: controller.signal })
      .then((health) => setState({ phase: 'done', health }))
      .catch(() => {
        if (!controller.signal.aborted) setState({ phase: 'error' })
      })
    return () => controller.abort()
  }, [attempt])

  const retry = () => {
    setState({ phase: 'loading' })
    setAttempt((n) => n + 1)
  }

  let kind: 'loading' | 'ok' | 'degraded' | 'error'
  if (state.phase === 'loading') kind = 'loading'
  else if (state.phase === 'error') kind = 'error'
  else kind = state.health.status === 'ok' && state.health.db === 'ok' ? 'ok' : 'degraded'

  return (
    <section className={`status status--${kind}`} aria-labelledby="status-title">
      <h2 id="status-title">{t('status.title')}</h2>
      <p role="status" aria-live="polite">
        {t(`status.${kind}`)}
      </p>
      {state.phase === 'done' && (
        <p className="status__meta">{t('status.version', { version: state.health.version })}</p>
      )}
      {kind === 'error' && (
        <button type="button" className="btn" onClick={retry}>
          {t('status.retry')}
        </button>
      )}
    </section>
  )
}
