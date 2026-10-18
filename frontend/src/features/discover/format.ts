import type { TFunction } from 'i18next'
import { ApiError } from '../../api/client'
import { errorMessage } from '../../api/errors'

/** Only plain web addresses are ever turned into links. */
export function safeHref(url: string | null | undefined): string | null {
  if (!url) return null
  try {
    const u = new URL(url)
    return u.protocol === 'https:' || u.protocol === 'http:' ? u.href : null
  } catch {
    return null
  }
}

/** "2026-10-18" -> "18 Oct 2026" (or Tamil). Falls back to the raw text. */
export function formatDate(iso: string | null | undefined, lang: string): string {
  if (!iso) return ''
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso)
  if (!m) return iso
  const d = new Date(Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3])))
  return d.toLocaleDateString(lang === 'ta' ? 'ta-IN' : 'en-IN', {
    timeZone: 'UTC',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

/** Translates `prefix.value`, or shows the value in plain words when we have no translation yet. */
export function enumText(t: TFunction, prefix: string, value: string): string {
  return t(`${prefix}.${value}`, { defaultValue: value.replace(/_/g, ' ') })
}

/** Like errorMessage(), plus our own wording for the "not found" style error codes. */
export function apiMessage(err: unknown, t: TFunction): string {
  if (err instanceof ApiError && err.detail) {
    const own = t(`discover.errors.${err.detail}`, { defaultValue: '' })
    if (own) return own
  }
  return errorMessage(err, t)
}
