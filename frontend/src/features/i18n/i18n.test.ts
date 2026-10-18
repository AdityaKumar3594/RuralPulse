import { describe, expect, it } from 'vitest'
import i18n from './index'

describe('i18n', () => {
  it('falls back to English for a key missing in Tamil', async () => {
    i18n.addResourceBundle('en', 'test', { onlyEnglish: 'English only' })
    i18n.addResourceBundle('ta', 'test', {})
    await i18n.changeLanguage('ta')
    expect(i18n.t('onlyEnglish', { ns: 'test' })).toBe('English only')
    expect(i18n.t('home.welcome')).not.toBe('Welcome to Ruralpulse')
  })
})
