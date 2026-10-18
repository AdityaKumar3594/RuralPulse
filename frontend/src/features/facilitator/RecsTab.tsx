import { useCallback, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ApiError } from '../../api/client'
import { ErrorLine, LoadGate, useAction, useLoad } from '../support/shared'
import { getRecommendations, reviewRecommendation } from './api'
import type { RecItem, ReviewDecision } from './types'

const DECISIONS: ReviewDecision[] = ['agree', 'disagree', 'needs_discussion']

export function RecsTab({ studentId }: { studentId: string }) {
  const { t, i18n } = useTranslation()
  const lang = i18n.language
  const load = useCallback((o: { signal: AbortSignal }) => getRecommendations(studentId, lang, o), [studentId, lang])
  const { state, reload } = useLoad(load)
  // "no suggestions yet" is a normal state, not a failure
  if (state.phase === 'error' && state.error instanceof ApiError && state.error.detail === 'no_recommendations_yet')
    return <p role="status">{t('facilitator.recs.none')}</p>
  return (
    <LoadGate state={state} reload={reload}>
      {(run) => (
        <>
          <p className="muted">{t('facilitator.recs.intro')}</p>
          {run.items.length === 0 ? (
            <p role="status">{t(`facilitator.recs.status.${run.status}`)}</p>
          ) : (
            <ul className="sp-list">
              {run.items.map((item) => (
                <RecCard key={item.slug} item={item} runId={run.id} studentId={studentId} />
              ))}
            </ul>
          )}
        </>
      )}
    </LoadGate>
  )
}

function RecCard({ item, runId, studentId }: { item: RecItem; runId: string; studentId: string }) {
  const { t } = useTranslation()
  const { run, busy, error } = useAction()
  const [note, setNote] = useState('')
  const [saved, setSaved] = useState<ReviewDecision | null>(null)
  const name = item.career.title ?? item.slug

  const review = async (decision: ReviewDecision) => {
    setSaved(null)
    const ok = await run(async () => {
      await reviewRecommendation(studentId, { run_id: runId, career: item.slug, decision, note: note.trim() || null })
      return true
    })
    if (ok) setSaved(decision)
  }

  return (
    <li className="sp-card">
      <h3>{name}</h3>
      <p>
        <span className="sp-tag">
          {item.kind === 'match' && item.match_level ? t(`facilitator.recs.level.${item.match_level}`) : t('facilitator.recs.explore')}
        </span>
      </p>
      {item.career.description && <p>{item.career.description}</p>}
      {item.reasons.length > 0 && (
        <ul>
          {item.reasons.map((r, i) => (
            <li key={i}>{t('facilitator.recs.reason', { term: r.student_term, text: r.matched_text })}</li>
          ))}
        </ul>
      )}
      <div className="sp-field sp-form">
        <label htmlFor={`rn-${item.slug}`}>{t('facilitator.recs.note')}</label>
        <textarea id={`rn-${item.slug}`} value={note} maxLength={500} onChange={(e) => setNote(e.target.value)} />
      </div>
      <ErrorLine message={error} />
      {saved && (
        <p role="status" className="sp-ok">
          {t('facilitator.recs.saved', { decision: t(`facilitator.recs.decision.${saved}`) })}
        </p>
      )}
      <div className="sp-row">
        {DECISIONS.map((d) => (
          <button key={d} type="button" className="btn btn--secondary" disabled={busy} onClick={() => review(d)}>
            {t(`facilitator.recs.decision.${d}`)}
            <span className="visually-hidden">: {name}</span>
          </button>
        ))}
      </div>
    </li>
  )
}
