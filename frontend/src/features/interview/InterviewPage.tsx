import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'
import { answerQuestion, startInterview } from '../../api/endpoints'
import { errorMessage } from '../../api/errors'
import type { InterviewSession } from '../../api/types'
import { QuestionCard, type Answer } from './QuestionCard'

export function InterviewPage() {
  const { t, i18n } = useTranslation()
  const [session, setSession] = useState<InterviewSession | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const [attempt, setAttempt] = useState(0)

  // Starts (or resumes) the session once on mount and again on retry, not when the language
  // changes: the server keeps the session's own language.
  useEffect(() => {
    let cancelled = false
    startInterview(i18n.language)
      .then((s) => !cancelled && setSession(s))
      .catch((err: unknown) => !cancelled && setLoadError(errorMessage(err, t)))
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [attempt])

  const start = useCallback(() => {
    setLoadError(null)
    setAttempt((n) => n + 1)
  }, [])

  const submit = async (answer: Answer) => {
    if (!session?.question) return
    setBusy(true)
    setError(null)
    try {
      const result = await answerQuestion(session.id, { question_id: session.question.id, ...answer })
      setMessage(result.message)
      setSession(result.session)
    } catch (err) {
      setError(errorMessage(err, t)) // the typed answer stays in the form so the student can resend
    } finally {
      setBusy(false)
    }
  }

  if (loadError) {
    return (
      <div role="alert">
        <p>{loadError}</p>
        <button type="button" className="btn" onClick={start}>
          {t('common.retry')}
        </button>
      </div>
    )
  }
  if (!session) return <p role="status">{t('common.loading')}</p>

  if (session.status === 'completed' || !session.question) {
    return (
      <section>
        <h1>{t('interview.doneTitle')}</h1>
        <p className="lead">{t('interview.doneBody')}</p>
        <Link className="btn btn--big" to="/profile">
          {t('interview.viewProfile')}
        </Link>
      </section>
    )
  }

  const { answered, total } = session.progress
  return (
    <>
      <h1 className="visually-hidden">{t('interview.title')}</h1>
      <p className="muted" id="progress-label">
        {t('interview.progress', { answered, total })}
      </p>
      <progress aria-labelledby="progress-label" value={answered} max={total} />
      <QuestionCard
        key={session.question.id}
        question={session.question}
        busy={busy}
        mode="interview"
        onAnswer={(a) => void submit(a)}
        message={message}
        error={error}
      />
    </>
  )
}
