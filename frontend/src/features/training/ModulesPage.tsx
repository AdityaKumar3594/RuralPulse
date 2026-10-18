import { useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'
import { LoadGate, useLoad } from '../support/shared'
import { listModules } from './api'
import { priceText } from './price'

export function ModulesPage() {
  const { t } = useTranslation()
  const load = useCallback((o: { signal: AbortSignal }) => listModules(o), [])
  const { state, reload } = useLoad(load)
  return (
    <>
      <h1>{t('training.title')}</h1>
      <p className="lead">{t('training.intro')}</p>
      <LoadGate state={state} reload={reload}>
        {(list) =>
          list.length === 0 ? (
            <p role="status">{t('training.empty')}</p>
          ) : (
            <ul className="sp-list">
              {list.map((m) => (
                <li key={m.id} className="sp-card">
                  <h2>{m.title}</h2>
                  <p>{m.description}</p>
                  <p className="muted">
                    {t(`training.language.${m.language}`, { defaultValue: m.language })} · {priceText(t, m)}
                    {m.enrolled ? ` · ${t('training.enrolledTag')}` : ''}
                  </p>
                  <Link className="btn btn--secondary" to={`/modules/${encodeURIComponent(m.id)}`}>
                    {t('training.open')}
                    <span className="visually-hidden">: {m.title}</span>
                  </Link>
                </li>
              ))}
            </ul>
          )
        }
      </LoadGate>
    </>
  )
}
