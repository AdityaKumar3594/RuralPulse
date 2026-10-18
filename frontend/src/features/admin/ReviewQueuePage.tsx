import { useCallback, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'
import { listProviders, listSubmissions } from './api'
import { formatDate, LoadState, useLoad } from './common'
import { SUBMISSION_STATUSES } from './types'

function titleOf(payload: Record<string, unknown>): string {
  const t = payload.title
  if (typeof t === 'object' && t !== null && 'en' in t) return String((t as { en: unknown }).en)
  return ''
}

export function ReviewQueuePage() {
  const { t, i18n } = useTranslation()
  const [status, setStatus] = useState('submitted')
  const load = useCallback(
    async (o: { signal: AbortSignal }) => {
      const [subs, providers] = await Promise.all([listSubmissions(status, o), listProviders(undefined, o)])
      return { subs, providers }
    },
    [status],
  )
  const { state, reload } = useLoad(load)

  return (
    <section aria-labelledby="adm-rq-h">
      <h2 id="adm-rq-h">{t('admin.review.title')}</h2>
      <div className="field adm-form">
        <label htmlFor="adm-rq-status">{t('admin.review.filter')}</label>
        <select id="adm-rq-status" value={status} onChange={(e) => setStatus(e.target.value)}>
          {SUBMISSION_STATUSES.map((s) => (
            <option key={s} value={s}>
              {t(`admin.submissionStatus.${s}`)}
            </option>
          ))}
        </select>
      </div>
      <LoadState state={state} onRetry={reload} />
      {state.phase === 'ready' &&
        (state.data.subs.length === 0 ? (
          <p role="status">{t('admin.review.empty')}</p>
        ) : (
          <ul className="adm-list">
            {state.data.subs.map((s) => {
              const p = state.data.providers.find((x) => x.id === s.provider_id)
              return (
                <li key={s.id} className="adm-card">
                  <h3>{titleOf(s.payload) || s.id}</h3>
                  <p>
                    <span className="badge">{t(`admin.submissionStatus.${s.status}`, { defaultValue: s.status })}</span>{' '}
                    {p?.name ?? ''}
                  </p>
                  <p className="muted">{t('admin.review.updated', { date: formatDate(s.updated_at, i18n.language) })}</p>
                  <Link className="btn" to={`/admin/review/${s.id}?status=${status}`}>
                    {t('admin.review.open')}
                  </Link>
                </li>
              )
            })}
          </ul>
        ))}
    </section>
  )
}
