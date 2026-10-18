import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router'
import { errorMessage } from '../../api/errors'
import { useAuth } from '../../auth/AuthContext'
import { Field } from '../../components/Field'
import { PHONE_RE, PIN_RE } from './validation'

export function LoginPage() {
  const { t } = useTranslation()
  const { login } = useAuth()
  const navigate = useNavigate()
  const [phone, setPhone] = useState('')
  const [pin, setPin] = useState('')
  const [errors, setErrors] = useState<{ phone?: string; pin?: string }>({})
  const [formError, setFormError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    const found: typeof errors = {}
    if (!PHONE_RE.test(phone)) found.phone = t('errors.validation.phone')
    if (!PIN_RE.test(pin)) found.pin = t('errors.validation.pin')
    setErrors(found)
    setFormError(null)
    if (Object.keys(found).length > 0) return
    setBusy(true)
    try {
      await login(phone, pin)
      void navigate('/home')
    } catch (err) {
      setFormError(errorMessage(err, t))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={(e) => void submit(e)} noValidate>
      <h1>{t('auth.login.title')}</h1>
      <Field id="phone" label={t('auth.register.phone')} type="tel" inputMode="numeric"
        autoComplete="tel-national" maxLength={10} value={phone}
        onChange={(e) => setPhone(e.target.value)} error={errors.phone} />
      <Field id="pin" label={t('auth.register.pin')} type="password" inputMode="numeric"
        autoComplete="current-password" maxLength={6} value={pin}
        onChange={(e) => setPin(e.target.value)} error={errors.pin} />
      {formError && (
        <p className="error" role="alert">
          {formError}
        </p>
      )}
      <button type="submit" className="btn btn--big" disabled={busy}>
        {busy ? t('common.loading') : t('auth.login.submit')}
      </button>
      <p>
        <Link to="/register">{t('auth.login.noAccount')}</Link>
      </p>
    </form>
  )
}
