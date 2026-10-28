import { fireEvent, screen, waitFor } from '@testing-library/dom'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { axe } from 'vitest-axe'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { JSDOM } from 'jsdom'
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
  title: 'Example Site', kind: 'feed', feed_url: 'https://site.example/feed',
  site_url: 'https://site.example', follows_site_feed_notice: true,
  entries: [{ title: 'Latest', link: 'https://site.example/latest', published_at: null }],
}
const xPreview = {
  ...preview, title: 'Sample Writer', kind: 'x', feed_url: 'x:user:123',
  site_url: 'https://x.com/writer', username: 'writer',
  follows_site_feed_notice: false,
}
const captured = {
  url: 'https://site.example/post', title: 'A post', site_name: 'Example Site',
  author: 'Sam', published_at: null, content_text: 'The page text.',
  images: [{ url: 'https://site.example/image.png', alt: 'Photo' }],
  links: [{ url: 'https://site.example/more', text: 'Read more' }], replies: [],
}
const genericResult = (page: unknown) => {
  chromeMock.scripting.executeScript.mockImplementation(async (details: { files?: string[]; func?: () => unknown }) =>
    details.files ? [] : [{ result: details.func?.name === 'extractReadable' ? null : page }])
}
const saves = () => fetchMock.mock.calls.filter(([url]) => String(url).endsWith('/api/captures'))

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
  expect(screen.getByText('Website feed')).toBeInTheDocument()
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
  ['podcast', 'Podcast'], ['youtube', 'YouTube channel'],
])('labels a %s preview as %s', async (kind, label) => {
  connect()
  fetchMock.mockImplementation(async (url: string) => url.endsWith('/preview')
    ? response(200, { ...preview, kind })
    : response(200, { name: 'My browser', waiting: 3 }))
  initPopup()
  fireEvent.click(await screen.findByRole('button', { name: 'Follow this site' }))
  await screen.findByText(label)
  expect((await axe(document.body, { rules: { 'color-contrast': { enabled: false } } })).violations).toEqual([])
})

it.each([1, 2])('shows the correct waiting-page wording for %i', async waiting => {
  connect()
  fetchMock.mockResolvedValue(response(200, { name: 'My browser', waiting }))
  initPopup()
  expect(await screen.findByText(`${waiting} ${waiting === 1 ? 'page' : 'pages'} waiting`)).toBeInTheDocument()
  expect((await axe(document.body, { rules: { 'color-contrast': { enabled: false } } })).violations).toEqual([])
})

it.each(
  ['Add this page to my next digest', 'Follow this site', 'Confirm', 'Remove']
    .flatMap(action => ['rejected fetch', 'non-JSON 502'].map(failure => [action, failure])),
)('reports %s failure (%s) after connecting', async (action, failure) => {
  connect()
  genericResult(captured)
  fetchMock.mockImplementation(async (url: string, init?: RequestInit) => {
    if (url.endsWith('/status')) return response(200, { name: 'My browser', waiting: 3 })
    if (action === 'Confirm' && url.endsWith('/preview')) return response(200, preview)
    if (action === 'Remove' && url.endsWith('/captures') && init?.method === 'POST')
      return response(201, { id: 42, waiting: 4 })
    if (failure === 'rejected fetch') throw new Error('Failed to fetch')
    return { ok: false, status: 502, json: async () => { throw new SyntaxError('Unexpected HTML') } }
  })
  initPopup()
  if (action === 'Confirm') {
    fireEvent.click(await screen.findByRole('button', { name: 'Follow this site' }))
    await screen.findByText('Latest')
  }
  if (action === 'Remove') {
    fireEvent.click(await screen.findByRole('button', { name: 'Add this page to my next digest' }))
    await screen.findByText('Saved. It will be in your next digest.')
  }
  fireEvent.click(await screen.findByRole('button', { name: action }))
  await waitFor(() => expect(screen.getByRole('status'))
    .toHaveTextContent('Could not connect to CatchUp.'))
  expect((await axe(document.body, { rules: { 'color-contrast': { enabled: false } } })).violations).toEqual([])
  },
)

it.each(['popup', 'options'])('links the styled %s page', page => {
  const html = readFileSync(resolve(`${page}.html`), 'utf8')
  const css = readFileSync(resolve(`src/${page}.css`), 'utf8')
  expect(html).toContain(`href="/src/${page}.css"`)
  expect(css).toContain('frontend/src/styles/tokens.css')
  expect(css).toContain('prefers-color-scheme: dark')
  expect(css).toContain('var(--fg)')
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
  expect((await axe(document.body, { rules: { 'color-contrast': { enabled: false } } })).violations).toEqual([])
})

it('treats a revoked token as disconnected and does not make other requests', async () => {
  connect()
  fetchMock.mockResolvedValue(response(401, { error: { code: 'invalid_token', message: 'Not connected' } }))
  initPopup()
  await screen.findByText(/Connect this browser in CatchUp/)
  expect(fetchMock).toHaveBeenCalledTimes(1)
  expect(await axe(document.body, { rules: { 'color-contrast': { enabled: false } } }).then(r => r.violations)).toEqual([])
})

it('offers Follow this account alongside Add on an X profile', async () => {
  connect()
  chromeMock.tabs.query.mockResolvedValue([{ id: 1, url: 'https://x.com/writer', title: 'Someone on X' }])
  fetchMock.mockImplementation(async (url: string) => url.endsWith('/preview')
    ? response(200, xPreview)
    : url.endsWith('/sources') ? response(201, { id: 8 })
      : response(200, { name: 'My browser', waiting: 3 }))
  initPopup()
  fireEvent.click(await screen.findByRole('button', { name: 'Follow this account' }))
  const section = await screen.findByRole('region', { name: 'Source preview' })
  expect(section).toHaveTextContent('X account')
  expect(section).toHaveTextContent('@writer')
  expect(section).toHaveTextContent('https://x.com/writer')
  expect(section).not.toHaveTextContent('x:user:')
  expect(fetchMock).toHaveBeenCalledWith('http://127.0.0.1:8000/api/sources/preview',
    expect.objectContaining({ method: 'POST', body: JSON.stringify({ url: 'https://x.com/writer' }) }))
  fireEvent.click(screen.getByRole('button', { name: 'Confirm' }))
  await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
    'http://127.0.0.1:8000/api/sources',
    expect.objectContaining({ method: 'POST', body: JSON.stringify({ feed_url: 'x:user:123' }) }),
  ))
  expect(screen.queryByText(/cannot be followed/i)).toBeNull()
  expect(await screen.findByRole('button', { name: 'Add this page to my next digest' })).toBeInTheDocument()
  expect(await axe(document.body, { rules: { 'color-contrast': { enabled: false } } }).then(r => r.violations)).toEqual([])
})

it('injects the generic extractor and saves a checked page, then removes it', async () => {
  connect()
  genericResult(captured)
  fetchMock.mockImplementation(async (url: string, init?: RequestInit) => url.endsWith('/captures')
    ? init?.method === 'DELETE' ? { ok: true, status: 204 } : response(201, { id: 42, waiting: 4 })
    : response(200, { name: 'My browser', waiting: 3 }))
  initPopup()
  fireEvent.click(await screen.findByRole('button', { name: 'Add this page to my next digest' }))
  await screen.findByText('Saved. It will be in your next digest.')
  expect(chromeMock.scripting.executeScript).toHaveBeenCalledWith({
    target: { tabId: 1 }, func: expect.any(Function),
  })
  expect(chromeMock.scripting.executeScript.mock.calls.map(([details]) =>
    details.files ? 'readability.js' : details.func.name))
    .toEqual(['readability.js', 'extractReadable', 'extractGeneric'])
  expect(fetchMock).toHaveBeenCalledWith('http://127.0.0.1:8000/api/captures',
    expect.objectContaining({
      method: 'POST', headers: expect.objectContaining({ Authorization: 'Bearer fake-browser-token' }),
      body: JSON.stringify({
        url: captured.url, title: captured.title, text: captured.content_text,
        site_name: captured.site_name, author: captured.author, published_at: captured.published_at,
        images: captured.images, links: captured.links, replies: [],
      }),
    }))
  expect(screen.getByText(/4 pages waiting/)).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Remove' }))
  await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
    'http://127.0.0.1:8000/api/captures/42',
    expect.objectContaining({ method: 'DELETE', headers: { Authorization: 'Bearer fake-browser-token' } }),
  ))
  await waitFor(() => expect(screen.getByText(/3 pages waiting/)).toBeInTheDocument())
  expect(await axe(document.body, { rules: { 'color-contrast': { enabled: false } } }).then(r => r.violations)).toEqual([])
})

it.each(['reject', 'empty', 'missing'])('does not save an unreadable tab (%s)', async outcome => {
  connect()
  chromeMock.scripting.executeScript.mockImplementation(async () => {
    if (outcome === 'reject') throw new Error('Cannot inject')
    return outcome === 'empty' ? [] : [{}]
  })
  initPopup()
  fireEvent.click(await screen.findByRole('button', { name: 'Add this page to my next digest' }))
  await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent("This page can't be read by extensions."))
  expect(saves()).toHaveLength(0)
  expect((await axe(document.body, { rules: { 'color-contrast': { enabled: false } } })).violations).toEqual([])
})

it('disables Add while saving and shows a run_active conflict', async () => {
  connect()
  genericResult(captured)
  let complete!: (value: unknown) => void
  fetchMock.mockImplementation((url: string) => url.endsWith('/captures')
    ? new Promise(resolve => { complete = resolve })
    : Promise.resolve(response(200, { name: 'My browser', waiting: 3 })))
  initPopup()
  const add = await screen.findByRole('button', { name: 'Add this page to my next digest' })
  fireEvent.click(add)
  await waitFor(() => expect(saves()).toHaveLength(1))
  expect(add).toBeDisabled()
  fireEvent.click(add)
  expect(saves()).toHaveLength(1)
  complete(response(409, { error: { code: 'run_active', message: 'A digest is being made.' } }))
  await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('A digest is being made.'))
  expect(add).toBeEnabled()
  expect((await axe(document.body, { rules: { 'color-contrast': { enabled: false } } })).violations).toEqual([])
})

it('still saves an X profile as a generic page when Add is chosen', async () => {
  connect()
  chromeMock.tabs.query.mockResolvedValue([{ id: 8, url: 'https://x.com/someone', title: 'Someone' }])
  genericResult({ ...captured, url: 'https://x.com/someone' })
  fetchMock.mockImplementation(async (url: string) => url.endsWith('/captures')
    ? response(201, { id: 43, waiting: 4 })
    : response(200, { name: 'My browser', waiting: 3 }))
  initPopup()
  await screen.findByRole('button', { name: 'Follow this account' })
  fireEvent.click(screen.getByRole('button', { name: 'Add this page to my next digest' }))
  await screen.findByText('Saved. It will be in your next digest.')
  expect(chromeMock.scripting.executeScript).toHaveBeenCalledWith({
    target: { tabId: 8 }, func: expect.any(Function),
  })
  expect(chromeMock.scripting.executeScript.mock.calls.map(([details]) =>
    details.files ? 'readability.js' : details.func.name))
    .toEqual(['readability.js', 'extractReadable', 'extractGeneric'])
  expect(saves()).toHaveLength(1)
  expect((await axe(document.body, { rules: { 'color-contrast': { enabled: false } } })).violations).toEqual([])
})

it.each(['https://x.com/writer/status/1', 'https://x.com./writer/status/1'])(
  'offers Follow on post page %s but keeps Add using the X extractor', async url => {
  connect()
  chromeMock.tabs.query.mockResolvedValue([{ id: 9, url, title: 'Post' }])
  chromeMock.scripting.executeScript.mockResolvedValue([{ result: {
    ...captured, url,
  } }])
  fetchMock.mockImplementation(async (url: string) => url.endsWith('/captures')
    ? response(201, { id: 46, waiting: 4 })
    : response(200, { name: 'My browser', waiting: 3 }))
  initPopup()
  await screen.findByRole('button', { name: 'Follow this account' })
  fireEvent.click(screen.getByRole('button', { name: 'Add this page to my next digest' }))
  await screen.findByText('Saved. It will be in your next digest.')
  expect(chromeMock.scripting.executeScript.mock.calls[0][0].func.name).toBe('extractX')
})

it('only offers Add on X home pages', async () => {
  connect()
  chromeMock.tabs.query.mockResolvedValue([{ id: 10, url: 'https://x.com/home', title: 'Home' }])
  initPopup()
  await screen.findByRole('button', { name: 'Add this page to my next digest' })
  expect(screen.queryByRole('button', { name: /Follow/ })).toBeNull()
  expect(screen.queryByText(/cannot be followed/i)).toBeNull()
  expect((await axe(document.body, { rules: { 'color-contrast': { enabled: false } } })).violations).toEqual([])
})

it('offers only Add on a help.x.com page', async () => {
  connect()
  chromeMock.tabs.query.mockResolvedValue([{ id: 8, url: 'https://help.x.com/en', title: 'Help' }])
  initPopup()
  await screen.findByRole('button', { name: 'Add this page to my next digest' })
  expect(screen.queryByRole('button', { name: /Follow/ })).toBeNull()
})

it.each([
  ['https://x.com./simonw', 'Follow this account'],
  ['https://help.x.com./en', null],
])('recognizes a trailing-dot X host on %s', async (url, follow) => {
  connect()
  chromeMock.tabs.query.mockResolvedValue([{ id: 8, url, title: 'X tab' }])
  initPopup()
  await screen.findByRole('button', { name: 'Add this page to my next digest' })
  if (follow) expect(screen.getByRole('button', { name: follow })).toBeInTheDocument()
  else expect(screen.queryByRole('button', { name: /Follow/ })).toBeNull()
})

it.each(['https://notx.com/simonw', 'https://x.com.example.org/simonw'])(
  'offers Follow this site for look-alike host %s', async url => {
    connect()
    chromeMock.tabs.query.mockResolvedValue([{ id: 8, url, title: 'Other site' }])
    initPopup()
    await screen.findByRole('button', { name: 'Add this page to my next digest' })
    expect(screen.getByRole('button', { name: 'Follow this site' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Follow this account' })).toBeNull()
  })

it('uses generic page extraction for a help.x.com URL that looks like a post', async () => {
  connect()
  chromeMock.tabs.query.mockResolvedValue([{ id: 8, url: 'https://help.x.com/a/status/1', title: 'Help' }])
  genericResult({ ...captured, url: 'https://help.x.com/a/status/1' })
  fetchMock.mockImplementation(async (url: string) => url.endsWith('/captures')
    ? response(201, { id: 50, waiting: 4 })
    : response(200, { name: 'My browser', waiting: 3 }))
  initPopup()
  fireEvent.click(await screen.findByRole('button', { name: 'Add this page to my next digest' }))
  await screen.findByText('Saved. It will be in your next digest.')
  expect(chromeMock.scripting.executeScript.mock.calls.map(([details]) =>
    details.files ? 'readability.js' : details.func.name))
    .toEqual(['readability.js', 'extractReadable', 'extractGeneric'])
})

it.each([
  ['https://twitter.com/Writer/status/123', true],
  ['https://www.x.com/Writer', true],
  ['https://mobile.twitter.com/Writer', true],
  ['https://x.com/i/flow/login', false],
  ['https://x.com/HOME', false],
  ['https://x.com/1234567890123456', false],
  ['https://x.com/a-b', false],
])('matches backend X username recognition for %s', async (url, follows) => {
  connect()
  chromeMock.tabs.query.mockResolvedValue([{ id: 3, url, title: 'X tab' }])
  initPopup()
  await screen.findByRole('button', { name: 'Add this page to my next digest' })
  expect(Boolean(screen.queryByRole('button', { name: 'Follow this account' }))).toBe(follows)
  expect(screen.queryByRole('button', { name: 'Follow this site' })).toBeNull()
})

it('asks for an X API token, saves it through the API, and retries the preview without browser storage', async () => {
  connect()
  chromeMock.tabs.query.mockResolvedValue([{ id: 1, url: 'https://x.com/writer', title: 'Writer' }])
  let tokenSaved = false
  fetchMock.mockImplementation(async (url: string, init?: RequestInit) => {
    if (url.endsWith('/preview')) return tokenSaved ? response(200, xPreview)
      : response(422, { error: { code: 'x_token_required', message: 'X token needed.' } })
    if (url.endsWith('/settings/x')) {
      tokenSaved = true
      return response(200, { token_set: true, token_last4: 'xxxx' })
    }
    return response(200, { name: 'My browser', waiting: 3 })
  })
  initPopup()
  fireEvent.click(await screen.findByRole('button', { name: 'Follow this account' }))
  const field = await screen.findByLabelText('X API token')
  expect(field).toHaveAttribute('type', 'password')
  // The x_token_required wording is shared with describeError in frontend/src/pages/Sources.tsx.
  expect(screen.getByRole('status').textContent).toBe('X token needed.')
  expect(screen.getByText('Copy the Bearer token of your X App from console.x.com.')).toBeInTheDocument()
  expect(field).toHaveAccessibleDescription('Copy the Bearer token of your X App from console.x.com.')
  expect((await axe(document.body, { rules: { 'color-contrast': { enabled: false } } })).violations).toEqual([])
  fireEvent.input(field, { target: { value: 'invented-x-token' } })
  fireEvent.click(screen.getByRole('button', { name: 'Save' }))
  await screen.findByText('@writer')
  expect(fetchMock).toHaveBeenCalledWith('http://127.0.0.1:8000/api/settings/x',
    expect.objectContaining({
      method: 'PUT', body: JSON.stringify({ token: 'invented-x-token' }),
      headers: expect.objectContaining({ Authorization: 'Bearer fake-browser-token' }),
    }))
  expect(fetchMock.mock.calls.filter(([url]) => String(url).endsWith('/preview'))).toHaveLength(2)
  expect(chromeMock.storage.local.set).not.toHaveBeenCalled()
})

it.each([
  ['x_token_exists', 'save', 'Replace the X token in CatchUp Settings.'],
  ['x_token_rejected', 'preview', 'X rejected the token. Replace the X token in CatchUp Settings.'],
])('directs %s to CatchUp Settings and offers Open CatchUp', async (code, stage, wording) => {
  connect()
  chromeMock.tabs.query.mockResolvedValue([{ id: 1, url: 'https://x.com/writer', title: 'Writer' }])
  fetchMock.mockImplementation(async (url: string) => url.endsWith('/preview')
    ? response(422, { error: { code: stage === 'save' ? 'x_token_required' : code, message: 'No token' } })
    : url.endsWith('/settings/x') ? response(409, { error: { code, message: 'Replace in settings' } })
      : response(200, { name: 'My browser', waiting: 3 }))
  initPopup()
  fireEvent.click(await screen.findByRole('button', { name: 'Follow this account' }))
  if (stage === 'save') {
    fireEvent.input(await screen.findByLabelText('X API token'),
      { target: { value: 'invented-x-token' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
  }
  await waitFor(() => expect(screen.getByRole('status').textContent).toBe(wording))
  fireEvent.click(screen.getByRole('button', { name: 'Open CatchUp' }))
  expect(chromeMock.tabs.create).toHaveBeenCalledWith({ url: 'http://127.0.0.1:8000' })
  expect((await axe(document.body, { rules: { 'color-contrast': { enabled: false } } })).violations).toEqual([])
})

// These strings mirror describeError in frontend/src/pages/Sources.tsx.
it.each([
  ['x_token_rejected', 'X rejected the token. Replace the X token in CatchUp Settings.'],
  ['x_account_protected', 'Protected X accounts cannot be followed.'],
  ['x_account_not_found', 'X account not found.'],
  ['x_account_suspended', 'X account suspended.'],
  ['not_an_x_account', 'This is not an X account address.'],
  ['rate_limited', 'Rate limited — try again later (about 60 seconds).'],
])('shows the Sources wording for %s', async (code, expected) => {
  connect()
  chromeMock.tabs.query.mockResolvedValue([{ id: 1, url: 'https://x.com/writer', title: 'Writer' }])
  fetchMock.mockImplementation(async (url: string) => url.endsWith('/preview')
    ? response(422, { error: { code, message: 'Backend message', retry_after: 60 } })
    : response(200, { name: 'My browser', waiting: 3 }))
  initPopup()
  fireEvent.click(await screen.findByRole('button', { name: 'Follow this account' }))
  await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent(expected))
  expect((await axe(document.body, { rules: { 'color-contrast': { enabled: false } } })).violations).toEqual([])
})

it('rejects wrong result types and clamps long text, images and links before posting', async () => {
  connect()
  genericResult({ ...captured, images: 'wrong type' })
  initPopup()
  const add = await screen.findByRole('button', { name: 'Add this page to my next digest' })
  fireEvent.click(add)
  await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent("This page can't be read by extensions."))
  expect(saves()).toHaveLength(0)
  fetchMock.mockImplementation(async (url: string) => url.endsWith('/captures')
    ? response(201, { id: 44, waiting: 4 })
    : response(200, { name: 'My browser', waiting: 3 }))
  genericResult({
    ...captured, title: 'T'.repeat(400), content_text: 'C'.repeat(17000),
    images: Array.from({ length: 12 }, () => captured.images[0]),
    links: Array.from({ length: 60 }, () => captured.links[0]),
    replies: Array.from({ length: 15 }, () => 'R'.repeat(500)),
  })
  fireEvent.click(add)
  await waitFor(() => expect(saves()).toHaveLength(1))
  const body = JSON.parse(String((saves()[0][1] as RequestInit).body))
  expect(body.title).toHaveLength(300)
  expect(body.text).toHaveLength(16000)
  expect(body.images).toHaveLength(8)
  expect(body.links).toHaveLength(50)
  expect(body.replies.length).toBeLessThanOrEqual(10)
  expect(body.replies.join('\n\n').length).toBeLessThanOrEqual(4000)
})

it.each(['x.com', 'twitter.com'])('uses the X extractor for a %s post URL', async host => {
  connect()
  chromeMock.tabs.query.mockResolvedValue([{
    id: 9, url: `https://${host}/alice/status/123`, title: 'Alice on X',
  }])
  chromeMock.scripting.executeScript.mockResolvedValue([{ result: {
    ...captured, url: `https://${host}/alice/status/123`, replies: ['Author reply'],
  } }])
  fetchMock.mockImplementation(async (url: string) => url.endsWith('/captures')
    ? response(201, { id: 46, waiting: 4 })
    : response(200, { name: 'My browser', waiting: 3 }))
  initPopup()
  fireEvent.click(await screen.findByRole('button', { name: 'Add this page to my next digest' }))
  await screen.findByText('Saved. It will be in your next digest.')
  expect(chromeMock.scripting.executeScript.mock.calls[0][0].func.name).toBe('extractX')
  expect(JSON.parse(String((saves()[0][1] as RequestInit).body)).replies).toEqual(['Author reply'])
})

it('falls back to generic after the X extractor returns null', async () => {
  connect()
  chromeMock.tabs.query.mockResolvedValue([{ id: 10, url: 'https://x.com/alice/status/123', title: 'Alice on X' }])
  chromeMock.scripting.executeScript.mockResolvedValueOnce([{ result: null }])
    .mockResolvedValueOnce([{ result: captured }])
  fetchMock.mockImplementation(async (url: string) => url.endsWith('/captures')
    ? response(201, { id: 47, waiting: 4 })
    : response(200, { name: 'My browser', waiting: 3 }))
  initPopup()
  fireEvent.click(await screen.findByRole('button', { name: 'Add this page to my next digest' }))
  await screen.findByText('Saved. It will be in your next digest.')
  expect(chromeMock.scripting.executeScript.mock.calls.map(([details]) => details.func.name))
    .toEqual(['extractX', 'extractGeneric'])
  expect(saves()).toHaveLength(1)
})

it('saves only reader-view post content on a page without an article element', async () => {
  connect()
  const tab = new JSDOM(
    readFileSync(resolve('src/extract/fixtures/blog-no-article.html'), 'utf8'),
    { url: 'https://garden.example/post', runScripts: 'outside-only' },
  )
  const original = tab.window.document.body.outerHTML
  const library = readFileSync(resolve('node_modules/@mozilla/readability/Readability.js'), 'utf8')
  chromeMock.scripting.executeScript.mockImplementation(async (details: {
    files?: string[]; func?: () => unknown;
  }) => {
    if (details.files) {
      expect(details.files).toEqual(['readability.js'])
      tab.window.eval(library)
      return []
    }
    return [{ result: tab.window.eval(`(${details.func!.toString()})()`) }]
  })
  fetchMock.mockImplementation(async (url: string) => url.endsWith('/captures')
    ? response(201, { id: 48, waiting: 4 })
    : response(200, { name: 'My browser', waiting: 3 }))
  try {
    initPopup()
    fireEvent.click(await screen.findByRole('button', { name: 'Add this page to my next digest' }))
    await screen.findByText('Saved. It will be in your next digest.')
    const body = JSON.parse(String((saves()[0][1] as RequestInit).body))
    expect(body.text).toContain('Tiny gardens thrive')
    expect(body.text).not.toMatch(/Recent articles|Unrelated recent story|Sponsored|Archive 2023/)
    expect(body.links).toEqual([{ url: 'https://garden.example/soil-guide', text: 'the soil guide' }])
    expect(body.images).toEqual([{ url: 'https://garden.example/pot.png', alt: 'A garden pot' }])
    expect(chromeMock.scripting.executeScript.mock.calls.map(([details]) =>
      details.files ? 'readability.js' : details.func.name)).toEqual(['readability.js', 'extractReadable'])
    expect(tab.window.document.body.outerHTML).toBe(original)
  } finally {
    tab.window.close()
  }
})

it.each(['https://garden.example/post', 'https://x.com/someone'])(
  'falls back to generic after Readability returns null for %s', async url => {
    connect()
    chromeMock.tabs.query.mockResolvedValue([{ id: 8, url, title: 'A page' }])
    chromeMock.scripting.executeScript.mockImplementation(async (details: { files?: string[]; func?: () => unknown }) =>
      details.files ? [] : [{ result: details.func?.name === 'extractReadable' ? null : captured }])
    fetchMock.mockImplementation(async (path: string) => path.endsWith('/captures')
      ? response(201, { id: 49, waiting: 4 })
      : response(200, { name: 'My browser', waiting: 3 }))
    initPopup()
    fireEvent.click(await screen.findByRole('button', { name: 'Add this page to my next digest' }))
    await screen.findByText('Saved. It will be in your next digest.')
    expect(chromeMock.scripting.executeScript.mock.calls.map(([details]) =>
      details.files ? 'readability.js' : details.func.name))
      .toEqual(['readability.js', 'extractReadable', 'extractGeneric'])
  },
)

it('falls back to generic when injecting readability.js rejects', async () => {
  connect()
  chromeMock.scripting.executeScript.mockImplementation(async (details: { files?: string[]; func?: () => unknown }) => {
    if (details.files) throw new Error('Cannot inject library')
    return [{ result: captured }]
  })
  fetchMock.mockImplementation(async (url: string) => url.endsWith('/captures')
    ? response(201, { id: 50, waiting: 4 })
    : response(200, { name: 'My browser', waiting: 3 }))
  initPopup()
  fireEvent.click(await screen.findByRole('button', { name: 'Add this page to my next digest' }))
  await screen.findByText('Saved. It will be in your next digest.')
  expect(chromeMock.scripting.executeScript.mock.calls.map(([details]) =>
    details.files ? 'readability.js' : details.func.name)).toEqual(['readability.js', 'extractGeneric'])
})
