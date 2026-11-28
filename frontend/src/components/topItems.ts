import type { DigestItem } from './DigestArticle'

export function shownItemIds(topics: ReadonlyArray<{ items: DigestItem[] }>, limit: number): Set<number> | null {
  const items = topics.flatMap(topic => topic.items)
  if (limit <= 0 || items.length <= limit || !items.some(item => typeof item.importance === 'number')) return null
  const ranked = items.map((item, position) => ({
    id: item.id, position,
    rank: typeof item.importance === 'number' ? item.importance : item.summary_unavailable ? 0 : 3,
  }))
  ranked.sort((a, b) => b.rank - a.rank || a.position - b.position)
  return new Set(ranked.slice(0, limit).map(item => item.id))
}
