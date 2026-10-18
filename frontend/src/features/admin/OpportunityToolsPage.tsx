import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { useSearchParams } from 'react-router'
import { reverify, withdrawOpportunity } from './api'
import { errText, Msg } from './common'
import {
  checkVerification,
  emptyVerification,
  usedEvidence,
  VerificationForm,
  type VerificationValue,
} from './VerificationForm'

export function OpportunityToolsPage() {
  const { t } = useTranslation()
  const [params] = useSearchParams()
  const [slug, setSlug] = useState(params.get('slug') ?? '')
  const [ver, setVer] = useState<VerificationValue>(emptyVerification)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [ok, setOk] = useState<string | null>(null)

  const cleanSlug = slug.trim()

  async function onReverify(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setOk(null)
    if (!cleanSlug) return setError(t('admin.tools.slugRequired'))
    if (ver.fields.length === 0) return setError(t('admin.tools.tickOne'))
    const problem = checkVerification(ver, t)
    if (problem) return setError(problem)
    setBusy(true)
    try {
      await reverify(cleanSlug, ver.fields, usedEvidence(ver))
      setOk(t('admin.tools.reverified', { slug: cleanSlug }))
    } catch (err) {
      setError(errText(err, t))
    } finally {
      setBusy(false)
    }
  }

  async function onWithdraw() {
    setError(null)
    setOk(null)
    if (!cleanSlug) return setError(t('admin.tools.slugRequired'))
    if (!window.confirm(t('admin.tools.confirmWithdraw', { slug: cleanSlug }))) return
    setBusy(true)
    try {
      await withdrawOpportunity(cleanSlug)
      setOk(t('admin.tools.withdrawn', { slug: cleanSlug }))
    } catch (err) {
      setError(errText(err, t))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section aria-labelledby="adm-op-h">
      <h2 id="adm-op-h">{t('admin.tools.title')}</h2>
      <p className="muted">{t('admin.tools.intro')}</p>
      <form className="adm-form" onSubmit={onReverify} noValidate>
        <div className="field">
          <label htmlFor="adm-slug">{t('admin.tools.slug')}</label>
          <input id="adm-slug" type="text" autoCapitalize="none" autoCorrect="off" value={slug} onChange={(e) => setSlug(e.target.value)} />
        </div>
        <h3>{t('admin.tools.reverifyTitle')}</h3>
        <p className="muted">{t('admin.tools.reverifyHint')}</p>
        <VerificationForm value={ver} onChange={setVer} />
        <button type="submit" className="btn btn--big" disabled={busy}>
          {busy ? t('admin.saving') : t('admin.tools.reverify')}
        </button>
        <h3>{t('admin.tools.withdrawTitle')}</h3>
        <p className="muted">{t('admin.tools.withdrawHint')}</p>
        <button type="button" className="btn btn--danger btn--big" disabled={busy} onClick={() => void onWithdraw()}>
          {t('admin.tools.withdraw')}
        </button>
        <Msg error={error} ok={ok} />
      </form>
    </section>
  )
}
