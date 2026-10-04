import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import Generate from './Generate'

const fetchMock = vi.fn()
const respond = (value: unknown, status = 200) => ({
  ok: status < 400, status, json: async () => value,
})
const run = {
  id: 1, status: 'collecting', items_total: 0, items_done: 0,
  sources_total: 3, source_checks: [
    { source_id: 1, source_title: 'News', status: 'failed', possible_gap: false, error: 'offline' },
    { source_id: 2, source_title: 'Blog', status: 'new_items', possible_gap: true, error: null },
  ], error_kind: null, error_message: null, digest_id: null,
}
function page() { render(<MemoryRouter><Generate /></MemoryRouter>) }

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock)
  fetchMock.mockResolvedValue(respond(null))
})
afterEach(() => {
  vi.unstubAllGlobals()
  fetchMock.mockReset()
})

it('resumes collection progress and shows source outcomes on reload', async () => {
  fetchMock.mockResolvedValue(respond(run))
  page()
  expect(await screen.findByText('Sources checked: 2 of 3')).toBeInTheDocument()
  expect(screen.getByText(/News: failed: offline/)).toBeInTheDocument()
  expect(screen.getByText(/Blog: new_items \(possible gap\)/)).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Generate Digest' })).toBeDisabled()
})

it('labels rate-limited source checks distinctly from failures', async () => {
  fetchMock.mockResolvedValue(respond({
    ...run, status: 'no_new_content', source_checks: [
      { source_id: 1, source_title: 'News', status: 'failed', possible_gap: false,
        http_status: 429, rate_limited: true, error: 'The source is rate limiting requests.' },
    ],
  }))
  page()
  expect(await screen.findByText('News: rate limited (try later)')).toBeInTheDocument()
  expect(screen.queryByText(/News: failed/)).not.toBeInTheDocument()
})

it('starts generation and follows item progress, then links to the digest', async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true })
  try {
    fetchMock.mockImplementation(async (path: string) => {
      if (path === '/api/digest-runs/active') return respond(null)
      if (path === '/api/digest-runs') return respond({ ...run, status: 'summarizing', items_total: 12, items_done: 5 }, 202)
      if (path === '/api/digest-runs/1') return respond({
        ...run, status: 'succeeded', items_total: 12, items_done: 12, digest_id: 8,
      })
      throw new Error(path)
    })
    page()
    fireEvent.click(screen.getByRole('button', { name: 'Generate Digest' }))
    expect(await screen.findByText('Items summarized: 5 of 12')).toBeInTheDocument()
    await vi.advanceTimersByTimeAsync(1000)
    expect(await screen.findByRole('link', { name: 'View digest' })).toHaveAttribute('href', '/digests/8')
  } finally {
    vi.useRealTimers()
  }
})

it('shows no new content with failed source details', async () => {
  fetchMock.mockResolvedValue(respond({ ...run, status: 'no_new_content' }))
  page()
  expect(await screen.findByText('No new content.')).toBeInTheDocument()
  expect(screen.getByText(/News: failed: offline/)).toBeInTheDocument()
})

it('directs unconfigured users to settings', async () => {
  fetchMock.mockImplementation(async (path: string) => path.endsWith('/active')
    ? respond(null)
    : respond({ error: { code: 'model_not_configured', message: 'Configure model' } }, 409))
  page()
  fireEvent.click(screen.getByRole('button', { name: 'Generate Digest' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Set up your model')
  expect(screen.getByRole('link', { name: 'Settings' })).toHaveAttribute('href', '/settings')
})

it('shows provider failure and can start another run', async () => {
  fetchMock.mockResolvedValue(respond({
    ...run, status: 'failed', error_kind: 'auth_failed',
    error_message: 'The provider rejected the API key. Check the model settings.',
  }))
  page()
  expect(await screen.findByRole('alert')).toHaveTextContent('Check the model settings')
  expect(screen.getByRole('button', { name: 'Generate Digest' })).toBeEnabled()
})

it('resolves a run-active conflict by fetching the active run', async () => {
  let reads = 0
  fetchMock.mockImplementation(async (path: string) => {
    if (path.endsWith('/active')) return respond(++reads === 1 ? null : run)
    return respond({ error: { code: 'run_active', message: 'Already active' } }, 409)
  })
  page()
  await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/digest-runs/active', undefined))
  fireEvent.click(screen.getByRole('button', { name: 'Generate Digest' }))
  expect(await screen.findByText('Sources checked: 2 of 3')).toBeInTheDocument()
})
