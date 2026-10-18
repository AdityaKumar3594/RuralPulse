import { useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'
import { ErrorLine, LoadGate, useAction, useLoad } from '../support/shared'
import { listMine, publishModule, withdrawModule } from './api'
import { priceText } from './price'
import type { FacilitatorModule } from './types'

export function FacilitatorModulesPage() {
  const { t } = useTranslation()
  const load = useCallback((o: { signal: AbortSignal }) => listMine(o), [])
  const { state, reload, setData } = useLoad(load)
  return (
    <>
      <h1>{t('training.mine.title')}</h1>
      <p className="lead">{t('training.mine.intro')}</p>
      <Link className="btn" to="/facilitator/modules/new">
        {t('training.mine.create')}
      </Link>
      <LoadGate state={state} reload={reload}>
        {(list) =>
          list.length === 0 ? (
            <p role="status">{t('training.mine.empty')}</p>
          ) : (
            <ul className="sp-list" style={{ marginTop: '1rem' }}>
              {list.map((row) => (
                <Row
                  key={row.module.id}
                  row={row}
                  onChanged={(m) => setData(list.map((r) => (r.module.id === m.id ? { ...r, module: m } : r)))}
                />
              ))}
            </ul>
          )
        }
      </LoadGate>
    </>
  )
}

function Row({ row, onChanged }: { row: FacilitatorModule; onChanged: (m: FacilitatorModule['module']) => void }) {
  const { t } = useTranslation()
  const { run, busy, error } = useAction()
  const m = row.module
  const act = async (fn: typeof publishModule) => {
    const out = await run(() => fn(m.id))
    if (out) onChanged(out)
  }
  return (
    <li className="sp-card">
      <h2>{m.title}</h2>
      <p>
        <span className={m.status === 'published' ? 'sp-tag sp-tag--ok' : 'sp-tag sp-tag--warn'}>
          {t(`training.mine.status.${m.status}`, { defaultValue: m.status })}
        </span>
      </p>
      <p className="muted">
        {t('training.mine.counts', { enrolled: row.enrollments, lessons: m.lesson_titles.length })} · {priceText(t, m)}
      </p>
      <ErrorLine message={error} />
      <div className="sp-row">
        <Link className="btn btn--secondary" to={`/facilitator/modules/${encodeURIComponent(m.id)}`}>
          {t('training.mine.edit')}
          <span className="visually-hidden">: {m.title}</span>
        </Link>
        {m.status !== 'published' && (
          <button type="button" className="btn" disabled={busy} onClick={() => act(publishModule)}>
            {t('training.mine.publish')}
          </button>
        )}
        {m.status === 'published' && (
          <button type="button" className="btn btn--secondary" disabled={busy} onClick={() => act(withdrawModule)}>
            {t('training.mine.withdraw')}
          </button>
        )}
      </div>
    </li>
  )
}
