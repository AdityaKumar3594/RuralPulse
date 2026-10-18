import { useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'
import { Status } from '../discover/Badges'
import { apiMessage } from '../discover/format'
import { useLoad } from '../discover/useLoad'
import { listPlans } from './api'
import '../discover/shared.css'

export function PathwayListPage() {
  const { t, i18n } = useTranslation()
  const lang = i18n.language
  const load = useCallback((o: { signal: AbortSignal }) => listPlans(lang, o), [lang])
  const { state, reload } = useLoad(load)

  return (
    <>
      <h1>{t('pathway.listTitle')}</h1>
      <p className="lead">{t('pathway.listIntro')}</p>
      {state.phase === 'loading' && <Status />}
      {state.phase === 'error' && <Status error={apiMessage(state.error, t)} onRetry={reload} />}
      {state.phase === 'ready' &&
        (state.data.length === 0 ? (
          <div>
            <p role="status">{t('pathway.empty')}</p>
            <div className="stack">
              <Link className="btn" to="/recommendations">
                {t('pathway.toSuggestions')}
              </Link>
              <Link className="btn btn--secondary" to="/careers">
                {t('pathway.toCareers')}
              </Link>
            </div>
          </div>
        ) : (
          <ul className="cards">
            {state.data.map((p) => {
              const done = p.steps.filter((s) => s.status === 'done').length
              const name = p.career.title ?? p.career.slug
              return (
                <li key={p.id} className="card">
                  <h2>{name}</h2>
                  <p>{t('pathway.progress', { done, total: p.steps.length })}</p>
                  <progress max={p.steps.length} value={done} aria-label={t('pathway.progress', { done, total: p.steps.length })} />
                  <p>
                    <Link className="btn btn--secondary" to={`/pathways/${encodeURIComponent(p.id)}`}>
                      {t('pathway.open')}
                      <span className="visually-hidden">: {name}</span>
                    </Link>
                  </p>
                </li>
              )
            })}
          </ul>
        ))}
    </>
  )
}
