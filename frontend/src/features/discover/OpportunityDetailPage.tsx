import { useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router'
import { useAuth } from '../../auth/AuthContext'
import { SaveOpportunityButton } from '../applications/SaveOpportunityButton'
import { EligibilityCheck } from '../eligibility/EligibilityCheck'
import { getOpportunity } from './api'
import { ExternalLink, FlagList, FreshnessChip, Status, VerificationDetails } from './Badges'
import { apiMessage, enumText, formatDate, safeHref } from './format'
import type { Opportunity } from './types'
import { useLoad } from './useLoad'
import './shared.css'

/** Kinds the eligibility engine can check (mirrors the backend's pathway.CHECKABLE_KINDS). */
const CHECKABLE_KINDS = ['scheme', 'scholarship', 'apprenticeship', 'internship', 'job']

export function OpportunityDetailPage() {
  const { slug = '' } = useParams()
  const { t, i18n } = useTranslation()
  const lang = i18n.language
  const load = useCallback((o: { signal: AbortSignal }) => getOpportunity(slug, lang, o), [slug, lang])
  const { state, reload } = useLoad(load)

  return (
    <>
      <p>
        <Link to="/search">{t('discover.backToSearch')}</Link>
      </p>
      {state.phase === 'loading' && <Status />}
      {state.phase === 'error' && <Status error={apiMessage(state.error, t)} onRetry={reload} />}
      {state.phase === 'ready' && <OpportunityView opp={state.data} />}
    </>
  )
}

function OpportunityView({ opp }: { opp: Opportunity }) {
  const { t, i18n } = useTranslation()
  const { user } = useAuth()
  const date = (d: string | null) => formatDate(d, i18n.language)
  const el = opp.eligibility
  const hasEligibility =
    el != null &&
    (el.education_stages?.length || el.min_age != null || el.max_age != null || el.max_family_income_inr_per_year != null || el.text || el.other_criteria?.length)
  const states = opp.scope.level === 'state' ? (opp.scope.states ?? []) : []
  const canCheck = CHECKABLE_KINDS.includes(opp.kind) && el != null

  return (
    <article>
      <h1>{opp.title ?? opp.slug}</h1>
      <div className="tags">
        <span className="tag tag--info">{enumText(t, 'discover.kind', opp.kind)}</span>
        <FreshnessChip value={opp.freshness} />
      </div>
      <p>{t('discover.opp.provider', { name: opp.provider })}</p>
      {opp.summary && <p className="lead">{opp.summary}</p>}
      {opp.language_fallback && <p className="muted">{t('discover.languageFallback')}</p>}
      <p className="muted">{t(`discover.freshnessHelp.${opp.freshness}`)}</p>
      <FlagList flags={opp.flags} />

      <p>
        {safeHref(opp.url) ? (
          <ExternalLink href={opp.url} className="btn btn--big">
            {t('discover.opp.officialLink')}
          </ExternalLink>
        ) : (
          t('discover.opp.noLink')
        )}
      </p>

      {opp.benefits.length > 0 && (
        <section className="section" aria-labelledby="o-ben">
          <h2 id="o-ben">{t('discover.opp.benefitsTitle')}</h2>
          <ul>
            {opp.benefits.map((b, i) => (
              <li key={i}>
                {b.text}
                {b.amount_inr != null && (
                  <>
                    {' '}
                    ({t('discover.opp.benefitAmount', { amount: b.amount_inr.toLocaleString('en-IN') })}
                    {b.period ? ` ${t(`discover.opp.period.${b.period}`)}` : ''})
                  </>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      {(opp.application_deadline || opp.expires_on) && (
        <section className="section" aria-labelledby="o-dates">
          <h2 id="o-dates">{t('discover.opp.datesTitle')}</h2>
          <ul className="plain-list">
            {opp.application_deadline && <li>{t('discover.opp.deadline', { date: date(opp.application_deadline) })}</li>}
            {opp.expires_on && <li>{t('discover.opp.expires', { date: date(opp.expires_on) })}</li>}
          </ul>
        </section>
      )}

      {opp.required_documents.length > 0 && (
        <section className="section" aria-labelledby="o-docs">
          <h2 id="o-docs">{t('discover.opp.documentsTitle')}</h2>
          <ul>{opp.required_documents.map((d) => <li key={d}>{d}</li>)}</ul>
        </section>
      )}

      {el && hasEligibility && (
        <section className="section" aria-labelledby="o-elig">
          <h2 id="o-elig">{t('discover.opp.eligibilityTitle')}</h2>
          <ul>
            {el.text && <li>{el.text}</li>}
            {el.education_stages && el.education_stages.length > 0 && (
              <li>
                {t('discover.opp.stages', {
                  stages: el.education_stages.map((s) => enumText(t, 'discover.stage', s)).join(', '),
                })}
              </li>
            )}
            {el.min_age != null && <li>{t('discover.opp.minAge', { age: el.min_age })}</li>}
            {el.max_age != null && <li>{t('discover.opp.maxAge', { age: el.max_age })}</li>}
            {el.max_family_income_inr_per_year != null && (
              <li>{t('discover.opp.income', { amount: el.max_family_income_inr_per_year.toLocaleString('en-IN') })}</li>
            )}
            {(el.other_criteria ?? []).filter(Boolean).map((c) => (
              <li key={c}>{t('discover.opp.other', { rule: c })}</li>
            ))}
          </ul>
          <p className="muted">{states.length > 0 ? t('discover.opp.scopeState', { states: states.join(', ') }) : t('discover.opp.scopeNational')}</p>
        </section>
      )}

      <section className="section" aria-labelledby="o-src">
        <h2 id="o-src">{t('discover.opp.sourceTitle')}</h2>
        <p>{t('discover.opp.source', { name: opp.source.name, publisher: opp.source.publisher })}</p>
      </section>

      <section className="section" aria-labelledby="o-ver">
        <h2 id="o-ver">{t('discover.opp.checkTitle')}</h2>
        <VerificationDetails verification={opp.verification} />
      </section>

      {user?.role === 'student' && (
        <section className="section" aria-labelledby="o-can">
          <h2 id="o-can">{t('discover.opp.canApplyTitle')}</h2>
          {canCheck ? (
            <>
              <p>{t('discover.opp.canApplyIntro')}</p>
              <EligibilityCheck slug={opp.slug} />
            </>
          ) : (
            <p className="note" role="note">
              {CHECKABLE_KINDS.includes(opp.kind) ? t('discover.opp.noRules') : t('discover.opp.notAvailableKind')}
            </p>
          )}
          <SaveOpportunityButton slug={opp.slug} />
        </section>
      )}
      {!user && canCheck && (
        <p className="note">
          {t('discover.opp.loginToCheck')} <Link to="/login">{t('discover.opp.login')}</Link>
        </p>
      )}
    </article>
  )
}
