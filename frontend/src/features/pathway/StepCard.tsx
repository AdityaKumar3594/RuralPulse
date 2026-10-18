import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'
import { ExternalLink, FreshnessChip, VerificationTag } from '../discover/Badges'
import { enumText } from '../discover/format'
import type { Step, StepStatus } from './types'

const STATUSES: StepStatus[] = ['not_started', 'in_progress', 'done']

interface Props {
  step: Step
  /** Titles of the steps this one comes after. */
  afterTitles: string[]
  /** True when every step this one depends on is done. */
  ready: boolean
  busy: boolean
  number?: number
  message?: { kind: 'ok' | 'error'; text: string } | null
  onChange: (status: StepStatus) => void
}

export function StepCard({ step, afterTitles, ready, busy, number, message, onChange }: Props) {
  const { t } = useTranslation()
  const title = step.title ?? step.id
  const gid = `step-${step.id.replace(/[^a-zA-Z0-9_-]/g, '_')}`
  const r = step.resource
  return (
    <li className={`step${step.status === 'done' ? ' step--done' : ''}`}>
      {number != null && <p className="step__no">{t('pathway.stepNumber', { n: number })}</p>}
      <h3>{title}</h3>
      <div className="tags">
        <span className="tag">{enumText(t, 'pathway.type', step.type)}</span>
        <span className="tag tag--info">{enumText(t, 'pathway.level', step.requirement_level)}</span>
      </div>
      {afterTitles.length > 0 && <p className="muted">{t('pathway.after', { steps: afterTitles.join(', ') })}</p>}
      {step.skills && step.skills.length > 0 && <p>{t('pathway.skillsList', { skills: step.skills.join(', ') })}</p>}
      {step.type === 'check_in' && (
        <p>
          <Link to="/profile">{t('pathway.updateProfile')}</Link>
        </p>
      )}
      {r && (
        <div className="resource">
          <h4>{t('pathway.resource.title')}</h4>
          <p>
            <strong>{r.title ?? r.slug}</strong>
          </p>
          <div className="tags">
            <span className="tag">{enumText(t, 'discover.kind', r.kind)}</span>
            <FreshnessChip value={r.freshness} />
            <VerificationTag status={r.verification_status === 'verified' ? 'verified' : 'unverified'} />
          </div>
          {r.source && <p className="muted">{t('pathway.resource.source', { name: r.source })}</p>}
          <p>
            <Link to={`/opportunities/${encodeURIComponent(r.slug)}`}>{t('pathway.resource.details')}</Link>
          </p>
          {r.check_eligibility && (
            <p>
              <Link to={`/eligibility/${encodeURIComponent(r.slug)}`}>{t('pathway.resource.check')}</Link>
            </p>
          )}
          <p>
            <ExternalLink href={r.url}>{t('pathway.resource.open')}</ExternalLink>
          </p>
        </div>
      )}
      <fieldset className="status-group" aria-describedby={ready ? undefined : `${gid}-wait`}>
        <legend>{t('pathway.statusLabel', { title })}</legend>
        <div className="status-group__options">
          {STATUSES.map((s) => (
            <button
              key={s}
              type="button"
              className="btn status-btn"
              aria-pressed={step.status === s}
              disabled={busy || (s !== 'not_started' && s !== step.status && !ready)}
              onClick={() => step.status !== s && onChange(s)}
            >
              {t(`pathway.status.${s}`)}
            </button>
          ))}
        </div>
      </fieldset>
      {!ready && (
        <p id={`${gid}-wait`} className="muted">
          {t('pathway.waiting')}
        </p>
      )}
      {message && (
        <p role={message.kind === 'error' ? 'alert' : 'status'} className={message.kind === 'error' ? 'error' : 'muted'}>
          {message.text}
        </p>
      )}
    </li>
  )
}
