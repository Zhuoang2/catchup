import { fireEvent, render, screen, waitFor, act } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { expectAccessible } from '../test/accessibility'
import Generate from './Generate'

const fetchMock = vi.fn()
const respond = (value: unknown, status = 200) => ({ ok: status < 400, status, json: async () => value })
const run = {
  id: 1, status: 'collecting', items_total: 0, items_done: 0,
  waiting_count: 0, deferred_count: 0, prompt_tokens: null, completion_tokens: null,
  sources_total: 3, source_checks: [
    { source_id: 1, source_title: 'News', status: 'failed', possible_gap: false, error: 'offline' },
    { source_id: 2, source_title: 'Blog', status: 'new_items', possible_gap: true, error: null },
  ], error_kind: null, error_message: null, digest_id: null,
}
const sources = [{ kind: 'feed' }, { kind: 'podcast' }, { kind: 'youtube' }]
const history = [{ id: 4, created_at: '2026-10-03T10:00:00Z', item_count: 8, source_count: 3 }]
function mockPage(options: { ready?: boolean; run?: unknown; sources?: unknown[]; history?: unknown[] } = {}) {
  fetchMock.mockImplementation(async (path: string) => {
    if (path === '/api/settings/model') return respond({ key_set: options.ready ?? true })
    if (path === '/api/sources') return respond(options.sources ?? sources)
    if (path === '/api/digests') return respond(options.history ?? history)
    if (path === '/api/digest-runs/active') return respond(options.run ?? null)
    throw Error(`Unexpected request ${path}`)
  })
  return render(<MemoryRouter><Generate/></MemoryRouter>)
}

beforeEach(() => { vi.stubGlobal('fetch', fetchMock) })
afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); fetchMock.mockReset() })

it.each([['existing sources', sources], ['no sources (fresh install)', []]])(
  'puts model setup first with a visible disabled Generate and a state-aware rail: %s', async (_case, list) => {
  const { container } = mockPage({ ready: false, sources: list, history })
  expect((await screen.findAllByRole('link', { name: 'Set up your model' }))[0]).toHaveClass('btn-primary')
  expect(container.querySelectorAll('.btn-primary')).toHaveLength(1)
  expect(screen.getByRole('button', { name: 'Generate digest' })).toBeDisabled()
  expect(screen.getByText('Available once a model is set up and a source is added.')).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: 'Getting started' })).toBeInTheDocument()
  expect(screen.queryByRole('heading', { name: 'Last digest' })).toBeNull()
  expect(screen.queryByRole('heading', { name: 'Your sources' })).toBeNull()
  expect(container.querySelector('.hero-last')).toBeNull()
  expect(screen.queryByRole('link', { name: 'Add sources' })).not.toHaveClass('btn-primary')
  await expectAccessible(container)
})

it('offers Generate as the only primary action while idle', async () => {
  const { container } = mockPage({ history: [], sources: [{ kind: 'feed' }] })
  await screen.findByText(/Check your 1 source and summarize/)
  expect(container.querySelectorAll('.btn-primary')).toHaveLength(1)
  expect(screen.getByRole('button', { name: 'Generate digest' })).toHaveClass('btn-primary')
  expect(screen.getByText(/Check your 1 source and summarize/)).toBeInTheDocument()
  await expectAccessible(container)
})

it('offers Add sources as the only primary action when the configured model has no sources', async () => {
  const { container } = mockPage({ ready: true, sources: [], history: [] })
  expect(await screen.findByRole('link', { name: 'Add sources' })).toHaveAttribute('href', '/sources')
  expect(screen.getByRole('link', { name: 'Add sources' })).toHaveClass('btn-primary')
  expect(container.querySelectorAll('.btn-primary')).toHaveLength(1)
  const generate = screen.getByRole('button', { name: 'Generate digest' })
  expect(generate).toBeDisabled()
  expect(generate).toHaveClass('btn-secondary')
  expect(generate).toHaveAccessibleDescription('Available once a source is added.')
})

it('keeps the hero last-digest link when the configured model has no sources', async () => {
  const { container } = mockPage({ ready: true, sources: [], history })
  await screen.findByRole('link', { name: 'Add sources' })
  expect(container.querySelector('.hero-last')).toHaveTextContent('Last digest: No. 4')
})

it('shows a running run, not the no-sources state, when sources are empty', async () => {
  const { container } = mockPage({ ready: true, sources: [], run: { ...run, status: 'collecting' } })
  expect(await screen.findByRole('button', { name: 'Generating…' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Generating…' })).toHaveClass('btn-primary')
  expect(container.querySelectorAll('.btn-primary')).toHaveLength(1)
  expect(screen.queryByRole('link', { name: 'Add sources' })).toBeNull()
})

it.each(['collecting', 'summarizing'])('shows %s progress and named source outcomes', async status => {
  const { container } = mockPage({ run: { ...run, status, items_total: 12, items_done: 5 } })
  expect(await screen.findByRole('progressbar', {
    name: status === 'collecting' ? 'Sources checked: 2 of 3' : 'Items summarized: 5 of 12',
  })).toBeInTheDocument()
  expect(screen.getByText('News').closest('li')).toHaveTextContent('Failed')
  expect(screen.getByText('Blog').closest('li')).toHaveTextContent('Possible gap')
  expect(screen.getByText('Failed')).toHaveClass('chip-error')
  expect(screen.getByText('Possible gap')).toHaveClass('chip-warn')
  expect(screen.getByRole('heading', { name: 'Your sources' }).closest('section'))
    .toHaveTextContent('1 podcast · 1 YouTube · 1 website')
  if (status === 'collecting') expect(screen.getByRole('status')).toHaveTextContent('Checking sources, 2 of 3')
  expect(container.querySelectorAll('.btn-primary')).toHaveLength(1)
  expect(screen.getByRole('button', { name: 'Generating…' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Generating…' })).toHaveClass('btn-primary')
  await expectAccessible(container)
})

it('shows the saved digest as the only primary action after success', async () => {
  const { container } = mockPage({ run: {
    ...run, status: 'succeeded', items_total: 12, items_done: 12, digest_id: 8,
    waiting_count: 2, deferred_count: 5, prompt_tokens: 12, completion_tokens: 4,
  } })
  expect(await screen.findByRole('link', { name: 'View digest' })).toHaveAttribute('href', '/digests/8')
  expect(container.querySelectorAll('.btn-primary')).toHaveLength(1)
  expect(screen.getByRole('button', { name: 'Generate digest' })).toHaveClass('btn-secondary')
  expect(screen.getByText('2 items waiting for transcripts or captions')).toBeInTheDocument()
  expect(screen.getByText('5 videos deferred to the next run')).toBeInTheDocument()
  expect(screen.getByRole('status')).toHaveTextContent('Digest ready: 12 items')
  expect(container.querySelector('.result-ok .result-meta')).toHaveTextContent('Tokens: 12 in / 4 out')
  await expectAccessible(container)
})

it('shows no primary action after a no-new-content run, with rate limit and held counts', async () => {
  const { container } = mockPage({ run: {
    ...run, status: 'no_new_content', waiting_count: 2, deferred_count: 5,
    source_checks: [{ ...run.source_checks[0], rate_limited: true, http_status: 429 }],
  } })
  expect(await screen.findByRole('heading', { name: 'No new content' })).toBeInTheDocument()
  expect(container.querySelector('.result-none .result-head .icon-result')).toBeInTheDocument()
  expect(container.querySelector('.result-none .result-meta')).toHaveTextContent('Nothing new')
  expect(container.querySelectorAll('.btn-primary')).toHaveLength(0)
  expect(screen.getByText('Rate limited · try later')).toBeInTheDocument()
  expect(screen.getByRole('status')).toHaveTextContent('No new content')
  await expectAccessible(container)
})

it.each([
  ['auth_failed', 'Check settings'], ['run_failed', 'Try again'],
])('offers the right primary action for %s with reused summary copy', async (error_kind, primary) => {
  const { container } = mockPage({ run: {
    ...run, status: 'failed', error_kind, items_total: 12, items_done: 3,
    error_message: 'The provider rejected the API key. Check the model settings.',
  } })
  expect(await screen.findByText('The provider rejected the API key. Check the model settings.')).toBeInTheDocument()
  expect(screen.queryByRole('alert')).toBeNull()
  expect(screen.getByRole('status')).toHaveTextContent('Digest generation failed: The provider rejected the API key.')
  expect(container.querySelectorAll('.btn-primary')).toHaveLength(1)
  expect(container.querySelector('.btn-primary')).toHaveTextContent(primary)
  expect(screen.getByText(/No digest was saved/)).toHaveTextContent('summaries are reused next time')
  await expectAccessible(container)
})

it('does not claim to have summarized zero items before an interrupted run', async () => {
  const { container } = mockPage({ run: { ...run, status: 'failed', error_kind: 'interrupted',
    items_total: 0, items_done: 0, error_message: 'Interrupted.' } })
  expect(await screen.findByText('Interrupted.')).toBeInTheDocument()
  expect(container.querySelector('.result-card .result-meta')).toHaveTextContent('No digest was saved.')
  expect(container.querySelector('.result-card .result-meta')).not.toHaveTextContent('0 of 0')
})

it('polls from summarizing to success with a persistent status region using fake timers', async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true })
  fetchMock.mockImplementation(async (path: string) => {
    if (path === '/api/settings/model') return respond({ key_set: true })
    if (path === '/api/sources') return respond(sources)
    if (path === '/api/digests') return respond(history)
    if (path === '/api/digest-runs/active') return respond({ ...run, status: 'summarizing', items_total: 12, items_done: 5 })
    if (path === '/api/digest-runs/1') return respond({ ...run, status: 'succeeded',
      items_total: 12, items_done: 12, digest_id: 8 })
    throw Error(path)
  })
  render(<MemoryRouter><Generate/></MemoryRouter>)
  expect(await screen.findByRole('status')).toHaveTextContent('Summarizing, 5 of 12')
  const statusRegion = screen.getByRole('status')
  await act(async () => { await vi.advanceTimersByTimeAsync(1000) })
  expect(statusRegion).toBe(screen.getByRole('status'))
  expect(statusRegion).toHaveTextContent('Digest ready: 12 items')
})

it('announces a polled run failure only through the persistent status region', async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true })
  fetchMock.mockImplementation(async (path: string) => {
    if (path === '/api/settings/model') return respond({ key_set: true })
    if (path === '/api/sources') return respond(sources)
    if (path === '/api/digests') return respond(history)
    if (path === '/api/digest-runs/active') return respond(run)
    if (path === '/api/digest-runs/1') return respond({ ...run, status: 'failed',
      error_kind: 'provider_error', error_message: 'Provider is unavailable.' })
    throw Error(path)
  })
  render(<MemoryRouter><Generate/></MemoryRouter>)
  await screen.findByRole('progressbar')
  await act(async () => { await vi.advanceTimersByTimeAsync(1000) })
  expect(screen.getByText('Provider is unavailable.')).toBeInTheDocument()
  expect(screen.queryByRole('alert')).toBeNull()
  expect(screen.getByRole('status')).toHaveTextContent('Digest generation failed: Provider is unavailable.')
})

it.each([[3, 1], [2, 0]])('announces %i saved items when %i were summarized', async (saved, summarized) => {
  vi.useFakeTimers({ shouldAdvanceTime: true })
  fetchMock.mockImplementation(async (path: string) => {
    if (path === '/api/settings/model') return respond({ key_set: true })
    if (path === '/api/sources') return respond(sources)
    if (path === '/api/digests') return respond(history)
    if (path === '/api/digest-runs/active') return respond({ ...run, status: 'summarizing',
      items_total: summarized, items_done: summarized })
    if (path === '/api/digest-runs/1') return respond({ ...run, status: 'succeeded',
      items_total: summarized, items_done: summarized, digest_id: 8, digest_item_count: saved })
    throw Error(path)
  })
  const { container } = render(<MemoryRouter><Generate/></MemoryRouter>)
  await screen.findByRole('progressbar')
  await act(async () => { await vi.advanceTimersByTimeAsync(1000) })
  expect(screen.getByRole('status')).toHaveTextContent(`Digest ready: ${saved} items`)
  expect(container.querySelector('.result-ok .result-meta')).toHaveTextContent(`${saved} items`)
})

it('keeps an active run visible when the digest list fails', async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true })
  fetchMock.mockImplementation(async (path: string) => {
    if (path === '/api/settings/model') return respond({ key_set: true })
    if (path === '/api/sources') return respond(sources)
    if (path === '/api/digests') return respond({ error: { code: 'request_failed', message: 'History unavailable' } }, 503)
    if (path === '/api/digest-runs/active') return respond({ ...run, status: 'summarizing',
      items_total: 12, items_done: 5 })
    if (path === '/api/digest-runs/1') return respond(run)
    throw Error(path)
  })
  const { container } = render(<MemoryRouter><Generate/></MemoryRouter>)
  expect(await screen.findByRole('progressbar', { name: 'Items summarized: 5 of 12' })).toBeInTheDocument()
  expect(screen.getByRole('alert')).toHaveTextContent('History unavailable')
  expect(container.querySelectorAll('.btn-primary')).toHaveLength(1)
  expect(screen.getByRole('button', { name: 'Generating…' })).toBeDisabled()
})

it('keeps a startup load error visible through successful progress polls', async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true })
  fetchMock.mockImplementation(async (path: string) => {
    if (path === '/api/settings/model') return respond({ key_set: true })
    if (path === '/api/sources') return respond(sources)
    if (path === '/api/digests') return respond({
      error: { code: 'request_failed', message: 'History unavailable' },
    }, 503)
    if (path === '/api/digest-runs/active' || path === '/api/digest-runs/1') {
      return respond({ ...run, status: 'summarizing', items_total: 12, items_done: 5 })
    }
    throw Error(path)
  })
  render(<MemoryRouter><Generate/></MemoryRouter>)
  expect(await screen.findByRole('alert')).toHaveTextContent('Could not load some page details')
  await act(async () => { await vi.advanceTimersByTimeAsync(2000) })
  expect(fetchMock.mock.calls.filter(([path]) => path === '/api/digest-runs/1')).toHaveLength(2)
  expect(screen.getByRole('alert')).toHaveTextContent('Could not load some page details')
})

it('does not invent source counts when the source list cannot be read', async () => {
  fetchMock.mockImplementation(async (path: string) => {
    if (path === '/api/settings/model') return respond({ key_set: true })
    if (path === '/api/sources') return respond({
      error: { code: 'request_failed', message: 'Sources unavailable' },
    }, 503)
    if (path === '/api/digests') return respond(history)
    if (path === '/api/digest-runs/active') return respond(null)
    throw Error(path)
  })
  const { container } = render(<MemoryRouter><Generate/></MemoryRouter>)
  expect(await screen.findByRole('alert')).toHaveTextContent('Sources unavailable')
  expect(screen.getByText('Check your sources and summarize everything new since your last digest.'))
    .toBeInTheDocument()
  expect(screen.queryByText(/Check your 0 sources/)).toBeNull()
  expect(screen.queryByText(/Add sources before generating a digest/)).toBeNull()
  expect(screen.queryByRole('heading', { name: 'Your sources' })).toBeNull()
  expect(screen.queryByRole('link', { name: 'Add sources' })).toBeNull()
  expect(screen.getByRole('button', { name: 'Generate digest' })).toBeEnabled()
  expect(screen.getByRole('button', { name: 'Generate digest' })).toHaveClass('btn-primary')
  await expectAccessible(container)
})

it('shows a short hero date but keeps the rail last-digest date long', async () => {
  const { container } = mockPage({ history: [{
    id: 3, created_at: '2026-10-05T09:00:00', item_count: 4, source_count: 2,
  }] })
  await screen.findByRole('heading', { name: 'Last digest' })
  expect(container.querySelector('.hero-last')).toHaveTextContent('Last digest: No. 3 · 5 Oct 2026, 09:00')
  expect(screen.getByRole('heading', { name: 'Last digest' }).closest('section'))
    .toHaveTextContent('No. 3 · Monday, 5 October 2026, 09:00')
})

it('starts one run, polls to success and refreshes the last digest', async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true })
  let historyReads = 0
  fetchMock.mockImplementation(async (path: string, options?: RequestInit) => {
    if (path === '/api/settings/model') return respond({ key_set: true })
    if (path === '/api/sources') return respond(sources)
    if (path === '/api/digests') return respond(++historyReads === 1 ? history
      : [{ id: 9, created_at: '2026-10-04T10:00:00Z', item_count: 12, source_count: 3 }])
    if (path === '/api/digest-runs/active') return respond(null)
    if (path === '/api/digest-runs' && options?.method === 'POST') return respond(run)
    if (path === '/api/digest-runs/1') return respond({ ...run, status: 'succeeded',
      items_total: 12, items_done: 12, digest_id: 9 })
    throw Error(path)
  })
  render(<MemoryRouter><Generate/></MemoryRouter>)
  await waitFor(() => expect(screen.getByRole('button', { name: 'Generate digest' })).toBeEnabled())
  fireEvent.click(screen.getByRole('button', { name: 'Generate digest' }))
  expect(await screen.findByRole('progressbar', { name: 'Sources checked: 2 of 3' })).toBeInTheDocument()
  expect(fetchMock.mock.calls.filter(([path, options]) => path === '/api/digest-runs'
    && options?.method === 'POST')).toHaveLength(1)
  await act(async () => { await vi.advanceTimersByTimeAsync(1000) })
  expect(await screen.findByRole('link', { name: 'View digest' })).toHaveAttribute('href', '/digests/9')
  expect((await screen.findAllByRole('link', { name: /No. 9/ })).length).toBeGreaterThan(0)
  expect(screen.getByRole('heading', { name: 'Last digest' }).closest('section')).toHaveTextContent('No. 9')
  expect(historyReads).toBe(2)
})

it('switches to first-run after a model-not-configured POST', async () => {
  fetchMock.mockImplementation(async (path: string, options?: RequestInit) => {
    if (path === '/api/settings/model') return respond({ key_set: true })
    if (path === '/api/sources') return respond(sources)
    if (path === '/api/digests') return respond([])
    if (path === '/api/digest-runs/active') return respond(null)
    if (path === '/api/digest-runs' && options?.method === 'POST') {
      return respond({ error: { code: 'model_not_configured', message: 'Set up your model' } }, 400)
    }
    throw Error(path)
  })
  render(<MemoryRouter><Generate/></MemoryRouter>)
  await waitFor(() => expect(screen.getByRole('button', { name: 'Generate digest' })).toBeEnabled())
  fireEvent.click(screen.getByRole('button', { name: 'Generate digest' }))
  expect((await screen.findAllByRole('link', { name: 'Set up your model' }))[0]).toHaveClass('btn-primary')
  expect(screen.getByRole('button', { name: 'Generate digest' })).toBeDisabled()
})

it('uses action-specific alerts when starting or checking a run fails', async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true })
  let started = false
  fetchMock.mockImplementation(async (path: string, options?: RequestInit) => {
    if (path === '/api/settings/model') return respond({ key_set: true })
    if (path === '/api/sources') return respond(sources)
    if (path === '/api/digests') return respond([])
    if (path === '/api/digest-runs/active') return respond(null)
    if (path === '/api/digest-runs' && options?.method === 'POST') {
      if (!started) {
        started = true
        return respond({ error: { code: 'provider_error', message: 'Try later' } }, 503)
      }
      return respond(run)
    }
    if (path === '/api/digest-runs/1') return respond({
      error: { code: 'request_failed', message: 'Progress unavailable' },
    }, 503)
    throw Error(path)
  })
  render(<MemoryRouter><Generate/></MemoryRouter>)
  await waitFor(() => expect(screen.getByRole('button', { name: 'Generate digest' })).toBeEnabled())
  fireEvent.click(screen.getByRole('button', { name: 'Generate digest' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Could not start digest')
  fireEvent.click(screen.getByRole('button', { name: 'Generate digest' }))
  expect(await screen.findByRole('progressbar')).toBeInTheDocument()
  await act(async () => { await vi.advanceTimersByTimeAsync(1000) })
  expect(screen.getByRole('alert')).toHaveTextContent('Could not check digest progress')
})

it('recovers a run-active conflict without a duplicate run', async () => {
  let activeReads = 0
  fetchMock.mockImplementation(async (path: string) => {
    if (path === '/api/settings/model') return respond({ key_set: true })
    if (path === '/api/sources') return respond(sources)
    if (path === '/api/digests') return respond(history)
    if (path === '/api/digest-runs/active') return respond(++activeReads === 1 ? null : run)
    if (path === '/api/digest-runs') return respond({ error: { code: 'run_active', message: 'Already active' } }, 409)
    if (path === '/api/digest-runs/1') return respond(run)
    throw Error(path)
  })
  render(<MemoryRouter><Generate/></MemoryRouter>)
  await waitFor(() => expect(screen.getByRole('button', { name: 'Generate digest' })).toBeEnabled())
  fireEvent.click(screen.getByRole('button', { name: 'Generate digest' }))
  expect(await screen.findByRole('progressbar', { name: 'Sources checked: 2 of 3' })).toBeInTheDocument()
  expect(fetchMock.mock.calls.filter(([path, options]) => path === '/api/digest-runs'
    && options?.method === 'POST')).toHaveLength(1)
})
