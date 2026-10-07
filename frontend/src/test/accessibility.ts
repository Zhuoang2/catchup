import { expect } from 'vitest'
import { axe } from 'vitest-axe'

export async function expectAccessible(container: HTMLElement): Promise<void> {
  // jsdom cannot paint or measure contrast; the token test checks both themes.
  const results = await axe(container, { rules: { 'color-contrast': { enabled: false } } })
  expect(results.violations).toEqual([])
}
