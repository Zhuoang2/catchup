const languageNames: Record<string, string> = {
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
}

export function digestLang(language: string | null | undefined): string | undefined {
  const name = language?.trim().toLocaleLowerCase()
  if (!name || name === 'original') return undefined
  if (name === 'en') return 'en'
  if (name === 'zh-hans') return 'zh-Hans'
  return languageNames[name]
}
