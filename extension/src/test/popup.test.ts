import { fireEvent, screen, waitFor } from '@testing-library/dom'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { axe } from 'vitest-axe'
import { initPopup } from '../popup'

const fetchMock = vi.fn()
const openOptionsPage = vi.fn()
const chromeMock = {
  storage: { local: { get: vi.fn(async () => ({})), set: vi.fn() } },
  tabs: { query: vi.fn(async () => [{ id: 1, url: 'https://site.example/post', title: 'A post' }]),
    create: vi.fn() },
  scripting: { executeScript: vi.fn() },
  runtime: { openOptionsPage },
}

beforeEach(() => {
  document.body.innerHTML = '<main><h1>CatchUp</h1><div id="popup"></div></main>'
  chromeMock.storage.local.get.mockResolvedValue({})
  chromeMock.tabs.query.mockResolvedValue([{ id: 1, url: 'https://site.example/post', title: 'A post' }])
  vi.stubGlobal('chrome', chromeMock)
  vi.stubGlobal('fetch', fetchMock)
})
afterEach(() => { vi.unstubAllGlobals(); fetchMock.mockReset(); vi.clearAllMocks() })
const response = (status: number, body: object) =>
  ({ ok: status >= 200 && status < 300, status, json: async () => body })
const connect = () => {
  chromeMock.storage.local.get.mockResolvedValue({
    server: 'http://127.0.0.1:8000', token: 'fake-browser-token',
  })
  fetchMock.mockResolvedValue(response(200, { name: 'My browser', waiting: 3 }))
}
const preview = {
  title: 'Example Site', kind: 'rss', feed_url: 'https://site.example/feed',
  site_url: 'https://site.example', follows_site_feed_notice: true,
  entries: [{ title: 'Latest', link: 'https://site.example/latest', published_at: null }],
}

it('sends nothing before a browser is connected and links to options', async () => {
  initPopup()
  await waitFor(() => expect(screen.getByText(/Connect this browser in CatchUp/)).toBeInTheDocument())
  expect(screen.getByRole('button', { name: /options/i })).toBeInTheDocument()
  expect(fetchMock).not.toHaveBeenCalled()
  expect(chromeMock.scripting.executeScript).not.toHaveBeenCalled()
  expect((await axe(document.body, { rules: { 'color-contrast': { enabled: false } } })).violations).toEqual([])
})

it('shows the tab and waiting count, and opens the configured local server', async () => {
  connect()
  initPopup()
  await waitFor(() => expect(screen.getByText(/3 pages waiting/)).toBeInTheDocument())
  expect(screen.getByText(/A post/)).toBeInTheDocument()
  expect(screen.getByText(/site\.example/)).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Open CatchUp' }))
  expect(chromeMock.tabs.create).toHaveBeenCalledWith({ url: 'http://127.0.0.1:8000' })
  expect(await axe(document.body, { rules: { 'color-contrast': { enabled: false } } }).then(r => r.violations)).toEqual([])
})

it('previews a site, cancels without posting, then confirms only its feed URL', async () => {
  connect()
  fetchMock.mockImplementation(async (url: string) => url.endsWith('/preview') ? response(200, preview)
    : url.endsWith('/sources') ? response(201, { id: 12 }) : response(200, { name: 'My browser', waiting: 3 }))
  initPopup()
  fireEvent.click(await screen.findByRole('button', { name: 'Follow this site' }))
  await screen.findByText('Latest')
  expect(screen.getByText('Example Site')).toBeInTheDocument()
  expect(screen.getByText('rss')).toBeInTheDocument()
  expect(screen.getByText('https://site.example/feed')).toBeInTheDocument()
  expect(screen.getByText(/whole site's feed/)).toBeInTheDocument()
  expect(fetchMock).toHaveBeenCalledWith('http://127.0.0.1:8000/api/sources/preview',
    expect.objectContaining({
      method: 'POST', headers: expect.objectContaining({ Authorization: 'Bearer fake-browser-token' }),
      body: JSON.stringify({ url: 'https://site.example/post' }),
    }))
  fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
  expect(fetchMock.mock.calls.filter(([url]) => String(url).endsWith('/api/sources'))).toHaveLength(0)
  fireEvent.click(screen.getByRole('button', { name: 'Follow this site' }))
  fireEvent.click(await screen.findByRole('button', { name: 'Confirm' }))
  await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('http://127.0.0.1:8000/api/sources',
    expect.objectContaining({ method: 'POST', body: JSON.stringify({ feed_url: preview.feed_url }) })))
  expect(await axe(document.body, { rules: { 'color-contrast': { enabled: false } } }).then(r => r.violations)).toEqual([])
})

it.each([
  ['duplicate', null, 'Already following this feed.', 'Already following this feed.'],
  ['no_feed', null, 'Backend text', 'No supported feed was found at this URL.'],
  ['fetch_failed', 403, 'Backend text', 'The site refused the request (HTTP 403). If you know its feed URL, paste that instead.'],
  ['fetch_failed', 404, 'Backend text', "The page was not found (HTTP 404). Check the URL, or paste the site's feed URL."],
  ['fetch_failed', 503, 'Backend text', 'The site is not responding (HTTP 503). Try again later.'],
  ['fetch_failed', 418, 'Backend text', "The site answered HTTP 418. Check the URL, or paste the site's feed URL."],
  ['fetch_failed', null, 'Backend text', 'Could not fetch the source. Check the URL and try again.'],
])('maps %s error (HTTP %s)', async (code, http_status, message, expected) => {
  connect()
  fetchMock.mockImplementation(async (url: string) => url.endsWith('/preview')
    ? response(400, { error: { code, message, http_status } })
    : response(200, { name: 'My browser', waiting: 3 }))
  initPopup()
  fireEvent.click(await screen.findByRole('button', { name: 'Follow this site' }))
  await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent(expected))
})

it('treats a revoked token as disconnected and does not make other requests', async () => {
  connect()
  fetchMock.mockResolvedValue(response(401, { error: { code: 'invalid_token', message: 'Not connected' } }))
  initPopup()
  await screen.findByText(/Connect this browser in CatchUp/)
  expect(fetchMock).toHaveBeenCalledTimes(1)
  expect(await axe(document.body, { rules: { 'color-contrast': { enabled: false } } }).then(r => r.violations)).toEqual([])
})

it('does not offer Follow this site or preview on X tabs', async () => {
  connect()
  chromeMock.tabs.query.mockResolvedValue([{ id: 1, url: 'https://x.com/someone', title: 'Someone on X' }])
  initPopup()
  await screen.findByText(/cannot be followed/i)
  expect(screen.queryByRole('button', { name: 'Follow this site' })).not.toBeInTheDocument()
  expect(fetchMock).toHaveBeenCalledTimes(1)
  expect(await axe(document.body, { rules: { 'color-contrast': { enabled: false } } }).then(r => r.violations)).toEqual([])
})
