import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Field } from '../../components/Field'
import { confirmApplication, getStats } from './api'
import { errText, Msg } from './common'
import { EXTERNAL_STATUSES, type ExternalStatus, type Stats } from './types'

export function ApplicationsPage() {
  const { t } = useTranslation()
  const [code, setCode] = useState('')
  const [status, setStatus] = useState<ExternalStatus>('accepted')
  const [note, setNote] = useState('')
  const [codeErr, setCodeErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<{ opportunity: string; external_status: string } | null>(null)

  const [slug, setSlug] = useState('')
  const [stats, setStats] = useState<Stats | null>(null)
  const [statsBusy, setStatsBusy] = useState(false)
  const [statsError, setStatsError] = useState<string | null>(null)

  async function confirm(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setResult(null)
    const c = code.trim().toUpperCase()
    if (c.length !== 8) {
      setCodeErr(t('partner.apps.codeInvalid'))
      return
    }
    setCodeErr(null)
    setBusy(true)
    try {
      setResult(await confirmApplication(c, status, note.trim() || null))
      setCode('')
      setNote('')
    } catch (err) {
      setError(errText(err, t))
    } finally {
      setBusy(false)
    }
  }

  async function loadStats(e: FormEvent) {
    e.preventDefault()
    setStatsError(null)
    setStats(null)
    if (!slug.trim()) {
      setStatsError(t('partner.apps.slugRequired'))
      return
    }
    setStatsBusy(true)
    try {
      setStats(await getStats(slug.trim()))
    } catch (err) {
      setStatsError(errText(err, t))
    } finally {
      setStatsBusy(false)
    }
  }

  const rows = (m: Record<string, number>, ns: string) =>
    Object.entries(m).length === 0 ? (
      <p>{t('partner.apps.noCounts')}</p>
    ) : (
      Object.entries(m).map(([k, v]) => (
        <div key={k} className="ptn-stat">
          <span>{t(`partner.${ns}.${k}`, { defaultValue: k })}</span>
          <strong>{v}</strong>
        </div>
      ))
    )

  return (
    <>
      <section aria-labelledby="ptn-conf-h">
        <h2 id="ptn-conf-h">{t('partner.apps.confirmTitle')}</h2>
        <p className="muted">{t('partner.apps.confirmHint')}</p>
        <form className="ptn-form" onSubmit={confirm} noValidate>
          <Field id="ptn-code" label={t('partner.apps.code')} hint={t('partner.apps.codeHint')} value={code} error={codeErr} maxLength={8} autoCapitalize="characters" autoComplete="off" onChange={(e) => setCode(e.target.value.toUpperCase())} />
          <div className="field">
            <label htmlFor="ptn-status">{t('partner.apps.status')}</label>
            <select id="ptn-status" value={status} onChange={(e) => setStatus(e.target.value as ExternalStatus)}>
              {EXTERNAL_STATUSES.map((s) => (
                <option key={s} value={s}>
                  {t(`partner.external.${s}`)}
                </option>
              ))}
            </select>
          </div>
          <Field id="ptn-note" label={t('partner.apps.note')} maxLength={300} value={note} onChange={(e) => setNote(e.target.value)} />
          <button type="submit" className="btn btn--big" disabled={busy}>
            {busy ? t('partner.saving') : t('partner.apps.confirm')}
          </button>
          <Msg error={error} />
        </form>
        {result && (
          <p role="status" className="ptn-ok">
            {t('partner.apps.confirmed', {
              opportunity: result.opportunity,
              status: t(`partner.external.${result.external_status}`, { defaultValue: result.external_status }),
            })}
          </p>
        )}
      </section>

      <section aria-labelledby="ptn-stats-h">
        <h2 id="ptn-stats-h">{t('partner.apps.statsTitle')}</h2>
        <p className="muted">{t('partner.apps.statsHint')}</p>
        <form className="ptn-form" onSubmit={loadStats} noValidate>
          <Field id="ptn-slug" label={t('partner.apps.slug')} autoCapitalize="none" value={slug} onChange={(e) => setSlug(e.target.value)} />
          <button type="submit" className="btn btn--big" disabled={statsBusy}>
            {statsBusy ? t('partner.loading') : t('partner.apps.showStats')}
          </button>
          <Msg error={statsError} />
        </form>
        {stats && (
          <div className="ptn-card" role="status">
            <h3>{stats.opportunity}</h3>
            <h4>{t('partner.apps.byExternal')}</h4>
            {rows(stats.by_external_status, 'external')}
            <h4>{t('partner.apps.byInternal')}</h4>
            {rows(stats.by_internal_status, 'internal')}
          </div>
        )}
      </section>
    </>
  )
}
