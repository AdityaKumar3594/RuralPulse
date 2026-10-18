import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { ErrorLine, useAction } from '../support/shared'
import { addAssistedAnswer, addObservation } from './api'
import { FIELDS, fieldMeta, parseValue } from './fields'

function KeySelect({ id, value, onChange }: { id: string; value: string; onChange: (k: string) => void }) {
  const { t } = useTranslation()
  return (
    <div className="sp-field">
      <label htmlFor={id}>{t('facilitator.form.field')}</label>
      <select id={id} value={value} onChange={(e) => onChange(e.target.value)}>
        {FIELDS.map((f) => (
          <option key={f.key} value={f.key}>
            {t(`facilitator.fields.${f.key}`)}
          </option>
        ))}
      </select>
    </div>
  )
}

function ValueInput({
  id,
  fieldKey,
  value,
  onChange,
  disabled,
  error,
}: {
  id: string
  fieldKey: string
  value: string
  onChange: (v: string) => void
  disabled?: boolean
  error?: string
}) {
  const { t } = useTranslation()
  const meta = fieldMeta(fieldKey)
  const hintId = `${id}-hint`
  const hint =
    meta.kind === 'list'
      ? t('facilitator.form.hintList')
      : meta.kind === 'int'
        ? t('facilitator.form.hintInt', { min: meta.min ?? 0, max: meta.max ?? 0 })
        : ''
  return (
    <div className="sp-field">
      <label htmlFor={id}>{t('facilitator.form.value')}</label>
      {hint && (
        <p id={hintId} className="muted">
          {hint}
        </p>
      )}
      {meta.kind === 'enum' ? (
        <select id={id} value={value} disabled={disabled} onChange={(e) => onChange(e.target.value)} aria-describedby={error ? `${id}-err` : undefined}>
          <option value="">{t('facilitator.form.choose')}</option>
          {meta.options?.map((o) => (
            <option key={o} value={o}>
              {t(`facilitator.enum.${meta.key}.${o}`)}
            </option>
          ))}
        </select>
      ) : (
        <input
          id={id}
          value={value}
          disabled={disabled}
          inputMode={meta.kind === 'int' ? 'numeric' : undefined}
          onChange={(e) => onChange(e.target.value)}
          aria-invalid={error ? true : undefined}
          aria-describedby={[hint ? hintId : '', error ? `${id}-err` : ''].filter(Boolean).join(' ') || undefined}
        />
      )}
      {error && (
        <p id={`${id}-err`} className="error" role="alert">
          {error}
        </p>
      )}
    </div>
  )
}

export function ObservationForm({ studentId, onSaved }: { studentId: string; onSaved: () => void }) {
  const { t } = useTranslation()
  const { run, busy, error } = useAction()
  const [key, setKey] = useState(FIELDS[0].key)
  const [value, setValue] = useState('')
  const [provenance, setProvenance] = useState<'observed' | 'hypothesis'>('observed')
  const [basis, setBasis] = useState('')
  const [verified, setVerified] = useState(false)
  const [problems, setProblems] = useState<{ value?: string; basis?: string }>({})
  const [done, setDone] = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setDone(false)
    const parsed = parseValue(fieldMeta(key), value)
    const found: typeof problems = {}
    if (parsed === null) found.value = t('facilitator.form.errValue')
    if (basis.trim().length < 3) found.basis = t('facilitator.form.errBasis')
    setProblems(found)
    if (parsed === null || found.basis) return
    const ok = await run(async () => {
      await addObservation(studentId, { key, value: parsed, provenance, basis: basis.trim(), verified })
      return true
    })
    if (ok) {
      setDone(true)
      setValue('')
      setBasis('')
      setVerified(false)
      onSaved()
    }
  }

  return (
    <form className="sp-box sp-form" onSubmit={submit} noValidate aria-labelledby="fo-title">
      <h3 id="fo-title">{t('facilitator.obs.title')}</h3>
      <p className="muted">{t('facilitator.obs.intro')}</p>
      <KeySelect id="fo-key" value={key} onChange={(k) => { setKey(k); setValue('') }} />
      <ValueInput id="fo-value" fieldKey={key} value={value} onChange={setValue} error={problems.value} />
      <fieldset className="sp-field" style={{ border: 0, padding: 0, margin: '0 0 1rem' }}>
        <legend className="sp-label">{t('facilitator.obs.kind')}</legend>
        {(['observed', 'hypothesis'] as const).map((p) => (
          <label key={p} className="sp-radio">
            <input type="radio" name="fo-prov" checked={provenance === p} onChange={() => setProvenance(p)} />
            <span>{t(`facilitator.obs.${p}`)}</span>
          </label>
        ))}
      </fieldset>
      <div className="sp-field">
        <label htmlFor="fo-basis">{t('facilitator.obs.basis')}</label>
        <p className="muted">{t('facilitator.obs.basisHint')}</p>
        <textarea id="fo-basis" value={basis} maxLength={500} onChange={(e) => setBasis(e.target.value)} aria-invalid={problems.basis ? true : undefined} />
        {problems.basis && <p className="error" role="alert">{problems.basis}</p>}
      </div>
      <div className="sp-field">
        <label className="check">
          <input type="checkbox" checked={verified} onChange={(e) => setVerified(e.target.checked)} />
          <span>{t('facilitator.obs.verified')}</span>
        </label>
      </div>
      <ErrorLine message={error} />
      {done && <p role="status" className="sp-ok">{t('facilitator.obs.saved')}</p>}
      <button type="submit" className="btn" disabled={busy}>
        {busy ? t('common.loading') : t('facilitator.obs.save')}
      </button>
    </form>
  )
}

export function AssistedForm({ studentId, onSaved }: { studentId: string; onSaved: () => void }) {
  const { t } = useTranslation()
  const { run, busy, error } = useAction()
  const [key, setKey] = useState(FIELDS[0].key)
  const [value, setValue] = useState('')
  const [unknown, setUnknown] = useState(false)
  const [problem, setProblem] = useState<string | undefined>()
  const [done, setDone] = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setDone(false)
    let body: { key: string; value?: unknown; unknown?: boolean }
    if (unknown) body = { key, unknown: true }
    else {
      const parsed = parseValue(fieldMeta(key), value)
      if (parsed === null) {
        setProblem(t('facilitator.form.errValue'))
        return
      }
      body = { key, value: parsed }
    }
    setProblem(undefined)
    const ok = await run(async () => {
      await addAssistedAnswer(studentId, body)
      return true
    })
    if (ok) {
      setDone(true)
      setValue('')
      setUnknown(false)
      onSaved()
    }
  }

  return (
    <form className="sp-box sp-form" onSubmit={submit} noValidate aria-labelledby="fa-title">
      <h3 id="fa-title">{t('facilitator.assisted.title')}</h3>
      <p className="muted">{t('facilitator.assisted.intro')}</p>
      <KeySelect id="fa-key" value={key} onChange={(k) => { setKey(k); setValue('') }} />
      <ValueInput id="fa-value" fieldKey={key} value={value} onChange={setValue} disabled={unknown} error={problem} />
      <div className="sp-field">
        <label className="check">
          <input type="checkbox" checked={unknown} onChange={(e) => setUnknown(e.target.checked)} />
          <span>{t('facilitator.assisted.unknown')}</span>
        </label>
      </div>
      <ErrorLine message={error} />
      {done && <p role="status" className="sp-ok">{t('facilitator.assisted.saved')}</p>}
      <button type="submit" className="btn" disabled={busy}>
        {busy ? t('common.loading') : t('facilitator.assisted.save')}
      </button>
    </form>
  )
}
