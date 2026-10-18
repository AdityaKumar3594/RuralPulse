import { useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'
import { LoadGate, useLoad } from '../support/shared'
import { listApplications } from './api'

export function ApplicationsPage() {
  const { t, i18n } = useTranslation()
  const lang = i18n.language
  const load = useCallback((o: { signal: AbortSignal }) => listApplications(lang, o), [lang])
  const { state, reload } = useLoad(load)
  return (
    <>
      <h1>{t('applications.title')}</h1>
      <p className="lead">{t('applications.intro')}</p>
      <LoadGate state={state} reload={reload}>
        {(list) =>
          list.length === 0 ? (
            <div>
              <p role="status">{t('applications.empty')}</p>
              <Link className="btn" to="/search">
                {t('applications.findOpportunities')}
              </Link>
            </div>
          ) : (
            <ul className="sp-list">
              {list.map((a) => {
                const name = a.opportunity.title ?? a.opportunity.slug
                return (
                  <li key={a.id} className="sp-card">
                    <h2>{name}</h2>
                    <p>
                      <span className="sp-tag sp-tag--info">{t(`applications.status.${a.internal_status}`)}</span>{' '}
                      <span className={a.external_confirmed ? 'sp-tag sp-tag--ok' : 'sp-tag sp-tag--warn'}>
                        {a.external_confirmed
                          ? t('applications.list.confirmed', {
                              status: t(`applications.external.${a.external_status}`),
                            })
                          : t('applications.external.notConfirmed')}
                      </span>
                    </p>
                    <Link className="btn btn--secondary" to={`/applications/${encodeURIComponent(a.id)}`}>
                      {t('applications.list.open')}
                      <span className="visually-hidden">: {name}</span>
                    </Link>
                  </li>
                )
              })}
            </ul>
          )
        }
      </LoadGate>
    </>
  )
}
