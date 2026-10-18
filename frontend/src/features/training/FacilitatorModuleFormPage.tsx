import { useCallback, useRef, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useParams } from 'react-router'
import { Field } from '../../components/Field'
import { ErrorLine, LoadGate, useAction, useLoad } from '../support/shared'
import { createModule, listMine, updateModule } from './api'
import type { ModuleBody, PriceType, TrainingModule } from './types'

export function FacilitatorModuleFormPage() {
  const { id } = useParams()
  const { t } = useTranslation()
  const load = useCallback((o: { signal: AbortSignal }) => (id ? listMine(o) : Promise.resolve(null)), [id])
  const { state, reload } = useLoad(load)
  return (
    <>
      <p>
        <Link to="/facilitator/modules">{t('training.form.back')}</Link>
      </p>
      <h1>{id ? t('training.form.editTitle') : t('training.form.createTitle')}</h1>
      <LoadGate state={state} reload={reload}>
        {(rows) => {
          const existing = id ? (rows?.find((r) => r.module.id === id)?.module ?? null) : null
          if (id && !existing) return <p role="alert" className="error">{t('support.err.not_found')}</p>
          return <ModuleForm existing={existing} />
        }}
      </LoadGate>
    </>
  )
}

interface LessonDraft {
  key: number
  title: string
  body: string
  url: string
}

function ModuleForm({ existing }: { existing: TrainingModule | null }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { run, busy, error } = useAction()
  const nextKey = useRef(1000)
  const [title, setTitle] = useState(existing?.title ?? '')
  const [description, setDescription] = useState(existing?.description ?? '')
  const [language, setLanguage] = useState<'ta' | 'en'>(existing?.language === 'en' ? 'en' : 'ta')
  const [priceType, setPriceType] = useState<PriceType>((existing?.price_type as PriceType) ?? 'free')
  const [price, setPrice] = useState(existing?.price_inr ? String(existing.price_inr) : '')
  const [lessons, setLessons] = useState<LessonDraft[]>(
    (existing?.lessons ?? []).map((l, i) => ({ key: i, title: l.title, body: l.body, url: l.url ?? '' })),
  )
  const [problems, setProblems] = useState<Record<string, string>>({})

  const setLesson = (key: number, patch: Partial<LessonDraft>) =>
    setLessons((ls) => ls.map((l) => (l.key === key ? { ...l, ...patch } : l)))

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    const found: Record<string, string> = {}
    if (title.trim().length < 3) found.title = t('training.form.errTitle')
    if (description.trim().length < 3) found.description = t('training.form.errDescription')
    let priceNum: number | null = null
    if (priceType !== 'free') {
      priceNum = /^\d+$/.test(price.trim()) ? Number(price) : NaN
      if (!Number.isInteger(priceNum) || priceNum < 1 || priceNum > 100000) found.price = t('training.form.errPrice')
    }
    for (const l of lessons) {
      if (!l.title.trim()) found[`lt${l.key}`] = t('training.form.errLessonTitle')
      if (l.url.trim() && !l.url.trim().startsWith('https://')) found[`lu${l.key}`] = t('training.form.errUrl')
    }
    setProblems(found)
    if (Object.keys(found).length > 0) return
    const body: ModuleBody = {
      title: title.trim(),
      description: description.trim(),
      language,
      price_type: priceType,
      price_inr: priceType === 'free' ? null : priceNum,
      lessons: lessons.map((l) => ({ title: l.title.trim(), body: l.body, url: l.url.trim() || null })),
    }
    const out = await run(() => (existing ? updateModule(existing.id, body) : createModule(body)))
    if (out) navigate('/facilitator/modules')
  }

  return (
    <form className="sp-form" onSubmit={submit} noValidate>
      <Field id="tm-title" label={t('training.form.title')} value={title} maxLength={150} onChange={(e) => setTitle(e.target.value)} error={problems.title} />
      <div className="sp-field">
        <label htmlFor="tm-desc">{t('training.form.description')}</label>
        <textarea id="tm-desc" value={description} maxLength={1000} onChange={(e) => setDescription(e.target.value)} aria-invalid={problems.description ? true : undefined} />
        {problems.description && <p className="error" role="alert">{problems.description}</p>}
      </div>
      <div className="sp-field">
        <label htmlFor="tm-lang">{t('training.form.language')}</label>
        <select id="tm-lang" value={language} onChange={(e) => setLanguage(e.target.value as 'ta' | 'en')}>
          <option value="ta">{t('training.language.ta')}</option>
          <option value="en">{t('training.language.en')}</option>
        </select>
      </div>
      <div className="sp-field">
        <label htmlFor="tm-ptype">{t('training.form.priceType')}</label>
        <select id="tm-ptype" value={priceType} onChange={(e) => setPriceType(e.target.value as PriceType)}>
          <option value="free">{t('training.price.free')}</option>
          <option value="per_module">{t('training.price.per_module')}</option>
          <option value="subscription">{t('training.price.subscription')}</option>
        </select>
      </div>
      {priceType !== 'free' && (
        <>
          <Field id="tm-price" label={t('training.form.price')} value={price} inputMode="numeric" onChange={(e) => setPrice(e.target.value)} error={problems.price} />
          <p className="notice">{t('training.form.paidNotice')}</p>
        </>
      )}

      <fieldset className="sp-box">
        <legend>{t('training.form.lessons')}</legend>
        {lessons.length === 0 && <p className="muted">{t('training.form.noLessons')}</p>}
        <ol className="sp-list">
          {lessons.map((l, i) => (
            <li key={l.key} className="sp-card">
              <h2>{t('training.form.lessonN', { n: i + 1 })}</h2>
              <Field id={`lt-${l.key}`} label={t('training.form.lessonTitle')} value={l.title} maxLength={150} onChange={(e) => setLesson(l.key, { title: e.target.value })} error={problems[`lt${l.key}`]} />
              <div className="sp-field">
                <label htmlFor={`lb-${l.key}`}>{t('training.form.lessonBody')}</label>
                <textarea id={`lb-${l.key}`} value={l.body} maxLength={4000} onChange={(e) => setLesson(l.key, { body: e.target.value })} />
              </div>
              <Field id={`lu-${l.key}`} label={t('training.form.lessonUrl')} hint={t('training.form.lessonUrlHint')} value={l.url} maxLength={300} inputMode="url" onChange={(e) => setLesson(l.key, { url: e.target.value })} error={problems[`lu${l.key}`]} />
              <button type="button" className="btn btn--secondary" onClick={() => setLessons((ls) => ls.filter((x) => x.key !== l.key))}>
                {t('training.form.removeLesson', { n: i + 1 })}
              </button>
            </li>
          ))}
        </ol>
        <button
          type="button"
          className="btn btn--secondary"
          disabled={lessons.length >= 30}
          onClick={() => setLessons((ls) => [...ls, { key: nextKey.current++, title: '', body: '', url: '' }])}
        >
          {t('training.form.addLesson')}
        </button>
      </fieldset>

      <ErrorLine message={error} />
      <button type="submit" className="btn btn--big" disabled={busy}>
        {busy ? t('common.loading') : t('training.form.save')}
      </button>
    </form>
  )
}
