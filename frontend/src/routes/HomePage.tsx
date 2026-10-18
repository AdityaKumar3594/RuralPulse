import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'
import { homeWidgets, navItems, type Role } from '../app/registry'
import { useAuth } from '../auth/AuthContext'
import { BackendStatus } from '../features/system/BackendStatus'

export function HomePage() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const visibleNavItems = user ? navItems.filter((n) => n.roles.includes(user.role as Role)) : []

  return (
    <>
      <section className="home-hero" aria-labelledby="home-title">
        <div>
          <p className="home-hero__eyebrow">Learning to livelihood</p>
          <h1 id="home-title">{user ? t('home.hello', { name: user.display_name }) : t('home.welcome')}</h1>
          <p className="lead">{t('home.tagline')}</p>
        </div>
        <aside className="home-hero__aside" aria-label="Ruralpulse promise">
          <strong>One step at a time.</strong>
          <p>Discover what fits you, build confidence, and move towards an opportunity that feels real.</p>
        </aside>
      </section>

      <section className="home-section" aria-labelledby="home-actions-title">
        <div className="home-section__heading">
          <div>
            <h2 id="home-actions-title">Your next move</h2>
            <p>Everything you need, in one place.</p>
          </div>
        </div>
        <div className="action-grid">
          {user ? (
            visibleNavItems.map((n, i) => (
              <Link key={n.to} className={`action-card${i === 0 ? ' action-card--primary' : ''}`} to={n.to}>
                <span className="action-card__index">{String(i + 1).padStart(2, '0')}</span>
                <span className="action-card__label">{t(n.labelKey)}</span>
                <span className="action-card__arrow" aria-hidden="true">↗</span>
              </Link>
            ))
          ) : (
            <>
              <Link className="action-card action-card--primary" to="/register">
                <span className="action-card__index">01</span>
                <span className="action-card__label">{t('home.register')}</span>
                <span className="action-card__arrow" aria-hidden="true">↗</span>
              </Link>
              <Link className="action-card" to="/login">
                <span className="action-card__index">02</span>
                <span className="action-card__label">{t('home.login')}</span>
                <span className="action-card__arrow" aria-hidden="true">↗</span>
              </Link>
            </>
          )}
        </div>
      </section>

      {user && homeWidgets.map((w) => <div key={w.id}>{w.element}</div>)}
      <BackendStatus />
    </>
  )
}
