import { useCallback, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'
import { listCareers } from './api'
import { Status } from './Badges'
import { apiMessage, enumText } from './format'
import { useLoad } from './useLoad'
import './shared.css'

const FAMILIES = [
  'agriculture', 'skilled_trades', 'health_care', 'education', 'creative_crafts', 'public_service',
  'business', 'technology', 'hospitality', 'transport_logistics',
]

export function CareersPage() {
  const { t, i18n } = useTranslation()
  const [family, setFamily] = useState('')
  const lang = i18n.language
  const load = useCallback(
    (o: { signal: AbortSignal }) => listCareers(family || undefined, lang, o),
    [family, lang],
  )
  const { state, reload } = useLoad(load)

  return (
    <>
      <h1>{t('discover.careers.title')}</h1>
      <p className="lead">{t('discover.careers.intro')}</p>
      <div className="field filters">
        <label htmlFor="c-family">{t('discover.careers.familyLabel')}</label>
        <select id="c-family" value={family} onChange={(e) => setFamily(e.target.value)}>
          <option value="">{t('discover.careers.familyAll')}</option>
          {FAMILIES.map((f) => (
            <option key={f} value={f}>{t(`discover.family.${f}`)}</option>
          ))}
        </select>
      </div>
      {state.phase === 'loading' && <Status />}
      {state.phase === 'error' && <Status error={apiMessage(state.error, t)} onRetry={reload} />}
      {state.phase === 'ready' &&
        (state.data.length === 0 ? (
          <p role="status">{t('discover.careers.empty')}</p>
        ) : (
          <>
            <p role="status">{t('discover.careers.count', { count: state.data.length })}</p>
            <ul className="cards">
              {state.data.map((c) => (
                <li key={c.slug} className="card">
                  <h2>{c.title ?? c.slug}</h2>
                  <p className="muted">{enumText(t, 'discover.family', c.family)}</p>
                  <Link className="btn btn--secondary" to={`/careers/${encodeURIComponent(c.slug)}`}>
                    {t('discover.careers.view')}
                    <span className="visually-hidden">: {c.title ?? c.slug}</span>
                  </Link>
                </li>
              ))}
            </ul>
          </>
        ))}
    </>
  )
}
