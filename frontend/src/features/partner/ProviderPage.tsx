import { useCallback, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { ApiError } from '../../api/client'
import { Field } from '../../components/Field'
import { createProvider, getProvider, updateProvider } from './api'
import { errText, LoadState, Msg, useLoad, type Loaded } from './common'
import { PROVIDER_KINDS, type Provider } from './types'

type Result = { provider: Provider | null }

export function ProviderPage() {
  const { t } = useTranslation()
  const load = useCallback(async (o: { signal: AbortSignal }): Promise<Result> => {
    try {
      return { provider: await getProvider(o) }
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) return { provider: null }
      throw e
    }
  }, [])
  const { state, reload } = useLoad(load)
  return (
    <section aria-labelledby="ptn-prov-h">
      <h2 id="ptn-prov-h">{t('partner.provider.title')}</h2>
      <LoadState state={state as Loaded<unknown>} onRetry={reload} />
      {state.phase === 'ready' && <ProviderForm key={state.data.provider?.id ?? 'new'} provider={state.data.provider} onSaved={reload} />}
    </section>
  )
}

function ProviderForm({ provider, onSaved }: { provider: Provider | null; onSaved: () => void }) {
  const { t } = useTranslation()
  const locked = provider !== null && provider.status !== 'pending'
  const [name, setName] = useState(provider?.name ?? '')
  const [kind, setKind] = useState(provider?.kind ?? 'ngo')
  const [website, setWebsite] = useState(provider?.website ?? '')
  const [description, setDescription] = useState(provider?.description ?? '')
  const [errs, setErrs] = useState<{ name?: string; website?: string }>({})
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [ok, setOk] = useState<string | null>(null)

  async function submit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setOk(null)
    const next = {
      name: locked || name.trim().length >= 2 ? undefined : t('partner.provider.nameInvalid'),
      website: locked || website.trim().startsWith('https://') ? undefined : t('partner.errors.url_must_be_https'),
    }
    setErrs(next)
    if (next.name || next.website) return
    setBusy(true)
    try {
      const desc = description.trim() || null
      if (!provider) {
        await createProvider({ name: name.trim(), kind, website: website.trim(), description: desc })
      } else if (locked) {
        await updateProvider({ description: desc })
      } else {
        await updateProvider({ name: name.trim(), kind, website: website.trim(), description: desc })
      }
      setOk(t('partner.provider.saved'))
      onSaved()
    } catch (err) {
      setError(errText(err, t))
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      {provider ? (
        <div className="ptn-card" role="status">
          <p>
            <span className="badge">{t(`partner.provider.status.${provider.status}`)}</span>
          </p>
          <p>{t(`partner.provider.explain.${provider.status}`)}</p>
        </div>
      ) : (
        <p className="notice">{t('partner.provider.none')}</p>
      )}
      {locked && <p className="muted">{t('partner.errors.identity_locked_after_approval')}</p>}
      <form className="ptn-form" onSubmit={submit} noValidate>
        <Field id="ptn-pname" label={t('partner.provider.name')} value={name} disabled={locked} error={errs.name} onChange={(e) => setName(e.target.value)} />
        <div className="field">
          <label htmlFor="ptn-pkind">{t('partner.provider.kind')}</label>
          <select id="ptn-pkind" value={kind} disabled={locked} onChange={(e) => setKind(e.target.value)}>
            {PROVIDER_KINDS.map((k) => (
              <option key={k} value={k}>
                {t(`partner.provider.kinds.${k}`)}
              </option>
            ))}
          </select>
        </div>
        <Field id="ptn-pweb" type="url" inputMode="url" placeholder="https://" label={t('partner.provider.website')} hint={t('partner.provider.websiteHint')} value={website} disabled={locked} error={errs.website} onChange={(e) => setWebsite(e.target.value)} />
        <div className="field">
          <label htmlFor="ptn-pdesc">{t('partner.provider.description')}</label>
          <textarea id="ptn-pdesc" maxLength={1000} value={description} onChange={(e) => setDescription(e.target.value)} />
        </div>
        <button type="submit" className="btn btn--big" disabled={busy}>
          {busy ? t('partner.saving') : provider ? t('partner.provider.save') : t('partner.provider.create')}
        </button>
        <Msg error={error} ok={ok} />
      </form>
    </>
  )
}
