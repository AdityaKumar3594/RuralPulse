import { useTranslation } from 'react-i18next'
import { Link, NavLink, Outlet } from 'react-router'
import { navItems, type Role } from '../app/registry'
import { useAuth } from '../auth/AuthContext'
import { SUPPORTED_LANGUAGES } from '../i18n/config'

export function Layout() {
  const { t, i18n } = useTranslation()
  const { user, logout } = useAuth()
  return (
    <>
      <a className="skip-link" href="#main">
        {t('common.skipToContent')}
      </a>
      <header className="topbar">
        <Link to="/home" className="topbar__brand" aria-label={t('app.name')}>
          {t('app.name')}
        </Link>
        <nav className="topbar__actions" aria-label={t('language.title')}>
          {SUPPORTED_LANGUAGES.map((l) => (
            <button
              key={l.code}
              type="button"
              lang={l.code}
              className="chip"
              aria-pressed={i18n.language === l.code}
              onClick={() => void i18n.changeLanguage(l.code)}
            >
              {l.nativeName}
            </button>
          ))}
          {user && (
            <button type="button" className="chip" onClick={logout}>
              {t('common.logout')}
            </button>
          )}
        </nav>
      </header>
      {user && (
        <nav className="mainnav" aria-label={t('app.name')}>
          {navItems
            .filter((n) => n.roles.includes(user.role as Role))
            .map((n) => (
              <NavLink key={n.to} to={n.to} className="mainnav__link">
                {t(n.labelKey)}
              </NavLink>
            ))}
        </nav>
      )}
      <main id="main" className="page" tabIndex={-1}>
        <Outlet />
      </main>
    </>
  )
}
