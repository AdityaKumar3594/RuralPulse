import { useCallback, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useParams } from 'react-router'
import { Field } from '../../components/Field'
import { createSubmission, getSubmission, submitSubmission, updateSubmission } from './api'
import { errText, LoadState, Msg, useLoad } from './common'
import { emptyForm, toForm, toPayload, validate, type FormState } from './formModel'
import { EDUCATION_STAGES, OPPORTUNITY_KINDS, type Submission } from './types'

export function SubmissionFormPage() {
  const { id } = useParams()
  const { t } = useTranslation()
  const load = useCallback(
    (o: { signal: AbortSignal }) => (id ? getSubmission(id, o) : Promise.resolve(null)),
    [id],
  )
  const { state, reload } = useLoad(load)
  return (
    <section aria-labelledby="ptn-form-h">
      <h2 id="ptn-form-h">{id ? t('partner.form.editTitle') : t('partner.form.newTitle')}</h2>
      <Link className="btn btn--link" to="/partner/submissions">
        {t('partner.form.back')}
      </Link>
      <LoadState state={state} onRetry={reload} />
      {state.phase === 'ready' && <SubmissionForm key={id ?? 'new'} existing={state.data} />}
    </section>
  )
}

function SubmissionForm({ existing }: { existing: Submission | null }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [f, setF] = useState<FormState>(existing ? toForm(existing.payload) : emptyForm)
  const [savedId, setSavedId] = useState<string | null>(existing?.id ?? null)
  const [invalid, setInvalid] = useState<{ field: string; key: string } | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [ok, setOk] = useState<string | null>(null)

  const readOnly = existing !== null && existing.status !== 'draft' && existing.status !== 'changes_requested'
  const set = <K extends keyof FormState>(k: K, v: FormState[K]) => setF((p) => ({ ...p, [k]: v }))
  const err = (field: string) => (invalid?.field === field ? t(`partner.form.errors.${invalid.key}`) : null)

  async function save(thenSubmit: boolean) {
    setError(null)
    setOk(null)
    const bad = validate(f)
    setInvalid(bad)
    if (bad) {
      setError(t(`partner.form.errors.${bad.key}`))
      return
    }
    setBusy(true)
    try {
      const payload = toPayload(f)
      const saved = savedId ? await updateSubmission(savedId, payload) : await createSubmission(payload)
      setSavedId(saved.id)
      if (thenSubmit) {
        await submitSubmission(saved.id)
        void navigate('/partner/submissions')
        return
      }
      setOk(t('partner.form.saved'))
      if (!savedId) void navigate(`/partner/submissions/${saved.id}`, { replace: true })
    } catch (e) {
      setError(errText(e, t))
    } finally {
      setBusy(false)
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    void save(false)
  }

  const toggleStage = (s: string) =>
    set('stages', f.stages.includes(s) ? f.stages.filter((x) => x !== s) : [...f.stages, s])
  const setBenefit = (i: number, patch: Partial<FormState['benefits'][number]>) =>
    set('benefits', f.benefits.map((b, j) => (j === i ? { ...b, ...patch } : b)))

  return (
    <>
      {existing?.review_notes && (
        <p className="notice">
          <strong>{t('partner.sub.reviewNotes')}:</strong> {existing.review_notes}
        </p>
      )}
      {existing?.published_slug && (
        <p>
          <strong>{t('partner.sub.slug')}:</strong> {existing.published_slug}
        </p>
      )}
      {readOnly && <p className="notice">{t('partner.form.readOnly')}</p>}
      <p className="ptn-claims">{t('partner.form.claimsNote')}</p>
      <form className="ptn-form" onSubmit={onSubmit} noValidate>
        <fieldset className="ptn-fieldset" disabled={readOnly || busy}>
          <legend>{t('partner.form.basics')}</legend>
          <div className="field">
            <label htmlFor="ptn-kind">{t('partner.form.kind')}</label>
            <select id="ptn-kind" value={f.kind} onChange={(e) => set('kind', e.target.value)}>
              {OPPORTUNITY_KINDS.map((k) => (
                <option key={k} value={k}>
                  {t(`partner.kinds.${k}`)}
                </option>
              ))}
            </select>
          </div>
          <Field id="ptn-title-en" label={t('partner.form.titleEn')} value={f.titleEn} error={err('titleEn')} onChange={(e) => set('titleEn', e.target.value)} />
          <Field id="ptn-title-ta" label={t('partner.form.titleTa')} value={f.titleTa} onChange={(e) => set('titleTa', e.target.value)} />
          <div className="field">
            <label htmlFor="ptn-sum-en">{t('partner.form.summaryEn')}</label>
            <textarea id="ptn-sum-en" value={f.summaryEn} aria-invalid={err('summaryEn') ? true : undefined} onChange={(e) => set('summaryEn', e.target.value)} />
            {err('summaryEn') && <p className="error" role="alert">{err('summaryEn')}</p>}
          </div>
          <div className="field">
            <label htmlFor="ptn-sum-ta">{t('partner.form.summaryTa')}</label>
            <textarea id="ptn-sum-ta" value={f.summaryTa} onChange={(e) => set('summaryTa', e.target.value)} />
          </div>
          <Field id="ptn-url" type="url" inputMode="url" placeholder="https://" label={t('partner.form.url')} hint={t('partner.form.urlHint')} value={f.url} error={err('url')} onChange={(e) => set('url', e.target.value)} />
          <Field id="ptn-kw" label={t('partner.form.keywords')} hint={t('partner.form.keywordsHint')} value={f.keywords} onChange={(e) => set('keywords', e.target.value)} />
        </fieldset>

        <fieldset className="ptn-fieldset" disabled={readOnly || busy}>
          <legend>{t('partner.form.scope')}</legend>
          <div className="field">
            <label htmlFor="ptn-level">{t('partner.form.scopeLevel')}</label>
            <select id="ptn-level" value={f.level} onChange={(e) => set('level', e.target.value === 'state' ? 'state' : 'national')}>
              <option value="national">{t('partner.form.national')}</option>
              <option value="state">{t('partner.form.state')}</option>
            </select>
          </div>
          {f.level === 'state' && (
            <Field id="ptn-states" label={t('partner.form.states')} hint={t('partner.form.statesHint')} value={f.states} error={err('states')} onChange={(e) => set('states', e.target.value)} />
          )}
        </fieldset>

        <fieldset className="ptn-fieldset" disabled={readOnly || busy}>
          <legend>{t('partner.form.eligibility')}</legend>
          <p className="muted">{t('partner.form.stagesHint')}</p>
          {EDUCATION_STAGES.map((s) => (
            <label key={s} className="ptn-check">
              <input type="checkbox" checked={f.stages.includes(s)} onChange={() => toggleStage(s)} />
              <span>{t(`partner.stages.${s}`)}</span>
            </label>
          ))}
          <Field id="ptn-minage" type="number" inputMode="numeric" min={0} max={100} label={t('partner.form.minAge')} value={f.minAge} error={err('minAge')} onChange={(e) => set('minAge', e.target.value)} />
          <Field id="ptn-maxage" type="number" inputMode="numeric" min={0} max={100} label={t('partner.form.maxAge')} value={f.maxAge} error={err('maxAge')} onChange={(e) => set('maxAge', e.target.value)} />
          <Field id="ptn-income" type="number" inputMode="numeric" min={0} label={t('partner.form.income')} value={f.income} error={err('income')} onChange={(e) => set('income', e.target.value)} />
          <div className="field">
            <label htmlFor="ptn-elig">{t('partner.form.eligText')}</label>
            <textarea id="ptn-elig" value={f.eligText} onChange={(e) => set('eligText', e.target.value)} />
          </div>
        </fieldset>

        <fieldset className="ptn-fieldset" disabled={readOnly || busy}>
          <legend>{t('partner.form.documentsDates')}</legend>
          <div className="field">
            <label htmlFor="ptn-docs">{t('partner.form.documents')}</label>
            <p className="muted">{t('partner.form.documentsHint')}</p>
            <textarea id="ptn-docs" value={f.documents} onChange={(e) => set('documents', e.target.value)} />
          </div>
          <Field id="ptn-deadline" type="date" label={t('partner.form.deadline')} value={f.deadline} onChange={(e) => set('deadline', e.target.value)} />
          <Field id="ptn-expires" type="date" label={t('partner.form.expires')} value={f.expires} onChange={(e) => set('expires', e.target.value)} />
        </fieldset>

        <fieldset className="ptn-fieldset" disabled={readOnly || busy}>
          <legend>{t('partner.form.benefits')}</legend>
          {err('benefits') && <p className="error" role="alert">{err('benefits')}</p>}
          {f.benefits.map((b, i) => (
            <div key={i} className="ptn-ev">
              <Field id={`ptn-b-text-${i}`} label={t('partner.form.benefitText', { n: i + 1 })} value={b.text} onChange={(e) => setBenefit(i, { text: e.target.value })} />
              <Field id={`ptn-b-amt-${i}`} type="number" inputMode="numeric" min={0} label={t('partner.form.benefitAmount', { n: i + 1 })} value={b.amount} onChange={(e) => setBenefit(i, { amount: e.target.value })} />
              <div className="field">
                <label htmlFor={`ptn-b-per-${i}`}>{t('partner.form.benefitPeriod', { n: i + 1 })}</label>
                <select id={`ptn-b-per-${i}`} value={b.period} onChange={(e) => setBenefit(i, { period: e.target.value === 'month' || e.target.value === 'year' || e.target.value === 'one_time' ? e.target.value : '' })}>
                  <option value="">{t('partner.form.periodNone')}</option>
                  <option value="month">{t('partner.form.periods.month')}</option>
                  <option value="year">{t('partner.form.periods.year')}</option>
                  <option value="one_time">{t('partner.form.periods.one_time')}</option>
                </select>
              </div>
              <button type="button" className="btn btn--secondary" onClick={() => set('benefits', f.benefits.filter((_, j) => j !== i))}>
                {t('partner.form.removeBenefit', { n: i + 1 })}
              </button>
            </div>
          ))}
          <button type="button" className="btn btn--secondary" onClick={() => set('benefits', [...f.benefits, { text: '', amount: '', period: '' }])}>
            {t('partner.form.addBenefit')}
          </button>
        </fieldset>

        {!readOnly && (
          <div className="stack">
            <button type="submit" className="btn btn--big" disabled={busy}>
              {busy ? t('partner.saving') : t('partner.form.saveDraft')}
            </button>
            <button type="button" className="btn btn--secondary" disabled={busy} onClick={() => void save(true)}>
              {t('partner.sub.submit')}
            </button>
          </div>
        )}
        <Msg error={error} ok={ok} />
      </form>
    </>
  )
}
