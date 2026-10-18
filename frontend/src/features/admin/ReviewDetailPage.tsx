import { useCallback, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useParams, useSearchParams } from 'react-router'
import { decide, listProviders, listSubmissions } from './api'
import { errText, LoadState, Msg, useLoad } from './common'
import { PayloadView } from './PayloadView'
import {
  checkVerification,
  emptyVerification,
  usedEvidence,
  VerificationForm,
  type VerificationValue,
} from './VerificationForm'
import type { Decision, DecisionResult } from './types'

export function ReviewDetailPage() {
  const { t } = useTranslation()
  const { id = '' } = useParams()
  const [params] = useSearchParams()
  const listStatus = params.get('status') || 'submitted'
  const load = useCallback(
    async (o: { signal: AbortSignal }) => {
      const [subs, providers] = await Promise.all([listSubmissions(listStatus, o), listProviders(undefined, o)])
      return { sub: subs.find((s) => s.id === id) ?? null, providers }
    },
    [id, listStatus],
  )
  const { state, reload } = useLoad(load)

  const [decision, setDecision] = useState<Decision>('approve')
  const [notes, setNotes] = useState('')
  const [ver, setVer] = useState<VerificationValue>(emptyVerification)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<DecisionResult | null>(null)

  async function submit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    if (decision !== 'approve' && !notes.trim()) {
      setError(t('admin.errors.notes_required'))
      return
    }
    if (decision === 'approve') {
      const problem = checkVerification(ver, t)
      if (problem) {
        setError(problem)
        return
      }
    }
    setBusy(true)
    try {
      const approve = decision === 'approve'
      setResult(await decide(id, decision, notes.trim(), approve ? ver.fields : [], approve ? usedEvidence(ver) : []))
    } catch (err) {
      setError(errText(err, t))
    } finally {
      setBusy(false)
    }
  }

  const back = (
    <Link className="btn btn--link" to="/admin/review">
      {t('admin.review.back')}
    </Link>
  )

  if (result) {
    return (
      <section aria-labelledby="adm-res-h">
        <h2 id="adm-res-h">{t('admin.result.title')}</h2>
        <p role="status">{t(`admin.result.decided.${decision}`)}</p>
        <dl className="adm-dl">
          <dt>{t('admin.result.status')}</dt>
          <dd>{t(`admin.submissionStatus.${result.submission.status}`, { defaultValue: result.submission.status })}</dd>
          {result.published_slug && (
            <>
              <dt>{t('admin.result.slug')}</dt>
              <dd>{result.published_slug}</dd>
            </>
          )}
          {result.verification_status && (
            <>
              <dt>{t('admin.result.verification')}</dt>
              <dd>{result.verification_status}</dd>
            </>
          )}
          {result.stripped_claims.length > 0 && (
            <>
              <dt>{t('admin.result.stripped')}</dt>
              <dd>
                <p className="muted">{t('admin.result.strippedHint')}</p>
                <ul>
                  {result.stripped_claims.map((c) => (
                    <li key={c}>{c}</li>
                  ))}
                </ul>
              </dd>
            </>
          )}
        </dl>
        <div className="stack">
          {result.published_slug && (
            <Link className="btn btn--secondary" to={`/admin/opportunities?slug=${encodeURIComponent(result.published_slug)}`}>
              {t('admin.result.tools')}
            </Link>
          )}
          {back}
        </div>
      </section>
    )
  }

  return (
    <section aria-labelledby="adm-rd-h">
      <h2 id="adm-rd-h">{t('admin.review.detailTitle')}</h2>
      {back}
      <LoadState state={state} onRetry={reload} />
      {state.phase === 'ready' &&
        (!state.data.sub ? (
          <p role="status">{t('admin.review.notFound')}</p>
        ) : (
          <>
            <p>
              <span className="badge">{t(`admin.submissionStatus.${state.data.sub.status}`, { defaultValue: state.data.sub.status })}</span>{' '}
              {t('admin.review.byProvider', {
                name: state.data.providers.find((p) => p.id === state.data.sub?.provider_id)?.name ?? '',
              })}
            </p>
            {state.data.sub.replaces_slug && <p className="notice">{t('admin.review.replaces', { slug: state.data.sub.replaces_slug })}</p>}
            <p className="adm-claims">{t('admin.review.claimsNote')}</p>
            <PayloadView payload={state.data.sub.payload} />

            {state.data.sub.status === 'submitted' ? (
              <form className="adm-form" onSubmit={submit} noValidate>
                <fieldset className="adm-fieldset">
                  <legend>{t('admin.decision.title')}</legend>
                  {(['approve', 'request_changes', 'reject'] as Decision[]).map((d) => (
                    <label key={d} className="adm-check">
                      <input type="radio" name="decision" checked={decision === d} onChange={() => setDecision(d)} />
                      <span>{t(`admin.decision.${d}`)}</span>
                    </label>
                  ))}
                </fieldset>
                <div className="field">
                  <label htmlFor="adm-notes">
                    {decision === 'approve' ? t('admin.decision.notesOptional') : t('admin.decision.notesRequired')}
                  </label>
                  <textarea id="adm-notes" maxLength={1000} value={notes} onChange={(e) => setNotes(e.target.value)} />
                </div>
                {decision === 'approve' && <VerificationForm value={ver} onChange={setVer} />}
                <button type="submit" className="btn btn--big" disabled={busy}>
                  {busy ? t('admin.saving') : t('admin.decision.submit')}
                </button>
                <Msg error={error} />
              </form>
            ) : (
              <p className="notice">{t('admin.errors.not_awaiting_review')}</p>
            )}
          </>
        ))}
    </section>
  )
}
