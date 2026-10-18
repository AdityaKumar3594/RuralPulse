import { useCallback, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { ExternalStatusBlock } from '../applications/ExternalStatusBlock'
import type { Application } from '../applications/types'
import { ErrorLine, LoadGate, useAction, useLoad } from '../support/shared'
import { confirmApplication, getApplications } from './api'

const CONFIRMABLE = ['submitted', 'under_review', 'accepted', 'rejected'] as const
type Confirmable = (typeof CONFIRMABLE)[number]

export function ApplicationsTab({ studentId }: { studentId: string }) {
  const { t, i18n } = useTranslation()
  const lang = i18n.language
  const load = useCallback((o: { signal: AbortSignal }) => getApplications(studentId, lang, o), [studentId, lang])
  const { state, reload, setData } = useLoad(load)
  return (
    <LoadGate state={state} reload={reload}>
      {(apps) =>
        apps.length === 0 ? (
          <p role="status">{t('facilitator.apps.none')}</p>
        ) : (
          <ul className="sp-list">
            {apps.map((a) => (
              <AppCard key={a.id} app={a} onUpdated={(u) => setData(apps.map((x) => (x.id === u.id ? u : x)))} />
            ))}
          </ul>
        )
      }
    </LoadGate>
  )
}

function AppCard({ app, onUpdated }: { app: Application; onUpdated: (a: Application) => void }) {
  const { t, i18n } = useTranslation()
  const { run, busy, error } = useAction()
  const [status, setStatus] = useState<Confirmable>('submitted')
  const [note, setNote] = useState('')
  const [seen, setSeen] = useState(false)
  const [problem, setProblem] = useState<string | null>(null)
  const [done, setDone] = useState(false)
  const name = app.opportunity.title ?? app.opportunity.slug

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setDone(false)
    if (!seen) {
      setProblem(t('facilitator.apps.errSeen'))
      return
    }
    setProblem(null)
    const out = await run(() => confirmApplication(app.id, i18n.language, status, note.trim() || null))
    if (out) {
      onUpdated(out)
      setDone(true)
      setNote('')
      setSeen(false)
    }
  }

  return (
    <li className="sp-card">
      <h3>{name}</h3>
      <p>
        {t('facilitator.apps.internal', { status: t(`applications.status.${app.internal_status}`) })}{' '}
        <span className="muted">{t('facilitator.apps.internalNote')}</span>
      </p>
      <ExternalStatusBlock app={app} audience="facilitator" />
      <p className="muted">{t('facilitator.apps.code', { code: app.reference_code })}</p>
      <form className="sp-form sp-box" onSubmit={submit} noValidate aria-label={t('facilitator.apps.confirmTitle', { name })}>
        <h4>{t('facilitator.apps.confirmTitle', { name })}</h4>
        <p className="notice">{t('facilitator.apps.warning')}</p>
        <div className="sp-field">
          <label htmlFor={`cs-${app.id}`}>{t('facilitator.apps.status')}</label>
          <select id={`cs-${app.id}`} value={status} onChange={(e) => setStatus(e.target.value as Confirmable)}>
            {CONFIRMABLE.map((s) => (
              <option key={s} value={s}>
                {t(`applications.external.${s}`)}
              </option>
            ))}
          </select>
        </div>
        <div className="sp-field">
          <label htmlFor={`cn-${app.id}`}>{t('facilitator.apps.note')}</label>
          <textarea id={`cn-${app.id}`} value={note} maxLength={300} onChange={(e) => setNote(e.target.value)} />
        </div>
        <div className="sp-field">
          <label className="check">
            <input type="checkbox" checked={seen} onChange={(e) => setSeen(e.target.checked)} />
            <span>{t('facilitator.apps.seenEvidence')}</span>
          </label>
          {problem && <p className="error" role="alert">{problem}</p>}
        </div>
        <ErrorLine message={error} />
        {done && <p role="status" className="sp-ok">{t('facilitator.apps.confirmed')}</p>}
        <button type="submit" className="btn" disabled={busy}>
          {busy ? t('common.loading') : t('facilitator.apps.confirm')}
        </button>
      </form>
    </li>
  )
}
