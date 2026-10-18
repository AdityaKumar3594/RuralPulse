import { useTranslation } from 'react-i18next'
import { formatDateTime } from '../support/shared'
import type { Application } from './types'

/** Plain words for who said what. Only a confirmed status is ever shown as fact. */
export function ExternalStatusBlock({ app, audience }: { app: Application; audience: 'student' | 'facilitator' }) {
  const { t, i18n } = useTranslation()
  const status = t(`applications.external.${app.external_status}`, { defaultValue: app.external_status })
  const source = app.external_status_source
    ? t(`applications.source.${app.external_status_source}`, { defaultValue: app.external_status_source })
    : ''
  const when = formatDateTime(app.external_status_at, i18n.language)

  return (
    <section className="sp-box" aria-labelledby={`ext-${app.id}`}>
      <h3 id={`ext-${app.id}`}>{t('applications.external.title')}</h3>
      {app.external_confirmed ? (
        <>
          <p>
            <span className="sp-tag sp-tag--ok">
              <span aria-hidden="true">✓ </span>
              {t('applications.external.confirmedTag')}
            </span>
          </p>
          <p>
            <strong>{status}</strong>
          </p>
          <p className="muted">
            {t('applications.external.confirmedBy', { source })}
            {when ? ` · ${when}` : ''}
          </p>
          {app.external_status_note && <p>{t('applications.external.note', { note: app.external_status_note })}</p>}
        </>
      ) : (
        <>
          <p>
            <span className="sp-tag sp-tag--warn">
              <span aria-hidden="true">? </span>
              {t('applications.external.notConfirmed')}
            </span>
          </p>
          {app.external_status !== 'unknown' && app.external_status_source === 'student_reported' ? (
            <p>
              {audience === 'student'
                ? t('applications.external.youSaid', { status })
                : t('applications.external.studentSaid', { status })}
            </p>
          ) : (
            <p className="muted">{t('applications.external.nothingYet')}</p>
          )}
        </>
      )}
    </section>
  )
}
