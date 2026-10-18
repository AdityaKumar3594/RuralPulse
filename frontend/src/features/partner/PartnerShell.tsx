import { useTranslation } from 'react-i18next'
import { NavLink, Outlet } from 'react-router'
import './partner.css'

const LINKS = [
  { to: '/partner', key: 'provider', end: true },
  { to: '/partner/submissions', key: 'submissions', end: false },
  { to: '/partner/applications', key: 'applications', end: false },
]

export function PartnerShell() {
  const { t } = useTranslation()
  return (
    <>
      <h1>{t('partner.title')}</h1>
      <nav aria-label={t('partner.sections')}>
        <ul className="ptn-nav">
          {LINKS.map((l) => (
            <li key={l.to}>
              <NavLink to={l.to} end={l.end}>
                {t(`partner.tabs.${l.key}`)}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
      <Outlet />
    </>
  )
}
