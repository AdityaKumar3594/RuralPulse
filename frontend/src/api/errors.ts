import type { TFunction } from 'i18next'
import { ApiError } from './client'

/** Turns any failure into a short, translated message for the student. */
export function errorMessage(err: unknown, t: TFunction): string {
  if (err instanceof ApiError) {
    if (err.kind === 'network' || err.kind === 'timeout') return t('errors.network')
    if (err.detail) {
      const key = `errors.detail.${err.detail}`
      return t(key, { defaultValue: t('errors.generic') })
    }
  }
  return t('errors.generic')
}
