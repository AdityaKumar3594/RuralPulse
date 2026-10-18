import { useCallback, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router'
import { ApiError } from '../../api/client'
import { ExplanationPanel } from '../../components/ExplanationPanel'
import { Status } from '../discover/Badges'
import { apiMessage, enumText } from '../discover/format'
import { useLoad } from '../discover/useLoad'
import { getPlan, setStepStatus } from './api'
import { StepCard } from './StepCard'
import type { Plan, StepStatus } from './types'
import '../discover/shared.css'
import './pathway.css'

export function PathwayDetailPage() {
  const { id = '' } = useParams()
  const { t, i18n } = useTranslation()
  const lang = i18n.language
  const load = useCallback((o: { signal: AbortSignal }) => getPlan(id, lang, o), [id, lang])
  const { state, reload, setData } = useLoad(load)

  return (
    <>
      <p>
        <Link to="/pathways">{t('pathway.back')}</Link>
      </p>
      {state.phase === 'loading' && <Status />}
      {state.phase === 'error' && <Status error={apiMessage(state.error, t)} onRetry={reload} />}
      {state.phase === 'ready' && <PlanView plan={state.data} lang={lang} onPlan={setData} />}
    </>
  )
}

function PlanView({ plan, lang, onPlan }: { plan: Plan; lang: string; onPlan: (p: Plan) => void }) {
  const { t } = useTranslation()
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<{ stepId: string; kind: 'ok' | 'error'; text: string } | null>(null)

  const byId = new Map(plan.steps.map((s) => [s.id, s]))
  const alternatives = new Set(plan.alternatives)
  const main = plan.steps.filter((s) => !alternatives.has(s.id))
  const routes = plan.steps.filter((s) => alternatives.has(s.id))
  const done = plan.steps.filter((s) => s.status === 'done').length
  const career = plan.career.title ?? plan.career.slug

  const change = async (stepId: string, status: StepStatus) => {
    const step = byId.get(stepId)
    setBusy(true)
    setMessage(null)
    try {
      const updated = await setStepStatus(plan.id, stepId, status, lang)
      onPlan(updated)
      setMessage({
        stepId,
        kind: 'ok',
        text: t('pathway.saved', { title: step?.title ?? stepId, status: t(`pathway.status.${status}`) }),
      })
    } catch (err) {
      const own =
        err instanceof ApiError && err.status === 409 && err.detail
          ? t(`pathway.errors.${err.detail}`, { defaultValue: '' })
          : ''
      setMessage({ stepId, kind: 'error', text: own || apiMessage(err, t) })
    } finally {
      setBusy(false)
    }
  }

  const card = (stepId: string, number?: number) => {
    const step = byId.get(stepId)
    if (!step) return null
    const deps = step.depends_on.map((d) => byId.get(d)).filter((s) => s !== undefined)
    return (
      <StepCard
        key={step.id}
        step={step}
        number={number}
        afterTitles={deps.map((d) => d.title ?? d.id)}
        ready={deps.every((d) => d.status === 'done')}
        busy={busy}
        message={message && message.stepId === step.id ? message : null}
        onChange={(s) => void change(step.id, s)}
      />
    )
  }

  return (
    <article>
      <h1>{t('pathway.detailTitle', { career })}</h1>
      <p className="lead">{t('pathway.listIntro')}</p>
      <p role="status">{t('pathway.progress', { done, total: plan.steps.length })}</p>
      <progress max={plan.steps.length} value={done} aria-label={t('pathway.progress', { done, total: plan.steps.length })} />
      {plan.student_stage && (
        <p className="muted">{t('pathway.forStage', { stage: enumText(t, 'discover.stage', plan.student_stage) })}</p>
      )}
      {plan.language_fallback && <p className="muted">{t('discover.languageFallback')}</p>}
      <p>
        <Link to={`/careers/${encodeURIComponent(plan.career.slug)}`}>{t('pathway.readCareer')}</Link>
      </p>

      <section className="section" aria-labelledby="p-steps">
        <h2 id="p-steps">{t('pathway.stepsTitle')}</h2>
        <ol className="steps" aria-labelledby="p-steps">{main.map((s, i) => card(s.id, i + 1))}</ol>
      </section>

      {routes.length > 0 && (
        <section className="alternatives" aria-labelledby="p-alt">
          <h2 id="p-alt">{t('pathway.alternativesTitle')}</h2>
          <p>{t('pathway.alternativesHelp')}</p>
          <ul className="steps" aria-labelledby="p-alt">{routes.map((s) => card(s.id))}</ul>
        </section>
      )}

      {plan.unknowns.length > 0 && (
        <section className="section" aria-labelledby="p-unk">
          <h2 id="p-unk">{t('pathway.unknownsTitle')}</h2>
          <ul>
            {plan.unknowns.map((u) => (
              <li key={u}>{enumText(t, 'pathway.unknown', u)}</li>
            ))}
          </ul>
        </section>
      )}

      <p className="muted">{t('pathway.version', { version: plan.version })}</p>
      <ExplanationPanel request={{ kind: 'pathway', plan_id: plan.id }} />
    </article>
  )
}
