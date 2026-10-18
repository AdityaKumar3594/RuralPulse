// Mirrors backend/app/modules/profile/fields.py (the server validates again).

export type FieldKind = 'list' | 'int' | 'text' | 'enum'

export interface FieldMeta {
  key: string
  kind: FieldKind
  options?: string[]
  min?: number
  max?: number
}

export const FIELDS: FieldMeta[] = [
  {
    key: 'education_stage',
    kind: 'enum',
    options: ['class_9', 'class_10', 'class_11', 'class_12', 'iti_or_diploma', 'undergraduate', 'graduate', 'not_in_school'],
  },
  { key: 'subjects_studied', kind: 'list' },
  { key: 'subject_preferences', kind: 'list' },
  { key: 'interests', kind: 'list' },
  { key: 'skills', kind: 'list' },
  { key: 'goals', kind: 'list' },
  { key: 'weekly_learning_hours', kind: 'int', min: 0, max: 70 },
  { key: 'device_type', kind: 'enum', options: ['basic_phone', 'smartphone', 'shared_device', 'computer'] },
  { key: 'connectivity', kind: 'enum', options: ['good', 'patchy', 'poor'] },
  { key: 'state', kind: 'text' },
  { key: 'district', kind: 'text' },
  { key: 'annual_family_income_inr', kind: 'int', min: 0, max: 100000000 },
]

export const fieldMeta = (key: string): FieldMeta => FIELDS.find((f) => f.key === key) ?? FIELDS[0]

/** Turns what was typed into the value the server expects, or null when it is not usable. */
export function parseValue(meta: FieldMeta, raw: string): string | number | string[] | null {
  const text = raw.trim()
  if (!text) return null
  switch (meta.kind) {
    case 'list': {
      const items = text.split(',').map((x) => x.trim()).filter(Boolean)
      return items.length > 0 && items.length <= 20 ? items : null
    }
    case 'int': {
      if (!/^\d+$/.test(text)) return null
      const n = Number(text)
      return n >= (meta.min ?? 0) && n <= (meta.max ?? Number.MAX_SAFE_INTEGER) ? n : null
    }
    case 'enum':
      return meta.options?.includes(text) ? text : null
    default:
      return text.slice(0, 100)
  }
}

export function showValue(value: unknown): string {
  if (Array.isArray(value)) return value.map(String).join(', ')
  if (value === null || value === undefined) return ''
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}
