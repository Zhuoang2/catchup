import { expect, it } from 'vitest'

it('leaves a title behind', () => {
  document.title = 'Left by an earlier test'
})

it('starts the next test with a blank title', () => {
  expect(document.title).toBe('')
})
