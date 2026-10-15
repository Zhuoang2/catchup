import { expect, it } from 'vitest'
import { localDateISO, shortDateTime } from './format'

it('shows a compact local publication timestamp without weekday or full month', () => {
  expect(shortDateTime('2026-10-02T10:05:00')).toBe('2 Oct 2026, 10:05')
})

it('uses local calendar components instead of UTC for the masthead date', () => {
  const date = new Date(2026, 9, 6, 23, 30)
  expect(localDateISO(date)).toBe('2026-10-06')
})
