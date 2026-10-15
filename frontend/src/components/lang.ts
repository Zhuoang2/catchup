const languageNames = new Map(Object.entries({
  english: 'en',
  'simplified chinese': 'zh-Hans',
  '简体中文': 'zh-Hans',
  'traditional chinese': 'zh-Hant',
  '繁體中文': 'zh-Hant',
  japanese: 'ja',
  '日本語': 'ja',
  french: 'fr',
  français: 'fr',
  spanish: 'es',
  español: 'es',
  german: 'de',
  deutsch: 'de',
  korean: 'ko',
  '한국어': 'ko',
}))
const supportedLanguages = new Set(['en', 'zh', 'ja', 'ko', 'fr', 'de', 'es', 'it', 'pt', 'ru', 'ar', 'hi'])

export function digestLang(language: string | null | undefined): string | undefined {
  const name = language?.trim().toLowerCase()
  if (!name || name === 'original') return undefined
  const named = languageNames.get(name)
  if (named) return named
  try {
    const tag = Intl.getCanonicalLocales(name)[0]
    return tag && supportedLanguages.has(tag.split('-')[0]) ? tag : undefined
  } catch (error) {
    if (error instanceof RangeError) return undefined
    throw error
  }
}
