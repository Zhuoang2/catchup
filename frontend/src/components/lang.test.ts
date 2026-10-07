import { expect, it, vi } from 'vitest'
import { digestLang } from './lang'

it.each([
  ['en', 'en'], ['zh-Hans', 'zh-Hans'], ['original', undefined], [null, undefined],
  ['Japanese', 'ja'], ['日本語', 'ja'], ['Français', 'fr'], ['繁體中文', 'zh-Hant'],
  ['Klingon', undefined], [' TRADITIONAL CHINESE ', 'zh-Hant'], ['japanese', 'ja'],
])('maps saved language %s to %s', (value, expected) => {
  expect(digestLang(value)).toBe(expected)
})

it.each([
  ['ja', 'ja'], ['fr', 'fr'], ['zh-hant', 'zh-Hant'], ['PT-br', 'pt-BR'],
  ['de-CH', 'de-CH'], ['abcdefgh', undefined], ['xx', undefined],
])('accepts only supported canonical language tags: %s', (value, expected) => {
  expect(digestLang(value)).toBe(expected)
})

it.each([
  ['constructor'], ['__proto__'],
])('does not treat the built-in object key %s as a language name', value => {
  expect(digestLang(value)).toBeUndefined()
})

it.each([
  ['Brazilian Portuguese'], ['English (US)'], ['中文（简体）'],
])('gives free text that is neither a known name nor a tag (%s) no lang', value => {
  expect(digestLang(value)).toBeUndefined()
})

it('matches names regardless of the browser locale\'s case rules', () => {
  // Turkish lowercases "I" to a dotless "ı", which would turn ENGLISH into "englısh".
  const turkish = vi.spyOn(String.prototype, 'toLocaleLowerCase').mockImplementation(function (this: string) {
    return this.replace(/I/g, 'ı').toLowerCase()
  })
  try {
    expect(digestLang('ENGLISH')).toBe('en')
    expect(digestLang('JAPANESE')).toBe('ja')
  } finally {
    turkish.mockRestore()
  }
})
