import { useCallback, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'
import { Field } from '../../components/Field'
import {
  askForHelp,
  getMyEndorsements,
  getMyFacilitators,
  getSharing,
  grantSharing,
  setEndorsementStatus,
  withdrawSharing,
  type Endorsement,
  type HelpTopic,
  type ConsentStatus,
} from './api'
import { ErrorLine, LoadGate, formatDateTime, useAction, useLoad } from './shared'

const PHONE_RE = /^[6-9]\d{9}$/
const TOPICS: HelpTopic[] = ['general', 'interview', 'pathway', 'application']

export function SupportPage() {
  const { t } = useTranslation()
  return (
    <>
      <h1>{t('support.title')}</h1>
      <p className="lead">{t('support.intro')}</p>
      <SharingSection />
      <TeachersSection />
      <EndorsementsSection />
      <HelpSection />
    </>
  )
}

function SharingSection() {
  const { t } = useTranslation()
  const load = useCallback((o: { signal: AbortSignal }) => getSharing(o), [])
  const { state, reload, setData } = useLoad(load)
  return (
    <section aria-labelledby="sp-share" className="sp-box">
      <h2 id="sp-share">{t('support.share.title')}</h2>
      <LoadGate state={state} reload={reload}>
        {(status) => <SharingBody status={status} onChange={setData} />}
      </LoadGate>
    </section>
  )
}

function SharingBody({ status, onChange }: { status: ConsentStatus; onChange: (s: ConsentStatus) => void }) {
  const { t } = useTranslation()
  const { run, busy, error } = useAction()
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [agree, setAgree] = useState(false)
  const [problems, setProblems] = useState<{ name?: string; phone?: string; agree?: string }>({})
  const [message, setMessage] = useState<string | null>(null)
  const on = status.active !== null
  const byGuardian = status.required_given_by === 'guardian'

  const turnOn = async (e: FormEvent) => {
    e.preventDefault()
    const found: typeof problems = {}
    if (byGuardian && !name.trim()) found.name = t('support.share.errName')
    if (byGuardian && !PHONE_RE.test(phone)) found.phone = t('support.share.errPhone')
    if (!agree) found.agree = t('support.share.errAgree')
    setProblems(found)
    if (Object.keys(found).length > 0) return
    const out = await run(() =>
      grantSharing(byGuardian ? { given_by: 'guardian', guardian_name: name.trim(), guardian_phone: phone } : { given_by: 'self' }),
    )
    if (out) {
      onChange({ ...status, active: out })
      setMessage(t('support.share.nowOn'))
    }
  }

  const turnOff = async () => {
    const done = await run(async () => {
      await withdrawSharing()
      return true
    })
    if (done) {
      onChange({ ...status, active: null })
      setMessage(t('support.share.nowOff'))
    }
  }

  return (
    <>
      <p>
        <span className={on ? 'sp-tag sp-tag--ok' : 'sp-tag sp-tag--warn'}>
          <span aria-hidden="true">{on ? '✓ ' : '○ '}</span>
          {on ? t('support.share.stateOn') : t('support.share.stateOff')}
        </span>
      </p>
      <p>{t('support.share.explain')}</p>
      <ul>
        <li>{t('support.share.point1')}</li>
        <li>{t('support.share.point2')}</li>
        <li>{t('support.share.point3')}</li>
      </ul>
      {message && <p role="status" className="sp-ok">{message}</p>}
      <ErrorLine message={error} />
      {on ? (
        <button type="button" className="btn btn--secondary" disabled={busy} onClick={turnOff}>
          {busy ? t('common.loading') : t('support.share.turnOff')}
        </button>
      ) : (
        <form className="sp-form" onSubmit={turnOn} noValidate>
          {byGuardian && (
            <>
              <p className="notice">{t('support.share.guardianNeeded')}</p>
              <Field id="sp-gname" label={t('support.share.guardianName')} value={name} onChange={(e) => setName(e.target.value)} error={problems.name} autoComplete="off" />
              <Field id="sp-gphone" label={t('support.share.guardianPhone')} value={phone} onChange={(e) => setPhone(e.target.value)} error={problems.phone} inputMode="numeric" autoComplete="off" />
            </>
          )}
          <div className="sp-field">
            <label className="check">
              <input type="checkbox" checked={agree} onChange={(e) => setAgree(e.target.checked)} />
              <span>{byGuardian ? t('support.share.agreeGuardian') : t('support.share.agreeSelf')}</span>
            </label>
            {problems.agree && <p className="error" role="alert">{problems.agree}</p>}
          </div>
          <button type="submit" className="btn" disabled={busy}>
            {busy ? t('common.loading') : t('support.share.turnOn')}
          </button>
        </form>
      )}
    </>
  )
}

function TeachersSection() {
  const { t, i18n } = useTranslation()
  const load = useCallback((o: { signal: AbortSignal }) => getMyFacilitators(o), [])
  const { state, reload } = useLoad(load)
  return (
    <section aria-labelledby="sp-teachers" className="sp-box">
      <h2 id="sp-teachers">{t('support.teachers.title')}</h2>
      <LoadGate state={state} reload={reload}>
        {(list) =>
          list.length === 0 ? (
            <p>{t('support.teachers.none')}</p>
          ) : (
            <ul className="sp-list">
              {list.map((f) => (
                <li key={f.id} className="sp-card">
                  <strong>{f.display_name}</strong>
                  <p className="muted">{t('support.teachers.since', { date: formatDateTime(f.since, i18n.language) })}</p>
                </li>
              ))}
            </ul>
          )
        }
      </LoadGate>
    </section>
  )
}

function EndorsementsSection() {
  const { t } = useTranslation()
  const load = useCallback((o: { signal: AbortSignal }) => getMyEndorsements(o), [])
  const { state, reload, setData } = useLoad(load)
  return (
    <section aria-labelledby="sp-endorse" className="sp-box">
      <h2 id="sp-endorse">{t('support.endorse.title')}</h2>
      <p className="muted">{t('support.endorse.intro')}</p>
      <LoadGate state={state} reload={reload}>
        {(list) =>
          list.length === 0 ? (
            <p>{t('support.endorse.none')}</p>
          ) : (
            <ul className="sp-list">
              {list.map((e) => (
                <EndorsementCard
                  key={e.id}
                  item={e}
                  onUpdated={(u) => setData(list.map((x) => (x.id === u.id ? u : x)))}
                />
              ))}
            </ul>
          )
        }
      </LoadGate>
    </section>
  )
}

function EndorsementCard({ item, onUpdated }: { item: Endorsement; onUpdated: (e: Endorsement) => void }) {
  const { t, i18n } = useTranslation()
  const { run, busy, error } = useAction()
  const set = async (status: 'seen' | 'dismissed') => {
    const out = await run(() => setEndorsementStatus(item.id, status))
    if (out) onUpdated(out)
  }
  const label = t(`support.endorse.status.${item.status}`, { defaultValue: item.status })
  return (
    <li className="sp-card">
      <h3>
        <Link to={`/opportunities/${encodeURIComponent(item.opportunity_slug)}`}>{item.opportunity_slug}</Link>
      </h3>
      {item.note && <p>{t('support.endorse.note', { note: item.note })}</p>}
      <p className="muted">
        <span className="sp-tag">{label}</span> {formatDateTime(item.created_at, i18n.language)}
      </p>
      <ErrorLine message={error} />
      {item.status === 'suggested' && (
        <div className="sp-row">
          <button type="button" className="btn btn--secondary" disabled={busy} onClick={() => set('seen')}>
            {t('support.endorse.markSeen')}
          </button>
          <button type="button" className="btn btn--secondary" disabled={busy} onClick={() => set('dismissed')}>
            {t('support.endorse.dismiss')}
          </button>
        </div>
      )}
      {item.status === 'seen' && (
        <button type="button" className="btn btn--secondary" disabled={busy} onClick={() => set('dismissed')}>
          {t('support.endorse.dismiss')}
        </button>
      )}
    </li>
  )
}

function HelpSection() {
  const { t } = useTranslation()
  const { run, busy, error } = useAction()
  const [topic, setTopic] = useState<HelpTopic>('general')
  const [message, setMessage] = useState('')
  const [sent, setSent] = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setSent(false)
    const out = await run(async () => {
      await askForHelp(topic, message.trim() || null)
      return true
    })
    if (out) {
      setSent(true)
      setMessage('')
    }
  }

  return (
    <section aria-labelledby="sp-help" className="sp-box">
      <h2 id="sp-help">{t('support.help.title')}</h2>
      <p className="muted">{t('support.help.intro')}</p>
      <form className="sp-form" onSubmit={submit}>
        <div className="sp-field">
          <label htmlFor="sp-topic">{t('support.help.topic')}</label>
          <select id="sp-topic" value={topic} onChange={(e) => setTopic(e.target.value as HelpTopic)}>
            {TOPICS.map((x) => (
              <option key={x} value={x}>
                {t(`support.help.topics.${x}`)}
              </option>
            ))}
          </select>
        </div>
        <div className="sp-field">
          <label htmlFor="sp-msg">{t('support.help.message')}</label>
          <textarea id="sp-msg" value={message} maxLength={500} onChange={(e) => setMessage(e.target.value)} />
        </div>
        <ErrorLine message={error} />
        {sent && <p role="status" className="sp-ok">{t('support.help.sent')}</p>}
        <button type="submit" className="btn" disabled={busy}>
          {busy ? t('common.loading') : t('support.help.send')}
        </button>
      </form>
    </section>
  )
}
