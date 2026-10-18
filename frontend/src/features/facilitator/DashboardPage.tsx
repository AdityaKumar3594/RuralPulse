import { useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'
import { ErrorLine, LoadGate, formatDateTime, useAction, useLoad, type Loaded } from '../support/shared'
import { listHelpRequests, listStudents, resolveHelp } from './api'
import type { HelpRequest, StudentSummary } from './types'

export function DashboardPage() {
  const { t } = useTranslation()
  const load = useCallback((o: { signal: AbortSignal }) => listStudents(o), [])
  const { state, reload } = useLoad(load)
  const names = new Map<string, string>(state.phase === 'ready' ? state.data.map((s) => [s.id, s.display_name]) : [])
  return (
    <>
      <h1>{t('facilitator.title')}</h1>
      <p className="lead">{t('facilitator.intro')}</p>
      <StudentsSection state={state} reload={reload} />
      <HelpSection names={names} />
    </>
  )
}

function StudentsSection({ state, reload }: { state: Loaded<StudentSummary[]>; reload: () => void }) {
  const { t } = useTranslation()
  return (
    <section aria-labelledby="fd-students">
      <h2 id="fd-students">{t('facilitator.students.title')}</h2>
      <LoadGate state={state} reload={reload}>
        {(list) =>
          list.length === 0 ? (
            <p role="status">{t('facilitator.students.none')}</p>
          ) : (
            <ul className="sp-list">
              {list.map((s) => (
                <StudentCard key={s.id} s={s} />
              ))}
            </ul>
          )
        }
      </LoadGate>
    </section>
  )
}

function StudentCard({ s }: { s: StudentSummary }) {
  const { t } = useTranslation()
  return (
    <li className="sp-card">
      <h3>{s.display_name}</h3>
      <p>
        {s.is_minor && <span className="sp-tag sp-tag--info">{t('facilitator.students.minor')}</span>}{' '}
        <span className={s.shared ? 'sp-tag sp-tag--ok' : 'sp-tag sp-tag--warn'}>
          <span aria-hidden="true">{s.shared ? '✓ ' : '○ '}</span>
          {s.shared ? t('facilitator.students.shared') : t('facilitator.students.notShared')}
        </span>
      </p>
      <p>{t('facilitator.students.openHelp', { count: s.open_help_requests })}</p>
      {s.shared && (
        <Link className="btn" to={`/facilitator/students/${encodeURIComponent(s.id)}`}>
          {t('facilitator.students.open')}
          <span className="visually-hidden">: {s.display_name}</span>
        </Link>
      )}
    </li>
  )
}

function HelpSection({ names }: { names: Map<string, string> }) {
  const { t } = useTranslation()
  const load = useCallback((o: { signal: AbortSignal }) => listHelpRequests(o), [])
  const { state, reload, setData } = useLoad(load)
  return (
    <section aria-labelledby="fd-help">
      <h2 id="fd-help">{t('facilitator.help.title')}</h2>
      <LoadGate state={state} reload={reload}>
        {(list) =>
          list.length === 0 ? (
            <p role="status">{t('facilitator.help.none')}</p>
          ) : (
            <ul className="sp-list">
              {list.map((r) => (
                <HelpCard key={r.id} r={r} name={names.get(r.student_id)} onResolved={() => setData(list.filter((x) => x.id !== r.id))} />
              ))}
            </ul>
          )
        }
      </LoadGate>
    </section>
  )
}

function HelpCard({ r, name, onResolved }: { r: HelpRequest; name: string | undefined; onResolved: () => void }) {
  const { t, i18n } = useTranslation()
  const { run, busy, error } = useAction()
  const resolve = async () => {
    const out = await run(() => resolveHelp(r.id))
    if (out) onResolved()
  }
  return (
    <li className="sp-card">
      <h3>{t(`facilitator.help.topics.${r.topic}`, { defaultValue: r.topic })}</h3>
      {name && <p>{t('facilitator.help.from', { name })}</p>}
      {r.message && <p>{r.message}</p>}
      {r.opportunity_slug && (
        <p className="muted">{t('facilitator.help.about', { slug: r.opportunity_slug })}</p>
      )}
      <p className="muted">{formatDateTime(r.created_at, i18n.language)}</p>
      <ErrorLine message={error} />
      <button type="button" className="btn btn--secondary" disabled={busy} onClick={resolve}>
        {t('facilitator.help.resolve')}
      </button>
    </li>
  )
}
