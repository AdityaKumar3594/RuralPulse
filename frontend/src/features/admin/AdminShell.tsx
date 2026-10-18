import { useTranslation } from 'react-i18next'
import { NavLink, Outlet } from 'react-router'
import './admin.css'

const LINKS = [
  { to: '/admin', key: 'users', end: true },
  { to: '/admin/assignments', key: 'assignments', end: false },
  { to: '/admin/providers', key: 'providers', end: false },
  { to: '/admin/review', key: 'review', end: false },
  { to: '/admin/opportunities', key: 'opportunities', end: false },
]

export function AdminShell() {
  const { t } = useTranslation()
  return (
    <>
      <h1>{t('admin.title')}</h1>
      <nav aria-label={t('admin.sections')}>
        <ul className="adm-nav">
          {LINKS.map((l) => (
            <li key={l.to}>
              <NavLink to={l.to} end={l.end}>
                {t(`admin.tabs.${l.key}`)}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
      <Outlet />
    </>
  )
}
