import { useCallback, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router'
import { LoadGate, useLoad } from '../support/shared'
import { ApplicationsTab } from './ApplicationsTab'
import { EndorseTab } from './EndorseTab'
import { PathwaysTab } from './PathwaysTab'
import { ProfileTab } from './ProfileTab'
import { RecsTab } from './RecsTab'
import { getProfile } from './api'

const TABS = ['profile', 'recs', 'endorse', 'pathways', 'apps'] as const
type Tab = (typeof TABS)[number]

export function StudentPage() {
  const { id = '' } = useParams()
  const { t } = useTranslation()
  const load = useCallback((o: { signal: AbortSignal }) => getProfile(id, o), [id])
  const { state, reload } = useLoad(load)
  const [tab, setTab] = useState<Tab>('profile')

  return (
    <>
      <p>
        <Link to="/facilitator">{t('facilitator.back')}</Link>
      </p>
      <LoadGate state={state} reload={reload}>
        {(profile) => (
          <>
            <h1>{profile.student.display_name}</h1>
            <p>
              {profile.student.is_minor && <span className="sp-tag sp-tag--info">{t('facilitator.students.minor')}</span>}
            </p>
            <nav aria-label={t('facilitator.tabs.label')}>
              <ul className="sp-tabs">
                {TABS.map((k) => (
                  <li key={k}>
                    <button type="button" aria-current={tab === k ? 'true' : undefined} onClick={() => setTab(k)}>
                      {t(`facilitator.tabs.${k}`)}
                    </button>
                  </li>
                ))}
              </ul>
            </nav>
            <section aria-labelledby="fs-tab-title">
              <h2 id="fs-tab-title">{t(`facilitator.tabs.${tab}`)}</h2>
              {tab === 'profile' && <ProfileTab profile={profile} onChanged={reload} />}
              {tab === 'recs' && <RecsTab studentId={id} />}
              {tab === 'endorse' && <EndorseTab studentId={id} />}
              {tab === 'pathways' && <PathwaysTab studentId={id} />}
              {tab === 'apps' && <ApplicationsTab studentId={id} />}
            </section>
          </>
        )}
      </LoadGate>
    </>
  )
}
