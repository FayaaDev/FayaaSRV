import { useState, useCallback, useEffect, type ReactNode } from 'react'
import { translations, type Locale, type TranslationKey } from './translations'
import { I18nContext } from './state'

function formatTemplate(template: string, vars: Record<string, string | number>) {
  return template.replace(/\{(\w+)\}/g, (match, key: string) => {
    const value = vars[key]
    return value === undefined || value === null ? match : String(value)
  })
}

function getInitialLocale(): Locale {
  const stored = localStorage.getItem('locale') as Locale | null
  if (stored === 'en' || stored === 'ar') return stored
  const browserLang = navigator.language.slice(0, 2)
  return browserLang === 'ar' ? 'ar' : 'en'
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(getInitialLocale)
  const dir = locale === 'ar' ? 'rtl' : 'ltr'

  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next)
    localStorage.setItem('locale', next)
  }, [])

  useEffect(() => {
    document.documentElement.lang = locale
    document.documentElement.dir = locale === 'ar' ? 'rtl' : 'ltr'
  }, [locale])

  const t = useCallback(
    (key: TranslationKey) => translations[locale][key] as string,
    [locale],
  )

  const tf = useCallback(
    (key: TranslationKey, vars: Record<string, string | number>) => {
      const template = translations[locale][key] as string
      return formatTemplate(template, vars)
    },
    [locale],
  )

  const ts = useCallback(
    (key: string) => {
      const svc = translations[locale].services as Record<string, string>
      return svc[key] ?? key
    },
    [locale],
  )

  return (
    <I18nContext.Provider value={{ locale, dir, t, tf, ts, setLocale }}>
      {children}
    </I18nContext.Provider>
  )
}
