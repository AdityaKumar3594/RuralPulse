import { useCallback, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { listProviders, setProvider } from './api'
import { errText, LoadState, Msg, useLoad } from './common'

export function ProvidersPage() {
  const { t } = useTranslation()
  const [status, setStatus] = useState('')
  const load = useCallback((o: { signal: AbortSignal }) => listProviders(status || undefined, o), [status])
  const { state, reload } = useLoad(load)
  const [error, setError] = useState<string | null>(null)
  const [ok, setOk] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<string | null>(null)

  async function act(id: string, action: 'approve' | 'suspend') {
    setError(null)
    setOk(null)
    setBusyId(id)
    try {
      const p = await setProvider(id, action)
      setOk(t(`admin.providers.done.${action}`, { name: p.name }))
      reload()
    } catch (err) {
      setError(errText(err, t))
    } finally {
      setBusyId(null)
    }
  }

  return (
    <section aria-labelledby="adm-pr-h">
      <h2 id="adm-pr-h">{t('admin.providers.title')}</h2>
      <div className="field adm-form">
        <label htmlFor="adm-pr-status">{t('admin.providers.filter')}</label>
        <select id="adm-pr-status" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">{t('admin.users.all')}</option>
          {['pending', 'approved', 'suspended'].map((s) => (
            <option key={s} value={s}>
              {t(`admin.providers.status.${s}`)}
            </option>
          ))}
        </select>
      </div>
      <Msg error={error} ok={ok} />
      <LoadState state={state} onRetry={reload} />
      {state.phase === 'ready' &&
        (state.data.length === 0 ? (
          <p role="status">{t('admin.providers.empty')}</p>
        ) : (
          <ul className="adm-list">
            {state.data.map((p) => (
              <li key={p.id} className="adm-card">
                <h3>{p.name}</h3>
                <p>
                  <span className="badge">{t(`admin.providers.status.${p.status}`)}</span>{' '}
                  {t(`admin.providers.kind.${p.kind}`, { defaultValue: p.kind })}
                </p>
                <p>
                  <a href={p.website} target="_blank" rel="noopener noreferrer">
                    {p.website}
                  </a>
                </p>
                {p.description && <p>{p.description}</p>}
                <div className="adm-actions">
                  {p.status !== 'approved' && (
                    <button type="button" className="btn" disabled={busyId === p.id} onClick={() => void act(p.id, 'approve')}>
                      {t('admin.providers.approve')}
                    </button>
                  )}
                  {p.status !== 'suspended' && (
                    <button type="button" className="btn btn--danger" disabled={busyId === p.id} onClick={() => void act(p.id, 'suspend')}>
                      {t('admin.providers.suspend')}
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        ))}
    </section>
  )
}
