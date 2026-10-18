import { useRef, useState, type RefObject } from 'react'
import { useTranslation } from 'react-i18next'
import { ExternalLink, FreshnessChip } from '../features/discover/Badges'
import { explain, type Explanation, type ExplainRef } from '../features/discover/explain'
import { apiMessage } from '../features/discover/format'
import '../features/discover/shared.css'

type State =
  | { phase: 'idle' }
  | { phase: 'loading' }
  | { phase: 'error'; message: string }
  | { phase: 'ready'; data: Explanation }

interface Props {
  /** What to explain, exactly as the backend expects it (language is added from the UI language). */
  request: ExplainRef
  className?: string
}

/** "Explain in simple words": fetches an explanation and shows it with its sources and how it was written. */
export function ExplanationPanel({ request, className }: Props) {
  const { t, i18n } = useTranslation()
  const key = JSON.stringify(request) + i18n.language
  const [result, setResult] = useState<{ key: string; state: State }>({ key, state: { phase: 'idle' } })
  const latest = useRef(0)
  const heading = useRef<HTMLHeadingElement>(null)
  // A different request or language means any earlier answer no longer applies.
  const state: State = result.key === key ? result.state : { phase: 'idle' }

  const run = async () => {
    const mine = ++latest.current
    setResult({ key, state: { phase: 'loading' } })
    try {
      const data = await explain({ ...request, language: i18n.language === 'ta' ? 'ta' : 'en' })
      if (mine !== latest.current) return
      setResult({ key, state: { phase: 'ready', data } })
      setTimeout(() => heading.current?.focus(), 0)
    } catch (err) {
      if (mine !== latest.current) return
      setResult({ key, state: { phase: 'error', message: apiMessage(err, t) } })
    }
  }

  return (
    <div className={`explain${className ? ` ${className}` : ''}`}>
      {state.phase !== 'ready' && (
        <button type="button" className="btn btn--secondary btn--small" disabled={state.phase === 'loading'} onClick={() => void run()}>
          {t('discover.explainPanel.button')}
        </button>
      )}
      {state.phase === 'loading' && <p role="status">{t('discover.explainPanel.loading')}</p>}
      {state.phase === 'error' && (
        <div role="alert">
          <p className="error">{state.message}</p>
          <button type="button" className="btn" onClick={() => void run()}>
            {t('discover.explainPanel.retry')}
          </button>
        </div>
      )}
      {state.phase === 'ready' && <Result data={state.data} headingRef={heading} />}
    </div>
  )
}

function Result({ data, headingRef }: { data: Explanation; headingRef: RefObject<HTMLHeadingElement | null> }) {
  const { t } = useTranslation()
  const e = data.explanation
  const sources = data.sources.filter((s) => s.url)
  return (
    <section className="explain__body" aria-labelledby={`explain-${data.id}`}>
      <h3 id={`explain-${data.id}`} ref={headingRef} tabIndex={-1} className="explain__headline">
        {t('discover.explainPanel.title')}: {e.headline}
      </h3>
      <p className="explain__label">
        <span className="tag tag--info">
          {data.source === 'ai' ? t('discover.explainPanel.sourceAi') : t('discover.explainPanel.sourceTemplate')}
        </span>
      </p>
      <List title={t('discover.explainPanel.why')} items={e.why} />
      <List title={t('discover.explainPanel.requirements')} items={e.requirements} />
      {e.eligibility_status !== 'NOT_APPLICABLE' && (
        <>
          <h4>{t('discover.explainPanel.status')}</h4>
          <p>
            <strong>{t(`discover.explainPanel.statusValue.${e.eligibility_status}`)}</strong>
          </p>
        </>
      )}
      {e.freshness_note && (
        <>
          <h4>{t('discover.explainPanel.freshness')}</h4>
          <p>{e.freshness_note}</p>
        </>
      )}
      <List title={t('discover.explainPanel.missing')} items={e.missing_information} />
      {e.next_action && (
        <>
          <h4>{t('discover.explainPanel.next')}</h4>
          <p>{e.next_action}</p>
        </>
      )}
      {sources.length > 0 && (
        <>
          <h4>{t('discover.explainPanel.sources')}</h4>
          <ul className="link-list">
            {sources.map((s) => (
              <li key={s.url}>
                <ExternalLink href={s.url ?? null}>{s.title || s.url}</ExternalLink> <FreshnessChip value={s.freshness} />
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  )
}

function List({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null
  return (
    <>
      <h4>{title}</h4>
      <ul>
        {items.map((x, i) => (
          <li key={i}>{x}</li>
        ))}
      </ul>
    </>
  )
}
