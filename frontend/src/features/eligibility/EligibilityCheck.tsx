import { useCallback, useEffect, useRef, useState, type RefObject } from 'react'
import { useTranslation } from 'react-i18next'
import type { TFunction } from 'i18next'
import { getQuestions, updateProfileField } from '../../api/endpoints'
import type { Question } from '../../api/types'
import { ExplanationPanel } from '../../components/ExplanationPanel'
import { ExternalLink, FlagList, Status } from '../discover/Badges'
import { apiMessage, enumText, formatDate } from '../discover/format'
import { useLoad } from '../discover/useLoad'
import { QuestionCard, type Answer } from '../interview/QuestionCard'
import { evaluate } from './api'
import type { Check, Evaluation, MissingFact, Outcome } from './types'
import '../discover/shared.css'
import './eligibility.css'

const OUTCOME_ICON: Record<Outcome, string> = { ELIGIBLE: '✓', INELIGIBLE: '✕', UNKNOWN: '?', NEEDS_REVIEW: '!' }
const RESULT_ICON: Record<Check['result'], string> = { pass: '✓', fail: '✕', unknown: '?', conflict: '≠' }

interface Props {
  /** Slug of the opportunity to check. */
  slug: string
  /** Start checking straight away (the page does); otherwise a button starts it. */
  autoRun?: boolean
}

/** Checks the signed-in student against one opportunity and shows what is met, not met or missing. */
export function EligibilityCheck({ slug, autoRun = false }: Props) {
  const { t } = useTranslation()
  const [started, setStarted] = useState(autoRun)
  if (!started) {
    return (
      <button type="button" className="btn btn--big" onClick={() => setStarted(true)}>
        {t('eligibility.check')}
      </button>
    )
  }
  return <EvaluationView slug={slug} />
}

function EvaluationView({ slug }: { slug: string }) {
  const { t, i18n } = useTranslation()
  const [lang] = useState(i18n.language) // do not store a new evaluation just because the language was switched
  const [rechecks, setRechecks] = useState(0)
  const load = useCallback((o: { signal: AbortSignal }) => evaluate(slug, lang, o), [slug, lang])
  const { state, reload } = useLoad(load)

  const recheck = useCallback(() => {
    setRechecks((n) => n + 1)
    reload()
  }, [reload])

  if (state.phase === 'loading')
    return <Status loading={rechecks > 0 ? t('eligibility.rechecking') : t('eligibility.checking')} />
  if (state.phase === 'error') return <Status error={apiMessage(state.error, t)} onRetry={reload} />
  return <Result evaluation={state.data} lang={lang} onRecheck={recheck} />
}

function Result({ evaluation: ev, lang, onRecheck }: { evaluation: Evaluation; lang: string; onRecheck: () => void }) {
  const { t } = useTranslation()
  const heading = useRef<HTMLHeadingElement>(null)
  useEffect(() => heading.current?.focus(), [])

  return (
    <section aria-label={t('eligibility.resultTitle')}>
      <OutcomeBox outcome={ev.outcome} headingRef={heading} />

      {ev.reasons.length > 0 && (
        <div className="section">
          <h3>{t('eligibility.reasonsTitle')}</h3>
          <ul>
            {ev.reasons.map((r) => (
              <li key={r}>{enumText(t, 'eligibility.reason', r)}</li>
            ))}
          </ul>
        </div>
      )}

      {ev.checks.length > 0 && (
        <div className="section">
          <h3>{t('eligibility.checksTitle')}</h3>
          <ul className="checks">
            {ev.checks.map((c) => (
              <CheckRow key={c.rule} check={c} />
            ))}
          </ul>
        </div>
      )}

      {ev.missing.length > 0 && (
        <div className="section">
          <h3>{t('eligibility.missingTitle')}</h3>
          <p>{t('eligibility.missingIntro')}</p>
          <ul className="missing">
            {ev.missing.map((m) => (
              <MissingItem key={m.fact} item={m} lang={lang} onAnswered={onRecheck} />
            ))}
          </ul>
        </div>
      )}

      {ev.flags.length > 0 && (
        <div className="section">
          <h3>{t('eligibility.flagsTitle')}</h3>
          <FlagList flags={ev.flags} />
        </div>
      )}

      <p className="note" role="note">
        {t('eligibility.separate')}
      </p>
      <p className="elig-meta">
        {t('eligibility.version', { version: ev.rules_version })}
        <br />
        {t('eligibility.checkedOn', { date: formatDate(ev.evaluated_on, lang) })}
      </p>
      <p>
        <ExternalLink href={ev.opportunity.url}>{t('eligibility.officialLink')}</ExternalLink>
      </p>
      <div className="actions">
        <button type="button" className="btn btn--secondary" onClick={onRecheck}>
          {t('eligibility.recheck')}
        </button>
      </div>
      <ExplanationPanel request={{ kind: 'eligibility', evaluation_id: ev.id }} />
    </section>
  )
}

function OutcomeBox({ outcome, headingRef }: { outcome: Outcome; headingRef: RefObject<HTMLHeadingElement | null> }) {
  const { t } = useTranslation()
  return (
    <div className={`outcome outcome--${outcome}`}>
      <h2 ref={headingRef} tabIndex={-1}>
        <span className="outcome__icon" aria-hidden="true">
          {OUTCOME_ICON[outcome]}
        </span>
        {t(`eligibility.outcome.${outcome}.title`)}
      </h2>
      <p>{t(`eligibility.outcome.${outcome}.body`)}</p>
    </div>
  )
}

// --- one rule ---------------------------------------------------------------------------------

type Formatter = (value: unknown) => string

function formatters(t: TFunction, lang: string): Record<string, { expected: Formatter; actual: Formatter }> {
  const stage: Formatter = (v) => (typeof v === 'string' ? enumText(t, 'discover.stage', v) : String(v))
  const money: Formatter = (v) => t('eligibility.value.amount', { amount: Number(v).toLocaleString('en-IN') })
  const plain: Formatter = (v) => (Array.isArray(v) ? v.join(', ') : String(v))
  const age: Formatter = (v) => t('eligibility.value.years', { age: String(v) })
  const ageRule: Formatter = (v) => {
    const o = v as { limit?: unknown; as_on?: unknown } | null
    return o && typeof o === 'object'
      ? t('eligibility.value.age', { limit: String(o.limit), date: formatDate(String(o.as_on), lang) })
      : t('eligibility.value.years', { age: String(v) })
  }
  return {
    expiry: { expected: (v) => t('eligibility.value.validUntil', { date: formatDate(String(v), lang) }), actual: plain },
    deadline: { expected: (v) => t('eligibility.value.deadline', { date: formatDate(String(v), lang) }), actual: plain },
    state: { expected: plain, actual: plain },
    education_stage: { expected: (v) => (Array.isArray(v) ? v.map(stage).join(', ') : stage(v)), actual: stage },
    age_min: { expected: ageRule, actual: age },
    age_max: { expected: ageRule, actual: age },
    family_income_max: {
      expected: (v) => t('eligibility.value.income', { amount: Number(v).toLocaleString('en-IN') }),
      actual: money,
    },
  }
}

function CheckRow({ check }: { check: Check }) {
  const { t, i18n } = useTranslation()
  const f = formatters(t, i18n.language)[check.rule] ?? {
    expected: (v: unknown) => JSON.stringify(v),
    actual: (v: unknown) => JSON.stringify(v),
  }
  const basis = (b: string) => enumText(t, 'eligibility.basis', b)

  let actual: string | null = null
  if (check.result === 'conflict' && Array.isArray(check.actual)) {
    // Each candidate is [basis, value]: every answer we hold, side by side.
    actual = check.actual
      .map((c) => (Array.isArray(c) ? t('eligibility.value.conflict', { basis: basis(String(c[0])), value: f.actual(c[1]) }) : String(c)))
      .join('; ')
    actual = t('eligibility.actual', { value: actual })
  } else if (check.actual != null) {
    const base = f.actual(check.actual)
    actual = t('eligibility.actual', { value: check.basis ? `${base} (${basis(check.basis)})` : base })
  } else if (check.result === 'unknown' && !['expiry', 'deadline'].includes(check.rule)) {
    actual = t('eligibility.noActual')
  }

  return (
    <li>
      <p>
        <strong>{enumText(t, 'eligibility.rule', check.rule)}</strong>{' '}
        <span className={`tag tag--${check.result}`}>
          <span aria-hidden="true">{RESULT_ICON[check.result]} </span>
          {t(`eligibility.result.${check.result}`)}
        </span>
      </p>
      {check.expected != null && <p>{t('eligibility.expected', { value: f.expected(check.expected) })}</p>}
      {actual && <p>{actual}</p>}
    </li>
  )
}

// --- answering a missing fact right here ----------------------------------------------------

function splitItems(text: string): string[] {
  return [...new Set(text.split(/[,;\n،]/).map((s) => s.trim()).filter(Boolean))]
}

type AnswerState =
  | { phase: 'closed' }
  | { phase: 'loading' }
  | { phase: 'missing' }
  | { phase: 'open'; question: Question }

function MissingItem({ item, lang, onAnswered }: { item: MissingFact; lang: string; onAnswered: () => void }) {
  const { t } = useTranslation()
  const [state, setState] = useState<AnswerState>({ phase: 'closed' })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fact = enumText(t, 'eligibility.fact', item.fact)

  const open = async () => {
    if (!item.question_id) return
    setState({ phase: 'loading' })
    setError(null)
    try {
      const questions = await getQuestions(lang)
      const question = questions.find((q) => q.id === item.question_id)
      setState(question ? { phase: 'open', question } : { phase: 'missing' })
    } catch (err) {
      setError(apiMessage(err, t))
      setState({ phase: 'closed' })
    }
  }

  const save = async (question: Question, answer: Answer) => {
    let body: { value: unknown } | { unknown: true }
    if (answer.kind === 'unknown') body = { unknown: true }
    else if (answer.kind === 'value') body = { value: answer.value }
    else if (answer.kind === 'text')
      body = { value: question.kind === 'list_text' ? splitItems(answer.text) : answer.text }
    else return
    setBusy(true)
    setError(null)
    try {
      await updateProfileField(question.field_key, body)
      onAnswered() // the whole check runs again and replaces this list
    } catch (err) {
      setError(apiMessage(err, t))
      setBusy(false)
    }
  }

  return (
    <li>
      <p>
        <strong>{fact}</strong>
      </p>
      {item.question_id === null && <p className="muted">{t('eligibility.setAtRegistration')}</p>}
      {item.question_id !== null && state.phase === 'closed' && (
        <button type="button" className="btn btn--secondary" onClick={() => void open()} aria-label={t('eligibility.answerFor', { fact })}>
          {t('eligibility.answerNow')}
        </button>
      )}
      {state.phase === 'loading' && <p role="status">{t('eligibility.loadingQuestion')}</p>}
      {state.phase === 'missing' && <p role="alert">{t('eligibility.noQuestion')}</p>}
      {state.phase === 'open' && (
        <>
          <QuestionCard question={state.question} busy={busy} mode="edit" error={error} onAnswer={(a) => void save(state.question, a)} />
          <button type="button" className="btn btn--link" disabled={busy} onClick={() => setState({ phase: 'closed' })}>
            {t('eligibility.cancel')}
          </button>
        </>
      )}
      {state.phase !== 'open' && error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
    </li>
  )
}
