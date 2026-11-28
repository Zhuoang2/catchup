import type { Digest, DigestItem } from '../components/DigestArticle'

function item(id: number, title: string, importance: number | null): DigestItem {
  return {
    id, title, importance, bookmarked: false, liked: false, rating: null, note: null,
    link: `https://example.test/${id}`, source_name: 'Blog', published_at: null,
    summary: `Summary ${title}`, summary_unavailable: false,
  }
}

export const limitedDigest: Digest = {
  id: 7, created_at: '2026-11-20T10:00:00Z', model_id: 'test', language: 'en',
  item_count: 10, source_count: 3, transcript_wait_days: 7,
  topics: [
    { title: 'Alpha', overview: 'Alpha overview', items: [item(1, 'A1', 2), item(2, 'A2', 5)] },
    { title: 'Beta', overview: 'Beta overview', items: [item(3, 'B1', 1), item(4, 'B2', 1)] },
    { title: 'Gamma', overview: 'Gamma overview', items: [
      item(5, 'C1', 4), item(6, 'C2', null),
      { ...item(7, 'C3', null), summary: null, summary_unavailable: true }, item(8, 'C4', 3),
    ] },
  ],
  creator_updates: [{ source_name: 'Channel', source_kind: 'youtube', items: [
    { title: 'Video one', link: 'https://example.test/v1', published_at: null, reason: 'no_captions' },
    { title: 'Video two', link: 'https://example.test/v2', published_at: null, reason: 'no_captions' },
  ] }],
}

export function unrated(digest: Digest): Digest {
  return { ...digest, topics: digest.topics.map(topic => ({
    ...topic, items: topic.items.map(item => ({ ...item, importance: null })),
  })) }
}
