import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router'
import { SUPPORTED_LANGUAGES } from '../i18n/config'

export function LanguageSelectPage() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()

  const choose = async (code: string) => {
    await i18n.changeLanguage(code)
    void navigate('/home')
  }

  return (
    <>
      <h1>{t('language.title')}</h1>
      <ul className="lang-list">
        {SUPPORTED_LANGUAGES.map((l) => (
          <li key={l.code}>
            <button type="button" className="btn btn--big" lang={l.code} onClick={() => void choose(l.code)}>
              {l.nativeName}
            </button>
          </li>
        ))}
      </ul>
      <p className="muted">{t('language.hint')}</p>
    </>
  )
}
