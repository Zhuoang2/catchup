import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import Bookmarks from './Bookmarks'
import { expectAccessible } from '../test/accessibility'

const fetchMock = vi.fn()
const respond = (value: unknown, status = 200) => ({
  ok: status < 400, status, json: async () => value,
})
const entries = [
  {
    id: 21, title: 'Saved article', link: 'https://example.test/saved', source_name: 'Blog',
    source_kind: 'feed', published_at: '2026-10-02T12:00:00Z', summary: 'Saved summary',
    summary_unavailable: false, bookmarked: true, liked: false, rating: null, note: null,
    bookmarked_at: '2026-10-04T12:00:00Z',
    digest: { id: 5, created_at: '2026-10-03T12:00:00Z', language: null },
    images: [{ url: 'https://cdn.example/chart.png', alt: 'Growth chart' }],
    also_read: [{ title: 'Details', url: 'https://docs.example/details', kind: 'link' }],
  },
  {
    id: 22, title: 'Another article', link: 'https://example.test/another', source_name: 'News',
    source_kind: 'feed', published_at: null, summary: 'Chinese summary',
    summary_unavailable: false, bookmarked: true, liked: false, rating: null, note: null,
    bookmarked_at: '2026-10-03T12:00:00Z',
    digest: { id: 3, created_at: '2026-10-01T12:00:00Z', language: 'zh-Hans' },
    images: [], also_read: [],
  },
]

function page() {
  return render(<MemoryRouter initialEntries={['/bookmarks']}>
    <Routes><Route path="/bookmarks" element={<Bookmarks/>}/></Routes>
  </MemoryRouter>)
}

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock)
  fetchMock.mockImplementation(async (url: string) => {
    if (url === '/api/bookmarks') return respond(entries)
    if (url === '/api/settings/preferences') return respond({ show_images: true })
    throw new Error(`Unexpected request: ${url}`)
  })
})
afterEach(() => {
  vi.unstubAllGlobals()
  fetchMock.mockReset()
})

it('lists every bookmark whatever Items to show says', async () => {
  const saved = Array.from({ length: 8 }, (_, index) => ({
    ...entries[0], id: 31 + index, title: `Saved ${index + 1}`, importance: index % 5 + 1,
  }))
  fetchMock.mockImplementation(async (url: string) => {
    if (url === '/api/bookmarks') return respond(saved)
    if (url === '/api/settings/preferences') return respond({ show_images: true, top_items: 5 })
    throw Error(url)
  })
  page()
  await screen.findByRole('link', { name: 'Saved 1 (opens the original)' })
  for (let index = 1; index <= 8; index++) {
    expect(screen.getByRole('link', { name: `Saved ${index} (opens the original)` })).toBeInTheDocument()
  }
  expect(screen.getAllByRole('article')).toHaveLength(8)
})

it('lists bookmarked items with their digest link', async () => {
  const { container } = page()
  expect(await screen.findByRole('link', { name: 'Saved article (opens the original)' }))
    .toHaveAttribute('href', 'https://example.test/saved')
  expect(document.title).toBe('Bookmarks · CatchUp')
  expect(screen.getByRole('heading', { name: 'Bookmarks', level: 1 })).toBeInTheDocument()
  const articles = screen.getAllByRole('article')
  expect(articles).toHaveLength(2)
  const first = within(articles[0])
  expect(first.getByText('Saved summary')).toBeInTheDocument()
  expect(articles[0].querySelector('.item-meta')).toHaveTextContent('Blog')
  const from = first.getByRole('link', { name: 'From No. 5 · 3 Oct 2026' })
  expect(from).toHaveAttribute('href', '/digests/5')
  expect(from.closest('p')?.textContent).toMatch(/^From /)
  expect(first.getByRole('button', { name: 'Bookmark Saved article' })).toHaveAttribute('aria-pressed', 'true')
  expect(articles[1].querySelector('div.summary')).toHaveAttribute('lang', 'zh-Hans')
  expect(first.getByRole('link', { name: 'Details' })).toHaveAttribute('href', 'https://docs.example/details')
  expect(first.getByText('Growth chart', { selector: 'figcaption' })).toBeInTheDocument()
  await expectAccessible(container)
})

it('keeps an entry after its bookmark is removed', async () => {
  fetchMock.mockImplementation(async (url: string) => {
    if (url === '/api/bookmarks') return respond(entries)
    if (url === '/api/settings/preferences') return respond({ show_images: true })
    if (url === '/api/digest-items/21/bookmark') return respond({
      id: 21, bookmarked: false, liked: false, rating: null, note: null,
    })
    throw new Error(`Unexpected request: ${url}`)
  })
  const { container } = page()
  const button = await screen.findByRole('button', { name: 'Bookmark Saved article' })
  expect(container.querySelectorAll('section [role="status"]')).toHaveLength(1)
  const status = screen.getByRole('status')
  expect(status).toBeEmptyDOMElement()
  button.focus()
  fireEvent.click(button)
  await waitFor(() => expect(button).toHaveAttribute('aria-pressed', 'false'))
  expect(fetchMock).toHaveBeenCalledWith('/api/digest-items/21/bookmark', { method: 'DELETE' })
  expect(screen.getAllByRole('article')).toHaveLength(2)
  expect(button).toBeInTheDocument()
  expect(button).toHaveFocus()
  expect(status).toHaveTextContent('Bookmark removed.')
})

it('shows the empty state', async () => {
  fetchMock.mockResolvedValue(respond([]))
  page()
  expect(await screen.findByRole('heading', { name: 'No bookmarks yet' })).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Open the latest digest' })).toHaveAttribute('href', '/')
})

it('hides images when they are turned off', async () => {
  fetchMock.mockImplementation(async (url: string) =>
    respond(url === '/api/bookmarks' ? entries : { show_images: false }))
  const { container } = page()
  await screen.findByRole('link', { name: 'Saved article (opens the original)' })
  expect(container.querySelector('img')).toBeNull()
})

it('reports a load error', async () => {
  fetchMock.mockImplementation(async (url: string) => url === '/api/bookmarks'
    ? respond({ error: { code: 'x', message: 'Could not load.' } }, 500)
    : respond({ show_images: true }))
  page()
  expect(await screen.findByRole('alert')).toHaveTextContent('Could not load.')
})
