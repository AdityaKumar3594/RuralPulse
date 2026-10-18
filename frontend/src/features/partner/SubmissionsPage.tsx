import { useCallback, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'
import { listSubmissions, reviseSubmission, submitSubmission, withdrawSubmission } from './api'
import { errText, formatDate, LoadState, Msg, useLoad } from './common'
import type { Submission } from './types'

const ICON: Record<string, string> = {
  draft: '✎',
  submitted: '⏳',
  changes_requested: '!',
  approved: '✓',
  rejected: '✕',
  withdrawn: '–',
}

export function titleOf(payload: Record<string, unknown>): string {
  const t = payload.title
  if (typeof t === 'object' && t !== null && 'en' in t) return String((t as { en: unknown }).en)
  return ''
}

export function SubmissionsPage() {
  const { t, i18n } = useTranslation()
  const load = useCallback((o: { signal: AbortSignal }) => listSubmissions(o), [])
  const { state, reload } = useLoad(load)
  const [error, setError] = useState<string | null>(null)
  const [ok, setOk] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<string | null>(null)

  async function run(s: Submission, action: 'submit' | 'withdraw' | 'revise') {
    if (action === 'withdraw' && !window.confirm(t('partner.sub.confirmWithdraw'))) return
    setError(null)
    setOk(null)
    setBusyId(s.id)
    try {
      if (action === 'submit') await submitSubmission(s.id)
      else if (action === 'withdraw') await withdrawSubmission(s.id)
      else await reviseSubmission(s.id)
      setOk(t(`partner.sub.done.${action}`))
      reload()
    } catch (err) {
      setError(errText(err, t))
    } finally {
      setBusyId(null)
    }
  }

  return (
    <section aria-labelledby="ptn-sub-h">
      <h2 id="ptn-sub-h">{t('partner.sub.title')}</h2>
      <Link className="btn btn--big" to="/partner/submissions/new">
        {t('partner.sub.new')}
      </Link>
      <Msg error={error} ok={ok} />
      <LoadState state={state} onRetry={reload} />
      {state.phase === 'ready' &&
        (state.data.length === 0 ? (
          <p role="status">{t('partner.sub.empty')}</p>
        ) : (
          <ul className="ptn-list" style={{ marginTop: '1rem' }}>
            {state.data.map((s) => {
              const editable = s.status === 'draft' || s.status === 'changes_requested'
              return (
                <li key={s.id} className="ptn-card">
                  <h3>{titleOf(s.payload) || s.id}</h3>
                  <p>
                    <span className="badge">
                      <span aria-hidden="true">{ICON[s.status] ?? '?'} </span>
                      {t(`partner.status.${s.status}`, { defaultValue: s.status })}
                    </span>
                  </p>
                  <p className="muted">{t('partner.sub.updated', { date: formatDate(s.updated_at, i18n.language) })}</p>
                  {s.review_notes && (
                    <p className="notice">
                      <strong>{t('partner.sub.reviewNotes')}:</strong> {s.review_notes}
                    </p>
                  )}
                  {s.published_slug && (
                    <p>
                      <strong>{t('partner.sub.slug')}:</strong> {s.published_slug}
                    </p>
                  )}
                  <div className="ptn-actions">
                    {editable && (
                      <>
                        <Link className="btn btn--secondary" to={`/partner/submissions/${s.id}`}>
                          {t('partner.sub.edit')}
                        </Link>
                        <button type="button" className="btn" disabled={busyId === s.id} onClick={() => void run(s, 'submit')}>
                          {t('partner.sub.submit')}
                        </button>
                      </>
                    )}
                    {s.status === 'approved' && (
                      <button type="button" className="btn btn--secondary" disabled={busyId === s.id} onClick={() => void run(s, 'revise')}>
                        {t('partner.sub.revise')}
                      </button>
                    )}
                    {s.status !== 'rejected' && s.status !== 'withdrawn' && (
                      <button type="button" className="btn btn--danger" disabled={busyId === s.id} onClick={() => void run(s, 'withdraw')}>
                        {t('partner.sub.withdraw')}
                      </button>
                    )}
                  </div>
                </li>
              )
            })}
          </ul>
        ))}
    </section>
  )
}
