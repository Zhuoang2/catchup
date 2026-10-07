import { expect } from 'vitest'
import { axe } from 'vitest-axe'

export async function expectAccessible(container: HTMLElement): Promise<void> {
  const results = await axe(container)
  expect(results.violations).toEqual([])
}
