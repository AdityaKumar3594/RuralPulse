import { useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router'
import { useAuth } from '../../auth/AuthContext'
import { BuildPathwayButton } from '../pathway/BuildPathwayButton'
import { getCareer } from './api'
import { Status } from './Badges'
import { apiMessage, enumText } from './format'
import type { Career } from './types'
import { useLoad } from './useLoad'
import './shared.css'

export function CareerDetailPage() {
  const { slug = '' } = useParams()
  const { t, i18n } = useTranslation()
  const lang = i18n.language
  const load = useCallback((o: { signal: AbortSignal }) => getCareer(slug, lang, o), [slug, lang])
  const { state, reload } = useLoad(load)

  return (
    <>
      <p>
        <Link to="/careers">{t('discover.backToCareers')}</Link>
      </p>
      {state.phase === 'loading' && <Status />}
      {state.phase === 'error' && <Status error={apiMessage(state.error, t)} onRetry={reload} />}
      {state.phase === 'ready' && <CareerView career={state.data} />}
    </>
  )
}

function CareerView({ career }: { career: Career }) {
  const { t } = useTranslation()
  const { user } = useAuth()
  const stage = career.entry.typical_min_stage
  return (
    <article>
      <h1>{career.title ?? career.slug}</h1>
      <p className="muted">{enumText(t, 'discover.family', career.family)}</p>
      {career.language_fallback && <p className="muted">{t('discover.languageFallback')}</p>}
      {career.verification_status !== 'verified' && (
        <p className="note note--warn" role="note">
          {t('discover.career.draftNote')}
        </p>
      )}
      {career.description && (
        <section className="section" aria-labelledby="c-about">
          <h2 id="c-about">{t('discover.career.about')}</h2>
          <p>{career.description}</p>
        </section>
      )}
      {career.activities.length > 0 && (
        <section className="section" aria-labelledby="c-act">
          <h2 id="c-act">{t('discover.career.activities')}</h2>
          <ul>{career.activities.map((a) => <li key={a}>{a}</li>)}</ul>
        </section>
      )}
      {career.skills.length > 0 && (
        <section className="section" aria-labelledby="c-skills">
          <h2 id="c-skills">{t('discover.career.skills')}</h2>
          <ul>{career.skills.map((s) => <li key={s}>{s}</li>)}</ul>
        </section>
      )}

      <section className="section" aria-labelledby="c-entry">
        <h2 id="c-entry">{t('discover.career.entryTitle')}</h2>
        {stage && <p>{t('discover.career.minStage', { stage: enumText(t, 'discover.stage', stage) })}</p>}
        <h3>{t('discover.career.entryNotes')}</h3>
        <p>{career.entry.notes || t('discover.career.noNotes')}</p>
        <p className="note" role="note">
          {t('discover.career.typicalNote')}
        </p>
      </section>

      <section className="section" aria-labelledby="c-routes">
        <h2 id="c-routes">{t('discover.career.routesTitle')}</h2>
        {career.routes.length === 0 ? (
          <p className="muted">{t('discover.career.none')}</p>
        ) : (
          <ul className="cards">
            {career.routes.map((r, i) => (
              <li key={i} className="card">
                <h3>{r.title ?? enumText(t, 'discover.routeKind', r.kind)}</h3>
                <p className="muted">{enumText(t, 'discover.routeKind', r.kind)}</p>
                {r.min_stage && <p>{t('discover.career.routeFrom', { stage: enumText(t, 'discover.stage', r.min_stage) })}</p>}
                {r.opportunity && (
                  <p>
                    {t('discover.career.routeLinked')}:{' '}
                    <Link to={`/opportunities/${encodeURIComponent(r.opportunity.slug)}`}>{r.opportunity.title ?? r.opportunity.slug}</Link>
                  </p>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      {career.learning_resources.length > 0 && (
        <section className="section" aria-labelledby="c-res">
          <h2 id="c-res">{t('discover.career.resourcesTitle')}</h2>
          <ul className="link-list">
            {career.learning_resources.map((o) => (
              <li key={o.slug}>
                <Link to={`/opportunities/${encodeURIComponent(o.slug)}`}>{o.title ?? o.slug}</Link>
              </li>
            ))}
          </ul>
        </section>
      )}

      {career.related.length > 0 && (
        <section className="section" aria-labelledby="c-rel">
          <h2 id="c-rel">{t('discover.career.relatedTitle')}</h2>
          <ul className="link-list">
            {career.related.map((c) => (
              <li key={c.slug}>
                <Link to={`/careers/${encodeURIComponent(c.slug)}`}>{c.title ?? c.slug}</Link>
              </li>
            ))}
          </ul>
        </section>
      )}

      {user?.role === 'student' && <BuildPathwayButton career={career.slug} />}
    </article>
  )
}
