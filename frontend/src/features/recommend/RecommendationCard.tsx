import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'
import { ExplanationPanel } from '../../components/ExplanationPanel'
import { ExternalLink, FlagList, FreshnessChip, VerificationTag } from '../discover/Badges'
import { enumText } from '../discover/format'
import { BuildPathwayButton } from '../pathway/BuildPathwayButton'
import type { NextAction, Recommendation } from './types'
import '../discover/shared.css'
import './recommend.css'

const stageText = (t: ReturnType<typeof useTranslation>['t'], s: string | null) => (s ? enumText(t, 'discover.stage', s) : '')

export function RecommendationCard({ item, runId }: { item: Recommendation; runId: string }) {
  const { t } = useTranslation()
  const name = item.career.title ?? item.slug
  const isMatch = item.kind === 'match'
  const stage = item.stage
  const hid = `reco-${item.slug}`
  return (
    <li className={`reco reco--${item.kind}`} aria-labelledby={hid}>
      <h3 id={hid}>{name}</h3>
      <div className="tags">
        <span className="tag">{enumText(t, 'discover.family', item.family)}</span>
        {isMatch && item.match_level ? (
          <span className={`tag tag--${item.match_level}`}>{t(`recommend.level.${item.match_level}`)}</span>
        ) : (
          <span className="tag tag--info">{t('recommend.exploreBadge')}</span>
        )}
      </div>
      {item.career.description && <p>{item.career.description}</p>}
      {item.language_fallback && <p className="muted">{t('discover.languageFallback')}</p>}

      {isMatch && item.reasons.length > 0 && (
        <>
          <h4>{t('recommend.reasonsTitle')}</h4>
          <ul>
            {item.reasons.map((r, i) => (
              <li key={i}>
                {t(r.basis === 'observed' ? 'recommend.reasonObserved' : 'recommend.reasonReported', {
                  term: r.student_term,
                  field: enumText(t, 'recommend.termField', r.student_field),
                  text: r.matched_text,
                  careerField: enumText(t, 'recommend.careerField', r.career_field),
                })}
              </li>
            ))}
          </ul>
          <p className="muted">{t('recommend.levelNote')}</p>
        </>
      )}

      <h4>{t('recommend.stageTitle')}</h4>
      <p>
        {t(`recommend.stage.${stage.status}`, {
          min: stageText(t, stage.typical_min_stage),
          student: stageText(t, stage.student_stage),
        })}
      </p>
      {item.career.entry_notes && <p className="muted">{item.career.entry_notes}</p>}

      {item.unknowns.length > 0 && (
        <>
          <h4>{t('recommend.unknownsTitle')}</h4>
          <ul>
            {item.unknowns.map((u) => (
              <li key={u}>{enumText(t, 'recommend.unknown', u)}</li>
            ))}
          </ul>
        </>
      )}
      <FlagList flags={item.flags} />

      <h4>{t('recommend.sourcesTitle')}</h4>
      {item.sources.length === 0 ? (
        <p className="muted">{t('recommend.noSources')}</p>
      ) : (
        <ul className="link-list">
          {item.sources.map((s) => (
            <li key={s.slug}>
              <Link to={`/opportunities/${encodeURIComponent(s.slug)}`}>{s.title ?? s.slug}</Link>
              <div className="tags">
                <span className="tag">{enumText(t, 'discover.kind', s.kind)}</span>
                <FreshnessChip value={s.freshness} />
                <VerificationTag status={s.verification_status === 'verified' ? 'verified' : 'unverified'} />
              </div>
              <ExternalLink href={s.url}>{s.source ?? s.url}</ExternalLink>
            </li>
          ))}
        </ul>
      )}

      {item.next_actions.length > 0 && (
        <>
          <h4>{t('recommend.nextTitle')}</h4>
          <ul className="link-list">
            {item.next_actions.map((a, i) => (
              <li key={i}>
                <Action action={a} />
              </li>
            ))}
          </ul>
        </>
      )}

      <div className="reco__actions">
        <ExplanationPanel request={{ kind: 'recommendation', run_id: runId, career: item.slug }} />
        <BuildPathwayButton career={item.slug} />
      </div>
    </li>
  )
}

function Action({ action }: { action: NextAction }) {
  const { t } = useTranslation()
  switch (action.type) {
    case 'view_career':
      return <Link to={`/careers/${encodeURIComponent(action.career ?? '')}`}>{t('recommend.action.view_career')}</Link>
    case 'tell_us':
      return <Link to="/interview">{t('recommend.action.tell_us')}</Link>
    case 'plan_prerequisite':
      return <span>{t('recommend.action.plan_prerequisite', { stage: stageText(t, action.typical_min_stage ?? null) })}</span>
    case 'open_route':
      return (
        <Link to={`/opportunities/${encodeURIComponent(action.opportunity ?? '')}`}>
          {t('recommend.action.open_route', { route: enumText(t, 'discover.routeKind', action.route_kind ?? '') })}
        </Link>
      )
    default:
      return <span>{enumText(t, 'recommend.action', action.type)}</span>
  }
}
