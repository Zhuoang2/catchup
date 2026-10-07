import { expect, it } from 'vitest'
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
