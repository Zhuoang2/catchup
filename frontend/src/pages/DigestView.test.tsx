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
