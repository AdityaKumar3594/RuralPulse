// To add a language: add src/i18n/locales/<code>.json and one entry here
// (plus one import in ./index.ts).
export const SUPPORTED_LANGUAGES = [
  { code: 'ta', nativeName: 'தமிழ்' },
  { code: 'en', nativeName: 'English' },
] as const

export type LanguageCode = (typeof SUPPORTED_LANGUAGES)[number]['code']

export const DEFAULT_LANGUAGE: LanguageCode = 'ta'
export const FALLBACK_LANGUAGE: LanguageCode = 'en'
export const LANG_STORAGE_KEY = 'Ruralpulse.lang'

export function isSupportedLanguage(code: string | null | undefined): code is LanguageCode {
  return SUPPORTED_LANGUAGES.some((l) => l.code === code)
}
