import { useCallback, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'
import { Status } from '../discover/Badges'
import { apiMessage, enumText } from '../discover/format'
import { useLoad } from '../discover/useLoad'
import { createRun } from './api'
import { RecommendationCard } from './RecommendationCard'
import type { Run } from './types'
import '../discover/shared.css'
import './recommend.css'

export function RecommendPage() {
  const { t, i18n } = useTranslation()
  // One run per visit. Switching language does not make a new run; "Show suggestions again" does.
  const [runLang, setRunLang] = useState(i18n.language)
  const load = useCallback((o: { signal: AbortSignal }) => createRun(runLang, 5, o), [runLang])
  const { state, reload } = useLoad(load)

  const again = () => {
    if (runLang !== i18n.language) setRunLang(i18n.language)
    else reload()
  }

  return (
    <>
      <h1>{t('recommend.title')}</h1>
      <p className="lead">{t('recommend.intro')}</p>
      {state.phase === 'loading' && <Status loading={t('recommend.loading')} />}
      {state.phase === 'error' && <Status error={apiMessage(state.error, t)} onRetry={reload} />}
      {state.phase === 'ready' && <RunView run={state.data} />}
      {state.phase !== 'loading' && (
        <p>
          <button type="button" className="btn btn--secondary" onClick={again}>
            {t('recommend.rerun')}
          </button>
        </p>
      )}
    </>
  )
}

function RunView({ run }: { run: Run }) {
  const { t } = useTranslation()
  const matches = run.items.filter((i) => i.kind === 'match')
  const explore = run.items.filter((i) => i.kind === 'explore')
  const unmatched = run.profile_summary.unmatched_terms ?? []

  return (
    <>
      {run.status === 'insufficient_profile' && (
        <section className="note note--warn" aria-labelledby="r-insuf">
          <h2 id="r-insuf">{t('recommend.insufficient.title')}</h2>
          <p>{t('recommend.insufficient.body')}</p>
        </section>
      )}
      {run.status === 'no_matches' && (
        <section className="note note--warn" aria-labelledby="r-none">
          <h2 id="r-none">{t('recommend.noMatches.title')}</h2>
          <p>{t('recommend.noMatches.body')}</p>
          {unmatched.length > 0 && (
            <>
              <h3>{t('recommend.unmatchedTitle')}</h3>
              <ul>
                {unmatched.map((u, i) => (
                  <li key={i}>
                    {t('recommend.unmatched', { field: enumText(t, 'recommend.termField', u.field), text: u.text })}
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>
      )}

      {run.missing.length > 0 && run.status !== 'ok' && (
        <section className="section" aria-labelledby="r-miss">
          <h2 id="r-miss">{t('recommend.missingTitle')}</h2>
          <MissingList missing={run.missing} />
        </section>
      )}

      {matches.length > 0 && (
        <section className="section" aria-labelledby="r-matches">
          <h2 id="r-matches">{t('recommend.matchesTitle')}</h2>
          <p>{t('recommend.matchesIntro')}</p>
          <p className="muted">{t('recommend.levelNote')}</p>
          <ul className="cards">
            {matches.map((i) => (
              <RecommendationCard key={i.slug} item={i} runId={run.id} />
            ))}
          </ul>
        </section>
      )}

      {explore.length > 0 && (
        <section className="section" aria-labelledby="r-explore">
          <h2 id="r-explore">{t('recommend.exploreTitle')}</h2>
          <p>{t('recommend.exploreIntro')}</p>
          <ul className="cards">
            {explore.map((i) => (
              <RecommendationCard key={i.slug} item={i} runId={run.id} />
            ))}
          </ul>
        </section>
      )}

      {run.missing.length > 0 && run.status === 'ok' && (
        <section className="section" aria-labelledby="r-miss2">
          <h2 id="r-miss2">{t('recommend.missingTitle')}</h2>
          <MissingList missing={run.missing} />
        </section>
      )}

      {run.notes.length > 0 && (
        <section className="section" aria-labelledby="r-notes">
          <h2 id="r-notes">{t('recommend.notesTitle')}</h2>
          <ul>
            {run.notes.map((n) => (
              <li key={n}>{enumText(t, 'recommend.note', n)}</li>
            ))}
          </ul>
        </section>
      )}
    </>
  )
}

function MissingList({ missing }: { missing: Run['missing'] }) {
  const { t } = useTranslation()
  return (
    <>
      <ul>
        {missing.map((m) => (
          <li key={m.field}>{enumText(t, 'recommend.field', m.field)}</li>
        ))}
      </ul>
      {missing.some((m) => m.question_id) && (
        <Link className="btn" to="/interview">
          {t('recommend.answerQuestions')}
        </Link>
      )}
    </>
  )
}
