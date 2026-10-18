import { useCallback, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Field } from '../../components/Field'
import { createStaff, listUsers } from './api'
import { errText, LoadState, Msg, useLoad } from './common'
import type { StaffRole } from './types'

const PHONE = /^[6-9]\d{9}$/
const PIN = /^\d{6,12}$/

export function UsersPage() {
  const { t } = useTranslation()
  const [role, setRole] = useState('')
  const load = useCallback((o: { signal: AbortSignal }) => listUsers(role || undefined, o), [role])
  const { state, reload } = useLoad(load)

  const [newRole, setNewRole] = useState<StaffRole>('facilitator')
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [pin, setPin] = useState('')
  const [errs, setErrs] = useState<{ name?: string; phone?: string; pin?: string }>({})
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [ok, setOk] = useState<string | null>(null)

  async function submit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setOk(null)
    const next = {
      name: name.trim().length >= 1 ? undefined : t('admin.users.nameInvalid'),
      phone: PHONE.test(phone) ? undefined : t('admin.users.phoneInvalid'),
      pin: PIN.test(pin) ? undefined : t('admin.users.pinInvalid'),
    }
    setErrs(next)
    if (next.name || next.phone || next.pin) return
    setBusy(true)
    try {
      const u = await createStaff({ role: newRole, phone, pin, display_name: name.trim() })
      setOk(t('admin.users.created', { name: u.display_name }))
      setName('')
      setPhone('')
      setPin('')
      reload()
    } catch (err) {
      setError(errText(err, t))
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <section aria-labelledby="adm-users-h">
        <h2 id="adm-users-h">{t('admin.users.listTitle')}</h2>
        <div className="field adm-form">
          <label htmlFor="adm-role">{t('admin.users.filter')}</label>
          <select id="adm-role" value={role} onChange={(e) => setRole(e.target.value)}>
            <option value="">{t('admin.users.all')}</option>
            {['student', 'facilitator', 'partner', 'admin'].map((r) => (
              <option key={r} value={r}>
                {t(`admin.roles.${r}`)}
              </option>
            ))}
          </select>
        </div>
        <LoadState state={state} onRetry={reload} />
        {state.phase === 'ready' &&
          (state.data.length === 0 ? (
            <p role="status">{t('admin.users.empty')}</p>
          ) : (
            <ul className="adm-list">
              {state.data.map((u) => (
                <li key={u.id} className="adm-card">
                  <h3>{u.display_name}</h3>
                  <p>
                    {t(`admin.roles.${u.role}`, { defaultValue: u.role })} · {u.phone}
                    {!u.is_active && ` · ${t('admin.users.inactive')}`}
                  </p>
                </li>
              ))}
            </ul>
          ))}
      </section>

      <section aria-labelledby="adm-new-h">
        <h2 id="adm-new-h">{t('admin.users.createTitle')}</h2>
        <p className="muted">{t('admin.users.createHint')}</p>
        <form className="adm-form" onSubmit={submit} noValidate>
          <div className="field">
            <label htmlFor="adm-newrole">{t('admin.users.role')}</label>
            <select id="adm-newrole" value={newRole} onChange={(e) => setNewRole(e.target.value as StaffRole)}>
              <option value="facilitator">{t('admin.roles.facilitator')}</option>
              <option value="partner">{t('admin.roles.partner')}</option>
            </select>
          </div>
          <Field id="adm-name" label={t('admin.users.name')} value={name} error={errs.name} autoComplete="off" onChange={(e) => setName(e.target.value)} />
          <Field id="adm-phone" label={t('admin.users.phone')} hint={t('admin.users.phoneHint')} value={phone} error={errs.phone} inputMode="numeric" autoComplete="off" onChange={(e) => setPhone(e.target.value.trim())} />
          <Field id="adm-pin" label={t('admin.users.pin')} hint={t('admin.users.pinHint')} value={pin} error={errs.pin} inputMode="numeric" autoComplete="new-password" onChange={(e) => setPin(e.target.value.trim())} />
          <button type="submit" className="btn btn--big" disabled={busy}>
            {busy ? t('admin.saving') : t('admin.users.create')}
          </button>
          <Msg error={error} ok={ok} />
        </form>
      </section>
    </>
  )
}
