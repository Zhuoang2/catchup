import { expect, it } from 'vitest'
import type { DigestItem } from './DigestArticle'
import { shownItemIds } from './topItems'
import { limitedDigest, unrated } from '../test/limitedDigest'

function item(id: number, importance?: number | null, unavailable = false): DigestItem {
  return {
    id, importance, title: `Item ${id}`, bookmarked: false, liked: false, rating: null, note: null,
    link: `https://example.test/${id}`, source_name: 'Blog', published_at: null,
    summary: unavailable ? null : 'Summary', summary_unavailable: unavailable,
  }
}

it('ranks by rating, an unrated summary as 3, and an unavailable one last', () => {
  expect([...shownItemIds(limitedDigest.topics, 5)!].sort((a, b) => a - b)).toEqual([1, 2, 5, 6, 8])
})

it('keeps reading order among equal ranks', () => {
  expect([...shownItemIds([{ items: [item(1, 3), item(2, 3)] }, { items: [item(3, 3)] }], 2)!])
    .toEqual([1, 2])
})

it('ranks an unavailable summary below a rating of 1', () => {
  expect([...shownItemIds([{ items: [item(1, null, true), item(2, 1)] }], 1)!]).toEqual([2])
})

it('shows everything without a limit, for a short digest, or without ratings', () => {
  for (const limit of [0, 8, 10]) expect(shownItemIds(limitedDigest.topics, limit)).toBeNull()
  expect(shownItemIds(unrated(limitedDigest).topics, 5)).toBeNull()
  const oldItems = Array.from({ length: 8 }, (_, index) => {
    const old = item(index + 1)
    delete old.importance
    return old
  })
  expect(shownItemIds([{ items: oldItems }], 5)).toBeNull()
})
