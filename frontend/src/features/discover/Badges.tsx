import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { enumText, formatDate, safeHref } from './format'
import type { Freshness, Verification } from './types'
import './shared.css'

const ICON: Record<Freshness, string> = { fresh: '✓', stale: '!', expired: '✕', unverified: '?' }

/** Freshness as a word plus a symbol, so it never depends on colour alone. */
export function FreshnessChip({ value }: { value: Freshness | null | undefined }) {
  const { t } = useTranslation()
  if (!value) return null
  return (
    <span className={`tag tag--${value}`} title={t(`discover.freshnessHelp.${value}`)}>
      <span aria-hidden="true">{ICON[value]} </span>
      {t(`discover.freshness.${value}`)}
    </span>
  )
}

export function VerificationTag({ status }: { status: 'verified' | 'unverified' }) {
  const { t } = useTranslation()
  return (
    <span className={`tag tag--${status === 'verified' ? 'verified' : 'draft'}`}>
      <span aria-hidden="true">{status === 'verified' ? '✓' : '?'} </span>
      {t(`discover.verification.${status}`)}
    </span>
  )
}

/** Plain-language caveats from the server. Unknown codes are shown as readable words. */
export function FlagList({ flags, prefix = 'discover.flags' }: { flags: string[]; prefix?: string }) {
  const { t } = useTranslation()
  if (flags.length === 0) return null
  return (
    <ul className="flags">
      {flags.map((f) => (
        <li key={f}>{enumText(t, prefix, f)}</li>
      ))}
    </ul>
  )
}

export function ExternalLink({ href, className, children }: { href: string | null; className?: string; children: ReactNode }) {
  const { t } = useTranslation()
  const safe = safeHref(href)
  if (!safe) return null
  return (
    <a href={safe} target="_blank" rel="noopener noreferrer" className={className}>
      {children}
      <span className="visually-hidden"> ({t('discover.external')})</span>
    </a>
  )
}

export function VerificationDetails({ verification }: { verification: Verification }) {
  const { t, i18n } = useTranslation()
  const fields = verification.verified_fields.map((f) => enumText(t, 'discover.verifiedField', f)).join(', ')
  return (
    <ul className="plain-list">
      <li>
        <VerificationTag status={verification.status} />
      </li>
      {fields && <li>{t('discover.verification.fields', { fields })}</li>}
      {verification.verified_at && (
        <li>{t('discover.verification.checkedOn', { date: formatDate(verification.verified_at, i18n.language) })}</li>
      )}
      <li>{verification.human_reviewed ? t('discover.verification.reviewed') : t('discover.verification.notReviewed')}</li>
    </ul>
  )
}

/** Shared loading / error-with-retry wrapper for async views. */
export function Status({ error, onRetry, loading }: { error?: string | null; onRetry?: () => void; loading?: string }) {
  const { t } = useTranslation()
  if (error)
    return (
      <div role="alert" className="status-box">
        <p className="error">{error}</p>
        {onRetry && (
          <button type="button" className="btn" onClick={onRetry}>
            {t('common.retry')}
          </button>
        )}
      </div>
    )
  return <p role="status">{loading ?? t('common.loading')}</p>
}
