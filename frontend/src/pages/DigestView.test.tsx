import { fireEvent, render, screen } from '@testing-library/react'
import { Link, MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import DigestView from './DigestView'
import { expectAccessible } from '../test/accessibility'

const fetchMock = vi.fn()
const respond = (value: unknown, status = 200) => ({
  ok: status < 400, status, json: async () => value,
})
function page(id = '7') {
  return render(<MemoryRouter initialEntries={[`/digests/${id}`]}>
    <Routes><Route path="/digests/:id" element={<DigestView />} /></Routes>
  </MemoryRouter>)
}

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock)
})
afterEach(() => {
  vi.unstubAllGlobals()
  fetchMock.mockReset()
})

it('renders saved topics, text summaries, dates and safe original links', async () => {
  fetchMock.mockResolvedValue(respond({
    id: 7, created_at: '2026-10-03T10:00:00Z', model_id: 'test',
    topics: [
      { title: '<img src=x onerror=alert(1)>', overview: 'A saved overview', items: [
        { title: 'Saved article', link: 'https://example.test/article', source_name: 'Blog',
          published_at: '2026-10-02T10:00:00Z', summary: '<strong>Plain summary</strong>',
          summary_unavailable: false },
        { title: 'Another article', link: 'https://example.test/another', source_name: 'News',
          published_at: null, summary: null, summary_unavailable: true },
      ] },
      { title: 'Other', overview: 'More', items: [
        { title: 'Third article', link: 'https://example.test/third', source_name: 'Elsewhere',
          published_at: null, summary: 'Third summary', summary_unavailable: false },
      ] },
    ],
  }))
  page()
  expect(await screen.findByRole('region', { name: '<img src=x onerror=alert(1)>' })).toHaveTextContent(
    'A saved overview',
  )
  expect(screen.getByText('<strong>Plain summary</strong>')).toBeInTheDocument()
  expect(document.querySelector('img, strong')).toBeNull()
  const link = screen.getByRole('link', { name: 'Saved article (opens the original)' })
  expect(link).toHaveAttribute('href', 'https://example.test/article')
  expect(link).toHaveAttribute('target', '_blank')
  expect(link).toHaveAttribute('rel', 'noopener noreferrer')
  expect(link.closest('article')).toHaveTextContent('Blog')
  expect(link.closest('article')?.querySelector('time')).toHaveAttribute('dateTime', '2026-10-02T10:00:00Z')
  expect(link.closest('article')?.querySelector('time')).toHaveTextContent(/\d{1,2} Oct 2026, \d{2}:\d{2}/)
  expect(screen.getByRole('navigation', { name: 'In this digest' }).querySelectorAll('.toc-count'))
    .toHaveLength(2)
  expect(screen.getByText('Summary unavailable')).toBeInTheDocument()
  expect(document.querySelector('.digest-head')).toHaveTextContent('No. 7')
  expect(screen.getByRole('region', { name: 'Other' })).toHaveTextContent('Third summary')
  expect(fetchMock).toHaveBeenCalledWith('/api/digests/7', undefined)
})

it('reports an unavailable digest', async () => {
  fetchMock.mockResolvedValue(respond({ error: { code: 'not_found', message: 'Digest not found.' } }, 404))
  page()
  expect(screen.getByRole('heading', { name: 'Loading digest…', level: 1 })).toBeInTheDocument()
  expect(document.title).toBe('Digest · CatchUp')
  expect(await screen.findByRole('alert')).toHaveTextContent('Digest not found.')
  expect(document.title).toBe('Digest · CatchUp')
  expect(screen.getByRole('heading', { name: 'Could not load digest', level: 1 })).toBeInTheDocument()
})

it('clears a prior error when navigating to a different digest id', async () => {
  fetchMock.mockImplementation(async (url: string) => url.endsWith('/7')
    ? respond({ error: { code: 'not_found', message: 'Digest not found.' } }, 404)
    : respond({ id: 8, created_at: '2026-10-03T10:00:00Z', model_id: 'test',
      item_count: 0, source_count: 0, topics: [] }))
  render(<MemoryRouter initialEntries={['/digests/7']}>
    <Link to="/digests/8">Next digest</Link>
    <Routes><Route path="/digests/:id" element={<DigestView/>}/></Routes>
  </MemoryRouter>)
  expect(await screen.findByRole('alert')).toHaveTextContent('Digest not found.')
  fireEvent.click(screen.getByRole('link', { name: 'Next digest' }))
  expect(await screen.findByText(/Tokens: not reported/)).toBeInTheDocument()
  expect(screen.queryByText('Digest not found.')).toBeNull()
})

it('does not keep showing the previous digest while the next one loads', async () => {
  let release!: () => void
  const pending = new Promise<void>(resolve => { release = resolve })
  fetchMock.mockImplementation(async (url: string) => {
    if (url.endsWith('/8')) await pending
    const id = Number(url.split('/').pop())
    return respond({ id, created_at: '2026-10-03T10:00:00Z', model_id: `model-${id}`,
      item_count: 0, source_count: 0, topics: [] })
  })
  render(<MemoryRouter initialEntries={['/digests/7']}>
    <Link to="/digests/8">Next digest</Link>
    <Routes><Route path="/digests/:id" element={<DigestView/>}/></Routes>
  </MemoryRouter>)
  expect(await screen.findByText(/model-7/)).toBeInTheDocument()
  fireEvent.click(screen.getByRole('link', { name: 'Next digest' }))
  expect(await screen.findByRole('heading', { name: 'Loading digest…' })).toBeInTheDocument()
  expect(screen.queryByText(/model-7/)).toBeNull()
  release()
  expect(await screen.findByText(/model-8/)).toBeInTheDocument()
})

it('titles a saved edition using its local short date', async () => {
  fetchMock.mockResolvedValue(respond({
    id: 3, created_at: '2026-10-05T09:00:00', model_id: 'test', topics: [],
  }))
  page('3')
  await screen.findByText(/Tokens: not reported/)
  expect(document.title).toBe('No. 3 · 5 Oct 2026 · CatchUp')
})

it('uses saved source count when two distinct sources have the same title', async () => {
  fetchMock.mockResolvedValue(respond({
    id: 7, created_at: '2026-10-03T10:00:00Z', model_id: 'test',
    item_count: 2, source_count: 2,
    topics: [{ title: 'Topic', overview: '', items: [
      { title: 'First', link: 'https://one.example/a', source_name: 'Shared name',
        published_at: null, summary: 'One', summary_unavailable: false },
      { title: 'Second', link: 'https://two.example/b', source_name: 'Shared name',
        published_at: null, summary: 'Two', summary_unavailable: false },
    ] }],
  }))
  const { container } = page()
  await screen.findByRole('heading', { name: 'Topic' })
  expect(container.querySelector('.digest-meta')).toHaveTextContent('2 items · 2 sources')
})

it('renders creator updates after topics with saved wait labels', async () => {
  fetchMock.mockResolvedValue(respond({
    id: 7, created_at: '2026-10-03T10:00:00Z', model_id: 'test',
    transcript_wait_days: 10,
    topics: [{ title: 'Technology', overview: 'News', items: [] }],
    creator_updates: [
      { source_name: 'Show', source_kind: 'podcast', items: [
        { title: 'Episode', link: 'https://example.test/ep', source_kind: 'podcast',
          published_at: null, reason: 'no_transcript' },
      ] },
      { source_name: 'Channel', source_kind: 'youtube', items: [
        { title: 'Off', link: 'https://example.test/off', source_kind: 'youtube',
          published_at: null, reason: 'captions_off' },
        { title: 'Missing', link: 'https://example.test/missing',
          source_kind: 'youtube', published_at: '2026-10-02T10:00:00Z', reason: 'no_captions' },
        { title: 'Blocked', link: 'https://example.test/blocked', source_kind: 'youtube',
          published_at: null, reason: 'blocked' },
        { title: 'Failed', link: 'https://example.test/failed', source_kind: 'youtube',
          published_at: null, reason: 'captions_failed' },
      ] },
    ],
  }))
  const { container } = page()
  const creator = await screen.findByRole('region', { name: 'Creator updates' })
  expect(screen.getByRole('navigation', { name: 'In this digest' }).querySelector('.toc-creator .toc-count'))
    .toHaveTextContent('5')
  expect(creator.compareDocumentPosition(screen.getByRole('region', { name: 'Technology' }))
    & Node.DOCUMENT_POSITION_PRECEDING).toBeTruthy()
  expect(screen.getByRole('region', { name: 'Show' })).toHaveTextContent('No transcript within 10 days')
  expect(screen.getByRole('region', { name: 'Channel' })).toHaveTextContent('Caption fetching is off')
  expect(screen.getByRole('region', { name: 'Channel' })).toHaveTextContent('This video has no captions')
  expect(screen.getByRole('region', { name: 'Channel' })).toHaveTextContent('Blocked by YouTube')
  expect(screen.getByRole('region', { name: 'Channel' })).toHaveTextContent('Captions could not be fetched')
  expect(screen.getByRole('link', { name: 'Missing (opens the original)' }).closest('li')?.querySelector('time')).toHaveTextContent(
    /\d{1,2} Oct 2026, \d{2}:\d{2}/)
  expect(screen.getByRole('link', { name: 'Episode (opens the original)' })).toHaveAttribute(
    'rel', 'noopener noreferrer')
  expect(screen.getByRole('region', { name: 'Show' }).querySelectorAll('.creator-source .sr-only'))
    .toHaveLength(1)
  expect(screen.getByRole('region', { name: 'Show' }).querySelector('.creator-source .sr-only'))
    .toHaveTextContent('Podcast:')
  expect(screen.getByRole('region', { name: 'Channel' }).querySelectorAll('.creator-source .sr-only'))
    .toHaveLength(1)
  expect(screen.getByRole('region', { name: 'Channel' }).querySelector('.creator-source .sr-only'))
    .toHaveTextContent('YouTube channel:')
  expect(creator.querySelectorAll('.creator-item .creator-meta .sr-only')).toHaveLength(0)
  expect(creator.querySelectorAll('.creator-item .icon-sm')).toHaveLength(0)
  await expectAccessible(container)
})

it('shows transcript key points as a list', async () => {
  fetchMock.mockResolvedValue(respond({
    id: 7, created_at: '2026-10-03T10:00:00Z', model_id: 'test',
    topics: [{ title: 'Podcast', overview: 'Overview', items: [{
      title: 'Episode', link: 'https://example.test/ep', source_name: 'Show',
      published_at: null, summary: 'Overview.\n- First point\n- Final point',
      summary_unavailable: false,
    }] }],
    creator_updates: [],
  }))
  page()
  expect(await screen.findByRole('region', { name: 'Podcast' })).toHaveTextContent('Overview.')
  expect(screen.getByText('First point').tagName).toBe('LI')
  expect(screen.getByText('Final point').tagName).toBe('LI')
})

it('keeps overview, bullets, and later prose in original order', async () => {
  fetchMock.mockResolvedValue(respond({
    id: 7, created_at: '2026-10-03T10:00:00Z', model_id: 'test',
    topics: [{ title: 'Podcast', overview: '', items: [{
      title: 'Episode', link: 'https://example.test/ep', source_name: 'Show',
      published_at: null, summary: 'Overview\n- Key point\nContinuation\nClosing sentence',
      summary_unavailable: false,
    }] }],
  }))
  page()
  const item = (await screen.findByRole('link', { name: 'Episode (opens the original)' })).closest('article')!
  const blocks = Array.from(item.querySelector('.summary')!.children)
  expect(blocks.map(element => element.tagName)).toEqual(['P', 'UL', 'P'])
  expect(blocks.map(element => element.textContent)).toEqual([
    'Overview', 'Key point', 'Continuation\nClosing sentence',
  ])
})

it('marks Chinese generated text and focuses index targets', async () => {
  fetchMock.mockResolvedValue(respond({
    id: 7, language: 'zh-Hans', created_at: '2026-10-03T10:00:00Z', model_id: 'test',
    topics: [
      { title: '中文主题', overview: '中文概要', items: [
        { title: 'Original episode', link: 'https://example.test/ep', source_name: 'Show',
          source_kind: 'podcast', published_at: null,
          summary: '说明\n- 要点一\n- 要点二', summary_unavailable: false },
        { title: 'Original article', link: 'https://example.test/short', source_name: 'Blog',
          source_kind: 'feed', published_at: null, summary: '短摘要', summary_unavailable: false },
      ] },
      { title: '第二主题', overview: '介绍', items: [] },
    ],
  }))
  const { container } = page()
  await screen.findByRole('heading', { name: '中文主题' })
  expect(screen.getByText('要点一').tagName).toBe('LI')
  expect(screen.getByRole('heading', { name: '中文主题' })).toHaveAttribute('lang', 'zh-Hans')
  expect(screen.getByText('中文概要')).toHaveAttribute('lang', 'zh-Hans')
  expect(screen.getByText('要点一').closest('.summary')).toHaveAttribute('lang', 'zh-Hans')
  expect(screen.getByRole('link', { name: 'Original episode (opens the original)' })).not.toHaveAttribute('lang')
  expect(screen.getAllByText(/Podcast/)).not.toHaveLength(0)
  const jump = screen.getByRole('navigation', { name: 'In this digest' }).querySelector('a')!
  expect(screen.getByRole('navigation', { name: 'In this digest' }).querySelectorAll('.toc-count'))
    .toHaveLength(2)
  jump.click()
  expect(document.activeElement).toBe(screen.getByRole('region', { name: '中文主题' }))
  await expectAccessible(container)
})

it('keeps every item in one markup order regardless of summary length or availability', async () => {
  fetchMock.mockResolvedValue(respond({
    id: 7, created_at: '2026-10-03T10:00:00Z', model_id: 'test',
    item_count: 4, source_count: 1,
    topics: [{ title: 'One layout', overview: '', items: [
      { title: 'Key points', link: 'https://example.test/points', source_name: 'Feed',
        published_at: null, summary: 'Overview\n- First point\n- Second point', summary_unavailable: false },
      { title: 'Story 141', link: 'https://example.test/141', source_name: 'Feed',
        published_at: null, summary: 'x'.repeat(141), summary_unavailable: false },
      { title: 'Story 140', link: 'https://example.test/140', source_name: 'Feed',
        published_at: null, summary: 'x'.repeat(140), summary_unavailable: false },
      { title: 'Unavailable', link: 'https://example.test/unavailable', source_name: 'Feed',
        published_at: null, summary: null, summary_unavailable: true },
    ] }],
  }))
  const { container } = page()
  const topic = await screen.findByRole('region', { name: 'One layout' })
  const articles = Array.from(topic.querySelectorAll('article'))
  expect(articles).toHaveLength(4)
  for (const [index, article] of articles.entries()) {
    expect(article.classList.value).toBe('item')
    expect(Array.from(article.children).map(child =>
      `${child.tagName.toLowerCase()}.${child.className}`)).toEqual([
      'p.item-meta', 'h3.item-title',
      index === 3 ? 'p.summary-unavailable' : 'div.summary',
    ])
  }
  expect(container.querySelector('.digest-meta')).toHaveTextContent('4 items · 1 source')
})

it('hides the single-entry index and explains creator-only digests', async () => {
  fetchMock.mockResolvedValue(respond({
    id: 7, language: 'en', created_at: '2026-10-03T10:00:00Z', model_id: 'test', topics: [],
    creator_updates: [{ source_name: 'Channel', source_kind: 'youtube', items: [
      { title: 'Video', link: 'https://example.test/video', source_kind: 'youtube',
        published_at: null, reason: 'captions_off' },
    ] }],
  }))
  const { container } = page()
  expect(await screen.findByText('Nothing could be summarized this time. Here is what your sources published.')).toBeInTheDocument()
  expect(screen.queryByRole('navigation', { name: 'In this digest' })).toBeNull()
  expect(screen.getByText('Caption fetching is off')).toBeInTheDocument()
  await expectAccessible(container)
})

it.each([{ language: 'en', kind: 'feed' }, { language: null, kind: null }])(
  'shows an old or English digest without Chinese marks or invented kind icons', async ({ language, kind }) => {
    fetchMock.mockResolvedValue(respond({
      id: 7, language, created_at: '2026-10-03T10:00:00Z', model_id: 'test',
      topics: [{ title: 'Topic', overview: 'Overview', items: [{
        title: 'Article', link: 'https://example.test/item', source_name: 'Source',
        source_kind: kind, published_at: null, summary: 'Summary', summary_unavailable: false,
      }] }],
    }))
    const { container } = page()
    await screen.findByRole('heading', { name: 'Topic' })
    expect(container.querySelector('[lang="zh-Hans"]')).toBeNull()
    if (language === null) expect(container.querySelector('.page-digest [lang]')).toBeNull()
    if (!kind) expect(screen.getByRole('link', { name: 'Article (opens the original)' }).closest('article')?.querySelector('svg.icon-sm')).toBeNull()
    await expectAccessible(container)
  })

it('omits all digest language marks when the saved preference is original', async () => {
  fetchMock.mockResolvedValue(respond({
    id: 7, language: 'original', created_at: '2026-10-03T10:00:00Z', model_id: 'test',
    topics: [
      { title: 'First', overview: 'Overview', items: [{
        title: 'Original title', link: 'https://example.test/a', source_name: 'News',
        published_at: null, summary: 'Summary', summary_unavailable: false,
      }] },
      { title: 'Second', overview: 'Overview', items: [] },
    ],
  }))
  const { container } = page()
  await screen.findByRole('navigation', { name: 'In this digest' })
  expect(container.querySelector('.page-digest [lang]')).toBeNull()
  await expectAccessible(container)
})

it.each([
  [12, 4, 'Tokens: 12 in / 4 out'],
  [null, null, 'Tokens: not reported'],
])('shows saved token totals %s / %s', async (prompt, completion, text) => {
  fetchMock.mockResolvedValue(respond({
    id: 7, created_at: '2026-10-03T10:00:00Z', model_id: 'test',
    topics: [], creator_updates: [], prompt_tokens: prompt, completion_tokens: completion,
  }))
  page()
  expect((await screen.findByText(/Tokens:/)).textContent).toBe(text)
})
