import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'

type Obj = Record<string, unknown>
const isObj = (v: unknown): v is Obj => typeof v === 'object' && v !== null && !Array.isArray(v)
const str = (v: unknown): string => (typeof v === 'string' || typeof v === 'number' ? String(v) : '')
const list = (v: unknown): unknown[] => (Array.isArray(v) ? v : [])

function localized(v: unknown): string {
  if (!isObj(v)) return ''
  return [v.en ? `EN: ${str(v.en)}` : '', v.ta ? `TA: ${str(v.ta)}` : ''].filter(Boolean).join(' / ')
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <>
      <dt>{label}</dt>
      <dd>{children}</dd>
    </>
  )
}

/** The partner's proposed record, shown completely so the reviewer sees every claim. */
export function PayloadView({ payload }: { payload: Obj }) {
  const { t } = useTranslation()
  const none = <span className="muted">{t('admin.payload.none')}</span>
  const scope = isObj(payload.scope) ? payload.scope : {}
  const elig = isObj(payload.eligibility) ? payload.eligibility : null
  const docs = list(payload.required_documents).map(str)
  const benefits = list(payload.benefits)
  const keywords = list(payload.keywords).map(str)
  const url = str(payload.url)

  return (
    <dl className="adm-dl">
      <Row label={t('admin.payload.kind')}>{str(payload.kind)}</Row>
      <Row label={t('admin.payload.title')}>{localized(payload.title) || none}</Row>
      <Row label={t('admin.payload.summary')}>{localized(payload.summary) || none}</Row>
      <Row label={t('admin.payload.url')}>
        {url.startsWith('https://') ? (
          <a href={url} target="_blank" rel="noopener noreferrer">
            {url}
          </a>
        ) : (
          url || none
        )}
      </Row>
      <Row label={t('admin.payload.keywords')}>{keywords.length ? keywords.join(', ') : none}</Row>
      <Row label={t('admin.payload.scope')}>
        {scope.level === 'state'
          ? t('admin.payload.scopeState', { states: list(scope.states).map(str).join(', ') })
          : t('admin.payload.scopeNational')}
      </Row>
      <Row label={t('admin.payload.eligibility')}>
        {elig ? (
          <ul>
            {list(elig.education_stages).length > 0 && (
              <li>{t('admin.payload.stages', { v: list(elig.education_stages).map(str).join(', ') })}</li>
            )}
            {elig.min_age != null && <li>{t('admin.payload.minAge', { v: str(elig.min_age) })}</li>}
            {elig.max_age != null && <li>{t('admin.payload.maxAge', { v: str(elig.max_age) })}</li>}
            {elig.max_family_income_inr_per_year != null && (
              <li>{t('admin.payload.income', { v: str(elig.max_family_income_inr_per_year) })}</li>
            )}
            {localized(elig.text) && <li>{localized(elig.text)}</li>}
          </ul>
        ) : (
          none
        )}
      </Row>
      <Row label={t('admin.payload.benefits')}>
        {benefits.length ? (
          <ul>
            {benefits.map((b, i) => {
              const o = isObj(b) ? b : {}
              const extra = [o.amount_inr != null ? `₹${str(o.amount_inr)}` : '', str(o.period)].filter(Boolean).join(' / ')
              return (
                <li key={i}>
                  {localized(o.text)}
                  {extra && ` (${extra})`}
                </li>
              )
            })}
          </ul>
        ) : (
          none
        )}
      </Row>
      <Row label={t('admin.payload.deadline')}>{str(payload.application_deadline) || none}</Row>
      <Row label={t('admin.payload.expires')}>{str(payload.expires_on) || none}</Row>
      <Row label={t('admin.payload.documents')}>
        {docs.length ? (
          <ul>
            {docs.map((d, i) => (
              <li key={i}>{d}</li>
            ))}
          </ul>
        ) : (
          none
        )}
      </Row>
    </dl>
  )
}
