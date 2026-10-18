import { useCallback, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router'
import { ErrorLine, LoadGate, safeHttps, useAction, useLoad } from '../support/shared'
import { askApplicationHelp, getApplication, updateApplication, type UpdateBody } from './api'
import { ExternalStatusBlock } from './ExternalStatusBlock'
import { STEPS, TRANSITIONS, type Application, type ExternalStatus, type InternalStatus } from './types'

const REPORTABLE: ExternalStatus[] = ['submitted', 'under_review', 'accepted', 'rejected', 'unknown']

export function ApplicationDetailPage() {
  const { id = '' } = useParams()
  const { t, i18n } = useTranslation()
  const lang = i18n.language
  const load = useCallback((o: { signal: AbortSignal }) => getApplication(id, lang, o), [id, lang])
  const { state, reload, setData } = useLoad(load)
  return (
    <>
      <p>
        <Link to="/applications">{t('applications.back')}</Link>
      </p>
      <LoadGate state={state} reload={reload}>
        {(app) => <Detail app={app} onChange={setData} />}
      </LoadGate>
    </>
  )
}

function Detail({ app, onChange }: { app: Application; onChange: (a: Application) => void }) {
  const { t, i18n } = useTranslation()
  const update = useAction()
  const name = app.opportunity.title ?? app.opportunity.slug
  const href = safeHttps(app.opportunity.url)

  const send = (body: UpdateBody) =>
    update.run(async () => {
      const out = await updateApplication(app.id, i18n.language, body)
      onChange(out)
      return out
    })

  return (
    <>
      <h1>{name}</h1>
      {href && (
        <p>
          <a href={href} target="_blank" rel="noopener noreferrer">
            {t('applications.officialSite')}
          </a>
        </p>
      )}
      <p className="notice">{t('applications.trackingOnly')}</p>
      <ErrorLine message={update.error} />

      <section className="sp-box" aria-labelledby="ap-progress">
        <h2 id="ap-progress">{t('applications.progress.title')}</h2>
        <p className="muted">{t('applications.progress.help')}</p>
        <Stepper current={app.internal_status} />
        <Moves app={app} busy={update.busy} onMove={(s) => send({ internal_status: s })} />
      </section>

      <section className="sp-box" aria-labelledby="ap-docs">
        <h2 id="ap-docs">{t('applications.docs.title')}</h2>
        {Object.keys(app.documents).length === 0 ? (
          <p>{t('applications.docs.none')}</p>
        ) : (
          <ul className="sp-list">
            {Object.entries(app.documents).map(([doc, done]) => (
              <li key={doc}>
                <label className="check">
                  <input
                    type="checkbox"
                    checked={done}
                    disabled={update.busy}
                    onChange={(e) => send({ documents: { [doc]: e.target.checked } })}
                  />
                  <span>{doc}</span>
                </label>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="ap-ext">
        <h2 id="ap-ext">{t('applications.external.heading')}</h2>
        <ExternalStatusBlock app={app} audience="student" />
        <ReportForm app={app} busy={update.busy} onReport={(s) => send({ reported_external_status: s })} />
      </section>

      <section className="sp-box" aria-labelledby="ap-code">
        <h2 id="ap-code">{t('applications.code.title')}</h2>
        <p className="sp-code" aria-label={app.reference_code.split('').join(' ')}>
          {app.reference_code}
        </p>
        <p>{t('applications.code.give')}</p>
        <CopyButton text={app.reference_code} />
      </section>

      <HelpForm id={app.id} />
    </>
  )
}

function Stepper({ current }: { current: InternalStatus }) {
  const { t } = useTranslation()
  if (current === 'withdrawn') {
    return (
      <p>
        <span className="sp-tag sp-tag--warn">{t('applications.status.withdrawn')}</span> {t('applications.progress.withdrawnNote')}
      </p>
    )
  }
  const at = STEPS.indexOf(current)
  return (
    <ol className="sp-list" aria-label={t('applications.progress.title')}>
      {STEPS.map((s, i) => (
        <li key={s} className="sp-card" aria-current={i === at ? 'step' : undefined}>
          <span aria-hidden="true">{i < at ? '✓ ' : i === at ? '● ' : '○ '}</span>
          <strong>{t(`applications.status.${s}`)}</strong>{' '}
          <span className="muted">
            {i < at ? t('applications.progress.done') : i === at ? t('applications.progress.now') : t('applications.progress.later')}
          </span>
          <p className="muted">{t(`applications.statusHelp.${s}`)}</p>
        </li>
      ))}
    </ol>
  )
}

function Moves({ app, busy, onMove }: { app: Application; busy: boolean; onMove: (s: InternalStatus) => void }) {
  const { t } = useTranslation()
  return (
    <div className="sp-row">
      {TRANSITIONS[app.internal_status].map((s) => (
        <button
          key={s}
          type="button"
          className={s === 'withdrawn' ? 'btn btn--secondary' : 'btn'}
          disabled={busy}
          onClick={() => onMove(s)}
        >
          {t(`applications.move.${s}`)}
        </button>
      ))}
    </div>
  )
}

function ReportForm({ app, busy, onReport }: { app: Application; busy: boolean; onReport: (s: ExternalStatus) => void }) {
  const { t } = useTranslation()
  const [value, setValue] = useState<ExternalStatus>('submitted')
  const applied = app.internal_status === 'applied'
  const locked = app.external_confirmed
  const disabled = !applied || locked || busy
  const submit = (e: FormEvent) => {
    e.preventDefault()
    onReport(value)
  }
  return (
    <form className="sp-box sp-form" onSubmit={submit}>
      <h3>{t('applications.report.title')}</h3>
      {!applied && <p className="notice">{t('applications.report.needApplied')}</p>}
      {locked && <p className="notice">{t('applications.report.locked')}</p>}
      <div className="sp-field">
        <label htmlFor="ap-report">{t('applications.report.label')}</label>
        <select id="ap-report" value={value} disabled={disabled} onChange={(e) => setValue(e.target.value as ExternalStatus)}>
          {REPORTABLE.map((s) => (
            <option key={s} value={s}>
              {t(`applications.reportOption.${s}`)}
            </option>
          ))}
        </select>
      </div>
      <p className="muted">{t('applications.report.hint')}</p>
      <button type="submit" className="btn" disabled={disabled}>
        {t('applications.report.send')}
      </button>
    </form>
  )
}

function CopyButton({ text }: { text: string }) {
  const { t } = useTranslation()
  const [copied, setCopied] = useState<'yes' | 'no' | null>(null)
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied('yes')
    } catch {
      setCopied('no')
    }
  }
  return (
    <>
      <button type="button" className="btn btn--secondary" onClick={copy}>
        {t('applications.code.copy')}
      </button>
      <p role="status" className="muted">
        {copied === 'yes' ? t('applications.code.copied') : copied === 'no' ? t('applications.code.copyFailed') : ''}
      </p>
    </>
  )
}

function HelpForm({ id }: { id: string }) {
  const { t } = useTranslation()
  const { run, busy, error } = useAction()
  const [message, setMessage] = useState('')
  const [sent, setSent] = useState(false)
  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setSent(false)
    const ok = await run(async () => {
      await askApplicationHelp(id, message.trim() || null)
      return true
    })
    if (ok) {
      setSent(true)
      setMessage('')
    }
  }
  return (
    <form className="sp-box sp-form" onSubmit={submit} aria-labelledby="ap-help">
      <h2 id="ap-help">{t('applications.help.title')}</h2>
      <p className="muted">{t('applications.help.intro')}</p>
      <div className="sp-field">
        <label htmlFor="ap-help-msg">{t('applications.help.message')}</label>
        <textarea id="ap-help-msg" value={message} maxLength={500} onChange={(e) => setMessage(e.target.value)} />
      </div>
      <ErrorLine message={error} />
      {sent && (
        <p role="status" className="sp-ok">
          {t('applications.help.sent')}
        </p>
      )}
      <button type="submit" className="btn" disabled={busy}>
        {busy ? t('common.loading') : t('applications.help.send')}
      </button>
    </form>
  )
}
