import { expect, it } from 'vitest'
import { translations } from './resources'

const en = translations.en
const ta = translations.ta

function keys(obj: Record<string, unknown>, prefix = ''): string[] {
  return Object.entries(obj).flatMap(([k, v]) =>
    v && typeof v === 'object' ? keys(v as Record<string, unknown>, `${prefix}${k}.`) : [`${prefix}${k}`],
  )
}

it('Tamil has every key English has, and nothing extra', () => {
  expect(keys(ta).sort()).toEqual(keys(en).sort())
})

it('no Tamil string is left identical to English (untranslated), except names', () => {
  const flat = (o: Record<string, unknown>, p = ''): [string, string][] =>
    Object.entries(o).flatMap(([k, v]) =>
      v && typeof v === 'object' ? flat(v as Record<string, unknown>, `${p}${k}.`) : [[`${p}${k}`, String(v)] as [string, string]],
    )
  const enMap = Object.fromEntries(flat(en))
  const same = flat(ta).filter(([k, v]) => v === enMap[k] && k !== 'app.name')
  expect(same).toEqual([])
})

it('every placeholder in English exists in the Tamil string', () => {
  const placeholders = (s: string) => (s.match(/{{\w+}}/g) ?? []).sort()
  const flat = (o: Record<string, unknown>, p = ''): [string, string][] =>
    Object.entries(o).flatMap(([k, v]) =>
      v && typeof v === 'object' ? flat(v as Record<string, unknown>, `${p}${k}.`) : [[`${p}${k}`, String(v)] as [string, string]],
    )
  const taMap = Object.fromEntries(flat(ta))
  for (const [k, v] of flat(en)) expect(placeholders(taMap[k]), k).toEqual(placeholders(v))
})
