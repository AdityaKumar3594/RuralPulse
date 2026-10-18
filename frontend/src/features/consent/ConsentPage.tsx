import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Navigate, useNavigate } from 'react-router'
import { grantConsent } from '../../api/endpoints'
import { errorMessage } from '../../api/errors'
import { Field } from '../../components/Field'
import { PHONE_RE } from '../auth/validation'
import { useConsent } from './useConsent'

export function ConsentPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const consent = useConsent()
  const [agree, setAgree] = useState(false)
  const [guardianName, setGuardianName] = useState('')
  const [guardianPhone, setGuardianPhone] = useState('')
  const [errors, setErrors] = useState<{ name?: string; phone?: string; agree?: string }>({})
  const [formError, setFormError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  if (consent.phase === 'loading') return <p role="status">{t('common.loading')}</p>
  if (consent.phase === 'error') {
    return (
      <div role="alert">
        <p>{errorMessage(consent.error, t)}</p>
        <button type="button" className="btn" onClick={consent.reload}>
          {t('common.retry')}
        </button>
      </div>
    )
  }
  if (consent.valid) return <Navigate to="/interview" replace />

  const byGuardian = consent.status.required_given_by === 'guardian'

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    const found: typeof errors = {}
    if (byGuardian && !guardianName.trim()) found.name = t('errors.validation.guardianName')
    if (byGuardian && !PHONE_RE.test(guardianPhone)) found.phone = t('errors.validation.guardianPhone')
    if (!agree) found.agree = t('errors.validation.agree')
    setErrors(found)
    setFormError(null)
    if (Object.keys(found).length > 0) return
    setBusy(true)
    try {
      await grantConsent(
        byGuardian
          ? { given_by: 'guardian', guardian_name: guardianName.trim(), guardian_phone: guardianPhone }
          : { given_by: 'self' },
      )
      void navigate('/interview')
    } catch (err) {
      setFormError(errorMessage(err, t))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={(e) => void submit(e)} noValidate>
      <h1>{t('consent.title')}</h1>
      <p className="lead">{t('consent.intro')}</p>
      <ul>
        {[1, 2, 3, 4].map((n) => (
          <li key={n}>{t(`consent.point${n}`)}</li>
        ))}
      </ul>
      {byGuardian && (
        <>
          <p className="notice">{t('consent.guardianIntro')}</p>
          <Field id="guardian-name" label={t('consent.guardianName')} value={guardianName}
            onChange={(e) => setGuardianName(e.target.value)} error={errors.name} />
          <Field id="guardian-phone" label={t('consent.guardianPhone')} type="tel" inputMode="numeric"
            maxLength={10} value={guardianPhone} onChange={(e) => setGuardianPhone(e.target.value)}
            error={errors.phone} />
        </>
      )}
      <div className="field">
        <label className="check">
          <input type="checkbox" checked={agree} onChange={(e) => setAgree(e.target.checked)}
            aria-describedby={errors.agree ? 'agree-error' : undefined} />
          <span>{byGuardian ? t('consent.guardianAgree') : t('consent.selfAgree')}</span>
        </label>
        {errors.agree && (
          <p id="agree-error" className="error" role="alert">
            {errors.agree}
          </p>
        )}
      </div>
      {formError && (
        <p className="error" role="alert">
          {formError}
        </p>
      )}
      <button type="submit" className="btn btn--big" disabled={busy}>
        {t('consent.submit')}
      </button>
      <p className="muted">{t('consent.draft')}</p>
    </form>
  )
}
