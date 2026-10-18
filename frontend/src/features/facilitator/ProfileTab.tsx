import { useTranslation } from 'react-i18next'
import { formatDateTime } from '../support/shared'
import { showValue } from './fields'
import { AssistedForm, ObservationForm } from './ProfileForms'
import type { ProfileEntry, ProfileField, StudentProfile } from './types'

function sourceText(t: ReturnType<typeof useTranslation>['t'], source: string): string {
  if (source.startsWith('facilitator:')) return t('facilitator.profile.sourceTeacher')
  if (source.startsWith('assisted_by:')) return t('facilitator.profile.sourceAssisted')
  return t(`facilitator.profile.source.${source}`, { defaultValue: source })
}

function Entry({ e }: { e: ProfileEntry }) {
  const { t, i18n } = useTranslation()
  const verifiedIcon = e.verification === 'verified' ? '✓ ' : e.verification === 'disputed' ? '! ' : '? '
  return (
    <li className="entry">
      <span className={`badge badge--${e.provenance}`}>{t(`facilitator.profile.prov.${e.provenance}`)}</span>{' '}
      <span className="badge">
        <span aria-hidden="true">{verifiedIcon}</span>
        {t(`facilitator.profile.verification.${e.verification}`, { defaultValue: e.verification })}
      </span>{' '}
      <strong>{e.provenance === 'unknown' ? t('facilitator.profile.unknownValue') : showValue(e.value)}</strong>
      {e.basis && <p className="muted">{t('facilitator.profile.basis', { basis: e.basis })}</p>}
      <p className="muted">
        {t('facilitator.profile.source.label', { source: sourceText(t, e.source) })} · {formatDateTime(e.created_at, i18n.language)}
      </p>
    </li>
  )
}

function FieldCard({ f }: { f: ProfileField }) {
  const { t } = useTranslation()
  return (
    <li className="field-card">
      <h3>{t(`facilitator.fields.${f.key}`, { defaultValue: f.description })}</h3>
      <p className="muted">{t(`facilitator.profile.state.${f.state}`, { defaultValue: f.state })}</p>
      {f.conflict && <p className="notice">{t('facilitator.profile.conflict')}</p>}
      {f.entries.length === 0 ? (
        <p>{t('facilitator.profile.noEntries')}</p>
      ) : (
        <ul className="entries">
          {f.entries.map((e, i) => (
            <Entry key={i} e={e} />
          ))}
        </ul>
      )}
    </li>
  )
}

export function ProfileTab({ profile, onChanged }: { profile: StudentProfile; onChanged: () => void }) {
  const { t } = useTranslation()
  const id = profile.student.id
  return (
    <>
      <p className="muted">{t('facilitator.profile.legend')}</p>
      <ul className="fields">
        {profile.fields.map((f) => (
          <FieldCard key={f.key} f={f} />
        ))}
      </ul>
      <ObservationForm studentId={id} onSaved={onChanged} />
      <AssistedForm studentId={id} onSaved={onChanged} />
    </>
  )
}
