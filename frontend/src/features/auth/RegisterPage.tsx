import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router'
import { errorMessage } from '../../api/errors'
import { useAuth } from '../../auth/AuthContext'
import { Field } from '../../components/Field'
import { PHONE_RE, PIN_RE } from './validation'

type Errors = Partial<Record<'name' | 'phone' | 'pin' | 'dob', string>>

export function RegisterPage() {
  const { t } = useTranslation()
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ name: '', phone: '', pin: '', dob: '' })
  const [errors, setErrors] = useState<Errors>({})
  const [formError, setFormError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const set = (k: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [k]: e.target.value }))

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    const found: Errors = {}
    if (!form.name.trim()) found.name = t('errors.validation.name')
    if (!PHONE_RE.test(form.phone)) found.phone = t('errors.validation.phone')
    if (!PIN_RE.test(form.pin)) found.pin = t('errors.validation.pin')
    if (!form.dob) found.dob = t('errors.validation.dob')
    setErrors(found)
    setFormError(null)
    if (Object.keys(found).length > 0) return
    setBusy(true)
    try {
      await register({
        display_name: form.name.trim(),
        phone: form.phone,
        pin: form.pin,
        date_of_birth: form.dob,
      })
      void navigate('/consent')
    } catch (err) {
      setFormError(errorMessage(err, t))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={(e) => void submit(e)} noValidate>
      <h1>{t('auth.register.title')}</h1>
      <Field id="name" label={t('auth.register.name')} autoComplete="name" value={form.name}
        onChange={set('name')} error={errors.name} />
      <Field id="phone" label={t('auth.register.phone')} hint={t('auth.register.phoneHint')}
        type="tel" inputMode="numeric" autoComplete="tel-national" maxLength={10}
        value={form.phone} onChange={set('phone')} error={errors.phone} />
      <Field id="pin" label={t('auth.register.pin')} hint={t('auth.register.pinHint')}
        type="password" inputMode="numeric" autoComplete="new-password" maxLength={6}
        value={form.pin} onChange={set('pin')} error={errors.pin} />
      <Field id="dob" label={t('auth.register.dob')} type="date" autoComplete="bday"
        value={form.dob} onChange={set('dob')} error={errors.dob} />
      {formError && (
        <p className="error" role="alert">
          {formError}
        </p>
      )}
      <button type="submit" className="btn btn--big" disabled={busy}>
        {busy ? t('common.loading') : t('auth.register.submit')}
      </button>
      <p>
        <Link to="/login">{t('auth.register.haveAccount')}</Link>
      </p>
    </form>
  )
}
