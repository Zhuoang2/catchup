import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import History from './History'

const fetchMock = vi.fn()
const respond = (value: unknown, status = 200) => ({
  ok: status < 400, status, json: async () => value,
})

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock)
})
afterEach(() => {
  vi.unstubAllGlobals()
  fetchMock.mockReset()
})

it('shows saved digests with time, item and source counts and detail links', async () => {
  fetchMock.mockResolvedValue(respond([
    { id: 3, created_at: '2026-10-03T10:00:00Z', item_count: 8, source_count: 2 },
    { id: 1, created_at: '2026-10-01T10:00:00Z', item_count: 1, source_count: 1 },
  ]))
  render(<MemoryRouter><History /></MemoryRouter>)
  const links = await screen.findAllByRole('link')
  expect(links.map((link) => link.getAttribute('href'))).toEqual(['/digests/3', '/digests/1'])
  expect(links[0].querySelector('time')).toHaveAttribute('dateTime', '2026-10-03T10:00:00Z')
  expect(links[0].closest('li')).toHaveTextContent('8 items · 2 sources')
  expect(links[1].closest('li')).toHaveTextContent('1 item · 1 source')
  expect(fetchMock).toHaveBeenCalledWith('/api/digests', undefined)
})

it('shows empty history and request errors', async () => {
  fetchMock.mockResolvedValueOnce(respond([]))
  const page = render(<MemoryRouter><History /></MemoryRouter>)
  expect(await screen.findByText('No saved digests yet.')).toBeInTheDocument()
  page.unmount()
  fetchMock.mockResolvedValueOnce(respond({ error: { code: 'request_failed', message: 'Unavailable' } }, 503))
  render(<MemoryRouter><History /></MemoryRouter>)
  expect(await screen.findByRole('alert')).toHaveTextContent('Unavailable')
})
