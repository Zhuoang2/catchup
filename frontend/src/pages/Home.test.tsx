import { fireEvent, render, screen, waitFor, act, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { expectAccessible } from '../test/accessibility'
import Home from './Home'
import DigestView from './DigestView'

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
const digest = {
  id: 4, created_at: '2026-10-03T10:00:00Z', model_id: 'test',
  item_count: 2, source_count: 2, topics: [
    { title: 'Technology', overview: 'New topics', items: [{
      title: 'Saved story', link: 'https://example.test/story', source_name: 'News',
      published_at: null, summary: 'Summary', summary_unavailable: false,
    }] },
  ], creator_updates: [{ source_name: 'Show', source_kind: 'podcast', items: [{
    title: 'Episode', link: 'https://example.test/episode', published_at: null,
    reason: 'no_transcript',
  }] }],
}
it('shows the same digest reading markup on Home and the saved digest page', async () => {
  const edition = { ...digest, id: 7 }
  const home = mockPage({ latest: edition })
  await within(home.container).findByRole('heading', { name: 'Technology' })
  fetchMock.mockImplementation(async (path: string) => {
    if (path === '/api/digests/7') return respond(edition)
    throw Error(path)
  })
  const saved = render(<MemoryRouter initialEntries={['/digests/7']}>
    <Routes><Route path="/digests/:id" element={<DigestView/>}/></Routes>
  </MemoryRouter>)
  await within(saved.container).findByRole('heading', { name: 'Technology' })
  const homeArticle = home.container.querySelector('section.page-digest')!.cloneNode(true) as HTMLElement
  const savedArticle = saved.container.querySelector('section.page-digest')!.cloneNode(true) as HTMLElement
  homeArticle.classList.remove('page-home')
  homeArticle.querySelector('.run-bar')!.remove()
  savedArticle.querySelector('.back-link')!.remove()
  expect(homeArticle.outerHTML).toBe(savedArticle.outerHTML)
})
it('shows the latest article and one compact action above its headline without a rail', async () => {
  const { container } = mockPage({ latest: digest })
  expect(await screen.findByRole('heading', { name: 'Technology' })).toBeInTheDocument()
  expect(screen.getByRole('navigation', { name: 'In this digest' })).toHaveTextContent('Creator updates')
  expect(screen.getByRole('link', { name: 'Saved story (opens the original)' })).toBeInTheDocument()
  const bar = screen.getByRole('region', { name: 'Digest run' })
  expect(bar).toHaveTextContent('3 sources ·')
  expect(screen.getByRole('link', { name: 'Manage sources' })).toHaveAttribute('href', '/sources')
  expect(bar.querySelectorAll('.btn-primary')).toHaveLength(1)
  expect(screen.getByRole('button', { name: 'Generate digest' })).toHaveClass('btn-primary')
  expect(bar.querySelector('h1,h2,h3')).toBeNull()
  expect(container.querySelector('h1')).toBe(container.querySelector('.digest-head h1'))
  expect(container.querySelector('.rail')).toBeNull()
  expect(document.title).toBe('Latest · No. 4 · CatchUp')
  await expectAccessible(container)
})

it.each([
  [false, sources, 'Set up your model', 'Available once a model is set up and a source is added.'],
  [true, [], 'Add sources', 'Available once a source is added.'],
] as const)('offers %s / %s guidance while keeping a saved digest', async (ready, list, primary, reason) => {
  const { container } = mockPage({ ready, sources: [...list], latest: digest })
  expect(await screen.findByRole('heading', { name: 'Technology' })).toBeInTheDocument()
  expect(screen.getByRole('link', { name: primary })).toHaveClass('btn-primary')
  expect(container.querySelectorAll('.btn-primary')).toHaveLength(1)
  expect(screen.getByRole('button', { name: 'Generate digest' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Generate digest' })).toHaveAccessibleDescription(reason)
  await expectAccessible(container)
})

it('titles an empty home without an edition', async () => {
  const { container } = mockPage()
  await screen.findByRole('button', { name: 'Generate digest' })
  expect(document.title).toBe('Latest · CatchUp')
  await expectAccessible(container)
})
it('keeps the article beneath named run progress and source checks', async () => {
  const { container } = mockPage({ latest: digest, run })
  expect(await screen.findByRole('progressbar', { name: 'Sources checked: 2 of 3' })).toBeInTheDocument()
  const bar = screen.getByRole('region', { name: 'Digest run' })
  expect(bar).toHaveTextContent('Checking sources')
  expect(bar).toHaveTextContent('News')
  expect(screen.getByRole('heading', { name: 'Technology' })).toBeInTheDocument()
  expect(bar.querySelector('h1,h2,h3')).toBeNull()
  expect(screen.getByRole('status')).toHaveTextContent('Checking sources, 2 of 3')
  await expectAccessible(container)
})

it('shows a saved result, held notes and checks without a new primary action', async () => {
  const { container } = mockPage({ latest: digest, run: {
    ...run, status: 'succeeded', digest_id: 4, digest_item_count: 2, digest_update_count: 1,
    waiting_count: 2, deferred_count: 3, prompt_tokens: 10, completion_tokens: 5,
  } })
  const bar = await screen.findByRole('region', { name: 'Digest run' })
  expect(bar).toHaveTextContent('2 items (1 summarized, 1 in Creator updates) · 3 sources · Tokens: 10 in / 5 out')
  expect(bar).toHaveTextContent('2 items waiting for transcripts or captions')
  expect(bar).toHaveTextContent('3 videos deferred to the next run')
  expect(bar).toHaveTextContent('News')
  expect(bar.querySelectorAll('.btn-primary')).toHaveLength(0)
  expect(screen.queryByRole('link', { name: 'View digest' })).toBeNull()
  expect(screen.getByRole('button', { name: 'Generate digest' })).toHaveClass('btn-secondary')
  expect(screen.getByRole('status')).toHaveTextContent('Digest ready: 2 items (1 summarized, 1 in Creator updates)')
  expect(screen.getByRole('heading', { name: 'Technology' })).toBeInTheDocument()
  await expectAccessible(container)
})

it('keeps the digest after a run finds nothing new', async () => {
  const { container } = mockPage({ latest: digest, run: { ...run, status: 'no_new_content' } })
  const bar = await screen.findByRole('region', { name: 'Digest run' })
  expect(bar).toHaveTextContent('Nothing new since your last digest')
  expect(bar).toHaveTextContent('News')
  expect(bar.querySelectorAll('.btn-primary')).toHaveLength(0)
  expect(screen.getByRole('heading', { name: 'Technology' })).toBeInTheDocument()
  expect(screen.getByRole('status')).toHaveTextContent('No new content')
  await expectAccessible(container)
})

it.each([
  ['auth_failed', 'Check settings'],
  ['provider_error', 'Try again'],
])('keeps the article and a single %s failure action', async (error_kind, primary) => {
  const { container } = mockPage({ latest: digest, run: {
    ...run, status: 'failed', error_kind, items_total: 5, items_done: 2, error_message: 'Run failed.',
  } })
  const bar = await screen.findByRole('region', { name: 'Digest run' })
  expect(bar).toHaveTextContent('2 of 5 items were summarized before the error.')
  expect(bar).toHaveTextContent('News')
  expect(bar.querySelectorAll('.btn-primary')).toHaveLength(1)
  expect(bar.querySelector('.btn-primary')).toHaveTextContent(primary)
  if (error_kind === 'auth_failed') expect(screen.getByRole('button', { name: 'Try again' })).toHaveClass('btn-secondary')
  expect(screen.queryByRole('alert')).toBeNull()
  expect(screen.getByRole('heading', { name: 'Technology' })).toBeInTheDocument()
  expect(screen.getByRole('status')).toHaveTextContent('Digest generation failed: Run failed.')
  await expectAccessible(container)
})

it.each([
  ['existing', digest],
  ['first', null],
])('swaps the %s article after a run, retaining status and focus', async (_case, latest) => {
  vi.useFakeTimers({ shouldAdvanceTime: true })
  const next = { ...digest, id: 9, topics: [{ ...digest.topics[0], title: 'New edition' }] }
  fetchMock.mockImplementation(async (path: string) => {
    if (path === '/api/settings/model') return respond({ key_set: true })
    if (path === '/api/sources') return respond(sources)
    if (path === '/api/digests/latest') return respond(latest)
    if (path === '/api/digest-runs/active') return respond(run)
    if (path === '/api/digest-runs/1') return respond({
      ...run, status: 'succeeded', digest_id: 9, digest_item_count: 2, digest_update_count: 1,
    })
    if (path === '/api/digests/9') return respond(next)
    throw Error(`Unexpected request ${path}`)
  })
  const focus = vi.spyOn(HTMLElement.prototype, 'focus')
  render(<MemoryRouter><Home/></MemoryRouter>)
  await screen.findByRole('progressbar')
  const status = screen.getByRole('status')
  if (latest) {
    const link = screen.getByRole('link', { name: 'Manage sources' })
    link.focus()
    focus.mockClear()
  }
  await act(async () => { await vi.advanceTimersByTimeAsync(1000) })
  expect(await screen.findByRole('heading', { name: 'New edition' })).toBeInTheDocument()
  expect(screen.queryByRole('heading', { name: 'Technology' })).toBeNull()
  expect(document.title).toBe('Latest · No. 9 · CatchUp')
  expect(fetchMock).toHaveBeenCalledWith('/api/digests/9', undefined)
  expect(fetchMock.mock.calls.some(([path]) => path === '/api/digests')).toBe(false)
  expect(screen.getByRole('status')).toBe(status)
  expect(status.textContent).toBe('Digest ready: 2 items (1 summarized, 1 in Creator updates)')
  if (latest) expect(document.activeElement).toBe(screen.getByRole('link', { name: 'Manage sources' }))
  expect(focus).not.toHaveBeenCalled()
  focus.mockRestore()
})

it('keeps the previous article and links to the new edition when detail loading fails', async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true })
  fetchMock.mockImplementation(async (path: string) => {
    if (path === '/api/settings/model') return respond({ key_set: true })
    if (path === '/api/sources') return respond(sources)
    if (path === '/api/digests/latest') return respond(digest)
    if (path === '/api/digest-runs/active') return respond(run)
    if (path === '/api/digest-runs/1') return respond({ ...run, status: 'succeeded', digest_id: 9 })
    if (path === '/api/digests/9') return respond({
      error: { code: 'not_found', message: 'Not ready' },
    }, 404)
    throw Error(path)
  })
  render(<MemoryRouter><Home/></MemoryRouter>)
  await screen.findByRole('progressbar')
  await act(async () => { await vi.advanceTimersByTimeAsync(1000) })
  expect(await screen.findByText('Could not load the new digest')).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'View digest' })).toHaveAttribute('href', '/digests/9')
  expect(screen.getByRole('heading', { name: 'Technology' })).toBeInTheDocument()
  expect(document.title).toBe('Latest · No. 4 · CatchUp')
})

it('keeps Generate available when the latest digest fails to load', async () => {
  fetchMock.mockImplementation(async (path: string, options?: RequestInit) => {
    if (path === '/api/settings/model') return respond({ key_set: true })
    if (path === '/api/sources') return respond(sources)
    if (path === '/api/digests/latest') return respond({
      error: { code: 'request_failed', message: 'Offline' },
    }, 503)
    if (path === '/api/digest-runs/active') return respond(null)
    if (path === '/api/digest-runs' && options?.method === 'POST') return respond(run)
    throw Error(path)
  })
  render(<MemoryRouter><Home/></MemoryRouter>)
  expect(await screen.findByText('Could not load the latest digest')).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'View History' })).toHaveAttribute('href', '/digests')
  fireEvent.click(screen.getByRole('button', { name: 'Generate digest' }))
  expect(await screen.findByRole('progressbar')).toBeInTheDocument()
})

it('drops the startup latest-digest error when a run delivers a digest', async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true })
  fetchMock.mockImplementation(async (path: string, options?: RequestInit) => {
    if (path === '/api/settings/model') return respond({ key_set: true })
    if (path === '/api/sources') return respond(sources)
    if (path === '/api/digests/latest') return respond({
      error: { code: 'request_failed', message: 'Latest unavailable' },
    }, 503)
    if (path === '/api/digest-runs/active') return respond(null)
    if (path === '/api/digest-runs' && options?.method === 'POST') return respond(run)
    if (path === '/api/digest-runs/1') return respond({ ...run, status: 'succeeded', digest_id: 8 })
    if (path === '/api/digests/8') return respond({ ...digest, id: 8 })
    throw Error(path)
  })
  render(<MemoryRouter><Home/></MemoryRouter>)
  expect(await screen.findByRole('alert')).toHaveTextContent('Could not load the latest digest')
  fireEvent.click(screen.getByRole('button', { name: 'Generate digest' }))
  await screen.findByRole('progressbar')
  await act(async () => { await vi.advanceTimersByTimeAsync(1000) })
  expect(await screen.findByRole('heading', { name: 'Technology' })).toBeInTheDocument()
  expect(screen.queryByText('Could not load the latest digest')).toBeNull()
  expect(screen.queryByRole('alert')).toBeNull()
})

it('clears a failed new-digest fetch when another run is started', async () => {
  fetchMock.mockImplementation(async (path: string, options?: RequestInit) => {
    if (path === '/api/settings/model') return respond({ key_set: true })
    if (path === '/api/sources') return respond(sources)
    if (path === '/api/digests/latest') return respond(digest)
    if (path === '/api/digest-runs/active') return respond({ ...run, status: 'succeeded', digest_id: 8 })
    if (path === '/api/digests/8') return respond({
      error: { code: 'not_found', message: 'Missing edition' },
    }, 404)
    if (path === '/api/digest-runs' && options?.method === 'POST') return respond({ ...run, id: 2 })
    throw Error(path)
  })
  render(<MemoryRouter><Home/></MemoryRouter>)
  expect(await screen.findByText('Could not load the new digest')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Generate digest' }))
  expect(await screen.findByRole('progressbar')).toBeInTheDocument()
  expect(screen.queryByText('Could not load the new digest')).toBeNull()
})

it.each([
  ['failure', respond({ error: { code: 'not_found', message: 'Missing edition' } }, 404)],
  ['success', respond({ ...digest, id: 8 })],
])('shows a pending first digest without an action, then handles %s', async (outcome, response) => {
  let release!: (value: ReturnType<typeof respond>) => void
  const pending = new Promise<ReturnType<typeof respond>>(resolve => { release = resolve })
  fetchMock.mockImplementation(async (path: string) => {
    if (path === '/api/settings/model') return respond({ key_set: true })
    if (path === '/api/sources') return respond(sources)
    if (path === '/api/digests/latest') return respond(null)
    if (path === '/api/digest-runs/active') return respond({ ...run, status: 'succeeded', digest_id: 8 })
    if (path === '/api/digests/8') return pending
    throw Error(path)
  })
  const { container } = render(<MemoryRouter><Home/></MemoryRouter>)
  expect(await screen.findByText('Loading the new digest…')).toBeInTheDocument()
  expect(container.querySelectorAll('.btn-primary')).toHaveLength(0)
  expect(screen.queryByRole('link', { name: 'View digest' })).toBeNull()
  await expectAccessible(container)
  await act(async () => { release(response); await pending })
  if (outcome === 'failure') {
    expect(await screen.findByText('Could not load the new digest')).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: 'View digest' })).toHaveLength(1)
    expect(screen.getByRole('link', { name: 'View digest' })).toHaveAttribute('href', '/digests/8')
    expect(container.querySelectorAll('.btn-primary')).toHaveLength(0)
  } else {
    expect(await screen.findByRole('heading', { name: 'Technology' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'View digest' })).toBeNull()
  }
  await expectAccessible(container)
})

it('keeps other startup request errors in the bar when an article is shown', async () => {
  fetchMock.mockImplementation(async (path: string) => {
    if (path === '/api/settings/model') return respond({ key_set: true })
    if (path === '/api/sources') return respond({
      error: { code: 'request_failed', message: 'Sources unavailable' },
    }, 503)
    if (path === '/api/digests/latest') return respond(digest)
    if (path === '/api/digest-runs/active') return respond(null)
    throw Error(path)
  })
  render(<MemoryRouter><Home/></MemoryRouter>)
  expect(await screen.findByRole('heading', { name: 'Technology' })).toBeInTheDocument()
  expect(screen.getByRole('alert')).toHaveTextContent('Could not load some page details')
  expect(screen.getByRole('alert')).toHaveTextContent('Sources unavailable')
})

it('pairs the latest-digest error title with its own failure message', async () => {
  fetchMock.mockImplementation(async (path: string) => {
    if (path === '/api/settings/model') return respond({
      error: { code: 'request_failed', message: 'Model settings unavailable' },
    }, 503)
    if (path === '/api/sources') return respond(sources)
    if (path === '/api/digests/latest') return respond({
      error: { code: 'request_failed', message: 'Digest history unavailable' },
    }, 503)
    if (path === '/api/digest-runs/active') return respond(null)
    throw Error(path)
  })
  render(<MemoryRouter><Home/></MemoryRouter>)
  const alert = await screen.findByRole('alert')
  expect(alert).toHaveTextContent('Could not load the latest digest')
  expect(alert).toHaveTextContent('Digest history unavailable')
  expect(alert).not.toHaveTextContent('Model settings unavailable')
})

it.each([
  ['no_new_content', 8],
  ['succeeded', 9],
])('keeps a fetched edition when the next run ends %s', async (secondStatus, shownId) => {
  vi.useFakeTimers({ shouldAdvanceTime: true })
  let release!: (value: ReturnType<typeof respond>) => void
  const pending = new Promise<ReturnType<typeof respond>>(resolve => { release = resolve })
  let ninthFetches = 0
  // Hold an unexpected second fetch so a transient older edition cannot be hidden by its response.
  const repeatedNinth = new Promise<ReturnType<typeof respond>>(() => {})
  fetchMock.mockImplementation(async (path: string, options?: RequestInit) => {
    if (path === '/api/settings/model') return respond({ key_set: true })
    if (path === '/api/sources') return respond(sources)
    if (path === '/api/digests/latest') return respond(digest)
    if (path === '/api/digest-runs/active') return respond(run)
    if (path === '/api/digest-runs/1') return respond({ ...run, status: 'succeeded', digest_id: 8 })
    if (path === '/api/digests/8') return pending
    if (path === '/api/digest-runs' && options?.method === 'POST') {
      return respond({ ...run, id: 2, status: 'collecting' })
    }
    if (path === '/api/digest-runs/2') return respond({
      ...run, id: 2, status: secondStatus, digest_id: secondStatus === 'succeeded' ? 9 : null,
    })
    if (path === '/api/digests/9') return ++ninthFetches === 1 ? respond({ ...digest, id: 9,
      topics: [{ ...digest.topics[0], title: 'Newer edition' }] }) : repeatedNinth
    throw Error(path)
  })
  render(<MemoryRouter><Home/></MemoryRouter>)
  await screen.findByRole('progressbar')
  await act(async () => { await vi.advanceTimersByTimeAsync(1000) })
  await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/digests/8', undefined))
  fireEvent.click(screen.getByRole('button', { name: 'Generate digest' }))
  await screen.findByRole('progressbar')
  await act(async () => { await vi.advanceTimersByTimeAsync(1000) })
  if (secondStatus === 'succeeded') {
    expect(await screen.findByRole('heading', { name: 'Newer edition' })).toBeInTheDocument()
  } else expect(screen.getByRole('status')).toHaveTextContent('No new content')
  await act(async () => { release(respond({ ...digest, id: 8,
    topics: [{ ...digest.topics[0], title: 'Fetched edition' }] })); await pending })
  if (shownId === 9) {
    expect(screen.queryByRole('heading', { name: 'Fetched edition' })).toBeNull()
    expect(fetchMock.mock.calls.filter(([path]) => path === '/api/digests/9')).toHaveLength(1)
  }
  expect(await screen.findByRole('heading', { name: shownId === 8 ? 'Fetched edition' : 'Newer edition' }))
    .toBeInTheDocument()
  expect(document.title).toBe(`Latest · No. ${shownId} · CatchUp`)
})

it('hides an older digest fetch error after an overlapping run shows a newer edition', async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true })
  let release8!: (response: ReturnType<typeof respond>) => void
  const pending8 = new Promise<ReturnType<typeof respond>>(resolve => { release8 = resolve })
  fetchMock.mockImplementation(async (path: string, options?: RequestInit) => {
    if (path === '/api/settings/model') return respond({ key_set: true })
    if (path === '/api/sources') return respond(sources)
    if (path === '/api/digests/latest') return respond(digest)
    if (path === '/api/digest-runs/active') return respond(run)
    if (path === '/api/digest-runs/1') return respond({ ...run, status: 'succeeded', digest_id: 8 })
    if (path === '/api/digests/8') return pending8
    if (path === '/api/digest-runs' && options?.method === 'POST') return respond({ ...run, id: 2 })
    if (path === '/api/digest-runs/2') return respond({ ...run, id: 2, status: 'succeeded', digest_id: 9 })
    if (path === '/api/digests/9') return respond({ ...digest, id: 9,
      topics: [{ ...digest.topics[0], title: 'Newer edition' }] })
    throw Error(path)
  })
  render(<MemoryRouter><Home/></MemoryRouter>)
  await screen.findByRole('progressbar')
  await act(async () => { await vi.advanceTimersByTimeAsync(1000) })
  await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/digests/8', undefined))
  fireEvent.click(screen.getByRole('button', { name: 'Generate digest' }))
  await screen.findByRole('progressbar')
  await act(async () => { release8(respond({ error: { code: 'not_found', message: 'Missing 8' } }, 404)); await pending8 })
  expect(await screen.findByRole('alert')).toHaveTextContent('Could not load the new digest')
  await act(async () => { await vi.advanceTimersByTimeAsync(1000) })
  expect(await screen.findByRole('heading', { name: 'Newer edition' })).toBeInTheDocument()
  expect(screen.queryByRole('alert')).toBeNull()
  expect(screen.queryByRole('link', { name: 'View digest' })).toBeNull()
})

it('hides an older fetch error when the newer digest resolves in the same tick', async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true })
  let release8!: (response: ReturnType<typeof respond>) => void
  let release9!: (response: ReturnType<typeof respond>) => void
  const pending8 = new Promise<ReturnType<typeof respond>>(resolve => { release8 = resolve })
  const pending9 = new Promise<ReturnType<typeof respond>>(resolve => { release9 = resolve })
  fetchMock.mockImplementation(async (path: string, options?: RequestInit) => {
    if (path === '/api/settings/model') return respond({ key_set: true })
    if (path === '/api/sources') return respond(sources)
    if (path === '/api/digests/latest') return respond(digest)
    if (path === '/api/digest-runs/active') return respond(run)
    if (path === '/api/digest-runs/1') return respond({ ...run, status: 'succeeded', digest_id: 8 })
    if (path === '/api/digests/8') return pending8
    if (path === '/api/digest-runs' && options?.method === 'POST') return respond({ ...run, id: 2 })
    if (path === '/api/digest-runs/2') return respond({ ...run, id: 2, status: 'succeeded', digest_id: 9 })
    if (path === '/api/digests/9') return pending9
    throw Error(path)
  })
  render(<MemoryRouter><Home/></MemoryRouter>)
  await screen.findByRole('progressbar')
  await act(async () => { await vi.advanceTimersByTimeAsync(1000) })
  await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/digests/8', undefined))
  fireEvent.click(screen.getByRole('button', { name: 'Generate digest' }))
  await screen.findByRole('progressbar')
  await act(async () => { await vi.advanceTimersByTimeAsync(1000) })
  await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/digests/9', undefined))
  await act(async () => {
    release9(respond({ ...digest, id: 9, topics: [{ ...digest.topics[0], title: 'Newer edition' }] }))
    release8(respond({ error: { code: 'not_found', message: 'Missing 8' } }, 404))
    await Promise.all([pending9, pending8])
  })
  expect(screen.getByRole('heading', { name: 'Newer edition' })).toBeInTheDocument()
  expect(screen.queryByRole('alert')).toBeNull()
  expect(screen.queryByRole('link', { name: 'View digest' })).toBeNull()
})

it('requests only the latest digest, never the full history list', async () => {
  mockPage()
  await screen.findByRole('heading', { name: 'Generate digest' })
  expect(fetchMock).toHaveBeenCalledWith('/api/digests/latest', undefined)
  expect(fetchMock.mock.calls.some(([path]) => path === '/api/digests')).toBe(false)
})

it('waits for all four startup requests before showing the no-digest page', async () => {
  let release!: () => void
  const pending = new Promise<void>(resolve => { release = resolve })
  fetchMock.mockImplementation(async (path: string) => {
    if (path === '/api/settings/model') return respond({ key_set: true })
    if (path === '/api/sources') return respond(sources)
    if (path === '/api/digests/latest') return respond(null)
    if (path === '/api/digest-runs/active') { await pending; return respond(null) }
    throw Error(path)
  })
  render(<MemoryRouter><Home/></MemoryRouter>)
  expect(screen.getByRole('heading', { name: 'Loading…' })).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Generate digest' })).toBeNull()
  release()
  expect(await screen.findByRole('button', { name: 'Generate digest' })).toBeInTheDocument()
})
function mockPage(options: { ready?: boolean; run?: unknown; sources?: unknown[]; latest?: unknown; detail?: unknown } = {}) {
  fetchMock.mockImplementation(async (path: string) => {
    if (path === '/api/settings/model') return respond({ key_set: options.ready ?? true })
    if (path === '/api/sources') return respond(options.sources ?? sources)
    if (path === '/api/digests/latest') return respond(options.latest ?? null)
    if (path === '/api/digests/8' && options.detail) return respond(options.detail)
    if (path === '/api/digest-runs/active') return respond(options.run ?? null)
    throw Error(`Unexpected request ${path}`)
  })
  return render(<MemoryRouter><Home/></MemoryRouter>)
}

beforeEach(() => { vi.stubGlobal('fetch', fetchMock) })
afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); fetchMock.mockReset() })

it.each([['existing sources', sources], ['no sources (fresh install)', []]])(
  'puts model setup first with a visible disabled Generate and a state-aware rail: %s', async (_case, list) => {
  const { container } = mockPage({ ready: false, sources: list })
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
  const { container } = mockPage({ sources: [{ kind: 'feed' }] })
  await screen.findByText(/Check your 1 source and summarize/)
  expect(container.querySelectorAll('.btn-primary')).toHaveLength(1)
  expect(screen.getByRole('button', { name: 'Generate digest' })).toHaveClass('btn-primary')
  expect(screen.getByText(/Check your 1 source and summarize/)).toBeInTheDocument()
  await expectAccessible(container)
})

it('offers Add sources as the only primary action when the configured model has no sources', async () => {
  const { container } = mockPage({ ready: true, sources: [] })
  expect(await screen.findByRole('link', { name: 'Add sources' })).toHaveAttribute('href', '/sources')
  expect(screen.getByRole('link', { name: 'Add sources' })).toHaveClass('btn-primary')
  expect(container.querySelectorAll('.btn-primary')).toHaveLength(1)
  const generate = screen.getByRole('button', { name: 'Generate digest' })
  expect(generate).toBeDisabled()
  expect(generate).toHaveClass('btn-secondary')
  expect(generate).toHaveAccessibleDescription('Available once a source is added.')
})

it('does not show last-digest links in the no-digest guidance', async () => {
  const { container } = mockPage({ ready: true, sources: [] })
  await screen.findByRole('link', { name: 'Add sources' })
  expect(container.querySelector('.hero-last')).toBeNull()
  expect(screen.queryByRole('heading', { name: 'Last digest' })).toBeNull()
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

it('shows the saved digest with no primary action after success', async () => {
  const { container } = mockPage({ run: {
    ...run, status: 'succeeded', items_total: 12, items_done: 12, digest_id: 8,
    waiting_count: 2, deferred_count: 5, prompt_tokens: 12, completion_tokens: 4,
  }, detail: { ...digest, id: 8 } })
  const statusRegion = screen.getByRole('status')
  expect(await screen.findByRole('heading', { name: 'Technology' })).toBeInTheDocument()
  expect(screen.getByRole('status')).toBe(statusRegion)
  expect(screen.queryByRole('link', { name: 'View digest' })).toBeNull()
  expect(container.querySelectorAll('.btn-primary')).toHaveLength(0)
  expect(screen.getByRole('button', { name: 'Generate digest' })).toHaveClass('btn-secondary')
  expect(screen.getByText('2 items waiting for transcripts or captions')).toBeInTheDocument()
  expect(screen.getByText('5 videos deferred to the next run')).toBeInTheDocument()
  expect(screen.getByRole('status')).toHaveTextContent('Digest ready: 12 items')
  expect(screen.getByRole('region', { name: 'Digest run' })).toHaveTextContent('Tokens: 12 in / 4 out')
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
    if (path === '/api/digests/latest') return respond(null)
    if (path === '/api/digest-runs/active') return respond({ ...run, status: 'summarizing', items_total: 12, items_done: 5 })
    if (path === '/api/digest-runs/1') return respond({ ...run, status: 'succeeded',
      items_total: 12, items_done: 12, digest_id: 8 })
    if (path === '/api/digests/8') return respond({ ...digest, id: 8 })
    throw Error(path)
  })
  render(<MemoryRouter><Home/></MemoryRouter>)
  expect(await screen.findByRole('status')).toHaveTextContent('Summarizing, 5 of 12')
  const statusRegion = screen.getByRole('status')
  await act(async () => { await vi.advanceTimersByTimeAsync(1000) })
  expect(statusRegion).toBe(screen.getByRole('status'))
  expect(statusRegion).toHaveTextContent('Digest ready: 12 items')
  expect(await screen.findByRole('heading', { name: 'Technology' })).toBeInTheDocument()
  expect(screen.getByRole('status')).toBe(statusRegion)
  expect(document.title).toBe('Latest · No. 8 · CatchUp')
})

it('announces a polled run failure only through the persistent status region', async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true })
  fetchMock.mockImplementation(async (path: string) => {
    if (path === '/api/settings/model') return respond({ key_set: true })
    if (path === '/api/sources') return respond(sources)
    if (path === '/api/digests/latest') return respond(null)
    if (path === '/api/digest-runs/active') return respond(run)
    if (path === '/api/digest-runs/1') return respond({ ...run, status: 'failed',
      error_kind: 'provider_error', error_message: 'Provider is unavailable.' })
    throw Error(path)
  })
  render(<MemoryRouter><Home/></MemoryRouter>)
  await screen.findByRole('progressbar')
  await act(async () => { await vi.advanceTimersByTimeAsync(1000) })
  expect(screen.getByText('Provider is unavailable.')).toBeInTheDocument()
  expect(screen.queryByRole('alert')).toBeNull()
  expect(screen.getByRole('status')).toHaveTextContent('Digest generation failed: Provider is unavailable.')
})

it.each([
  [16, 14, 2, '16 items (14 summarized, 2 in Creator updates)'],
  [3, 3, 0, '3 items'],
  [2, 0, 2, '2 items in Creator updates'],
])('announces %i saved items (%i summarized, %i in Creator updates)', async (saved, summarized, updates, text) => {
  vi.useFakeTimers({ shouldAdvanceTime: true })
  fetchMock.mockImplementation(async (path: string) => {
    if (path === '/api/settings/model') return respond({ key_set: true })
    if (path === '/api/sources') return respond(sources)
    if (path === '/api/digests/latest') return respond(null)
    if (path === '/api/digest-runs/active') return respond({ ...run, status: 'summarizing',
      items_total: summarized, items_done: summarized })
    if (path === '/api/digest-runs/1') return respond({ ...run, status: 'succeeded',
      items_total: summarized, items_done: summarized, digest_id: 8, digest_item_count: saved,
      digest_update_count: updates })
    if (path === '/api/digests/8') return respond({ ...digest, id: 8 })
    throw Error(path)
  })
  const { container } = render(<MemoryRouter><Home/></MemoryRouter>)
  await screen.findByRole('progressbar')
  const statusRegion = screen.getByRole('status')
  await act(async () => { await vi.advanceTimersByTimeAsync(1000) })
  expect(screen.getByRole('status').textContent).toBe(`Digest ready: ${text}`)
  expect(await screen.findByRole('heading', { name: 'Technology' })).toBeInTheDocument()
  expect(screen.getByRole('status')).toBe(statusRegion)
  expect(container.querySelector('.run-bar .result-meta')?.textContent)
    .toContain(`${text} · 3 sources`)
})

it('keeps an active run visible when the latest digest fails to load', async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true })
  fetchMock.mockImplementation(async (path: string) => {
    if (path === '/api/settings/model') return respond({ key_set: true })
    if (path === '/api/sources') return respond(sources)
    if (path === '/api/digests/latest') return respond({ error: { code: 'request_failed', message: 'Latest unavailable' } }, 503)
    if (path === '/api/digest-runs/active') return respond({ ...run, status: 'summarizing',
      items_total: 12, items_done: 5 })
    if (path === '/api/digest-runs/1') return respond(run)
    throw Error(path)
  })
  const { container } = render(<MemoryRouter><Home/></MemoryRouter>)
  expect(await screen.findByRole('progressbar', { name: 'Items summarized: 5 of 12' })).toBeInTheDocument()
  expect(screen.getByRole('alert')).toHaveTextContent('Latest unavailable')
  expect(container.querySelectorAll('.btn-primary')).toHaveLength(1)
  expect(screen.getByRole('button', { name: 'Generating…' })).toBeDisabled()
})

it('keeps a startup latest-digest error visible through successful progress polls', async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true })
  fetchMock.mockImplementation(async (path: string) => {
    if (path === '/api/settings/model') return respond({ key_set: true })
    if (path === '/api/sources') return respond(sources)
    if (path === '/api/digests/latest') return respond({
      error: { code: 'request_failed', message: 'Latest unavailable' },
    }, 503)
    if (path === '/api/digest-runs/active' || path === '/api/digest-runs/1') {
      return respond({ ...run, status: 'summarizing', items_total: 12, items_done: 5 })
    }
    throw Error(path)
  })
  render(<MemoryRouter><Home/></MemoryRouter>)
  expect(await screen.findByRole('alert')).toHaveTextContent('Could not load the latest digest')
  await act(async () => { await vi.advanceTimersByTimeAsync(2000) })
  expect(fetchMock.mock.calls.filter(([path]) => path === '/api/digest-runs/1')).toHaveLength(2)
  expect(screen.getByRole('alert')).toHaveTextContent('Could not load the latest digest')
})

it('does not invent source counts when the source list cannot be read', async () => {
  fetchMock.mockImplementation(async (path: string) => {
    if (path === '/api/settings/model') return respond({ key_set: true })
    if (path === '/api/sources') return respond({
      error: { code: 'request_failed', message: 'Sources unavailable' },
    }, 503)
    if (path === '/api/digests/latest') return respond(null)
    if (path === '/api/digest-runs/active') return respond(null)
    throw Error(path)
  })
  const { container } = render(<MemoryRouter><Home/></MemoryRouter>)
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

it('starts one run and shows its saved article without requesting the list', async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true })
  fetchMock.mockImplementation(async (path: string, options?: RequestInit) => {
    if (path === '/api/settings/model') return respond({ key_set: true })
    if (path === '/api/sources') return respond(sources)
    if (path === '/api/digests/latest') return respond(null)
    if (path === '/api/digest-runs/active') return respond(null)
    if (path === '/api/digest-runs' && options?.method === 'POST') return respond(run)
    if (path === '/api/digest-runs/1') return respond({ ...run, status: 'succeeded',
      items_total: 12, items_done: 12, digest_id: 9 })
    if (path === '/api/digests/9') return respond({ ...digest, id: 9 })
    throw Error(path)
  })
  render(<MemoryRouter><Home/></MemoryRouter>)
  await waitFor(() => expect(screen.getByRole('button', { name: 'Generate digest' })).toBeEnabled())
  fireEvent.click(screen.getByRole('button', { name: 'Generate digest' }))
  expect(await screen.findByRole('progressbar', { name: 'Sources checked: 2 of 3' })).toBeInTheDocument()
  expect(fetchMock.mock.calls.filter(([path, options]) => path === '/api/digest-runs'
    && options?.method === 'POST')).toHaveLength(1)
  await act(async () => { await vi.advanceTimersByTimeAsync(1000) })
  await screen.findByText('New from sources you follow, listed without a summary because no transcript or captions were available.')
  expect(screen.getByRole('heading', { name: 'Technology' })).toBeInTheDocument()
  expect(document.title).toBe('Latest · No. 9 · CatchUp')
  expect(screen.queryByRole('link', { name: 'View digest' })).toBeNull()
  expect(fetchMock.mock.calls.some(([path]) => path === '/api/digests')).toBe(false)
})

it('switches to first-run after a model-not-configured POST', async () => {
  fetchMock.mockImplementation(async (path: string, options?: RequestInit) => {
    if (path === '/api/settings/model') return respond({ key_set: true })
    if (path === '/api/sources') return respond(sources)
    if (path === '/api/digests/latest') return respond(null)
    if (path === '/api/digest-runs/active') return respond(null)
    if (path === '/api/digest-runs' && options?.method === 'POST') {
      return respond({ error: { code: 'model_not_configured', message: 'Set up your model' } }, 400)
    }
    throw Error(path)
  })
  render(<MemoryRouter><Home/></MemoryRouter>)
  await waitFor(() => expect(screen.getByRole('button', { name: 'Generate digest' })).toBeEnabled())
  fireEvent.click(screen.getByRole('button', { name: 'Generate digest' }))
  expect((await screen.findAllByRole('link', { name: 'Set up your model' }))[0]).toHaveClass('btn-primary')
  expect(screen.getByRole('button', { name: 'Generate digest' })).toBeDisabled()
})

it('hides a failed run card when a retry reveals the model is not configured', async () => {
  fetchMock.mockImplementation(async (path: string, options?: RequestInit) => {
    if (path === '/api/settings/model') return respond({ key_set: true })
    if (path === '/api/sources') return respond(sources)
    if (path === '/api/digests/latest') return respond(null)
    if (path === '/api/digest-runs/active') return respond({
      ...run, status: 'failed', error_kind: 'provider_error', error_message: 'Provider unavailable.',
    })
    if (path === '/api/digest-runs' && options?.method === 'POST') return respond({
      error: { code: 'model_not_configured', message: 'Set up your model' },
    }, 400)
    throw Error(path)
  })
  const { container } = render(<MemoryRouter><Home/></MemoryRouter>)
  fireEvent.click(await screen.findByRole('button', { name: 'Try again' }))
  await waitFor(() => expect(screen.getByRole('button', { name: 'Generate digest' })).toBeDisabled())
  expect(screen.queryByText('Digest generation failed')).toBeNull()
  expect(container.querySelector('.result-card')).toBeNull()
  expect(container.querySelectorAll('.btn-primary')).toHaveLength(1)
  expect(screen.getAllByRole('link', { name: 'Set up your model' })[0]).toHaveClass('btn-primary')
})

it('hides a completed run line in the bar when the model becomes unconfigured', async () => {
  fetchMock.mockImplementation(async (path: string, options?: RequestInit) => {
    if (path === '/api/settings/model') return respond({ key_set: true })
    if (path === '/api/sources') return respond(sources)
    if (path === '/api/digests/latest') return respond(digest)
    if (path === '/api/digest-runs/active') return respond({ ...run, status: 'succeeded', digest_id: 4 })
    if (path === '/api/digest-runs' && options?.method === 'POST') return respond({
      error: { code: 'model_not_configured', message: 'Set up your model' },
    }, 400)
    throw Error(path)
  })
  render(<MemoryRouter><Home/></MemoryRouter>)
  fireEvent.click(await screen.findByRole('button', { name: 'Generate digest' }))
  await waitFor(() => expect(screen.getByRole('button', { name: 'Generate digest' })).toBeDisabled())
  expect(screen.getByRole('region', { name: 'Digest run' }).querySelector('.result-meta')).toBeNull()
  expect(screen.getByRole('heading', { name: 'Technology' })).toBeInTheDocument()
})

it.each([null, digest])('keeps running progress in first run with digest %s', async latest => {
  const { container } = mockPage({ ready: false, latest, run })
  expect(await screen.findByRole('progressbar', { name: 'Sources checked: 2 of 3' })).toBeInTheDocument()
  expect(container.querySelectorAll('.btn-primary')).toHaveLength(1)
})

it('uses action-specific alerts when starting or checking a run fails', async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true })
  let started = false
  fetchMock.mockImplementation(async (path: string, options?: RequestInit) => {
    if (path === '/api/settings/model') return respond({ key_set: true })
    if (path === '/api/sources') return respond(sources)
    if (path === '/api/digests/latest') return respond(null)
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
  render(<MemoryRouter><Home/></MemoryRouter>)
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
    if (path === '/api/digests/latest') return respond(null)
    if (path === '/api/digest-runs/active') return respond(++activeReads === 1 ? null : run)
    if (path === '/api/digest-runs') return respond({ error: { code: 'run_active', message: 'Already active' } }, 409)
    if (path === '/api/digest-runs/1') return respond(run)
    throw Error(path)
  })
  render(<MemoryRouter><Home/></MemoryRouter>)
  await waitFor(() => expect(screen.getByRole('button', { name: 'Generate digest' })).toBeEnabled())
  fireEvent.click(screen.getByRole('button', { name: 'Generate digest' }))
  expect(await screen.findByRole('progressbar', { name: 'Sources checked: 2 of 3' })).toBeInTheDocument()
  expect(fetchMock.mock.calls.filter(([path, options]) => path === '/api/digest-runs'
    && options?.method === 'POST')).toHaveLength(1)
})
