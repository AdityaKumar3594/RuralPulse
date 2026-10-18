import { useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router'
import { ErrorLine, LoadGate, safeHttps, useAction, useLoad } from '../support/shared'
import { enroll, getModule, setLessonDone } from './api'
import { priceText } from './price'
import type { TrainingModule } from './types'

export function ModuleDetailPage() {
  const { id = '' } = useParams()
  const { t } = useTranslation()
  const load = useCallback((o: { signal: AbortSignal }) => getModule(id, o), [id])
  const { state, reload, setData } = useLoad(load)
  return (
    <>
      <p>
        <Link to="/modules">{t('training.back')}</Link>
      </p>
      <LoadGate state={state} reload={reload}>
        {(m) => <Detail m={m} onChange={setData} />}
      </LoadGate>
    </>
  )
}

function Detail({ m, onChange }: { m: TrainingModule; onChange: (m: TrainingModule) => void }) {
  const { t } = useTranslation()
  const { run, busy, error } = useAction()
  const paid = m.price_type !== 'free'
  const locked = !m.access
  const lessons = m.lessons

  const doEnroll = async () => {
    const out = await run(() => enroll(m.id))
    if (out) onChange(out)
  }
  const toggle = async (index: number, done: boolean) => {
    const out = await run(() => setLessonDone(m.id, index, done))
    if (out) onChange(out)
  }

  return (
    <>
      <h1>{m.title}</h1>
      <p className="lead">{m.description}</p>
      <p className="muted">
        {t(`training.language.${m.language}`, { defaultValue: m.language })} · {priceText(t, m)}
      </p>
      <ErrorLine message={error} />

      {!m.enrolled && (
        <section className="sp-box" aria-labelledby="tr-enroll">
          <h2 id="tr-enroll">{t('training.join.title')}</h2>
          {paid && <p className="notice">{t('training.join.paidNotice')}</p>}
          <button type="button" className="btn" disabled={busy} onClick={doEnroll}>
            {busy ? t('common.loading') : paid ? t('training.join.reserve') : t('training.join.enroll')}
          </button>
        </section>
      )}

      {m.enrolled && locked && (
        <section className="sp-box" role="status">
          <h2>{t('training.locked.title')}</h2>
          <p className="notice">
            {m.payment_status === 'unpaid_no_gateway' || !m.payments_available
              ? t('training.locked.noPayment')
              : t('training.locked.generic')}
          </p>
        </section>
      )}

      {m.enrolled && !locked && (
        <p>
          <span className="sp-tag sp-tag--ok">
            <span aria-hidden="true">✓ </span>
            {t('training.enrolledTag')}
          </span>
        </p>
      )}

      <section aria-labelledby="tr-lessons">
        <h2 id="tr-lessons">{t('training.lessons.title')}</h2>
        {!locked && lessons ? (
          <>
            <p>{t('training.lessons.progress', { done: m.completed_lessons.length, total: lessons.length })}</p>
            <progress
              max={lessons.length}
              value={m.completed_lessons.length}
              aria-label={t('training.lessons.progress', { done: m.completed_lessons.length, total: lessons.length })}
            />
            <ol className="sp-list">
              {lessons.map((l, i) => {
                const done = m.completed_lessons.includes(i)
                const href = safeHttps(l.url)
                return (
                  <li key={i} className="sp-card">
                    <h3>{l.title}</h3>
                    <p style={{ whiteSpace: 'pre-wrap' }}>{l.body}</p>
                    {href && (
                      <p>
                        <a href={href} target="_blank" rel="noopener noreferrer">
                          {t('training.lessons.link')}
                        </a>
                      </p>
                    )}
                    {m.enrolled && (
                      <label className="check">
                        <input type="checkbox" checked={done} disabled={busy} onChange={(e) => toggle(i, e.target.checked)} />
                        <span>{t('training.lessons.markDone')}</span>
                      </label>
                    )}
                  </li>
                )
              })}
            </ol>
          </>
        ) : (
          <>
            <p className="muted">{t('training.lessons.titlesOnly')}</p>
            <ol>
              {m.lesson_titles.map((title, i) => (
                <li key={i}>{title}</li>
              ))}
            </ol>
          </>
        )}
      </section>
    </>
  )
}
