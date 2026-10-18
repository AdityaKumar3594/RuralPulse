import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'
import { saveApplication } from './api'
import { ErrorLine, useAction } from '../support/shared'

/** Saves an opportunity to track, then links to the tracking page. Tracking does not apply for the student. */
export function SaveOpportunityButton({ slug }: { slug: string }) {
  const { t, i18n } = useTranslation()
  const { run, busy, error } = useAction()
  const [savedId, setSavedId] = useState<string | null>(null)

  const save = async () => {
    const app = await run(() => saveApplication(slug, i18n.language))
    if (app) setSavedId(app.id)
  }

  return (
    <div>
      {savedId ? (
        <p role="status">
          {t('applications.save.done')}{' '}
          <Link className="btn btn--secondary" to={`/applications/${encodeURIComponent(savedId)}`}>
            {t('applications.save.open')}
          </Link>
        </p>
      ) : (
        <>
          <button type="button" className="btn btn--secondary" disabled={busy} onClick={save}>
            {busy ? t('common.loading') : t('applications.save.button')}
          </button>
          <p className="muted">{t('applications.save.hint')}</p>
        </>
      )}
      <ErrorLine message={error} />
    </div>
  )
}
