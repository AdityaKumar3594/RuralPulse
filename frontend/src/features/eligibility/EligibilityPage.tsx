import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router'
import { EligibilityCheck } from './EligibilityCheck'

/** Full-page flow: runs the check straight away for /eligibility/:slug. */
export function EligibilityPage() {
  const { slug = '' } = useParams()
  const { t } = useTranslation()
  return (
    <>
      <h1>{t('eligibility.pageTitle')}</h1>
      <p className="lead">{t('eligibility.pageIntro')}</p>
      <EligibilityCheck key={slug} slug={slug} autoRun />
      <p>
        <Link to={`/opportunities/${encodeURIComponent(slug)}`}>{t('eligibility.backToOpportunity')}</Link>
      </p>
    </>
  )
}
