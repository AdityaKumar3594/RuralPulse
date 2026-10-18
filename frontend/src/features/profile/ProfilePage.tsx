import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router'
import { getProfile, getQuestions, updateProfileField, withdrawConsent } from '../../api/endpoints'
import { errorMessage } from '../../api/errors'
import type { Profile, ProfileEntry, ProfileField, Question } from '../../api/types'
import { QuestionCard, type Answer } from '../interview/QuestionCard'

function splitItems(text: string): string[] {
  return [...new Set(text.split(/[,;\n،]/).map((s) => s.trim()).filter(Boolean))]
}

function formatValue(value: unknown, question?: Question): string {
  if (Array.isArray(value)) return value.join(', ')
  const option = question?.options.find((o) => o.value === value)
  return option ? option.label : String(value)
}

function initialText(field: ProfileField): string {
  const entry = field.entries.find((e) => e.provenance === 'reported')
  if (!entry || entry.value == null) return ''
  return Array.isArray(entry.value) ? entry.value.join(', ') : String(entry.value)
}

export function ProfilePage() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const [data, setData] = useState<{ profile: Profile; questions: Question[] } | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [editing, setEditing] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [confirmWithdraw, setConfirmWithdraw] = useState(false)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    const { signal } = controller
    Promise.all([getProfile({ signal }), getQuestions(i18n.language, { signal })])
      .then(([profile, questions]) => setData({ profile, questions }))
      .catch((err: unknown) => {
        if (!signal.aborted) setLoadError(errorMessage(err, t))
      })
    return () => controller.abort()
  }, [i18n.language, t, attempt])

  const load = useCallback(() => {
    setLoadError(null)
    setAttempt((n) => n + 1)
  }, [])

  const save = async (field: ProfileField, question: Question, answer: Answer) => {
    let body: { value: unknown } | { unknown: true }
    if (answer.kind === 'unknown') body = { unknown: true }
    else if (answer.kind === 'value') body = { value: answer.value }
    else if (answer.kind === 'text') body = { value: question.kind === 'list_text' ? splitItems(answer.text) : answer.text }
    else return
    setBusy(true)
    setError(null)
    try {
      const profile = await updateProfileField(field.key, body)
      setData((d) => (d ? { ...d, profile } : d))
      setEditing(null)
    } catch (err) {
      setError(errorMessage(err, t))
    } finally {
      setBusy(false)
    }
  }

  const withdraw = async () => {
    setBusy(true)
    try {
      await withdrawConsent()
      void navigate('/consent')
    } catch (err) {
      setError(errorMessage(err, t))
      setBusy(false)
    }
  }

  if (loadError) {
    return (
      <div role="alert">
        <p>{loadError}</p>
        <button type="button" className="btn" onClick={load}>{t('common.retry')}</button>
      </div>
    )
  }
  if (!data) return <p role="status">{t('common.loading')}</p>

  const questionFor = (key: string) => data.questions.find((q) => q.field_key === key)
  const knownFields = data.profile.fields.filter((field) => field.entries.some((entry) => entry.provenance !== 'unknown')).length
  const completion = data.profile.fields.length ? Math.round((knownFields / data.profile.fields.length) * 100) : 0

  const renderEntry = (e: ProfileEntry, question?: Question) => (
    <li key={e.id} className="entry">
      <span className={`badge badge--${e.provenance}`}>{t(`profile.provenance.${e.provenance}`)}</span>
      {e.provenance !== 'unknown' && <strong className="entry__value">{formatValue(e.value, question)}</strong>}
      {e.verification !== 'unverified' && <span className="muted entry__verification"> · {t(`profile.verification.${e.verification}`)}</span>}
    </li>
  )

  return (
    <>
      <header className="profile-header">
        <div>
          <p className="eyebrow">Your starting point</p>
          <h1>{t('profile.title')}</h1>
          <p className="lead">{t('profile.intro')}</p>
        </div>
        <div className="profile-progress" aria-label={`${completion}% of your profile is known`}>
          <span className="profile-progress__value">{completion}%</span>
          <span className="profile-progress__label">profile known</span>
        </div>
      </header>

      <section className="profile-overview" aria-label="Profile overview">
        <div className="profile-overview__copy">
          <span className="profile-overview__kicker">A living profile</span>
          <strong>Built from what you share.</strong>
          <p>Your answers can change as you learn more about yourself.</p>
        </div>
        <div className="profile-meter" aria-hidden="true"><span style={{ width: `${completion}%` }} /></div>
        <div className="profile-overview__stat"><strong>{knownFields}</strong><span>of {data.profile.fields.length} areas shared</span></div>
      </section>

      <section className="profile-fields" aria-labelledby="profile-fields-title">
        <div className="profile-section-heading">
          <div>
            <p className="eyebrow">Your signals</p>
            <h2 id="profile-fields-title">What we know about you</h2>
          </div>
          <p>Change anything, anytime.</p>
        </div>
        <ul className="fields">
          {data.profile.fields.map((field) => {
            const question = questionFor(field.key)
            const title = t(`profile.fields.${field.key}`, { defaultValue: field.description })
            return (
              <li key={field.key} className={`field-card${field.entries.length === 0 ? ' field-card--empty' : ''}`}>
                <div className="field-card__topline"><span className="field-card__dot" aria-hidden="true" /><span className="field-card__state">{field.entries.length ? 'Shared' : 'Open question'}</span></div>
                <h3>{title}</h3>
                {field.entries.length === 0 ? (
                  <p className="muted">{t('profile.notTold')}</p>
                ) : (
                  <ul className="entries">{field.entries.map((e) => renderEntry(e, question))}</ul>
                )}
                {field.conflict && <p className="notice" role="status">{t('profile.conflict')}</p>}
                {question && editing === field.key ? (
                  <div className="field-card__editor">
                    <QuestionCard question={question} busy={busy} mode="edit" initial={initialText(field)} error={error} onAnswer={(a) => void save(field, question, a)} />
                    <button type="button" className="btn btn--link" onClick={() => setEditing(null)}>{t('common.cancel')}</button>
                  </div>
                ) : (
                  question && (
                    <button type="button" className="btn btn--link field-card__change" onClick={() => { setError(null); setEditing(field.key) }} aria-label={`${t('profile.change')}: ${title}`}>
                      {t('profile.change')} <span aria-hidden="true">↗</span>
                    </button>
                  )
                )}
              </li>
            )
          })}
        </ul>
      </section>

      <section className="danger-zone">
        {confirmWithdraw ? (
          <>
            <p role="alert">{t('profile.withdrawConfirm')}</p>
            <button type="button" className="btn btn--danger" disabled={busy} onClick={() => void withdraw()}>{t('profile.withdrawYes')}</button>{' '}
            <button type="button" className="btn btn--link" onClick={() => setConfirmWithdraw(false)}>{t('common.cancel')}</button>
          </>
        ) : (
          <button type="button" className="btn btn--link" onClick={() => setConfirmWithdraw(true)}>{t('profile.withdraw')}</button>
        )}
      </section>
    </>
  )
}
