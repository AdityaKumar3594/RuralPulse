import { useId } from 'react'
import { useTranslation } from 'react-i18next'
import type { TFunction } from 'i18next'
import { VERIFIED_FIELDS, type Evidence, type VerifiedField } from './types'

export interface VerificationValue {
  fields: VerifiedField[]
  evidence: Evidence[]
}

export const emptyVerification: VerificationValue = { fields: [], evidence: [{ url: '', note: '' }] }

export function usedEvidence(v: VerificationValue): Evidence[] {
  return v.evidence
    .map((e) => ({ url: e.url.trim(), note: e.note.trim() }))
    .filter((e) => e.url || e.note)
}

/** Client-side checks that mirror the server's; the server stays the authority. */
export function checkVerification(v: VerificationValue, t: TFunction): string | null {
  const ev = usedEvidence(v)
  if (v.fields.length > 0 && ev.length === 0) return t('admin.errors.evidence_required')
  for (const e of ev) {
    if (!e.url.startsWith('https://')) return t('admin.errors.url_must_be_https')
    if (!e.note) return t('admin.verify.noteMissing')
  }
  return null
}

export function VerificationForm({
  value,
  onChange,
}: {
  value: VerificationValue
  onChange: (v: VerificationValue) => void
}) {
  const { t } = useTranslation()
  const uid = useId()

  const toggle = (f: VerifiedField) =>
    onChange({
      ...value,
      fields: value.fields.includes(f) ? value.fields.filter((x) => x !== f) : [...value.fields, f],
    })
  const setEv = (i: number, patch: Partial<Evidence>) =>
    onChange({ ...value, evidence: value.evidence.map((e, j) => (j === i ? { ...e, ...patch } : e)) })

  return (
    <div className="adm-form">
      <fieldset className="adm-fieldset">
        <legend>{t('admin.verify.title')}</legend>
        <p className="adm-claims">{t('admin.verify.warning')}</p>
        {VERIFIED_FIELDS.map((f) => (
          <label key={f} className="adm-check">
            <input type="checkbox" checked={value.fields.includes(f)} onChange={() => toggle(f)} />
            <span>{t(`admin.verify.fields.${f}`)}</span>
          </label>
        ))}
      </fieldset>
      <fieldset className="adm-fieldset">
        <legend>{t('admin.verify.evidenceTitle')}</legend>
        <p className="muted">{t('admin.verify.evidenceHint')}</p>
        {value.evidence.map((e, i) => (
          <div key={i} className="adm-ev">
            <div className="field">
              <label htmlFor={`${uid}-u${i}`}>{t('admin.verify.evidenceUrl', { n: i + 1 })}</label>
              <input id={`${uid}-u${i}`} type="url" inputMode="url" placeholder="https://" value={e.url} onChange={(ev) => setEv(i, { url: ev.target.value })} />
            </div>
            <div className="field">
              <label htmlFor={`${uid}-n${i}`}>{t('admin.verify.evidenceNote', { n: i + 1 })}</label>
              <input id={`${uid}-n${i}`} type="text" maxLength={300} value={e.note} onChange={(ev) => setEv(i, { note: ev.target.value })} />
            </div>
            {value.evidence.length > 1 && (
              <button type="button" className="btn btn--secondary" onClick={() => onChange({ ...value, evidence: value.evidence.filter((_, j) => j !== i) })}>
                {t('admin.verify.removeEvidence', { n: i + 1 })}
              </button>
            )}
          </div>
        ))}
        <button type="button" className="btn btn--secondary" onClick={() => onChange({ ...value, evidence: [...value.evidence, { url: '', note: '' }] })}>
          {t('admin.verify.addEvidence')}
        </button>
      </fieldset>
    </div>
  )
}
