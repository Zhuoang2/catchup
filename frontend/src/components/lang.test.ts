import { expect, it } from 'vitest'
import { digestLang } from './lang'

it.each([
  ['en', 'en'], ['zh-Hans', 'zh-Hans'], ['original', undefined], [null, undefined],
  ['Japanese', 'ja'], ['日本語', 'ja'], ['Français', 'fr'], ['繁體中文', 'zh-Hant'],
  ['Klingon', undefined], [' TRADITIONAL CHINESE ', 'zh-Hant'],
])('maps saved language %s to %s', (value, expected) => {
  expect(digestLang(value)).toBe(expected)
})
