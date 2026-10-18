import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import {
  DEFAULT_LANGUAGE,
  FALLBACK_LANGUAGE,
  LANG_STORAGE_KEY,
  SUPPORTED_LANGUAGES,
  isSupportedLanguage,
} from './config'
import { resources } from './resources'

function readStoredLanguage() {
  try {
    const stored = localStorage.getItem(LANG_STORAGE_KEY)
    return isSupportedLanguage(stored) ? stored : null
  } catch {
    return null
  }
}

i18n.on('languageChanged', (lng) => {
  document.documentElement.lang = lng
  if (isSupportedLanguage(lng)) {
    try {
      localStorage.setItem(LANG_STORAGE_KEY, lng)
    } catch {
      // storage unavailable; preference just won't persist
    }
  }
})

void i18n.use(initReactI18next).init({
  resources,
  lng: readStoredLanguage() ?? DEFAULT_LANGUAGE,
  fallbackLng: FALLBACK_LANGUAGE,
  supportedLngs: SUPPORTED_LANGUAGES.map((l) => l.code),
  interpolation: { escapeValue: false },
  initAsync: false,
})

export default i18n
