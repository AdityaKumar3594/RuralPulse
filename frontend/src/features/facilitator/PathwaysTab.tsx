import { useCallback, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ErrorLine, LoadGate, useAction, useLoad } from '../support/shared'
import { getPathways, setStep } from './api'
import type { Plan, PlanStep, StepStatus } from './types'

const STATUSES: StepStatus[] = ['not_started', 'in_progress', 'done']

export function PathwaysTab({ studentId }: { studentId: string }) {
  const { t, i18n } = useTranslation()
  const lang = i18n.language
  const load = useCallback((o: { signal: AbortSignal }) => getPathways(studentId, lang, o), [studentId, lang])
  const { state, reload, setData } = useLoad(load)
  return (
    <LoadGate state={state} reload={reload}>
      {(plans) =>
        plans.length === 0 ? (
          <p role="status">{t('facilitator.pathways.none')}</p>
        ) : (
          <>
            <p className="muted">{t('facilitator.pathways.intro')}</p>
            {plans.map((p) => (
              <PlanCard
                key={p.id}
                plan={p}
                studentId={studentId}
                onUpdated={(u) => setData(plans.map((x) => (x.id === u.id ? u : x)))}
              />
            ))}
          </>
        )
      }
    </LoadGate>
  )
}

function PlanCard({ plan, studentId, onUpdated }: { plan: Plan; studentId: string; onUpdated: (p: Plan) => void }) {
  const { t } = useTranslation()
  const done = plan.steps.filter((s) => s.status === 'done').length
  const [message, setMessage] = useState<{ stepId: string; text: string } | null>(null)
  return (
    <section className="sp-box" aria-labelledby={`pl-${plan.id}`}>
      <h3 id={`pl-${plan.id}`}>{plan.career.title ?? plan.career.slug}</h3>
      <p>{t('facilitator.pathways.progress', { done, total: plan.steps.length })}</p>
      <ol className="sp-list">
        {plan.steps.map((s) => (
          <StepRow key={s.id} step={s} plan={plan} studentId={studentId} onUpdated={onUpdated} message={message} setMessage={setMessage} />
        ))}
      </ol>
    </section>
  )
}

function StepRow({
  step,
  plan,
  studentId,
  onUpdated,
  message,
  setMessage,
}: {
  step: PlanStep
  plan: Plan
  studentId: string
  onUpdated: (p: Plan) => void
  message: { stepId: string; text: string } | null
  setMessage: (m: { stepId: string; text: string } | null) => void
}) {
  const { t, i18n } = useTranslation()
  const { run, busy, error } = useAction()
  const change = async (status: StepStatus) => {
    setMessage(null)
    const out = await run(() => setStep(studentId, plan.id, step.id, status, i18n.language))
    if (out) {
      onUpdated(out)
      setMessage({ stepId: step.id, text: t('facilitator.pathways.updated') })
    }
  }
  return (
    <li className="sp-card">
      <strong>{step.title ?? step.id}</strong>
      <p className="muted">{t(`facilitator.pathways.status.${step.status}`)}</p>
      <ErrorLine message={error} />
      {message?.stepId === step.id && (
        <p role="status" className="sp-ok">
          {message.text}
        </p>
      )}
      <div className="sp-row" role="group" aria-label={t('facilitator.pathways.setStatus')}>
        {STATUSES.map((s) => (
          <button
            key={s}
            type="button"
            className="btn btn--secondary"
            aria-pressed={step.status === s}
            disabled={busy || step.status === s}
            onClick={() => change(s)}
          >
            {t(`facilitator.pathways.status.${s}`)}
          </button>
        ))}
      </div>
    </li>
  )
}
