import { useCallback, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { createAssignment, endAssignment, listAssignments, listUsers } from './api'
import { errText, formatDate, LoadState, Msg, useLoad } from './common'
import type { AdminUser } from './types'

const label = (u: AdminUser) => `${u.display_name} (${u.phone})`

export function AssignmentsPage() {
  const { t, i18n } = useTranslation()
  const loadAll = useCallback(
    async (o: { signal: AbortSignal }) => {
      const [assignments, facilitators, students] = await Promise.all([
        listAssignments(o),
        listUsers('facilitator', o),
        listUsers('student', o),
      ])
      return { assignments, facilitators, students }
    },
    [],
  )
  const { state, reload } = useLoad(loadAll)
  const [fac, setFac] = useState('')
  const [stu, setStu] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [ok, setOk] = useState<string | null>(null)

  async function submit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setOk(null)
    if (!fac || !stu) {
      setError(t('admin.assign.choose'))
      return
    }
    setBusy(true)
    try {
      await createAssignment(fac, stu)
      setOk(t('admin.assign.created'))
      setStu('')
      reload()
    } catch (err) {
      setError(errText(err, t))
    } finally {
      setBusy(false)
    }
  }

  async function end(id: string) {
    if (!window.confirm(t('admin.assign.confirmEnd'))) return
    setError(null)
    setOk(null)
    try {
      await endAssignment(id)
      setOk(t('admin.assign.ended'))
      reload()
    } catch (err) {
      setError(errText(err, t))
    }
  }

  return (
    <>
      <LoadState state={state} onRetry={reload} />
      {state.phase === 'ready' && (
        <>
          <section aria-labelledby="adm-as-new">
            <h2 id="adm-as-new">{t('admin.assign.createTitle')}</h2>
            <form className="adm-form" onSubmit={submit}>
              <div className="field">
                <label htmlFor="adm-fac">{t('admin.assign.facilitator')}</label>
                <select id="adm-fac" value={fac} onChange={(e) => setFac(e.target.value)}>
                  <option value="">{t('admin.assign.pick')}</option>
                  {state.data.facilitators.map((u) => (
                    <option key={u.id} value={u.id}>
                      {label(u)}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="adm-stu">{t('admin.assign.student')}</label>
                <select id="adm-stu" value={stu} onChange={(e) => setStu(e.target.value)}>
                  <option value="">{t('admin.assign.pick')}</option>
                  {state.data.students.map((u) => (
                    <option key={u.id} value={u.id}>
                      {label(u)}
                    </option>
                  ))}
                </select>
              </div>
              <button type="submit" className="btn btn--big" disabled={busy}>
                {busy ? t('admin.saving') : t('admin.assign.create')}
              </button>
            </form>
            <Msg error={error} ok={ok} />
          </section>
          <section aria-labelledby="adm-as-list">
            <h2 id="adm-as-list">{t('admin.assign.listTitle')}</h2>
            {state.data.assignments.length === 0 ? (
              <p role="status">{t('admin.assign.empty')}</p>
            ) : (
              <ul className="adm-list">
                {state.data.assignments.map((a) => {
                  const f = state.data.facilitators.find((u) => u.id === a.facilitator_id)
                  const s = state.data.students.find((u) => u.id === a.student_id)
                  return (
                    <li key={a.id} className="adm-card">
                      <p>
                        <strong>{t('admin.assign.facilitator')}:</strong> {f ? label(f) : a.facilitator_id}
                      </p>
                      <p>
                        <strong>{t('admin.assign.student')}:</strong> {s ? label(s) : a.student_id}
                      </p>
                      <p className="muted">
                        {a.ended_at
                          ? t('admin.assign.endedOn', { date: formatDate(a.ended_at, i18n.language) })
                          : t('admin.assign.active', { date: formatDate(a.created_at, i18n.language) })}
                      </p>
                      {!a.ended_at && (
                        <button type="button" className="btn btn--danger" onClick={() => void end(a.id)}>
                          {t('admin.assign.end')}
                        </button>
                      )}
                    </li>
                  )
                })}
              </ul>
            )}
          </section>
        </>
      )}
      {state.phase !== 'ready' && <Msg error={error} />}
    </>
  )
}
