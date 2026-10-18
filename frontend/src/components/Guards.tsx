import { useTranslation } from 'react-i18next'
import { Navigate, Outlet } from 'react-router'
import { errorMessage } from '../api/errors'
import { useAuth } from '../auth/AuthContext'
import type { Role } from '../app/registry'
import { useConsent } from '../features/consent/useConsent'

export function RequireAuth() {
  const { user } = useAuth()
  return user ? <Outlet /> : <Navigate to="/login" replace />
}

/** Student screens that read or write the profile need valid consent first. */
export function RequireConsent() {
  const { t } = useTranslation()
  const consent = useConsent()
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
  return consent.valid ? <Outlet /> : <Navigate to="/consent" replace />
}

/** Staff screens: the server enforces permissions; this just keeps other roles off the page. */
export function RequireRole({ roles }: { roles: Role[] }) {
  const { user } = useAuth()
  return user && roles.includes(user.role as Role) ? <Outlet /> : <Navigate to="/home" replace />
}
