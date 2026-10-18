import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import type { Question } from '../../api/types'

export type Answer =
  | { kind: 'value'; value: unknown }
  | { kind: 'text'; text: string }
  | { kind: 'unknown' }
  | { kind: 'skip' }

interface Props {
  question: Question
  busy: boolean
  /** interview: free text allowed on choices, "skip" shown. edit: strict values, no skip. */
  mode: 'interview' | 'edit'
  onAnswer: (answer: Answer) => void
  message?: string | null
  error?: string | null
  initial?: string
}

const DEFAULT_MAX = 1_000_000_000

export function QuestionCard({ question, busy, mode, onAnswer, message, error, initial = '' }: Props) {
  const { t } = useTranslation()
  const [text, setText] = useState(initial)
  const [localError, setLocalError] = useState<string | null>(null)
  const heading = useRef<HTMLHeadingElement>(null)

  // Move focus to the new question so screen reader users hear it.
  useEffect(() => heading.current?.focus(), [question.id])

  const sendText = (e: FormEvent) => {
    e.preventDefault()
    const value = text.trim()
    if (!value) return setLocalError(t('errors.validation.answer'))
    if (question.kind === 'number') {
      const min = question.min_value ?? 0
      const max = question.max_value ?? DEFAULT_MAX
      const range = t('errors.validation.number', { min, max })
      const digits = value.replace(/[,\s]/g, '') // "3,50,000" is just 350000
      if (/^\d{1,9}$/.test(digits)) {
        const n = Number(digits)
        if (n < min || n > max) return setLocalError(range)
        setLocalError(null)
        return onAnswer({ kind: 'value', value: n })
      }
      if (mode === 'edit') return setLocalError(range)
    }
    setLocalError(null)
    onAnswer({ kind: 'text', text: value })
  }

  const textInput = (label: string, multiline: boolean, hint?: string) => (
    <form onSubmit={sendText} noValidate>
      <label htmlFor="answer-text">{label}</label>
      {hint && (
        <p id="answer-hint" className="muted">
          {hint}
        </p>
      )}
      {multiline ? (
        <textarea id="answer-text" rows={3} value={text} maxLength={500}
          aria-describedby={hint ? 'answer-hint' : undefined}
          onChange={(e) => setText(e.target.value)} />
      ) : (
        <input id="answer-text" type="text" value={text} maxLength={500}
          inputMode={question.kind === 'number' ? 'numeric' : undefined}
          onChange={(e) => setText(e.target.value)} />
      )}
      <button type="submit" className="btn" disabled={busy}>
        {mode === 'edit' ? t('common.save') : t('interview.send')}
      </button>
    </form>
  )

  const shownError = localError ?? error

  return (
    <section aria-labelledby="question-title">
      <h2 id="question-title" ref={heading} tabIndex={-1}>
        {question.prompt}
      </h2>
      <p className="muted">{t('interview.why', { why: question.why })}</p>

      {question.kind === 'single_choice' && (
        <>
          <ul className="options">
            {question.options.map((o) => (
              <li key={o.value}>
                <button type="button" className="btn btn--option" disabled={busy}
                  onClick={() => onAnswer({ kind: 'value', value: o.value })}>
                  {o.label}
                </button>
              </li>
            ))}
          </ul>
          {mode === 'interview' && (
            <details>
              <summary>{t('interview.typeOwn')}</summary>
              {textInput(t('interview.textLabel'), false)}
            </details>
          )}
        </>
      )}
      {question.kind === 'list_text' &&
        textInput(
          t('interview.listLabel'),
          true,
          mode === 'edit' ? t('profile.listHint') : t('interview.listHint'),
        )}
      {question.kind === 'number' && textInput(t('interview.numberLabel'), false)}
      {question.kind === 'short_text' && textInput(t('interview.textLabel'), false)}

      {message && (
        <p role="status" className="notice">
          {message}
        </p>
      )}
      {shownError && (
        <p role="alert" className="error">
          {shownError}
        </p>
      )}

      <div className="actions">
        <button type="button" className="btn btn--link" disabled={busy}
          onClick={() => onAnswer({ kind: 'unknown' })}>
          {t('interview.dontKnow')}
        </button>
        {mode === 'interview' && (
          <button type="button" className="btn btn--link" disabled={busy}
            onClick={() => onAnswer({ kind: 'skip' })}>
            {t('interview.skip')}
          </button>
        )}
      </div>
    </section>
  )
}
