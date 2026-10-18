import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router'
import { apiMessage } from '../discover/format'
import { createPlan } from './api'

/** Builds (or opens the existing) pathway for a career, then goes to it. */
export function BuildPathwayButton({ career }: { career: string }) {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const build = async () => {
    setBusy(true)
    setError(null)
    try {
      const plan = await createPlan(career, i18n.language)
      void navigate(`/pathways/${encodeURIComponent(plan.id)}`)
    } catch (err) {
      setError(apiMessage(err, t))
      setBusy(false)
    }
  }

  return (
    <div>
      <button type="button" className="btn" disabled={busy} onClick={() => void build()}>
        {t('pathway.build')}
      </button>
      {busy && <p role="status">{t('pathway.building')}</p>}
      {error && (
        <p role="alert" className="error">
          {error}{' '}
          <button type="button" className="btn btn--link" onClick={() => void build()}>
            {t('pathway.retry')}
          </button>
        </p>
      )}
    </div>
  )
}
