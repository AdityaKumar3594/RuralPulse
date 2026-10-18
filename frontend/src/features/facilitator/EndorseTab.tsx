import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { ErrorLine, useAction } from '../support/shared'
import { endorse, searchOpportunities } from './api'
import type { SearchHit } from './types'

export function EndorseTab({ studentId }: { studentId: string }) {
  const { t, i18n } = useTranslation()
  const search = useAction()
  const send = useAction()
  const [q, setQ] = useState('')
  const [hits, setHits] = useState<SearchHit[] | null>(null)
  const [slug, setSlug] = useState('')
  const [note, setNote] = useState('')
  const [done, setDone] = useState<string | null>(null)
  const [problem, setProblem] = useState<string | null>(null)

  const doSearch = async (e: FormEvent) => {
    e.preventDefault()
    const out = await search.run(() => searchOpportunities(q, i18n.language))
    if (out) {
      setHits(out.results)
      setSlug('')
    }
  }

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setDone(null)
    if (!slug) {
      setProblem(t('facilitator.endorse.errChoose'))
      return
    }
    setProblem(null)
    const out = await send.run(() => endorse(studentId, slug, note.trim() || null))
    if (out) {
      setDone(slug)
      setNote('')
    }
  }

  return (
    <>
      <p className="muted">{t('facilitator.endorse.intro')}</p>
      <form className="sp-form sp-box" onSubmit={doSearch}>
        <div className="sp-field">
          <label htmlFor="en-q">{t('facilitator.endorse.search')}</label>
          <input id="en-q" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        <ErrorLine message={search.error} />
        <button type="submit" className="btn btn--secondary" disabled={search.busy}>
          {search.busy ? t('common.loading') : t('facilitator.endorse.searchButton')}
        </button>
      </form>

      {hits && (
        <form className="sp-form sp-box" onSubmit={submit} noValidate>
          {hits.length === 0 ? (
            <p role="status">{t('facilitator.endorse.noResults')}</p>
          ) : (
            <fieldset style={{ border: 0, padding: 0, margin: '0 0 1rem' }}>
              <legend className="sp-label">{t('facilitator.endorse.choose')}</legend>
              {hits.map((h) => (
                <label key={h.id} className="sp-radio">
                  <input type="radio" name="en-opp" checked={slug === h.id} onChange={() => setSlug(h.id)} />
                  <span>{h.title ?? h.id}</span>
                </label>
              ))}
            </fieldset>
          )}
          {problem && <p className="error" role="alert">{problem}</p>}
          {hits.length > 0 && (
            <>
              <div className="sp-field">
                <label htmlFor="en-note">{t('facilitator.endorse.note')}</label>
                <textarea id="en-note" value={note} maxLength={300} onChange={(e) => setNote(e.target.value)} />
              </div>
              <ErrorLine message={send.error} />
              <button type="submit" className="btn" disabled={send.busy}>
                {send.busy ? t('common.loading') : t('facilitator.endorse.send')}
              </button>
            </>
          )}
        </form>
      )}
      {done && (
        <p role="status" className="sp-ok">
          {t('facilitator.endorse.sent')}
        </p>
      )}
    </>
  )
}
