import en from './locales/en.json'
import ta from './locales/ta.json'

type Tree = { [key: string]: string | Tree }

function merge(target: Tree, source: Tree, path = '') {
  for (const [key, value] of Object.entries(source)) {
    const here = path ? `${path}.${key}` : key
    if (typeof value === 'object') {
      const existing = target[key]
      if (typeof existing === 'string') throw new Error(`i18n clash at ${here}`)
      target[key] = existing ?? {}
      merge(target[key] as Tree, value, here)
    } else {
      if (key in target) throw new Error(`i18n clash at ${here}`)
      target[key] = value
    }
  }
}

/**
 * Feature modules add their own strings in src/i18n/locales/modules/<name>.<lang>.json, so
 * features never edit the shared en.json / ta.json. A key defined twice is an error.
 */
const moduleFiles = import.meta.glob('./locales/modules/*.json', { eager: true, import: 'default' }) as Record<
  string,
  Tree
>

function build(lang: 'en' | 'ta', base: Tree): Tree {
  const merged: Tree = JSON.parse(JSON.stringify(base)) as Tree
  for (const [file, content] of Object.entries(moduleFiles)) {
    if (file.endsWith(`.${lang}.json`)) merge(merged, content)
  }
  return merged
}

export const translations = {
  en: build('en', en as Tree),
  ta: build('ta', ta as Tree),
}

export const resources = {
  en: { translation: translations.en },
  ta: { translation: translations.ta },
}
