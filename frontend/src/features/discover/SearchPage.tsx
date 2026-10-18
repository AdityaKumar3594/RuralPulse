import { useEffect, useRef, useState, type FormEvent, type RefObject } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'
import { search } from './api'
import { FlagList, FreshnessChip, Status, VerificationTag } from './Badges'
import { apiMessage, enumText } from './format'
import type { SearchHit, SearchParams, SearchResponse } from './types'
import './shared.css'

const KINDS = [
  'platform', 'course', 'scholarship', 'scheme', 'apprenticeship', 'internship', 'exam',
  'training_program', 'mentorship', 'job',
]
const STAGES = ['class_9', 'class_10', 'class_11', 'class_12', 'iti_or_diploma', 'undergraduate', 'graduate', 'not_in_school']

type State =
  | { phase: 'idle' }
  | { phase: 'loading' }
  | { phase: 'error'; message: string }
  | { phase: 'done'; data: SearchResponse }

export function SearchPage() {
  const { t, i18n } = useTranslation()
  const [q, setQ] = useState('')
  const [type, setType] = useState('')
  const [kind, setKind] = useState('')
  const [stateName, setStateName] = useState('')
  const [stage, setStage] = useState('')
  const [state, setState] = useState<State>({ phase: 'idle' })
  const last = useRef<SearchParams>({})
  const latest = useRef(0)
  const results = useRef<HTMLHeadingElement>(null)

  useEffect(() => {
    if (state.phase === 'done') results.current?.focus()
  }, [state])

  const run = async (params: SearchParams) => {
    const mine = ++latest.current
    last.current = params
    setState({ phase: 'loading' })
    try {
      const data = await search(params, i18n.language)
      if (mine === latest.current) setState({ phase: 'done', data })
    } catch (err) {
      if (mine === latest.current) setState({ phase: 'error', message: apiMessage(err, t) })
    }
  }

  const submit = (e: FormEvent) => {
    e.preventDefault()
    void run({
      q: q.trim() || undefined,
      type: type || undefined,
      // The server leaves careers out when a kind of opportunity is chosen.
      kind: type === 'career' ? undefined : kind || undefined,
      state: stateName.trim() || undefined,
      stage: stage || undefined,
    })
  }

  return (
    <>
      <h1>{t('discover.search.title')}</h1>
      <p className="lead">{t('discover.search.intro')}</p>

      <form onSubmit={submit} className="filters" role="search" aria-label={t('discover.search.title')}>
        <div className="field">
          <label htmlFor="s-q">{t('discover.search.queryLabel')}</label>
          <p id="s-q-hint" className="muted">{t('discover.search.queryHint')}</p>
          <input id="s-q" type="search" value={q} maxLength={200} aria-describedby="s-q-hint" onChange={(e) => setQ(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="s-type">{t('discover.search.typeLabel')}</label>
          <select id="s-type" value={type} onChange={(e) => setType(e.target.value)}>
            <option value="">{t('discover.search.typeAny')}</option>
            <option value="career">{t('discover.type.career')}</option>
            <option value="opportunity">{t('discover.type.opportunity')}</option>
          </select>
        </div>
        <div className="field">
          <label htmlFor="s-kind">{t('discover.search.kindLabel')}</label>
          <select id="s-kind" value={kind} disabled={type === 'career'} onChange={(e) => setKind(e.target.value)}>
            <option value="">{t('discover.search.kindAny')}</option>
            {KINDS.map((k) => (
              <option key={k} value={k}>{t(`discover.kind.${k}`)}</option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="s-state">{t('discover.search.stateLabel')}</label>
          <p id="s-state-hint" className="muted">{t('discover.search.stateHint')}</p>
          <input id="s-state" type="text" value={stateName} maxLength={60} aria-describedby="s-state-hint" onChange={(e) => setStateName(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="s-stage">{t('discover.search.stageLabel')}</label>
          <select id="s-stage" value={stage} onChange={(e) => setStage(e.target.value)}>
            <option value="">{t('discover.search.stageAny')}</option>
            {STAGES.map((s) => (
              <option key={s} value={s}>{t(`discover.stage.${s}`)}</option>
            ))}
          </select>
        </div>
        <button type="submit" className="btn btn--big" disabled={state.phase === 'loading'}>
          {t('discover.search.submit')}
        </button>
      </form>

      <details className="section">
        <summary>{t('discover.search.matchTitle')}</summary>
        <p>{t('discover.search.matchExplain')}</p>
      </details>

      {state.phase === 'idle' && <p className="muted">{t('discover.search.idle')}</p>}
      {state.phase === 'loading' && <Status loading={t('discover.search.searching')} />}
      {state.phase === 'error' && <Status error={state.message} onRetry={() => void run(last.current)} />}
      {state.phase === 'done' && <Results data={state.data} headingRef={results} />}
    </>
  )
}

function Results({ data, headingRef }: { data: SearchResponse; headingRef: RefObject<HTMLHeadingElement | null> }) {
  const { t } = useTranslation()
  return (
    <section aria-labelledby="results-title">
      <h2 id="results-title" ref={headingRef} tabIndex={-1}>
        {t('discover.search.resultsTitle')}
      </h2>
      {data.status === 'insufficient_evidence' && (
        <p role="status" className="note note--warn">
          {t('discover.search.insufficient')}
        </p>
      )}
      {data.status === 'partial_only' && (
        <p role="status" className="note note--warn">
          {t('discover.search.partialOnly')}
        </p>
      )}
      {data.results.length > 0 && (
        <>
          <p role="status">{t('discover.search.resultsCount', { count: data.results.length })}</p>
          <ul className="cards">
            {data.results.map((hit) => (
              <li key={`${hit.type}:${hit.id}`} className="card">
                <Hit hit={hit} />
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  )
}

function Hit({ hit }: { hit: SearchHit }) {
  const { t } = useTranslation()
  const title = hit.title ?? t('discover.search.untitled')
  const to = hit.type === 'career' ? `/careers/${encodeURIComponent(hit.id)}` : `/opportunities/${encodeURIComponent(hit.id)}`
  const group = enumText(t, hit.type === 'career' ? 'discover.family' : 'discover.kind', hit.group)
  return (
    <>
      <h3>{title}</h3>
      {hit.summary && <p>{hit.summary}</p>}
      <div className="tags">
        <span className="tag tag--info">{t(`discover.type.${hit.type}`)}</span>
        <span className="tag">{group}</span>
        <span className={`tag${hit.match_type === 'exact' ? ' tag--verified' : ''}`}>{t(`discover.search.match.${hit.match_type}`)}</span>
        <FreshnessChip value={hit.freshness} />
        {hit.verification && <VerificationTag status={hit.verification.status} />}
      </div>
      <p className="muted">{t(`discover.search.matchHelp.${hit.match_type}`)}</p>
      {hit.source && <p className="muted">{t('discover.search.source', { name: hit.source.name })}</p>}
      {hit.eligibility_known && <p className="muted">{t('discover.search.hasRules')}</p>}
      {hit.language_fallback && <p className="muted">{t('discover.languageFallback')}</p>}
      <FlagList flags={hit.flags} />
      <Link className="btn btn--secondary" to={to}>
        {t('discover.search.view')}
        <span className="visually-hidden">: {title}</span>
      </Link>
    </>
  )
}

