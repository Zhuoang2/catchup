import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import DigestView from './DigestView'

const fetchMock = vi.fn()
const respond = (value: unknown, status = 200) => ({
  ok: status < 400, status, json: async () => value,
})
function page() {
  render(<MemoryRouter initialEntries={['/digests/7']}>
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
  const link = screen.getByRole('link', { name: 'Saved article' })
  expect(link).toHaveAttribute('href', 'https://example.test/article')
  expect(link).toHaveAttribute('target', '_blank')
  expect(link).toHaveAttribute('rel', 'noopener noreferrer')
  expect(link.closest('li')).toHaveTextContent('Blog')
  expect(link.closest('li')?.querySelector('time')).toHaveAttribute('dateTime', '2026-10-02T10:00:00Z')
  expect(screen.getByText('Summary unavailable')).toBeInTheDocument()
  expect(screen.getByRole('region', { name: 'Other' })).toHaveTextContent('Third summary')
  expect(fetchMock).toHaveBeenCalledWith('/api/digests/7', undefined)
})

it('reports an unavailable digest', async () => {
  fetchMock.mockResolvedValue(respond({ error: { code: 'not_found', message: 'Digest not found.' } }, 404))
  page()
  expect(await screen.findByRole('alert')).toHaveTextContent('Digest not found.')
})

it('renders creator updates after topics with saved wait labels', async () => {
  fetchMock.mockResolvedValue(respond({
    id: 7, created_at: '2026-10-03T10:00:00Z', model_id: 'test',
    transcript_wait_days: 10,
    topics: [{ title: 'Technology', overview: 'News', items: [] }],
    creator_updates: [
      { source_name: 'Show', items: [
        { title: 'Episode', link: 'https://example.test/ep', published_at: null, reason: 'no_transcript' },
      ] },
      { source_name: 'Channel', items: [
        { title: 'Off', link: 'https://example.test/off', published_at: null, reason: 'captions_off' },
        { title: 'Missing', link: 'https://example.test/missing',
          published_at: '2026-10-02T10:00:00Z', reason: 'no_captions' },
        { title: 'Blocked', link: 'https://example.test/blocked', published_at: null, reason: 'blocked' },
        { title: 'Failed', link: 'https://example.test/failed', published_at: null, reason: 'captions_failed' },
      ] },
    ],
  }))
  page()
  const creator = await screen.findByRole('region', { name: 'Creator updates' })
  expect(creator.compareDocumentPosition(screen.getByRole('region', { name: 'Technology' }))
    & Node.DOCUMENT_POSITION_PRECEDING).toBeTruthy()
  expect(screen.getByRole('region', { name: 'Show' })).toHaveTextContent('No transcript within 10 days')
  expect(screen.getByRole('region', { name: 'Channel' })).toHaveTextContent('Caption fetching is off')
  expect(screen.getByRole('region', { name: 'Channel' })).toHaveTextContent('This video has no captions')
  expect(screen.getByRole('region', { name: 'Channel' })).toHaveTextContent('Blocked by YouTube')
  expect(screen.getByRole('region', { name: 'Channel' })).toHaveTextContent('Captions could not be fetched')
  expect(screen.getByRole('link', { name: 'Missing' }).closest('li')?.querySelector('time')).toBeTruthy()
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
  const item = (await screen.findByRole('link', { name: 'Episode' })).closest('li')!
  const blocks = Array.from(item.children).filter(element => element.textContent?.includes('Overview')
    || element.textContent?.includes('Key point') || element.textContent?.includes('Closing sentence'))
  expect(blocks.map(element => element.tagName)).toEqual(['P', 'UL', 'P'])
  expect(blocks.map(element => element.textContent)).toEqual([
    'Overview', 'Key point', 'Continuation\nClosing sentence',
  ])
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
  expect(await screen.findByText(text)).toBeInTheDocument()
})
