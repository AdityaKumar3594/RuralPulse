import type { Period, SubmissionPayload } from './types'

export interface BenefitRow {
  text: string
  amount: string
  period: '' | Period
}

export interface FormState {
  kind: string
  titleEn: string
  titleTa: string
  summaryEn: string
  summaryTa: string
  url: string
  keywords: string
  level: 'national' | 'state'
  states: string
  stages: string[]
  minAge: string
  maxAge: string
  income: string
  eligText: string
  documents: string
  deadline: string
  expires: string
  benefits: BenefitRow[]
}

export const emptyForm: FormState = {
  kind: 'scholarship',
  titleEn: '',
  titleTa: '',
  summaryEn: '',
  summaryTa: '',
  url: '',
  keywords: '',
  level: 'national',
  states: '',
  stages: [],
  minAge: '',
  maxAge: '',
  income: '',
  eligText: '',
  documents: '',
  deadline: '',
  expires: '',
  benefits: [],
}

type Obj = Record<string, unknown>
const isObj = (v: unknown): v is Obj => typeof v === 'object' && v !== null && !Array.isArray(v)
const s = (v: unknown): string => (typeof v === 'string' || typeof v === 'number' ? String(v) : '')
const arr = (v: unknown): unknown[] => (Array.isArray(v) ? v : [])
const loc = (v: unknown, k: 'en' | 'ta'): string => (isObj(v) ? s(v[k]) : '')

/** Reads a stored payload defensively into editable form fields. */
export function toForm(p: Obj): FormState {
  const scope = isObj(p.scope) ? p.scope : {}
  const el = isObj(p.eligibility) ? p.eligibility : {}
  return {
    kind: s(p.kind) || 'scholarship',
    titleEn: loc(p.title, 'en'),
    titleTa: loc(p.title, 'ta'),
    summaryEn: loc(p.summary, 'en'),
    summaryTa: loc(p.summary, 'ta'),
    url: s(p.url),
    keywords: arr(p.keywords).map(s).join(', '),
    level: scope.level === 'state' ? 'state' : 'national',
    states: arr(scope.states).map(s).join(', '),
    stages: arr(el.education_stages).map(s),
    minAge: s(el.min_age),
    maxAge: s(el.max_age),
    income: s(el.max_family_income_inr_per_year),
    eligText: loc(el.text, 'en'),
    documents: arr(p.required_documents).map(s).join('\n'),
    deadline: s(p.application_deadline),
    expires: s(p.expires_on),
    benefits: arr(p.benefits).map((b) => {
      const o = isObj(b) ? b : {}
      const period = s(o.period)
      return {
        text: loc(o.text, 'en'),
        amount: s(o.amount_inr),
        period: period === 'month' || period === 'year' || period === 'one_time' ? period : '',
      }
    }),
  }
}

const splitList = (v: string, sep: RegExp): string[] =>
  v
    .split(sep)
    .map((x) => x.trim())
    .filter(Boolean)
const num = (v: string): number | null => (v.trim() === '' ? null : Number(v))

function localized(en: string, ta: string) {
  return ta.trim() ? { en: en.trim(), ta: ta.trim() } : { en: en.trim() }
}

export function toPayload(f: FormState): SubmissionPayload {
  const hasElig =
    f.stages.length > 0 || f.minAge.trim() || f.maxAge.trim() || f.income.trim() || f.eligText.trim()
  return {
    kind: f.kind,
    title: localized(f.titleEn, f.titleTa),
    summary: localized(f.summaryEn, f.summaryTa),
    url: f.url.trim(),
    keywords: splitList(f.keywords, /,/),
    scope: {
      level: f.level,
      states: f.level === 'state' ? splitList(f.states, /,/) : [],
    },
    eligibility: hasElig
      ? {
          education_stages: f.stages.length ? f.stages : null,
          min_age: num(f.minAge),
          max_age: num(f.maxAge),
          max_family_income_inr_per_year: num(f.income),
          text: f.eligText.trim() ? { en: f.eligText.trim() } : null,
        }
      : null,
    required_documents: splitList(f.documents, /\n/),
    application_deadline: f.deadline || null,
    expires_on: f.expires || null,
    benefits: f.benefits
      .filter((b) => b.text.trim())
      .map((b) => ({
        text: { en: b.text.trim() },
        amount_inr: num(b.amount),
        period: b.period || null,
      })),
  }
}

/** Returns an i18n key (under partner.form.errors) for the first problem, or null. */
export function validate(f: FormState): { field: string; key: string } | null {
  if (!f.titleEn.trim()) return { field: 'titleEn', key: 'titleRequired' }
  if (!f.summaryEn.trim()) return { field: 'summaryEn', key: 'summaryRequired' }
  if (!f.url.trim().startsWith('https://')) return { field: 'url', key: 'urlHttps' }
  if (f.level === 'state' && splitList(f.states, /,/).length === 0) return { field: 'states', key: 'statesRequired' }
  for (const [field, v] of [
    ['minAge', f.minAge],
    ['maxAge', f.maxAge],
    ['income', f.income],
  ] as const) {
    if (v.trim() !== '' && (!Number.isInteger(Number(v)) || Number(v) < 0)) return { field, key: 'numberInvalid' }
  }
  if (f.benefits.some((b) => b.amount.trim() !== '' && (!Number.isInteger(Number(b.amount)) || Number(b.amount) < 0)))
    return { field: 'benefits', key: 'numberInvalid' }
  return null
}
